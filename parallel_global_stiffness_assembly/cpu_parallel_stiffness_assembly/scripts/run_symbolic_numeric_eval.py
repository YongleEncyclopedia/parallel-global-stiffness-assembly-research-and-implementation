#!/usr/bin/env python3
"""Run the symbolic-vs-numeric assembly evaluation matrix."""
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import date
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def executable_path(build_dir: Path) -> Path:
    exe_name = "symbolic_numeric_eval.exe" if os.name == "nt" else "symbolic_numeric_eval"
    return build_dir / "bin" / exe_name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run physics_tet4 + WindHub symbolic/numeric assembly evaluation."
    )
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--out-root", default=None, help="default: results/YYYY-MM-DD-symbolic-numeric")
    parser.add_argument("--assemblies-list", default="1,3,10,30")
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = root / args.build_dir

    if not args.skip_build:
        run(
            [
                "cmake",
                "-S",
                ".",
                "-B",
                str(build_dir),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_TESTS=ON",
                "-DBUILD_BENCHMARKS=ON",
            ],
            root,
        )
        run(["cmake", "--build", str(build_dir), "--target", "symbolic_numeric_eval", "-j", "4"], root)

    exe = executable_path(build_dir)
    if not exe.exists():
        raise FileNotFoundError(f"symbolic_numeric_eval executable not found: {exe}")

    out_root = (
        root / "results" / f"{date.today().isoformat()}-symbolic-numeric"
        if args.out_root is None
        else Path(args.out_root)
    )
    out_root.mkdir(parents=True, exist_ok=True)

    run(
        [
            str(exe),
            "--mesh",
            "inp",
            "--inp",
            "../../examples/3d-WindTurbineHub.inp",
            "--case-name",
            "3d-WindTurbineHub",
            "--kernel",
            "physics_tet4",
            "--assemblies-list",
            args.assemblies_list,
            "--max-memory-gb",
            str(args.max_memory_gb),
            "--csv",
            str(out_root / "symbolic_numeric_eval.csv"),
            "--json",
            str(out_root / "symbolic_numeric_eval.json"),
            "--summary-md",
            str(out_root / "symbolic_numeric_eval_report.md"),
        ],
        root,
    )

    print(f"[OK] symbolic/numeric evaluation output: {out_root}")


if __name__ == "__main__":
    main()
