# Reproducing Benchmarks

Step-by-step guide to running benchmarks and generating reports.

## Requirements

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 4 GB | 8+ GB |
| Python | 3.10+ | 3.11+ |
| Docker | 20.10+ | Latest |

### Installing Dependencies

```bash
# Clone repository
git clone https://github.com/spumer/kombu-pyamqp-threadsafe.git
cd kombu-pyamqp-threadsafe

# Install dependencies via Poetry
poetry install --with test,dev

# Or via pip
pip install -e ".[test]"
```

## Starting Infrastructure

### Docker Compose

```bash
# Start RabbitMQ and Toxiproxy
docker compose -f docker-compose.test.yml up -d

# Check status
docker compose -f docker-compose.test.yml ps
```

**Services:**

| Service | Port | Description |
|---------|------|-------------|
| RabbitMQ | 5672 | AMQP broker |
| RabbitMQ Management | 15672 | Web UI |
| Toxiproxy | 8474 | Management API |
| Toxiproxy Proxy | 25672 | Proxied RabbitMQ |

## Running Benchmarks

### Full Run

```bash
# All benchmarks with report generation
python scripts/run_benchmarks.py
```

**What happens:**

1. Environment capture (Python version, git commit, platform)
2. Clean old results
3. Run pytest with benchmark markers
4. Collect results from JSON files
5. Generate Markdown report
6. Save to history

### Quick Run

```bash
# Quick tests only (no stress and slow)
python scripts/run_benchmarks.py --quick
```

### Compare with Previous

```bash
# Compare results
python scripts/run_benchmarks.py --compare
```

### Report Only

```bash
# Use existing results
python scripts/run_benchmarks.py --report
```

## Running Individual Tests

### By Category

```bash
# Throughput tests
pytest tests/benchmarks/bench_throughput.py -v

# Scalability tests
pytest tests/benchmarks/bench_realistic.py -v

# Recovery tests (requires Toxiproxy)
pytest tests/benchmarks/bench_recovery_latency.py -v

# Stability tests
pytest tests/benchmarks/bench_race_conditions.py -v
```

### By Markers

```bash
# All benchmark tests
pytest -m benchmark -v

# Stress tests (slow)
pytest -m stress -v

# Exclude slow
pytest -m "not slow" -v
```

## Results Structure

```
reports/
├── .test-output/              # Raw JSON results
│   ├── publish_throughput_*.json
│   ├── massive_consumers_*.json
│   └── ...
└── benchmarks/
    ├── LATEST_REPORT.md       # Latest report
    ├── benchmark_history.json # Run history
    ├── run_*.json             # Archived results
    └── junit.xml              # pytest JUnit report
```

## Environment Fingerprint

Each run gets a unique fingerprint based on:

- Git commit hash
- Git dirty status (uncommitted changes)
- Python version
- Platform

!!! tip "Reproducibility"
    For exact result reproduction, ensure:

    1. Git commit matches
    2. No uncommitted changes
    3. Python version matches
    4. Docker images are up to date

## Generating Charts

```bash
# Generate static PNG/SVG charts
python scripts/generate_charts.py

# From specific report
python scripts/generate_charts.py --input report.json

# Custom output directory
python scripts/generate_charts.py --output docs/assets/images
```

## Building Documentation

```bash
# Install dependencies
pip install mkdocs-material mkdocs-charts-plugin mkdocs-static-i18n

# Local server
cd docs && mkdocs serve

# Build static site
cd docs && mkdocs build
```

Documentation will be available at http://localhost:8000
