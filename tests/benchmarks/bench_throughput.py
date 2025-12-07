"""Throughput Benchmark.

Measures message throughput under concurrent load:
- messages_per_second: Raw throughput
- p50/p95/p99 latency: Per-message latency percentiles
- lock_contention: Time spent waiting for locks

Target metrics (900 threads):
- throughput: > 1000 msg/s
- p50_latency: < 10ms
- p99_latency: < 100ms
"""

import threading
import time
from dataclasses import dataclass, field

import kombu
import pytest

from bench_metrics import LatencyMetrics
from testing import PropagatingThread

from .conftest import rabbitmq_available

# ====================
# Constants
# ====================

THREAD_TIMEOUT = 60.0  # Longer timeout for throughput tests
MESSAGE_BODY = b"x" * 100  # 100 byte messages


# ====================
# Throughput Metrics
# ====================


@dataclass
class ThroughputResult:
    """Results from throughput benchmark."""

    total_messages: int = 0
    duration_seconds: float = 0.0
    latencies: LatencyMetrics = field(default_factory=LatencyMetrics)
    errors: int = 0

    @property
    def messages_per_second(self) -> float:
        if self.duration_seconds > 0:
            return self.total_messages / self.duration_seconds
        return 0.0

    def to_dict(self) -> dict:
        return {
            "total_messages": self.total_messages,
            "duration_seconds": self.duration_seconds,
            "messages_per_second": self.messages_per_second,
            "latency_p50_ms": self.latencies.p50 * 1000,
            "latency_p95_ms": self.latencies.p95 * 1000,
            "latency_p99_ms": self.latencies.p99 * 1000,
            "latency_mean_ms": self.latencies.mean * 1000,
            "errors": self.errors,
        }


# ====================
# Benchmark Tests
# ====================


