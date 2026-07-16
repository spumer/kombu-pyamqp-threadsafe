"""Drainer publish-latency benchmark: legacy DrainGuard vs dedicated_drainer.

Methodology ("publishing must not wait on the drainer"):
a background thread sits in a blocking drain_events() loop on the SAME
KombuConnection a publisher thread uses. In legacy mode drain_events(timeout=X)
holds _transport_lock for the whole blocking socket read -- up to X seconds
per call (__init__.py ThreadSafeConnection._execute_and_finish_drain). Every
publish() on that connection writes through the same lock (frame_writer), so
it queues up behind whichever blocking read is in flight. In dedicated_drainer
mode the background thread never touches the socket itself -- it parks in
wait_activity() -- and the drainer thread's own reads are timeout=0 on an
already-ready frame, holding the lock for microseconds. A publish should
therefore never wait behind a multi-second blocking recv() in that mode.

drain_events(timeout=None), the plan's literal worst case, is NOT used for the
background loop: nothing is ever delivered to this connection's own queue, so
in legacy mode an unbounded blocking read would never observe a frame and
would hold _transport_lock forever -- deadlocking the publisher (and the
benchmark itself) rather than merely slowing it down. CONSUMER_DRAIN_TIMEOUT_S
reproduces the identical lock-contention mechanism (blocking read holds the
lock for the call's whole duration) without the hang risk, matching the
plan's own "(или большим timeout)" allowance.

Runs through the rabbitmq_bench Toxiproxy proxy (127.0.0.1:25672, see
tests/benchmarks/fixtures/toxiproxy.py) rather than the plain "rabbitmq" proxy
(5672) other suites use concurrently, so this benchmark does not perturb them.

No hard p99 threshold is asserted here -- that call belongs to the project
owner, not this test. Assertions here are sanity only (benchmark completed,
every message got published); the p50/p95/p99/max numbers for both modes are
printed and handed back for the owner to judge.
"""

import threading
import time
from dataclasses import dataclass, field

import kombu
import pytest

import kombu_pyamqp_threadsafe
from bench_metrics import LatencyMetrics
from testing import PropagatingThread

# ====================
# Constants
# ====================

N_MESSAGES = 30
MESSAGE_BODY = b"x" * 100

# Timeout for each blocking drain_events() call the background thread makes.
# Large enough to reproduce "lock held for the whole blocking read"; bounded
# so the benchmark cannot hang -- see module docstring.
CONSUMER_DRAIN_TIMEOUT_S = 1.0

THREAD_TIMEOUT = 60.0

# Owner-set ceiling (2026-07-15): the benchmark stays informational, but no
# publish p99 may exceed this in either mode -- above it is a regression.
P99_CEILING_S = 5.0


# ====================
# Result
# ====================


@dataclass
class PublishLatencyResult:
    """Publish-latency samples collected while a background thread drains."""

    latencies: LatencyMetrics = field(default_factory=LatencyMetrics)
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "count": self.latencies.count,
            "errors": self.errors,
            "p50_ms": self.latencies.p50 * 1000,
            "p95_ms": self.latencies.p95 * 1000,
            "p99_ms": self.latencies.p99 * 1000,
            "max_ms": self.latencies.max * 1000,
            "mean_ms": self.latencies.mean * 1000,
        }


# ====================
# Background drain loop
# ====================


def _background_drain_loop(conn, stop_event: threading.Event) -> None:
    """Sit in a blocking drain_events() loop until told to stop.

    Models an idle consumer thread sharing the connection with the publisher:
    nothing is ever delivered to this connection, so every call either times
    out (legacy: after holding _transport_lock for the full window) or is
    released by the dedicated drainer's own generation bump / termination.
    """
    while not stop_event.is_set():
        try:
            conn.drain_events(timeout=CONSUMER_DRAIN_TIMEOUT_S)
        except TimeoutError:
            continue
        except Exception:
            if stop_event.is_set():
                # Teardown in progress (connection.close() racing the last
                # loop iteration) -- expected, not a benchmark failure.
                return
            raise


# ====================
# Benchmark core
# ====================


