#!/usr/bin/env python3
"""Run Apple Silicon P/E QoS-biased thread-scaling supplements.

The runs produced here intentionally use macOS QoS policy, not Linux-style
hard CPU affinity. Package notes and the supplement report keep that
interpretation boundary explicit.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from cross_platform_schema import (
    SCHEMA_VERSION,
    load_package,
    package_from_thread_scaling_root,
    render_cross_platform_report,
    validate_package,
    validate_packages,
    write_package,
)
from cross_platform_schema import current_platform_metadata


PLATFORM_ID = "apple-m4-max"
QOS_NOTE = "QoS-biased sensitivity run; not hard-pinned core affinity"
ALGORITHMS = (
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
)
PROFILE_ORDER = {
    "full_host": 0,
    "performance_core_only": 1,
    "efficiency_core_only": 2,
}


@dataclass(frozen=True)
class ProfileSpec:
    run_profile: str
    label: str
    threads: int
    policy: str
    taskpolicy_args: tuple[str, ...]
    out_suffix: str


PROFILES = (
    ProfileSpec(
        run_profile="performance_core_only",
        label="Performance QoS",
        threads=10,
        policy="normal foreground/default scheduling; thread range limited to detected P-core count",
        taskpolicy_args=(),
        out_suffix="performance-qos",
    ),
    ProfileSpec(
        run_profile="efficiency_core_only",
        label="Efficiency QoS",
        threads=4,
        policy="taskpolicy -c background; thread range limited to detected E-core count",
        taskpolicy_args=("taskpolicy", "-c", "background"),
        out_suffix="efficiency-qos",
    ),
)


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def run_capture(cmd: list[str], cwd: Path) -> str:
    print("+", " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(completed.stdout, end="")
    return completed.stdout


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_platform(metadata: dict) -> None:
    if metadata.get("os") != "Darwin" or metadata.get("arch") != "arm64":
        raise RuntimeError(f"expected macOS arm64, got {metadata.get('os')} {metadata.get('arch')}")
    if metadata.get("cpu_model") != "Apple M4 Max":
        raise RuntimeError(f"expected Apple M4 Max, got {metadata.get('cpu_model')}")
    if int(metadata.get("performance_core_count") or 0) != 10:
        raise RuntimeError(f"expected 10 performance cores, got {metadata.get('performance_core_count')}")
    if int(metadata.get("efficiency_core_count") or 0) != 4:
        raise RuntimeError(f"expected 4 efficiency cores, got {metadata.get('efficiency_core_count')}")
    if not shutil.which("taskpolicy"):
        raise RuntimeError("taskpolicy is required for the efficiency QoS profile")


def build_and_test(root: Path, build_dir: Path) -> str:
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
    run(["cmake", "--build", str(build_dir), "-j"], root)
    return run_capture(["ctest", "--test-dir", str(build_dir), "--output-on-failure"], root)


def profile_command(args: argparse.Namespace, spec: ProfileSpec, out_root: Path) -> list[str]:
    profile_note = f"{spec.label}: {QOS_NOTE}. {spec.policy}."
    command = [
        sys.executable,
        "scripts/run_thread_scaling_eval.py",
        "--skip-build",
        "--threads-range",
        f"1:{spec.threads}",
        "--warmup",
        str(args.warmup),
        "--repeat",
        str(args.repeat),
        "--max-memory-gb",
        str(args.max_memory_gb),
        "--out-root",
        str(out_root),
        "--platform-id",
        PLATFORM_ID,
        "--run-profile",
        spec.run_profile,
        "--profile-note",
        profile_note,
    ]
    return [*spec.taskpolicy_args, *command]


def run_profile(root: Path, args: argparse.Namespace, spec: ProfileSpec, out_root: Path) -> list[str]:
    actual_command = profile_command(args, spec, out_root)
    run(actual_command, root)
    run([sys.executable, "scripts/plot_thread_scaling_results.py", "--results-root", str(out_root)], root)
    return actual_command


def validate_result_root(root: Path, spec: ProfileSpec) -> dict[str, int]:
    combined = root / "thread_scaling_combined.csv"
    rows = csv_rows(combined)
    non_pass = sum(1 for row in rows if row.get("status") != "PASS")
    expected_rows = 2 * len(ALGORITHMS) * spec.threads
    if len(rows) != expected_rows:
        raise RuntimeError(f"{root} expected {expected_rows} rows, got {len(rows)}")
    if non_pass:
        raise RuntimeError(f"{root} has {non_pass} non-PASS rows")

    required_files = [
        root / "default" / "thread_scaling_default.csv",
        root / "default" / "thread_scaling_default.json",
        root / "default" / "benchmark_summary_default.md",
        root / "bound" / "thread_scaling_bound.csv",
        root / "bound" / "thread_scaling_bound.json",
        root / "bound" / "benchmark_summary_bound.md",
        root / "figures" / "summary.md",
        root / "figures" / "thread_scaling_contact_sheet.png",
        root / "figures" / "thread_scaling_default_dashboard.png",
        root / "figures" / "thread_scaling_default_dashboard.svg",
        root / "figures" / "thread_scaling_bound_dashboard.png",
        root / "figures" / "thread_scaling_bound_dashboard.svg",
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        raise RuntimeError(f"{root} missing required output files: {', '.join(missing)}")
    return {"rows": len(rows), "non_pass": non_pass}


def package_profile(
    source_root: Path,
    out_dir: Path,
    run_profile: str,
    profile_note: str,
    profile_statuses: dict[str, str],
    metadata: dict,
) -> Path:
    package = package_from_thread_scaling_root(
        source_root,
        platform_id=PLATFORM_ID,
        run_profile=run_profile,
        profile_note=profile_note,
        core_profile_status=profile_statuses,
        schema_version=SCHEMA_VERSION,
    )
    package["platform"].update(
        {
            "inspector_cpu_model": metadata.get("cpu_model", ""),
            "performance_core_count": metadata.get("performance_core_count", 0),
            "efficiency_core_count": metadata.get("efficiency_core_count", 0),
            "affinity_control": metadata.get("affinity_control", "unknown"),
            "inspection_evidence": metadata.get("evidence", []),
        }
    )
    result = validate_package(package)
    if result.errors:
        raise RuntimeError("; ".join(result.errors))
    for warning in result.warnings:
        print(f"[WARN] package: {warning}")
    return write_package(package, out_dir)


def best_bound_rows(source_root: Path) -> dict[str, dict[str, str]]:
    rows = csv_rows(source_root / "thread_scaling_combined.csv")
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("env_group") != "bound" or row.get("status") != "PASS":
            continue
        algorithm = row.get("algorithm", "")
        assembly_ms = float(row.get("assembly_ms") or row.get("assembly_mean_ms") or 0.0)
        if assembly_ms <= 0.0:
            continue
        current = best.get(algorithm)
        if current is None or assembly_ms < float(current["_assembly_ms"]):
            row = dict(row)
            row["_assembly_ms"] = str(assembly_ms)
            best[algorithm] = row
    return best


def describe_best(row: dict[str, str] | None) -> str:
    if not row:
        return "no PASS data"
    return f"`{int(float(row['threads']))}T`, `{float(row['_assembly_ms']):.3f} ms`"


def compare(candidate: dict[str, str] | None, reference: dict[str, str] | None) -> str:
    if not candidate or not reference:
        return "n/a"
    cand = float(candidate["_assembly_ms"])
    ref = float(reference["_assembly_ms"])
    if ref <= 0.0:
        return "n/a"
    change = (cand / ref - 1.0) * 100.0
    if abs(change) <= 5.0:
        return "within `5%`"
    direction = "slower" if change > 0.0 else "faster"
    return f"{direction} by `{abs(change):.1f}%`"


def ctest_summary(output: str) -> str:
    match = re.search(r"100% tests passed, (\d+) tests passed out of (\d+)", output)
    if match:
        return f"`{match.group(1)}/{match.group(2)}` tests passed"
    match = re.search(r"100% tests passed, 0 tests failed out of (\d+)", output)
    if match:
        return f"`{match.group(1)}/{match.group(1)}` tests passed"
    if "100% tests passed" in output:
        return "`ctest` passed"
    return "`ctest` completed with exit code 0"


def render_supplement(
    *,
    run_date: str,
    metadata: dict,
    ctest_output: str,
    profile_commands: dict[str, list[str]],
    result_stats: dict[str, dict[str, int]],
    full_host_source: Path,
    performance_root: Path,
    efficiency_root: Path,
) -> str:
    full_best = best_bound_rows(full_host_source)
    perf_best = best_bound_rows(performance_root)
    eff_best = best_bound_rows(efficiency_root)

    lines = [
        "# Apple M4 Max QoS-Biased P/E-Core Supplement",
        "",
        "## Scope",
        "",
        "This supplement keeps the existing Apple M4 Max `full_host` run as the mixed Mac baseline and adds two macOS scheduler-policy sensitivity runs:",
        "",
        f"- Performance profile: `{performance_root}`, normal foreground/default scheduling, `threads=1..10`.",
        f"- Efficiency profile: `{efficiency_root}`, `taskpolicy -c background`, `threads=1..4`.",
        "",
        f"Both new profiles are recorded as `{QOS_NOTE}`. They are not equivalent to Linux `taskset` CPU affinity.",
        "",
        "## Host And QoS Evidence",
        "",
        f"- CPU model: `{metadata.get('cpu_model', '')}`",
        f"- physical_cores: `{metadata.get('physical_cores', 0)}`",
        f"- logical_cores: `{metadata.get('logical_cores', 0)}`",
        f"- performance_core_count: `{metadata.get('performance_core_count', 0)}`",
        f"- efficiency_core_count: `{metadata.get('efficiency_core_count', 0)}`",
        f"- affinity_control metadata: `{metadata.get('affinity_control', 'unknown')}`",
        "- Core-class evidence: `sysctl hw.perflevel0/1.physicalcpu`.",
        "- QoS policy evidence: Apple documents QoS as the public mechanism that influences P/E core placement on Apple Silicon; macOS `taskpolicy` exposes QoS/background policy but not per-core hard pinning.",
        "",
        "## Commands",
        "",
        "```bash",
        "cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON",
        "cmake --build build/cpu-release -j",
        "ctest --test-dir build/cpu-release --output-on-failure",
        "",
        " ".join(profile_commands["performance_core_only"]),
        f"python3 scripts/plot_thread_scaling_results.py --results-root {performance_root}",
        "",
        " ".join(profile_commands["efficiency_core_only"]),
        f"python3 scripts/plot_thread_scaling_results.py --results-root {efficiency_root}",
        "```",
        "",
        "## Validation",
        "",
        "- Release configure/build completed successfully.",
        f"- `ctest`: {ctest_summary(ctest_output)}.",
        f"- Performance QoS: `{result_stats['performance_core_only']['rows']}` combined rows, `non_pass={result_stats['performance_core_only']['non_pass']}`.",
        f"- Efficiency QoS: `{result_stats['efficiency_core_only']['rows']}` combined rows, `non_pass={result_stats['efficiency_core_only']['non_pass']}`.",
        "- Each new output root contains combined CSV, default/bound CSV+JSON+summary files, figure index, contact sheet, and default/bound dashboard PNG/SVG files.",
        "",
        "## Bound Best-Time Comparison",
        "",
        "The table below uses `bound` as the primary interpretation group. Runtime changes within `5%` are treated as roughly flat.",
        "",
        "| Algorithm | Full-host bound best | Performance QoS best | P QoS vs full | Efficiency QoS best | E QoS vs full | E vs P |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for algorithm in ALGORITHMS:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                algorithm,
                describe_best(full_best.get(algorithm)),
                describe_best(perf_best.get(algorithm)),
                compare(perf_best.get(algorithm), full_best.get(algorithm)),
                describe_best(eff_best.get(algorithm)),
                compare(eff_best.get(algorithm), full_best.get(algorithm)),
                compare(eff_best.get(algorithm), perf_best.get(algorithm)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These results are macOS QoS-policy sensitivity results under restricted thread ranges. They should not be interpreted as intrinsic P-core-only or E-core-only hardware throughput, and they should not be compared with the Intel `taskset` results as if the isolation mechanism were identical.",
            "",
            f"Generated on `{run_date}`.",
            "",
        ]
    )
    return "\n".join(lines)


def package_set(cross_platform_root: Path) -> list[Path]:
    def sort_key(path: Path) -> tuple[str, int, str]:
        profile = path.parent.name
        platform = path.parent.parent.name
        return (platform, PROFILE_ORDER.get(profile, 99), profile)

    return sorted((cross_platform_root / "packages").glob("*/*/benchmark_package.json"), key=sort_key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", default=date.today().isoformat())
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--max-memory-gb", type=float, default=32.0)
    parser.add_argument("--build-dir", default="build/cpu-release")
    parser.add_argument("--full-host-source", default="results/2026-05-11-thread-scaling")
    parser.add_argument("--cross-platform-root", default="results/cross-platform-v1")
    parser.add_argument(
        "--reuse-existing-results",
        action="store_true",
        help="reuse dated raw roots if they already contain complete CSV/figure outputs",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    # Keep generated package source paths relative, matching existing packages.
    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(root)
        metadata = current_platform_metadata()
        print("[INFO] detected platform metadata:")
        print(metadata)
        validate_platform(metadata)

        build_dir = Path(args.build_dir)
        ctest_output = build_and_test(root, build_dir)

        result_roots = {
            spec.run_profile: Path("results") / f"{args.run_date}-thread-scaling-macos-m4max-{spec.out_suffix}"
            for spec in PROFILES
        }
        profile_commands: dict[str, list[str]] = {}
        result_stats: dict[str, dict[str, int]] = {}
        for spec in PROFILES:
            out_root = result_roots[spec.run_profile]
            if args.reuse_existing_results and (out_root / "thread_scaling_combined.csv").exists():
                profile_commands[spec.run_profile] = profile_command(args, spec, out_root)
                print(f"[INFO] reusing existing result root: {out_root}")
                if not (out_root / "figures" / "summary.md").exists():
                    run([sys.executable, "scripts/plot_thread_scaling_results.py", "--results-root", str(out_root)], root)
            else:
                profile_commands[spec.run_profile] = run_profile(root, args, spec, out_root)
            result_stats[spec.run_profile] = validate_result_root(out_root, spec)

        profile_statuses = {
            "full_host": "available",
            "performance_core_only": "available",
            "efficiency_core_only": "available",
        }
        cross_root = Path(args.cross_platform_root)
        package_root = cross_root / "packages" / PLATFORM_ID
        full_host_note = (
            f"Existing Mac full-host thread-scaling baseline. "
            f"P/E supplements collected as {QOS_NOTE}."
        )
        package_profile(
            Path(args.full_host_source),
            package_root / "full_host",
            "full_host",
            full_host_note,
            profile_statuses,
            metadata,
        )
        for spec in PROFILES:
            note = f"{spec.label}: {QOS_NOTE}. {spec.policy}."
            package_profile(
                result_roots[spec.run_profile],
                package_root / spec.run_profile,
                spec.run_profile,
                note,
                profile_statuses,
                metadata,
            )

        supplement_path = Path("results") / f"{args.run_date}-thread-scaling-macos-m4max-qos-supplement.md"
        supplement_path.write_text(
            render_supplement(
                run_date=args.run_date,
                metadata=metadata,
                ctest_output=ctest_output,
                profile_commands=profile_commands,
                result_stats=result_stats,
                full_host_source=Path(args.full_host_source),
                performance_root=result_roots["performance_core_only"],
                efficiency_root=result_roots["efficiency_core_only"],
            ),
            encoding="utf-8",
        )
        print(f"[OK] wrote {supplement_path}")

        package_paths = package_set(cross_root)
        packages = [load_package(path) for path in package_paths]
        validation = validate_packages(packages)
        for warning in validation.warnings:
            print(f"WARNING: {warning}")
        if validation.errors:
            for error in validation.errors:
                print(f"ERROR: {error}")
            return 1
        report_path = cross_root / "cross_platform_schema_report.md"
        report_path.write_text(render_cross_platform_report(packages), encoding="utf-8")
        print(f"[OK] wrote {report_path}")
        print(f"[OK] validated {len(packages)} package(s)")
        return 0
    finally:
        import os

        os.chdir(old_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
