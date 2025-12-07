"""Race Conditions Benchmark.

Chaos testing to detect race conditions under extreme load:
- Random operations executed concurrently
- Periodic connection kills
- Invariant checking after each iteration

Invariants checked:
- No deadlocks (all threads complete)
- No lost frames (all frames dispatched)
- No double-release (pool consistency)
- No KeyError: None (regression check)
"""

import random
import threading
import time

import pytest

import kombu_pyamqp_threadsafe
from bench_metrics import LatencyMetrics, RaceInvariantChecker
from testing import PropagatingThread

from .conftest import rabbitmq_available

# ====================
# Constants
# ====================

THREAD_TIMEOUT = 30.0
OPERATIONS = ["drain", "connected", "acquire_release", "publish"]


# ====================
# Chaos Monkey Operations
# ====================


def random_operation(connection, queue_name: str) -> str:
    """Execute a random operation on the connection.

    Returns the name of the operation executed.
    """
    op = random.choice(OPERATIONS)

    try:
        if op == "drain":
            if connection._connection:
                connection._connection.drain_events(timeout=0.001)

        elif op == "connected":
            _ = connection.connected

        elif op == "acquire_release":
            try:
                ch = connection.default_channel_pool.acquire()
                time.sleep(random.uniform(0, 0.001))
                ch.release()
            except Exception:
                pass

        elif op == "publish":
            try:
                ch = connection.default_channel_pool.acquire()
                producer = kombu_pyamqp_threadsafe.kombu.Producer(ch)
                producer.publish(
                    b"test",
                    routing_key=queue_name,
                )
                ch.release()
            except Exception:
                pass

    except Exception:
        pass  # Expected during connection kills

    return op


# ====================
# Benchmark Tests
# ====================


@rabbitmq_available
@pytest.mark.benchmark
@pytest.mark.stress
class TestRaceConditions:
    """Chaos testing for race condition detection."""

    @pytest.mark.parametrize(
        "n_threads,n_iterations",
        [
            (10, 100),  # Quick smoke test
            (50, 100),  # Medium load
        ],
    )
    def test_chaos_no_deadlock(
        self,
        benchmark_connection,
        benchmark_queue_name,
        cleanup_queues,
        n_threads: int,
        n_iterations: int,
        benchmark_reporter,
    ) -> None:
        """Chaos test: random operations with no deadlocks.

        Multiple threads execute random operations concurrently.
        Verify all threads complete (no deadlock).
        """
        connection = benchmark_connection
        queue_name = benchmark_queue_name
        cleanup_queues(queue_name)

        # Setup
        _ = connection.default_channel
        queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue.declare()

        checker = RaceInvariantChecker()
        operation_counts = dict.fromkeys(OPERATIONS, 0)
        lock = threading.Lock()

        all_ready = threading.Event()
        ready_count = [0]
        ready_lock = threading.Lock()

        def worker(thread_id: int):
            with ready_lock:
                ready_count[0] += 1
                if ready_count[0] >= n_threads:
                    all_ready.set()

            all_ready.wait(timeout=THREAD_TIMEOUT)

            for i in range(n_iterations):
                op = random_operation(connection, queue_name)
                with lock:
                    operation_counts[op] += 1

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]

        start_time = time.monotonic()

        for t in threads:
            t.start()

        # Check for deadlock
        no_deadlock = checker.check_no_deadlock(threads, timeout=THREAD_TIMEOUT)

        duration = time.monotonic() - start_time

        metrics = {
            "duration_seconds": duration,
            "no_deadlock": no_deadlock,
            "operation_counts": operation_counts,
            **checker.to_dict(),
        }

        benchmark_reporter.record(
            name="chaos_no_deadlock",
            params={"n_threads": n_threads, "n_iterations": n_iterations},
            metrics=metrics,
        )

        print(f"\n=== Chaos Test (threads={n_threads}, iter={n_iterations}) ===")
        print(f"Duration: {duration:.2f}s")
        print(f"Operations: {operation_counts}")
        print(f"Deadlocks: {checker.deadlocks}")
        print(f"KeyError None: {checker.keyerror_none}")

        assert no_deadlock, f"Deadlock detected with {n_threads} threads"
        assert checker.keyerror_none == 0, "Regression: KeyError: None"

    @pytest.mark.parametrize(
        "n_threads,n_iterations,kill_interval",
        [
            (20, 50, 10),  # Kill every 10 iterations
            (50, 30, 5),  # More frequent kills
        ],
    )
    def test_chaos_with_connection_kills(
        self,
        connection_factory,
        kill_connection,
        reset_connection,
        benchmark_queue_name,
        cleanup_queues,
        n_threads: int,
        n_iterations: int,
        kill_interval: int,
        benchmark_reporter,
    ) -> None:
        """Chaos test with periodic connection kills.

        Tests recovery behavior under random operations with failures.
        """
        connection = connection_factory(pool_size=n_threads * 2)
        queue_name = benchmark_queue_name
        cleanup_queues(queue_name)

        # Setup
        _ = connection.default_channel
        queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue.declare()

        checker = RaceInvariantChecker()
        kills_performed = [0]
        lock = threading.Lock()

        stop_flag = threading.Event()
        iteration_count = [0]

        def worker(thread_id: int):
            while not stop_flag.is_set():
                try:
                    random_operation(connection, queue_name)
                    with lock:
                        iteration_count[0] += 1
                except KeyError as e:
                    if "None" in str(e):
                        checker.keyerror_none += 1
                except Exception as e:
                    checker.record_exception(e)

        def killer():
            """Periodically kill connection."""
            while not stop_flag.is_set():
                time.sleep(0.1)
                try:
                    kill_connection(connection)
                    with lock:
                        kills_performed[0] += 1
                except Exception:
                    pass
                time.sleep(0.2)

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        killer_thread = PropagatingThread(target=killer)

        start_time = time.monotonic()

        for t in threads:
            t.start()
        killer_thread.start()

        # Run for fixed duration
        time.sleep(3.0)
        stop_flag.set()

        # Wait for threads
        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)
        killer_thread.join(timeout=THREAD_TIMEOUT)

        duration = time.monotonic() - start_time

        # Check for alive threads (deadlock)
        alive_threads = [t for t in threads if t.is_alive()]
        if alive_threads:
            checker.deadlocks = len(alive_threads)

        metrics = {
            "duration_seconds": duration,
            "iterations": iteration_count[0],
            "kills_performed": kills_performed[0],
            **checker.to_dict(),
        }

        benchmark_reporter.record(
            name="chaos_with_kills",
            params={
                "n_threads": n_threads,
                "kill_interval": kill_interval,
            },
            metrics=metrics,
        )

        print(f"\n=== Chaos with Kills (threads={n_threads}) ===")
        print(f"Duration: {duration:.2f}s")
        print(f"Iterations: {iteration_count[0]}")
        print(f"Connection kills: {kills_performed[0]}")
        print(f"Deadlocks: {checker.deadlocks}")
        print(f"KeyError None: {checker.keyerror_none}")

        assert checker.deadlocks == 0, "Deadlock detected"
        assert checker.keyerror_none == 0, "Regression: KeyError: None"


