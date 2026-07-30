#!/usr/bin/env python3
"""Reproducible evidence runner for the CSC3 assembly demo.

This module intentionally uses only the Python standard library.  The public
helpers form the safety and evidence contract used by the workflow tests; the
subprocess orchestration is added separately so that these invariants remain
independently testable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import importlib.util
import json
import math
import os
import platform
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


def _load_formal_host_module():
    path = Path(__file__).resolve().with_name("formal_host.py")
    name = "csc3_formal_host"
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load formal host helpers: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


_FORMAL_HOST = _load_formal_host_module()
LinuxCpuTopology = _FORMAL_HOST.LinuxCpuTopology
CANONICAL_FORMAL_ENVIRONMENT = dict(_FORMAL_HOST.CANONICAL_FORMAL_ENVIRONMENT)
CONFLICTING_OPENMP_ENVIRONMENT = tuple(_FORMAL_HOST.CONFLICTING_OPENMP_ENVIRONMENT)
canonical_formal_threads = _FORMAL_HOST.canonical_formal_threads
collect_linux_cpu_topology = _FORMAL_HOST.collect_linux_cpu_topology
conflicting_formal_environment_keys = (
    _FORMAL_HOST.conflicting_formal_environment_keys
)
formal_host_blockers = _FORMAL_HOST.formal_host_blockers
parse_cpu_list = _FORMAL_HOST.parse_cpu_list
sanitized_formal_environment = _FORMAL_HOST.sanitized_formal_environment


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
COMPARISON_FAILURE_ERROR = sys.float_info.max
FORMAL_WARMUP_COUNT = 2
FORMAL_REPEAT_COUNT = 7
FORMAL_AMORTIZATION_COUNT = 1
BENCHMARK_SCHEMA_V1 = "csc3-demo-benchmark-v1"
BENCHMARK_SCHEMA_V2 = "csc3-demo-benchmark-v2"
BENCHMARK_CSV_HEADER_V1: Tuple[str, ...] = (
    "schema_version", "case_name", "element_type", "nx", "ny", "nz",
    "node_count", "element_count", "dof_count", "nnz", "thread_count",
    "sample_index", "sample_kind", "input_prepare_ms", "serial_symbolic_ms",
    "serial_numeric_ms", "symbolic_pattern_ms", "symbolic_scatter_ms",
    "symbolic_total_ms", "numeric_reset_ms", "numeric_kernel_ms",
    "numeric_total_ms", "amortized_total_ms", "symbolic_speedup",
    "numeric_speedup", "relative_frobenius_error", "max_absolute_error",
    "matrix_correctness_status", "estimated_persistent_bytes",
    "performance_evidence_level",
)
BENCHMARK_CSV_HEADER_V2 = BENCHMARK_CSV_HEADER_V1 + (
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
)
_BENCHMARK_INTEGER_FIELDS = {
    "nx", "ny", "nz", "node_count", "element_count", "dof_count", "nnz",
    "thread_count", "sample_index", "estimated_persistent_bytes",
}
_BENCHMARK_POSITIVE_INTEGER_FIELDS = {
    "node_count", "element_count", "dof_count", "nnz", "thread_count",
}
_BENCHMARK_FLOAT_FIELDS = {
    "input_prepare_ms", "serial_symbolic_ms", "serial_numeric_ms",
    "symbolic_pattern_ms", "symbolic_scatter_ms", "symbolic_total_ms",
    "numeric_reset_ms", "numeric_kernel_ms", "numeric_total_ms",
    "amortized_total_ms", "symbolic_speedup", "numeric_speedup",
    "relative_frobenius_error", "max_absolute_error",
}
_BENCHMARK_PHASES = (
    "symbolic_pattern_ms", "symbolic_scatter_ms", "symbolic_total_ms",
    "numeric_reset_ms", "numeric_kernel_ms", "numeric_algorithm_ms",
    "numeric_total_ms", "amortized_total_ms",
)
_BENCHMARK_STATISTIC_KEYS = (
    "mean_ms", "median_ms", "population_standard_deviation_ms",
    "minimum_ms", "maximum_ms", "coefficient_of_variation",
)
_BENCHMARK_INTEGER_TEXT = re.compile(r"0|[1-9][0-9]*")
_BENCHMARK_FLOAT_TEXT = re.compile(
    r"-?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)


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


def _proc_status_cpu_sets(
    status_path: Union[str, Path] = "/proc/self/status",
) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    text = Path(status_path).read_text(encoding="utf-8", errors="strict")
    values: Dict[str, Tuple[int, ...]] = {}
    for line in text.splitlines():
        name, separator, value = line.partition(":")
        if separator and name in {"Cpus_allowed_list", "Mems_allowed_list"}:
            values[name] = parse_cpu_list(value.strip())
    if set(values) != {"Cpus_allowed_list", "Mems_allowed_list"}:
        raise RuntimeError("Linux cpuset status lacks CPU or memory allow-list")
    return values["Cpus_allowed_list"], values["Mems_allowed_list"]


def collect_formal_host_facts(
    environment: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Collect one JSON-ready Linux topology, cpuset, and environment snapshot."""

    topology = collect_linux_cpu_topology()
    errors = list(topology.errors)
    cpuset_cpu_ids: Tuple[int, ...] = ()
    cpuset_memory_ids: Tuple[int, ...] = ()
    try:
        cpuset_cpu_ids, cpuset_memory_ids = _proc_status_cpu_sets()
    except Exception as error:
        errors.append(f"cpuset collection failed: {type(error).__name__}: {error}")
    source = os.environ if environment is None else environment
    effective_environment = sanitized_formal_environment(source)
    formal_environment = {
        name: effective_environment[name]
        for name in CANONICAL_FORMAL_ENVIRONMENT
    }
    conflicting_environment_keys = list(
        conflicting_formal_environment_keys(source)
    )
    host = {
        "online_cpu_ids": list(topology.online_cpu_ids),
        "affinity_cpu_ids": list(topology.affinity_cpu_ids),
        "physical_core_ids": [list(value) for value in topology.physical_core_ids],
        "full_host_affinity": topology.full_host_affinity,
        "cpuset_cpu_ids": list(cpuset_cpu_ids),
        "cpuset_memory_ids": list(cpuset_memory_ids),
        "formal_environment": formal_environment,
        "conflicting_environment_keys": conflicting_environment_keys,
        "topology_errors": list(topology.errors),
        "collection_errors": errors,
    }
    return {
        "physical_core_count": topology.physical_core_count,
        "formal_host": host,
        "formal_environment": formal_environment,
    }


