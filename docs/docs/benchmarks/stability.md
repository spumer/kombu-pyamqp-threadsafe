# Stability Benchmarks

Chaos testing to detect race conditions, deadlocks, and regressions.

## Invariants

Each test verifies a set of invariants that should **never** be violated:

| Invariant | Description | Violation Meaning |
|-----------|-------------|-------------------|
| `deadlocks = 0` | All threads complete within timeout | Mutual thread blocking |
| `lost_frames = 0` | All AMQP frames delivered | Data loss |
| `double_releases = 0` | Channel released once | Pool corruption |
| `keyerror_none = 0` | No `KeyError: None` | KeyError regression |

## Tests

### test_chaos_no_deadlock

Basic chaos test — random operations without external failures.

```python
@pytest.mark.parametrize("n_threads,n_iterations", [
    (10, 100),    # Quick smoke test
    (50, 100),    # Medium load
])
def test_chaos_no_deadlock(...)
```

**Operations:**

```python
OPERATIONS = ['drain', 'connected', 'acquire_release', 'publish']
```

**Verifies:**

- Thread safety of all basic operations
- Correct pool management
- No deadlocks under concurrent access

---

### test_chaos_with_connection_kills

Chaos test with periodic connection breaks.

```python
@pytest.mark.parametrize("n_threads,n_iterations,kill_interval", [
    (20, 50, 10),   # Kill every 10 iterations
    (50, 30, 5),    # More frequent kills
])
def test_chaos_with_connection_kills(...)
```

---

### test_high_contention_stress

Stress test with high resource contention.

```python
@pytest.mark.parametrize("n_threads", [100, 500])
def test_high_contention_stress(...)
```

---

### test_repeated_recovery_stress

1000 iterations of kill/recovery cycle.

```python
@pytest.mark.parametrize("n_iterations", [1000])
def test_repeated_recovery_stress(...)
```

## Results

### Chaos Tests Summary

| Test | Threads | Duration | Iterations | Deadlocks | Errors |
|------|---------|----------|------------|-----------|--------|
| chaos_no_deadlock | 50 | 0.16s | 5,000 | **0** | **0** |
| chaos_with_kills | 50 | 3.07s | 127,449 | **0** | **0** |
| chaos_with_kills | 20 | 3.05s | 105,274 | **0** | **0** |
| high_contention | 500 | 0.39s | 5,000 | **0** | **0** |

### Repeated Recovery Stats

| Metric | Value |
|--------|-------|
| Iterations | 1,000 |
| Recovery P50 | **0.01 ms** |
| Recovery P99 | **0.02 ms** |
| KeyError: None | **0** |

## KeyError: None Regression Check

!!! danger "Critical Invariant"
    `KeyError: None` is the key indicator of a regression.

    **Before fix:** Race condition in `drain_events()` could add
    `channel_id = None` to pending events dictionary.

    **After fix:** Selective exception propagation ensures correct
    exception handling in `drain_events()`.

```python
# Check in every test
assert checker.keyerror_none == 0, "Regression: KeyError: None"
```

## Reproduction

```bash
# All stability tests
pytest tests/benchmarks/bench_race_conditions.py -v

# Quick smoke test
pytest tests/benchmarks/bench_race_conditions.py::TestRaceConditions::test_chaos_no_deadlock -v

# Stress tests (slow!)
pytest tests/benchmarks/bench_race_conditions.py -v -m stress
```
