"""Recovery Latency Benchmark.

Uses Toxiproxy for realistic network failure simulation:
- reset_peer: TCP RST (connection reset by peer) - RabbitMQ crash
- timeout: Network partition - cable disconnect
- latency + reset: Degraded network then failure

Metrics measured:
- error_detection_latency: Time for first thread to detect error
- error_propagation_latency: Time for all threads to receive error
- full_recovery_latency: Time until all channels are working

Target metrics (50+ threads):
- error_detection_latency: < 100ms
- error_propagation_latency: < 500ms
- full_recovery_latency: < 5s

Requires: docker compose -f docker-compose.test.yml up -d
"""

import threading
import time
from dataclasses import dataclass

import pytest

import kombu_pyamqp_threadsafe
from testing import PropagatingThread

# ====================
# Constants
# ====================

THREAD_TIMEOUT = 30.0
OPERATION_TIMEOUT = 2.0  # Timeout for AMQP operations


# ====================
# Recovery Metrics
# ====================


@dataclass
class RecoveryTimings:
    """Captures timing data during recovery."""

    failure_injected_at: float = 0.0
    first_error_detected_at: float = 0.0
    all_errors_propagated_at: float = 0.0
    first_recovery_at: float = 0.0
    all_recovered_at: float = 0.0

    @property
    def error_detection_latency(self) -> float:
        if self.first_error_detected_at and self.failure_injected_at:
            return self.first_error_detected_at - self.failure_injected_at
        return 0.0

    @property
    def error_propagation_latency(self) -> float:
        if self.all_errors_propagated_at and self.failure_injected_at:
            return self.all_errors_propagated_at - self.failure_injected_at
        return 0.0

    @property
    def full_recovery_latency(self) -> float:
        if self.all_recovered_at and self.failure_injected_at:
            return self.all_recovered_at - self.failure_injected_at
        return 0.0

    def to_dict(self) -> dict:
        return {
            "error_detection_latency_ms": self.error_detection_latency * 1000,
            "error_propagation_latency_ms": self.error_propagation_latency * 1000,
            "full_recovery_latency_ms": self.full_recovery_latency * 1000,
        }


# ====================
# Toxiproxy Benchmarks
# ====================


