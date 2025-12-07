# Scalability Benchmarks

Measuring system's ability to handle large numbers of concurrent consumers.

## Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `produce_throughput` | Message publishing rate | msg/s |
| `consume_throughput` | Message consumption rate | msg/s |
| `latency_p50/p99` | End-to-end latency (publish to consume) | ms |
| `message_loss_pct` | Percentage of lost messages | % |
| `consumer_startup_sec` | Time to start all consumers | sec |

## Tests

### test_massive_consumers_stress

Key scalability test. Verifies operation with extreme concurrent consumer counts.

```python
@pytest.mark.parametrize("n_consumers,n_messages", [
    (100, 1000),   # Moderate stress
    (500, 2000),   # High stress
    (900, 3000),   # Extreme stress
])
def test_massive_consumers_stress(...)
```

**Methodology:**

1. Create connection with pool size `n_consumers + 10`
2. Start `n_consumers` consumer threads
3. All consumers synchronize via `Barrier`
4. After all consumers ready — publish messages
5. Measure consumption time for each message

---

### test_concurrent_produce_consume

Realistic scenario with simultaneous producers and consumers.

```python
@pytest.mark.parametrize("n_producers,n_consumers,n_messages", [
    (5, 5, 500),    # Balanced workload
    (10, 3, 300),   # Producer-heavy
])
def test_concurrent_produce_consume(...)
```

---

### test_burst_traffic

Testing burst traffic handling (traffic spikes).

```python
# Traffic pattern: (messages, delay_ms)
traffic = [
    (50, 20),    # Normal: ~50/s
    (200, 2),    # Spike: ~500/s
    (50, 20),    # Normal
    (300, 0),    # Heavy spike: instant
    (50, 20),    # Normal
]
```

## Results

### Scalability by Consumer Count

![Consumer Scalability](../assets/images/consumer_scalability.png)

| Consumers | Messages | Throughput | Startup | P50 | P99 | Loss |
|-----------|----------|------------|---------|-----|-----|------|
| 100 | 1,000 | 2,142 msg/s | 0.08s | 4.84ms | 13.05ms | 0% |
| 500 | 2,000 | 906 msg/s | 0.36s | 19.93ms | 315ms | 0% |
| 900 | 3,000 | 341 msg/s | 0.73s | 36.36ms | 326ms | 0% |

## Analysis

### Scaling Efficiency

$$
\text{Scaling Efficiency} = \frac{\text{Throughput}_{900} / \text{Throughput}_{100}}{900 / 100} = 1.8\%
$$

!!! info "Sublinear scaling"
    1.8% efficiency indicates significant degradation at scale.
    Expected for shared-nothing architecture with single connection.

### Bottlenecks

1. **Single Connection** — all consumers share one TCP connection
2. **Transport Lock** — all operations serialized through `_transport_lock`
3. **SimpleQueue Overhead** — each consumer maintains its own queue

### Recommendations

!!! tip "Production scaling"
    - For > 100 consumers, use multiple connections
    - Each connection — separate pool with 50-100 consumers
    - Consider queue sharding across consumers

## Reproduction

```bash
# All scalability tests
pytest tests/benchmarks/bench_realistic.py::TestRealisticWorkloads -v

# Massive consumers only
pytest tests/benchmarks/bench_realistic.py::TestRealisticWorkloads::test_massive_consumers_stress -v
```
