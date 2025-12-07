# Benchmarks Overview

Benchmarks are divided into four categories, each measuring a specific aspect of performance and reliability.

## Categories

### 1. Throughput

Measures the number of messages the system can process per unit of time.

**What we measure:**

- `messages_per_second` — messages per second
- `latency_p50/p95/p99` — per-message latency

**Tests:**

| Test | Threads | Messages | Purpose |
|------|---------|----------|---------|
| `test_publish_throughput` | 10-100 | 1K-10K | Basic throughput |
| `test_publish_throughput_stress` | 300-900 | 9K-15K | Stress test |
| `test_channel_pool_throughput` | 100-500 | 5K-25K | Channel pool performance |

[More details →](throughput.md)

---

### 2. Scalability

Measures the system's ability to handle increasing load.

**What we measure:**

- Throughput as thread count grows
- Latency degradation under load
- Startup time for large numbers of consumers

**Tests:**

| Test | Consumers | Messages | Purpose |
|------|-----------|----------|---------|
| `test_massive_consumers_stress` | 100 | 1000 | Moderate load |
| `test_massive_consumers_stress` | 500 | 2000 | High load |
| `test_massive_consumers_stress` | 900 | 3000 | Extreme load |

[More details →](scalability.md)

---

### 3. Recovery

Measures failure detection and recovery speed.

**What we measure:**

- `error_detection_latency` — time to detect failure
- `error_propagation_latency` — time for all threads to see the error
- `full_recovery_latency` — total recovery time

**Failure Types:**

| Type | Simulation | Description |
|------|------------|-------------|
| TCP RST | `toxic_reset_peer` | Connection reset (RabbitMQ crash) |
| Network Partition | `toxic_timeout` | Network break (cable disconnect) |
| Degraded + Failure | `toxic_latency` + `reset` | Slow network → failure |

[More details →](recovery.md)

---

### 4. Stability

Verifies absence of deadlocks, data loss, and race conditions.

**What we verify:**

- No deadlocks (all threads complete)
- No lost frames
- No double-release of channels
- No `KeyError: None` regression

**Tests:**

| Test | Threads | Feature |
|------|---------|---------|
| `test_chaos_no_deadlock` | 10-50 | Random operations |
| `test_chaos_with_connection_kills` | 20-50 | + periodic disconnects |
| `test_high_contention_stress` | 100-500 | High contention |
| `test_repeated_recovery_stress` | 1000 iterations | Multiple recoveries |

[More details →](stability.md)

---

## Test Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                        Throughput                                │
│                    (baseline metric)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Scalability  │  │   Recovery    │  │   Stability   │
│ (throughput   │  │ (throughput   │  │ (throughput   │
│  under load)  │  │  with failures│  │  without errs)│
└───────────────┘  └───────────────┘  └───────────────┘
```

## Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Throughput (100 threads) | > 10,000 msg/s | ✅ 19,157 msg/s |
| Throughput (900 threads) | > 1,000 msg/s | ⚠️ 988 msg/s |
| Latency P99 | < 50ms | ✅ 12.88ms |
| TCP RST Recovery | < 10ms | ✅ 0.48ms |
| Network Partition Recovery | < 100ms | ✅ 9.55ms |
| Deadlocks | 0 | ✅ 0 |
| Lost Frames | 0 | ✅ 0 |
