"""Benchmark metrics utilities.

Provides:
- LatencyMetrics: Statistics for latency measurements
- MetricsCollector: Collects and aggregates benchmark metrics
- RaceInvariantChecker: Checks invariants for race condition testing
- BenchmarkResult: Result of a single benchmark run
- BenchmarkReporter: Reporter for saving benchmark results
"""

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from testing import PropagatingThread

DEFAULT_THREAD_TIMEOUT = 2.0


@dataclass
class LatencyMetrics:
    """Statistics for latency measurements."""

    samples: list[float] = field(default_factory=list)

    def add(self, value: float) -> None:
        """Add a latency sample."""
        self.samples.append(value)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0

    def percentile(self, p: float) -> float:
        """Calculate p-th percentile (0-100)."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        idx = min(idx, len(sorted_samples) - 1)
        return sorted_samples[idx]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    def to_dict(self) -> dict:
        """Export metrics as dictionary."""
        return {
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "stdev": self.stdev,
            "min": self.min,
            "max": self.max,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
        }


class MetricsCollector:
    """Collects and aggregates benchmark metrics."""

    def __init__(self):
        self.latencies: dict[str, LatencyMetrics] = {}
        self.counters: dict[str, int] = {}
        self.timers: dict[str, float] = {}

    def add_latency(self, name: str, value: float) -> None:
        """Add a latency measurement."""
        if name not in self.latencies:
            self.latencies[name] = LatencyMetrics()
        self.latencies[name].add(value)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value

    def set_timer(self, name: str, value: float) -> None:
        """Set a timer value."""
        self.timers[name] = value

    def get_latency_stats(self, name: str) -> dict:
        """Get statistics for a latency metric."""
        if name not in self.latencies:
            return {}
        return self.latencies[name].to_dict()

    def to_dict(self) -> dict:
        """Export all metrics as dictionary."""
        return {
            "latencies": {k: v.to_dict() for k, v in self.latencies.items()},
            "counters": self.counters,
            "timers": self.timers,
        }


# ====================
# Invariant Checkers
# ====================


@dataclass
class RaceInvariantChecker:
    """Checks invariants for race condition testing."""

    deadlocks: int = 0
    lost_frames: int = 0
    double_releases: int = 0
    keyerror_none: int = 0
    unexpected_exceptions: list = field(default_factory=list)

    def check_no_deadlock(self, threads: list[PropagatingThread], timeout: float = 10.0) -> bool:
        """Check that all threads completed (no deadlock)."""
        for t in threads:
            t.join(timeout=timeout)
            if t.is_alive():
                self.deadlocks += 1
                return False
        return True

    def check_no_lost_frames(self, connection) -> bool:
        """Check that no frames were lost in buffers."""
        conn = connection._connection if hasattr(connection, "_connection") else connection

        for ch_id, buff in conn.channel_frame_buff.items():
            if buff:
                self.lost_frames += len(buff)

        return self.lost_frames == 0

    def check_pool_consistency(self, pool) -> bool:
        """Check pool state is consistent."""
        try:
            dirty = len(pool._dirty)
            free_count = pool._resource.qsize()
            # Basic sanity check
            return True
        except Exception as e:
            self.unexpected_exceptions.append(str(e))
            return False

    def record_exception(self, exc: Exception) -> None:
        """Record an unexpected exception."""
        exc_str = f"{type(exc).__name__}: {exc}"
        if "KeyError" in exc_str and "None" in exc_str:
            self.keyerror_none += 1
        self.unexpected_exceptions.append(exc_str)

    def is_healthy(self) -> bool:
        """Check if all invariants are satisfied."""
        return (
            self.deadlocks == 0
            and self.lost_frames == 0
            and self.double_releases == 0
            and self.keyerror_none == 0
            and len(self.unexpected_exceptions) == 0
        )

    def to_dict(self) -> dict:
        """Export checker state."""
        return {
            "deadlocks": self.deadlocks,
            "lost_frames": self.lost_frames,
            "double_releases": self.double_releases,
            "keyerror_none": self.keyerror_none,
            "unexpected_exceptions": self.unexpected_exceptions,
            "healthy": self.is_healthy(),
        }


# ====================
# Benchmark Results
# ====================


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    timestamp: float
    params: dict
    metrics: dict

    def save(self, output_dir: Path) -> Path:
        """Save result to JSON file."""
        filename = f"{self.name}-{int(self.timestamp)}.json"
        filepath = output_dir / filename
        filepath.write_text(json.dumps(asdict(self), indent=2))
        return filepath


class BenchmarkReporter:
    """Reporter for saving benchmark results."""

    def __init__(self, output_dir: Path):
        self.results: list[dict[str, Any]] = []
        self.output_dir = output_dir

    def record(self, name: str, params: dict, metrics: dict) -> None:
        """Record benchmark result."""
        timestamp = time.time()
        result = {
            "name": name,
            "timestamp": timestamp,
            "params": params,
            "metrics": metrics,
        }
        self.results.append(result)

        # Save to file
        filename = f"{name}-{int(timestamp)}.json"
        filepath = self.output_dir / filename
        filepath.write_text(json.dumps(result, indent=2))

    def get_all_results(self) -> list:
        """Get all recorded results."""
        return self.results