@pytest.mark.usefixtures("requires_toxiproxy")
@pytest.mark.benchmark
class TestRecoveryLatency:
    """Recovery latency benchmarks using Toxiproxy.

    Simulates real network failures:
    - reset_peer: TCP RST (RabbitMQ crash)
    - timeout: Network partition
    - latency + reset: Degraded network then failure
    """

    @pytest.fixture
    def toxiproxy_connection(self, rabbitmq_proxy):
        """Connection through Toxiproxy on port 25672."""
        # Ensure proxy is clean
        rabbitmq_proxy.remove_all_toxics()

        conn = kombu_pyamqp_threadsafe.KombuConnection(
            "amqp://guest:guest@127.0.0.1:25672//",
            default_channel_pool_size=100,
        )
        yield conn
        try:
            conn.close()
        except Exception:
            pass
        # Clean up toxics after test
        rabbitmq_proxy.remove_all_toxics()

    @pytest.mark.parametrize("n_threads", [10, 50])
    def test_recovery_after_reset_peer(
        self,
        toxiproxy_connection,
        add_toxic_reset_peer,
        n_threads: int,
        benchmark_reporter,
    ) -> None:
        """Measure recovery latency after TCP RST.

        Simulates RabbitMQ crash or network device reset.
        Workers perform heartbeat operations until failure, then attempt recovery.
        """
        connection = toxiproxy_connection
        timings = RecoveryTimings()

        # Pre-establish connection
        _ = connection.default_channel

        # Synchronization
        all_ready = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)
        failure_injected = threading.Event()
        stop_event = threading.Event()

        error_times: list[float] = []
        recovery_times: list[float] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            # Signal ready and wait for all workers
            all_ready.wait()

            # Perform operations until failure is detected
            # drain_events actually reads from socket - will fail on broken connection
            while not stop_event.is_set():
                try:
                    if connection._connection:
                        # Short timeout to detect failure quickly
                        connection._connection.drain_events(timeout=0.05)
                except Exception:
                    with lock:
                        error_times.append(time.monotonic())
                    break

            # Wait for toxic to be removed before attempting recovery
            failure_injected.wait(timeout=THREAD_TIMEOUT)

            # Attempt recovery
            try:
                connection.ensure_connection()
                _ = connection.default_channel
                with lock:
                    recovery_times.append(time.monotonic())
            except Exception:
                pass

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        # Wait for all workers to be ready
        all_ready.wait()
        time.sleep(0.05)  # Let workers start their loops

        # Inject failure
        timings.failure_injected_at = time.monotonic()
        toxic = add_toxic_reset_peer(timeout_ms=0)

        # Wait for errors to propagate
        time.sleep(0.5)
        stop_event.set()  # Signal workers to stop polling

        # Remove toxic to allow recovery
        toxic.remove()
        failure_injected.set()  # Signal workers can attempt recovery

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        if error_times:
            timings.first_error_detected_at = min(error_times)
            timings.all_errors_propagated_at = max(error_times)
        if recovery_times:
            timings.first_recovery_at = min(recovery_times)
            timings.all_recovered_at = max(recovery_times)

        metrics = timings.to_dict()
        metrics["n_threads"] = n_threads
        metrics["failure_type"] = "reset_peer"
        metrics["n_errors"] = len(error_times)
        metrics["n_recovered"] = len(recovery_times)

        benchmark_reporter.record(
            name="recovery_reset_peer",
            params={"n_threads": n_threads},
            metrics=metrics,
        )

        print(f"\n=== Reset Peer Recovery (n={n_threads}) ===")
        print(f"Error Detection: {timings.error_detection_latency * 1000:.1f}ms")
        print(f"Error Propagation: {timings.error_propagation_latency * 1000:.1f}ms")
        print(f"Full Recovery: {timings.full_recovery_latency * 1000:.1f}ms")
        print(f"Threads: {len(error_times)} detected errors, {len(recovery_times)} recovered")

    @pytest.mark.parametrize("n_threads", [10, 50])
    def test_recovery_after_network_partition(
        self,
        toxiproxy_connection,
        add_toxic_timeout,
        n_threads: int,
        benchmark_reporter,
    ) -> None:
        """Measure recovery latency after network partition.

        Simulates network cable disconnect - no data passes through.
        Workers perform drain_events until timeout/failure.
        """
        connection = toxiproxy_connection
        timings = RecoveryTimings()

        _ = connection.default_channel

        # Synchronization
        all_ready = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)
        failure_injected = threading.Event()

        error_times: list[float] = []
        recovery_times: list[float] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            all_ready.wait()

            # drain_events will fail when connection is broken
            try:
                while True:
                    connection._connection.drain_events(timeout=OPERATION_TIMEOUT)
            except Exception:
                with lock:
                    error_times.append(time.monotonic())

            # Wait for toxic removal
            failure_injected.wait(timeout=THREAD_TIMEOUT)

            # Attempt recovery
            try:
                connection.ensure_connection()
                _ = connection.default_channel
                with lock:
                    recovery_times.append(time.monotonic())
            except Exception:
                pass

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        all_ready.wait()
        time.sleep(0.05)

        timings.failure_injected_at = time.monotonic()
        toxic = add_toxic_timeout(timeout_ms=100)

        time.sleep(1.5)  # Allow time for timeout detection
        toxic.remove()
        failure_injected.set()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        if error_times:
            timings.first_error_detected_at = min(error_times)
            timings.all_errors_propagated_at = max(error_times)
        if recovery_times:
            timings.first_recovery_at = min(recovery_times)
            timings.all_recovered_at = max(recovery_times)

        metrics = timings.to_dict()
        metrics["failure_type"] = "network_partition"
        metrics["n_threads"] = n_threads
        metrics["n_errors"] = len(error_times)
        metrics["n_recovered"] = len(recovery_times)

        benchmark_reporter.record(
            name="recovery_network_partition",
            params={"n_threads": n_threads},
            metrics=metrics,
        )

        print(f"\n=== Network Partition Recovery (n={n_threads}) ===")
        print(f"Error Detection: {timings.error_detection_latency * 1000:.1f}ms")
        print(f"Error Propagation: {timings.error_propagation_latency * 1000:.1f}ms")
        print(f"Full Recovery: {timings.full_recovery_latency * 1000:.1f}ms")
        print(f"Threads: {len(error_times)} detected errors, {len(recovery_times)} recovered")

    def test_recovery_with_latency_before_failure(
        self,
        toxiproxy_connection,
        add_toxic_latency,
        add_toxic_reset_peer,
        benchmark_reporter,
    ) -> None:
        """Measure recovery when network was slow before failure.

        Simulates degraded network that then fails completely.
        """
        connection = toxiproxy_connection
        n_threads = 20

        _ = connection.default_channel

        # Synchronization
        all_ready = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)
        stop_event = threading.Event()
        failure_injected = threading.Event()

        error_times: list[float] = []
        recovery_times: list[float] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            all_ready.wait()

            while not stop_event.is_set():
                try:
                    if connection._connection:
                        connection._connection.drain_events(timeout=0.05)
                except Exception:
                    with lock:
                        error_times.append(time.monotonic())
                    break

            failure_injected.wait(timeout=THREAD_TIMEOUT)

            try:
                connection.ensure_connection()
                _ = connection.default_channel
                with lock:
                    recovery_times.append(time.monotonic())
            except Exception:
                pass

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        all_ready.wait()
        time.sleep(0.05)

        # Add latency first (degraded network)
        latency_toxic = add_toxic_latency(200, jitter_ms=100)
        time.sleep(0.3)

        # Then fail completely
        failure_time = time.monotonic()
        reset_toxic = add_toxic_reset_peer(timeout_ms=0)

        time.sleep(0.5)
        stop_event.set()

        latency_toxic.remove()
        reset_toxic.remove()
        failure_injected.set()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        recovery_latency = 0.0
        if recovery_times:
            recovery_latency = max(recovery_times) - failure_time

        metrics = {
            "failure_type": "latency_then_reset",
            "n_threads": n_threads,
            "n_errors": len(error_times),
            "n_recovered": len(recovery_times),
            "recovery_latency_ms": recovery_latency * 1000,
        }

        benchmark_reporter.record(
            name="recovery_latency_then_reset",
            params={"n_threads": n_threads},
            metrics=metrics,
        )

        print(f"\n=== Latency+Reset Recovery (n={n_threads}) ===")
        print(f"Recovery Latency: {recovery_latency * 1000:.1f}ms")
        print(f"Threads: {len(error_times)} detected errors, {len(recovery_times)} recovered")
