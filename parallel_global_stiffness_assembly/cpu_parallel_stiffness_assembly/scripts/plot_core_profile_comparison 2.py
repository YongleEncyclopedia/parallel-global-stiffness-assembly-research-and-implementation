#!/usr/bin/env python3
"""Plot full-host/P-core/E-core acceleration comparisons from existing CSVs."""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from benchmark_figure_style import (
    INK,
    MUTED,
    PROFILE_COLORS,
    add_baseline,
    annotate_point,
    apply_presentation_style,
    format_ms,
    format_ratio,
    save_figure as save_styled_figure,
    set_slide_title,
    style_axis,
)


ALGORITHM_ORDER = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

ALGO_LABELS = {
    "cpu_atomic": "Atomic",
    "cpu_private_csr": "Private CSR",
    "cpu_row_owner": "Row Owner",
    "cpu_graph_coloring": "Coloring",
}

PROFILE_ORDER = ["full_host", "performance_core_only", "efficiency_core_only"]


@dataclass(frozen=True)
class ProfileInput:
    profile_id: str
    label: str
    root: Path


@dataclass(frozen=True)
class BestRecord:
    algorithm: str
    threads: int
    assembly_ms: float
    speedup: float


@dataclass(frozen=True)
class ComparisonRow:
    profile_id: str
    profile_label: str
    algorithm: str
    threads: int
    assembly_ms: float
    speedup: float
    time_ratio: float


@dataclass(frozen=True)
class PlatformSpec:
    platform_id: str
    title: str
    subtitle: str
    output_stem: str
    profiles: tuple[ProfileInput, ProfileInput, ProfileInput]


def parse_float(row: dict[str, str], *keys: str) -> float:
    for key in keys:
        value = row.get(key, "")
        if value not in ("", None):
            return float(value)
    return 0.0


def parse_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value not in ("", None) else 0


def best_bound_records(root: Path | str) -> dict[str, BestRecord]:
    csv_path = Path(root) / "thread_scaling_combined.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    best: dict[str, BestRecord] = {}
    for row in rows:
        if row.get("env_group") != "bound" or row.get("status") != "PASS":
            continue
        algorithm = row.get("algorithm", "")
        if algorithm not in ALGORITHM_ORDER:
            continue
        assembly_ms = parse_float(row, "assembly_ms", "assembly_mean_ms")
        if assembly_ms <= 0.0:
            continue
        candidate = BestRecord(
            algorithm=algorithm,
            threads=parse_int(row, "threads"),
            assembly_ms=assembly_ms,
            speedup=parse_float(row, "speedup"),
        )
        current = best.get(algorithm)
        if current is None or candidate.assembly_ms < current.assembly_ms:
            best[algorithm] = candidate
    return best


def platform_rows(profiles: Iterable[ProfileInput]) -> list[ComparisonRow]:
    profiles = list(profiles)
    by_profile = {profile.profile_id: best_bound_records(profile.root) for profile in profiles}
    if "full_host" not in by_profile:
        raise ValueError("profiles must include full_host")

    rows: list[ComparisonRow] = []
    full = by_profile["full_host"]
    for algorithm in ALGORITHM_ORDER:
        full_record = full.get(algorithm)
        if full_record is None:
            continue
        for profile in profiles:
            record = by_profile[profile.profile_id].get(algorithm)
            if record is None:
                continue
            rows.append(
                ComparisonRow(
                    profile_id=profile.profile_id,
                    profile_label=profile.label,
                    algorithm=algorithm,
                    threads=record.threads,
                    assembly_ms=record.assembly_ms,
                    speedup=record.speedup,
                    time_ratio=record.assembly_ms / full_record.assembly_ms,
                )
            )
    return rows


def value_lookup(rows: list[ComparisonRow], attr: str) -> dict[tuple[str, str], float]:
    return {(row.profile_id, row.algorithm): float(getattr(row, attr)) for row in rows}


def thread_lookup(rows: list[ComparisonRow]) -> dict[tuple[str, str], int]:
    return {(row.profile_id, row.algorithm): row.threads for row in rows}


