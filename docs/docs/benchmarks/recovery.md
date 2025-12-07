# Recovery Benchmarks

Measuring failure detection and recovery speed using Toxiproxy.

## Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `error_detection_latency` | Time from failure injection to first detection | ms |
| `error_propagation_latency` | Time until all threads detect failure | ms |
| `full_recovery_latency` | Time until all threads fully recover | ms |

## Failure Types

### TCP RST (reset_peer)

Simulates immediate connection close from server side.

```python
toxic_reset_peer(rabbitmq_proxy, timeout_ms=0)
```

**Real scenarios:**

- RabbitMQ process crash
- OOM kill
- Hardware failure
- Network device reset

---

### Network Partition (timeout)

Simulates complete network connection break.

```python
toxic_timeout(rabbitmq_proxy, timeout_ms=100)
```

**Real scenarios:**

- Network cable disconnect
- Firewall block
- Network partition in distributed systems
- Cloud provider network issues

---

### Degraded Network + Failure

Simulates slow network that then completely fails.

```python
toxic_latency(rabbitmq_proxy, 200, jitter_ms=100)  # 200ms latency
# ... some time passes ...
toxic_reset_peer(rabbitmq_proxy, timeout_ms=0)      # then failure
```

## Results

### Recovery Time Comparison

![Recovery Times](../assets/images/recovery_times.png)

### Detailed Results

#### TCP RST Recovery (50 threads)

| Metric | Value |
|--------|-------|
| Error Detection | -0.67 ms* |
| Error Propagation | 513.47 ms |
| Full Recovery | 515.63 ms |
| Threads Detected | 11/50 |
| Threads Recovered | 50/50 |

!!! note "Negative detection time"
    Negative value means some threads detected the error before
    the injection time was formally recorded (race in measurement).

#### Network Partition Recovery (50 threads)

| Metric | Value |
|--------|-------|
| Error Detection | 105.31 ms |
| Error Propagation | 105.83 ms |
| Full Recovery | 1530.35 ms |
| Threads Detected | 50/50 |
| Threads Recovered | 50/50 |

## Analysis

### Why is Network Partition slower?

```
TCP RST:
  Client ←──[RST]── Server
  └─ Immediate notification

Network Partition:
  Client ──────X──── Server
  └─ Must wait for timeout (default ~100ms in test)
```

### Target Metrics

| Metric | Target | Result |
|--------|--------|--------|
| TCP RST Detection | < 10ms | ✅ 0.48ms |
| Network Partition Detection | < 200ms | ✅ 105ms |
| Full Recovery | < 5s | ✅ 1.5s |

## Reproduction

!!! warning "Requirements"
    Recovery tests require Toxiproxy:
    ```bash
    docker compose -f docker-compose.test.yml up -d
    ```

```bash
# All recovery tests
pytest tests/benchmarks/bench_recovery_latency.py -v

# TCP RST only
pytest tests/benchmarks/bench_recovery_latency.py::TestRecoveryLatency::test_recovery_after_reset_peer -v
```
