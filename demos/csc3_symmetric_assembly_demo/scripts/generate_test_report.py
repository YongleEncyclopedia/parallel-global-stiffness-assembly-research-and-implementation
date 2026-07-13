#!/usr/bin/env python3
"""Validate hash-bound evidence for the CSC3 delivery report.

This task deliberately exposes an importable validation core only.  Markdown
rendering and command-line output belong to the following delivery task.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List, Mapping, Sequence, Tuple


MANIFEST_SCHEMA_VERSION = "csc3-demo-benchmark-run-v1"
CANONICAL_WINDHUB_PATH = "examples/3d-WindTurbineHub.inp"
MEMORY_KIND = "owned_vector_payload_bytes_not_rss"
NUMERIC_SPEEDUP_BASIS = "serial_reset_plus_kernel_over_atomic_reset_plus_kernel"
DOUBLE_EPSILON = float.fromhex("0x1.0000000000000p-52")
TIMING_TOLERANCE_MS = 1.0e-6

CSV_HEADER = (
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

JUNIT_NAMES = (
    "Csc3DemoTests",
    "Csc3DemoConsumer",
    "Csc3DemoCorrectness",
    "Csc3DemoBenchmarkTiming",
    "Csc3DemoBenchmarkEngine",
    "Csc3DemoBenchmarkIo",
    "Csc3DemoInpCase",
    "Csc3DemoWindHubBenchmark",
    "Csc3DemoBenchmarkRunner",
)

REQUIRED_ARTIFACTS = (
    "ctest.xml",
    "benchmark_samples.csv",
    "benchmark_summary.json",
    "summary.md",
)

REQUIRED_BINDING_ENVIRONMENT = {
    "OMP_DYNAMIC": "false",
    "OMP_PROC_BIND": "close",
    "OMP_PLACES": "cores",
}

INTEGER_FIELDS = {
    "nx", "ny", "nz", "node_count", "element_count", "dof_count", "nnz",
    "thread_count", "sample_index", "estimated_persistent_bytes",
}

POSITIVE_INTEGER_FIELDS = {
    "node_count", "element_count", "dof_count", "nnz", "thread_count",
}

FLOAT_FIELDS = {
    "input_prepare_ms", "serial_symbolic_ms", "serial_numeric_ms",
    "symbolic_pattern_ms", "symbolic_scatter_ms", "symbolic_total_ms",
    "numeric_reset_ms", "numeric_kernel_ms", "numeric_total_ms",
    "amortized_total_ms", "symbolic_speedup", "numeric_speedup",
    "relative_frobenius_error", "max_absolute_error",
}

PER_THREAD_PHASES = (
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_total_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_algorithm_ms",
    "numeric_total_ms",
    "amortized_total_ms",
)

STATISTIC_KEYS = (
    "mean_ms",
    "median_ms",
    "population_standard_deviation_ms",
    "minimum_ms",
    "maximum_ms",
    "coefficient_of_variation",
)

_FLOAT_TEXT = re.compile(
    r"-?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)
_INTEGER_TEXT = re.compile(r"0|[1-9][0-9]*")
_SHA40 = re.compile(r"[0-9a-fA-F]{40}")
_SHA64 = re.compile(r"[0-9a-fA-F]{64}")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


class EvidenceValidationError(RuntimeError):
    """Raised when an evidence bundle violates its integrity contract."""


@dataclass(frozen=True)
class EvidenceBundle:
    manifest: Mapping[str, object]
    benchmark_summary: Mapping[str, object]
    csv_rows: Tuple[Mapping[str, object], ...]
    recomputed_statistics: Mapping[str, object]
    recomputed_gate: Mapping[str, object]
    junit_testcase_names: Tuple[str, ...]
    artifact_paths: Mapping[str, Path]
    report_status: str


def _load_runner() -> object:
    path = Path(__file__).resolve().with_name("run_benchmark.py")
    module_name = "csc3_report_runner_contract"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load benchmark runner contract: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


RUNNER = _load_runner()


def _error(message: str) -> EvidenceValidationError:
    return EvidenceValidationError(message)


def _is_int(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _require_object(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, Mapping):
        raise _error(f"manifest field {key!r} must be an object")
    return value


def _require_list(container: Mapping[str, object], key: str) -> List[object]:
    value = container.get(key)
    if not isinstance(value, list):
        raise _error(f"manifest field {key!r} must be a list")
    return value


def _utc_timestamp(value: object, label: str) -> datetime:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value.endswith("Z")
    ):
        raise _error(f"manifest {label} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise _error(f"manifest {label} is not a valid UTC timestamp") from error
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise _error(f"manifest {label} must be UTC")
    return parsed


def _validate_manifest(manifest: object) -> Tuple[Mapping[str, object], List[int]]:
    if not isinstance(manifest, Mapping):
        raise _error("manifest root must be a JSON object")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise _error("manifest schema_version is unsupported")
    status = manifest.get("status")
    if status == "PENDING":
        raise _error("manifest status cannot be PENDING")
    if status not in {"LOCAL_SMOKE", "BLOCKED", "PASS", "FAIL"}:
        raise _error("manifest status is invalid")

    source = _require_object(manifest, "source")
    environment = _require_object(manifest, "environment")
    toolchain = _require_object(manifest, "toolchain")
    input_facts = _require_object(manifest, "input")
    benchmark = _require_object(manifest, "benchmark")
    commands = _require_object(manifest, "commands")
    tasks = _require_list(manifest, "tasks")
    blockers = _require_list(manifest, "blockers")
    _require_list(manifest, "artifacts")

    if _SHA40.fullmatch(str(source.get("commit_sha") or "")) is None:
        raise _error("manifest source.commit_sha must be exactly 40 hexadecimal characters")
    if not isinstance(source.get("source_dirty_at_start"), bool):
        raise _error("manifest source.source_dirty_at_start must be boolean")
    branch = source.get("branch")
    if not isinstance(branch, str) or not branch.strip():
        raise _error("manifest source.branch must be nonempty")
    version = source.get("demo_version")
    if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
        raise _error("manifest source.demo_version must be major.minor.patch")

    started = _utc_timestamp(manifest.get("started_at_utc"), "started_at_utc")
    ended = _utc_timestamp(manifest.get("ended_at_utc"), "ended_at_utc")
    if ended < started:
        raise _error("manifest ended_at_utc precedes started_at_utc")

    evidence_level = manifest.get("evidence_level")
    if evidence_level not in {"ci-smoke", "local-smoke", "formal"}:
        raise _error("manifest evidence_level is invalid")
    if manifest.get("report_intent") not in {"local-smoke", "delivery"}:
        raise _error("manifest report_intent is invalid")

    requested_raw = benchmark.get("requested_thread_counts")
    observed_raw = benchmark.get("observed_thread_counts")
    if not isinstance(requested_raw, list) or not isinstance(observed_raw, list):
        raise _error("manifest requested/observed thread counts must be lists")
    if (
        not requested_raw
        or any(not _is_int(value, minimum=1) for value in requested_raw)
        or len(requested_raw) != len(set(requested_raw))
    ):
        raise _error("manifest requested thread counts must be unique positive integers")
    if (
        any(not _is_int(value, minimum=1) for value in observed_raw)
        or len(observed_raw) != len(set(observed_raw))
        or observed_raw != requested_raw
    ):
        raise _error("manifest observed threads must equal requested threads in order")
    for key, minimum in (
        ("warmup_count", 0),
        ("repeat_count", 1),
        ("amortization_count", 1),
    ):
        if not _is_int(benchmark.get(key), minimum=minimum):
            raise _error(f"manifest benchmark.{key} is invalid")

    binding = manifest.get("binding_environment")
    if not isinstance(binding, Mapping) or dict(binding) != REQUIRED_BINDING_ENVIRONMENT:
        raise _error("manifest binding environment is not the required fixed OpenMP binding")

    case = input_facts.get("case")
    if case not in {"generated-tet4", "generated-hex8", "windhub"}:
        raise _error("manifest input.case is unsupported")
    if case.startswith("generated-"):
        grid = input_facts.get("grid")
        if not isinstance(grid, Mapping) or any(
            not _is_int(grid.get(axis), minimum=1) for axis in ("nx", "ny", "nz")
        ):
            raise _error("manifest generated input grid is invalid")

    if any(not isinstance(item, Mapping) for item in tasks):
        raise _error("manifest task entries must be objects")
    if any(not isinstance(item, str) for item in blockers):
        raise _error("manifest blocker entries must be strings")
    if not isinstance(environment, Mapping) or not isinstance(toolchain, Mapping):
        raise _error("manifest environment and toolchain must be objects")
    if any(not isinstance(key, str) for key in commands):
        raise _error("manifest command names must be strings")
    return manifest, list(requested_raw)


def _safe_relative_path(raw: object) -> Tuple[str, ...]:
    if not isinstance(raw, str) or not raw:
        raise _error("artifact path must be a nonempty POSIX relative path")
    if raw.startswith("/") or ":" in raw or "\\" in raw:
        raise _error(f"artifact path is unsafe: {raw!r}")
    components = tuple(raw.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise _error(f"artifact path has an empty or dot component: {raw!r}")
    return components


def _validate_artifacts(
    root: Path, records: Sequence[object]
) -> Tuple[Dict[str, Path], Dict[str, bytes]]:
    paths: Dict[str, Path] = {}
    contents: Dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise _error("manifest artifact entries must be objects")
        raw_path = record.get("path")
        components = _safe_relative_path(raw_path)
        assert isinstance(raw_path, str)
        if raw_path in paths:
            raise _error(f"duplicate artifact binding: {raw_path}")
        size = record.get("size_bytes")
        if not _is_int(size, minimum=0):
            raise _error(f"artifact {raw_path!r} has an invalid size")
        expected_digest = record.get("sha256")
        if not isinstance(expected_digest, str) or _SHA64.fullmatch(expected_digest) is None:
            raise _error(f"artifact {raw_path!r} has an invalid SHA-256")
        candidate = root.joinpath(*components)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError) as error:
            raise _error(f"artifact {raw_path!r} escapes or is missing from the manifest root") from error
        if not resolved.is_file():
            raise _error(f"artifact {raw_path!r} is not a regular file")
        try:
            content = resolved.read_bytes()
        except OSError as error:
            raise _error(f"cannot read artifact {raw_path!r}: {error}") from error
        if len(content) != size:
            raise _error(f"artifact {raw_path!r} size does not match the manifest")
        digest = hashlib.sha256(content).hexdigest()
        if digest.lower() != expected_digest.lower():
            raise _error(f"artifact {raw_path!r} SHA-256 does not match the manifest")
        paths[raw_path] = resolved
        contents[raw_path] = content
    missing = set(REQUIRED_ARTIFACTS) - set(paths)
    if missing:
        raise _error("manifest is missing required artifact bindings: " + ", ".join(sorted(missing)))
    return paths, contents


def _xml_local_name(tag: object) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _root_count(root: ElementTree.Element, name: str, *, required: bool) -> int:
    raw = root.attrib.get(name)
    if raw is None:
        if required:
            raise _error(f"CTest JUnit root {name!r} count is missing")
        return 0
    if _INTEGER_TEXT.fullmatch(raw) is None:
        raise _error(f"CTest JUnit root {name!r} count is missing or invalid")
    value = int(raw)
    if name != "tests" and value != 0:
        raise _error(f"CTest JUnit root {name!r} count is not zero")
    return value


def _validate_junit(path: Path, content: bytes) -> Tuple[str, ...]:
    try:
        RUNNER.validate_ctest_junit(path)
    except RuntimeError as error:
        raise _error(str(error)) from error
    try:
        if path.read_bytes() != content:
            raise _error("CTest JUnit changed after artifact hash validation")
    except OSError as error:
        raise _error(f"cannot re-read CTest JUnit after validation: {error}") from error
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise _error(f"CTest JUnit output is invalid XML: {error}") from error
    testcases = [node for node in root.iter() if _xml_local_name(node.tag) == "testcase"]
    if _root_count(root, "tests", required=True) != len(testcases):
        raise _error("CTest JUnit root test count does not match testcase elements")
    for name in ("failures", "errors", "skipped", "disabled"):
        _root_count(root, name, required=False)
    if len(testcases) != len(JUNIT_NAMES):
        raise _error("CTest JUnit does not contain exactly nine testcase elements")

    names: List[str] = []
    forbidden_states = {
        "notrun", "not run", "not-run", "skipped", "disabled",
        "failed", "failure", "error", "errored",
    }
    for testcase in testcases:
        name = testcase.attrib.get("name")
        if not isinstance(name, str) or not name.strip():
            raise _error("CTest JUnit testcase name is empty")
        names.append(name)
        for attribute in ("status", "result"):
            state = str(testcase.attrib.get(attribute, "")).strip().lower()
            if state in forbidden_states:
                raise _error(f"CTest JUnit testcase {name!r} is not run")
        disabled = str(testcase.attrib.get("disabled", "")).strip().lower()
        if disabled not in {"", "0", "false"}:
            raise _error(f"CTest JUnit testcase {name!r} is disabled")
        child_names = {_xml_local_name(child.tag) for child in testcase.iter()}
        if child_names.intersection({"failure", "error", "skipped"}):
            raise _error(f"CTest JUnit testcase {name!r} is not clean")
    if len(names) != len(set(names)):
        raise _error("CTest JUnit testcase names are duplicated")
    if set(names) != set(JUNIT_NAMES):
        raise _error("CTest JUnit testcase inventory is not exact")
    return tuple(names)


def _parse_integer(text: str, field: str) -> int:
    if _INTEGER_TEXT.fullmatch(text) is None:
        raise _error(f"CSV field {field!r} is not a strict decimal integer")
    value = int(text)
    if field in POSITIVE_INTEGER_FIELDS and value <= 0:
        raise _error(f"CSV field {field!r} must be positive")
    return value


def _parse_float(text: str, field: str) -> float:
    if _FLOAT_TEXT.fullmatch(text) is None:
        raise _error(f"CSV field {field!r} is not a strict finite number")
    value = float(text)
    if not math.isfinite(value) or value < 0.0:
        raise _error(f"CSV field {field!r} must be finite and nonnegative")
    return value


def _parse_csv(content: bytes) -> Tuple[Dict[str, object], ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise _error(f"benchmark samples CSV is not UTF-8: {error}") from error
    try:
        raw_rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        raise _error(f"benchmark samples CSV is malformed: {error}") from error
    if not raw_rows or tuple(raw_rows[0]) != CSV_HEADER:
        raise _error("benchmark samples CSV header is not the exact 30-column contract")
    parsed: List[Dict[str, object]] = []
    for row_index, values in enumerate(raw_rows[1:], start=2):
        if not values or all(value == "" for value in values):
            raise _error(f"benchmark samples CSV contains an empty row at line {row_index}")
        if len(values) != len(CSV_HEADER):
            raise _error(f"benchmark samples CSV row {row_index} has unexpected fields")
        row: Dict[str, object] = {}
        for field, raw in zip(CSV_HEADER, values):
            if raw != raw.strip() or raw == "":
                raise _error(f"CSV field {field!r} is empty or has surrounding whitespace")
            if field in INTEGER_FIELDS:
                row[field] = _parse_integer(raw, field)
            elif field in FLOAT_FIELDS:
                row[field] = _parse_float(raw, field)
            else:
                row[field] = raw
        parsed.append(row)
    if not parsed:
        raise _error("benchmark samples CSV contains no data rows")
    return tuple(parsed)


def _json_number(value: object, label: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise _error(f"{label} must be finite and nonnegative")
    return float(value)


def _close(actual: float, expected: float) -> bool:
    if not math.isfinite(actual) or not math.isfinite(expected):
        return False
    tolerance = 64.0 * DOUBLE_EPSILON * max(1.0, abs(actual), abs(expected))
    return abs(actual - expected) <= tolerance


def _statistics(values: Sequence[float]) -> Dict[str, object]:
    if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
        raise _error("statistics require finite nonnegative measured values")
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
        standard_deviation = float(variance.sqrt())
    middle = len(ordered) // 2
    median = (
        ordered[middle - 1] + (ordered[middle] - ordered[middle - 1]) / 2.0
        if len(ordered) % 2 == 0
        else ordered[middle]
    )
    if mean == 0.0:
        if ordered[-1] != 0.0:
            raise _error("zero-mean nonzero samples have undefined coefficient of variation")
        coefficient = 0.0
    else:
        coefficient = standard_deviation / mean
    if any(not math.isfinite(value) for value in (mean, median, standard_deviation, coefficient)):
        raise _error("recomputed statistics are not finite")
    return {
        "sample_count": len(values),
        "mean_ms": mean,
        "median_ms": median,
        "population_standard_deviation_ms": standard_deviation,
        "minimum_ms": ordered[0],
        "maximum_ms": ordered[-1],
        "coefficient_of_variation": coefficient,
    }


def _compare_statistics(actual: object, expected: Mapping[str, object], label: str) -> None:
    if not isinstance(actual, Mapping):
        raise _error(f"benchmark summary {label} statistics are missing")
    count = actual.get("sample_count")
    if not _is_int(count, minimum=1) or count != expected["sample_count"]:
        raise _error(f"benchmark summary {label} sample_count disagrees with CSV")
    for key in STATISTIC_KEYS:
        actual_value = _json_number(actual.get(key), f"benchmark summary {label}.{key}")
        expected_value = float(expected[key])
        if not _close(actual_value, expected_value):
            raise _error(f"benchmark summary {label}.{key} disagrees with CSV")


def _expected_configuration(manifest: Mapping[str, object]) -> Dict[str, object]:
    benchmark = manifest["benchmark"]
    input_facts = manifest["input"]
    assert isinstance(benchmark, Mapping)
    assert isinstance(input_facts, Mapping)
    case = input_facts["case"]
    if case == "windhub":
        nx = ny = nz = 0
    else:
        grid = input_facts["grid"]
        assert isinstance(grid, Mapping)
        nx, ny, nz = grid["nx"], grid["ny"], grid["nz"]
    return {
        "case": case,
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "thread_counts": list(benchmark["requested_thread_counts"]),
        "warmup_count": benchmark["warmup_count"],
        "repeat_count": benchmark["repeat_count"],
        "amortization_count": benchmark["amortization_count"],
        "performance_evidence_level": manifest["evidence_level"],
    }


def _strict_summary(
    path: Path,
    content: bytes,
    manifest: Mapping[str, object],
    requested: Sequence[int],
) -> Mapping[str, object]:
    try:
        parsed, _ = RUNNER.validate_benchmark_summary(
            path,
            requested,
            manifest["evidence_level"],
            _expected_configuration(manifest),
        )
    except RuntimeError as error:
        raise _error(str(error)) from error
    try:
        bound = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise _error(f"benchmark summary is invalid UTF-8 JSON: {error}") from error
    if not isinstance(bound, Mapping) or parsed != bound:
        raise _error("benchmark summary changed after artifact hash validation")
    return parsed


def _validate_cross_file_fields(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, object]],
) -> None:
    first = rows[0]
    invariant_fields = (
        "schema_version", "case_name", "element_type", "nx", "ny", "nz",
        "node_count", "element_count", "dof_count", "nnz", "input_prepare_ms",
        "relative_frobenius_error", "max_absolute_error",
        "matrix_correctness_status", "estimated_persistent_bytes",
        "performance_evidence_level",
    )
    for row in rows[1:]:
        for field in invariant_fields:
            if row[field] != first[field]:
                raise _error(f"CSV field {field!r} is not invariant across samples")

    configuration = summary.get("configuration")
    sizes = summary.get("case_sizes")
    correctness = summary.get("correctness")
    if not all(isinstance(value, Mapping) for value in (configuration, sizes, correctness)):
        raise _error("benchmark summary configuration, sizes, or correctness is missing")
    assert isinstance(configuration, Mapping)
    assert isinstance(sizes, Mapping)
    assert isinstance(correctness, Mapping)
    expected = {
        "schema_version": summary.get("schema_version"),
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
        "estimated_persistent_bytes": summary.get("estimated_persistent_bytes"),
        "performance_evidence_level": summary.get("performance_evidence_level"),
    }
    for field, value in expected.items():
        if first[field] != value:
            raise _error(f"CSV field {field!r} disagrees with benchmark summary")
    for field, key in (
        ("relative_frobenius_error", "relative_frobenius_error"),
        ("max_absolute_error", "max_absolute_error"),
    ):
        if not _close(float(first[field]), _json_number(correctness.get(key), key)):
            raise _error(f"CSV correctness field {field!r} disagrees with benchmark summary")
    input_prepare = _json_number(summary.get("input_prepare_ms"), "input_prepare_ms")
    if float(first["input_prepare_ms"]) != input_prepare:
        raise _error("CSV input_prepare_ms is not exactly equal to the JSON root field")
    if summary.get("estimated_persistent_memory_kind") != MEMORY_KIND:
        raise _error("benchmark persistent-memory meaning is invalid")
    if summary.get("numeric_speedup_basis") != NUMERIC_SPEEDUP_BASIS:
        raise _error("benchmark numeric speedup basis is invalid")
    if first["performance_evidence_level"] != manifest.get("evidence_level"):
        raise _error("CSV evidence level disagrees with the manifest")

    input_facts = manifest.get("input")
    if not isinstance(input_facts, Mapping):
        raise _error("manifest input facts are missing")
    case = input_facts.get("case")
    if case in {"generated-tet4", "generated-hex8"}:
        grid = input_facts.get("grid")
        if not isinstance(grid, Mapping):
            raise _error("generated case grid is missing")
        nx, ny, nz = (int(grid[axis]) for axis in ("nx", "ny", "nz"))
        tet4 = case == "generated-tet4"
        expected_case = f"cube_{'tet4' if tet4 else 'hex8'}_{nx}x{ny}x{nz}"
        expected_element_type = "Tet4" if tet4 else "Hex8"
        expected_nodes = (nx + 1) * (ny + 1) * (nz + 1)
        expected_elements = (6 if tet4 else 1) * nx * ny * nz
        semantic_fields = {
            "case_name": expected_case,
            "element_type": expected_element_type,
            "node_count": expected_nodes,
            "element_count": expected_elements,
            "dof_count": 3 * expected_nodes,
        }
    else:
        repository_path = input_facts.get("repository_relative_path")
        has_repository_path = isinstance(repository_path, str) and bool(repository_path)
        path_text = repository_path if has_repository_path else input_facts.get("path")
        if not isinstance(path_text, str) or not path_text:
            raise _error("WindHub input path is missing")
        environment = manifest.get("environment")
        environment = environment if isinstance(environment, Mapping) else {}
        path_type = (
            PureWindowsPath
            if not has_repository_path and environment.get("system") == "Windows"
            else PurePosixPath
        )
        semantic_fields = {"case_name": path_type(path_text).name}
        if (
            manifest.get("evidence_level") == "formal"
            and repository_path == CANONICAL_WINDHUB_PATH
        ):
            semantic_fields["element_type"] = "Tet4"
    for field, value in semantic_fields.items():
        if first[field] != value:
            raise _error(f"benchmark case field {field!r} disagrees with manifest input")


def _recompute_statistics(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, object]],
    requested: Sequence[int],
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    benchmark = manifest["benchmark"]
    assert isinstance(benchmark, Mapping)
    warmup = int(benchmark["warmup_count"])
    repeat = int(benchmark["repeat_count"])
    amortization = int(benchmark["amortization_count"])
    sample_count = warmup + repeat
    if len(rows) != len(requested) * sample_count:
        raise _error("CSV row count does not match threads times warmup-plus-repeat")

    grouped: Dict[int, Dict[int, Mapping[str, object]]] = {
        thread: {} for thread in requested
    }
    serial_by_index: Dict[int, Tuple[float, float]] = {}
    for row in rows:
        thread = int(row["thread_count"])
        sample_index = int(row["sample_index"])
        if thread not in grouped:
            raise _error(f"CSV contains unexpected thread count {thread}")
        if sample_index in grouped[thread]:
            raise _error(f"CSV contains duplicate sample identity ({thread}, {sample_index})")
        grouped[thread][sample_index] = row
        if sample_index < 0 or sample_index >= sample_count:
            raise _error("CSV sample index is outside the configured range")
        expected_kind = "warmup" if sample_index < warmup else "measured"
        if row["sample_kind"] != expected_kind:
            raise _error("CSV sample kind disagrees with its configured index")
        serial_pair = (float(row["serial_symbolic_ms"]), float(row["serial_numeric_ms"]))
        previous = serial_by_index.setdefault(sample_index, serial_pair)
        if previous != serial_pair:
            raise _error("CSV serial samples drift across thread configurations")

        symbolic_sum = float(row["symbolic_pattern_ms"]) + float(row["symbolic_scatter_ms"])
        symbolic_total = float(row["symbolic_total_ms"])
        if not math.isfinite(symbolic_sum) or symbolic_sum > symbolic_total + TIMING_TOLERANCE_MS:
            raise _error("CSV symbolic phase timings exceed symbolic_total_ms")
        numeric_algorithm = float(row["numeric_reset_ms"]) + float(row["numeric_kernel_ms"])
        if not math.isfinite(numeric_algorithm) or numeric_algorithm < 0.0:
            raise _error("CSV numeric reset-plus-kernel timing is invalid")
        if numeric_algorithm > float(row["numeric_total_ms"]) + TIMING_TOLERANCE_MS:
            raise _error("CSV numeric algorithm timing exceeds numeric_total_ms")
        expected_amortized = symbolic_total / float(amortization) + float(row["numeric_total_ms"])
        actual_amortized = float(row["amortized_total_ms"])
        tolerance = 1.0e-12 * max(1.0, abs(expected_amortized))
        if not math.isfinite(expected_amortized) or abs(actual_amortized - expected_amortized) > tolerance:
            raise _error("CSV amortized timing is inconsistent")

    expected_indices = set(range(sample_count))
    for thread in requested:
        if set(grouped[thread]) != expected_indices:
            raise _error(f"CSV sample indices are incomplete for thread {thread}")
    measured_indices = list(range(warmup, sample_count))
    serial = {
        "symbolic_total_ms": _statistics(
            [serial_by_index[index][0] for index in measured_indices]
        ),
        "numeric_total_ms": _statistics(
            [serial_by_index[index][1] for index in measured_indices]
        ),
    }
    serial_json = summary.get("serial_measured_statistics")
    if not isinstance(serial_json, Mapping):
        raise _error("benchmark serial measured statistics are missing")
    for phase, values in serial.items():
        _compare_statistics(serial_json.get(phase), values, f"serial {phase}")

    json_rows = summary.get("per_thread_measured_statistics")
    if not isinstance(json_rows, list) or [
        item.get("thread_count") if isinstance(item, Mapping) else None
        for item in json_rows
    ] != list(requested):
        raise _error("benchmark per-thread summaries do not match requested order")
    json_by_thread = {
        int(item["thread_count"]): item for item in json_rows if isinstance(item, Mapping)
    }
    recomputed_rows: List[Dict[str, object]] = []
    serial_symbolic_median = float(serial["symbolic_total_ms"]["median_ms"])
    serial_numeric_median = float(serial["numeric_total_ms"]["median_ms"])
    for thread in requested:
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
        phase_statistics = {phase: _statistics(values) for phase, values in phase_values.items()}
        symbolic_median = float(phase_statistics["symbolic_total_ms"]["median_ms"])
        numeric_median = float(phase_statistics["numeric_algorithm_ms"]["median_ms"])
        if symbolic_median <= 0.0 or numeric_median <= 0.0:
            raise _error("benchmark candidate timing medians must be positive")
        symbolic_speedup = serial_symbolic_median / symbolic_median
        numeric_speedup = serial_numeric_median / numeric_median
        if any(
            not math.isfinite(value) or value < 0.0
            for value in (symbolic_speedup, numeric_speedup)
        ):
            raise _error("recomputed benchmark speedup is invalid")

        json_row = json_by_thread[thread]
        for phase in PER_THREAD_PHASES:
            _compare_statistics(
                json_row.get(phase), phase_statistics[phase], f"thread {thread} {phase}"
            )
        for key, expected_speedup in (
            ("symbolic_speedup", symbolic_speedup),
            ("numeric_speedup", numeric_speedup),
        ):
            json_speedup = _json_number(json_row.get(key), f"thread {thread} {key}")
            if not _close(json_speedup, expected_speedup):
                raise _error(f"benchmark summary {key} disagrees with CSV medians")
            if any(float(row[key]) != json_speedup for row in grouped[thread].values()):
                raise _error(f"CSV {key} does not equal its per-thread summary")
        recomputed_rows.append(
            {
                "thread_count": thread,
                **phase_statistics,
                "symbolic_speedup": symbolic_speedup,
                "numeric_speedup": numeric_speedup,
            }
        )
    return {"serial": serial, "per_thread": tuple(recomputed_rows)}, recomputed_rows


def _recompute_gate(
    benchmark_case: object,
    evidence_level: object,
    requested: Sequence[int],
    rows: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    thresholds = {
        "numeric_speedup_threshold": 1.5,
        "symbolic_speedup_threshold": 1.0,
        "maximum_coefficient_of_variation": 0.05,
    }
    if benchmark_case in {"generated-tet4", "generated-hex8"}:
        return {
            "status": "NOT_APPLICABLE_GENERATED_CASE",
            "applicable": False,
            "performance_requirements_met": False,
            "numeric_requirement_met": False,
            "symbolic_requirement_met": False,
            "numeric_thread_count": 0,
            "symbolic_thread_count": 0,
            **thresholds,
        }
    if benchmark_case != "windhub":
        raise _error("benchmark case is unsupported for performance gating")
    by_thread = {int(row["thread_count"]): row for row in rows}
    numeric_thread = 0
    symbolic_thread = 0
    for thread in requested:
        if thread == 1:
            continue
        row = by_thread[thread]
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
    numeric_met = numeric_thread != 0
    symbolic_met = symbolic_thread != 0
    formal = evidence_level == "formal"
    requirements_met = numeric_met and symbolic_met if formal else False
    status = (
        ("PASS" if requirements_met else "FAIL")
        if formal
        else ("NON_FORMAL_CI_SMOKE" if evidence_level == "ci-smoke" else "NON_FORMAL_LOCAL_SMOKE")
    )
    return {
        "status": status,
        "applicable": True,
        "performance_requirements_met": requirements_met,
        "numeric_requirement_met": numeric_met,
        "symbolic_requirement_met": symbolic_met,
        "numeric_thread_count": numeric_thread,
        "symbolic_thread_count": symbolic_thread,
        **thresholds,
    }


def _compare_gate(summary: Mapping[str, object], expected: Mapping[str, object]) -> None:
    actual = summary.get("performance_gate")
    if not isinstance(actual, Mapping):
        raise _error("benchmark performance_gate object is missing")
    for key, value in expected.items():
        actual_value = actual.get(key)
        if key in {
            "numeric_speedup_threshold",
            "symbolic_speedup_threshold",
            "maximum_coefficient_of_variation",
        }:
            if _json_number(actual_value, f"performance_gate.{key}") != float(value):
                raise _error(f"benchmark performance gate threshold {key!r} is invalid")
        elif actual_value != value:
            raise _error(f"benchmark performance gate field {key!r} disagrees with CSV")
    if summary.get("performance_gate_status") != expected["status"]:
        raise _error("benchmark performance_gate_status disagrees with CSV")


def _known_text(value: object) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and text not in {"unknown", "unknown unknown"}


def _formal_provenance_errors(
    manifest: Mapping[str, object], *, allow_benchmark_failure: bool = False
) -> Tuple[str, ...]:
    errors: List[str] = []
    source = manifest.get("source")
    environment = manifest.get("environment")
    toolchain = manifest.get("toolchain")
    input_facts = manifest.get("input")
    benchmark = manifest.get("benchmark")
    commands = manifest.get("commands")
    tasks = manifest.get("tasks")
    source = source if isinstance(source, Mapping) else {}
    environment = environment if isinstance(environment, Mapping) else {}
    toolchain = toolchain if isinstance(toolchain, Mapping) else {}
    input_facts = input_facts if isinstance(input_facts, Mapping) else {}
    benchmark = benchmark if isinstance(benchmark, Mapping) else {}
    commands = commands if isinstance(commands, Mapping) else {}
    tasks = tasks if isinstance(tasks, list) else []

    if environment.get("system") != "Linux":
        errors.append("formal evidence requires Linux")
    if str(environment.get("architecture") or "").lower() not in {"x86_64", "amd64"}:
        errors.append("formal evidence requires Linux x86_64/amd64")
    if "intel" not in str(environment.get("cpu_vendor") or "").lower():
        errors.append("formal evidence requires an Intel CPU")
    if not str(environment.get("controlled_host_id") or "").strip():
        errors.append("formal evidence requires a controlled-host ID")
    if source.get("source_dirty_at_start") is not False:
        errors.append("formal evidence requires a clean source tree at start")
    if not _known_text(toolchain.get("compiler")):
        errors.append("formal evidence requires an identified compiler")
    if not _known_text(toolchain.get("cmake_version")):
        errors.append("formal evidence requires an identified CMake version")
    openmp = toolchain.get("openmp")
    openmp = openmp if isinstance(openmp, Mapping) else {}
    if openmp.get("found") is not True:
        errors.append("formal evidence requires detected OpenMP")
    if openmp.get("require_openmp") is not True:
        errors.append("formal evidence requires the OpenMP-required build")

    if input_facts.get("case") != "windhub":
        errors.append("formal evidence requires the WindHub case")
    if input_facts.get("repository_relative_path") != CANONICAL_WINDHUB_PATH:
        errors.append("formal evidence requires the canonical WindHub repository path")
    size = input_facts.get("size_bytes")
    digest = input_facts.get("sha256")
    if not _is_int(size, minimum=1):
        errors.append("formal evidence requires a positive materialized input size")
    if not isinstance(digest, str) or _SHA64.fullmatch(digest) is None:
        errors.append("formal evidence requires a valid materialized input SHA-256")
    if input_facts.get("head_lfs_size_bytes") != size:
        errors.append("materialized input size does not match the HEAD LFS pointer")
    head_digest = input_facts.get("head_lfs_oid_sha256")
    if (
        not isinstance(head_digest, str)
        or not isinstance(digest, str)
        or head_digest.lower() != digest.lower()
    ):
        errors.append("materialized input SHA-256 does not match the HEAD LFS pointer")
    for key in ("tracked", "materialized", "matches_head_lfs"):
        if input_facts.get(key) is not True:
            errors.append(f"formal evidence requires input {key}=true")

    warmup = benchmark.get("warmup_count")
    repeat = benchmark.get("repeat_count")
    requested = benchmark.get("requested_thread_counts")
    requested = requested if isinstance(requested, list) else []
    if not _is_int(warmup, minimum=2):
        errors.append("formal evidence requires at least two warmups")
    if not _is_int(repeat, minimum=7):
        errors.append("formal evidence requires at least seven repeats")
    if not {1, 2, 4, 8, 16}.issubset(set(requested)):
        errors.append("formal evidence requires thread counts 1, 2, 4, 8, and 16")
    physical = environment.get("physical_core_count")
    if not _is_int(physical, minimum=1):
        errors.append("formal evidence requires a positive physical-core count")
    elif physical not in requested:
        errors.append("formal evidence must include the physical-core thread count")

    for name in ("configure", "build", "ctest", "benchmark"):
        command = commands.get(name)
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(part, str) or not part for part in command)
        ):
            errors.append(f"formal evidence requires command array {name!r}")
    task_objects = [task for task in tasks if isinstance(task, Mapping)]
    for name in ("configure", "build", "ctest", "benchmark"):
        matching = [task for task in task_objects if task.get("name") == name]
        if len(matching) != 1:
            errors.append(f"formal evidence requires exactly one {name} task")
            continue
        task = matching[0]
        status = task.get("status")
        return_code = task.get("returncode")
        exit_code = task.get("exit_code")
        if (
            not _is_int(return_code, minimum=0)
            or not _is_int(exit_code, minimum=0)
            or return_code != exit_code
        ):
            errors.append(f"formal evidence task {name!r} has inconsistent exit codes")
            continue
        if name == "benchmark" and allow_benchmark_failure and status == "FAIL":
            if (
                exit_code == 0
                or not str(task.get("error") or "").strip()
            ):
                errors.append("failing formal benchmark task lost its original nonzero exit")
        elif status != "PASS" or exit_code != 0:
            errors.append(f"formal evidence task {name!r} did not pass")
    if len(task_objects) != 4:
        errors.append("formal evidence contains unexpected workflow tasks")
    return tuple(errors)


def _benchmark_task_failed(manifest: Mapping[str, object]) -> bool:
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        return False
    matches = [task for task in tasks if isinstance(task, Mapping) and task.get("name") == "benchmark"]
    return len(matches) == 1 and matches[0].get("status") == "FAIL"


def _validate_status(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    gate: Mapping[str, object],
) -> str:
    evidence_level = str(manifest["evidence_level"])
    report_intent = str(manifest["report_intent"])
    command_failed = _benchmark_task_failed(manifest)
    if evidence_level != "formal" or report_intent != "delivery":
        if command_failed or any(
            isinstance(task, Mapping) and task.get("status") != "PASS"
            for task in manifest["tasks"]
        ):
            raise _error("non-delivery evidence contains a failed workflow task")
    if evidence_level == "formal" and report_intent == "delivery":
        gate_failed = gate.get("status") == "FAIL"
        provenance_errors = _formal_provenance_errors(
            manifest, allow_benchmark_failure=gate_failed
        )
        if provenance_errors:
            raise _error("formal provenance is incomplete: " + "; ".join(provenance_errors))
        if command_failed and not gate_failed:
            raise _error("formal benchmark task failure is inconsistent with a passing gate")
    try:
        status, _ = RUNNER.derive_run_status(
            evidence_level=evidence_level,
            report_intent=report_intent,
            benchmark_summary=summary,
            command_failed=command_failed,
        )
    except Exception as error:
        raise _error(f"cannot recompute report status: {error}") from error
    if manifest.get("status") != status:
        raise _error(
            f"manifest status {manifest.get('status')!r} disagrees with recomputed status {status!r}"
        )
    return status


def validate_evidence_bundle(manifest_path: Path) -> EvidenceBundle:
    """Validate and recompute one manifest-rooted evidence bundle without writes."""

    path = Path(manifest_path).expanduser()
    if not path.is_file():
        raise _error(f"manifest file does not exist: {path}")
    try:
        manifest_value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _error(f"manifest is not a UTF-8 JSON object: {error}") from error
    manifest, requested = _validate_manifest(manifest_value)
    root = path.resolve().parent
    artifact_paths, artifact_contents = _validate_artifacts(
        root, manifest["artifacts"]
    )

    junit_names = _validate_junit(
        artifact_paths["ctest.xml"], artifact_contents["ctest.xml"]
    )
    summary = _strict_summary(
        artifact_paths["benchmark_summary.json"],
        artifact_contents["benchmark_summary.json"],
        manifest,
        requested,
    )
    configuration = summary.get("configuration")
    if not isinstance(configuration, Mapping):
        raise _error("benchmark summary configuration is missing")
    if configuration.get("thread_counts") != requested:
        raise _error("benchmark JSON threads do not equal manifest threads in order")
    if manifest.get("evidence_level") == "formal" and configuration.get("case") != "windhub":
        raise _error("formal evidence is restricted to the WindHub case")

    csv_rows = _parse_csv(artifact_contents["benchmark_samples.csv"])
    _validate_cross_file_fields(manifest, summary, csv_rows)
    recomputed_statistics, recomputed_rows = _recompute_statistics(
        manifest, summary, csv_rows, requested
    )
    recomputed_gate = _recompute_gate(
        configuration.get("case"),
        manifest.get("evidence_level"),
        requested,
        recomputed_rows,
    )
    _compare_gate(summary, recomputed_gate)
    report_status = _validate_status(manifest, summary, recomputed_gate)
    return EvidenceBundle(
        manifest=manifest,
        benchmark_summary=summary,
        csv_rows=tuple(csv_rows),
        recomputed_statistics=recomputed_statistics,
        recomputed_gate=recomputed_gate,
        junit_testcase_names=junit_names,
        artifact_paths=artifact_paths,
        report_status=report_status,
    )
