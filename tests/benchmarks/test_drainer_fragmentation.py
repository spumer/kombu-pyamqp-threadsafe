"""Fragmented-frame busy-spin benchmark for the dedicated drainer.

Methodology (fragmented-frame delivery under a dedicated drainer):
`ThreadSafeConnection._drain_into_buffers` (src/kombu_pyamqp_threadsafe/__init__.py)
reads `super().drain_events(timeout=0)` under `_transport_lock`. At timeout=0
amqp puts the socket in non-blocking mode; `TCPTransport._read`
(.venv/.../amqp/transport.py:625-647) raises `socket.timeout` on EAGAIN only
for the *initial* 7-byte frame-header read -- a partially-arrived frame
*body* (`initial=False`) hits `continue` instead, busy-spinning in a Python
loop until the rest of the body arrives, all while still holding
`_transport_lock`.

This test reproduces that scenario for real: a message with a body ~=
frame_max (131072 bytes, amqp/connection.py:203) is delivered to a consumer
connected through a Toxiproxy proxy carrying a `bandwidth` + `slicer` toxic
pair, so the body arrives downstream in many small, throttled chunks instead
of one syscall's worth of bytes. It measures, rather than asserts:

  (a) sanity -- did the message arrive intact;
  (b) the longest unbroken interval `_transport_lock` was held by the
      drainer thread during delivery (sampled from a second thread that
      continuously tries to acquire the same lock -- the wall-clock time
      each attempt blocks is the current hold duration, since RLock only
      excludes non-owner threads, and the probe never touches the lock from
      the connection's own thread);
  (c) process-wide CPU time consumed during the delivery window
      (psutil `cpu_times()`, user+system), as a busy-spin indicator: a tight
      Python spin loop burns CPU roughly proportional to wall-clock time it
      runs, unlike a thread parked in a blocking wait.

No hard thresholds are asserted on (b) or (c) -- whether this needs a
contingency fix (e.g. a small non-zero timeout on frame continuation reads)
is a decision for the project owner, not this test.
Only message delivery is asserted; the rest is printed for the owner to read.

Infra note: this suite was originally scoped to run through its own
dedicated Toxiproxy proxy, but docker-compose.test.yml only forwards three
ports on the toxiproxy container (5672 "rabbitmq", 8474 the Toxiproxy API
itself, 25672 "rabbitmq_bench") and none is free -- adding a new mapping
would require restarting the toxiproxy container, dropping the proxies other
benchmarks (test_drainer_benchmarks.py) may be using concurrently. Instead
this test borrows the existing "rabbitmq_bench" proxy (127.0.0.1:25672),
adding only two uniquely-named toxics ("frag_bandwidth", "frag_slicer") and
removing exactly those two in a finally block -- it never calls
`remove_all_toxics()` on a shared proxy and never touches "rabbitmq" or
deletes "rabbitmq_bench" itself. Because it mutates shared proxy state, this
test must not run concurrently with another benchmark that also uses
"rabbitmq_bench" -- in this repo that is already true, since `poe benchmark`
runs `pytest -m benchmark tests/benchmarks/` as one serial process.
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from dataclasses import dataclass, field

import kombu
import psutil
import pytest

import kombu_pyamqp_threadsafe
from toxiproxy_client import Proxy, ToxiproxyClient, ToxiproxyConnectionError

# ====================
# Constants
# ====================

# amqp.Connection's own default when frame_max is not overridden
# (.venv/.../amqp/connection.py:203: `frame_max = frame_max or 131072`).
MESSAGE_BODY_SIZE = 131_072

# Toxics applied to the *existing* "rabbitmq_bench" proxy (127.0.0.1:25672)
# for the duration of this test only -- see module docstring.
BANDWIDTH_TOXIC_NAME = "frag_bandwidth"
SLICER_TOXIC_NAME = "frag_slicer"
BANDWIDTH_RATE_KB = 16  # KB/s downstream cap
SLICER_AVERAGE_SIZE = 512  # bytes per slice
SLICER_SIZE_VARIATION = 128
SLICER_DELAY_US = 2_000  # 2ms between slices

# Consumer-side drain_events() poll granularity while waiting for delivery.
DRAIN_POLL_TIMEOUT_S = 1.0
# Overall budget for the message to arrive before the test gives up.
DELIVERY_TIMEOUT_S = 60.0

# Probe thread: how long it sleeps after an *uncontended* acquire before
# trying again, to keep its own overhead out of the CPU measurement below.
PROBE_IDLE_SLEEP_S = 0.001
# How long a single blocked acquire attempt waits before giving up and
# re-checking stop_event. Set well above the observed per-frame hold so a
# real continuous hold is captured as ONE sample rather than being chopped
# into several PROBE_ACQUIRE_TIMEOUT_S-sized pieces: an earlier 1.0s cap
# under-measured one continuous hold as >=8 separate ~1.0s timeouts instead
# of a single number.
PROBE_ACQUIRE_TIMEOUT_S = 30.0


# ====================
# Local fixtures (duplicated rather than imported -- see module docstring:
# this file must not require changes to tests/benchmarks/fixtures/toxiproxy.py
# or docker-compose.test.yml)
# ====================


@pytest.fixture(scope="module")
def toxiproxy_client_local():
    """Toxiproxy HTTP client, skipping the module if the server is unreachable."""
    host = os.getenv("TOXIPROXY_HOST", "127.0.0.1")
    port = int(os.getenv("TOXIPROXY_PORT", "8474"))
    client = ToxiproxyClient(host=host, port=port)
    try:
        client.version()
    except ToxiproxyConnectionError:
        pytest.skip(
            "Toxiproxy not available (run: docker compose -f docker-compose.test.yml up -d)"
        )
    return client


@pytest.fixture
def rabbitmq_bench_proxy_local(toxiproxy_client_local):
    """The shared 'rabbitmq_bench' proxy (127.0.0.1:25672).

    Does NOT call remove_all_toxics(): that would clobber toxics belonging to
    a concurrently-running benchmark. Only ever touches this test's own two
    named toxics (added in the test body, removed in its finally).
    """
    return toxiproxy_client_local.get_or_create_proxy(
        name="rabbitmq_bench",
        listen="0.0.0.0:25672",
        upstream="rabbitmq:5672",
    )


@pytest.fixture
def rabbitmq_clean_proxy_local(toxiproxy_client_local):
    """The 'rabbitmq' proxy (127.0.0.1:5672), used toxic-free.

    Backs the publisher connection only, so publishing itself is never
    slowed down by the toxics under test -- only the consumer's delivery
    path should be.
    """
    return toxiproxy_client_local.get_or_create_proxy(
        name="rabbitmq", listen="0.0.0.0:5672", upstream="rabbitmq:5672"
    )


# ====================
# Result
# ====================


@dataclass
class FragmentationResult:
    delivered: bool = False
    body_size_match: bool = False
    delivery_wall_s: float = 0.0
    lock_max_hold_s: float = 0.0
    lock_probe_samples: int = 0
    lock_probe_timeouts: int = 0
    cpu_user_s: float = 0.0
    cpu_system_s: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def cpu_total_s(self) -> float:
        return self.cpu_user_s + self.cpu_system_s

    @property
    def cpu_busy_ratio(self) -> float:
        if self.delivery_wall_s <= 0:
            return 0.0
        return self.cpu_total_s / self.delivery_wall_s


# ====================
# _transport_lock hold-time probe
# ====================


def _probe_transport_lock(
    lock: threading.RLock,
    stop_event: threading.Event,
    result: FragmentationResult,
) -> None:
    """Continuously try to acquire `lock` from an independent thread.

    RLock only excludes *other* threads, so as long as this probe never runs
    on the connection's own drainer thread, the wall-clock time a given
    `acquire()` call blocks for is exactly how long some other thread (here,
    the drainer busy-spinning inside `_drain_into_buffers`) is currently
    holding the lock without releasing it.
    """
    while not stop_event.is_set():
        start = time.monotonic()
        acquired = lock.acquire(timeout=PROBE_ACQUIRE_TIMEOUT_S)
        if not acquired:
            # Held for at least PROBE_ACQUIRE_TIMEOUT_S straight through this
            # attempt -- record it and go straight back into another wait
            # rather than treating it as "no news".
            result.lock_probe_timeouts += 1
            hold = time.monotonic() - start
            result.lock_max_hold_s = max(result.lock_max_hold_s, hold)
            continue

        hold = time.monotonic() - start
        lock.release()
        result.lock_probe_samples += 1
        result.lock_max_hold_s = max(result.lock_max_hold_s, hold)
        # Idle sleep keeps the probe's own acquire/release churn from adding
        # a competing source of CPU usage/contention while the lock is free
        # (i.e. outside the fragmented delivery window).
        time.sleep(PROBE_IDLE_SLEEP_S)


# ====================
# Benchmark core
# ====================


def _run_fragmented_delivery(
    consumer_dsn: str,
    publisher_dsn: str,
    queue_name: str,
    rabbitmq_bench_proxy: Proxy,
) -> FragmentationResult:
    """Publish one ~frame_max message through a fragmenting proxy.

    Measures delivery, `_transport_lock` hold time, and process CPU while
    the message arrives.
    """
    result = FragmentationResult()
    received: dict[str, bytes] = {}
    message_ready = threading.Event()

    def on_message(body, message):
        received["body"] = body
        message.ack()
        message_ready.set()

    consumer_connection = kombu_pyamqp_threadsafe.KombuConnection(
        consumer_dsn,
        transport_options={"dedicated_drainer": True},
        # Isolate the scenario: no heartbeat frames/locks interleaving with
        # the measurement below (same convention as
        # tests/test_drainer_integration.py timeout-semantics tests).
        heartbeat=0,
    )
    publisher_connection = None
    bandwidth_toxic = None
    slicer_toxic = None

    try:
        consumer_connection.connect()
        transport_lock = consumer_connection._connection._transport_lock

        channel = consumer_connection.default_channel
        queue = kombu.Queue(queue_name, channel=consumer_connection)
        queue.declare()

        consumer = kombu.Consumer(
            channel, queues=[queue], callbacks=[on_message], accept=["application/data"]
        )
        consumer.consume()

        # Toxics go on AFTER declare/consume so that RPC setup traffic
        # (Queue.Declare, Basic.Consume) is not itself throttled/sliced --
        # only the message delivery under test should be.
        bandwidth_toxic = rabbitmq_bench_proxy.add_toxic(
            name=BANDWIDTH_TOXIC_NAME,
            toxic_type="bandwidth",
            attributes={"rate": BANDWIDTH_RATE_KB},
        )
        slicer_toxic = rabbitmq_bench_proxy.add_toxic(
            name=SLICER_TOXIC_NAME,
            toxic_type="slicer",
            attributes={
                "average_size": SLICER_AVERAGE_SIZE,
                "size_variation": SLICER_SIZE_VARIATION,
                "delay": SLICER_DELAY_US,
            },
        )

        stop_probe = threading.Event()
        probe_thread = threading.Thread(
            target=_probe_transport_lock,
            args=(transport_lock, stop_probe, result),
            daemon=True,
        )
        probe_thread.start()

        process = psutil.Process()
        cpu_before = process.cpu_times()
        wall_start = time.monotonic()

        publisher_connection = kombu_pyamqp_threadsafe.KombuConnection(publisher_dsn, heartbeat=0)
        publisher_connection.connect()
        producer = kombu.Producer(publisher_connection.default_channel)
        body = (bytes(range(256)) * (MESSAGE_BODY_SIZE // 256))[:MESSAGE_BODY_SIZE]
        producer.publish(
            body,
            routing_key=queue_name,
            declare=[queue],
            content_type="application/data",
            content_encoding="binary",
        )

        deadline = wall_start + DELIVERY_TIMEOUT_S
        while not message_ready.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                consumer_connection.drain_events(timeout=min(DRAIN_POLL_TIMEOUT_S, remaining))
            except TimeoutError:
                continue

        wall_end = time.monotonic()
        cpu_after = process.cpu_times()

        stop_probe.set()
        # The probe may be mid-way through a single acquire(timeout=
        # PROBE_ACQUIRE_TIMEOUT_S) call when stop_probe is set; give it that
        # long (plus slack) to notice the timeout/success and re-check
        # stop_event before treating a still-alive thread as an error.
        probe_join_timeout = PROBE_ACQUIRE_TIMEOUT_S + 5.0
        probe_thread.join(timeout=probe_join_timeout)
        if probe_thread.is_alive():
            result.errors.append(
                f"lock probe thread did not stop within {probe_join_timeout}s"
            )

        result.delivered = message_ready.is_set()
        result.delivery_wall_s = wall_end - wall_start
        result.cpu_user_s = cpu_after.user - cpu_before.user
        result.cpu_system_s = cpu_after.system - cpu_before.system
        if result.delivered:
            result.body_size_match = received.get("body") == body

    finally:
        # Toxics removed before connection teardown so close()/cancel() is
        # never itself slowed by a lingering toxic.
        if bandwidth_toxic is not None:
            bandwidth_toxic.remove()
        if slicer_toxic is not None:
            slicer_toxic.remove()

        if publisher_connection is not None:
            with contextlib.suppress(Exception):
                publisher_connection.close()

        with contextlib.suppress(Exception):
            kombu.Queue(queue_name, channel=consumer_connection).delete()

        with contextlib.suppress(Exception):
            consumer_connection.close()

    return result


def _print_result(result: FragmentationResult) -> None:
    print("\n=== Fragmented Frame Delivery (dedicated_drainer) ===")
    print(f"Message size: {MESSAGE_BODY_SIZE} bytes (~frame_max)")
    print(
        f"Toxics: bandwidth={BANDWIDTH_RATE_KB}KB/s, "
        f"slicer avg={SLICER_AVERAGE_SIZE}B var={SLICER_SIZE_VARIATION}B "
        f"delay={SLICER_DELAY_US}us"
    )
    print(f"Delivered: {result.delivered}  Body matches: {result.body_size_match}")
    print(f"Delivery wall time: {result.delivery_wall_s:.3f}s")
    print(
        f"_transport_lock max continuous hold: {result.lock_max_hold_s * 1000:.1f}ms "
        f"(probe samples: {result.lock_probe_samples}, "
        f"probe timeouts >= {PROBE_ACQUIRE_TIMEOUT_S}s: {result.lock_probe_timeouts})"
    )
    print(
        f"CPU during window: user={result.cpu_user_s:.3f}s system={result.cpu_system_s:.3f}s "
        f"total={result.cpu_total_s:.3f}s (busy_ratio={result.cpu_busy_ratio:.3f} "
        f"of one core over wall time)"
    )
    if result.errors:
        print(f"Errors: {result.errors}")


# ====================
# Benchmark Test
# ====================


@pytest.mark.usefixtures("toxiproxy_client_local")
@pytest.mark.benchmark
class TestDrainerFragmentedFrame:
    """Iteration 10.

    Fragmented frame body under dedicated_drainer -- does it busy-spin, and
    for how long does it hold _transport_lock while doing so.
    """

    def test_fragmented_delivery_lock_hold_and_cpu(
        self,
        rabbitmq_bench_proxy_local,
        rabbitmq_clean_proxy_local,
        rabbitmq_username,
        rabbitmq_password,
    ) -> None:
        consumer_dsn = f"amqp://{rabbitmq_username}:{rabbitmq_password}@127.0.0.1:25672/"
        publisher_dsn = f"amqp://{rabbitmq_username}:{rabbitmq_password}@127.0.0.1:5672/"
        queue_name = f"frag_bench_{int(time.time())}"

        result = _run_fragmented_delivery(
            consumer_dsn, publisher_dsn, queue_name, rabbitmq_bench_proxy_local
        )
        _print_result(result)

        # Sanity only -- no threshold on lock hold time or CPU: that call
        # belongs to the project owner, not this test.
        assert result.delivered, "message was not delivered within DELIVERY_TIMEOUT_S"
        assert result.body_size_match, "delivered body does not match published body"
        assert not result.errors, result.errors
