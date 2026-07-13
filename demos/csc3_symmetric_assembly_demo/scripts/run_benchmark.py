#!/usr/bin/env python3
"""Reproducible evidence runner for the CSC3 assembly demo.

This module intentionally uses only the Python standard library.  The public
helpers form the safety and evidence contract used by the workflow tests; the
subprocess orchestration is added separately so that these invariants remain
independently testable.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import shlex
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


OWNED_OUTPUT_NAMES: Tuple[str, ...] = (
    "ctest.xml",
    "benchmark_samples.csv",
    "benchmark_summary.json",
    "run_manifest.json",
    "summary.md",
)

REQUIRED_OPENMP_ENV: Dict[str, str] = {
    "OMP_DYNAMIC": "false",
    "OMP_PROC_BIND": "close",
    "OMP_PLACES": "cores",
}

MANIFEST_SCHEMA_VERSION = "csc3-demo-benchmark-run-v1"
NON_FORMAL_WARNING = "NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE"


class CommandResult:
    """Captured result of one external command."""

    __slots__ = ("command", "returncode", "stdout", "stderr")

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.command = list(command)
        self.returncode = int(returncode)
        self.stdout = stdout
        self.stderr = stderr


def sha256_file(path: Union[str, Path]) -> str:
    """Return the lowercase SHA-256 digest of a regular file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_materialized(path: Union[str, Path]) -> Path:
    """Validate that an input exists and is not a Git LFS pointer."""

    input_path = Path(path).expanduser()
    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"input path is not a regular file: {input_path}")
    with input_path.open("rb") as stream:
        prefix = stream.read(256)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            f"input is a Git LFS pointer, not materialized data: {input_path}"
        )
    return input_path.resolve()


# Stable compatibility name used by the repository's other workflow scripts.
assert_lfs_materialized = assert_materialized


def _resolved_protected_roots(source_root: Union[str, Path]) -> List[Path]:
    anchor = Path.cwd().anchor
    roots = [
        Path.cwd(),
        Path.home(),
        Path(tempfile.gettempdir()),
        Path(source_root),
    ]
    if anchor:
        roots.append(Path(anchor))
    protected = set()
    for item in roots:
        resolved = item.expanduser().resolve()
        protected.add(resolved)
        protected.update(resolved.parents)
    return list(protected)


def prepare_output_root(
    output_root: Union[str, Path],
    *,
    overwrite: bool,
    source_root: Union[str, Path],
) -> Path:
    """Create an output root, removing only workflow-owned files on overwrite."""

    target = Path(output_root).expanduser().resolve()
    protected = _resolved_protected_roots(source_root)
    if target in protected:
        raise ValueError(f"refusing to use protected output root: {target}")

    if target.exists():
        if not target.is_dir():
            raise FileExistsError(f"output root is not a directory: {target}")
        if not overwrite:
            raise FileExistsError(
                f"output root already exists; pass --overwrite: {target}"
            )
        for name in OWNED_OUTPUT_NAMES:
            owned_path = target / name
            if owned_path.is_symlink() or owned_path.is_file():
                owned_path.unlink()
            elif owned_path.exists():
                raise IsADirectoryError(
                    f"workflow-owned output name is a directory: {owned_path}"
                )
    else:
        target.mkdir(parents=True)
    return target


def resolve_executable(build_dir: Union[str, Path], name: str) -> Path:
    """Resolve a single- or multi-configuration benchmark executable."""

    build_root = Path(build_dir).expanduser().resolve()
    base_names = (name, f"{name}.exe")
    relative_directories = (
        Path("bin"),
        Path("bin") / "Release",
        Path("Release"),
        Path("bin") / "RelWithDebInfo",
        Path("RelWithDebInfo"),
        Path("bin") / "Debug",
        Path("Debug"),
    )
    candidates = [
        build_root / directory / base_name
        for directory in relative_directories
        for base_name in base_names
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"executable {name!r} not found; searched: {searched}")