def _run_publish_vs_background_drain(
    dsn: str,
    *,
    dedicated_drainer: bool,
    queue_name: str,
) -> PublishLatencyResult:
    transport_options = {"dedicated_drainer": True} if dedicated_drainer else {}
    connection = kombu_pyamqp_threadsafe.KombuConnection(
        dsn,
        transport_options=transport_options,
        heartbeat=0,  # keep the scenario clean: no heartbeat frames releasing
        # the legacy lock on their own cadence (matches the drainer test
        # suite's own convention for timeout-semantics tests).
    )
    result = PublishLatencyResult()
    stop_event = threading.Event()
    background: PropagatingThread | None = None

    try:
        connection.connect()
        low_level_conn = connection._connection

        channel = connection.default_channel
        queue = kombu.Queue(queue_name, channel=connection)
        queue.declare()
        producer = kombu.Producer(channel)

        background = PropagatingThread(
            target=_background_drain_loop, args=(low_level_conn, stop_event)
        )
        background.start()

        # Give the background thread a moment to actually park in its first
        # blocking read -- otherwise the first publish could race a
        # still-starting thread and look artificially fast.
        time.sleep(0.05)

        for _ in range(N_MESSAGES):
            start = time.monotonic()
            try:
                producer.publish(MESSAGE_BODY, routing_key=queue_name, declare=[queue])
                result.latencies.add(time.monotonic() - start)
            except Exception:
                result.errors += 1

        queue.delete()
    finally:
        stop_event.set()
        if background is not None:
            background.join(timeout=THREAD_TIMEOUT)
            if background.is_alive():
                pytest.fail("background drain thread did not stop within THREAD_TIMEOUT")
        connection.close()

    return result


def _print_result(label: str, result: PublishLatencyResult) -> None:
    m = result.to_dict()
    print(f"\n=== Publish Latency ({label}) ===")
    print(f"Messages: {m['count']}  Errors: {m['errors']}")
    print(f"P50: {m['p50_ms']:.2f}ms  P95: {m['p95_ms']:.2f}ms  P99: {m['p99_ms']:.2f}ms")
    print(f"Max: {m['max_ms']:.2f}ms  Mean: {m['mean_ms']:.2f}ms")


# ====================
# Benchmark Test
# ====================


@pytest.mark.usefixtures("requires_toxiproxy")
@pytest.mark.benchmark
class TestDrainerPublishLatency:
    """Iteration 8: publish latency does not wait on the drainer."""

    def test_publish_latency_legacy_vs_dedicated_drainer(
        self,
        rabbitmq_proxy,
        clean_toxics,
        rabbitmq_username,
        rabbitmq_password,
        cleanup_queues,
        benchmark_reporter,
    ) -> None:
        """Same methodology, two modes, same broker -- compare p99 old vs new."""
        dsn = f"amqp://{rabbitmq_username}:{rabbitmq_password}@127.0.0.1:25672/"

        run_id = int(time.time())
        legacy_queue = f"bench_drainer_latency_legacy_{run_id}"
        drainer_queue = f"bench_drainer_latency_dedicated_{run_id}"
        cleanup_queues(legacy_queue)
        cleanup_queues(drainer_queue)

        legacy_result = _run_publish_vs_background_drain(
            dsn, dedicated_drainer=False, queue_name=legacy_queue
        )
        drainer_result = _run_publish_vs_background_drain(
            dsn, dedicated_drainer=True, queue_name=drainer_queue
        )

        for label, result in (("legacy", legacy_result), ("dedicated_drainer", drainer_result)):
            benchmark_reporter.record(
                name="drainer_publish_latency",
                params={
                    "mode": label,
                    "n_messages": N_MESSAGES,
                    "consumer_drain_timeout_s": CONSUMER_DRAIN_TIMEOUT_S,
                },
                metrics=result.to_dict(),
            )
            _print_result(label, result)

        legacy_p99 = legacy_result.latencies.p99
        drainer_p99 = drainer_result.latencies.p99
        ratio = legacy_p99 / drainer_p99 if drainer_p99 > 0 else float("inf")
        print(f"\n=== Comparison ===\nP99 legacy / P99 dedicated_drainer: {ratio:.1f}x")

        # Sanity only -- the benchmark stays informational: no tight p99
        # threshold. The single hard bound below is the owner-set ceiling
        # (2026-07-15): no publish may take longer than 5 seconds in either
        # mode; anything above that is a functional regression, not noise.
        assert legacy_result.latencies.count == N_MESSAGES
        assert legacy_result.errors == 0
        assert drainer_result.latencies.count == N_MESSAGES
        assert drainer_result.errors == 0
        assert legacy_p99 <= P99_CEILING_S, f"legacy p99 {legacy_p99:.3f}s exceeds {P99_CEILING_S}s ceiling"
        assert drainer_p99 <= P99_CEILING_S, f"dedicated_drainer p99 {drainer_p99:.3f}s exceeds {P99_CEILING_S}s ceiling"