def annotate_bars(ax: Any, bars, values: list[float], suffix: str = "") -> None:
    for bar, value in zip(bars, values):
        if value <= 0.0:
            continue
        ax.annotate(
            f"{value:.2f}{suffix}",
            xy=(bar.get_x() + bar.get_width() / 2.0, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=0,
        )


def annotate_threads(ax: Any, bars, threads: list[int]) -> None:
    for bar, thread in zip(bars, threads):
        ax.annotate(
            f"{thread}T",
            xy=(bar.get_x() + bar.get_width() / 2.0, 0),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7,
            color="#334155",
        )


def plot_platform(spec: PlatformSpec, out_dir: Path) -> tuple[Path, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_presentation_style()

    rows = platform_rows(spec.profiles)
    speedups = value_lookup(rows, "speedup")
    ratios = value_lookup(rows, "time_ratio")
    threads = thread_lookup(rows)

    algorithms = [algorithm for algorithm in ALGORITHM_ORDER if ("full_host", algorithm) in speedups]
    y_centers = list(range(len(algorithms)))
    profile_offsets = {
        "full_host": 0.24,
        "performance_core_only": 0.0,
        "efficiency_core_only": -0.24,
    }

    fig, (ax_speedup, ax_ratio) = plt.subplots(1, 2, figsize=(15.2, 7.8), sharey=True)

    for profile in spec.profiles:
        color = PROFILE_COLORS[profile.profile_id]
        for center, algorithm in zip(y_centers, algorithms):
            ypos = center + profile_offsets[profile.profile_id]
            speedup = speedups.get((profile.profile_id, algorithm), 0.0)
            ratio = ratios.get((profile.profile_id, algorithm), 0.0)
            thread = threads.get((profile.profile_id, algorithm), 0)
            if speedup > 0:
                ax_speedup.hlines(ypos, 0, speedup, color=color, linewidth=3.2, alpha=0.85)
                ax_speedup.scatter(speedup, ypos, s=92, color=color, edgecolor="white", linewidth=1.2, zorder=3, label=profile.label if center == 0 else None)
                ax_speedup.text(speedup, ypos, f" {format_ratio(speedup)} @ {thread}T", va="center", fontsize=9.2, color=INK)
            if ratio > 0:
                ax_ratio.hlines(ypos, 1.0, ratio, color=color, linewidth=3.2, alpha=0.85)
                ax_ratio.scatter(ratio, ypos, s=92, color=color, edgecolor="white", linewidth=1.2, zorder=3)
                ax_ratio.text(ratio, ypos, f" {format_ratio(ratio)}", va="center", fontsize=9.2, color=INK)

    ax_speedup.set_xlabel("Best speedup vs serial baseline")
    style_axis(ax_speedup, grid_axis="x", title="Best bound-profile speedup")
    ax_speedup.set_yticks(y_centers)
    ax_speedup.set_yticklabels([ALGO_LABELS[algorithm] for algorithm in algorithms])
    ax_speedup.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=False)

    ax_ratio.axvline(1.0, color=MUTED, linestyle=(0, (5, 4)), linewidth=1.25, alpha=0.9)
    max_ratio = max(ratios.values()) if ratios else 1.0
    if max_ratio > 6.0:
        ax_ratio.set_xscale("log")
        ax_ratio.set_xlabel("Best assembly-time ratio vs full host (log scale)")
    else:
        ax_ratio.set_xlabel("Best assembly-time ratio vs full host")
    style_axis(ax_ratio, grid_axis="x", title="Normalized assembly time; lower is better")
    ax_ratio.set_yticks(y_centers)
    ax_ratio.set_yticklabels([ALGO_LABELS[algorithm] for algorithm in algorithms])
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    set_slide_title(fig, spec.title, spec.subtitle)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{spec.output_stem}.png"
    svg_path = out_dir / f"{spec.output_stem}.svg"
    save_styled_figure(fig, out_dir / spec.output_stem)
    plt.close(fig)
    return png_path, svg_path


def core_profile_figure_block(platform: str, png: str, svg: str) -> str:
    return (
        f"### {platform}\n\n"
        f"![{platform} core-profile acceleration comparison](figures/{png})\n\n"
        f"[{platform} SVG](figures/{svg})\n"
    )


def results_relative_figure_block(platform: str, png: str, svg: str) -> str:
    return (
        f"### {platform}\n\n"
        f"![{platform} core-profile acceleration comparison](cross-platform-v1/figures/{png})\n\n"
        f"[{platform} SVG](cross-platform-v1/figures/{svg})\n"
    )


def replace_block(text: str, marker: str, content: str) -> str:
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    block = f"{start}\n{content.rstrip()}\n{end}"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    return text.rstrip() + "\n\n" + block + "\n"


def update_cross_platform_report(report_path: Path) -> None:
    content = (
        "## Core-Profile Acceleration Figures\n\n"
        "The figures compare `full_host`, `performance_core_only`, and `efficiency_core_only` within each CPU platform using the `bound` environment and each algorithm's best assembly-time point.\n\n"
        + core_profile_figure_block(
            "Apple M4 Max",
            "core_profile_speedup_comparison_apple_m4_max.png",
            "core_profile_speedup_comparison_apple_m4_max.svg",
        )
        + "\n"
        + core_profile_figure_block(
            "Intel Core Ultra 7 265KF",
            "core_profile_speedup_comparison_intel_u7_265kf.png",
            "core_profile_speedup_comparison_intel_u7_265kf.svg",
        )
    )
    text = report_path.read_text(encoding="utf-8")
    report_path.write_text(replace_block(text, "core-profile-comparison-figures", content), encoding="utf-8")


def update_supplement(report_path: Path, platform: str, png: str, svg: str, note: str) -> None:
    content = (
        "## Core-Profile Acceleration Figure\n\n"
        f"{note}\n\n"
        + results_relative_figure_block(platform, png, svg)
    )
    text = report_path.read_text(encoding="utf-8")
    report_path.write_text(replace_block(text, "core-profile-comparison-figure", content), encoding="utf-8")


def write_summary(out_dir: Path) -> Path:
    summary = """# Core-Profile Acceleration Comparison Figures

These figures compare `full_host`, `performance_core_only`, and `efficiency_core_only` within each CPU platform using the `bound` environment and each algorithm's best assembly-time point.

| Figure | PNG | SVG | Notes |
| --- | --- | --- | --- |
| Apple M4 Max | [png](core_profile_speedup_comparison_apple_m4_max.png) | [svg](core_profile_speedup_comparison_apple_m4_max.svg) | macOS QoS-biased sensitivity profiles; not hard-pinned core affinity. |
| Intel Core Ultra 7 265KF | [png](core_profile_speedup_comparison_intel_u7_265kf.png) | [svg](core_profile_speedup_comparison_intel_u7_265kf.svg) | Linux `taskset` affinity-restricted P/E-core profiles. |
"""
    out_path = out_dir / "summary.md"
    out_path.write_text(summary, encoding="utf-8")
    return out_path


def platform_specs(root: Path) -> list[PlatformSpec]:
    results = root / "results"
    return [
        PlatformSpec(
            platform_id="apple-m4-max",
            title="Apple M4 Max Core-Profile Acceleration Comparison",
            subtitle="full host vs Performance QoS vs Efficiency QoS; QoS-biased, not hard-pinned core affinity",
            output_stem="core_profile_speedup_comparison_apple_m4_max",
            profiles=(
                ProfileInput("full_host", "Full host", results / "2026-05-11-thread-scaling"),
                ProfileInput("performance_core_only", "Performance QoS", results / "2026-05-14-thread-scaling-macos-m4max-performance-qos"),
                ProfileInput("efficiency_core_only", "Efficiency QoS", results / "2026-05-14-thread-scaling-macos-m4max-efficiency-qos"),
            ),
        ),
        PlatformSpec(
            platform_id="intel-u7-265kf",
            title="Intel Core Ultra 7 265KF Core-Profile Acceleration Comparison",
            subtitle="full host vs P-core-only vs E-core-only; Linux taskset affinity-restricted profiles",
            output_stem="core_profile_speedup_comparison_intel_u7_265kf",
            profiles=(
                ProfileInput("full_host", "Full host", results / "2026-05-11-thread-scaling-linux-intel"),
                ProfileInput("performance_core_only", "P-core taskset", results / "2026-05-12-thread-scaling-linux-intel-pcore"),
                ProfileInput("efficiency_core_only", "E-core taskset", results / "2026-05-12-thread-scaling-linux-intel-ecore"),
            ),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--out-dir", default="results/cross-platform-v1/figures")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    out_dir = root / args.out_dir
    for spec in platform_specs(root):
        png, svg = plot_platform(spec, out_dir)
        print(f"[OK] wrote {png}")
        print(f"[OK] wrote {svg}")
    summary = write_summary(out_dir)
    print(f"[OK] wrote {summary}")

    update_cross_platform_report(root / "results" / "cross-platform-v1" / "cross_platform_schema_report.md")
    update_supplement(
        root / "results" / "2026-05-12-thread-scaling-linux-intel-hybrid-core-supplement.md",
        "Intel Core Ultra 7 265KF",
        "core_profile_speedup_comparison_intel_u7_265kf.png",
        "core_profile_speedup_comparison_intel_u7_265kf.svg",
        "This figure visualizes the same `taskset` affinity-restricted P/E-core data summarized above.",
    )
    update_supplement(
        root / "results" / "2026-05-14-thread-scaling-macos-m4max-qos-supplement.md",
        "Apple M4 Max",
        "core_profile_speedup_comparison_apple_m4_max.png",
        "core_profile_speedup_comparison_apple_m4_max.svg",
        "This figure visualizes macOS QoS-biased sensitivity data. It is not evidence of hard-pinned core affinity.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
