# kombu-pyamqp-threadsafe Benchmarks

Comprehensive benchmark suite for evaluating performance and reliability of `kombu-pyamqp-threadsafe`.

## What is this?

`kombu-pyamqp-threadsafe` is a thread-safe implementation of the pyamqp transport for kombu. This documentation contains:

- **Benchmarking methodology** — what and how we measure
- **Test results** — current performance metrics
- **Reproduction guide** — how to run benchmarks yourself

## Key Metrics

```vegalite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "Key metrics overview",
  "width": 400,
  "height": 200,
  "data": {
    "values": [
      {"metric": "Peak Throughput", "value": 22547, "unit": "msg/s"},
      {"metric": "TCP RST Recovery", "value": 0.48, "unit": "ms"},
      {"metric": "Network Partition Recovery", "value": 9.55, "unit": "ms"},
      {"metric": "Max Concurrent Consumers", "value": 900, "unit": "threads"}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "metric", "type": "nominal", "title": null, "axis": {"labelAngle": -45}},
    "y": {"field": "value", "type": "quantitative", "title": "Value"},
    "color": {"field": "metric", "type": "nominal", "legend": null}
  }
}
```

## Benchmark Categories

| Category | Description | Key Metric |
|----------|-------------|------------|
| [Throughput](benchmarks/index.md) | Message publishing throughput | msg/s |
| [Scalability](benchmarks/scalability.md) | Scaling with consumer count | consumers → throughput |
| [Recovery](benchmarks/recovery.md) | Recovery time after failures | ms to recovery |
| [Stability](benchmarks/stability.md) | Deadlock and data loss prevention | 0 errors |

## Quick Start

```bash
# Start RabbitMQ and Toxiproxy
docker compose -f docker-compose.test.yml up -d

# Run benchmarks
python scripts/run_benchmarks.py

# Generate report
python scripts/run_benchmarks.py --report
```

## Test Architecture

```
tests/benchmarks/
├── conftest.py              # pytest fixtures
├── bench_throughput.py      # Throughput tests
├── bench_realistic.py       # Realistic scenarios
├── bench_recovery_latency.py # Recovery tests
├── bench_race_conditions.py # Chaos testing
└── bench_comprehensive.py   # Comprehensive tests
```

## Tools

- **pytest** — testing framework
- **Toxiproxy** — network failure simulation
- **RabbitMQ** — AMQP broker
- **matplotlib** — result visualization
