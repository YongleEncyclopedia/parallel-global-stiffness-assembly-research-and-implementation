#!/usr/bin/env python3
"""把 CUDA/GPU 历史内容移动到 legacy_gpu。

用途：在 CPU-only 主线中保留 GPU 历史资料，但避免它们继续出现在默认入口、
默认构建和用户文档中。脚本按路径和文件名启发式移动内容；运行前请先确认
工作区干净。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


GPU_TERMS = ("cuda", "gpu", "nvcc", ".cu")


def move_path(src: Path, dst_root: Path, project: Path, dry_run: bool) -> None:
    if not src.exists():
        return
    rel = src.relative_to(project)
    dst = dst_root / rel
    if dst.exists():
        print(f"跳过，目标已存在: {dst}")
        return
    print(f"移动: {rel} -> {dst.relative_to(project)}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))


def file_mentions_gpu(path: Path) -> bool:
    name = path.name.lower()
    if any(term in name for term in GPU_TERMS):
        return True
    if path.suffix.lower() not in {".py", ".bat", ".ps1", ".cmd", ".sh", ".md", ".txt"}:
        return False
    try:
        text = path.read_text(errors="ignore").lower()[:8192]
    except OSError:
        return False
    return any(term in text for term in GPU_TERMS)


def main() -> None:
    parser = argparse.ArgumentParser(description="归档 CUDA/GPU 历史内容到 legacy_gpu")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="cpu_parallel_stiffness_assembly 根目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印将移动的内容，不实际修改")
    args = parser.parse_args()

    project = args.project.resolve()
    if not (project / "CMakeLists.txt").exists():
        raise SystemExit(f"看起来不是 cpu_parallel_stiffness_assembly 根目录: {project}")

    legacy = project / "legacy_gpu"
    if not args.dry_run:
        legacy.mkdir(parents=True, exist_ok=True)

    fixed_paths = [
        project / "src" / "backends" / "cuda",
        project / "include" / "backends" / "cuda",
    ]
    for path in fixed_paths:
        move_path(path, legacy, project, args.dry_run)

    for cu_file in project.glob("*.cu"):
        move_path(cu_file, legacy / "standalone_cuda_verification", project, args.dry_run)

    for pattern in ("*.bat", "*.ps1", "*.cmd", "*.sh"):
        for script in project.glob(pattern):
            if file_mentions_gpu(script):
                move_path(script, legacy / "scripts", project, args.dry_run)

    scripts_dir = project / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.glob("*.py"):
            if script.name in {"archive_gpu_legacy.py", "plot_cpu_results.py", "run_cpu_experiments.py"}:
                continue
            if file_mentions_gpu(script):
                move_path(script, legacy / "scripts", project, args.dry_run)

    print("完成。legacy_gpu 仅作历史参考；当前主入口仍为 CPU benchmark。")


if __name__ == "__main__":
    main()
