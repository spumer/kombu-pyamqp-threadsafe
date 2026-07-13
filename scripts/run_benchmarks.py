#!/usr/bin/env python3
"""Benchmark Runner with Reproducible Report Generation.

Usage:
    python scripts/run_benchmarks.py              # Run all benchmarks
    python scripts/run_benchmarks.py --quick      # Run quick subset
    python scripts/run_benchmarks.py --compare    # Compare with previous run
    python scripts/run_benchmarks.py --report     # Generate report only (no tests)

Features:
- Captures full environment for reproducibility
- Stores results in timestamped JSON
- Generates Markdown report with comparison
- Tracks performance regressions
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# ====================
# Paths
# ====================

ROOT_DIR = Path(__file__).parent.parent
BENCHMARK_DIR = ROOT_DIR / "tests" / "benchmarks"
OUTPUT_DIR = ROOT_DIR / "reports" / ".test-output"
REPORTS_DIR = ROOT_DIR / "reports" / "benchmarks"
HISTORY_FILE = REPORTS_DIR / "benchmark_history.json"


# ====================
# Environment Capture
# ====================


@dataclass
class Environment:
    """Captured environment for reproducibility."""

    timestamp: str
    python_version: str
    platform: str
    platform_version: str
    machine: str
    processor: str
    cpu_count: int
    git_commit: str
    git_branch: str
    git_dirty: bool
    library_version: str

    @classmethod
    def capture(cls) -> "Environment":
        """Capture current environment."""
        git_commit = cls._run_cmd("git rev-parse --short HEAD")
        git_branch = cls._run_cmd("git branch --show-current")
        git_status = cls._run_cmd("git status --porcelain")

        try:
            import kombu_pyamqp_threadsafe

            lib_version = getattr(kombu_pyamqp_threadsafe, "__version__", "unknown")
        except ImportError:
            lib_version = "not installed"

        return cls(
            timestamp=datetime.now().isoformat(),
            python_version=platform.python_version(),
            platform=platform.system(),
            platform_version=platform.release(),
            machine=platform.machine(),
            processor=platform.processor() or "unknown",
            cpu_count=os.cpu_count() or 1,
            git_commit=git_commit,
            git_branch=git_branch,
            git_dirty=bool(git_status.strip()),
            library_version=lib_version,
        )

    @staticmethod
    def _run_cmd(cmd: str) -> str:
        try:
            result = subprocess.run(
                cmd.split(),
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT_DIR,
                timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def fingerprint(self) -> str:
        """Generate unique fingerprint for this environment."""
        key = f"{self.git_commit}:{self.git_dirty}:{self.python_version}:{self.platform}"
        return hashlib.md5(key.encode()).hexdigest()[:8]


# ====================
# Benchmark Results
# ====================


@dataclass
class BenchmarkResult:
    """Single benchmark result."""

    name: str
    params: dict
    metrics: dict
    timestamp: float


@dataclass
class BenchmarkRun:
    """Complete benchmark run with all results."""

    environment: Environment
    results: list[BenchmarkResult] = field(default_factory=list)
    duration_sec: float = 0.0
    tests_passed: int = 0
    tests_failed: int = 0

    def to_dict(self) -> dict:
        return {
            "environment": asdict(self.environment),
            "results": [asdict(r) for r in self.results],
            "duration_sec": self.duration_sec,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkRun":
        env = Environment(**data["environment"])
        results = [BenchmarkResult(**r) for r in data["results"]]
        return cls(
            environment=env,
            results=results,
            duration_sec=data.get("duration_sec", 0),
            tests_passed=data.get("tests_passed", 0),
            tests_failed=data.get("tests_failed", 0),
        )


# ====================
# Runner
# ====================


def run_benchmarks(quick: bool = False) -> tuple[int, int, float]:
    """Run pytest benchmarks and return (passed, failed, duration)."""
    args = [
        sys.executable,
        "-m",
        "pytest",
        str(BENCHMARK_DIR),
        "-v",
        "--tb=short",
        f"--junit-xml={REPORTS_DIR / 'junit.xml'}",
    ]

    if quick:
        # Run only quick tests
        args.extend(["-m", "not slow and not stress"])

    print(f"\n{'=' * 70}")
    print("RUNNING BENCHMARKS")
    print(f"{'=' * 70}")
    print(f"Command: {' '.join(args)}")
    print()

    start = time.monotonic()
    result = subprocess.run(args, check=False, cwd=ROOT_DIR)
    duration = time.monotonic() - start

    # Parse results from pytest output
    passed = 0
    failed = 0

    # Try to parse junit xml for accurate counts
    junit_file = REPORTS_DIR / "junit.xml"
    if junit_file.exists():
        import xml.etree.ElementTree as ET

        tree = ET.parse(junit_file)
        root = tree.getroot()
        for testsuite in root.findall(".//testsuite"):
            passed += (
                int(testsuite.get("tests", 0))
                - int(testsuite.get("failures", 0))
                - int(testsuite.get("errors", 0))
            )
            failed += int(testsuite.get("failures", 0)) + int(testsuite.get("errors", 0))

    return passed, failed, duration


def clean_output_dir() -> None:
    """Clean up old benchmark results."""
    if OUTPUT_DIR.exists():
        for json_file in OUTPUT_DIR.glob("*.json"):
            json_file.unlink()
        print(f"Cleaned {OUTPUT_DIR}")


def collect_results() -> list[BenchmarkResult]:
    """Collect benchmark results from JSON files in output directory.

    Aggregates duplicates by taking the latest result for each unique (name, params) pair.
    """
    results_map: dict[str, BenchmarkResult] = {}

    if not OUTPUT_DIR.exists():
        return []

    for json_file in OUTPUT_DIR.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            result = BenchmarkResult(
                name=data.get("name", json_file.stem),
                params=data.get("params", {}),
                metrics=data.get("metrics", {}),
                timestamp=data.get("timestamp", 0),
            )
            # Create unique key from name and params
            params_str = json.dumps(result.params, sort_keys=True)
            key = f"{result.name}:{params_str}"

            # Keep only the latest result for each unique test
            if key not in results_map or result.timestamp > results_map[key].timestamp:
                results_map[key] = result

        except Exception as e:
            print(f"Warning: Failed to parse {json_file}: {e}")

    return list(results_map.values())


def save_run(run: BenchmarkRun) -> Path:
    """Save benchmark run to timestamped file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fingerprint = run.environment.fingerprint()
    filename = f"run_{timestamp}_{fingerprint}.json"
    filepath = REPORTS_DIR / filename

    filepath.write_text(json.dumps(run.to_dict(), indent=2))

    # Update history
    update_history(run, filepath)

    return filepath


