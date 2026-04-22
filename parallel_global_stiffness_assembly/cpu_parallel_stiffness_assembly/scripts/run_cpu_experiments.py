#!/usr/bin/env python3
"""运行 CPU 并行装配标准实验矩阵并自动绘图。"""
from __future__ import annotations

import argparse
import subprocess
from datetime import date
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def benchmark_exe(build_dir: Path) -> Path:
    exe_name = "benchmark_assembly.exe" if __import__("os").name == "nt" else "benchmark_assembly"
    return build_dir / "bin" / exe_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--out-root", default=None, help="输出根目录，默认 results/YYYY-MM-DD")
    parser.add_argument("--threads-all", action="store_true", default=True)
    parser.add_argument("--threads-list", default="1,2,4,8,14")
    parser.add_argument("--cube-repeat", type=int, default=3)
    parser.add_argument("--windhub-repeat", type=int, default=3)
    parser.add_argument("--physics-repeat", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-memory-gb", type=int, default=32)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = root / args.build_dir
    exe = benchmark_exe(build_dir)
    if not exe.exists():
        raise FileNotFoundError(f"benchmark executable not found: {exe}")

    out_root = root / "results" / date.today().isoformat() if args.out_root is None else Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    csv_dir = out_root / "csv"
    json_dir = out_root / "json"
    summary_dir = out_root / "summaries"
    figure_dir = out_root / "figures"
    for folder in (csv_dir, json_dir, summary_dir, figure_dir):
        folder.mkdir(parents=True, exist_ok=True)

    thread_args = ["--threads-all"] if args.threads_all else ["--threads-list", args.threads_list]

    cube_csv = csv_dir / "cube_tet4_simplified.csv"
    run(
        [
            str(exe),
            "--mesh", "cube",
            "--element", "tet4",
            "--nx", "8", "--ny", "8", "--nz", "8",
            "--case-name", "cube_tet4_8x8x8",
            "--algo", "serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner",
            *thread_args,
            "--kernel", "simplified",
            "--warmup", str(args.warmup),
            "--repeat", str(args.cube_repeat),
            "--check",
            "--max-memory-gb", str(args.max_memory_gb),
            "--csv", str(cube_csv),
            "--json", str(json_dir / "cube_tet4_simplified.json"),
            "--summary-md", str(summary_dir / "cube_tet4_simplified.md"),
        ],
        root,
    )

    windhub_simplified_csv = csv_dir / "windhub_simplified.csv"
    run(
        [
            str(exe),
            "--mesh", "inp",
            "--inp", "../../examples/3d-WindTurbineHub.inp",
            "--case-name", "3d-WindTurbineHub",
            "--algo", "serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner",
            *thread_args,
            "--kernel", "simplified",
            "--warmup", str(args.warmup),
            "--repeat", str(args.windhub_repeat),
            "--check",
            "--max-memory-gb", str(args.max_memory_gb),
            "--csv", str(windhub_simplified_csv),
            "--json", str(json_dir / "windhub_simplified.json"),
            "--summary-md", str(summary_dir / "windhub_simplified.md"),
        ],
        root,
    )

    windhub_physics_csv = csv_dir / "windhub_physics_tet4.csv"
    run(
        [
            str(exe),
            "--mesh", "inp",
            "--inp", "../../examples/3d-WindTurbineHub.inp",
            "--case-name", "3d-WindTurbineHub",
            "--algo", "serial,atomic,private_csr,coloring,row_owner",
            "--threads-list", "1,2,4,8,14",
            "--kernel", "physics_tet4",
            "--warmup", "0",
            "--repeat", str(args.physics_repeat),
            "--check",
            "--max-memory-gb", str(args.max_memory_gb),
            "--csv", str(windhub_physics_csv),
            "--json", str(json_dir / "windhub_physics_tet4.json"),
            "--summary-md", str(summary_dir / "windhub_physics_tet4.md"),
        ],
        root,
    )

    windhub_physics_coo_csv = csv_dir / "windhub_physics_tet4_coo_sort_reduce.csv"
    run(
        [
            str(exe),
            "--mesh", "inp",
            "--inp", "../../examples/3d-WindTurbineHub.inp",
            "--case-name", "3d-WindTurbineHub",
            "--algo", "coo_sort_reduce",
            "--threads-list", "1,2,4",
            "--kernel", "physics_tet4",
            "--warmup", "0",
            "--repeat", "1",
            "--check",
            "--max-memory-gb", str(args.max_memory_gb),
            "--csv", str(windhub_physics_coo_csv),
            "--json", str(json_dir / "windhub_physics_tet4_coo_sort_reduce.json"),
            "--summary-md", str(summary_dir / "windhub_physics_tet4_coo_sort_reduce.md"),
        ],
        root,
    )

    run(
        [
            "python3",
            "scripts/plot_cpu_results.py",
            str(cube_csv),
            str(windhub_simplified_csv),
            str(windhub_physics_csv),
            str(windhub_physics_coo_csv),
            "--out-dir",
            str(figure_dir),
        ],
        root,
    )

    print(f"[OK] 实验结果目录 / Output root: {out_root}")


if __name__ == "__main__":
    main()
