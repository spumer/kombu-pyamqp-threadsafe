"""Bounded-shutdown benchmark: legacy DrainGuard vs dedicated_drainer.

The dedicated_drainer transport option promises a bounded connection.close():
ConnectionDrainer.stop(join_timeout=2.0) (src/kombu_pyamqp_threadsafe/drainer.py)
caps how long the drainer thread's join can take. Legacy mode (no drainer)
carries the same promise since the close()-deadlock fix below. This benchmark
checks both end-to-end, on a connection under realistic concurrent load (an
active background consumer plus a publisher, both still running when close()
is called), and compares their latency.

Why close() is bounded in dedicated_drainer mode:
amqp.Connection.close() sends Connection.Close and waits for CloseOk via
wait(), which drain_events()s on the calling thread. In dedicated_drainer mode
that routes to ConnectionDrainer.wait_activity() -- the drainer thread (not
the caller) does the actual socket read. Once CloseOk is pumped, the caller
dispatches it itself, which fires amqp's _on_close_ok -> collect() ->
ThreadSafeConnection.collect() -> ConnectionDrainer.stop(join_timeout=2.0).
ThreadSafeConnection.close() deliberately does NOT hold _transport_lock across
this wait in drainer mode (see its docstring: holding it would deadlock the
drainer out of the very read the waiter needs). So the whole close() call is
bounded by the Close/CloseOk round trip plus that one join, regardless of what
any other thread sharing the connection is doing.

Why legacy mode used to genuinely deadlock, and how the fix bounds it too:
before the fix, ThreadSafeConnection.close() wrapped the ENTIRE close+CloseOk
wait in `with self._transport_lock: super().close(...)`. If, at the moment
close() reached its internal drain_events(timeout=None) call,
DrainGuard.start_drain() had just been won by a *different* thread (the
background consumer, mid-loop), close() fell into
DrainGuard.wait_drain_finished(timeout=None) -- an unbounded wait on a
separate condition variable -- while STILL HOLDING _transport_lock (RLock,
exclusive across threads; wait_drain_finished does not touch it). The
consumer thread that won start_drain() then tried to acquire that very
_transport_lock to perform its own read (_execute_and_finish_drain) and
blocked forever. Neither side had a timeout that could break the cycle: the
consumer's own drain_events(timeout=X) never even reached its socket read (it
was stuck acquiring the lock, not inside a bounded recv), and close()'s
internal wait was unconditionally timeout=None. This was verified directly:
`faulthandler.dump_traceback_later` on a two-thread repro showed the closing
thread parked in DrainGuard.wait_drain_finished (__init__.py:442) while the
consumer thread was blocked acquiring _transport_lock inside
_execute_and_finish_drain (__init__.py:790) -- a textbook circular wait, not a
slow-but-eventually-successful call. The fix mirrors what drainer mode already
did: ThreadSafeConnection.close() no longer wraps super().close() in the outer
_transport_lock in either mode, so whichever thread ends up reading the socket
-- the consumer here, or close() itself when no consumer is active -- can
always acquire it and deliver CloseOk. See ThreadSafeConnection.close()'s own
docstring for the invariant this now protects unconditionally.

Consequently both modes now report a clean latency-only story: a deadlock in
either is a regression, not an expected finding. Rather than letting a
genuine regression hang this benchmark (or the whole `pytest -m benchmark`
run) forever, close() is still called on its own daemon thread and joined
with a bounded watchdog (CLOSE_WATCHDOG_S); a run that exceeds it is counted
as a deadlock, not folded into the latency percentiles as if it were merely
slow. A deadlocked run's connection, sockets and threads would be permanently
wedged and are deliberately abandoned (daemon threads only, so the process
can still exit) -- the watchdog exists purely as a regression guard now, kept
from when it was needed to make legacy's genuine deadlock survivable to
measure.

Why the publisher gets its own channel, separate from the one used for
queue.declare(): the first version of this benchmark shared one channel
between setup and the continuously-publishing producer. That reproduced a
SECOND, unrelated hang -- in BOTH modes, including dedicated_drainer --
because connection.close() -> _do_close_self() explicitly closes only
_default_channel (a channel-level Close/CloseOk wait, wrapped in
ChannelCoordinator.begin_teardown()/channel_operation, see __init__.py). A
channel kept continuously busy by the publisher never let that per-channel
wait see zero active operations. Giving the publisher its own channel
(connection.channel(), never touched by _do_close_self) isolates the
connection-level bound this benchmark exists to measure from that unrelated
per-channel mechanic. Even so, every close() still pays one bounded ~0.5s
self-wait for _default_channel's own Close/CloseOk handshake
(ChannelCoordinator's CHANNEL_TEARDOWN_WAIT_S) -- this shows up as the
dominant, roughly constant cost in dedicated_drainer's own completed-run
latencies below; it is a fixed per-close() cost in both modes, not something
either drainer path controls.

Why the background consumer uses a bounded drain_events(timeout=X) loop, not
drain_events(timeout=None): even a fixed close() would still block forever if
a consumer's own read blocked forever -- an unbounded consumer read holds
_transport_lock indefinitely on its own regardless of what close() does. A
bounded per-call timeout (matching test_drainer_benchmarks.py's
CONSUMER_DRAIN_TIMEOUT_S) keeps this scenario exercising the exact race that
used to deadlock legacy mode (see above), now as a regression check rather
than a reproduction.

Runs through the rabbitmq_bench Toxiproxy proxy (127.0.0.1:25672, see
tests/benchmarks/fixtures/toxiproxy.py) rather than the plain "rabbitmq" proxy
(5672) other suites use concurrently, so this benchmark does not perturb them.
No toxics are used -- only the proxy's plain pass-through.

Assertions: both dedicated_drainer and legacy must never deadlock and must
stay under the soft p95 ceiling (P95_CEILING_S) -- a bounded close() is now
the promise of both modes, so a violation in either is a regression.
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

N_RUNS = 10  # fresh connection per run -- not repeated publishes on one connection
MESSAGE_BODY = b"x" * 100
PUBLISH_INTERVAL_S = 0.01  # publisher keeps publishing while close() is measured

# Timeout for each blocking drain_events() call the background thread makes.
# Same constant and reasoning as test_drainer_benchmarks.py's
# CONSUMER_DRAIN_TIMEOUT_S: large enough to keep the consumer holding
# _transport_lock for a whole blocking read at a time (exercising close()
# against a live reader, the scenario that used to deadlock legacy mode),
# bounded so the consumer's OWN read can never itself be an unbounded wait --
# see module docstring for the distinct deadlock this benchmark guards against.
CONSUMER_DRAIN_TIMEOUT_S = 1.0

THREAD_TIMEOUT = 30.0

# Hard watchdog around the close() call itself -- a regression guard now that
# both modes promise a bounded close() (module docstring). Set comfortably
# above P95_CEILING_S so a merely-slow-but-completing close() is never
# misclassified as a deadlock, while still failing fast (well under
# THREAD_TIMEOUT) once a run is confirmed stuck rather than waiting out a
# generous THREAD_TIMEOUT for something that will never resolve.
CLOSE_WATCHDOG_S = 8.0

# Owner-set soft ceiling (2026-07-16): ConnectionDrainer.stop() bounds its own
# join to join_timeout=2.0s. close() in dedicated_drainer mode performs at
# most one such join synchronously (see module docstring), so its total
# latency is that join plus one Close/CloseOk round trip plus the fixed
# ~0.5s _default_channel teardown wait (also module docstring) -- observed in
# practice at ~0.5-0.6s total, nowhere near this ceiling. 2x the drainer's own
# join_timeout plus slack covers scheduling jitter without being a tight
# trip-wire; anything above it is a regression, not noise. Applied to
# legacy's completed (non-deadlocked) runs too, as a secondary, informational
# check.
P95_CEILING_S = 4.0


# ====================
# Result
# ====================


@dataclass
class ShutdownResult:
    """connection.close() outcomes collected across N_RUNS fresh connections.

    latencies holds only completed (non-deadlocked) close() calls -- folding
    a watchdog timeout into the percentiles as if it were merely a slow
    sample would understate how bad a deadlock is and corrupt p50/p95.
    deadlocks is asserted to be zero for both modes (module docstring); it
    stays a separate counter, not folded into errors, so a regression here
    reads as "deadlocked" rather than an ambiguous "errored".
    """

    latencies: LatencyMetrics = field(default_factory=LatencyMetrics)
    errors: int = 0
    deadlocks: int = 0

    def to_dict(self) -> dict:
        return {
            "count": self.latencies.count,
            "errors": self.errors,
            "deadlocks": self.deadlocks,
            "p50_ms": self.latencies.p50 * 1000,
            "p95_ms": self.latencies.p95 * 1000,
            "max_ms": self.latencies.max * 1000,
            "mean_ms": self.latencies.mean * 1000,
        }


# ====================
# Background threads
# ====================


def _background_drain_loop(conn, stop_event: threading.Event) -> None:
    """Active consumer thread parked in drain_events() on the low-level connection.

    Shares the connection with the publisher and the eventual close() call.
    Same background-consumer model as test_drainer_benchmarks.py's
    _background_drain_loop -- see this module's docstring for why a bounded
    per-call timeout is required here rather than drain_events(timeout=None).
    """
    while not stop_event.is_set():
        try:
            conn.drain_events(timeout=CONSUMER_DRAIN_TIMEOUT_S)
        except TimeoutError:
            continue
        except Exception:
            # Connection closing/closed underneath this read (dedicated_drainer:
            # ConnectionClosedIntentionally; legacy: whatever surfaces once the
            # transport is torn down mid-close) -- expected once a close() is
            # in flight, not a benchmark failure. On a deadlocked run (a
            # regression the module's assertions now catch) this thread
            # instead stays blocked acquiring _transport_lock and never
            # reaches this except at all; it is abandoned as a daemon thread
            # by the caller in that case.
            return


def _publisher_loop(
    producer: kombu.Producer, queue: kombu.Queue, routing_key: str, stop_event: threading.Event
) -> None:
    """Publish in a tight loop until stopped.

    Models a live publisher that has not yet noticed the shutdown, sharing
    the connection with the background consumer and the thread that
    eventually calls close().
    """
    while not stop_event.is_set():
        try:
            producer.publish(MESSAGE_BODY, routing_key=routing_key, declare=[queue])
        except Exception:
            # Same reasoning as _background_drain_loop: expected once close()
            # is in flight.
            return
        time.sleep(PUBLISH_INTERVAL_S)


# ====================
# Watchdog-bounded close()
# ====================


def _close_with_watchdog(connection: kombu_pyamqp_threadsafe.KombuConnection) -> dict:
    """Call connection.close() on its own daemon thread, bounded by CLOSE_WATCHDOG_S.

    A dedicated thread makes the call (not this one) so a regression -- a
    close() that hangs in either mode, see module docstring -- cannot hang
    this benchmark: the watchdog join() below always returns. daemon=True so
    a permanently wedged closer thread cannot block process exit.

    Returns a dict with "outcome" ("ok" | "deadlock" | "error"), "elapsed"
    (wall-clock seconds from the call to whichever of those was determined),
    and "exc" (the propagated exception, only set for "error").
    """
    closer = PropagatingThread(target=connection.close, daemon=True)
    start = time.monotonic()
    closer.start()
    try:
        closer.join(timeout=CLOSE_WATCHDOG_S)
    except Exception as exc:
        return {"outcome": "error", "elapsed": time.monotonic() - start, "exc": exc}

    elapsed = time.monotonic() - start
    if closer.is_alive():
        return {"outcome": "deadlock", "elapsed": elapsed}
    return {"outcome": "ok", "elapsed": elapsed}


# ====================
# Benchmark core
# ====================


def _run_shutdown_benchmark(
    dsn: str,
    *,
    dedicated_drainer: bool,
    queue_prefix: str,
    cleanup_queues,
) -> ShutdownResult:
    """Measure connection.close() outcomes across N_RUNS fresh connections.

    Each run has a concurrent background consumer and publisher sharing the
    connection with the (watchdog-bounded) close() call.
    """
    result = ShutdownResult()
    transport_options = {"dedicated_drainer": True} if dedicated_drainer else {}

    for i in range(N_RUNS):
        queue_name = f"{queue_prefix}_{i}"
        cleanup_queues(queue_name)

        connection = kombu_pyamqp_threadsafe.KombuConnection(
            dsn,
            transport_options=transport_options,
            heartbeat=0,  # keep the scenario clean: no heartbeat frames releasing
            # the legacy lock on their own cadence (matches
            # test_drainer_benchmarks.py's own convention).
        )
        stop_event = threading.Event()
        # daemon=True: on a deadlocked run (a regression, module docstring)
        # these threads would stay permanently blocked on _transport_lock and
        # are deliberately abandoned rather than joined forever.
        consumer_thread: PropagatingThread | None = None
        publisher_thread: PropagatingThread | None = None

        try:
            connection.connect()
            low_level_conn = connection._connection

            # One-time setup on default_channel: connection.close() ->
            # _do_close_self() explicitly closes ONLY _default_channel
            # (Channel.Close/CloseOk, a per-channel wait on top of the
            # connection-level close this benchmark targets). The publisher
            # gets its OWN channel below instead of reusing this one: sharing
            # it would make the publisher's continuous traffic keep that
            # channel's own operation-coordinator "active" for the whole
            # benchmark, entangling an unrelated channel-level wait with the
            # connection-level bound (ConnectionDrainer.stop(join_timeout))
            # this test exists to measure.
            queue = kombu.Queue(queue_name, channel=connection)
            queue.declare()

            # Bare, non-default, non-pool channel: connection.close() never
            # explicitly closes it (see above) -- it simply goes away when
            # the connection itself closes, same as any other channel on a
            # closed AMQP connection.
            pub_channel = connection.channel()
            producer = kombu.Producer(pub_channel)

            consumer_thread = PropagatingThread(
                target=_background_drain_loop, args=(low_level_conn, stop_event), daemon=True
            )
            consumer_thread.start()

            publisher_thread = PropagatingThread(
                target=_publisher_loop,
                args=(producer, queue, queue_name, stop_event),
                daemon=True,
            )
            publisher_thread.start()

            # Give both threads a moment to actually be in flight -- otherwise
            # close() could race still-starting threads and look artificially
            # uncontended.
            time.sleep(0.05)

            outcome = _close_with_watchdog(connection)

            if outcome["outcome"] == "ok":
                result.latencies.add(outcome["elapsed"])
                stop_event.set()
                for thread in (consumer_thread, publisher_thread):
                    thread.join(timeout=THREAD_TIMEOUT)
                    if thread.is_alive():
                        pytest.fail(
                            f"{thread.name} did not stop within THREAD_TIMEOUT after "
                            "a successfully completed close()"
                        )
            elif outcome["outcome"] == "deadlock":
                result.deadlocks += 1
                print(
                    f"\n!!! run {i} ({'dedicated_drainer' if dedicated_drainer else 'legacy'}): "
                    f"close() did not return within CLOSE_WATCHDOG_S={CLOSE_WATCHDOG_S}s -- "
                    "deadlock (regression -- both modes are asserted deadlock-free, see "
                    "module docstring); connection abandoned."
                )
                # Do NOT set stop_event / join: if this actually happens the
                # background threads are blocked acquiring the same lock the
                # closer holds forever (see module docstring) and will never
                # observe it anyway.
            else:
                result.errors += 1
                print(f"\n!!! run {i}: close() raised {outcome['exc']!r}")
                stop_event.set()

        except Exception as exc:
            result.errors += 1
            print(f"\n!!! run {i}: setup/measurement raised {exc!r}")
            stop_event.set()

    return result


def _print_result(label: str, result: ShutdownResult) -> None:
    m = result.to_dict()
    print(f"\n=== Shutdown Latency ({label}) ===")
    print(f"Completed: {m['count']}  Deadlocks: {m['deadlocks']}  Errors: {m['errors']}")
    if m["count"]:
        print(f"P50: {m['p50_ms']:.2f}ms  P95: {m['p95_ms']:.2f}ms  Max: {m['max_ms']:.2f}ms")
        print(f"Mean: {m['mean_ms']:.2f}ms")
    else:
        print("(no completed close() calls to report latency for)")


# ====================
# Benchmark Test
# ====================


@pytest.mark.usefixtures("requires_toxiproxy")
@pytest.mark.benchmark
class TestDrainerShutdownLatency:
    """Bounded connection.close() latency under concurrent load."""

    def test_shutdown_latency_legacy_vs_dedicated_drainer(
        self,
        rabbitmq_proxy,
        rabbitmq_username,
        rabbitmq_password,
        cleanup_queues,
        benchmark_reporter,
    ) -> None:
        """Same methodology, two modes, same broker -- compare close() outcomes old vs new."""
        dsn = f"amqp://{rabbitmq_username}:{rabbitmq_password}@127.0.0.1:25672/"

        run_id = int(time.time())
        legacy_prefix = f"bench_shutdown_legacy_{run_id}"
        drainer_prefix = f"bench_shutdown_dedicated_{run_id}"

        legacy_result = _run_shutdown_benchmark(
            dsn, dedicated_drainer=False, queue_prefix=legacy_prefix, cleanup_queues=cleanup_queues
        )
        drainer_result = _run_shutdown_benchmark(
            dsn, dedicated_drainer=True, queue_prefix=drainer_prefix, cleanup_queues=cleanup_queues
        )

        for label, result in (("legacy", legacy_result), ("dedicated_drainer", drainer_result)):
            benchmark_reporter.record(
                name="drainer_shutdown_latency",
                params={"mode": label, "n_runs": N_RUNS},
                metrics=result.to_dict(),
            )
            _print_result(label, result)

        print("\n=== Comparison ===")
        print(
            f"Deadlocks out of {N_RUNS} runs: legacy={legacy_result.deadlocks}  "
            f"dedicated_drainer={drainer_result.deadlocks}"
        )
        if legacy_result.latencies.count and drainer_result.latencies.count:
            print(
                f"P50 (completed runs only) legacy={legacy_result.latencies.p50 * 1000:.1f}ms "
                f"dedicated_drainer={drainer_result.latencies.p50 * 1000:.1f}ms"
            )
            print(
                f"P95 (completed runs only) legacy={legacy_result.latencies.p95 * 1000:.1f}ms "
                f"dedicated_drainer={drainer_result.latencies.p95 * 1000:.1f}ms"
            )

        # dedicated_drainer's whole promise is a bounded close() -- a deadlock
        # or error here is a genuine regression, not an expected finding.
        assert drainer_result.deadlocks == 0, (
            f"dedicated_drainer close() deadlocked on {drainer_result.deadlocks}/{N_RUNS} runs "
            "-- ConnectionDrainer.stop(join_timeout=2.0) should make this impossible"
        )
        assert drainer_result.errors == 0
        assert drainer_result.latencies.count == N_RUNS
        assert drainer_result.latencies.p95 < P95_CEILING_S, (
            f"dedicated_drainer p95 {drainer_result.latencies.p95:.3f}s exceeds "
            f"{P95_CEILING_S}s ceiling"
        )

        # Legacy: the close()-deadlock fix (module docstring) makes a bounded
        # close() the promise of this mode too now -- a deadlock here is a
        # regression, not the expected finding it used to be before the fix.
        assert legacy_result.deadlocks == 0, (
            f"legacy close() deadlocked on {legacy_result.deadlocks}/{N_RUNS} runs -- "
            "the outer _transport_lock must not wrap super().close() in either mode "
            "(see ThreadSafeConnection.close)"
        )
        assert legacy_result.errors == 0
        assert legacy_result.latencies.count == N_RUNS
        assert legacy_result.latencies.p95 < P95_CEILING_S, (
            f"legacy p95 {legacy_result.latencies.p95:.3f}s exceeds {P95_CEILING_S}s ceiling"
        )
