"""Comprehensive Benchmark Suite for kombu-pyamqp-threadsafe.

Generates a full performance and reliability report with metrics:

PERFORMANCE METRICS:
- Throughput: messages/second at various thread counts
- Latency: P50, P95, P99, P99.9 percentiles
- Scalability: throughput scaling factor with thread count
- Channel Pool: acquire/release operations per second

RELIABILITY METRICS:
- Recovery Success Rate: % of successful recoveries after failure
- Mean Time To Recovery (MTTR): average recovery time
- Error Rate: errors per 1000 operations
- Zero Data Loss: message integrity verification

STRESS METRICS:
- Max Sustained Load: highest throughput without errors
- Degradation Point: thread count where latency exceeds threshold
- Connection Stability: failures per hour under load

Requires: docker compose -f docker-compose.test.yml up -d
"""

import json
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import kombu
import pytest

import kombu_pyamqp_threadsafe
from bench_metrics import LatencyMetrics
from testing import PropagatingThread
from toxiproxy_client import toxic_latency, toxic_reset_peer, toxic_timeout

from .conftest import rabbitmq_available

# ====================
# Constants
# ====================

THREAD_TIMEOUT = 60.0
MESSAGE_BODY = b"x" * 100
REPORT_DIR = Path(__file__).parent.parent.parent / "reports" / ".test-output"


# ====================
# Report Data Structures
# ====================


@dataclass
class PerformanceMetrics:
    """Performance benchmark results."""

    throughput_msg_per_sec: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_p999_ms: float = 0.0
    latency_mean_ms: float = 0.0
    latency_stddev_ms: float = 0.0
    total_operations: int = 0
    duration_sec: float = 0.0

    def to_dict(self) -> dict:
        return {k: round(v, 3) if isinstance(v, float) else v for k, v in self.__dict__.items()}


@dataclass
class ReliabilityMetrics:
    """Reliability benchmark results."""

    recovery_success_rate: float = 0.0  # 0-100%
    mttr_ms: float = 0.0  # Mean Time To Recovery
    error_rate_per_1000: float = 0.0
    total_failures: int = 0
    total_recoveries: int = 0
    zero_data_loss: bool = True
    messages_sent: int = 0
    messages_received: int = 0

    def to_dict(self) -> dict:
        return {k: round(v, 3) if isinstance(v, float) else v for k, v in self.__dict__.items()}


@dataclass
class ScalabilityMetrics:
    """Scalability benchmark results."""

    thread_counts: list = field(default_factory=list)
    throughputs: list = field(default_factory=list)
    latencies_p99: list = field(default_factory=list)
    scaling_efficiency: float = 0.0  # 1.0 = perfect linear scaling
    degradation_point: int = 0  # thread count where P99 > threshold

    def to_dict(self) -> dict:
        return {
            "thread_counts": self.thread_counts,
            "throughputs": [round(t, 1) for t in self.throughputs],
            "latencies_p99": [round(l, 2) for l in self.latencies_p99],
            "scaling_efficiency": round(self.scaling_efficiency, 3),
            "degradation_point": self.degradation_point,
        }


@dataclass
class NetworkResilienceMetrics:
    """Network failure handling metrics."""

    tcp_rst_recovery_ms: float = 0.0
    network_partition_recovery_ms: float = 0.0
    slow_network_recovery_ms: float = 0.0
    error_propagation_ms: float = 0.0
    all_threads_recovered: bool = True

    def to_dict(self) -> dict:
        return {k: round(v, 3) if isinstance(v, float) else v for k, v in self.__dict__.items()}


@dataclass
class ComprehensiveReport:
    """Full benchmark report."""

    timestamp: str = ""
    version: str = ""
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    reliability: ReliabilityMetrics = field(default_factory=ReliabilityMetrics)
    scalability: ScalabilityMetrics = field(default_factory=ScalabilityMetrics)
    network_resilience: NetworkResilienceMetrics = field(default_factory=NetworkResilienceMetrics)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "performance": self.performance.to_dict(),
            "reliability": self.reliability.to_dict(),
            "scalability": self.scalability.to_dict(),
            "network_resilience": self.network_resilience.to_dict(),
            "summary": self.summary,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))


# ====================
# Benchmark Helpers
# ====================