def _is_full_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value) is not None


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def formal_preflight_blockers(context: Mapping[str, object]) -> List[str]:
    """Return every reason that a run cannot be accepted as formal evidence."""

    if context.get("evidence_level") != "formal":
        return []

    blockers: List[str] = []
    if context.get("case") != "windhub":
        blockers.append("formal evidence requires the materialized WindHub case")
    if context.get("report_intent") != "delivery":
        blockers.append("formal evidence requires delivery report intent")
    if context.get("system") != "Linux":
        blockers.append("formal evidence requires Linux")
    if context.get("architecture") != "x86_64":
        blockers.append("formal evidence requires Linux x86_64 architecture")
    vendor = str(context.get("cpu_vendor") or "")
    if "intel" not in vendor.lower():
        blockers.append("formal evidence requires an Intel CPU")
    if not str(context.get("controlled_host_id") or "").strip():
        blockers.append("formal evidence requires a controlled host identifier")
    if context.get("source_dirty_at_start") is not False:
        blockers.append("formal evidence requires a clean Git worktree")
    if not _is_full_sha(context.get("commit_sha")):
        blockers.append("formal evidence requires a full commit SHA")

    if context.get("input_is_materialized") is not True:
        blockers.append("formal evidence requires materialized WindHub input")
    if context.get("input_is_tracked") is not True:
        blockers.append("formal evidence requires a tracked WindHub input")
    if context.get("input_matches_head_lfs") is not True:
        blockers.append("formal evidence requires input matching the HEAD LFS object")
    if not _is_sha256(context.get("input_sha256")):
        blockers.append("formal evidence requires a valid input SHA-256")
    input_size = context.get("input_size_bytes")
    if not isinstance(input_size, int) or isinstance(input_size, bool) or input_size <= 0:
        blockers.append("formal evidence requires a positive input size")

    warmups = context.get("warmup_count")
    if not isinstance(warmups, int) or isinstance(warmups, bool) or warmups < 2:
        blockers.append("formal evidence requires at least 2 warmups")
    repeats = context.get("repeat_count")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 7:
        blockers.append("formal evidence requires at least 7 measured repeats")

    requested_raw = context.get("requested_thread_counts")
    requested = list(requested_raw) if isinstance(requested_raw, (list, tuple)) else []
    valid_requested = [
        value
        for value in requested
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    ]
    canonical_threads = {1, 2, 4, 8, 16}
    if (
        len(valid_requested) != len(requested)
        or len(set(valid_requested)) != len(valid_requested)
        or not canonical_threads.issubset(set(valid_requested))
    ):
        blockers.append("formal evidence requires thread counts 1, 2, 4, 8, and 16")
    physical = context.get("physical_core_count")
    if not isinstance(physical, int) or isinstance(physical, bool) or physical <= 0:
        blockers.append("formal evidence requires a positive physical-core count")
    elif physical not in valid_requested:
        blockers.append("formal evidence thread scan must include the physical-core count")

    binding = context.get("binding_environment")
    if not isinstance(binding, Mapping) or any(
        binding.get(name) != expected
        for name, expected in REQUIRED_OPENMP_ENV.items()
    ):
        blockers.append("formal evidence requires the fixed OpenMP binding environment")
    return blockers


def artifact_records(
    output_root: Union[str, Path], paths: Iterable[Union[str, Path]]
) -> List[Dict[str, object]]:
    """Describe artifacts with root-relative paths, sizes, and SHA-256 hashes."""

    root = Path(output_root).expanduser().resolve()
    records: List[Dict[str, object]] = []
    for raw_path in paths:
        artifact = Path(raw_path).expanduser().resolve()
        try:
            relative = artifact.relative_to(root)
        except ValueError as error:
            raise ValueError(f"artifact escapes output root: {artifact}") from error
        if relative == Path(".") or not artifact.is_file():
            raise FileNotFoundError(f"artifact is not a regular file: {artifact}")
        records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(artifact),
                "size_bytes": artifact.stat().st_size,
            }
        )
    return records


