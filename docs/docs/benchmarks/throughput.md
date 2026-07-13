# Throughput Benchmarks

Measuring message publishing throughput under various load conditions.

## Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `messages_per_second` | Successfully published messages per second | msg/s |
| `latency_p50` | Median publishing time per message | ms |
| `latency_p95` | 95th percentile latency | ms |
| `latency_p99` | 99th percentile latency (tail) | ms |
| `errors` | Publishing error count | count |

## Tests

### test_publish_throughput

Basic throughput test. Each thread publishes `msg_per_thread` messages.

```python
@pytest.mark.parametrize("n_threads,msg_per_thread", [
    (10, 100),   # Quick smoke test: 1K messages
    (100, 100),  # Base case: 10K messages
])
def test_publish_throughput(...)
```

**Methodology:**

1. Create `n_threads` threads
2. Each thread acquires a channel from the pool
3. All threads synchronize via `Barrier`
4. Simultaneous start of publishing
5. Measure time for each publish

**Key aspects:**

- Message size: 100 bytes
- Messages published without confirmation (fire-and-forget)
- Channel returned to pool after completion

---

### test_publish_throughput_stress

Stress test with large thread count.

```python
@pytest.mark.parametrize("n_threads,msg_per_thread", [
    (300, 50),   # Medium: 15K messages
    (900, 10),   # Stress: 9K messages
])
def test_publish_throughput_stress(...)
```

!!! warning "Target"
    At 900 threads, throughput should remain > 1000 msg/s

---

### test_channel_acquire_release_throughput

Tests channel pool operation overhead.

```python
@pytest.mark.parametrize("n_threads,n_iterations", [
    (100, 100),   # Base case
    (500, 50),    # Higher contention
])
def test_channel_acquire_release_throughput(...)
```

**Measures:**

- Speed of `acquire()` / `release()` without actual AMQP operations
- Thread synchronization overhead
- Internal lock efficiency

## Results

![Throughput by Threads](../assets/images/throughput_by_threads.png)

### Throughput by Configuration

| Threads | Messages | Duration | Throughput | P50 | P99 |
|---------|----------|----------|------------|-----|-----|
| 10 | 1,000 | 0.07s | 13,537 msg/s | 0.08ms | 3.62ms |
| 100 | 10,000 | 0.44s | 22,807 msg/s | 2.96ms | 7.56ms |
| 300 | 15,000 | 1.27s | 11,815 msg/s | 3.31ms | 628.51ms |
| 900 | 9,000 | 1.14s | 7,912 msg/s | 49.93ms | 55.05ms |

### Latency Percentiles

![Latency Percentiles](../assets/images/latency_percentiles.png)

### Channel Pool Performance

| Threads | Operations | Throughput | P99 |
|---------|------------|------------|-----|
| 100 | 10,000 | 71,044 ops/s | 2.24ms |
| 500 | 25,000 | 20,739 ops/s | 518.11ms |

## Interpretation

### Why does throughput drop at 900 threads?

1. **Lock contention** — all threads compete for single `_transport_lock`
2. **Context switching** — OS spends time switching between threads
3. **TCP buffer saturation** — TCP buffers fill faster than data is sent
4. **RabbitMQ backpressure** — broker can't accept messages fast enough

### Recommendations

!!! tip "Optimal thread count"
    For maximum throughput, use 50-200 threads.
    For scaling — increase process count rather than threads per process.

## Reproduction

```bash
# Throughput tests only
pytest tests/benchmarks/bench_throughput.py -v

# Specific test
pytest tests/benchmarks/bench_throughput.py::TestThroughput::test_publish_throughput -v
```