@rabbitmq_available
@pytest.mark.benchmark
class TestThroughput:
    """Benchmarks for message throughput."""

    @pytest.mark.parametrize(
        "n_threads,msg_per_thread",
        [
            (10, 100),  # Quick smoke test
            (100, 100),  # Base case: 10K messages
        ],
    )
    def test_publish_throughput(
        self,
        benchmark_connection,
        benchmark_queue_name,
        cleanup_queues,
        n_threads: int,
        msg_per_thread: int,
        benchmark_reporter,
    ) -> None:
        """Measure publish throughput with concurrent threads.

        Each thread publishes msg_per_thread messages.
        Measures total throughput and per-message latency.
        """
        connection = benchmark_connection
        queue_name = benchmark_queue_name
        cleanup_queues(queue_name)

        # Setup
        _ = connection.default_channel
        queue = kombu.Queue(queue_name, channel=connection)
        queue.declare()

        result = ThroughputResult()
        lock = threading.Lock()

        barrier = threading.Barrier(n_threads + 1)

        def publisher(thread_id: int):
            try:
                # Get channel from pool
                ch = connection.default_channel_pool.acquire()

                # Wait for all threads to be ready
                barrier.wait(timeout=THREAD_TIMEOUT)

                producer = kombu.Producer(ch)

                for i in range(msg_per_thread):
                    try:
                        start = time.monotonic()
                        producer.publish(
                            MESSAGE_BODY,
                            routing_key=queue_name,
                            declare=[queue],
                        )
                        latency = time.monotonic() - start

                        with lock:
                            result.total_messages += 1
                            result.latencies.add(latency)

                    except Exception:
                        with lock:
                            result.errors += 1

                ch.release()

            except Exception:
                with lock:
                    result.errors += 1

        # Start threads
        threads = [PropagatingThread(target=publisher, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()

        # Wait for barrier and start timing
        barrier.wait(timeout=THREAD_TIMEOUT)
        start_time = time.monotonic()

        # Wait for all threads
        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        result.duration_seconds = time.monotonic() - start_time

        # Report
        metrics = result.to_dict()
        benchmark_reporter.record(
            name="publish_throughput",
            params={
                "n_threads": n_threads,
                "msg_per_thread": msg_per_thread,
                "message_size": len(MESSAGE_BODY),
            },
            metrics=metrics,
        )

        print(f"\n=== Publish Throughput (threads={n_threads}) ===")
        print(f"Messages: {result.total_messages}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Throughput: {result.messages_per_second:.1f} msg/s")
        print(f"Latency P50: {result.latencies.p50 * 1000:.2f}ms")
        print(f"Latency P99: {result.latencies.p99 * 1000:.2f}ms")
        print(f"Errors: {result.errors}")

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "n_threads,msg_per_thread",
        [
            (300, 50),  # Medium load: 15K messages
            (900, 10),  # Stress test: 9K messages
        ],
    )
    def test_publish_throughput_stress(
        self,
        benchmark_connection,
        benchmark_queue_name,
        cleanup_queues,
        n_threads: int,
        msg_per_thread: int,
        benchmark_reporter,
    ) -> None:
        """Stress test: measure throughput at scale.

        Target: > 1000 msg/s with 900 threads.
        """
        connection = benchmark_connection
        queue_name = benchmark_queue_name
        cleanup_queues(queue_name)

        _ = connection.default_channel
        queue = kombu.Queue(queue_name, channel=connection)
        queue.declare()

        result = ThroughputResult()
        lock = threading.Lock()

        ready_count = [0]
        ready_lock = threading.Lock()
        all_ready = threading.Event()

        def publisher(thread_id: int):
            try:
                ch = connection.default_channel_pool.acquire()

                with ready_lock:
                    ready_count[0] += 1
                    if ready_count[0] >= n_threads:
                        all_ready.set()

                all_ready.wait(timeout=THREAD_TIMEOUT)

                producer = kombu.Producer(ch)

                for i in range(msg_per_thread):
                    try:
                        start = time.monotonic()
                        producer.publish(
                            MESSAGE_BODY,
                            routing_key=queue_name,
                            declare=[queue],
                        )
                        latency = time.monotonic() - start

                        with lock:
                            result.total_messages += 1
                            result.latencies.add(latency)

                    except Exception:
                        with lock:
                            result.errors += 1

                ch.release()

            except Exception:
                with lock:
                    result.errors += 1

        threads = [PropagatingThread(target=publisher, args=(i,)) for i in range(n_threads)]

        start_time = time.monotonic()

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        result.duration_seconds = time.monotonic() - start_time

        metrics = result.to_dict()
        benchmark_reporter.record(
            name="publish_throughput_stress",
            params={
                "n_threads": n_threads,
                "msg_per_thread": msg_per_thread,
            },
            metrics=metrics,
        )

        print(f"\n=== Publish Throughput Stress (threads={n_threads}) ===")
        print(f"Messages: {result.total_messages}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Throughput: {result.messages_per_second:.1f} msg/s")
        print(f"Latency P50: {result.latencies.p50 * 1000:.2f}ms")
        print(f"Latency P99: {result.latencies.p99 * 1000:.2f}ms")
        print(f"Errors: {result.errors}")

        # Soft assertion for target
        if result.messages_per_second < 1000:
            print(f"WARNING: Throughput {result.messages_per_second:.1f} < 1000 msg/s target")


@rabbitmq_available
@pytest.mark.benchmark
class TestChannelPoolThroughput:
    """Benchmarks for channel pool performance."""

    @pytest.mark.parametrize(
        "n_threads,n_iterations",
        [
            (100, 100),  # Base case
            (500, 50),  # Higher contention
        ],
    )
    def test_channel_acquire_release_throughput(
        self,
        benchmark_connection,
        n_threads: int,
        n_iterations: int,
        benchmark_reporter,
    ) -> None:
        """Measure channel acquire/release throughput.

        Tests the overhead of channel pool operations under load.
        """
        connection = benchmark_connection
        _ = connection.default_channel

        result = ThroughputResult()
        lock = threading.Lock()
        barrier = threading.Barrier(n_threads + 1)

        def worker(thread_id: int):
            try:
                barrier.wait(timeout=THREAD_TIMEOUT)

                for i in range(n_iterations):
                    start = time.monotonic()
                    try:
                        ch = connection.default_channel_pool.acquire()
                        # Simulate brief work
                        ch.release()
                        latency = time.monotonic() - start

                        with lock:
                            result.total_messages += 1
                            result.latencies.add(latency)

                    except Exception:
                        with lock:
                            result.errors += 1

            except Exception:
                with lock:
                    result.errors += 1

        threads = [PropagatingThread(target=worker, args=(i,)) for i in range(n_threads)]

        for t in threads:
            t.start()

        barrier.wait(timeout=THREAD_TIMEOUT)
        start_time = time.monotonic()

        for t in threads:
            t.join(timeout=THREAD_TIMEOUT)

        result.duration_seconds = time.monotonic() - start_time

        metrics = result.to_dict()
        benchmark_reporter.record(
            name="channel_pool_throughput",
            params={
                "n_threads": n_threads,
                "n_iterations": n_iterations,
            },
            metrics=metrics,
        )

        print(f"\n=== Channel Pool Throughput (threads={n_threads}) ===")
        print(f"Operations: {result.total_messages}")
        print(f"Throughput: {result.messages_per_second:.1f} ops/s")
        print(f"Latency P50: {result.latencies.p50 * 1000:.3f}ms")
        print(f"Latency P99: {result.latencies.p99 * 1000:.3f}ms")
