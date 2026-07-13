#!/usr/bin/env python3
"""Generate benchmark visualization charts.

Usage:
    python scripts/generate_charts.py                    # Generate all charts
    python scripts/generate_charts.py --input report.json  # From specific report
    python scripts/generate_charts.py --output docs/assets/images  # Custom output dir

Requires:
    pip install matplotlib seaborn
"""

import argparse
import json
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import ticker
except ImportError:
    print("Error: matplotlib required. Install with: pip install matplotlib")
    exit(1)

# ====================
# Paths
# ====================

ROOT_DIR = Path(__file__).parent.parent
REPORTS_DIR = ROOT_DIR / "reports" / "benchmarks"
OUTPUT_DIR = ROOT_DIR / "docs" / "docs" / "assets" / "images"

# ====================
# Chart Configuration
# ====================

COLORS = {
    "primary": "#7c3aed",
    "secondary": "#f59e0b",
    "success": "#22c55e",
    "danger": "#ef4444",
    "info": "#3b82f6",
    "muted": "#6b7280",
}

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["font.size"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 12


# ====================
# Data Extraction
# ====================


def load_latest_report() -> dict:
    """Load the most recent benchmark report."""
    history_file = REPORTS_DIR / "benchmark_history.json"
    if not history_file.exists():
        raise FileNotFoundError("No benchmark history found. Run benchmarks first.")

    history = json.loads(history_file.read_text())
    if not history:
        raise ValueError("Benchmark history is empty.")

    latest = history[-1]
    report_file = REPORTS_DIR / latest["file"]
    return json.loads(report_file.read_text())


def extract_throughput_data(results: list[dict]) -> dict:
    """Extract throughput benchmark data."""
    data: dict[str, list] = {"threads": [], "throughput": [], "latency_p50": [], "latency_p99": []}

    for r in results:
        if r["name"] == "publish_throughput":
            data["threads"].append(r["params"]["n_threads"])
            data["throughput"].append(r["metrics"]["messages_per_second"])
            data["latency_p50"].append(r["metrics"]["latency_p50_ms"])
            data["latency_p99"].append(r["metrics"]["latency_p99_ms"])

    # Sort by thread count
    if data["threads"]:
        sorted_indices = np.argsort(data["threads"])
        for key in data:
            data[key] = [data[key][i] for i in sorted_indices]

    return data


def extract_stress_throughput_data(results: list[dict]) -> dict:
    """Extract stress throughput benchmark data."""
    data: dict[str, list] = {"threads": [], "throughput": [], "latency_p50": [], "latency_p99": []}

    for r in results:
        if r["name"] == "publish_throughput_stress":
            data["threads"].append(r["params"]["n_threads"])
            data["throughput"].append(r["metrics"]["messages_per_second"])
            data["latency_p50"].append(r["metrics"]["latency_p50_ms"])
            data["latency_p99"].append(r["metrics"]["latency_p99_ms"])

    if data["threads"]:
        sorted_indices = np.argsort(data["threads"])
        for key in data:
            data[key] = [data[key][i] for i in sorted_indices]

    return data


def extract_scalability_data(results: list[dict]) -> dict:
    """Extract scalability benchmark data."""
    data: dict[str, list] = {
        "consumers": [],
        "throughput": [],
        "latency_p50": [],
        "latency_p99": [],
        "startup": [],
    }

    for r in results:
        if r["name"] == "massive_consumers_stress":
            data["consumers"].append(r["params"]["n_consumers"])
            data["throughput"].append(r["metrics"]["consume_throughput"])
            data["latency_p50"].append(r["metrics"]["latency_p50_ms"])
            data["latency_p99"].append(r["metrics"]["latency_p99_ms"])
            data["startup"].append(r["metrics"].get("consumer_startup_sec", 0))

    if data["consumers"]:
        sorted_indices = np.argsort(data["consumers"])
        for key in data:
            data[key] = [data[key][i] for i in sorted_indices]

    return data


def extract_recovery_data(results: list[dict]) -> dict:
    """Extract recovery benchmark data."""
    data: dict[str, dict[str, list]] = {
        "tcp_rst": {"detection": [], "propagation": [], "recovery": [], "threads": []},
        "network_partition": {
            "detection": [],
            "propagation": [],
            "recovery": [],
            "threads": [],
        },
    }

    for r in results:
        if r["name"] == "recovery_reset_peer":
            data["tcp_rst"]["threads"].append(r["params"]["n_threads"])
            data["tcp_rst"]["detection"].append(r["metrics"].get("error_detection_latency_ms", 0))
            data["tcp_rst"]["propagation"].append(
                r["metrics"].get("error_propagation_latency_ms", 0)
            )
            data["tcp_rst"]["recovery"].append(r["metrics"].get("full_recovery_latency_ms", 0))
        elif r["name"] == "recovery_network_partition":
            data["network_partition"]["threads"].append(r["params"]["n_threads"])
            data["network_partition"]["detection"].append(
                r["metrics"].get("error_detection_latency_ms", 0)
            )
            data["network_partition"]["propagation"].append(
                r["metrics"].get("error_propagation_latency_ms", 0)
            )
            data["network_partition"]["recovery"].append(
                r["metrics"].get("full_recovery_latency_ms", 0)
            )

    return data


def extract_network_resilience_data(results: list[dict]) -> dict:
    """Extract network resilience summary data."""
    for r in results:
        if r["name"] == "network_resilience_summary":
            return {
                "tcp_rst": r["metrics"].get("tcp_rst_recovery_ms", 0),
                "network_partition": r["metrics"].get("network_partition_recovery_ms", 0),
                "slow_network": r["metrics"].get("slow_network_recovery_ms", 0),
            }
    return {}


# ====================
# Chart Generation
# ====================


def generate_throughput_chart(data: dict, stress_data: dict, output_dir: Path) -> None:
    """Generate throughput by thread count chart."""
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Combine data
    all_threads = data["threads"] + stress_data["threads"]
    all_throughput = data["throughput"] + stress_data["throughput"]

    # Sort by threads
    sorted_pairs = sorted(zip(all_threads, all_throughput))
    threads = [p[0] for p in sorted_pairs]
    throughput = [p[1] for p in sorted_pairs]

    # Bar chart for throughput
    bars = ax1.bar(
        range(len(threads)),
        throughput,
        color=COLORS["primary"],
        alpha=0.8,
        label="Throughput",
    )
    ax1.set_xlabel("Thread Count")
    ax1.set_ylabel("Messages/sec", color=COLORS["primary"])
    ax1.tick_params(axis="y", labelcolor=COLORS["primary"])
    ax1.set_xticks(range(len(threads)))
    ax1.set_xticklabels(threads)

    # Add value labels on bars
    for bar, val in zip(bars, throughput):
        height = bar.get_height()
        ax1.annotate(
            f"{val:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    # Format y-axis
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{x:,.0f}"))

    ax1.set_title("Publish Throughput by Thread Count")
    ax1.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "throughput_by_threads.png", dpi=150)
    plt.savefig(output_dir / "throughput_by_threads.svg")
    plt.close()

    print(f"Generated: {output_dir / 'throughput_by_threads.png'}")


def generate_latency_chart(data: dict, stress_data: dict, output_dir: Path) -> None:
    """Generate latency percentiles chart."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Combine data
    all_threads = data["threads"] + stress_data["threads"]
    all_p50 = data["latency_p50"] + stress_data["latency_p50"]
    all_p99 = data["latency_p99"] + stress_data["latency_p99"]

    # Sort by threads
    sorted_data = sorted(zip(all_threads, all_p50, all_p99))
    threads = [str(p[0]) for p in sorted_data]
    p50 = [p[1] for p in sorted_data]
    p99 = [p[2] for p in sorted_data]

    x = np.arange(len(threads))
    width = 0.35

    bars1 = ax.bar(x - width / 2, p50, width, label="P50", color=COLORS["primary"])
    bars2 = ax.bar(x + width / 2, p99, width, label="P99", color=COLORS["secondary"])

    ax.set_xlabel("Thread Count")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Latency Percentiles by Thread Count")
    ax.set_xticks(x)
    ax.set_xticklabels(threads)
    ax.legend()

    # Log scale for better visibility
    ax.set_yscale("log")

    plt.tight_layout()
    plt.savefig(output_dir / "latency_percentiles.png", dpi=150)
    plt.savefig(output_dir / "latency_percentiles.svg")
    plt.close()

    print(f"Generated: {output_dir / 'latency_percentiles.png'}")


def generate_scalability_chart(data: dict, output_dir: Path) -> None:
    """Generate consumer scalability chart."""
    if not data["consumers"]:
        print("Skipping scalability chart: no data")
        return

    fig, ax1 = plt.subplots(figsize=(10, 6))

    consumers = data["consumers"]
    throughput = data["throughput"]
    latency = data["latency_p50"]

    # Throughput bars
    bars = ax1.bar(
        range(len(consumers)),
        throughput,
        color=COLORS["primary"],
        alpha=0.7,
        label="Throughput",
    )
    ax1.set_xlabel("Consumer Count")
    ax1.set_ylabel("Throughput (msg/s)", color=COLORS["primary"])
    ax1.tick_params(axis="y", labelcolor=COLORS["primary"])
    ax1.set_xticks(range(len(consumers)))
    ax1.set_xticklabels(consumers)

    # Latency line on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(
        range(len(consumers)),
        latency,
        color=COLORS["secondary"],
        marker="o",
        linewidth=2,
        markersize=8,
        label="Latency P50",
    )
    ax2.set_ylabel("Latency P50 (ms)", color=COLORS["secondary"])
    ax2.tick_params(axis="y", labelcolor=COLORS["secondary"])

    # Add value labels
    for bar, val in zip(bars, throughput):
        ax1.annotate(
            f"{val:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax1.set_title("Consumer Scalability: Throughput vs Latency")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "consumer_scalability.png", dpi=150)
    plt.savefig(output_dir / "consumer_scalability.svg")
    plt.close()

    print(f"Generated: {output_dir / 'consumer_scalability.png'}")


def generate_recovery_chart(data: dict, output_dir: Path) -> None:
    """Generate recovery time comparison chart."""
    resilience = data

    if not resilience:
        print("Skipping recovery chart: no data")
        return

    fig, ax = plt.subplots(figsize=(10, 5))

    scenarios = ["TCP RST", "Network Partition", "Slow Network"]
    times = [
        resilience.get("tcp_rst", 0),
        resilience.get("network_partition", 0),
        resilience.get("slow_network", 0),
    ]

    colors = [COLORS["success"], COLORS["info"], COLORS["secondary"]]
    bars = ax.barh(scenarios, times, color=colors, height=0.6)

    # Add value labels
    for bar, val in zip(bars, times):
        ax.annotate(
            f"{val:.2f} ms",
            xy=(val, bar.get_y() + bar.get_height() / 2),
            xytext=(5, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_xlabel("Recovery Time (ms)")
    ax.set_title("Network Resilience: Recovery Times")
    ax.set_xlim(0, max(times) * 1.3)

    plt.tight_layout()
    plt.savefig(output_dir / "recovery_times.png", dpi=150)
    plt.savefig(output_dir / "recovery_times.svg")
    plt.close()

    print(f"Generated: {output_dir / 'recovery_times.png'}")


def generate_summary_dashboard(report: dict, output_dir: Path) -> None:
    """Generate summary dashboard with key metrics."""
    results = report["results"]

    # Extract key metrics
    metrics = {
        "Tests Passed": report.get("tests_passed", 0),
        "Tests Failed": report.get("tests_failed", 0),
        "Duration (s)": int(report.get("duration_sec", 0)),
    }

    # Find peak throughput
    max_throughput = 0
    for r in results:
        if "throughput" in r["name"].lower():
            throughput = r["metrics"].get("messages_per_second", r["metrics"].get("throughput", 0))
            max_throughput = max(max_throughput, throughput)
    metrics["Peak Throughput"] = int(max_throughput)

    # Find deadlocks
    total_deadlocks = 0
    for r in results:
        if "chaos" in r["name"].lower() or "stress" in r["name"].lower():
            total_deadlocks += r["metrics"].get("deadlocks", 0)
    metrics["Deadlocks"] = total_deadlocks

    fig, axes = plt.subplots(1, len(metrics), figsize=(15, 3))

    for ax, (label, value) in zip(axes, metrics.items()):
        ax.text(
            0.5,
            0.6,
            f"{value:,}" if isinstance(value, int) else f"{value}",
            ha="center",
            va="center",
            fontsize=28,
            fontweight="bold",
            color=COLORS["primary"] if value != 0 or "Failed" not in label else COLORS["danger"],
        )
        ax.text(
            0.5,
            0.2,
            label,
            ha="center",
            va="center",
            fontsize=12,
            color=COLORS["muted"],
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(output_dir / "summary_dashboard.png", dpi=150)
    plt.savefig(output_dir / "summary_dashboard.svg")
    plt.close()

    print(f"Generated: {output_dir / 'summary_dashboard.png'}")


# ====================
# Main
# ====================


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark charts")
    parser.add_argument("--input", type=Path, help="Input JSON report file")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Load report
    if args.input:
        report = json.loads(args.input.read_text())
    else:
        report = load_latest_report()

    results = report["results"]

    print(f"Generating charts from {len(results)} benchmark results...")
    print(f"Output directory: {args.output}")
    print()

    # Generate all charts
    throughput_data = extract_throughput_data(results)
    stress_data = extract_stress_throughput_data(results)
    scalability_data = extract_scalability_data(results)
    recovery_data = extract_network_resilience_data(results)

    generate_throughput_chart(throughput_data, stress_data, args.output)
    generate_latency_chart(throughput_data, stress_data, args.output)
    generate_scalability_chart(scalability_data, args.output)
    generate_recovery_chart(recovery_data, args.output)
    generate_summary_dashboard(report, args.output)

    print()
    print("All charts generated successfully!")


if __name__ == "__main__":
    main()
