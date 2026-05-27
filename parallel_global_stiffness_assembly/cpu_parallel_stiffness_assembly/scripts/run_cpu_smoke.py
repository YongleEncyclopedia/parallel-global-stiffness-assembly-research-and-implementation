#!/usr/bin/env python3
"""配置、构建并运行小型 CPU 装配 smoke test。"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--threads", default="1,2,4")
    parser.add_argument("--nx", type=int, default=4)
    parser.add_argument("--ny", type=int, default=4)
    parser.add_argument("--nz", type=int, default=4)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = root / args.build_dir
    run(["cmake", "-S", ".", "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"], root)
    run(["cmake", "--build", str(build_dir), "-j"], root)
    exe = build_dir / "bin" / ("benchmark_assembly.exe" if __import__("os").name == "nt" else "benchmark_assembly")
    run([
        str(exe),
        "--mesh", "cube", "--element", "tet4",
        "--nx", str(args.nx), "--ny", str(args.ny), "--nz", str(args.nz),
        "--case-name", f"smoke_tet4_{args.nx}x{args.ny}x{args.nz}",
        "--algo", "all",
        "--threads-list", args.threads,
        "--kernel", "simplified",
        "--check",
        "--csv", "results/smoke_cpu.csv",
        "--json", "results/smoke_cpu.json",
        "--summary-md", "results/smoke_cpu.md",
    ], root)


if __name__ == "__main__":
    main()
