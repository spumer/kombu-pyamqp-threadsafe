"""Pytest fixtures for benchmark metrics.

Classes are defined in testing.py (src/), this module only provides fixtures.
"""

from pathlib import Path

import pytest

from bench_metrics import (
    BenchmarkReporter,
    LatencyMetrics,
    MetricsCollector,
    RaceInvariantChecker,
)

# ====================
# Pytest Fixtures
# ====================


@pytest.fixture(scope="session")
def benchmark_output_dir():
    """Directory for benchmark output files."""
    output_dir = Path(__file__).parent.parent.parent.parent / "reports" / ".test-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def latency_metrics():
    """Provides LatencyMetrics for measuring latencies."""
    return LatencyMetrics()


@pytest.fixture
def metrics_collector():
    """Provides MetricsCollector for benchmark measurements."""
    return MetricsCollector()


@pytest.fixture
def race_invariant_checker():
    """Provides RaceInvariantChecker for race condition testing."""
    return RaceInvariantChecker()


@pytest.fixture
def benchmark_reporter(benchmark_output_dir):
    """Provides BenchmarkReporter for saving results."""
    return BenchmarkReporter(benchmark_output_dir)