def validate_observed_teams(
    benchmark_summary: Mapping[str, object], requested_thread_counts: Sequence[int]
) -> List[int]:
    """Require one measured row and exact OpenMP teams for every request."""

    rows = benchmark_summary.get("per_thread_measured_statistics")
    if not isinstance(rows, list):
        raise RuntimeError("benchmark summary has no observed thread statistics")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in requested_thread_counts
    ):
        raise ValueError("requested thread counts must be unique positive integers")
    requested = list(requested_thread_counts)
    if len(requested) != len(set(requested)):
        raise ValueError("requested thread counts must be unique positive integers")

    by_thread: Dict[int, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("benchmark summary contains an invalid observed row")
        thread_count = row.get("thread_count")
        if not isinstance(thread_count, int) or isinstance(thread_count, bool):
            raise RuntimeError("benchmark summary contains an invalid observed thread count")
        if thread_count in by_thread:
            raise RuntimeError(f"duplicate observed statistics for {thread_count} threads")
        by_thread[thread_count] = row

    if set(by_thread) != set(requested):
        raise RuntimeError(
            "observed thread configurations do not exactly match requested thread counts"
        )
    for thread_count in requested:
        row = by_thread[thread_count]
        symbolic = row.get("symbolic_thread_count_observed")
        numeric = row.get("numeric_thread_count_observed")
        if symbolic != thread_count or numeric != thread_count:
            raise RuntimeError(
                "observed OpenMP team does not match requested thread count "
                f"{thread_count}: symbolic={symbolic!r}, numeric={numeric!r}"
            )
    return requested


def derive_run_status(
    *,
    evidence_level: str,
    report_intent: str,
    benchmark_summary: Mapping[str, object],
    command_failed: bool,
) -> Tuple[str, List[str]]:
    """Derive a conservative status without upgrading smoke data to delivery proof."""

    if command_failed:
        return "FAIL", ["one or more workflow commands failed"]

    correctness = benchmark_summary.get("correctness")
    correctness_status = (
        correctness.get("status") if isinstance(correctness, Mapping) else None
    )
    if correctness_status != "PASS":
        return "FAIL", ["benchmark correctness evidence did not pass"]

    if evidence_level != "formal":
        blocker = "formal controlled-host evidence was not produced"
        if report_intent == "delivery":
            return "BLOCKED", [blocker]
        return "LOCAL_SMOKE", [blocker]

    if report_intent != "delivery":
        return "BLOCKED", ["formal evidence requires delivery report intent"]
    gate = benchmark_summary.get("performance_gate")
    if not isinstance(gate, Mapping):
        return "FAIL", ["formal benchmark performance gate is missing"]
    if gate.get("status") == "PASS" and gate.get("performance_requirements_met") is True:
        return "PASS", []
    return "FAIL", ["formal benchmark performance requirements were not met"]


def _format_float(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            return f"{number:.6g}"
    return "N/A"


def _safe_command_text(command: object) -> str:
    """Render a command without retaining host-specific absolute paths."""

    if not isinstance(command, (list, tuple)):
        return "N/A"
    safe_parts: List[str] = []
    for raw_part in command:
        part = str(raw_part)
        option_prefix = ""
        value = part
        if "=" in part and part.startswith("-"):
            option_prefix, value = part.split("=", 1)
            option_prefix += "="
        is_windows_absolute = re.match(r"^[A-Za-z]:[\\/]", value) is not None
        if Path(value).is_absolute() or is_windows_absolute:
            normalized = value.replace("\\", "/").rstrip("/")
            leaf = normalized.rsplit("/", 1)[-1] or "root"
            value = f"<host-path>/{leaf}"
        safe_parts.append(shlex.quote(option_prefix + value))
    return " ".join(safe_parts)


def render_markdown_summary(
    manifest: Mapping[str, object],
    benchmark_summary: Mapping[str, object],
    samples_csv_path: Union[str, Path],
) -> str:
    """Render a path-independent human summary from structured evidence."""

    evidence_level = str(manifest.get("evidence_level", "unknown"))
    status = str(manifest.get("status", "UNKNOWN"))
    non_formal = evidence_level != "formal"
    lines: List[str] = ["# CSC3 Demo Benchmark Summary", ""]
    if non_formal:
        lines.extend([f"> **{NON_FORMAL_WARNING}**", ""])

    case_sizes = benchmark_summary.get("case_sizes")
    case_sizes = case_sizes if isinstance(case_sizes, Mapping) else {}
    correctness = benchmark_summary.get("correctness")
    correctness = correctness if isinstance(correctness, Mapping) else {}
    environment = manifest.get("environment")
    environment = environment if isinstance(environment, Mapping) else {}
    toolchain = manifest.get("toolchain")
    toolchain = toolchain if isinstance(toolchain, Mapping) else {}
    input_facts = manifest.get("input")
    input_facts = input_facts if isinstance(input_facts, Mapping) else {}
    lines.extend(
        [
            "## Run classification",
            "",
            f"- Status: `{status}`",
            f"- Evidence level: `{evidence_level}`",
            f"- Case: `{case_sizes.get('case_name', 'unknown')}`",
            "",
            "## Environment",
            "",
            f"- System: `{environment.get('system', 'unknown')}`",
            f"- Architecture: `{environment.get('architecture', 'unknown')}`",
            f"- CPU vendor: `{environment.get('cpu_vendor', 'unknown')}`",
            f"- CPU model: `{environment.get('cpu_model', 'unknown')}`",
            f"- Physical cores: `{environment.get('physical_core_count', 'unknown')}`",
            f"- Compiler: `{toolchain.get('compiler', 'unknown')}`",
            f"- CMake: `{toolchain.get('cmake_version', 'unknown')}`",
            "",
            "## Input",
            "",
            f"- Case selector: `{input_facts.get('case', 'unknown')}`",
            f"- Grid: `{input_facts.get('grid', 'not applicable')}`",
            f"- Input size bytes: `{input_facts.get('size_bytes', 'not recorded')}`",
            f"- Input SHA-256: `{input_facts.get('sha256', 'not recorded')}`",
            "",
            "## Commands",
            "",
        ]
    )
    commands = manifest.get("commands")
    if isinstance(commands, Mapping):
        for name, command in commands.items():
            lines.append(f"- `{name}`: `{_safe_command_text(command)}`")
    else:
        lines.append("- No commands were recorded.")
    lines.extend(
        [
            "",
            "## Correctness",
            "",
            f"- Status: `{correctness.get('status', 'UNKNOWN')}`",
            "- Relative Frobenius error: "
            + _format_float(correctness.get("relative_frobenius_error")),
            "- Maximum absolute error: "
            + _format_float(correctness.get("max_absolute_error")),
            "",
            "## Performance evidence",
            "",
            "| Threads | Symbolic median (ms) | Symbolic CV | Numeric median (ms) | "
            "Numeric CV | Amortized median (ms) | Amortized CV | Symbolic speedup | "
            "Numeric speedup |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    rows = benchmark_summary.get("per_thread_measured_statistics")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            symbolic = row.get("symbolic_total_ms")
            numeric = row.get("numeric_algorithm_ms")
            amortized = row.get("amortized_total_ms")
            symbolic = symbolic if isinstance(symbolic, Mapping) else {}
            numeric = numeric if isinstance(numeric, Mapping) else {}
            amortized = amortized if isinstance(amortized, Mapping) else {}
            lines.append(
                "| {threads} | {symbolic} | {symbolic_cv} | {numeric} | "
                "{numeric_cv} | {amortized} | {amortized_cv} | {symbolic_speedup} | "
                "{numeric_speedup} |".format(
                    threads=row.get("thread_count", "N/A"),
                    symbolic=_format_float(symbolic.get("median_ms")),
                    symbolic_cv=_format_float(
                        symbolic.get("coefficient_of_variation")
                    ),
                    numeric=_format_float(numeric.get("median_ms")),
                    numeric_cv=_format_float(numeric.get("coefficient_of_variation")),
                    amortized=_format_float(amortized.get("median_ms")),
                    amortized_cv=_format_float(
                        amortized.get("coefficient_of_variation")
                    ),
                    symbolic_speedup=_format_float(row.get("symbolic_speedup")),
                    numeric_speedup=_format_float(row.get("numeric_speedup")),
                )
            )
    gate = benchmark_summary.get("performance_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    lines.extend(
        [
            "",
            "## Performance gate",
            "",
            f"- Status: `{gate.get('status', 'UNKNOWN')}`",
            "- Applicable: `" + str(gate.get("applicable", False)) + "`",
            "- Performance requirements met: `"
            + str(gate.get("performance_requirements_met", False))
            + "`",
            "",
            "## Memory and artifacts",
            "",
            "- estimated persistent bytes: "
            + str(benchmark_summary.get("estimated_persistent_bytes", "N/A")),
            "- Memory meaning: owned vector payload estimate, not RSS.",
            "- [benchmark_samples.csv](benchmark_samples.csv)",
            "- [benchmark_summary.json](benchmark_summary.json)",
            "- [ctest.xml](ctest.xml)",
            "- [run_manifest.json](run_manifest.json)",
            "",
            "## Limits and blockers",
            "",
        ]
    )
    blockers = manifest.get("blockers")
    if isinstance(blockers, list) and blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- None recorded.")
    lines.append("")
    if non_formal:
        lines.extend([f"> **{NON_FORMAL_WARNING}**", ""])
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the stable command-line contract for the evidence workflow."""

    demo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=("generated-tet4", "generated-hex8", "windhub"),
        default="generated-tet4",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--nx", type=int, default=1)
    parser.add_argument("--ny", type=int, default=1)
    parser.add_argument("--nz", type=int, default=1)
    parser.add_argument("--source-dir", type=Path, default=demo_root)
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--threads-list", default="1,2")
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--amortization-count", type=int, default=1)
    parser.add_argument(
        "--evidence-level",
        choices=("ci-smoke", "local-smoke", "formal"),
        default="local-smoke",
    )
    parser.add_argument("--preset", default="delivery")
    parser.add_argument(
        "--report-intent", choices=("local-smoke", "delivery"), default="local-smoke"
    )
    parser.add_argument("--controlled-host-id")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run_workflow(
    arguments: Optional[Sequence[str]] = None,
    *,
    command_runner: Optional[object] = None,
) -> int:
    """Validate workflow inputs; subprocess orchestration is implemented separately."""

    options = build_argument_parser().parse_args(arguments)
    source_root = options.source_dir.expanduser().resolve()
    if options.case == "windhub":
        if options.input is None:
            raise ValueError("WindHub case requires --input")
        assert_materialized(options.input)
    if options.dry_run:
        return 0
    raise NotImplementedError(
        "benchmark subprocess orchestration is not part of the contract-only stage"
    )


def main() -> int:
    return run_workflow()


if __name__ == "__main__":
    raise SystemExit(main())
