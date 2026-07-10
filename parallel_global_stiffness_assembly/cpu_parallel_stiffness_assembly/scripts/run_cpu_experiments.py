#!/usr/bin/env python3
"""运行可复现的 CPU 装配实验 profile 并记录 manifest。"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from pgsa_workflow import (
    assert_lfs_materialized,
    cmake_configuration_for_preset,
    configure_and_build,
    prepare_output_root,
    resolve_executable,
    run_checked,
)


CUBE_ALGORITHMS = (
    "serial,atomic,lock_guard,private_csr,coo_sort_reduce,graph_coloring,row_owner"
)
WINDHUB_ALGORITHMS = (
    "serial,atomic,lock_guard,private_csr,graph_coloring,row_owner"
)
EXPERIMENT_OUTPUT_ENTRIES = (
    "cube_tet4",
    "windhub",
    "windhub_coo",
    "figures",
    "run_manifest.json",
)


def positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return value


def thread_list(text: str) -> list[int]:
    try:
        values = sorted({int(token.strip()) for token in text.split(",") if token.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("thread list must contain integers") from exc
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("thread list must contain positive integers")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行 cube、WindHub 或高内存 COO CPU 装配实验。"
    )
    parser.add_argument(
        "--profile",
        choices=("cube", "windhub", "windhub-coo", "standard"),
        default="standard",
    )
    parser.add_argument("--preset", default="cpu-release")
    parser.add_argument(
        "--build-dir",
        default=None,
        help="已有构建目录；自定义目录需与 --skip-build 一起使用",
    )
    parser.add_argument(
        "--out-root", default=None, help="输出根目录，默认 results/YYYY-MM-DD"
    )
    threads = parser.add_mutually_exclusive_group()
    threads.add_argument("--threads-all", action="store_true")
    threads.add_argument("--threads-list", type=thread_list)
    parser.add_argument("--cube-repeat", type=positive_int, default=3)
    parser.add_argument("--windhub-repeat", type=positive_int, default=3)
    parser.add_argument(
        "--coo-repeat",
        "--physics-repeat",
        dest="coo_repeat",
        type=positive_int,
        default=2,
    )
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-memory-gb", type=positive_int, default=32)
    parser.add_argument(
        "--windhub-input",
        default=None,
        help="WindHub .inp；默认使用仓库 examples/3d-WindTurbineHub.inp",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _resolve_build_dir(root: Path, value: Optional[str], preset: str) -> Path:
    if value is None:
        return (root / "build" / preset).resolve()
    path = Path(value).expanduser()
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def _resolve_output_root(root: Path, value: Optional[str]) -> Path:
    if value is None:
        return (root / "results" / date.today().isoformat()).resolve()
    return Path(value).expanduser().resolve()


def _resolve_windhub_input(root: Path, value: Optional[str]) -> Path:
    if value is None:
        return (root / ".." / ".." / "examples" / "3d-WindTurbineHub.inp").resolve()
    return Path(value).expanduser().resolve()


def _predicted_executable(build_dir: Path) -> Path:
    try:
        return resolve_executable(build_dir, "benchmark_assembly")
    except FileNotFoundError:
        pass
    suffix = ".exe" if os.name == "nt" else ""
    return build_dir / "bin" / f"benchmark_assembly{suffix}"


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _selected_task_names(profile: str) -> tuple[str, ...]:
    if profile == "standard":
        return ("cube_tet4", "windhub")
    if profile == "cube":
        return ("cube_tet4",)
    if profile == "windhub":
        return ("windhub",)
    return ("windhub_coo",)


def _thread_arguments(threads_all: bool, threads: Optional[list[int]]) -> list[str]:
    if threads_all or threads is None:
        return ["--threads-all"]
    return ["--threads-list", ",".join(str(value) for value in threads)]


def _task_command(
    executable: Path,
    name: str,
    out_root: Path,
    windhub_input: Path,
    thread_args: list[str],
    warmup: int,
    repeat: int,
    max_memory_gb: int,
) -> dict[str, object]:
    task_dir = out_root / name
    csv_path = task_dir / "results.csv"
    json_path = task_dir / "results.json"
    summary_path = task_dir / "summary.md"
    if name == "cube_tet4":
        mesh_args = [
            "--mesh",
            "cube",
            "--element",
            "tet4",
            "--nx",
            "8",
            "--ny",
            "8",
            "--nz",
            "8",
            "--case-name",
            "cube_tet4_8x8x8",
        ]
        algorithms = CUBE_ALGORITHMS
    else:
        mesh_args = [
            "--mesh",
            "inp",
            "--inp",
            str(windhub_input),
            "--case-name",
            "3d-WindTurbineHub",
        ]
        algorithms = "coo_sort_reduce" if name == "windhub_coo" else WINDHUB_ALGORITHMS
    command = [
        str(executable),
        *mesh_args,
        "--algo",
        algorithms,
        *thread_args,
        "--stiffness-model",
        "linear_elastic_solid",
        "--warmup",
        str(warmup),
        "--repeat",
        str(repeat),
        "--check",
        "--max-memory-gb",
        str(max_memory_gb),
        "--csv",
        str(csv_path),
        "--json",
        str(json_path),
        "--summary-md",
        str(summary_path),
    ]
    return {
        "name": name,
        "command": command,
        "csv": csv_path,
        "json": json_path,
        "summary": summary_path,
    }


def _build_tasks(
    executable: Path,
    out_root: Path,
    profile: str,
    windhub_input: Path,
    thread_args: list[str],
    warmup: int,
    cube_repeat: int,
    windhub_repeat: int,
    coo_repeat: int,
    max_memory_gb: int,
) -> list[dict[str, object]]:
    repeats = {
        "cube_tet4": cube_repeat,
        "windhub": windhub_repeat,
        "windhub_coo": coo_repeat,
    }
    return [
        _task_command(
            executable,
            name,
            out_root,
            windhub_input,
            thread_args,
            warmup,
            repeats[name],
            max_memory_gb,
        )
        for name in _selected_task_names(profile)
    ]


def _inspect_result(json_path: Path, csv_path: Path) -> tuple[str, dict[str, object]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    baseline = payload.get("baseline", {})
    if baseline.get("stiffness_model") != "linear_elastic_solid":
        raise RuntimeError(f"unexpected stiffness model in {json_path}")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"benchmark produced no records: {json_path}")
    with csv_path.open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    if not csv_rows or any(
        row.get("stiffness_model") != "linear_elastic_solid" for row in csv_rows
    ):
        raise RuntimeError(f"CSV stiffness model contract failed: {csv_path}")
    statuses = [record.get("status") for record in records]
    if any(status not in {"PASS", "SKIP", "FAIL"} for status in statuses):
        return "FAIL", payload
    if "FAIL" in statuses:
        return "FAIL", payload
    if "SKIP" in statuses:
        return "PASS_WITH_SKIPS", payload
    return "PASS", payload


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    build_dir = _resolve_build_dir(root, args.build_dir, args.preset)
    expected_build_dir = (root / "build" / args.preset).resolve()
    if args.build_dir is not None and not args.skip_build and build_dir != expected_build_dir:
        parser.error("a custom --build-dir requires --skip-build")
    out_root = _resolve_output_root(root, args.out_root)
    windhub_input = _resolve_windhub_input(root, args.windhub_input)
    selected = _selected_task_names(args.profile)

    if any(name.startswith("windhub") for name in selected):
        windhub_input = assert_lfs_materialized(windhub_input)

    thread_args = _thread_arguments(args.threads_all, args.threads_list)
    executable = _predicted_executable(build_dir)
    tasks = _build_tasks(
        executable,
        out_root,
        args.profile,
        windhub_input,
        thread_args,
        args.warmup,
        args.cube_repeat,
        args.windhub_repeat,
        args.coo_repeat,
        args.max_memory_gb,
    )
    plot_command = [
        sys.executable,
        str(root / "scripts" / "plot_cpu_results.py"),
        *(str(task["csv"]) for task in tasks),
        "--out-dir",
        str(out_root / "figures"),
    ]

    if args.dry_run:
        if not args.skip_build:
            print("+", shlex.join(["cmake", "--preset", args.preset]))
            print(
                "+",
                shlex.join(
                    [
                        "cmake",
                        "--build",
                        "--preset",
                        args.preset,
                        "--config",
                        cmake_configuration_for_preset(args.preset),
                    ]
                ),
            )
        for task in tasks:
            print("+", shlex.join(task["command"]))
        print("+", shlex.join(plot_command))
        return 0

    if not args.skip_build:
        build_dir = configure_and_build(root, args.preset)
    executable = resolve_executable(build_dir, "benchmark_assembly")
    tasks = _build_tasks(
        executable,
        out_root,
        args.profile,
        windhub_input,
        thread_args,
        args.warmup,
        args.cube_repeat,
        args.windhub_repeat,
        args.coo_repeat,
        args.max_memory_gb,
    )
    plot_command = [
        sys.executable,
        str(root / "scripts" / "plot_cpu_results.py"),
        *(str(task["csv"]) for task in tasks),
        "--out-dir",
        str(out_root / "figures"),
    ]
    prepare_output_root(out_root, args.overwrite, root, EXPERIMENT_OUTPUT_ENTRIES)

    thread_manifest = (
        {"mode": "list", "values": args.threads_list}
        if args.threads_list is not None
        else {"mode": "all", "values": []}
    )
    manifest_path = out_root / "run_manifest.json"
    manifest_tasks = [
        {
            "name": task["name"],
            "command": task["command"],
            "artifacts": {
                "csv": str(task["csv"]),
                "json": str(task["json"]),
                "summary": str(task["summary"]),
            },
            "status": "PENDING",
        }
        for task in tasks
    ]
    manifest: dict[str, object] = {
        "schema_version": "pgsa-experiment-run-v1",
        "commit_sha": _git_commit(root),
        "profile": args.profile,
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "build": {
            "preset": args.preset,
            "build_dir": str(build_dir),
            "compiler": "UNKNOWN",
            "openmp": "UNKNOWN",
        },
        "threads": thread_manifest,
        "commands": [task["command"] for task in tasks] + [plot_command],
        "tasks": manifest_tasks,
        "postprocess": {"name": "plot_cpu_results", "status": "PENDING"},
    }
    _write_manifest(manifest_path, manifest)

    for task, entry in zip(tasks, manifest_tasks):
        entry["status"] = "RUNNING"
        _write_manifest(manifest_path, manifest)
        try:
            run_checked(task["command"], root)
            status, payload = _inspect_result(task["json"], task["csv"])
        except Exception as exc:
            entry["status"] = "FAIL"
            entry["error"] = str(exc)
            _write_manifest(manifest_path, manifest)
            raise
        entry["status"] = status
        benchmark_platform = payload.get("platform", {})
        if isinstance(benchmark_platform, dict):
            build = manifest["build"]
            assert isinstance(build, dict)
            build["compiler"] = benchmark_platform.get("compiler", build["compiler"])
            build["openmp"] = benchmark_platform.get("openmp", build["openmp"])
        _write_manifest(manifest_path, manifest)
        if status == "FAIL":
            raise RuntimeError(f"benchmark task reported FAIL records: {task['name']}")

    postprocess = manifest["postprocess"]
    assert isinstance(postprocess, dict)
    postprocess["status"] = "RUNNING"
    postprocess["command"] = plot_command
    _write_manifest(manifest_path, manifest)
    try:
        run_checked(plot_command, root)
    except Exception as exc:
        postprocess["status"] = "FAIL"
        postprocess["error"] = str(exc)
        _write_manifest(manifest_path, manifest)
        raise
    postprocess["status"] = "PASS"
    postprocess["out_dir"] = str(out_root / "figures")
    _write_manifest(manifest_path, manifest)

    print(f"[OK] experiment outputs: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
