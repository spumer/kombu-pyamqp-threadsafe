"""Realistic Benchmark Scenarios for kombu-pyamqp-threadsafe.

Simulates real-world messaging patterns with focus on:
1. Concurrent producer-consumer workloads
2. Network failure recovery during message processing
3. Throughput under realistic conditions

Uses high-level kombu API with context managers.

Requires: docker compose -f docker-compose.test.yml up -d
"""

import random
import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field

import kombu
import pytest

import kombu_pyamqp_threadsafe
from bench_metrics import LatencyMetrics
from testing import PropagatingThread
from toxiproxy_client import toxic_latency, toxic_reset_peer

from .conftest import rabbitmq_available

# ====================
# Constants
# ====================

THREAD_TIMEOUT = 60.0


# ====================
# Metrics Classes
# ====================


@dataclass
class RealisticMetrics:
    """Metrics for realistic scenarios."""

    total_produced: int = 0
    total_consumed: int = 0
    produce_throughput: float = 0.0
    consume_throughput: float = 0.0
    latencies: LatencyMetrics = field(default_factory=LatencyMetrics)
    errors: int = 0
    recovery_times: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_produced": self.total_produced,
            "total_consumed": self.total_consumed,
            "produce_throughput": round(self.produce_throughput, 1),
            "consume_throughput": round(self.consume_throughput, 1),
            "latency_p50_ms": round(self.latencies.p50 * 1000, 2),
            "latency_p99_ms": round(self.latencies.p99 * 1000, 2),
            "errors": self.errors,
            "message_loss_pct": round((1 - self.total_consumed / self.total_produced) * 100, 2)
            if self.total_produced
            else 0,
        }


# ====================
# Shared Fixtures
# ====================


@pytest.fixture
def bench_queue_name(request):
    """Unique queue name for benchmark."""
    return f"bench_{request.node.name}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def bench_connection(rabbitmq_dsn):
    """Connection for benchmarks with large pool."""
    conn = kombu_pyamqp_threadsafe.KombuConnection(
        rabbitmq_dsn,
        default_channel_pool_size=100,
    )
    yield conn
    conn.close()


@pytest.fixture
def toxiproxy_bench_connection(rabbitmq_proxy):
    """Connection through Toxiproxy for failure tests."""
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


@pytest.fixture
def managed_queue(request, bench_connection, bench_queue_name):
    """Queue name with automatic cleanup after test.

    Doesn't pre-declare - lets SimpleQueue handle it with defaults.
    """
    conn = bench_connection
    _ = conn.default_channel  # ensure connection

    yield bench_queue_name

    # Cleanup - delete any queue that was created
    try:
        kombu.Queue(bench_queue_name, channel=conn).delete()
    except Exception:
        pass


@pytest.fixture
def toxiproxy_managed_queue(request, toxiproxy_bench_connection):
    """Queue name through Toxiproxy with automatic cleanup."""
    conn = toxiproxy_bench_connection
    queue_name = f"toxic_{request.node.name}_{uuid.uuid4().hex[:8]}"

    _ = conn.default_channel  # ensure connection

    yield queue_name, conn

    # Cleanup
    try:
        kombu.Queue(queue_name, channel=conn).delete()
    except Exception:
        pass


# ====================
# Basic Realistic Tests (No Network Failures)
# ====================