def _topology_from_host_facts(facts: Mapping[str, object]) -> object:
    def integer_tuple(name: str) -> Tuple[int, ...]:
        values = facts.get(name)
        if not isinstance(values, (list, tuple)) or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in values
        ):
            raise ValueError(f"{name} is not a CPU-ID list")
        return tuple(values)

    physical_values = facts.get("physical_core_ids")
    if not isinstance(physical_values, (list, tuple)):
        raise ValueError("physical_core_ids is not a package/core list")
    physical: List[Tuple[int, int]] = []
    for value in physical_values:
        if not isinstance(value, (list, tuple)) or len(value) != 2 or any(
            not isinstance(part, int) or isinstance(part, bool) or part < 0
            for part in value
        ):
            raise ValueError("physical_core_ids contains an invalid package/core pair")
        physical.append((value[0], value[1]))
    errors = facts.get("topology_errors", ())
    if not isinstance(errors, (list, tuple)) or any(
        not isinstance(error, str) for error in errors
    ):
        raise ValueError("topology_errors is not a string list")
    return LinuxCpuTopology(
        online_cpu_ids=integer_tuple("online_cpu_ids"),
        affinity_cpu_ids=integer_tuple("affinity_cpu_ids"),
        physical_core_ids=tuple(physical),
        full_host_affinity=facts.get("full_host_affinity") is True,
        errors=tuple(errors),
    )


def _formal_host_context_blockers(context: Mapping[str, object]) -> List[str]:
    host = context.get("formal_host")
    if not isinstance(host, Mapping):
        return ["formal Linux package/core topology is missing"]
    try:
        topology = _topology_from_host_facts(host)
    except (TypeError, ValueError) as error:
        return [f"formal Linux package/core topology is invalid: {error}"]
    environment = context.get("formal_environment")
    host_environment = host.get("formal_environment")
    blockers = formal_host_blockers(topology, {})
    if (
        environment != CANONICAL_FORMAL_ENVIRONMENT
        or host_environment != CANONICAL_FORMAL_ENVIRONMENT
    ):
        blockers.append(
            "formal environment must equal the canonical child environment"
        )
    conflicts = host.get("conflicting_environment_keys")
    if (
        not isinstance(conflicts, (list, tuple))
        or any(
            not isinstance(name, str) or name not in CONFLICTING_OPENMP_ENVIRONMENT
            for name in conflicts
        )
        or list(conflicts) != sorted(set(conflicts))
    ):
        blockers.append("formal conflicting environment key snapshot is invalid")
    else:
        blockers.extend(
            formal_host_blockers(topology, {name: "" for name in conflicts})
        )
    if topology.physical_core_count != context.get("physical_core_count"):
        blockers.append(
            "formal physical-core count must match the package/core topology"
        )
    collection_errors = host.get("collection_errors", ())
    if isinstance(collection_errors, (list, tuple)):
        blockers.extend(
            f"formal host fact collection failed: {error}"
            for error in collection_errors
            if isinstance(error, str) and error not in topology.errors
        )
    cpuset_cpu_ids = host.get("cpuset_cpu_ids")
    if cpuset_cpu_ids != list(topology.online_cpu_ids):
        blockers.append("formal host cpuset CPU set must equal the online CPU set")
    cpuset_memory_ids = host.get("cpuset_memory_ids")
    if not isinstance(cpuset_memory_ids, (list, tuple)) or not cpuset_memory_ids:
        blockers.append("formal host cpuset memory set is missing")
    return blockers


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
    if warmups != FORMAL_WARMUP_COUNT or isinstance(warmups, bool):
        blockers.append("formal evidence requires exactly 2 warmups")
    repeats = context.get("repeat_count")
    if repeats != FORMAL_REPEAT_COUNT or isinstance(repeats, bool):
        blockers.append("formal evidence requires exactly 7 measured repeats")
    amortization = context.get("amortization_count")
    if (
        amortization != FORMAL_AMORTIZATION_COUNT
        or isinstance(amortization, bool)
    ):
        blockers.append("formal evidence requires amortization count 1")

    physical = context.get("physical_core_count")
    if not isinstance(physical, int) or isinstance(physical, bool) or physical <= 0:
        blockers.append("formal evidence requires a positive physical-core count")
    else:
        requested_raw = context.get("requested_thread_counts")
        requested = (
            list(requested_raw) if isinstance(requested_raw, (list, tuple)) else []
        )
        expected_threads = list(canonical_formal_threads(physical))
        if requested != expected_threads:
            blockers.append(
                "formal evidence requires the exact canonical physical-core thread scan "
                + ",".join(str(value) for value in expected_threads)
            )

    blockers.extend(_formal_host_context_blockers(context))

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
    validation_cases = benchmark_summary.get("validation_cases")
    if not isinstance(validation_cases, list) or any(
        not isinstance(case, Mapping) or case.get("status") != "PASS"
        for case in validation_cases
    ):
        return "FAIL", ["benchmark validation evidence did not pass"]
    scatter = benchmark_summary.get("scatter_correctness")
    if benchmark_summary.get("schema_version") == BENCHMARK_SCHEMA_V2 and (
        not isinstance(scatter, Mapping) or scatter.get("status") != "PASS"
    ):
        return "FAIL", ["benchmark scatter plan evidence did not pass"]

    if evidence_level != "formal":
        blocker = "formal controlled-host evidence was not produced"
        if report_intent == "delivery":
            return "BLOCKED", [blocker]
        return "LOCAL_SMOKE", [blocker]

    if report_intent != "delivery":
        return "BLOCKED", ["formal evidence requires delivery report intent"]
    if benchmark_summary.get("schema_version") != BENCHMARK_SCHEMA_V2:
        return "FAIL", ["formal evidence requires benchmark schema v2"]
    gate = benchmark_summary.get("performance_gate")
    if not isinstance(gate, Mapping):
        return "FAIL", ["formal benchmark performance gate is missing"]
    if (
        gate.get("status") == "PASS"
        and gate.get("performance_requirements_met") is True
        and gate.get("scatter_requirement_met") is True
        and gate.get("formal_requirements_met") is True
    ):
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
    serial = benchmark_summary.get("serial_measured_statistics")
    serial = serial if isinstance(serial, Mapping) else {}
    serial_symbolic = serial.get("symbolic_total_ms")
    serial_numeric = serial.get("numeric_total_ms")
    serial_symbolic = serial_symbolic if isinstance(serial_symbolic, Mapping) else {}
    serial_numeric = serial_numeric if isinstance(serial_numeric, Mapping) else {}
    scatter = benchmark_summary.get("scatter_correctness")
    scatter = scatter if isinstance(scatter, Mapping) else {}
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
            "- Serial symbolic $CV$: "
            + _format_float(serial_symbolic.get("coefficient_of_variation")),
            "- Serial numeric $CV$: "
            + _format_float(serial_numeric.get("coefficient_of_variation")),
            "- Scatter plan status: `"
            + str(scatter.get("status", "N/A"))
            + "`; symbolic matches/checks: $"
            + str(scatter.get("symbolic_plan_match_count", "N/A"))
            + "/"
            + str(scatter.get("symbolic_plan_check_count", "N/A"))
            + "$; numeric setup matches/checks: $"
            + str(scatter.get("numeric_setup_plan_match_count", "N/A"))
            + "/"
            + str(scatter.get("numeric_setup_plan_check_count", "N/A"))
            + "$.",
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
            "- Serial symbolic/numeric $CV$ requirements met: `"
            + str(gate.get("serial_symbolic_cv_requirement_met", False))
            + "` / `"
            + str(gate.get("serial_numeric_cv_requirement_met", False))
            + "`",
            "- Scatter/formal requirements met: `"
            + str(gate.get("scatter_requirement_met", False))
            + "` / `"
            + str(gate.get("formal_requirements_met", False))
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
    child_environment = {
        str(key): str(value) for key, value in environment.items()
    }
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd),
        env=child_environment,
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