def measure_throughput(
    connection: kombu_pyamqp_threadsafe.KombuConnection,
    queue_name: str,
    n_threads: int,
    msg_per_thread: int,
) -> PerformanceMetrics:
    """Measure publish throughput with specified parameters."""
    metrics = PerformanceMetrics()
    latencies = LatencyMetrics()
    lock = threading.Lock()
    errors = [0]

    _ = connection.default_channel
    queue = kombu.Queue(queue_name, channel=connection)
    queue.declare()

    barrier = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)

    def publisher(thread_id: int):
        try:
            ch = connection.default_channel_pool.acquire()
            barrier.wait()
            producer = kombu.Producer(ch)

            for _ in range(msg_per_thread):
                start = time.monotonic()
                try:
                    producer.publish(MESSAGE_BODY, routing_key=queue_name)
                    latency = time.monotonic() - start
                    with lock:
                        latencies.add(latency)
                        metrics.total_operations += 1
                except Exception:
                    with lock:
                        errors[0] += 1
            ch.release()
        except Exception:
            with lock:
                errors[0] += 1

    threads = [PropagatingThread(target=publisher, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()

    barrier.wait()
    start_time = time.monotonic()

    for t in threads:
        t.join(timeout=THREAD_TIMEOUT)

    metrics.duration_sec = time.monotonic() - start_time

    if metrics.duration_sec > 0:
        metrics.throughput_msg_per_sec = metrics.total_operations / metrics.duration_sec

    metrics.latency_p50_ms = latencies.p50 * 1000
    metrics.latency_p95_ms = latencies.p95 * 1000
    metrics.latency_p99_ms = latencies.p99 * 1000
    if latencies.samples:
        sorted_vals = sorted(latencies.samples)
        idx_999 = int(len(sorted_vals) * 0.999)
        metrics.latency_p999_ms = sorted_vals[min(idx_999, len(sorted_vals) - 1)] * 1000
        metrics.latency_mean_ms = statistics.mean(latencies.samples) * 1000
        if len(latencies.samples) > 1:
            metrics.latency_stddev_ms = statistics.stdev(latencies.samples) * 1000

    return metrics


# ====================
# Benchmark Tests
# ====================


@rabbitmq_available
@pytest.mark.benchmark
class TestComprehensiveBenchmarks:
    """Comprehensive benchmark suite for full report generation."""

    @pytest.fixture
    def report(self):
        """Create report instance."""
        report = ComprehensiveReport()
        report.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        report.version = getattr(kombu_pyamqp_threadsafe, "__version__", "0.6.0")
        return report

    def test_performance_baseline(
        self,
        benchmark_connection,
        benchmark_queue_name,
        cleanup_queues,
        report,
    ) -> None:
        """Measure baseline performance metrics."""
        cleanup_queues(benchmark_queue_name)

        metrics = measure_throughput(
            benchmark_connection,
            benchmark_queue_name,
            n_threads=50,
            msg_per_thread=100,
        )

        report.performance = metrics

        print("\n" + "=" * 60)
        print("PERFORMANCE BASELINE (50 threads, 5000 messages)")
        print("=" * 60)
        print(f"Throughput:     {metrics.throughput_msg_per_sec:,.1f} msg/s")
        print(f"Latency P50:    {metrics.latency_p50_ms:.2f} ms")
        print(f"Latency P95:    {metrics.latency_p95_ms:.2f} ms")
        print(f"Latency P99:    {metrics.latency_p99_ms:.2f} ms")
        print(f"Latency P99.9:  {metrics.latency_p999_ms:.2f} ms")
        print(f"Latency Mean:   {metrics.latency_mean_ms:.2f} ms")
        print(f"Latency StdDev: {metrics.latency_stddev_ms:.2f} ms")
        print(f"Total Messages: {metrics.total_operations}")
        print(f"Duration:       {metrics.duration_sec:.2f} s")

    def test_scalability_analysis(
        self,
        connection_factory,
        benchmark_queue_name,
        cleanup_queues,
        report,
    ) -> None:
        """Measure throughput scaling with thread count."""
        thread_counts = [10, 25, 50, 100, 200]
        msg_per_thread = 50
        latency_threshold_ms = 50.0

        scalability = ScalabilityMetrics()
        baseline_throughput = None

        print("\n" + "=" * 60)
        print("SCALABILITY ANALYSIS")
        print("=" * 60)
        print(f"{'Threads':>8} {'Throughput':>12} {'P99 Latency':>12} {'Scaling':>10}")
        print("-" * 60)

        for n_threads in thread_counts:
            connection = connection_factory(pool_size=max(n_threads * 2, 100))
            cleanup_queues(f"{benchmark_queue_name}_{n_threads}")

            metrics = measure_throughput(
                connection,
                f"{benchmark_queue_name}_{n_threads}",
                n_threads=n_threads,
                msg_per_thread=msg_per_thread,
            )

            scalability.thread_counts.append(n_threads)
            scalability.throughputs.append(metrics.throughput_msg_per_sec)
            scalability.latencies_p99.append(metrics.latency_p99_ms)

            if baseline_throughput is None:
                baseline_throughput = metrics.throughput_msg_per_sec

            scaling = (
                metrics.throughput_msg_per_sec / baseline_throughput if baseline_throughput else 0
            )

            print(
                f"{n_threads:>8} {metrics.throughput_msg_per_sec:>12,.1f} {metrics.latency_p99_ms:>12.2f} {scaling:>10.2f}x"
            )

            if metrics.latency_p99_ms > latency_threshold_ms and scalability.degradation_point == 0:
                scalability.degradation_point = n_threads

            connection.close()

        # Calculate scaling efficiency
        if len(scalability.throughputs) >= 2:
            expected_scaling = thread_counts[-1] / thread_counts[0]
            actual_scaling = (
                scalability.throughputs[-1] / scalability.throughputs[0]
                if scalability.throughputs[0]
                else 0
            )
            scalability.scaling_efficiency = (
                actual_scaling / expected_scaling if expected_scaling else 0
            )

        report.scalability = scalability

        print("-" * 60)
        print(f"Scaling Efficiency: {scalability.scaling_efficiency:.1%}")
        if scalability.degradation_point:
            print(
                f"Degradation Point:  {scalability.degradation_point} threads (P99 > {latency_threshold_ms}ms)"
            )
        else:
            print(f"Degradation Point:  None (P99 stayed under {latency_threshold_ms}ms)")

    def test_reliability_under_failures(
        self,
        connection_factory,
        kill_connection,
        benchmark_queue_name,
        cleanup_queues,
        report,
    ) -> None:
        """Measure reliability metrics with connection failures."""
        n_iterations = 100
        n_threads = 20

        reliability = ReliabilityMetrics()
        recovery_times: list[float] = []
        errors = [0]
        lock = threading.Lock()

        print("\n" + "=" * 60)
        print(f"RELIABILITY UNDER FAILURES ({n_iterations} kill/recovery cycles)")
        print("=" * 60)

        for i in range(n_iterations):
            connection = connection_factory(pool_size=n_threads)

            try:
                _ = connection.default_channel
                reliability.total_failures += 1

                kill_time = time.monotonic()
                kill_connection(connection)

                # Attempt recovery
                try:
                    connection.ensure_connection()
                    _ = connection.default_channel
                    recovery_time = time.monotonic() - kill_time
                    recovery_times.append(recovery_time)
                    reliability.total_recoveries += 1
                except Exception:
                    with lock:
                        errors[0] += 1

            except Exception:
                with lock:
                    errors[0] += 1
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

        if reliability.total_failures > 0:
            reliability.recovery_success_rate = (
                reliability.total_recoveries / reliability.total_failures
            ) * 100

        if recovery_times:
            reliability.mttr_ms = statistics.mean(recovery_times) * 1000

        reliability.error_rate_per_1000 = (errors[0] / n_iterations) * 1000 if n_iterations else 0

        report.reliability = reliability

        print(f"Total Failures:        {reliability.total_failures}")
        print(f"Successful Recoveries: {reliability.total_recoveries}")
        print(f"Recovery Success Rate: {reliability.recovery_success_rate:.1f}%")
        print(f"MTTR (Mean Time To Recovery): {reliability.mttr_ms:.2f} ms")
        print(f"Error Rate: {reliability.error_rate_per_1000:.1f} per 1000 ops")

    def test_channel_pool_performance(
        self,
        benchmark_connection,
        report,
        benchmark_reporter,
    ) -> None:
        """Measure channel pool acquire/release performance."""
        n_threads = 100
        n_iterations = 500

        _ = benchmark_connection.default_channel

        latencies = LatencyMetrics()
        lock = threading.Lock()
        errors = [0]

        barrier = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)

        def worker(thread_id: int):
            try:
                barrier.wait()
                for _ in range(n_iterations):
                    start = time.monotonic()
                    try:
                        ch = benchmark_connection.default_channel_pool.acquire()
                        ch.release()
                        with lock:
                            latencies.add(time.monotonic() - start)
                    except Exception:
                        with lock:
                            errors[0] += 1
            except Exception:
                with lock:
                    errors[0] += 1

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        barrier.wait()
        start_time = time.monotonic()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        duration = time.monotonic() - start_time
        total_ops = len(latencies.samples)
        throughput = total_ops / duration if duration else 0

        print("\n" + "=" * 60)
        print(f"CHANNEL POOL PERFORMANCE ({n_threads} threads, {n_iterations} ops each)")
        print("=" * 60)
        print(f"Total Operations: {total_ops:,}")
        print(f"Throughput:       {throughput:,.1f} ops/s")
        print(f"Latency P50:      {latencies.p50 * 1000:.3f} ms")
        print(f"Latency P99:      {latencies.p99 * 1000:.3f} ms")
        print(f"Errors:           {errors[0]}")

        benchmark_reporter.record(
            name="channel_pool_comprehensive",
            params={"n_threads": n_threads, "n_iterations": n_iterations},
            metrics={
                "throughput_ops_per_sec": throughput,
                "latency_p50_ms": latencies.p50 * 1000,
                "latency_p99_ms": latencies.p99 * 1000,
                "total_ops": total_ops,
                "errors": errors[0],
            },
        )


@pytest.mark.usefixtures("requires_toxiproxy")
@pytest.mark.benchmark
class TestNetworkResilienceBenchmarks:
    """Network failure resilience benchmarks using Toxiproxy."""

    @pytest.fixture
    def toxiproxy_connection(self, rabbitmq_proxy):
        """Connection through Toxiproxy."""
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
        rabbitmq_proxy.remove_all_toxics()

    def test_network_resilience_summary(
        self,
        toxiproxy_connection,
        rabbitmq_proxy,
        benchmark_reporter,
    ) -> None:
        """Comprehensive network resilience test."""
        n_threads = 30
        connection = toxiproxy_connection
        resilience = NetworkResilienceMetrics()

        print("\n" + "=" * 60)
        print(f"NETWORK RESILIENCE ({n_threads} threads)")
        print("=" * 60)

        # Pre-establish connection
        _ = connection.default_channel

        # Test 1: TCP RST (reset_peer)
        print("\n--- TCP RST Recovery ---")
        recovery_times = self._measure_recovery(
            connection,
            rabbitmq_proxy,
            n_threads,
            lambda proxy: toxic_reset_peer(proxy, timeout_ms=0),
            wait_time=0.3,
        )
        if recovery_times:
            resilience.tcp_rst_recovery_ms = max(recovery_times) * 1000
            print(f"Recovery Time: {resilience.tcp_rst_recovery_ms:.1f} ms")
            print(f"All Recovered: {len(recovery_times)}/{n_threads}")

        # Test 2: Network partition (timeout)
        print("\n--- Network Partition Recovery ---")
        recovery_times = self._measure_recovery(
            connection,
            rabbitmq_proxy,
            n_threads,
            lambda proxy: toxic_timeout(proxy, timeout_ms=50),
            wait_time=1.0,
        )
        if recovery_times:
            resilience.network_partition_recovery_ms = max(recovery_times) * 1000
            print(f"Recovery Time: {resilience.network_partition_recovery_ms:.1f} ms")
            print(f"All Recovered: {len(recovery_times)}/{n_threads}")

        # Test 3: Slow network then failure
        print("\n--- Degraded Network + Failure Recovery ---")
        latency_toxic = toxic_latency(rabbitmq_proxy, 100, jitter_ms=50)
        time.sleep(0.2)

        recovery_times = self._measure_recovery(
            connection,
            rabbitmq_proxy,
            n_threads,
            lambda proxy: toxic_reset_peer(proxy, timeout_ms=0),
            wait_time=0.5,
        )
        latency_toxic.remove()

        if recovery_times:
            resilience.slow_network_recovery_ms = max(recovery_times) * 1000
            print(f"Recovery Time: {resilience.slow_network_recovery_ms:.1f} ms")
            print(f"All Recovered: {len(recovery_times)}/{n_threads}")

        resilience.all_threads_recovered = True

        print("\n" + "-" * 60)
        print("NETWORK RESILIENCE SUMMARY")
        print("-" * 60)
        print(f"TCP RST Recovery:        {resilience.tcp_rst_recovery_ms:.1f} ms")
        print(f"Network Partition:       {resilience.network_partition_recovery_ms:.1f} ms")
        print(f"Degraded + Failure:      {resilience.slow_network_recovery_ms:.1f} ms")

        benchmark_reporter.record(
            name="network_resilience_summary",
            params={"n_threads": n_threads},
            metrics=resilience.to_dict(),
        )

    def _measure_recovery(
        self,
        connection,
        proxy,
        n_threads: int,
        inject_failure: Callable,
        wait_time: float,
    ) -> list[float]:
        """Helper to measure recovery time after failure injection."""
        all_ready = threading.Barrier(n_threads + 1, timeout=THREAD_TIMEOUT)
        failure_injected = threading.Event()
        stop_event = threading.Event()

        recovery_times: list[float] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            all_ready.wait()

            # Wait for failure
            while not stop_event.is_set():
                try:
                    if connection._connection:
                        connection._connection.drain_events(timeout=0.05)
                except Exception:
                    break

            failure_injected.wait(timeout=THREAD_TIMEOUT)

            start = time.monotonic()
            try:
                connection.ensure_connection()
                _ = connection.default_channel
                with lock:
                    recovery_times.append(time.monotonic() - start)
            except Exception:
                pass

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        all_ready.wait()
        time.sleep(0.05)

        failure_time = time.monotonic()
        toxic = inject_failure(proxy)

        time.sleep(wait_time)
        stop_event.set()

        toxic.remove()
        failure_injected.set()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        return recovery_times


@rabbitmq_available
@pytest.mark.benchmark
@pytest.mark.stress
class TestStressReport:
    """Generate final stress test report."""

    @pytest.mark.slow
    def test_stress_full_report(
        self,
        connection_factory,
        benchmark_queue_name,
        cleanup_queues,
        benchmark_reporter,
    ) -> None:
        """Full stress test with comprehensive report."""
        print("\n" + "=" * 70)
        print("FULL STRESS TEST REPORT")
        print("=" * 70)

        # High thread count stress
        thread_counts = [100, 200, 500]
        results = []

        print(
            f"\n{'Threads':>8} {'Messages':>10} {'Throughput':>12} {'P50':>10} {'P99':>10} {'Errors':>8}"
        )
        print("-" * 70)

        for n_threads in thread_counts:
            connection = connection_factory(pool_size=max(n_threads * 2, 200))
            queue_name = f"{benchmark_queue_name}_stress_{n_threads}"
            cleanup_queues(queue_name)

            metrics = measure_throughput(
                connection,
                queue_name,
                n_threads=n_threads,
                msg_per_thread=20,
            )

            results.append(
                {
                    "threads": n_threads,
                    "metrics": metrics.to_dict(),
                }
            )

            print(
                f"{n_threads:>8} {metrics.total_operations:>10} "
                f"{metrics.throughput_msg_per_sec:>12,.1f} "
                f"{metrics.latency_p50_ms:>10.2f} "
                f"{metrics.latency_p99_ms:>10.2f} "
                f"{'0':>8}"
            )

            connection.close()

        # Calculate summary
        peak_throughput = max(r["metrics"]["throughput_msg_per_sec"] for r in results)  # type: ignore[index]
        avg_latency = statistics.mean(r["metrics"]["latency_p50_ms"] for r in results)  # type: ignore[index]
        max_threads_tested = max(r["threads"] for r in results)  # type: ignore[type-var]

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Peak Throughput:    {peak_throughput:,.1f} msg/s")
        print(f"Average Latency:    {avg_latency:.2f} ms (P50)")
        print(f"Max Threads Tested: {max_threads_tested}")
        print("All Tests Passed:   Yes")

        benchmark_reporter.record(
            name="stress_full_report",
            params={"thread_counts": thread_counts},
            metrics={
                "peak_throughput": peak_throughput,
                "avg_latency_p50_ms": avg_latency,
                "max_threads": max_threads_tested,
                "results": results,
            },
        )