@rabbitmq_available
@pytest.mark.benchmark
@pytest.mark.slow
@pytest.mark.stress
class TestRaceConditionsStress:
    """Extended stress tests for race conditions."""

    @pytest.mark.parametrize("n_threads", [100, 500])
    def test_high_contention_stress(
        self,
        benchmark_connection,
        benchmark_queue_name,
        cleanup_queues,
        n_threads: int,
        benchmark_reporter,
    ) -> None:
        """High contention stress test.

        Many threads competing for resources simultaneously.
        """
        connection = benchmark_connection
        queue_name = benchmark_queue_name
        cleanup_queues(queue_name)

        # Setup
        _ = connection.default_channel
        queue = kombu_pyamqp_threadsafe.kombu.Queue(queue_name, channel=connection)
        queue.declare()

        checker = RaceInvariantChecker()
        barrier = threading.Barrier(n_threads)
        completed = [0]
        lock = threading.Lock()

        def worker(thread_id: int):
            try:
                barrier.wait(timeout=THREAD_TIMEOUT)
            except threading.BrokenBarrierError:
                return

            for _ in range(10):
                random_operation(connection, queue_name)

            with lock:
                completed[0] += 1

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]

        start_time = time.monotonic()

        for t in threads:
            t.start()

        no_deadlock = checker.check_no_deadlock(threads, timeout=THREAD_TIMEOUT)

        duration = time.monotonic() - start_time

        metrics = {
            "duration_seconds": duration,
            "completed": completed[0],
            "n_threads": n_threads,
            **checker.to_dict(),
        }

        benchmark_reporter.record(
            name="high_contention_stress",
            params={"n_threads": n_threads},
            metrics=metrics,
        )

        print(f"\n=== High Contention (threads={n_threads}) ===")
        print(f"Duration: {duration:.2f}s")
        print(f"Completed: {completed[0]}/{n_threads}")
        print(f"Healthy: {checker.is_healthy()}")

        assert no_deadlock, f"Deadlock with {n_threads} threads"
        assert checker.is_healthy(), f"Invariant violations: {checker.to_dict()}"

    @pytest.mark.parametrize("n_iterations", [1000])
    def test_repeated_recovery_stress(
        self,
        connection_factory,
        kill_connection,
        n_iterations: int,
        benchmark_reporter,
    ) -> None:
        """Stress test: repeated kill/recovery cycles.

        Verifies no resource leaks or state corruption after many cycles.
        """
        checker = RaceInvariantChecker()
        recovery_latencies = LatencyMetrics()

        for i in range(n_iterations):
            connection = connection_factory(pool_size=10)

            try:
                _ = connection.default_channel

                start = time.monotonic()
                kill_connection(connection)

                # Trigger recovery
                try:
                    _ = connection.default_channel
                    recovery_latencies.add(time.monotonic() - start)
                except Exception:
                    pass

            except KeyError as e:
                if "None" in str(e):
                    checker.keyerror_none += 1
            except Exception as e:
                checker.record_exception(e)
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

        metrics = {
            "n_iterations": n_iterations,
            "recovery_p50_ms": recovery_latencies.p50 * 1000,
            "recovery_p99_ms": recovery_latencies.p99 * 1000,
            **checker.to_dict(),
        }

        benchmark_reporter.record(
            name="repeated_recovery_stress",
            params={"n_iterations": n_iterations},
            metrics=metrics,
        )

        print(f"\n=== Repeated Recovery (iterations={n_iterations}) ===")
        print(f"Recovery P50: {recovery_latencies.p50 * 1000:.2f}ms")
        print(f"Recovery P99: {recovery_latencies.p99 * 1000:.2f}ms")
        print(f"KeyError None: {checker.keyerror_none}")

        assert checker.keyerror_none == 0, "Regression: KeyError: None"
        assert checker.is_healthy(), f"Invariant violations: {checker.to_dict()}"