def _benchmark_close(actual: float, expected: float) -> bool:
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    tolerance = 64.0 * DOUBLE_EPSILON * max(1.0, abs(actual), abs(expected))
    return abs(actual - expected) <= tolerance


def _benchmark_statistics(values: Sequence[float]) -> Dict[str, object]:
    if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
        raise RuntimeError("benchmark statistics require finite nonnegative samples")
    ordered = sorted(values)
    with localcontext() as context:
        context.prec = 80
        decimals = [Decimal.from_float(value) for value in values]
        mean_decimal = sum(decimals, Decimal(0)) / Decimal(len(decimals))
        variance = sum(
            ((value - mean_decimal) * (value - mean_decimal) for value in decimals),
            Decimal(0),
        ) / Decimal(len(decimals))
        mean = float(mean_decimal)
        deviation = float(variance.sqrt())
    middle = len(ordered) // 2
    median = (
        ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2.0
        if len(ordered) % 2 == 0
        else ordered[middle]
    )
    if mean == 0.0:
        if ordered[-1] != 0.0:
            raise RuntimeError("benchmark zero-mean samples have undefined CV")
        coefficient = 0.0
    else:
        coefficient = deviation / mean
    if any(not math.isfinite(value) for value in (mean, median, deviation, coefficient)):
        raise RuntimeError("benchmark recomputed statistics are not finite")
    return {
        "sample_count": len(values),
        "mean_ms": mean,
        "median_ms": median,
        "population_standard_deviation_ms": deviation,
        "minimum_ms": ordered[0],
        "maximum_ms": ordered[-1],
        "coefficient_of_variation": coefficient,
    }


def _parse_benchmark_v2_csv(
    source: Union[str, Path, bytes],
) -> List[Dict[str, object]]:
    try:
        if isinstance(source, bytes):
            text = source.decode("utf-8")
        else:
            csv_path = Path(source)
            if not csv_path.is_file():
                raise RuntimeError(f"benchmark samples CSV is missing: {csv_path}")
            text = csv_path.read_text(encoding="utf-8")
        raw_rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except RuntimeError:
        raise
    except (OSError, UnicodeError, csv.Error) as error:
        raise RuntimeError(f"benchmark samples CSV is invalid: {error}") from error
    if not raw_rows or tuple(raw_rows[0]) != BENCHMARK_CSV_HEADER_V2:
        raise RuntimeError(
            "benchmark samples CSV header is not the exact 32-column v2 contract"
        )
    parsed: List[Dict[str, object]] = []
    for line_number, values in enumerate(raw_rows[1:], start=2):
        if len(values) != len(BENCHMARK_CSV_HEADER_V2):
            raise RuntimeError(
                f"benchmark samples CSV row {line_number} has unexpected fields"
            )
        row: Dict[str, object] = {}
        for field, raw in zip(BENCHMARK_CSV_HEADER_V2, values):
            if not raw or raw != raw.strip():
                raise RuntimeError(
                    f"benchmark CSV field {field!r} is empty or has whitespace"
                )
            if field in _BENCHMARK_INTEGER_FIELDS:
                if _BENCHMARK_INTEGER_TEXT.fullmatch(raw) is None:
                    raise RuntimeError(
                        f"benchmark CSV field {field!r} is not a strict integer"
                    )
                value = int(raw)
                if field in _BENCHMARK_POSITIVE_INTEGER_FIELDS and value <= 0:
                    raise RuntimeError(
                        f"benchmark CSV field {field!r} must be positive"
                    )
                row[field] = value
            elif field in _BENCHMARK_FLOAT_FIELDS:
                if _BENCHMARK_FLOAT_TEXT.fullmatch(raw) is None:
                    raise RuntimeError(
                        f"benchmark CSV field {field!r} is not a strict number"
                    )
                value = float(raw)
                if not math.isfinite(value) or value < 0.0:
                    raise RuntimeError(
                        f"benchmark CSV field {field!r} must be finite and nonnegative"
                    )
                row[field] = value
            elif field in {
                "symbolic_plan_matches_serial",
                "numeric_setup_plan_matches_serial",
            }:
                if raw not in {"true", "false"}:
                    raise RuntimeError(
                        f"benchmark CSV boolean field {field!r} must be lowercase true/false"
                    )
                row[field] = raw == "true"
            else:
                row[field] = raw
        parsed.append(row)
    if not parsed:
        raise RuntimeError("benchmark samples CSV contains no data rows")
    return parsed


