#!/usr/bin/env python3
"""配置、构建并运行可重复的小型 CPU 装配 smoke test。"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Set, Tuple

from pgsa_workflow import (
    cmake_configuration_for_preset,
    configure_and_build,
    prepare_output_root,
    resolve_executable,
    run_checked,
)


PARALLEL_ALGORITHMS = (
    ("atomic", "cpu_atomic"),
    ("lock_guard", "cpu_lock_guard"),
    ("private_csr", "cpu_private_csr"),
    ("coo_sort_reduce", "cpu_coo_sort_reduce"),
    ("graph_coloring", "cpu_graph_coloring"),
    ("row_owner", "cpu_row_owner"),
)
SMOKE_OUTPUT_ENTRIES = (
    "tet4_serial",
    "tet4_parallel",
    "hex8_serial",
    "hex8_parallel",
    "run_manifest.json",
)


def positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return value


def smoke_threads(text: str) -> list[int]:
    try:
        values = sorted({int(token.strip()) for token in text.split(",") if token.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("thread list must contain integers") from exc
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("thread list must contain positive integers")
    if not {1, 2}.issubset(values):
        raise argparse.ArgumentTypeError("smoke thread list must include 1 and 2")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="构建并运行 Tet4/Hex8 的小型 CPU 正确性 smoke。"
    )
    parser.add_argument("--preset", default="cpu-release")
    parser.add_argument(
        "--build-dir",
        default=None,
        help="已有构建目录；自定义目录需与 --skip-build 一起使用",
    )
    parser.add_argument(
        "--threads-list",
        "--threads",
        dest="threads",
        default="1,2",
        type=smoke_threads,
    )
    parser.add_argument("--nx", type=positive_int, default=4)
    parser.add_argument("--ny", type=positive_int, default=4)
    parser.add_argument("--nz", type=positive_int, default=4)
    parser.add_argument("--out-root", default=None)
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
        return (root / "results" / "smoke_cpu").resolve()
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


def _build_tasks(
    executable: Path,
    out_root: Path,
    threads: list[int],
    nx: int,
    ny: int,
    nz: int,
) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    parallel_cli = ",".join(name for name, _ in PARALLEL_ALGORITHMS)
    parallel_threads = ",".join(str(value) for value in threads)
    for element in ("tet4", "hex8"):
        case_name = f"smoke_{element}_{nx}x{ny}x{nz}"
        for mode, algorithms, thread_text, expected in (
            ("serial", "serial", "1", {("cpu_serial", 1)}),
            (
                "parallel",
                parallel_cli,
                parallel_threads,
                {
                    (canonical, thread)
                    for _, canonical in PARALLEL_ALGORITHMS
                    for thread in threads
                },
            ),
        ):
            task_name = f"{element}_{mode}"
            task_dir = out_root / task_name
            csv_path = task_dir / "results.csv"
            json_path = task_dir / "results.json"
            summary_path = task_dir / "summary.md"
            command = [
                str(executable),
                "--mesh",
                "cube",
                "--element",
                element,
                "--nx",
                str(nx),
                "--ny",
                str(ny),
                "--nz",
                str(nz),
                "--case-name",
                f"{case_name}_{mode}",
                "--algo",
                algorithms,
                "--threads-list",
                thread_text,
                "--stiffness-model",
                "linear_elastic_solid",
                "--warmup",
                "0",
                "--repeat",
                "1",
                "--check",
                "--csv",
                str(csv_path),
                "--json",
                str(json_path),
                "--summary-md",
                str(summary_path),
            ]
            tasks.append(
                {
                    "name": task_name,
                    "command": command,
                    "expected_records": expected,
                    "csv": csv_path,
                    "json": json_path,
                    "summary": summary_path,
                }
            )
    return tasks


def assert_all_pass(
    result_path: Path,
    expected_records: Optional[Set[Tuple[str, int]]] = None,
) -> dict[str, object]:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    baseline = payload.get("baseline", {})
    if baseline.get("stiffness_model") != "linear_elastic_solid":
        raise RuntimeError(f"unexpected stiffness model in {result_path}")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"benchmark produced no records: {result_path}")
    non_pass = [record for record in records if record.get("status") != "PASS"]
    if non_pass:
        details = ", ".join(
            f"{record.get('algorithm', '<missing>')}@{record.get('threads', '?')}="
            f"{record.get('status', '<missing>')}"
            for record in non_pass
        )
        raise RuntimeError(f"smoke result contains non-PASS records: {details}")
    if expected_records is not None:
        actual = {
            (str(record.get("algorithm")), int(record.get("threads")))
            for record in records
            if record.get("algorithm") is not None and record.get("threads") is not None
        }
        missing = sorted(expected_records - actual)
        unexpected = sorted(actual - expected_records)
        if missing or unexpected:
            raise RuntimeError(
                f"smoke record inventory mismatch in {result_path}: "
                f"missing={missing}, unexpected={unexpected}"
            )
    return payload


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
        tasks = _build_tasks(
            _predicted_executable(build_dir),
            out_root,
            args.threads,
            args.nx,
            args.ny,
            args.nz,
        )
        for task in tasks:
            print("+", shlex.join(task["command"]))
        return 0

    if not args.skip_build:
        build_dir = configure_and_build(root, args.preset)
    executable = resolve_executable(build_dir, "benchmark_assembly")
    prepare_output_root(out_root, args.overwrite, root, SMOKE_OUTPUT_ENTRIES)
    tasks = _build_tasks(
        executable, out_root, args.threads, args.nx, args.ny, args.nz
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
        "schema_version": "pgsa-smoke-run-v1",
        "commit_sha": _git_commit(root),
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
        "threads": args.threads,
        "commands": [task["command"] for task in tasks],
        "tasks": manifest_tasks,
    }
    _write_manifest(manifest_path, manifest)

    for task, entry in zip(tasks, manifest_tasks):
        entry["status"] = "RUNNING"
        _write_manifest(manifest_path, manifest)
        try:
            run_checked(task["command"], root)
            payload = assert_all_pass(task["json"], task["expected_records"])
        except Exception as exc:
            entry["status"] = "FAIL"
            entry["error"] = str(exc)
            _write_manifest(manifest_path, manifest)
            raise
        benchmark_platform = payload.get("platform", {})
        if isinstance(benchmark_platform, dict):
            build = manifest["build"]
            assert isinstance(build, dict)
            build["compiler"] = benchmark_platform.get("compiler", build["compiler"])
            build["openmp"] = benchmark_platform.get("openmp", build["openmp"])
        entry["status"] = "PASS"
        _write_manifest(manifest_path, manifest)

    print(f"[OK] smoke outputs: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
