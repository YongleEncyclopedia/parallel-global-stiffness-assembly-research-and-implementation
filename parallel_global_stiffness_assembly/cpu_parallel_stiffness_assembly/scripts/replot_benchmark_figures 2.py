#!/usr/bin/env python3
"""Replot all reproducible benchmark figures with the presentation style."""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


CPU_FIGURE_STEMS = [
    "cube_tet4_8x8x8_simplified_assembly_ms",
    "cube_tet4_8x8x8_simplified_total_ms",
    "cube_tet4_8x8x8_simplified_speedup",
    "cube_tet4_8x8x8_simplified_efficiency",
    "cube_tet4_8x8x8_simplified_stage_breakdown",
    "cube_tet4_8x8x8_simplified_extra_memory",
    "cube_tet4_8x8x8_simplified_dashboard",
    "3d-WindTurbineHub_simplified_assembly_ms",
    "3d-WindTurbineHub_simplified_total_ms",
    "3d-WindTurbineHub_simplified_speedup",
    "3d-WindTurbineHub_simplified_efficiency",
    "3d-WindTurbineHub_simplified_stage_breakdown",
    "3d-WindTurbineHub_simplified_extra_memory",
    "3d-WindTurbineHub_simplified_dashboard",
    "3d-WindTurbineHub_physics_tet4_assembly_ms",
    "3d-WindTurbineHub_physics_tet4_total_ms",
    "3d-WindTurbineHub_physics_tet4_speedup",
    "3d-WindTurbineHub_physics_tet4_efficiency",
    "3d-WindTurbineHub_physics_tet4_stage_breakdown",
    "3d-WindTurbineHub_physics_tet4_extra_memory",
    "3d-WindTurbineHub_physics_tet4_dashboard",
    "cross_case_best_speedup",
    "cross_kernel_best_speedup",
]

THREAD_FIGURE_STEMS = [
    "thread_scaling_default_dashboard",
    "thread_scaling_bound_dashboard",
    "thread_scaling_by_algorithm_cpu_atomic",
    "thread_scaling_by_algorithm_cpu_private_csr",
    "thread_scaling_by_algorithm_cpu_row_owner",
    "thread_scaling_by_algorithm_cpu_graph_coloring",
    "thread_scaling_memory_by_env",
    "thread_scaling_physical_vs_oversubscription",
    "thread_scaling_stage_breakdown_best",
]

THREAD_ROOTS = [
    "2026-05-11-thread-scaling",
    "2026-05-11-thread-scaling-linux-intel",
    "2026-05-12-thread-scaling-linux-intel-pcore",
    "2026-05-12-thread-scaling-linux-intel-ecore",
    "2026-05-14-thread-scaling-macos-m4max-performance-qos",
    "2026-05-14-thread-scaling-macos-m4max-efficiency-qos",
]

CROSS_PLATFORM_STEMS = [
    "core_profile_speedup_comparison_apple_m4_max",
    "core_profile_speedup_comparison_intel_u7_265kf",
]


@dataclass(frozen=True)
class FigureTarget:
    kind: str
    root: Path


def benchmark_targets(project_root: Path) -> list[FigureTarget]:
    results = project_root / "results"
    return [
        FigureTarget("cpu", results / "2026-04-22"),
        *[FigureTarget("thread_scaling", results / name) for name in THREAD_ROOTS],
        FigureTarget("cross_platform", results / "cross-platform-v1"),
    ]


def _with_png_svg(out_dir: Path, stems: list[str]) -> list[Path]:
    files: list[Path] = []
    for stem in stems:
        files.append(out_dir / f"{stem}.png")
        files.append(out_dir / f"{stem}.svg")
    return files


def planned_output_files(project_root: Path) -> list[Path]:
    results = project_root / "results"
    outputs = _with_png_svg(results / "2026-04-22" / "figures", CPU_FIGURE_STEMS)
    for name in THREAD_ROOTS:
        out_dir = results / name / "figures"
        outputs.extend(_with_png_svg(out_dir, THREAD_FIGURE_STEMS))
        outputs.append(out_dir / "thread_scaling_contact_sheet.png")
    outputs.extend(_with_png_svg(results / "cross-platform-v1" / "figures", CROSS_PLATFORM_STEMS))
    return outputs


def validate_inputs(project_root: Path) -> None:
    required = [
        project_root / "results" / "2026-04-22" / "csv" / "cube_tet4_simplified.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_simplified.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_physics_tet4.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_physics_tet4_coo_sort_reduce.csv",
    ]
    for name in THREAD_ROOTS:
        root = project_root / "results" / name
        required.append(root / "default" / "thread_scaling_default.csv")
        required.append(root / "bound" / "thread_scaling_bound.csv")
        required.append(root / "thread_scaling_combined.csv")
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing benchmark inputs:\n" + "\n".join(str(path) for path in missing))


def validate_outputs(project_root: Path) -> None:
    missing = [path for path in planned_output_files(project_root) if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing or empty benchmark figures:\n" + "\n".join(str(path) for path in missing))
    unexpected = [path for path in planned_output_files(project_root) if "presentation_charts" in path.as_posix()]
    if unexpected:
        raise RuntimeError("Presentation chart snapshots must not be in the replot manifest")


def run_command(args: list[str], cwd: Path) -> None:
    print("[RUN] " + " ".join(args))
    subprocess.run(args, cwd=cwd, check=True)


def replot(project_root: Path) -> None:
    validate_inputs(project_root)
    scripts = project_root / "scripts"
    cpu_csvs = [
        project_root / "results" / "2026-04-22" / "csv" / "cube_tet4_simplified.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_simplified.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_physics_tet4.csv",
        project_root / "results" / "2026-04-22" / "csv" / "windhub_physics_tet4_coo_sort_reduce.csv",
    ]
    run_command(
        [
            sys.executable,
            str(scripts / "plot_cpu_results.py"),
            *[str(path) for path in cpu_csvs],
            "--out-dir",
            str(project_root / "results" / "2026-04-22" / "figures"),
        ],
        project_root,
    )
    for name in THREAD_ROOTS:
        run_command(
            [sys.executable, str(scripts / "plot_thread_scaling_results.py"), "--results-root", str(project_root / "results" / name)],
            project_root,
        )
    run_command([sys.executable, str(scripts / "plot_core_profile_comparison.py"), "--project-root", str(project_root)], project_root)
    validate_outputs(project_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    replot(args.project_root.resolve())
    print(f"[OK] replotted {len(planned_output_files(args.project_root.resolve()))} benchmark figure files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
