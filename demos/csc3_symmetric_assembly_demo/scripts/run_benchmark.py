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
import json
import math
import os
import platform
import re
import shlex
import socket
import subprocess
import tempfile
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone
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
CANONICAL_WINDHUB_REPOSITORY_PATH = "examples/3d-WindTurbineHub.inp"
DOUBLE_EPSILON = float.fromhex("0x1.0000000000000p-52")
MAXIMUM_ABSOLUTE_BASE_TOLERANCE = 1.0e-10
MAXIMUM_ABSOLUTE_SCALE_TOLERANCE = 1.0e-8


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


def _cmake_bracket_close(text: str, index: int) -> Optional[Tuple[int, str]]:
    match = re.match(r"\[(=*)\[", text[index:])
    if match is None:
        return None
    return match.end(), "]" + match.group(1) + "]"


def _cmake_without_comments(text: str) -> str:
    """Blank CMake comments while retaining strings and bracket arguments."""

    result = list(text)
    index = 0
    quoted = False
    while index < len(text):
        if quoted:
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == '"':
                quoted = False
            index += 1
            continue
        if text[index] == '"':
            quoted = True
            index += 1
            continue
        bracket = _cmake_bracket_close(text, index)
        if bracket is not None:
            opening_length, closing = bracket
            closing_index = text.find(closing, index + opening_length)
            index = len(text) if closing_index < 0 else closing_index + len(closing)
            continue
        if text[index] != "#":
            index += 1
            continue
        bracket = _cmake_bracket_close(text, index + 1)
        if bracket is None:
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
        else:
            opening_length, closing = bracket
            closing_index = text.find(closing, index + 1 + opening_length)
            end = len(text) if closing_index < 0 else closing_index + len(closing)
        for position in range(index, end):
            if result[position] != "\n":
                result[position] = " "
        index = end
    return "".join(result)


def _cmake_project_arguments(text: str) -> List[str]:
    """Return balanced project command bodies from comment-free CMake text."""

    projects: List[str] = []
    command_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    cursor = 0
    while cursor < len(text):
        if text[cursor].isspace() or text[cursor] == ";":
            cursor += 1
            continue
        bracket = _cmake_bracket_close(text, cursor)
        if bracket is not None:
            opening_length, closing = bracket
            closing_index = text.find(closing, cursor + opening_length)
            cursor = len(text) if closing_index < 0 else closing_index + len(closing)
            continue
        if text[cursor] == '"':
            cursor += 1
            while cursor < len(text):
                if text[cursor] == "\\":
                    cursor += 2
                elif text[cursor] == '"':
                    cursor += 1
                    break
                else:
                    cursor += 1
            continue
        command = command_pattern.match(text, cursor)
        if command is None:
            cursor += 1
            continue
        open_parenthesis = command.end()
        while open_parenthesis < len(text) and text[open_parenthesis].isspace():
            open_parenthesis += 1
        if open_parenthesis >= len(text) or text[open_parenthesis] != "(":
            cursor = command.end()
            continue
        start = open_parenthesis + 1
        index = start
        depth = 1
        quoted = False
        while index < len(text) and depth:
            if quoted:
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == '"':
                    quoted = False
                index += 1
                continue
            if text[index] == '"':
                quoted = True
                index += 1
                continue
            bracket = _cmake_bracket_close(text, index)
            if bracket is not None:
                opening_length, closing = bracket
                closing_index = text.find(closing, index + opening_length)
                index = len(text) if closing_index < 0 else closing_index + len(closing)
                continue
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
                if depth == 0:
                    if command.group(0).lower() == "project":
                        projects.append(text[start:index])
                    break
            index += 1
        cursor = index + 1
    return projects


