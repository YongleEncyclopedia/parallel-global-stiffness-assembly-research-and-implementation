#!/usr/bin/env python3
"""Run the 2026-05-14 mentor action-item evaluation artifact pipeline."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

from cross_platform_schema import current_platform_metadata


def run(cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def exe(build_dir: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return build_dir / "bin" / f"{name}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--out-root", default=None)
    parser.add_argument("--assemblies-list", default="1")
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--matlab", default="/Applications/MATLAB_R2026a.app/bin/matlab")
    parser.add_argument("--skip-matlab", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = root / args.build_dir
    out_root = (
        root / "results" / f"{date.today().isoformat()}-mentor-action-items"
        if args.out_root is None
        else Path(args.out_root)
    )
    out_root.mkdir(parents=True, exist_ok=True)

    if not args.skip_build:
        run(
            [
                "cmake",
                "-S",
                ".",
                "-B",
                str(build_dir),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DPGSA_ENABLE_OPENMP=ON",
                "-DBUILD_TESTS=ON",
                "-DBUILD_BENCHMARKS=ON",
            ],
            root,
        )
        run(["cmake", "--build", str(build_dir), "--parallel"], root)

    metadata = current_platform_metadata()
    physical_cores = int(metadata.get("physical_cores") or os.cpu_count() or 1)
    platform_id = str(metadata.get("cpu_model", "local")).lower().replace(" ", "-").replace("(", "").replace(")", "")
    inp = (root / "../../examples/3d-WindTurbineHub.inp").resolve()
    threads_range = f"1:{physical_cores}"

    benchmark_csv = out_root / "windhub_lock_vs_atomic.csv"
    benchmark_json = out_root / "windhub_lock_vs_atomic.json"
    benchmark_md = out_root / "windhub_lock_vs_atomic.md"
    run(
        [
            str(exe(build_dir, "benchmark_assembly")),
            "--mesh",
            "inp",
            "--inp",
            str(inp),
            "--case-name",
            "3d-WindTurbineHub",
            "--kernel",
            "physics_tet4",
            "--algo",
            "atomic,private_csr,lock_guard",
            "--threads-range",
            threads_range,
            "--repeat",
            str(args.repeat),
            "--check",
            "--schema-version",
            "pgsa-cross-platform-v2-raw",
            "--platform-id",
            platform_id,
            "--run-profile",
            "full_host",
            "--env-group",
            "mentor_action_items",
            "--max-memory-gb",
            str(args.max_memory_gb),
            "--csv",
            str(benchmark_csv),
            "--json",
            str(benchmark_json),
            "--summary-md",
            str(benchmark_md),
        ],
        root,
    )

    symbolic_csv = out_root / "windhub_parallel_symbolic_direct.csv"
    symbolic_json = out_root / "windhub_parallel_symbolic_direct.json"
    symbolic_md = out_root / "windhub_parallel_symbolic_direct.md"
    run(
        [
            str(exe(build_dir, "symbolic_numeric_eval")),
            "--mesh",
            "inp",
            "--inp",
            str(inp),
            "--case-name",
            "3d-WindTurbineHub",
            "--kernel",
            "physics_tet4",
            "--assemblies-list",
            args.assemblies_list,
            "--threads-range",
            threads_range,
            "--backend-list",
            "atomic,private_csr,lock_guard",
            "--max-memory-gb",
            str(args.max_memory_gb),
            "--csv",
            str(symbolic_csv),
            "--json",
            str(symbolic_json),
            "--summary-md",
            str(symbolic_md),
        ],
        root,
    )

    pattern_dir = out_root / "sparse_pattern"
    run(
        [
            str(exe(build_dir, "stiffness_pattern_export")),
            "--mesh",
            "inp",
            "--inp",
            str(inp),
            "--case-name",
            "3d-WindTurbineHub",
            "--kernel",
            "physics_tet4",
            "--threads",
            str(physical_cores),
            "--parallel-algo",
            "atomic",
            "--out-dir",
            str(pattern_dir),
            "--prefix",
            "windhub_physics_tet4",
        ],
        root,
    )
    run(
        [
            "python3",
            str(root / "scripts" / "plot_stiffness_pattern.py"),
            "--serial-csv",
            str(pattern_dir / "windhub_physics_tet4_serial_pattern.csv"),
            "--parallel-csv",
            str(pattern_dir / "windhub_physics_tet4_parallel_pattern.csv"),
            "--metadata",
            str(pattern_dir / "windhub_physics_tet4_metadata.json"),
            "--out-base",
            str(pattern_dir / "windhub_physics_tet4_spy_python"),
            "--title",
            "WindHub stiffness sparse pattern",
        ],
        root,
    )

    matlab_path = Path(args.matlab)
    if not args.skip_matlab and matlab_path.exists():
        matlab_cmd = (
            "addpath('scripts'); "
            "plot_stiffness_pattern_matlab("
            f"'{pattern_dir / 'windhub_physics_tet4_serial_pattern.csv'}',"
            f"'{pattern_dir / 'windhub_physics_tet4_parallel_pattern.csv'}',"
            f"'{pattern_dir / 'windhub_physics_tet4_spy_matlab'}',"
            "'WindHub stiffness sparse pattern')"
        )
        run([str(matlab_path), "-batch", matlab_cmd], root)
    elif not args.skip_matlab:
        raise FileNotFoundError(f"MATLAB executable not found: {matlab_path}")

    package_dir = out_root / "cross-platform-v2"
    run(
        [
            "python3",
            str(root / "scripts" / "package_cross_platform_results_v2.py"),
            "--out-dir",
            str(package_dir),
            "--platform-id",
            platform_id,
            "--thread-scaling-csv",
            str(benchmark_csv),
            "--symbolic-csv",
            str(symbolic_csv),
            "--lock-benchmark-csv",
            str(benchmark_csv),
            "--pattern-metadata",
            str(pattern_dir / "windhub_physics_tet4_metadata.json"),
        ],
        root,
    )
    run(["python3", str(root / "scripts" / "validate_benchmark_package_v2.py"), str(package_dir)], root)
    if shutil.which("python3"):
        print(f"[OK] mentor action-item outputs: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