def _json_nonnegative_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuntimeError(f"benchmark {label} must be a finite nonnegative number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise RuntimeError(f"benchmark {label} must be a finite nonnegative number")
    return number


def _validate_comparison_failure_representation(
    structure_matches: bool,
    relative_frobenius_error: float,
    max_absolute_error: float,
    label: str,
) -> None:
    relative_is_sentinel = relative_frobenius_error == COMPARISON_FAILURE_ERROR
    absolute_is_sentinel = max_absolute_error == COMPARISON_FAILURE_ERROR
    if relative_is_sentinel != absolute_is_sentinel:
        raise RuntimeError(
            f"benchmark {label} must use a paired finite failure sentinel"
        )
    if not structure_matches and not relative_is_sentinel:
        raise RuntimeError(
            f"benchmark {label} structure failure must use the finite failure sentinel"
        )


def _json_nonnegative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RuntimeError(f"benchmark {label} must be a nonnegative integer")
    return value


def _compare_benchmark_statistics(
    actual: object, expected: Mapping[str, object], label: str
) -> None:
    if not isinstance(actual, Mapping):
        raise RuntimeError(f"benchmark {label} statistics are missing")
    if actual.get("sample_count") != expected["sample_count"]:
        raise RuntimeError(f"benchmark {label} sample_count disagrees with CSV")
    for key in _BENCHMARK_STATISTIC_KEYS:
        actual_value = _json_nonnegative_number(actual.get(key), f"{label}.{key}")
        expected_value = float(expected[key])
        if not _benchmark_close(actual_value, expected_value):
            raise RuntimeError(f"benchmark {label}.{key} disagrees with CSV")


def _validate_v2_cross_file_fields(
    parsed: Mapping[str, object],
    csv_rows: Sequence[Mapping[str, object]],
    evidence_level: str,
    configuration: Mapping[str, object],
) -> None:
    first = csv_rows[0]
    invariant_fields = (
        "schema_version", "case_name", "element_type", "nx", "ny", "nz",
        "node_count", "element_count", "dof_count", "nnz", "input_prepare_ms",
        "relative_frobenius_error", "max_absolute_error",
        "matrix_correctness_status", "estimated_persistent_bytes",
        "performance_evidence_level",
    )
    for row in csv_rows[1:]:
        for field in invariant_fields:
            if row[field] != first[field]:
                raise RuntimeError(
                    f"benchmark CSV invariant field {field!r} drifts across rows"
                )
    sizes = parsed.get("case_sizes")
    correctness = parsed.get("correctness")
    if not isinstance(sizes, Mapping) or not isinstance(correctness, Mapping):
        raise RuntimeError("benchmark sizes or correctness evidence is missing")
    expected_fields = {
        "schema_version": BENCHMARK_SCHEMA_V2,
        "case_name": sizes.get("case_name"),
        "element_type": sizes.get("element_type"),
        "nx": configuration.get("nx"),
        "ny": configuration.get("ny"),
        "nz": configuration.get("nz"),
        "node_count": sizes.get("node_count"),
        "element_count": sizes.get("element_count"),
        "dof_count": sizes.get("dof_count"),
        "nnz": sizes.get("nnz"),
        "matrix_correctness_status": correctness.get("status"),
        "estimated_persistent_bytes": parsed.get("estimated_persistent_bytes"),
        "performance_evidence_level": evidence_level,
    }
    for field, expected in expected_fields.items():
        if first[field] != expected:
            raise RuntimeError(
                f"benchmark CSV field {field!r} disagrees with summary"
            )
    for field, key in (
        ("relative_frobenius_error", "relative_frobenius_error"),
        ("max_absolute_error", "max_absolute_error"),
    ):
        expected = _json_nonnegative_number(correctness.get(key), key)
        if not _benchmark_close(float(first[field]), expected):
            raise RuntimeError(
                f"benchmark CSV correctness field {field!r} disagrees with summary"
            )
    input_prepare = _json_nonnegative_number(
        parsed.get("input_prepare_ms"), "input_prepare_ms"
    )
    if float(first["input_prepare_ms"]) != input_prepare:
        raise RuntimeError("benchmark CSV input_prepare_ms disagrees with summary")
    if parsed.get("numeric_speedup_basis") != (
        "serial_reset_plus_kernel_over_atomic_reset_plus_kernel"
    ):
        raise RuntimeError("benchmark numeric speedup basis is invalid")


def _v2_run_counts(
    configuration: Mapping[str, object],
    evidence_level: str,
) -> Tuple[int, int, int]:
    warmup = configuration.get("warmup_count")
    repeat = configuration.get("repeat_count")
    amortization = configuration.get("amortization_count")
    for label, value, minimum in (
        ("warmup_count", warmup, 0),
        ("repeat_count", repeat, 1),
        ("amortization_count", amortization, 1),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise RuntimeError(f"benchmark {label} is invalid")
    assert isinstance(warmup, int)
    assert isinstance(repeat, int)
    assert isinstance(amortization, int)
    if evidence_level == "formal" and (
        warmup != FORMAL_WARMUP_COUNT
        or repeat != FORMAL_REPEAT_COUNT
        or amortization != FORMAL_AMORTIZATION_COUNT
    ):
        raise RuntimeError(
            "formal benchmark evidence requires exactly warmup_count=2, "
            "repeat_count=7, and amortization_count=1"
        )
    return warmup, repeat, amortization


def _group_v2_samples(
    csv_rows: Sequence[Mapping[str, object]],
    requested: Sequence[int],
    evidence_level: str,
    warmup: int,
    repeat: int,
    amortization: int,
) -> Tuple[Dict[int, Dict[int, Mapping[str, object]]], Dict[int, Tuple[float, float]]]:
    sample_count = warmup + repeat
    if len(csv_rows) != len(requested) * sample_count:
        raise RuntimeError(
            "benchmark CSV row count does not equal threads times warmup-plus-repeat"
        )
    grouped: Dict[int, Dict[int, Mapping[str, object]]] = {
        thread: {} for thread in requested
    }
    serial_by_index: Dict[int, Tuple[float, float]] = {}
    for row in csv_rows:
        if row["schema_version"] != BENCHMARK_SCHEMA_V2:
            raise RuntimeError("benchmark CSV row schema_version is not v2")
        if row["performance_evidence_level"] != evidence_level:
            raise RuntimeError("benchmark CSV evidence level disagrees")
        if row["sample_kind"] not in {"warmup", "measured"}:
            raise RuntimeError("benchmark CSV sample_kind is invalid")
        if row["matrix_correctness_status"] not in {"PASS", "FAIL"}:
            raise RuntimeError("benchmark CSV correctness status is invalid")
        thread = int(row["thread_count"])
        sample_index = int(row["sample_index"])
        if thread not in grouped:
            raise RuntimeError(f"benchmark CSV has unexpected thread count {thread}")
        if sample_index in grouped[thread]:
            raise RuntimeError(
                f"benchmark CSV duplicates sample ({thread}, {sample_index})"
            )
        if sample_index < 0 or sample_index >= sample_count:
            raise RuntimeError("benchmark CSV sample_index is outside configuration")
        expected_kind = "warmup" if sample_index < warmup else "measured"
        if row["sample_kind"] != expected_kind:
            raise RuntimeError("benchmark CSV sample_kind disagrees with sample_index")
        grouped[thread][sample_index] = row
        serial_pair = (
            float(row["serial_symbolic_ms"]),
            float(row["serial_numeric_ms"]),
        )
        previous = serial_by_index.setdefault(sample_index, serial_pair)
        if previous != serial_pair:
            raise RuntimeError(
                "benchmark serial samples drift across thread configurations"
            )
        symbolic_sum = float(row["symbolic_pattern_ms"]) + float(
            row["symbolic_scatter_ms"]
        )
        if symbolic_sum > float(row["symbolic_total_ms"]) + 1.0e-6:
            raise RuntimeError("benchmark CSV symbolic phases exceed total")
        numeric_algorithm = float(row["numeric_reset_ms"]) + float(
            row["numeric_kernel_ms"]
        )
        if numeric_algorithm > float(row["numeric_total_ms"]) + 1.0e-6:
            raise RuntimeError("benchmark CSV numeric phases exceed total")
        expected_amortized = (
            float(row["symbolic_total_ms"]) / amortization
            + float(row["numeric_total_ms"])
        )
        if abs(float(row["amortized_total_ms"]) - expected_amortized) > (
            1.0e-12 * max(1.0, abs(expected_amortized))
        ):
            raise RuntimeError("benchmark CSV amortized timing is inconsistent")
    expected_indices = set(range(sample_count))
    for thread in requested:
        if set(grouped[thread]) != expected_indices:
            raise RuntimeError(
                f"benchmark CSV sample indices are incomplete for thread {thread}"
            )
    return grouped, serial_by_index


def _validate_v2_raw_samples(
    parsed: Mapping[str, object],
    csv_rows: Sequence[Mapping[str, object]],
    grouped: Mapping[int, Mapping[int, Mapping[str, object]]],
    requested: Sequence[int],
) -> None:
    raw = parsed.get("raw_samples")
    if not isinstance(raw, list) or len(raw) != len(csv_rows):
        raise RuntimeError("benchmark raw_samples count disagrees with CSV")
    raw_by_identity: Dict[Tuple[int, int], Mapping[str, object]] = {}
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise RuntimeError("benchmark raw_samples entry is invalid")
        thread = entry.get("thread_count")
        sample_index = entry.get("sample_index")
        if (
            not isinstance(thread, int)
            or isinstance(thread, bool)
            or not isinstance(sample_index, int)
            or isinstance(sample_index, bool)
        ):
            raise RuntimeError("benchmark raw_samples identity is invalid")
        identity = (thread, sample_index)
        if identity in raw_by_identity:
            raise RuntimeError("benchmark raw_samples identity is duplicated")
        raw_by_identity[identity] = entry
    for thread in requested:
        for sample_index, row in grouped[thread].items():
            entry = raw_by_identity.get((thread, sample_index))
            if entry is None:
                raise RuntimeError("benchmark raw_samples identity is missing")
            if not isinstance(entry.get("sample_kind"), str):
                raise RuntimeError("benchmark raw_samples sample_kind is invalid")
            for key in (
                "symbolic_plan_matches_serial",
                "numeric_setup_plan_matches_serial",
            ):
                if not isinstance(entry.get(key), bool):
                    raise RuntimeError(
                        f"benchmark raw_samples field {key!r} must be boolean"
                    )
            for key in (
                "sample_kind",
                "symbolic_plan_matches_serial",
                "numeric_setup_plan_matches_serial",
            ):
                if entry.get(key) != row[key]:
                    raise RuntimeError(
                        f"benchmark raw_samples field {key!r} disagrees with CSV"
                    )


def _recompute_v2_statistics(
    parsed: Mapping[str, object],
    grouped: Mapping[int, Mapping[int, Mapping[str, object]]],
    serial_by_index: Mapping[int, Tuple[float, float]],
    requested: Sequence[int],
    warmup: int,
    repeat: int,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    sample_count = warmup + repeat
    measured_indices = list(range(warmup, sample_count))
    serial = {
        "symbolic_total_ms": _benchmark_statistics(
            [serial_by_index[index][0] for index in measured_indices]
        ),
        "numeric_total_ms": _benchmark_statistics(
            [serial_by_index[index][1] for index in measured_indices]
        ),
    }
    serial_json = parsed.get("serial_measured_statistics")
    if not isinstance(serial_json, Mapping):
        raise RuntimeError("benchmark serial statistics are missing")
    for phase, values in serial.items():
        _compare_benchmark_statistics(
            serial_json.get(phase), values, f"serial {phase}"
        )

    json_rows = parsed.get("per_thread_measured_statistics")
    if not isinstance(json_rows, list) or [
        entry.get("thread_count") if isinstance(entry, Mapping) else None
        for entry in json_rows
    ] != requested:
        raise RuntimeError("benchmark per-thread summaries disagree with requested order")
    per_thread_statistics: List[Dict[str, object]] = []
    serial_symbolic_median = float(serial["symbolic_total_ms"]["median_ms"])
    serial_numeric_median = float(serial["numeric_total_ms"]["median_ms"])
    for thread, json_row in zip(requested, json_rows):
        assert isinstance(json_row, Mapping)
        all_samples = [grouped[thread][index] for index in range(sample_count)]
        measured = [grouped[thread][index] for index in measured_indices]
        phase_values = {
            "symbolic_pattern_ms": [float(row["symbolic_pattern_ms"]) for row in measured],
            "symbolic_scatter_ms": [float(row["symbolic_scatter_ms"]) for row in measured],
            "symbolic_total_ms": [float(row["symbolic_total_ms"]) for row in measured],
            "numeric_reset_ms": [float(row["numeric_reset_ms"]) for row in measured],
            "numeric_kernel_ms": [float(row["numeric_kernel_ms"]) for row in measured],
            "numeric_algorithm_ms": [
                float(row["numeric_reset_ms"]) + float(row["numeric_kernel_ms"])
                for row in measured
            ],
            "numeric_total_ms": [float(row["numeric_total_ms"]) for row in measured],
            "amortized_total_ms": [float(row["amortized_total_ms"]) for row in measured],
        }
        statistics_by_phase = {
            phase: _benchmark_statistics(values)
            for phase, values in phase_values.items()
        }
        for phase in _BENCHMARK_PHASES:
            _compare_benchmark_statistics(
                json_row.get(phase),
                statistics_by_phase[phase],
                f"thread {thread} {phase}",
            )
        symbolic_median = float(
            statistics_by_phase["symbolic_total_ms"]["median_ms"]
        )
        numeric_median = float(
            statistics_by_phase["numeric_algorithm_ms"]["median_ms"]
        )
        if symbolic_median <= 0.0 or numeric_median <= 0.0:
            raise RuntimeError("benchmark candidate timing medians must be positive")
        symbolic_speedup = serial_symbolic_median / symbolic_median
        numeric_speedup = serial_numeric_median / numeric_median
        for key, expected_speedup in (
            ("symbolic_speedup", symbolic_speedup),
            ("numeric_speedup", numeric_speedup),
        ):
            actual = _json_nonnegative_number(
                json_row.get(key), f"thread {thread} {key}"
            )
            if not _benchmark_close(actual, expected_speedup):
                raise RuntimeError(f"benchmark {key} disagrees with CSV medians")
            if any(float(row[key]) != actual for row in all_samples):
                raise RuntimeError(f"benchmark CSV {key} disagrees with summary")

        per_thread_statistics.append(
            {
                "thread_count": thread,
                **statistics_by_phase,
                "symbolic_speedup": symbolic_speedup,
                "numeric_speedup": numeric_speedup,
            }
        )
    return serial, per_thread_statistics


def _recompute_v2_scatter(
    parsed: Mapping[str, object],
    grouped: Mapping[int, Mapping[int, Mapping[str, object]]],
    requested: Sequence[int],
) -> Tuple[Dict[str, object], Dict[int, Dict[str, object]]]:
    root = {
        "symbolic_plan_check_count": 0,
        "symbolic_plan_match_count": 0,
        "numeric_setup_plan_check_count": 0,
        "numeric_setup_plan_match_count": 0,
        "status": "PASS",
    }
    json_rows = parsed.get("per_thread_measured_statistics")
    assert isinstance(json_rows, list)
    by_thread: Dict[int, Dict[str, object]] = {}
    for thread, json_row in zip(requested, json_rows):
        assert isinstance(json_row, Mapping)
        samples = list(grouped[thread].values())
        checks = len(samples)
        matches = sum(bool(row["symbolic_plan_matches_serial"]) for row in samples)
        numeric_values = {
            bool(row["numeric_setup_plan_matches_serial"]) for row in samples
        }
        if len(numeric_values) != 1:
            raise RuntimeError(
                f"benchmark numeric setup plan result drifts for thread {thread}"
            )
        numeric_matches = numeric_values == {True}
        status = "PASS" if matches == checks and numeric_matches else "FAIL"
        expected = {
            "symbolic_plan_check_count": checks,
            "symbolic_plan_match_count": matches,
            "numeric_setup_plan_matches_serial": numeric_matches,
            "scatter_status": status,
        }
        for key, value in expected.items():
            if key.endswith("_count"):
                _json_nonnegative_integer(json_row.get(key), f"thread {thread} {key}")
            elif key == "numeric_setup_plan_matches_serial" and not isinstance(
                json_row.get(key), bool
            ):
                raise RuntimeError(
                    f"benchmark thread {thread} numeric setup field must be boolean"
                )
            elif key == "scatter_status" and not isinstance(json_row.get(key), str):
                raise RuntimeError(
                    f"benchmark thread {thread} scatter status must be text"
                )
            if json_row.get(key) != value:
                raise RuntimeError(
                    f"benchmark thread {thread} scatter field {key!r} disagrees with CSV"
                )
        by_thread[thread] = expected
        root["symbolic_plan_check_count"] += checks
        root["symbolic_plan_match_count"] += matches
        root["numeric_setup_plan_check_count"] += 1
        root["numeric_setup_plan_match_count"] += int(numeric_matches)
        if status != "PASS":
            root["status"] = "FAIL"
    scatter_json = parsed.get("scatter_correctness")
    if not isinstance(scatter_json, Mapping):
        raise RuntimeError("benchmark scatter_correctness object is missing")
    for key, expected in root.items():
        if key.endswith("_count"):
            _json_nonnegative_integer(scatter_json.get(key), f"root scatter {key}")
        elif key == "status" and not isinstance(scatter_json.get(key), str):
            raise RuntimeError("benchmark root scatter status must be text")
        if scatter_json.get(key) != expected:
            raise RuntimeError(
                f"benchmark root scatter field {key!r} disagrees with CSV"
            )
    return root, by_thread


def _recompute_v2_gate(
    benchmark_case: object,
    evidence_level: str,
    requested: Sequence[int],
    serial: Mapping[str, object],
    per_thread_statistics: Sequence[Mapping[str, object]],
    scatter: Mapping[str, object],
) -> Dict[str, object]:
    thresholds = {
        "numeric_speedup_threshold": 1.5,
        "symbolic_speedup_threshold": 1.0,
        "maximum_coefficient_of_variation": 0.05,
    }
    numeric_thread = 0
    symbolic_thread = 0
    by_thread = {int(row["thread_count"]): row for row in per_thread_statistics}
    for thread in requested:
        row = by_thread[thread]
        thread = int(row["thread_count"])
        if thread == 1:
            continue
        numeric = row["numeric_algorithm_ms"]
        symbolic = row["symbolic_total_ms"]
        assert isinstance(numeric, Mapping)
        assert isinstance(symbolic, Mapping)
        if (
            numeric_thread == 0
            and float(row["numeric_speedup"]) >= 1.5
            and float(numeric["coefficient_of_variation"]) <= 0.05
        ):
            numeric_thread = thread
        if (
            symbolic_thread == 0
            and float(row["symbolic_speedup"]) > 1.0
            and float(symbolic["coefficient_of_variation"]) <= 0.05
        ):
            symbolic_thread = thread
    serial_symbolic_cv_met = (
        float(serial["symbolic_total_ms"]["coefficient_of_variation"]) <= 0.05
    )
    serial_numeric_cv_met = (
        float(serial["numeric_total_ms"]["coefficient_of_variation"]) <= 0.05
    )
    if benchmark_case in {"generated-tet4", "generated-hex8"}:
        expected_gate: Dict[str, object] = {
            "status": "NOT_APPLICABLE_GENERATED_CASE",
            "applicable": False,
            "performance_requirements_met": False,
            "numeric_requirement_met": False,
            "symbolic_requirement_met": False,
            "serial_symbolic_cv_requirement_met": False,
            "serial_numeric_cv_requirement_met": False,
            "scatter_requirement_met": False,
            "formal_requirements_met": False,
            "numeric_thread_count": 0,
            "symbolic_thread_count": 0,
            **thresholds,
        }
    elif benchmark_case == "windhub":
        numeric_met = numeric_thread != 0
        symbolic_met = symbolic_thread != 0
        formal = evidence_level == "formal"
        performance_met = (
            numeric_met
            and symbolic_met
            and serial_symbolic_cv_met
            and serial_numeric_cv_met
            if formal
            else False
        )
        formal_met = (
            performance_met and scatter.get("status") == "PASS" if formal else False
        )
        expected_gate = {
            "status": (
                ("PASS" if formal_met else "FAIL")
                if formal
                else (
                    "NON_FORMAL_CI_SMOKE"
                    if evidence_level == "ci-smoke"
                    else "NON_FORMAL_LOCAL_SMOKE"
                )
            ),
            "applicable": True,
            "performance_requirements_met": performance_met,
            "numeric_requirement_met": numeric_met,
            "symbolic_requirement_met": symbolic_met,
            "serial_symbolic_cv_requirement_met": serial_symbolic_cv_met,
            "serial_numeric_cv_requirement_met": serial_numeric_cv_met,
            "scatter_requirement_met": scatter.get("status") == "PASS",
            "formal_requirements_met": formal_met,
            "numeric_thread_count": numeric_thread,
            "symbolic_thread_count": symbolic_thread,
            **thresholds,
        }
    else:
        raise RuntimeError("benchmark configuration case is unsupported")
    return expected_gate


def _compare_v2_gate(
    parsed: Mapping[str, object], expected_gate: Mapping[str, object]
) -> None:
    thresholds = {
        "numeric_speedup_threshold",
        "symbolic_speedup_threshold",
        "maximum_coefficient_of_variation",
    }
    gate = parsed.get("performance_gate")
    if not isinstance(gate, Mapping):
        raise RuntimeError("benchmark performance_gate object is missing")
    for key, expected in expected_gate.items():
        actual = gate.get(key)
        if key in thresholds:
            actual_number = _json_nonnegative_number(
                actual, f"performance_gate.{key}"
            )
            if actual_number != float(expected):
                raise RuntimeError(
                    f"benchmark performance gate threshold {key!r} is invalid"
                )
        else:
            if isinstance(expected, bool) and not isinstance(actual, bool):
                raise RuntimeError(
                    f"benchmark performance gate field {key!r} must be boolean"
                )
            if isinstance(expected, int) and not isinstance(expected, bool):
                _json_nonnegative_integer(actual, f"performance_gate.{key}")
            if isinstance(expected, str) and not isinstance(actual, str):
                raise RuntimeError(
                    f"benchmark performance gate field {key!r} must be text"
                )
        if key not in thresholds and actual != expected:
            raise RuntimeError(
                f"benchmark performance gate field {key!r} disagrees with CSV"
            )
    if parsed.get("performance_gate_status") != expected_gate["status"]:
        raise RuntimeError("benchmark performance_gate_status disagrees with CSV")


def recompute_benchmark_v2_evidence(
    parsed: Mapping[str, object],
    samples_csv_path: Union[str, Path, bytes],
    requested_thread_counts: Sequence[int],
    evidence_level: str,
    configuration: Mapping[str, object],
) -> Dict[str, object]:
    """Recompute the canonical v2 CSV/JSON contract for runner and report."""

    csv_rows = _parse_benchmark_v2_csv(samples_csv_path)
    requested = list(requested_thread_counts)
    _validate_v2_cross_file_fields(parsed, csv_rows, evidence_level, configuration)
    warmup, repeat, amortization = _v2_run_counts(configuration, evidence_level)
    grouped, serial_by_index = _group_v2_samples(
        csv_rows, requested, evidence_level, warmup, repeat, amortization
    )
    _validate_v2_raw_samples(parsed, csv_rows, grouped, requested)
    serial, per_thread = _recompute_v2_statistics(
        parsed, grouped, serial_by_index, requested, warmup, repeat
    )
    scatter, scatter_by_thread = _recompute_v2_scatter(
        parsed, grouped, requested
    )
    combined = []
    for row in per_thread:
        enriched = dict(row)
        enriched.update(scatter_by_thread[int(row["thread_count"])])
        combined.append(enriched)
    gate = _recompute_v2_gate(
        configuration.get("case"),
        evidence_level,
        requested,
        serial,
        combined,
        scatter,
    )
    _compare_v2_gate(parsed, gate)
    return {
        "serial": serial,
        "per_thread": tuple(combined),
        "scatter": scatter,
        "gate": gate,
        "csv_rows": tuple(csv_rows),
    }


def _validate_benchmark_summary(
    path: Union[str, Path],
    requested_thread_counts: Sequence[int],
    expected_evidence_level: Optional[str] = None,
    expected_configuration: Optional[Mapping[str, object]] = None,
    samples_csv_path: Optional[Union[str, Path, bytes]] = None,
    require_current_schema: bool = False,
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
    schema_version = parsed.get("schema_version")
    if schema_version not in {BENCHMARK_SCHEMA_V1, BENCHMARK_SCHEMA_V2}:
        raise RuntimeError("benchmark summary schema_version is unsupported")
    evidence_level = parsed.get("performance_evidence_level")
    if evidence_level not in {"ci-smoke", "local-smoke", "formal"}:
        raise RuntimeError("benchmark performance_evidence_level is missing or invalid")
    if expected_evidence_level is not None and evidence_level != expected_evidence_level:
        raise RuntimeError(
            "benchmark performance_evidence_level does not match the workflow request"
        )
    if schema_version == BENCHMARK_SCHEMA_V1 and (
        require_current_schema or evidence_level != "local-smoke"
    ):
        raise RuntimeError(
            "legacy benchmark v1 is read-only local-smoke evidence and cannot be current or formal"
        )
    if schema_version == BENCHMARK_SCHEMA_V2 and samples_csv_path is None:
        raise RuntimeError("benchmark v2 validation requires the samples CSV")
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
    structure_matches = correctness.get("structure_matches")
    if not isinstance(structure_matches, bool):
        raise RuntimeError("benchmark root matrix structure flag is invalid")
    correctness_metrics: Dict[str, float] = {}
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
        correctness_metrics[key] = float(value)
    _validate_comparison_failure_representation(
        structure_matches,
        correctness_metrics["relative_frobenius_error"],
        correctness_metrics["max_absolute_error"],
        "root matrix comparison",
    )
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
    expected_correctness_status = (
        "PASS"
        if structure_matches
        and float(correctness["relative_frobenius_error"]) <= 1.0e-8
        and float(correctness["max_absolute_error"])
        <= float(correctness["max_absolute_tolerance"])
        else "FAIL"
    )
    if correctness.get("status") != expected_correctness_status:
        raise RuntimeError(
            "benchmark root correctness status contradicts its finite metrics"
        )

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
        matrix = validation.get("matrix")
        if not isinstance(matrix, Mapping):
            raise RuntimeError("benchmark validation matrix evidence is missing")
        if not isinstance(matrix.get("structure_matches"), bool):
            raise RuntimeError("benchmark validation matrix structure flag is invalid")
        relative_frobenius_error = validation_metric(
            matrix, "relative_frobenius_error", "matrix"
        )
        max_absolute_error = validation_metric(
            matrix, "max_absolute_error", "matrix"
        )
        _validate_comparison_failure_representation(
            bool(matrix["structure_matches"]),
            relative_frobenius_error,
            max_absolute_error,
            "validation matrix comparison",
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
        expected_matrix_status = (
            "PASS"
            if matrix.get("structure_matches") is True
            and relative_frobenius_error <= 1.0e-8
            and max_absolute_error <= max_absolute_tolerance
            else "FAIL"
        )
        if matrix.get("status") != expected_matrix_status:
            raise RuntimeError(
                "benchmark validation matrix status contradicts its finite metrics"
            )

        displacement = validation.get("displacement")
        if not isinstance(displacement, Mapping):
            raise RuntimeError(
                "benchmark validation displacement evidence is missing"
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
        if parallel_displacement_norm <= 0.0 or serial_displacement_norm <= 0.0:
            raise RuntimeError(
                "benchmark validation displacement norm must be positive"
            )
        expected_displacement_status = (
            "PASS"
            if relative_displacement_error <= 1.0e-8
            and parallel_relative_residual <= 1.0e-10
            and serial_relative_residual <= 1.0e-10
            else "FAIL"
        )
        if displacement.get("status") != expected_displacement_status:
            raise RuntimeError(
                "benchmark validation displacement status contradicts its finite metrics"
            )
        expected_validation_status = (
            "PASS"
            if expected_matrix_status == "PASS"
            and expected_displacement_status == "PASS"
            else "FAIL"
        )
        if validation.get("status") != expected_validation_status:
            raise RuntimeError(
                "benchmark validation case status contradicts component statuses"
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

    if schema_version == BENCHMARK_SCHEMA_V2:
        assert samples_csv_path is not None
        recompute_benchmark_v2_evidence(
            parsed,
            samples_csv_path,
            requested_thread_counts,
            evidence_level,
            configuration,
        )
        return parsed, observed

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
    samples_csv_path: Optional[Union[str, Path, bytes]] = None,
    require_current_schema: bool = False,
) -> Tuple[Dict[str, object], List[int]]:
    """Validate JSON evidence and translate numeric conversion failures."""

    try:
        return _validate_benchmark_summary(
            path,
            requested_thread_counts,
            expected_evidence_level,
            expected_configuration,
            samples_csv_path,
            require_current_schema,
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


def _runner_python_executable() -> str:
    """Return the runner interpreter path without resolving virtual-env links."""

    executable = str(sys.executable)
    if not executable or not Path(executable).is_absolute():
        raise RuntimeError(
            "benchmark runner requires an absolute sys.executable"
        )
    return executable


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
    formal_host_facts: Dict[str, object] = {}
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
        except OSError:
            pass
        formal_host_facts = collect_formal_host_facts()
        observed_physical = formal_host_facts.get("physical_core_count")
        if isinstance(observed_physical, int) and not isinstance(
            observed_physical, bool
        ):
            physical_core_count = observed_physical
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
    if physical_core_count is None and platform.system() != "Linux":
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
    runner_python_executable = _runner_python_executable()
    cmake_python_executable = cache_values.get("_Python3_EXECUTABLE")
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
            **formal_host_facts,
        },
        "toolchain": {
            "cmake_version": cmake_version_match.group(1) if cmake_version_match else "unknown",
            "compiler": compiler,
            "compiler_id": compiler_id,
            "compiler_version": compiler_version,
            "compiler_path": compiler_path,
            "compiler_banner": compiler_banner,
            "runner_python_executable": runner_python_executable,
            "cmake_python_executable": cmake_python_executable,
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
    if options.evidence_level == "formal" and (
        options.warmup != FORMAL_WARMUP_COUNT
        or options.repeat != FORMAL_REPEAT_COUNT
        or options.amortization_count != FORMAL_AMORTIZATION_COUNT
    ):
        raise ValueError(
            "formal evidence requires --warmup 2 --repeat 7 "
            "--amortization-count 1"
        )
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
_HOST_IDENTITY_KEYS: Tuple[str, ...] = (
    "online_cpu_ids",
    "affinity_cpu_ids",
    "cpuset_cpu_ids",
    "cpuset_memory_ids",
    "physical_core_ids",
    "full_host_affinity",
    "formal_environment",
    "conflicting_environment_keys",
    "topology_errors",
    "collection_errors",
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
    *,
    initial_host: Optional[Mapping[str, object]] = None,
    observed_host: Optional[Mapping[str, object]] = None,
) -> Dict[str, object]:
    """Compare one formal source, input, and Linux-host observation."""

    if phase not in _IDENTITY_PHASES:
        raise ValueError(f"unsupported identity-check phase: {phase}")
    source = _identity_snapshot(observed_source, _SOURCE_IDENTITY_KEYS)
    input_facts = _identity_snapshot(observed_input, _INPUT_IDENTITY_KEYS)
    expected_source = _identity_snapshot(initial_source, _SOURCE_IDENTITY_KEYS)
    expected_input = _identity_snapshot(initial_input, _INPUT_IDENTITY_KEYS)
    host = _identity_snapshot(observed_host or {}, _HOST_IDENTITY_KEYS)
    expected_host = _identity_snapshot(initial_host or {}, _HOST_IDENTITY_KEYS)
    errors: List[str] = []
    for key in _SOURCE_IDENTITY_KEYS:
        if source[key] != expected_source[key]:
            errors.append(f"source identity drift at {phase}: {key}")
    for key in _INPUT_IDENTITY_KEYS:
        if input_facts[key] != expected_input[key]:
            errors.append(f"input identity drift at {phase}: {key}")
    for key in _HOST_IDENTITY_KEYS:
        if host[key] != expected_host[key]:
            errors.append(f"formal host identity drift at {phase}: {key}")
    return {
        "phase": phase,
        "status": "PASS" if not errors else "FAIL",
        "source": source,
        "input": input_facts,
        "host": host,
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
        "amortization_count": options.amortization_count,
        "requested_thread_counts": list(requested_threads),
        "physical_core_count": environment.get("physical_core_count"),
        "formal_host": environment.get("formal_host"),
        "formal_environment": environment.get("formal_environment"),
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
    runner_python_executable = str(
        facts.get("runner_python_executable") or ""
    )
    cmake_python_executable = str(
        facts.get("cmake_python_executable") or ""
    )
    if not runner_python_executable:
        blockers.append(
            "formal evidence requires an identified benchmark-runner Python executable"
        )
    if not cmake_python_executable:
        blockers.append(
            "formal evidence requires an identified CMake Python executable"
        )
    if (
        runner_python_executable
        and cmake_python_executable
        and runner_python_executable != cmake_python_executable
    ):
        blockers.append(
            "formal evidence requires the CMake Python executable to exactly "
            "match the benchmark-runner Python executable"
        )
    return blockers


def _command_plan(
    options: argparse.Namespace,
    source_root: Path,
    build_root: Path,
    output_root: Path,
    requested_threads: Sequence[int],
    benchmark_executable: Path,
) -> Dict[str, List[str]]:
    runner_python_executable = _runner_python_executable()
    configure = [
        "cmake",
        "--preset",
        options.preset,
        "-B",
        str(build_root),
        "-DPython3_EXECUTABLE:FILEPATH=" + runner_python_executable,
    ]
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
        raise RuntimeError(
            "formal evidence preflight BLOCKED: " + "; ".join(preflight_blockers)
        )

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
    initial_environment = provenance.get("environment")
    initial_environment = (
        initial_environment if isinstance(initial_environment, Mapping) else {}
    )
    initial_host = initial_environment.get("formal_host")
    initial_host = initial_host if isinstance(initial_host, Mapping) else {}
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
    inherited_environment = {str(key): str(value) for key, value in os.environ.items()}
    command_environment = (
        sanitized_formal_environment(inherited_environment)
        if options.evidence_level == "formal"
        else {**inherited_environment, **REQUIRED_OPENMP_ENV}
    )

    def invoke(command: Sequence[str], cwd: Path) -> CommandResult:
        try:
            result = runner(command, cwd, command_environment)
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
            observed_environment = current_provenance.get("environment")
            observed_environment = (
                observed_environment
                if isinstance(observed_environment, Mapping)
                else {}
            )
            observed_host = observed_environment.get("formal_host")
            observed_host = (
                observed_host if isinstance(observed_host, Mapping) else {}
            )
            observed_input = _input_provenance(options, repository_root)
            record = _identity_check_record(
                phase,
                source_facts,
                observed_source,
                input_facts,
                observed_input,
                initial_host=initial_host,
                observed_host=observed_host,
            )
        except Exception as error:
            record = {
                "phase": phase,
                "status": "FAIL",
                "source": {},
                "input": {},
                "host": {},
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
                samples_csv_path=csv_path,
                require_current_schema=True,
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