@rabbitmq_available
@pytest.mark.benchmark
class TestRealisticWorkloads:
    """Realistic workload benchmarks without network failures."""

    @pytest.mark.parametrize(
        "n_producers,n_consumers,n_messages",
        [
            (5, 5, 500),  # Balanced workload
            (10, 3, 300),  # Producer-heavy
        ],
    )
    def test_concurrent_produce_consume(
        self,
        bench_connection,
        managed_queue,
        n_producers: int,
        n_consumers: int,
        n_messages: int,
        benchmark_reporter,
    ) -> None:
        """Concurrent producers and consumers on shared queue.

        Uses high-level API with context managers.
        """
        connection = bench_connection
        queue_name = managed_queue
        pool = connection.default_channel_pool

        metrics = RealisticMetrics()
        produced_ids: set[str] = set()
        consumed_ids: set[str] = set()
        lock = threading.Lock()

        msgs_per_producer = n_messages // n_producers
        stop_consumers = threading.Event()
        all_produced = threading.Event()

        def producer(prod_id: int) -> None:
            with pool.acquire() as ch, kombu.Producer(ch) as prod:
                for i in range(msgs_per_producer):
                    msg_id = f"{prod_id}-{i}"
                    try:
                        prod.publish(
                            {"id": msg_id, "ts": time.monotonic()},
                            routing_key=queue_name,
                            serializer="json",
                        )
                        with lock:
                            produced_ids.add(msg_id)
                            metrics.total_produced += 1
                    except Exception:
                        with lock:
                            metrics.errors += 1

        def consumer(cons_id: int) -> None:
            with pool.acquire() as ch:
                simple_queue = connection.SimpleQueue(queue_name, channel=ch)
                try:
                    while not stop_consumers.is_set():
                        try:
                            msg = simple_queue.get(timeout=0.5)
                            body = msg.payload
                            msg_id = body["id"]
                            latency = time.monotonic() - body["ts"]

                            # Simulate processing
                            time.sleep(random.uniform(0.005, 0.02))
                            msg.ack()

                            with lock:
                                if msg_id not in consumed_ids:
                                    consumed_ids.add(msg_id)
                                    metrics.total_consumed += 1
                                    metrics.latencies.add(latency)

                        except simple_queue.Empty:
                            if all_produced.is_set():
                                # Final drain attempt
                                try:
                                    msg = simple_queue.get(timeout=0.1)
                                    msg.ack()
                                    with lock:
                                        metrics.total_consumed += 1
                                except simple_queue.Empty:
                                    break
                        except Exception:
                            with lock:
                                metrics.errors += 1
                            time.sleep(0.05)
                finally:
                    simple_queue.close()

        # Start consumers first
        consumer_threads = [
            PropagatingThread(target=consumer, args=(i,)) for i in range(n_consumers)
        ]
        for t in consumer_threads:
            t.start()

        time.sleep(0.1)

        # Start producers
        produce_start = time.monotonic()
        producer_threads = [
            PropagatingThread(target=producer, args=(i,)) for i in range(n_producers)
        ]
        for t in producer_threads:
            t.start()

        for t in producer_threads:
            t.join(timeout=THREAD_TIMEOUT)

        produce_duration = time.monotonic() - produce_start
        all_produced.set()

        # Wait for consumers
        time.sleep(2.0)
        stop_consumers.set()

        for t in consumer_threads:
            t.join(timeout=THREAD_TIMEOUT)

        consume_duration = time.monotonic() - produce_start

        # Calculate metrics
        metrics.produce_throughput = (
            metrics.total_produced / produce_duration if produce_duration else 0
        )
        metrics.consume_throughput = (
            metrics.total_consumed / consume_duration if consume_duration else 0
        )

        benchmark_reporter.record(
            name="concurrent_produce_consume",
            params={
                "n_producers": n_producers,
                "n_consumers": n_consumers,
                "n_messages": n_messages,
            },
            metrics=metrics.to_dict(),
        )

        print(f"\n{'=' * 70}")
        print(f"CONCURRENT WORKLOAD ({n_producers} prod, {n_consumers} cons, {n_messages} msgs)")
        print(f"{'=' * 70}")
        print(f"Produced:          {metrics.total_produced}")
        print(f"Consumed:          {metrics.total_consumed}")
        print(f"Produce Throughput: {metrics.produce_throughput:,.1f} msg/s")
        print(f"Consume Throughput: {metrics.consume_throughput:,.1f} msg/s")
        print(f"Latency P50:       {metrics.latencies.p50 * 1000:.2f} ms")
        print(f"Latency P99:       {metrics.latencies.p99 * 1000:.2f} ms")
        print(f"Message Loss:      {metrics.to_dict()['message_loss_pct']:.1f}%")
        print(f"Errors:            {metrics.errors}")

    def test_burst_traffic(
        self,
        bench_connection,
        managed_queue,
        benchmark_reporter,
    ) -> None:
        """Burst traffic handling - sudden spikes in message rate."""
        connection = bench_connection
        queue_name = managed_queue
        pool = connection.default_channel_pool
        n_consumers = 5

        metrics = RealisticMetrics()
        lock = threading.Lock()
        stop_consumers = threading.Event()

        # Traffic pattern: (messages, delay_ms)
        traffic = [
            (50, 20),  # Normal: ~50/s
            (200, 2),  # Spike: ~500/s
            (50, 20),  # Normal
            (300, 0),  # Heavy spike: instant
            (50, 20),  # Normal
        ]

        def consumer(cons_id: int) -> None:
            with pool.acquire() as ch:
                simple_queue = connection.SimpleQueue(queue_name, channel=ch)
                try:
                    while not stop_consumers.is_set():
                        try:
                            msg = simple_queue.get(timeout=0.5)
                            latency = time.monotonic() - msg.payload.get("ts", 0)
                            time.sleep(random.uniform(0.005, 0.015))
                            msg.ack()

                            with lock:
                                metrics.total_consumed += 1
                                metrics.latencies.add(latency)

                        except simple_queue.Empty:
                            continue
                        except Exception:
                            with lock:
                                metrics.errors += 1
                            time.sleep(0.05)
                finally:
                    simple_queue.close()

        # Start consumers
        consumer_threads = [
            PropagatingThread(target=consumer, args=(i,)) for i in range(n_consumers)
        ]
        for t in consumer_threads:
            t.start()

        time.sleep(0.1)

        # Run traffic pattern
        start = time.monotonic()
        with pool.acquire() as ch, kombu.Producer(ch) as prod:
            for msg_count, delay_ms in traffic:
                for i in range(msg_count):
                    prod.publish(
                        {"ts": time.monotonic()}, routing_key=queue_name, serializer="json"
                    )
                    with lock:
                        metrics.total_produced += 1
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000)

        duration = time.monotonic() - start

        # Wait for drain
        time.sleep(3.0)
        stop_consumers.set()

        for t in consumer_threads:
            t.join(timeout=THREAD_TIMEOUT)

        metrics.produce_throughput = metrics.total_produced / duration if duration else 0

        benchmark_reporter.record(
            name="burst_traffic",
            params={"traffic_pattern": traffic},
            metrics=metrics.to_dict(),
        )

        print(f"\n{'=' * 70}")
        print(f"BURST TRAFFIC ({n_consumers} consumers)")
        print(f"{'=' * 70}")
        print(f"Produced:          {metrics.total_produced}")
        print(f"Consumed:          {metrics.total_consumed}")
        print(f"Throughput:        {metrics.produce_throughput:,.1f} msg/s")
        print(f"Latency P50:       {metrics.latencies.p50 * 1000:.2f} ms")
        print(f"Latency P99:       {metrics.latencies.p99 * 1000:.2f} ms")
        print(f"Latency Max:       {metrics.latencies.max * 1000:.2f} ms")
        print(f"Message Loss:      {metrics.to_dict()['message_loss_pct']:.1f}%")

    @pytest.mark.stress
    @pytest.mark.parametrize(
        "n_consumers,n_messages",
        [
            (100, 1000),  # Moderate stress
            (500, 2000),  # High stress
            (900, 3000),  # Extreme stress
        ],
    )
    def test_massive_consumers_stress(
        self,
        rabbitmq_dsn,
        benchmark_reporter,
        n_consumers: int,
        n_messages: int,
    ) -> None:
        """Stress test with massive number of concurrent consumers.

        Tests system stability under extreme consumer concurrency.
        Uses larger channel pool to accommodate all consumers.
        """
        # Create connection with pool matching consumer count
        connection = kombu_pyamqp_threadsafe.KombuConnection(
            rabbitmq_dsn,
            default_channel_pool_size=n_consumers + 10,
        )
        queue_name = f"stress_{n_consumers}_{uuid.uuid4().hex[:8]}"
        pool = connection.default_channel_pool

        _ = connection.default_channel  # ensure connection

        metrics = RealisticMetrics()
        consumed_ids: set[str] = set()
        lock = threading.Lock()
        stop_consumers = threading.Event()
        all_produced = threading.Event()
        consumers_ready = threading.Barrier(n_consumers + 1, timeout=120.0)

        def consumer(cons_id: int) -> None:
            try:
                with pool.acquire() as ch:
                    simple_queue = connection.SimpleQueue(queue_name, channel=ch)
                    try:
                        # Signal ready
                        consumers_ready.wait()

                        while not stop_consumers.is_set():
                            try:
                                msg = simple_queue.get(timeout=0.5)
                                msg_id = msg.payload.get("id")
                                latency = time.monotonic() - msg.payload.get("ts", 0)
                                msg.ack()

                                with lock:
                                    if msg_id not in consumed_ids:
                                        consumed_ids.add(msg_id)
                                        metrics.total_consumed += 1
                                        metrics.latencies.add(latency)

                            except simple_queue.Empty:
                                if all_produced.is_set():
                                    # Final drain
                                    try:
                                        msg = simple_queue.get(timeout=0.1)
                                        msg.ack()
                                        with lock:
                                            metrics.total_consumed += 1
                                    except simple_queue.Empty:
                                        break
                            except Exception:
                                with lock:
                                    metrics.errors += 1
                    finally:
                        simple_queue.close()
            except Exception:
                with lock:
                    metrics.errors += 1

        # Start all consumers
        print(f"\n  Starting {n_consumers} consumers...", end="", flush=True)
        start_time = time.monotonic()
        consumer_threads = [
            PropagatingThread(target=consumer, args=(i,)) for i in range(n_consumers)
        ]
        for t in consumer_threads:
            t.start()

        # Wait for all consumers to be ready
        consumers_ready.wait()
        consumer_startup = time.monotonic() - start_time
        print(f" done ({consumer_startup:.1f}s)")

        # Produce messages
        print(f"  Producing {n_messages} messages...", end="", flush=True)
        produce_start = time.monotonic()
        with pool.acquire() as ch, kombu.Producer(ch) as prod:
            for i in range(n_messages):
                prod.publish(
                    {"id": f"msg-{i}", "ts": time.monotonic()},
                    routing_key=queue_name,
                    serializer="json",
                )
                metrics.total_produced += 1

        produce_duration = time.monotonic() - produce_start
        all_produced.set()
        print(f" done ({produce_duration:.1f}s)")

        # Wait for consumption
        print("  Waiting for consumption...", end="", flush=True)
        time.sleep(min(5.0, n_messages / 500))  # Adaptive wait
        stop_consumers.set()

        for t in consumer_threads:
            t.join(timeout=120.0)

        consume_duration = time.monotonic() - produce_start
        print(" done")

        # Calculate metrics
        metrics.produce_throughput = (
            metrics.total_produced / produce_duration if produce_duration else 0
        )
        metrics.consume_throughput = (
            metrics.total_consumed / consume_duration if consume_duration else 0
        )

        # Cleanup
        try:
            kombu.Queue(queue_name, channel=connection).delete()
        except Exception:
            pass
        connection.close()

        result = metrics.to_dict()
        result["n_consumers"] = n_consumers
        result["consumer_startup_sec"] = round(consumer_startup, 2)

        benchmark_reporter.record(
            name="massive_consumers_stress",
            params={"n_consumers": n_consumers, "n_messages": n_messages},
            metrics=result,
        )

        print(f"\n{'=' * 70}")
        print(f"MASSIVE CONSUMERS STRESS ({n_consumers} consumers, {n_messages} msgs)")
        print(f"{'=' * 70}")
        print(f"Consumer Startup:  {consumer_startup:.1f}s")
        print(f"Produced:          {metrics.total_produced}")
        print(f"Consumed:          {metrics.total_consumed}")
        print(f"Produce Throughput: {metrics.produce_throughput:,.1f} msg/s")
        print(f"Consume Throughput: {metrics.consume_throughput:,.1f} msg/s")
        print(f"Latency P50:       {metrics.latencies.p50 * 1000:.2f} ms")
        print(f"Latency P99:       {metrics.latencies.p99 * 1000:.2f} ms")
        print(f"Message Loss:      {result['message_loss_pct']:.1f}%")
        print(f"Errors:            {metrics.errors}")