def _cmake_arguments(text: str) -> List[str]:
    """Tokenize the limited project arguments needed by the version contract."""

    tokens: List[str] = []
    index = 0
    while index < len(text):
        while index < len(text) and (text[index].isspace() or text[index] == ";"):
            index += 1
        if index >= len(text):
            break
        if text[index] == '"':
            start = index
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                elif text[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            tokens.append(text[start:index])
            continue
        bracket = _cmake_bracket_close(text, index)
        if bracket is not None:
            opening_length, closing = bracket
            closing_index = text.find(closing, index + opening_length)
            end = len(text) if closing_index < 0 else closing_index + len(closing)
            tokens.append(text[index:end])
            index = end
            continue
        start = index
        while index < len(text) and not text[index].isspace() and text[index] != ";":
            index += 1
        tokens.append(text[start:index])
    return tokens


def _read_project_version(source_root: Union[str, Path]) -> str:
    """Read one strict major.minor.patch version from the CMake project call."""

    cmake_path = Path(source_root).expanduser().resolve() / "CMakeLists.txt"
    try:
        text = cmake_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RuntimeError(f"cannot read source CMake project declaration: {error}") from error
    projects = _cmake_project_arguments(_cmake_without_comments(text))
    matching_projects = []
    for project in projects:
        tokens = _cmake_arguments(project)
        if tokens and tokens[0].lower() == "csc3symmetricassemblydemo":
            matching_projects.append(tokens)
    if len(matching_projects) != 1:
        raise RuntimeError(
            "source CMakeLists.txt must contain exactly one "
            "Csc3SymmetricAssemblyDemo project declaration"
        )
    tokens = matching_projects[0]
    version_positions = [
        index for index, token in enumerate(tokens) if token.upper() == "VERSION"
    ]
    if len(version_positions) != 1 or version_positions[0] + 1 >= len(tokens):
        raise RuntimeError("source CMake project declaration has no unambiguous VERSION")
    version = tokens[version_positions[0] + 1]
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise RuntimeError("source CMake project VERSION must be major.minor.patch")
    return version


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


def _repository_dirty_output(
    repository_root: Union[str, Path],
    owned_output_root: Optional[Union[str, Path]] = None,
) -> str:
    """Return Git porcelain state, excluding only one runner-owned output root."""

    repository = Path(repository_root).expanduser().resolve()
    command = [
        "git",
        "-C",
        str(repository),
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
    ]
    if owned_output_root is not None:
        output = Path(owned_output_root).expanduser().resolve()
        try:
            relative_output = output.relative_to(repository)
        except ValueError:
            relative_output = None
        if relative_output is not None and relative_output.parts:
            command.append(
                ":(exclude,top,literal)" + relative_output.as_posix()
            )
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.strip() or "git status failed"
        return "GIT_STATUS_ERROR: " + diagnostic
    return completed.stdout.strip()


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
    if str(context.get("architecture") or "").lower() not in {"x86_64", "amd64"}:
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
    if context.get("input_repository_relative_path") != CANONICAL_WINDHUB_REPOSITORY_PATH:
        blockers.append(
            "formal evidence requires the canonical tracked WindHub input path"
        )
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
    if "openmp_found" in context and context.get("openmp_found") is not True:
        blockers.append("formal evidence requires detected OpenMP support")
    if "openmp_required" in context and context.get("openmp_required") is not True:
        blockers.append("formal evidence requires the OpenMP-required delivery build")
    cmake_version = str(context.get("cmake_version") or "").strip()
    if not cmake_version or cmake_version.lower() == "unknown":
        blockers.append("formal evidence requires an identified CMake version")
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


def _mean_within_sample_range(
    mean: float, minimum: float, maximum: float, sample_count: int
) -> bool:
    """Accept only accumulation roundoff beyond the closed sample range.

    The C++ producer accumulates in ``long double``.  On platforms where that
    type is binary64, the additions and final division can place the rounded
    mean a few ULPs beyond an endpoint even though the exact mean is inside the
    interval.  The standard ``gamma_k`` bound below budgets one binary64
    rounding per sample plus the division; an endpoint ULP covers the final
    representable-value rounding at zero and other binade boundaries.
    """

    if minimum <= mean <= maximum:
        return True
    unit_roundoff = DOUBLE_EPSILON / 2.0
    operation_count = sample_count + 1
    if operation_count >= int(1.0 / unit_roundoff):
        return False
    accumulated_roundoff = operation_count * unit_roundoff
    relative_bound = accumulated_roundoff / (1.0 - accumulated_roundoff)
    scale = max(abs(minimum), abs(maximum))
    tolerance = max(
        math.ulp(minimum),
        math.ulp(maximum),
        relative_bound * scale,
    )
    endpoint = minimum if mean < minimum else maximum
    return abs(mean - endpoint) <= tolerance


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
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        lines.extend(["## Evidence hashes", ""])
        for artifact in artifacts:
            if isinstance(artifact, Mapping):
                lines.append(
                    "- `{path}`: `{digest}` ({size} bytes)".format(
                        path=artifact.get("path", "unknown"),
                        digest=artifact.get("sha256", "unknown"),
                        size=artifact.get("size_bytes", "unknown"),
                    )
                )
        lines.append("")
    return "\n".join(lines)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    """Atomically replace a UTF-8 JSON file in its destination directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary_path), str(path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _parse_thread_counts(text: str) -> List[int]:
    if not text or text.strip() != text:
        raise ValueError("--threads-list must be a comma-separated list")
    parts = text.split(",")
    if any(not re.fullmatch(r"[1-9][0-9]*", part) for part in parts):
        raise ValueError("--threads-list must contain positive decimal integers")
    values = [int(part) for part in parts]
    if len(values) != len(set(values)):
        raise ValueError("--threads-list must contain unique values")
    return values


def _default_command_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    merged_environment = os.environ.copy()
    merged_environment.update({str(key): str(value) for key, value in environment.items()})
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd),
        env=merged_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _output_excerpt(text: str, limit: int = 4000) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "\n<output truncated>"


def _task_record(
    name: str,
    command: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    result: CommandResult,
    *,
    validation_error: Optional[str] = None,
) -> Dict[str, object]:
    failed = result.returncode != 0 or validation_error is not None
    error = validation_error
    if error is None and result.returncode != 0:
        error = _output_excerpt(result.stderr.strip() or result.stdout.strip())
        if not error:
            error = f"command exited with status {result.returncode}"
    return {
        "name": name,
        "command": [str(part) for part in command],
        "cwd": str(cwd),
        "environment": dict(environment),
        "returncode": result.returncode,
        "exit_code": result.returncode,
        "status": "FAIL" if failed else "PASS",
        "stdout": _output_excerpt(result.stdout),
        "stderr": _output_excerpt(result.stderr),
        "error": error,
    }


def validate_ctest_junit(path: Union[str, Path]) -> Dict[str, int]:
    """Require a non-empty JUnit result with no failed or unrun tests."""

    junit_path = Path(path)
    if not junit_path.is_file():
        raise RuntimeError(f"CTest JUnit output is missing: {junit_path}")
    try:
        root = ElementTree.parse(str(junit_path)).getroot()
    except ElementTree.ParseError as error:
        raise RuntimeError(f"CTest JUnit output is invalid XML: {error}") from error
    nodes = [root] + list(root.iter())

    def total_attribute(name: str) -> int:
        values: List[int] = []
        for node in nodes:
            raw = node.attrib.get(name)
            if raw is None:
                continue
            try:
                value = int(raw)
            except ValueError as error:
                raise RuntimeError(f"CTest JUnit has invalid {name!r} count") from error
            if value < 0:
                raise RuntimeError(f"CTest JUnit has negative {name!r} count")
            values.append(value)
        return max(values, default=0)

    test_cases = list(root.iter("testcase"))
    if not test_cases:
        raise RuntimeError("CTest JUnit contains no testcase elements")
    declared_tests = root.attrib.get("tests")
    if declared_tests is None:
        raise RuntimeError("CTest JUnit root has no declared test count")
    try:
        tests = int(declared_tests)
    except ValueError as error:
        raise RuntimeError("CTest JUnit has an invalid declared test count") from error
    if tests != len(test_cases):
        raise RuntimeError(
            "CTest JUnit declared test count does not match testcase elements"
        )
    failures = max(total_attribute("failures"), len(list(root.iter("failure"))))
    errors = max(total_attribute("errors"), len(list(root.iter("error"))))
    skipped = max(
        total_attribute("skipped"),
        total_attribute("disabled"),
        len(list(root.iter("skipped"))),
    )
    not_run = 0
    for test_case in test_cases:
        state = " ".join(
            str(test_case.attrib.get(name, ""))
            for name in ("status", "result")
        ).strip().lower()
        if state in {"notrun", "not run", "skipped", "disabled"}:
            not_run += 1
    if failures or errors or skipped or not_run:
        raise RuntimeError(
            "CTest JUnit is not clean: "
            f"tests={tests}, failures={failures}, errors={errors}, "
            f"skipped={skipped}, not_run={not_run}"
        )
    return {
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "not_run": not_run,
    }


def _validate_benchmark_summary(
    path: Union[str, Path],
    requested_thread_counts: Sequence[int],
    expected_evidence_level: Optional[str] = None,
    expected_configuration: Optional[Mapping[str, object]] = None,
) -> Tuple[Dict[str, object], List[int]]:
    summary_path = Path(path)
    if not summary_path.is_file():
        raise RuntimeError(f"benchmark summary is missing: {summary_path}")
    try:
        parsed = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"benchmark summary is invalid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("benchmark summary root must be an object")
    if parsed.get("schema_version") != "csc3-demo-benchmark-v1":
        raise RuntimeError("benchmark summary schema_version is unsupported")
    evidence_level = parsed.get("performance_evidence_level")
    if evidence_level not in {"ci-smoke", "local-smoke", "formal"}:
        raise RuntimeError("benchmark performance_evidence_level is missing or invalid")
    if expected_evidence_level is not None and evidence_level != expected_evidence_level:
        raise RuntimeError(
            "benchmark performance_evidence_level does not match the workflow request"
        )
    configuration = parsed.get("configuration")
    if not isinstance(configuration, Mapping):
        raise RuntimeError("benchmark configuration object is missing")
    if configuration.get("performance_evidence_level") != evidence_level:
        raise RuntimeError("benchmark configuration evidence level disagrees")
    if configuration.get("thread_counts") != list(requested_thread_counts):
        raise RuntimeError("benchmark configuration thread counts disagree")
    if expected_configuration is not None:
        for key, expected in expected_configuration.items():
            if configuration.get(key) != expected:
                raise RuntimeError(
                    f"benchmark configuration field {key!r} disagrees with the workflow request"
                )
    case_sizes = parsed.get("case_sizes")
    if not isinstance(case_sizes, Mapping):
        raise RuntimeError("benchmark case_sizes object is missing")
    for key in ("node_count", "element_count", "dof_count", "nnz"):
        value = case_sizes.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise RuntimeError(f"benchmark case size {key!r} is invalid")
    correctness = parsed.get("correctness")
    if not isinstance(correctness, Mapping):
        raise RuntimeError("benchmark correctness object is missing")
    if correctness.get("status") != "PASS" or correctness.get("structure_matches") is not True:
        raise RuntimeError("benchmark matrix correctness did not pass")
    for key in (
        "relative_frobenius_error",
        "max_absolute_error",
        "reference_max_absolute_value",
        "max_absolute_tolerance",
    ):
        value = correctness.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) < 0.0
        ):
            raise RuntimeError(f"benchmark correctness field {key!r} is invalid")
    if float(correctness["relative_frobenius_error"]) > 1.0e-8:
        raise RuntimeError("benchmark relative Frobenius error exceeds its contract")
    expected_max_absolute_tolerance = (
        MAXIMUM_ABSOLUTE_BASE_TOLERANCE
        + MAXIMUM_ABSOLUTE_SCALE_TOLERANCE
        * float(correctness["reference_max_absolute_value"])
    )
    recorded_max_absolute_tolerance = float(
        correctness["max_absolute_tolerance"]
    )
    tolerance_scale = max(
        1.0,
        abs(expected_max_absolute_tolerance),
        abs(recorded_max_absolute_tolerance),
    )
    if abs(
        recorded_max_absolute_tolerance - expected_max_absolute_tolerance
    ) > 64.0 * DOUBLE_EPSILON * tolerance_scale:
        raise RuntimeError(
            "benchmark maximum absolute tolerance disagrees with reference scale"
        )
    if float(correctness["max_absolute_error"]) > float(
        correctness["max_absolute_tolerance"]
    ):
        raise RuntimeError("benchmark maximum absolute error exceeds its tolerance")

    if parsed.get("validation_cases_schema_version") != "csc3-demo-validation-v1":
        raise RuntimeError("benchmark validation cases schema is missing or invalid")
    validation_thresholds = parsed.get("validation_thresholds")
    if not isinstance(validation_thresholds, Mapping):
        raise RuntimeError("benchmark validation thresholds are missing")
    expected_validation_thresholds = {
        "relative_frobenius_error_max": 1.0e-8,
        "relative_displacement_error_max": 1.0e-8,
        "relative_residual_max": 1.0e-10,
    }
    for key, expected in expected_validation_thresholds.items():
        value = validation_thresholds.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or float(value) != expected
        ):
            raise RuntimeError(
                f"benchmark validation threshold {key!r} is invalid"
            )

    validation_cases = parsed.get("validation_cases")
    if not isinstance(validation_cases, list) or len(validation_cases) != 2:
        raise RuntimeError(
            "benchmark validation evidence must contain exactly Tet4 and Hex8 cases"
        )
    selected_validation_thread = 1
    if 2 in requested_thread_counts:
        selected_validation_thread = 2
    else:
        selected_validation_thread = next(
            (thread for thread in requested_thread_counts if thread > 1), 1
        )
    expected_validation_cases = (
        ("cube_tet4_1x1x1", "Tet4", 6),
        ("cube_hex8_1x1x1", "Hex8", 1),
    )

    def validation_metric(
        container: Mapping[str, object], key: str, label: str
    ) -> float:
        value = container.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) < 0.0
        ):
            raise RuntimeError(
                f"benchmark validation {label} metric {key!r} is invalid"
            )
        return float(value)

    for validation, expected in zip(
        validation_cases, expected_validation_cases
    ):
        if not isinstance(validation, Mapping):
            raise RuntimeError("benchmark validation case must be an object")
        expected_name, expected_element_type, expected_element_count = expected
        for key, expected_value in (
            ("case_name", expected_name),
            ("element_type", expected_element_type),
        ):
            if validation.get(key) != expected_value:
                raise RuntimeError(
                    f"benchmark validation case field {key!r} is invalid"
                )
        expected_sizes = {
            "node_count": 8,
            "element_count": expected_element_count,
            "dof_count": 24,
            "thread_count": selected_validation_thread,
        }
        for key, expected_value in expected_sizes.items():
            value = validation.get(key)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value != expected_value
            ):
                raise RuntimeError(
                    f"benchmark validation case field {key!r} is invalid"
                )
        if validation.get("status") != "PASS":
            raise RuntimeError("benchmark validation case status is not PASS")

        matrix = validation.get("matrix")
        if not isinstance(matrix, Mapping):
            raise RuntimeError("benchmark validation matrix evidence is missing")
        if matrix.get("structure_matches") is not True or matrix.get("status") != "PASS":
            raise RuntimeError("benchmark validation matrix status is not PASS")
        relative_frobenius_error = validation_metric(
            matrix, "relative_frobenius_error", "matrix"
        )
        max_absolute_error = validation_metric(
            matrix, "max_absolute_error", "matrix"
        )
        reference_max_absolute_value = validation_metric(
            matrix, "reference_max_absolute_value", "matrix"
        )
        max_absolute_tolerance = validation_metric(
            matrix, "max_absolute_tolerance", "matrix"
        )
        expected_max_absolute_tolerance = (
            MAXIMUM_ABSOLUTE_BASE_TOLERANCE
            + MAXIMUM_ABSOLUTE_SCALE_TOLERANCE
            * reference_max_absolute_value
        )
        tolerance_scale = max(
            1.0,
            abs(expected_max_absolute_tolerance),
            abs(max_absolute_tolerance),
        )
        if abs(
            max_absolute_tolerance - expected_max_absolute_tolerance
        ) > 64.0 * DOUBLE_EPSILON * tolerance_scale:
            raise RuntimeError(
                "benchmark validation maximum absolute tolerance "
                "disagrees with reference scale"
            )
        if relative_frobenius_error > 1.0e-8:
            raise RuntimeError(
                "benchmark validation relative Frobenius error exceeds its contract"
            )
        if max_absolute_error > max_absolute_tolerance:
            raise RuntimeError(
                "benchmark validation maximum absolute error exceeds its tolerance"
            )

        displacement = validation.get("displacement")
        if not isinstance(displacement, Mapping):
            raise RuntimeError(
                "benchmark validation displacement evidence is missing"
            )
        if displacement.get("status") != "PASS":
            raise RuntimeError(
                "benchmark validation displacement status is not PASS"
            )
        relative_displacement_error = validation_metric(
            displacement, "relative_displacement_error", "displacement"
        )
        parallel_relative_residual = validation_metric(
            displacement, "parallel_relative_residual", "displacement"
        )
        serial_relative_residual = validation_metric(
            displacement, "serial_relative_residual", "displacement"
        )
        parallel_displacement_norm = validation_metric(
            displacement, "parallel_displacement_norm", "displacement"
        )
        serial_displacement_norm = validation_metric(
            displacement, "serial_displacement_norm", "displacement"
        )
        if relative_displacement_error > 1.0e-8:
            raise RuntimeError(
                "benchmark validation displacement error exceeds its contract"
            )
        if (
            parallel_relative_residual > 1.0e-10
            or serial_relative_residual > 1.0e-10
        ):
            raise RuntimeError(
                "benchmark validation relative residual exceeds its contract"
            )
        if parallel_displacement_norm <= 0.0 or serial_displacement_norm <= 0.0:
            raise RuntimeError(
                "benchmark validation displacement norm must be positive"
            )

    persistent_bytes = parsed.get("estimated_persistent_bytes")
    if (
        not isinstance(persistent_bytes, int)
        or isinstance(persistent_bytes, bool)
        or persistent_bytes < 0
    ):
        raise RuntimeError("benchmark estimated_persistent_bytes is invalid")
    if parsed.get("estimated_persistent_memory_kind") != "owned_vector_payload_bytes_not_rss":
        raise RuntimeError("benchmark persistent-memory meaning is missing or invalid")
    gate = parsed.get("performance_gate")
    if not isinstance(gate, Mapping):
        raise RuntimeError("benchmark performance_gate object is missing")
    gate_status = gate.get("status")
    if not isinstance(gate_status, str) or not gate_status:
        raise RuntimeError("benchmark performance gate status is missing")
    if not isinstance(gate.get("applicable"), bool) or not isinstance(
        gate.get("performance_requirements_met"), bool
    ):
        raise RuntimeError("benchmark performance gate booleans are invalid")
    if parsed.get("performance_gate_status") != gate_status:
        raise RuntimeError("benchmark performance gate status fields disagree")
    observed = validate_observed_teams(parsed, requested_thread_counts)

    rows = parsed["per_thread_measured_statistics"]
    assert isinstance(rows, list)
    repeat_count = configuration.get("repeat_count")
    if (
        not isinstance(repeat_count, int)
        or isinstance(repeat_count, bool)
        or repeat_count <= 0
    ):
        raise RuntimeError("benchmark repeat_count is invalid")

    def validate_statistics(statistics: object, label: str) -> Mapping[str, object]:
        if not isinstance(statistics, Mapping):
            raise RuntimeError(f"benchmark {label} statistics are missing")
        if statistics.get("sample_count") != repeat_count:
            raise RuntimeError(f"benchmark {label} sample_count is inconsistent")
        numeric_keys = (
            "mean_ms", "median_ms", "population_standard_deviation_ms",
            "minimum_ms", "maximum_ms", "coefficient_of_variation",
        )
        for key in numeric_keys:
            value = statistics.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise RuntimeError(
                    f"benchmark {label} timing statistic {key!r} is invalid"
                )
        if not (
            float(statistics["minimum_ms"])
            <= float(statistics["median_ms"])
            <= float(statistics["maximum_ms"])
        ):
            raise RuntimeError(f"benchmark {label} order statistics are inconsistent")
        if not _mean_within_sample_range(
            float(statistics["mean_ms"]),
            float(statistics["minimum_ms"]),
            float(statistics["maximum_ms"]),
            repeat_count,
        ):
            raise RuntimeError(f"benchmark {label} mean is outside the sample range")
        return statistics

    serial = parsed.get("serial_measured_statistics")
    if not isinstance(serial, Mapping):
        raise RuntimeError("benchmark serial measured statistics are missing")
    validate_statistics(serial.get("symbolic_total_ms"), "serial symbolic")
    validate_statistics(serial.get("numeric_total_ms"), "serial numeric")
    serial_symbolic = serial["symbolic_total_ms"]
    serial_numeric = serial["numeric_total_ms"]
    assert isinstance(serial_symbolic, Mapping)
    assert isinstance(serial_numeric, Mapping)
    numeric_eligible: List[int] = []
    symbolic_eligible: List[int] = []
    for row in rows:
        assert isinstance(row, Mapping)
        thread_count = row["thread_count"]
        for key in ("symbolic_speedup", "numeric_speedup"):
            value = row.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise RuntimeError(f"benchmark statistic {key!r} is invalid")
        timing_keys = (
            "symbolic_pattern_ms", "symbolic_scatter_ms", "symbolic_total_ms",
            "numeric_reset_ms", "numeric_kernel_ms", "numeric_algorithm_ms",
            "numeric_total_ms", "amortized_total_ms",
        )
        validated_timings = {
            key: validate_statistics(row.get(key), f"thread {thread_count} {key}")
            for key in timing_keys
        }
        symbolic = validated_timings["symbolic_total_ms"]
        numeric = validated_timings["numeric_algorithm_ms"]
        symbolic_median = float(symbolic["median_ms"])
        numeric_median = float(numeric["median_ms"])
        if symbolic_median <= 0.0 or numeric_median <= 0.0:
            raise RuntimeError("benchmark candidate medians must be positive")
        expected_symbolic_speedup = (
            float(serial_symbolic["median_ms"]) / symbolic_median
        )
        expected_numeric_speedup = (
            float(serial_numeric["median_ms"]) / numeric_median
        )

        def require_speedup(actual: object, expected: float, label: str) -> None:
            if not math.isfinite(expected) or expected < 0.0:
                raise RuntimeError(
                    f"benchmark recomputed {label} must be finite and nonnegative"
                )
            actual_value = float(actual)
            scale = max(1.0, abs(actual_value), abs(expected))
            tolerance = 64.0 * float.fromhex("0x1.0000000000000p-52") * scale
            if abs(actual_value - expected) > tolerance:
                raise RuntimeError(
                    f"benchmark {label} disagrees with measured timing medians"
                )

        require_speedup(
            row["symbolic_speedup"], expected_symbolic_speedup, "symbolic_speedup"
        )
        require_speedup(
            row["numeric_speedup"], expected_numeric_speedup, "numeric_speedup"
        )
        if thread_count > 1:
            if (
                float(row["numeric_speedup"]) >= 1.5
                and float(numeric["coefficient_of_variation"]) <= 0.05
            ):
                numeric_eligible.append(thread_count)
            if (
                float(row["symbolic_speedup"]) > 1.0
                and float(symbolic["coefficient_of_variation"]) <= 0.05
            ):
                symbolic_eligible.append(thread_count)

    expected_gate: Dict[str, object]
    benchmark_case = configuration.get("case")
    if benchmark_case in {"generated-tet4", "generated-hex8"}:
        expected_gate = {
            "status": "NOT_APPLICABLE_GENERATED_CASE",
            "applicable": False,
            "performance_requirements_met": False,
            "numeric_requirement_met": False,
            "symbolic_requirement_met": False,
            "numeric_thread_count": 0,
            "symbolic_thread_count": 0,
        }
    elif benchmark_case == "windhub":
        formal = evidence_level == "formal"
        requirements_met = bool(numeric_eligible and symbolic_eligible) if formal else False
        expected_gate = {
            "status": (
                ("PASS" if requirements_met else "FAIL")
                if formal
                else (
                    "NON_FORMAL_CI_SMOKE"
                    if evidence_level == "ci-smoke"
                    else "NON_FORMAL_LOCAL_SMOKE"
                )
            ),
            "applicable": True,
            "performance_requirements_met": requirements_met,
            "numeric_requirement_met": bool(numeric_eligible),
            "symbolic_requirement_met": bool(symbolic_eligible),
            "numeric_thread_count": numeric_eligible[0] if numeric_eligible else 0,
            "symbolic_thread_count": symbolic_eligible[0] if symbolic_eligible else 0,
        }
    else:
        raise RuntimeError("benchmark configuration case is unsupported")
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise RuntimeError(f"benchmark performance gate field {key!r} is inconsistent")
    for key, expected in (
        ("numeric_speedup_threshold", 1.5),
        ("symbolic_speedup_threshold", 1.0),
        ("maximum_coefficient_of_variation", 0.05),
    ):
        value = gate.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or float(value) != expected
        ):
            raise RuntimeError(f"benchmark performance gate threshold {key!r} is invalid")
    return parsed, observed


def validate_benchmark_summary(
    path: Union[str, Path],
    requested_thread_counts: Sequence[int],
    expected_evidence_level: Optional[str] = None,
    expected_configuration: Optional[Mapping[str, object]] = None,
) -> Tuple[Dict[str, object], List[int]]:
    """Validate JSON evidence and translate numeric conversion failures."""

    try:
        return _validate_benchmark_summary(
            path,
            requested_thread_counts,
            expected_evidence_level,
            expected_configuration,
        )
    except (OverflowError, TypeError, ValueError) as error:
        raise RuntimeError(
            "benchmark summary contains an invalid numeric value"
        ) from error


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
    parser.add_argument("--nx", type=int)
    parser.add_argument("--ny", type=int)
    parser.add_argument("--nz", type=int)
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


def collect_provenance(
    source_root: Union[str, Path],
    build_root: Union[str, Path],
    controlled_host_id: Optional[str] = None,
    owned_output_root: Optional[Union[str, Path]] = None,
) -> Dict[str, object]:
    """Collect read-only source, host, and configured-toolchain facts."""

    source = Path(source_root).expanduser().resolve()
    build = Path(build_root).expanduser().resolve()

    def capture(command: Sequence[str], cwd: Path = source) -> str:
        completed = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    repository_text = capture(["git", "rev-parse", "--show-toplevel"])
    repository_root = Path(repository_text).resolve() if repository_text else source
    commit_sha = capture(["git", "rev-parse", "HEAD"])
    branch = capture(["git", "branch", "--show-current"])
    dirty_output = _repository_dirty_output(repository_root, owned_output_root)
    cmake_version_output = capture(["cmake", "--version"], cwd=source)
    cmake_version_match = re.search(r"cmake version ([^\s]+)", cmake_version_output)

    cpu_vendor = platform.processor() or "unknown"
    cpu_model = cpu_vendor
    physical_core_count: Optional[int] = None
    logical_core_count = os.cpu_count()
    total_memory_bytes: Optional[int] = None
    if platform.system() == "Linux":
        try:
            cpu_info = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
            vendor_match = re.search(r"^vendor_id\s*:\s*(.+)$", cpu_info, re.MULTILINE)
            model_match = re.search(r"^model name\s*:\s*(.+)$", cpu_info, re.MULTILINE)
            if vendor_match:
                cpu_vendor = vendor_match.group(1).strip()
            if model_match:
                cpu_model = model_match.group(1).strip()
            physical_pairs = set(
                re.findall(
                    r"^physical id\s*:\s*(\d+)\s*$[\s\S]*?^core id\s*:\s*(\d+)\s*$",
                    cpu_info,
                    re.MULTILINE,
                )
            )
            if physical_pairs:
                physical_core_count = len(physical_pairs)
        except OSError:
            pass
        try:
            memory_info = Path("/proc/meminfo").read_text(encoding="utf-8")
            memory_match = re.search(r"^MemTotal:\s*(\d+)\s+kB$", memory_info, re.MULTILINE)
            if memory_match:
                total_memory_bytes = int(memory_match.group(1)) * 1024
        except OSError:
            pass
    elif platform.system() == "Darwin":
        vendor = capture(["sysctl", "-n", "machdep.cpu.vendor"])
        model = capture(["sysctl", "-n", "machdep.cpu.brand_string"])
        physical = capture(["sysctl", "-n", "hw.physicalcpu"])
        memory = capture(["sysctl", "-n", "hw.memsize"])
        cpu_vendor = vendor or "Apple"
        cpu_model = model or platform.processor() or platform.machine()
        if physical.isdigit():
            physical_core_count = int(physical)
        if memory.isdigit():
            total_memory_bytes = int(memory)
    elif platform.system() == "Windows":
        vendor = capture(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Manufacturer)",
            ]
        )
        model = capture(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ]
        )
        physical = capture(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum",
            ]
        )
        memory = capture(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ]
        )
        cpu_vendor = vendor or cpu_vendor
        cpu_model = model or cpu_model
        if physical.isdigit():
            physical_core_count = int(physical)
        if memory.isdigit():
            total_memory_bytes = int(memory)
    if physical_core_count is None:
        physical_core_count = logical_core_count
    if total_memory_bytes is None:
        try:
            total_memory_bytes = int(os.sysconf("SC_PAGE_SIZE")) * int(
                os.sysconf("SC_PHYS_PAGES")
            )
        except (AttributeError, OSError, ValueError):
            total_memory_bytes = None

    cache_values: Dict[str, str] = {}
    cache_path = build / "CMakeCache.txt"
    if cache_path.is_file():
        for line in cache_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"([^#/][^:=]*):[^=]*=(.*)", line)
            if match:
                cache_values[match.group(1)] = match.group(2)
    compiler_description_values: Dict[str, str] = {}
    compiler_files = sorted(
        build.glob("CMakeFiles/*/CMakeCXXCompiler.cmake"),
        key=lambda path: path.as_posix(),
    )
    if compiler_files:
        compiler_text = compiler_files[-1].read_text(
            encoding="utf-8", errors="replace"
        )
        for name in (
            "CMAKE_CXX_COMPILER",
            "CMAKE_CXX_COMPILER_ID",
            "CMAKE_CXX_COMPILER_VERSION",
        ):
            match = re.search(
                r"^set\(" + re.escape(name) + r' "([^"]*)"\)$',
                compiler_text,
                re.MULTILINE,
            )
            if match:
                compiler_description_values[name] = match.group(1)
    for name, value in compiler_description_values.items():
        cache_values.setdefault(name, value)
    compiler_id = cache_values.get("CMAKE_CXX_COMPILER_ID", "unknown")
    compiler_version = cache_values.get("CMAKE_CXX_COMPILER_VERSION", "unknown")
    compiler_path = cache_values.get("CMAKE_CXX_COMPILER")
    compiler_banner = ""
    if compiler_path:
        compiler_banner_lines = capture(
            [compiler_path, "--version"], cwd=source
        ).splitlines()
        compiler_banner = compiler_banner_lines[0] if compiler_banner_lines else ""
    openmp_flags = cache_values.get("OpenMP_CXX_FLAGS", "")
    openmp_found = (
        bool(openmp_flags)
        or cache_values.get("OpenMP_CXX_FOUND") == "TRUE"
        or bool(cache_values.get("OpenMP_CXX_LIB_NAMES"))
        or bool(cache_values.get("OpenMP_CXX_SPEC_DATE"))
    )
    compiler = f"{compiler_id} {compiler_version}".strip()
    if compiler_id == "unknown" and compiler_banner:
        compiler = compiler_banner
    return {
        "source": {
            "commit_sha": commit_sha,
            "branch": branch or "DETACHED",
            "source_dirty_at_start": bool(dirty_output),
            "demo_version": _read_project_version(source),
        },
        "environment": {
            "system": platform.system(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "cpu_vendor": cpu_vendor,
            "cpu_model": cpu_model,
            "physical_core_count": physical_core_count,
            "logical_core_count": logical_core_count,
            "total_memory_bytes": total_memory_bytes,
            "python_version": platform.python_version(),
            "controlled_host_id": controlled_host_id,
        },
        "toolchain": {
            "cmake_version": cmake_version_match.group(1) if cmake_version_match else "unknown",
            "compiler": compiler,
            "compiler_id": compiler_id,
            "compiler_version": compiler_version,
            "compiler_path": compiler_path,
            "compiler_banner": compiler_banner,
            "openmp": {
                "found": openmp_found,
                "require_openmp": cache_values.get("CSC3_DEMO_REQUIRE_OPENMP") == "ON",
                "flags": openmp_flags,
            },
            "build_directory": str(build),
        },
        "repository_root": str(repository_root),
    }


def _validated_options(options: argparse.Namespace) -> Tuple[Path, Path, Path, List[int]]:
    source_root = options.source_dir.expanduser().resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_root}")
    if not (source_root / "CMakePresets.json").is_file():
        raise FileNotFoundError(f"CMakePresets.json is missing from source: {source_root}")
    build_root = (
        options.build_dir.expanduser().resolve()
        if options.build_dir is not None
        else (source_root / "build" / options.preset).resolve()
    )
    output_root = options.out_root.expanduser().resolve()
    requested_threads = _parse_thread_counts(options.threads_list)
    if options.evidence_level == "formal" and options.skip_build:
        raise ValueError("formal evidence does not permit --skip-build")
    if options.evidence_level == "formal" and options.preset != "delivery":
        raise ValueError("formal evidence requires the delivery CMake preset")
    if options.warmup < 0:
        raise ValueError("--warmup must be nonnegative")
    if options.repeat < 1:
        raise ValueError("--repeat must be positive")
    if options.amortization_count < 1:
        raise ValueError("--amortization-count must be positive")
    explicit_grid = (options.nx, options.ny, options.nz)
    if options.case == "windhub":
        if options.input is None:
            raise ValueError("WindHub case requires --input")
        if any(value is not None for value in explicit_grid):
            raise ValueError("WindHub case does not accept --nx, --ny, or --nz")
    else:
        if options.input is not None:
            raise ValueError("generated cases do not accept --input")
        for name in ("nx", "ny", "nz"):
            value = getattr(options, name)
            if value is None:
                setattr(options, name, 1)
            elif value <= 0:
                raise ValueError(f"--{name} must be positive")
    return source_root, build_root, output_root, requested_threads


def _input_provenance(
    options: argparse.Namespace,
    repository_root: Path,
) -> Dict[str, object]:
    repository_root = repository_root.expanduser().resolve()
    if options.case != "windhub":
        return {
            "case": options.case,
            "grid": {"nx": options.nx, "ny": options.ny, "nz": options.nz},
        }
    materialized = assert_materialized(options.input)
    facts: Dict[str, object] = {
        "case": "windhub",
        "path": str(materialized),
        "size_bytes": materialized.stat().st_size,
        "sha256": sha256_file(materialized),
        "materialized": True,
        "tracked": False,
        "matches_head_lfs": False,
    }
    try:
        relative = materialized.relative_to(repository_root).as_posix()
    except ValueError:
        return facts
    tracked = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--error-unmatch", "--", relative],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).returncode == 0
    facts["tracked"] = tracked
    facts["repository_relative_path"] = relative
    if not tracked:
        return facts
    head_blob = subprocess.run(
        ["git", "-C", str(repository_root), "show", f"HEAD:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if head_blob.returncode != 0:
        return facts
    pointer_text = head_blob.stdout.decode("utf-8", errors="replace")
    pointer_match = re.fullmatch(
        r"version https://git-lfs\.github\.com/spec/v1\n"
        r"oid sha256:([0-9a-f]{64})\n"
        r"size ([0-9]+)\n?",
        pointer_text,
    )
    if not pointer_match:
        return facts
    expected_sha = pointer_match.group(1)
    expected_size = int(pointer_match.group(2))
    facts["head_lfs_oid_sha256"] = expected_sha
    facts["head_lfs_size_bytes"] = expected_size
    facts["matches_head_lfs"] = (
        facts["sha256"] == expected_sha and facts["size_bytes"] == expected_size
    )
    return facts


_IDENTITY_PHASES: Tuple[str, ...] = (
    "after-build",
    "before-benchmark",
    "after-benchmark",
)
_SOURCE_IDENTITY_KEYS: Tuple[str, ...] = (
    "commit_sha",
    "branch",
    "source_dirty_at_start",
    "demo_version",
)
_INPUT_IDENTITY_KEYS: Tuple[str, ...] = (
    "case",
    "path",
    "size_bytes",
    "sha256",
    "materialized",
    "tracked",
    "matches_head_lfs",
    "repository_relative_path",
    "head_lfs_oid_sha256",
    "head_lfs_size_bytes",
)


def _identity_snapshot(
    facts: Mapping[str, object], keys: Sequence[str]
) -> Dict[str, object]:
    return {key: facts.get(key) for key in keys}


def _identity_check_record(
    phase: str,
    initial_source: Mapping[str, object],
    observed_source: Mapping[str, object],
    initial_input: Mapping[str, object],
    observed_input: Mapping[str, object],
) -> Dict[str, object]:
    """Compare one formal source/input observation with the run-start identity."""

    if phase not in _IDENTITY_PHASES:
        raise ValueError(f"unsupported identity-check phase: {phase}")
    source = _identity_snapshot(observed_source, _SOURCE_IDENTITY_KEYS)
    input_facts = _identity_snapshot(observed_input, _INPUT_IDENTITY_KEYS)
    expected_source = _identity_snapshot(initial_source, _SOURCE_IDENTITY_KEYS)
    expected_input = _identity_snapshot(initial_input, _INPUT_IDENTITY_KEYS)
    errors: List[str] = []
    for key in _SOURCE_IDENTITY_KEYS:
        if source[key] != expected_source[key]:
            errors.append(f"source identity drift at {phase}: {key}")
    for key in _INPUT_IDENTITY_KEYS:
        if input_facts[key] != expected_input[key]:
            errors.append(f"input identity drift at {phase}: {key}")
    return {
        "phase": phase,
        "status": "PASS" if not errors else "FAIL",
        "source": source,
        "input": input_facts,
        "errors": errors,
    }


def _formal_context(
    options: argparse.Namespace,
    provenance: Mapping[str, object],
    input_facts: Mapping[str, object],
    requested_threads: Sequence[int],
) -> Dict[str, object]:
    source = provenance.get("source")
    source = source if isinstance(source, Mapping) else {}
    environment = provenance.get("environment")
    environment = environment if isinstance(environment, Mapping) else {}
    toolchain = provenance.get("toolchain")
    toolchain = toolchain if isinstance(toolchain, Mapping) else {}
    return {
        "evidence_level": options.evidence_level,
        "case": options.case,
        "report_intent": options.report_intent,
        "system": environment.get("system"),
        "architecture": environment.get("architecture"),
        "cpu_vendor": environment.get("cpu_vendor"),
        "controlled_host_id": environment.get("controlled_host_id"),
        "source_dirty_at_start": source.get("source_dirty_at_start"),
        "commit_sha": source.get("commit_sha"),
        "input_is_materialized": input_facts.get("materialized"),
        "input_is_tracked": input_facts.get("tracked"),
        "input_matches_head_lfs": input_facts.get("matches_head_lfs"),
        "input_repository_relative_path": input_facts.get(
            "repository_relative_path"
        ),
        "input_sha256": input_facts.get("sha256"),
        "input_size_bytes": input_facts.get("size_bytes"),
        "warmup_count": options.warmup,
        "repeat_count": options.repeat,
        "requested_thread_counts": list(requested_threads),
        "physical_core_count": environment.get("physical_core_count"),
        "binding_environment": dict(REQUIRED_OPENMP_ENV),
        "cmake_version": toolchain.get("cmake_version"),
    }


def _formal_toolchain_blockers(
    evidence_level: str, toolchain: object
) -> List[str]:
    if evidence_level != "formal":
        return []
    facts = toolchain if isinstance(toolchain, Mapping) else {}
    blockers: List[str] = []
    cmake_version = str(facts.get("cmake_version") or "")
    if not cmake_version or cmake_version == "unknown":
        blockers.append("formal evidence requires an identified CMake version")
    compiler_id = str(facts.get("compiler_id") or "")
    compiler = str(facts.get("compiler") or "")
    if (not compiler_id or compiler_id == "unknown") and (
        not compiler or compiler == "unknown unknown"
    ):
        blockers.append("formal evidence requires an identified C++ compiler")
    openmp = facts.get("openmp")
    openmp = openmp if isinstance(openmp, Mapping) else {}
    if openmp.get("found") is not True:
        blockers.append("formal evidence requires detected OpenMP support")
    if openmp.get("require_openmp") is not True:
        blockers.append("formal evidence requires the OpenMP-required delivery build")
    return blockers


def _command_plan(
    options: argparse.Namespace,
    source_root: Path,
    build_root: Path,
    output_root: Path,
    requested_threads: Sequence[int],
    benchmark_executable: Path,
) -> Dict[str, List[str]]:
    configure = ["cmake", "--preset", options.preset, "-B", str(build_root)]
    build = ["cmake", "--build", str(build_root), "--config", "Release"]
    ctest = [
        "ctest", "--test-dir", str(build_root), "-C", "Release",
        "--label-regex", "ci", "--output-on-failure", "--no-tests=error",
        "--output-junit", str(output_root / "ctest.xml"),
    ]
    benchmark = [
        str(benchmark_executable),
        "--case", options.case,
        "--threads-list", ",".join(str(value) for value in requested_threads),
        "--warmup", str(options.warmup),
        "--repeat", str(options.repeat),
        "--amortization-count", str(options.amortization_count),
        "--evidence-level", options.evidence_level,
        "--samples-csv", str(output_root / "benchmark_samples.csv"),
        "--summary-json", str(output_root / "benchmark_summary.json"),
    ]
    if options.case == "windhub":
        benchmark.extend(["--input", str(Path(options.input).expanduser().resolve())])
    else:
        benchmark.extend(
            ["--nx", str(options.nx), "--ny", str(options.ny), "--nz", str(options.nz)]
        )
    return {"configure": configure, "build": build, "ctest": ctest, "benchmark": benchmark}


def run_workflow(
    arguments: Optional[Sequence[str]] = None,
    *,
    command_runner: Optional[object] = None,
) -> int:
    """Configure, test, benchmark, and bind all resulting evidence in a manifest."""

    options = build_argument_parser().parse_args(arguments)
    source_root, build_root, output_root, requested_threads = _validated_options(options)
    provenance = collect_provenance(
        source_root,
        build_root,
        options.controlled_host_id,
    )
    repository_root = Path(str(provenance.get("repository_root", source_root))).resolve()
    input_facts = _input_provenance(options, repository_root)
    preflight_blockers = formal_preflight_blockers(
        _formal_context(options, provenance, input_facts, requested_threads)
    )
    if preflight_blockers:
        raise RuntimeError("formal evidence preflight failed: " + "; ".join(preflight_blockers))

    expected_executable = build_root / "bin" / (
        "csc3_demo_benchmark.exe" if platform.system() == "Windows" else "csc3_demo_benchmark"
    )
    executable = (
        resolve_executable(build_root, "csc3_demo_benchmark")
        if options.skip_build
        else expected_executable
    )
    commands = _command_plan(
        options, source_root, build_root, output_root, requested_threads, executable
    )
    if options.dry_run:
        for name in ("configure", "build", "ctest", "benchmark"):
            if options.skip_build and name in {"configure", "build"}:
                continue
            print(f"{name}: {_safe_command_text(commands[name])}")
        return 0

    output_root = prepare_output_root(
        output_root, overwrite=options.overwrite, source_root=source_root
    )
    started_at = _utc_now()
    source_facts = provenance.get("source")
    source_facts = dict(source_facts) if isinstance(source_facts, Mapping) else {}
    commit_sha = str(source_facts.get("commit_sha", "unknown"))
    manifest_path = output_root / "run_manifest.json"
    manifest: Dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": (
            "run-" + started_at.strftime("%Y%m%dT%H%M%SZ") + "-" + commit_sha[:12]
        ),
        "report_intent": options.report_intent,
        "status": "PENDING",
        "evidence_level": options.evidence_level,
        "source": source_facts,
        "environment": provenance.get("environment", {}),
        "toolchain": provenance.get("toolchain", {}),
        "input": input_facts,
        "benchmark": {
            "warmup_count": options.warmup,
            "repeat_count": options.repeat,
            "amortization_count": options.amortization_count,
            "requested_thread_counts": list(requested_threads),
            "observed_thread_counts": [],
        },
        "commands": commands,
        "binding_environment": dict(REQUIRED_OPENMP_ENV),
        "tasks": [],
        "identity_checks": [],
        "blockers": [],
        "artifacts": [],
        "started_at_utc": _utc_text(started_at),
        "ended_at_utc": None,
    }
    _atomic_write_json(manifest_path, manifest)
    runner = command_runner if command_runner is not None else _default_command_runner

    def invoke(command: Sequence[str], cwd: Path) -> CommandResult:
        try:
            result = runner(command, cwd, REQUIRED_OPENMP_ENV)
        except OSError as error:
            return CommandResult(command, 127, "", f"{type(error).__name__}: {error}")
        except Exception as error:  # Preserve a manifest for injected runners too.
            return CommandResult(command, 1, "", f"{type(error).__name__}: {error}")
        if not isinstance(result, CommandResult):
            return CommandResult(
                command,
                1,
                "",
                "command runner returned an invalid result object",
            )
        return result

    task_specs: List[Tuple[str, List[str], Path]] = []
    if not options.skip_build:
        task_specs.extend(
            [("configure", commands["configure"], source_root),
             ("build", commands["build"], source_root)]
        )
    task_specs.append(("ctest", commands["ctest"], source_root))

    def fail_manifest(return_code: int, blocker: str) -> int:
        manifest["status"] = "FAIL"
        manifest["blockers"] = [blocker]
        manifest["ended_at_utc"] = _utc_text(_utc_now())
        existing = [
            output_root / name
            for name in ("ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md")
            if (output_root / name).is_file()
        ]
        manifest["artifacts"] = artifact_records(output_root, existing)
        _atomic_write_json(manifest_path, manifest)
        return return_code if return_code != 0 else 1

    def record_formal_identity_check(
        phase: str,
        observed_provenance: Optional[Mapping[str, object]] = None,
    ) -> Optional[str]:
        if options.evidence_level != "formal":
            return None
        try:
            current_provenance = (
                observed_provenance
                if observed_provenance is not None
                else collect_provenance(
                    source_root,
                    build_root,
                    options.controlled_host_id,
                    owned_output_root=output_root,
                )
            )
            observed_source = current_provenance.get("source")
            observed_source = (
                observed_source if isinstance(observed_source, Mapping) else {}
            )
            observed_input = _input_provenance(options, repository_root)
            record = _identity_check_record(
                phase,
                source_facts,
                observed_source,
                input_facts,
                observed_input,
            )
        except Exception as error:
            record = {
                "phase": phase,
                "status": "FAIL",
                "source": {},
                "input": {},
                "errors": [
                    f"identity collection failed at {phase}: "
                    f"{type(error).__name__}: {error}"
                ],
            }
        checks = manifest["identity_checks"]
        assert isinstance(checks, list)
        checks.append(record)
        _atomic_write_json(manifest_path, manifest)
        if record["status"] == "PASS":
            return None
        errors = record["errors"]
        assert isinstance(errors, list)
        return "; ".join(str(error) for error in errors)

    for name, command, cwd in task_specs:
        result = invoke(command, cwd)
        validation_error: Optional[str] = None
        if result.returncode == 0 and name == "ctest":
            try:
                validate_ctest_junit(output_root / "ctest.xml")
            except RuntimeError as error:
                validation_error = str(error)
        record = _task_record(
            name, command, cwd, REQUIRED_OPENMP_ENV, result,
            validation_error=validation_error,
        )
        tasks = manifest["tasks"]
        assert isinstance(tasks, list)
        tasks.append(record)
        _atomic_write_json(manifest_path, manifest)
        if record["status"] == "FAIL":
            return fail_manifest(result.returncode, str(record["error"]))
        if name == "build":
            try:
                post_build = collect_provenance(
                    source_root,
                    build_root,
                    options.controlled_host_id,
                    owned_output_root=output_root,
                )
            except Exception as error:
                return fail_manifest(
                    1, f"post-build provenance collection failed: {error}"
                )
            manifest["toolchain"] = post_build.get("toolchain", {})
            _atomic_write_json(manifest_path, manifest)
            identity_error = record_formal_identity_check(
                "after-build", post_build
            )
            if identity_error is not None:
                return fail_manifest(1, identity_error)
            toolchain_blockers = _formal_toolchain_blockers(
                options.evidence_level, manifest["toolchain"]
            )
            if toolchain_blockers:
                return fail_manifest(1, "; ".join(toolchain_blockers))

    if options.skip_build:
        toolchain_blockers = _formal_toolchain_blockers(
            options.evidence_level, manifest["toolchain"]
        )
        if toolchain_blockers:
            return fail_manifest(1, "; ".join(toolchain_blockers))

    if not options.skip_build:
        try:
            executable = resolve_executable(build_root, "csc3_demo_benchmark")
        except FileNotFoundError as error:
            return fail_manifest(1, str(error))
        commands = _command_plan(
            options, source_root, build_root, output_root, requested_threads, executable
        )
        manifest["commands"] = commands

    identity_error = record_formal_identity_check("before-benchmark")
    if identity_error is not None:
        return fail_manifest(1, identity_error)

    benchmark_command = commands["benchmark"]
    benchmark_result = invoke(benchmark_command, source_root)
    identity_error = record_formal_identity_check("after-benchmark")
    if identity_error is not None:
        benchmark_record = _task_record(
            "benchmark",
            benchmark_command,
            source_root,
            REQUIRED_OPENMP_ENV,
            benchmark_result,
            validation_error=identity_error,
        )
        tasks = manifest["tasks"]
        assert isinstance(tasks, list)
        tasks.append(benchmark_record)
        _atomic_write_json(manifest_path, manifest)
        return fail_manifest(
            benchmark_result.returncode if benchmark_result.returncode != 0 else 1,
            identity_error,
        )
    benchmark_summary: Optional[Dict[str, object]] = None
    observed_threads: List[int] = []
    validation_error = None
    outputs_exist = all(
        (output_root / name).is_file()
        for name in ("benchmark_samples.csv", "benchmark_summary.json")
    )
    if benchmark_result.returncode == 0 or outputs_exist:
        try:
            csv_path = output_root / "benchmark_samples.csv"
            if not csv_path.is_file() or csv_path.stat().st_size == 0:
                raise RuntimeError("benchmark samples CSV is missing or empty")
            benchmark_summary, observed_threads = validate_benchmark_summary(
                output_root / "benchmark_summary.json",
                requested_threads,
                options.evidence_level,
                {
                    "case": options.case,
                    "nx": options.nx if options.case != "windhub" else 0,
                    "ny": options.ny if options.case != "windhub" else 0,
                    "nz": options.nz if options.case != "windhub" else 0,
                    "thread_counts": list(requested_threads),
                    "warmup_count": options.warmup,
                    "repeat_count": options.repeat,
                    "amortization_count": options.amortization_count,
                    "performance_evidence_level": options.evidence_level,
                },
            )
        except RuntimeError as error:
            validation_error = str(error)
    benchmark_record = _task_record(
        "benchmark", benchmark_command, source_root, REQUIRED_OPENMP_ENV,
        benchmark_result, validation_error=validation_error,
    )
    tasks = manifest["tasks"]
    assert isinstance(tasks, list)
    tasks.append(benchmark_record)
    benchmark_facts = manifest["benchmark"]
    assert isinstance(benchmark_facts, dict)
    benchmark_facts["observed_thread_counts"] = observed_threads
    _atomic_write_json(manifest_path, manifest)
    if benchmark_summary is None:
        return fail_manifest(
            benchmark_result.returncode,
            str(benchmark_record["error"] or "benchmark evidence validation failed"),
        )

    status, derived_blockers = derive_run_status(
        evidence_level=options.evidence_level,
        report_intent=options.report_intent,
        benchmark_summary=benchmark_summary,
        command_failed=benchmark_record["status"] == "FAIL",
    )
    manifest["status"] = status
    manifest["blockers"] = list(preflight_blockers) + derived_blockers
    summary_path = output_root / "summary.md"
    manifest["artifacts"] = artifact_records(
        output_root,
        [
            output_root / "ctest.xml",
            output_root / "benchmark_samples.csv",
            output_root / "benchmark_summary.json",
        ],
    )
    summary_path.write_text(
        render_markdown_summary(
            manifest, benchmark_summary, output_root / "benchmark_samples.csv"
        ),
        encoding="utf-8",
    )
    manifest["artifacts"] = artifact_records(
        output_root,
        [
            output_root / "ctest.xml",
            output_root / "benchmark_samples.csv",
            output_root / "benchmark_summary.json",
            summary_path,
        ],
    )
    manifest["ended_at_utc"] = _utc_text(_utc_now())
    _atomic_write_json(manifest_path, manifest)
    if benchmark_record["status"] == "FAIL":
        return benchmark_result.returncode if benchmark_result.returncode != 0 else 1
    return 0


def main() -> int:
    return run_workflow()


if __name__ == "__main__":
    raise SystemExit(main())