def update_history(run: BenchmarkRun, filepath: Path) -> None:
    """Update benchmark history for comparison."""
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass

    history.append(
        {
            "file": filepath.name,
            "timestamp": run.environment.timestamp,
            "commit": run.environment.git_commit,
            "dirty": run.environment.git_dirty,
            "tests_passed": run.tests_passed,
            "duration_sec": run.duration_sec,
        }
    )

    # Keep last 50 runs
    history = history[-50:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def load_previous_run() -> BenchmarkRun | None:
    """Load most recent benchmark run for comparison."""
    if not HISTORY_FILE.exists():
        return None

    try:
        history = json.loads(HISTORY_FILE.read_text())
        if not history:
            return None

        latest = history[-1]
        filepath = REPORTS_DIR / latest["file"]
        if not filepath.exists():
            return None

        data = json.loads(filepath.read_text())
        return BenchmarkRun.from_dict(data)
    except Exception:
        return None


# ====================
# Report Generation
# ====================


def generate_report(run: BenchmarkRun, previous: BenchmarkRun | None = None) -> str:
    """Generate Markdown report from benchmark run."""
    lines = [
        "# Benchmark Report",
        "",
        f"**Generated:** {run.environment.timestamp}",
        "",
        "## Environment",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| Python | {run.environment.python_version} |",
        f"| Platform | {run.environment.platform} {run.environment.platform_version} |",
        f"| Machine | {run.environment.machine} |",
        f"| CPU Count | {run.environment.cpu_count} |",
        f"| Git Commit | `{run.environment.git_commit}` {'(dirty)' if run.environment.git_dirty else ''} |",
        f"| Git Branch | `{run.environment.git_branch}` |",
        f"| Library Version | {run.environment.library_version} |",
        "",
        "## Summary",
        "",
        f"- **Tests Passed:** {run.tests_passed}",
        f"- **Tests Failed:** {run.tests_failed}",
        f"- **Duration:** {run.duration_sec:.1f}s",
        "",
    ]

    if previous:
        lines.extend(
            [
                "### Comparison with Previous Run",
                "",
                f"- Previous commit: `{previous.environment.git_commit}`",
                f"- Previous passed: {previous.tests_passed}",
                f"- Time delta: {run.duration_sec - previous.duration_sec:+.1f}s",
                "",
            ]
        )

    # Group results by category
    categories: dict[str, list[BenchmarkResult]] = {}
    for result in run.results:
        category = result.name.split("_")[0] if "_" in result.name else "other"
        if category not in categories:
            categories[category] = []
        categories[category].append(result)

    lines.append("## Results by Category")
    lines.append("")

    for category, results in sorted(categories.items()):
        lines.append(f"### {category.title()}")
        lines.append("")

        for result in results:
            lines.append(f"#### {result.name}")
            if result.params:
                params_str = ", ".join(f"{k}={v}" for k, v in result.params.items())
                lines.append(f"**Params:** {params_str}")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")

            for key, value in result.metrics.items():
                if isinstance(value, float):
                    if "pct" in key.lower() or "percent" in key.lower():
                        formatted = f"{value:.1f}%"
                    elif "ms" in key.lower() or "latency" in key.lower():
                        formatted = f"{value:.2f} ms"
                    elif "throughput" in key.lower():
                        formatted = f"{value:,.1f}"
                    else:
                        formatted = f"{value:.2f}"
                else:
                    formatted = str(value)

                # Compare with previous if available
                if previous:
                    prev_result = next(
                        (
                            r
                            for r in previous.results
                            if r.name == result.name and r.params == result.params
                        ),
                        None,
                    )
                    if prev_result and key in prev_result.metrics:
                        prev_value = prev_result.metrics[key]
                        if isinstance(value, (int, float)) and isinstance(prev_value, (int, float)):
                            if prev_value != 0:
                                delta = ((value - prev_value) / prev_value) * 100
                                if abs(delta) > 5:  # Only show significant changes
                                    sign = "↑" if delta > 0 else "↓"
                                    formatted += f" ({sign} {abs(delta):.0f}%)"

                lines.append(f"| {key} | {formatted} |")

            lines.append("")

    # Key metrics summary
    lines.extend(
        [
            "## Key Metrics Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]
    )

    # Extract key metrics from results
    throughput_results = [r for r in run.results if "throughput" in r.name.lower()]
    if throughput_results:
        max_throughput = max(
            r.metrics.get("throughput", r.metrics.get("produce_throughput", 0))
            for r in throughput_results
        )
        lines.append(f"| Peak Throughput | {max_throughput:,.0f} msg/s |")

    recovery_results = [r for r in run.results if "recovery" in r.name.lower()]
    if recovery_results:
        for r in recovery_results:
            if "error_detection_latency_ms" in r.metrics:
                lines.append(
                    f"| Error Detection (n={r.params.get('n_threads', '?')}) | {r.metrics['error_detection_latency_ms']:.1f} ms |"
                )
                break

    lines.append("")
    lines.append("---")
    lines.append(f"*Report fingerprint: `{run.environment.fingerprint()}`*")

    return "\n".join(lines)


# ====================
# Main
# ====================


def main():
    parser = argparse.ArgumentParser(description="Run benchmarks with reproducible reporting")
    parser.add_argument("--quick", action="store_true", help="Run quick subset only")
    parser.add_argument("--compare", action="store_true", help="Compare with previous run")
    parser.add_argument("--report", action="store_true", help="Generate report only (no tests)")
    parser.add_argument(
        "--no-clean", action="store_true", help="Don't clean old results before run"
    )
    parser.add_argument("--output", type=Path, help="Output file for report")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Capture environment
    env = Environment.capture()

    print(f"\n{'=' * 70}")
    print("BENCHMARK RUNNER")
    print(f"{'=' * 70}")
    print(f"Commit:  {env.git_commit} {'(dirty)' if env.git_dirty else ''}")
    print(f"Branch:  {env.git_branch}")
    print(f"Python:  {env.python_version}")
    print(f"Platform: {env.platform} {env.platform_version}")

    if args.report:
        # Report-only mode: use existing results
        results = collect_results()
        run = BenchmarkRun(environment=env, results=results)
    else:
        # Clean old results unless --no-clean
        if not args.no_clean:
            clean_output_dir()

        # Run benchmarks
        passed, failed, duration = run_benchmarks(quick=args.quick)
        results = collect_results()
        run = BenchmarkRun(
            environment=env,
            results=results,
            duration_sec=duration,
            tests_passed=passed,
            tests_failed=failed,
        )

        # Save run
        filepath = save_run(run)
        print(f"\nResults saved to: {filepath}")

    # Load previous for comparison
    previous = load_previous_run() if args.compare else None

    # Generate report
    report = generate_report(run, previous)

    # Output
    output_file = args.output or (REPORTS_DIR / "LATEST_REPORT.md")
    output_file.write_text(report)
    print(f"Report saved to: {output_file}")

    # Also print summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Tests Passed: {run.tests_passed}")
    print(f"Tests Failed: {run.tests_failed}")
    print(f"Duration:     {run.duration_sec:.1f}s")
    print(f"Results:      {len(run.results)} benchmarks")
    print(f"Fingerprint:  {env.fingerprint()}")

    return 0 if run.tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