# ====================
# Network Failure Tests
# ====================


@pytest.mark.usefixtures("requires_toxiproxy")
@pytest.mark.benchmark
class TestRealisticWithNetworkFailures:
    """Realistic workloads with network failure injection."""

    def test_workload_with_periodic_failures(
        self,
        toxiproxy_managed_queue,
        add_toxic_reset_peer,
        benchmark_reporter,
    ) -> None:
        """Realistic workload with periodic connection failures.

        Measures:
        - Recovery time after each failure
        - Message loss during failures
        - Throughput degradation
        """
        queue_name, connection = toxiproxy_managed_queue
        pool = connection.default_channel_pool
        n_messages = 200
        n_consumers = 3
        failure_count = 3

        metrics = RealisticMetrics()
        produced_ids: set[str] = set()
        consumed_ids: set[str] = set()
        lock = threading.Lock()
        stop_flag = threading.Event()

        def producer() -> None:
            for i in range(n_messages):
                msg_id = f"msg-{i}"
                retries = 3
                while retries > 0:
                    try:
                        with pool.acquire() as ch:
                            with kombu.Producer(ch) as prod:
                                prod.publish(
                                    {"id": msg_id, "ts": time.monotonic()},
                                    routing_key=queue_name,
                                    serializer="json",
                                )
                        with lock:
                            produced_ids.add(msg_id)
                            metrics.total_produced += 1
                        break
                    except Exception:
                        retries -= 1
                        with lock:
                            metrics.errors += 1
                        time.sleep(0.1)
                time.sleep(0.01)

        def consumer(cons_id: int) -> None:
            while not stop_flag.is_set():
                try:
                    with pool.acquire() as ch:
                        simple_queue = connection.SimpleQueue(queue_name, channel=ch)
                        try:
                            while not stop_flag.is_set():
                                try:
                                    msg = simple_queue.get(timeout=0.5)
                                    msg_id = msg.payload.get("id")
                                    latency = time.monotonic() - msg.payload.get("ts", 0)
                                    time.sleep(random.uniform(0.01, 0.03))
                                    msg.ack()

                                    with lock:
                                        if msg_id not in consumed_ids:
                                            consumed_ids.add(msg_id)
                                            metrics.total_consumed += 1
                                            metrics.latencies.add(latency)

                                except simple_queue.Empty:
                                    continue
                                except Exception:
                                    break
                        finally:
                            simple_queue.close()
                except Exception:
                    with lock:
                        metrics.errors += 1
                    time.sleep(0.1)

        # Start workers
        consumer_threads = [
            PropagatingThread(target=consumer, args=(i,)) for i in range(n_consumers)
        ]
        for t in consumer_threads:
            t.start()

        producer_thread = PropagatingThread(target=producer)
        producer_thread.start()

        # Inject failures
        for i in range(failure_count):
            time.sleep(0.5)
            failure_start = time.monotonic()
            toxic = add_toxic_reset_peer(timeout_ms=0)
            time.sleep(0.1)
            toxic.remove()
            metrics.recovery_times.append(time.monotonic() - failure_start)

        producer_thread.join(timeout=THREAD_TIMEOUT)
        time.sleep(3.0)
        stop_flag.set()

        for t in consumer_threads:
            t.join(timeout=THREAD_TIMEOUT)

        lost = len(produced_ids - consumed_ids)
        avg_recovery = (
            statistics.mean(metrics.recovery_times) * 1000 if metrics.recovery_times else 0
        )

        result = metrics.to_dict()
        result["lost_messages"] = lost
        result["avg_recovery_ms"] = round(avg_recovery, 1)
        result["recovery_times_ms"] = [round(r * 1000, 1) for r in metrics.recovery_times]

        benchmark_reporter.record(
            name="workload_with_failures",
            params={"n_messages": n_messages, "failure_count": failure_count},
            metrics=result,
        )

        print(f"\n{'=' * 70}")
        print(f"WORKLOAD WITH FAILURES ({failure_count} failures)")
        print(f"{'=' * 70}")
        print(f"Produced:          {metrics.total_produced}")
        print(f"Consumed:          {metrics.total_consumed}")
        print(f"Lost:              {lost}")
        print(f"Avg Recovery:      {avg_recovery:.1f} ms")
        for i, rt in enumerate(metrics.recovery_times):
            print(f"  Failure {i + 1}:       {rt * 1000:.1f} ms")
        print(f"Errors:            {metrics.errors}")

    def test_workload_with_latency(
        self,
        toxiproxy_managed_queue,
        rabbitmq_proxy,
        benchmark_reporter,
    ) -> None:
        """Workload under degraded network (high latency)."""
        queue_name, connection = toxiproxy_managed_queue
        pool = connection.default_channel_pool
        n_messages = 50

        latencies_normal = LatencyMetrics()
        latencies_degraded = LatencyMetrics()

        def run_workload(latency_metrics: LatencyMetrics, msg_count: int) -> float:
            with pool.acquire() as ch:
                simple_queue = connection.SimpleQueue(queue_name, channel=ch)
                try:
                    with kombu.Producer(ch) as prod:
                        start = time.monotonic()
                        for i in range(msg_count):
                            send_time = time.monotonic()
                            prod.publish(
                                {"ts": send_time}, routing_key=queue_name, serializer="json"
                            )

                            # Consume immediately
                            try:
                                msg = simple_queue.get(timeout=5.0)
                                latency = time.monotonic() - send_time
                                latency_metrics.add(latency)
                                msg.ack()
                            except Exception:
                                pass

                        return time.monotonic() - start
                finally:
                    simple_queue.close()

        # Normal conditions
        duration_normal = run_workload(latencies_normal, n_messages)

        # Degraded network (200ms latency)
        toxic = toxic_latency(rabbitmq_proxy, 200, jitter_ms=50)
        duration_degraded = run_workload(latencies_degraded, n_messages)
        toxic.remove()

        benchmark_reporter.record(
            name="workload_with_latency",
            params={"injected_latency_ms": 200},
            metrics={
                "normal_duration_sec": round(duration_normal, 2),
                "degraded_duration_sec": round(duration_degraded, 2),
                "normal_p50_ms": round(latencies_normal.p50 * 1000, 2),
                "degraded_p50_ms": round(latencies_degraded.p50 * 1000, 2),
                "latency_increase_ms": round(
                    (latencies_degraded.p50 - latencies_normal.p50) * 1000, 1
                ),
                "throughput_degradation_pct": round(
                    (1 - duration_normal / duration_degraded) * 100, 1
                )
                if duration_degraded
                else 0,
            },
        )

        print(f"\n{'=' * 70}")
        print("WORKLOAD WITH NETWORK LATENCY (200ms injected)")
        print(f"{'=' * 70}")
        print(f"Normal Duration:   {duration_normal:.2f} s")
        print(f"Degraded Duration: {duration_degraded:.2f} s")
        print(f"Normal P50:        {latencies_normal.p50 * 1000:.2f} ms")
        print(f"Degraded P50:      {latencies_degraded.p50 * 1000:.2f} ms")
        print(f"Latency Increase:  {(latencies_degraded.p50 - latencies_normal.p50) * 1000:.0f} ms")

    def test_recovery_correctness(
        self,
        toxiproxy_managed_queue,
        rabbitmq_proxy,
        benchmark_reporter,
    ) -> None:
        """Verify message integrity and no duplicates after recovery."""
        queue_name, connection = toxiproxy_managed_queue
        pool = connection.default_channel_pool
        n_messages = 100

        sent_messages: list[str] = []
        received_messages: list[str] = []

        # Send messages with failures
        with pool.acquire() as ch, kombu.Producer(ch) as prod:
            for i in range(n_messages):
                msg_id = f"msg-{i:04d}"

                # Inject failure periodically
                if i > 0 and i % 25 == 0:
                    toxic = toxic_reset_peer(rabbitmq_proxy, timeout_ms=0)
                    time.sleep(0.05)
                    toxic.remove()
                    time.sleep(0.1)

                try:
                    prod.publish({"id": msg_id}, routing_key=queue_name, serializer="json")
                    sent_messages.append(msg_id)
                except Exception:
                    # Skip failed messages for now
                    pass

        # Consume all messages
        with pool.acquire() as ch:
            simple_queue = connection.SimpleQueue(queue_name, channel=ch)
            try:
                empty_count = 0
                while empty_count < 5:
                    try:
                        msg = simple_queue.get(timeout=1.0)
                        msg_id = msg.payload.get("id")
                        received_messages.append(msg_id)
                        msg.ack()
                        empty_count = 0
                    except simple_queue.Empty:
                        empty_count += 1
                    except Exception:
                        empty_count += 1
            finally:
                simple_queue.close()

        # Analyze
        sent_set = set(sent_messages)
        received_set = set(received_messages)
        duplicates = len(received_messages) - len(received_set)
        lost = sent_set - received_set
        unexpected = received_set - sent_set

        benchmark_reporter.record(
            name="recovery_correctness",
            params={"n_messages": n_messages, "failures": 4},
            metrics={
                "sent": len(sent_messages),
                "received": len(received_messages),
                "unique_received": len(received_set),
                "duplicates": duplicates,
                "lost_count": len(lost),
                "unexpected_count": len(unexpected),
                "integrity_ok": duplicates == 0 and len(unexpected) == 0,
            },
        )

        print(f"\n{'=' * 70}")
        print("RECOVERY CORRECTNESS (4 failures)")
        print(f"{'=' * 70}")
        print(f"Sent:              {len(sent_messages)}")
        print(f"Received:          {len(received_messages)}")
        print(f"Unique Received:   {len(received_set)}")
        print(f"Duplicates:        {duplicates}")
        print(f"Lost:              {len(lost)}")
        print(f"Unexpected:        {len(unexpected)}")
        print(f"Integrity OK:      {duplicates == 0 and len(unexpected) == 0}")
