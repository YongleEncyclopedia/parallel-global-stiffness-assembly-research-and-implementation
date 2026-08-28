#!/usr/bin/env python3
"""从 benchmark、CTest 和 manifest 证据生成可复算的 Markdown 报告。

脚本先检查数据格式、文件摘要和正式实验口径，再从原始样本重新计算统计量。
证据缺失或互相矛盾时不会生成报告。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import shlex
import sys
import tempfile
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
MAXIMUM_ABSOLUTE_BASE_TOLERANCE = 1.0e-10
MAXIMUM_ABSOLUTE_SCALE_TOLERANCE = 1.0e-8
COMPARISON_FAILURE_ERROR = sys.float_info.max
FORMAL_WARMUP_COUNT = 2
FORMAL_REPEAT_COUNT = 7
FORMAL_AMORTIZATION_COUNT = 1
NON_FORMAL_WARNING = (
    "NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE"
)
LICENSE_STATE = "INTERNAL EVALUATION ONLY"

BENCHMARK_SCHEMA_V1 = "csc3-demo-benchmark-v1"
BENCHMARK_SCHEMA_V2 = "csc3-demo-benchmark-v2"
BENCHMARK_SCHEMA_V3 = "csc3-demo-benchmark-v3"

CSV_HEADER_V1 = (
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

CSV_HEADER = CSV_HEADER_V1 + (
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
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
    "Csc3DemoPythonTests",
    "Csc3DemoAtomicContention",
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
    _require_list(manifest, "identity_checks")
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
        raise _error(
            "CTest JUnit does not contain exactly "
            f"{len(JUNIT_NAMES)} testcase elements"
        )

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
    if tuple(names) != JUNIT_NAMES:
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


def _parse_legacy_csv(content: bytes) -> Tuple[Dict[str, object], ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeError as error:
        raise _error(f"benchmark samples CSV is not UTF-8: {error}") from error
    try:
        raw_rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        raise _error(f"benchmark samples CSV is malformed: {error}") from error
    if not raw_rows or tuple(raw_rows[0]) != CSV_HEADER_V1:
        raise _error("benchmark samples CSV header is not the exact 30-column contract")
    parsed: List[Dict[str, object]] = []
    for row_index, values in enumerate(raw_rows[1:], start=2):
        if not values or all(value == "" for value in values):
            raise _error(f"benchmark samples CSV contains an empty row at line {row_index}")
        if len(values) != len(CSV_HEADER_V1):
            raise _error(f"benchmark samples CSV row {row_index} has unexpected fields")
        row: Dict[str, object] = {}
        for field, raw in zip(CSV_HEADER_V1, values):
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
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise _error(f"{label} must be finite and nonnegative")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as error:
        raise _error(f"{label} has an invalid numeric value") from error
    if not math.isfinite(number) or number < 0.0:
        raise _error(f"{label} must be finite and nonnegative")
    return number


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


def _validate_summary_reference_scaled_tolerances(
    summary: Mapping[str, object]
) -> None:
    correctness = summary.get("correctness")
    validation_cases = summary.get("validation_cases")
    if not isinstance(correctness, Mapping):
        raise _error("benchmark correctness object is missing")
    if not isinstance(validation_cases, list) or len(validation_cases) != 2:
        raise _error("benchmark validation cases are missing")
    matrices: List[Tuple[str, Mapping[str, object]]] = [("root", correctness)]
    for index, case in enumerate(validation_cases):
        if not isinstance(case, Mapping) or not isinstance(case.get("matrix"), Mapping):
            raise _error("benchmark validation matrix evidence is missing")
        matrix = case["matrix"]
        assert isinstance(matrix, Mapping)
        matrices.append(("Tet4" if index == 0 else "Hex8", matrix))
    for label, matrix in matrices:
        reference_scale = _json_number(
            matrix.get("reference_max_absolute_value"),
            f"{label} reference_max_absolute_value",
        )
        recorded_tolerance = _json_number(
            matrix.get("max_absolute_tolerance"),
            f"{label} max_absolute_tolerance",
        )
        expected_tolerance = (
            MAXIMUM_ABSOLUTE_BASE_TOLERANCE
            + MAXIMUM_ABSOLUTE_SCALE_TOLERANCE * reference_scale
        )
        if not _close(recorded_tolerance, expected_tolerance):
            raise _error(
                f"{label} max_absolute_tolerance disagrees with reference scale"
            )


def _strict_summary(
    path: Path,
    content: bytes,
    samples_csv_snapshot: bytes,
    manifest: Mapping[str, object],
    requested: Sequence[int],
) -> Mapping[str, object]:
    try:
        bound = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise _error(f"benchmark summary is invalid UTF-8 JSON: {error}") from error
    if not isinstance(bound, Mapping):
        raise _error("benchmark summary root must be an object")
    schema_version = bound.get("schema_version")
    if schema_version == BENCHMARK_SCHEMA_V1 and (
        manifest.get("evidence_level") != "local-smoke"
        or manifest.get("report_intent") != "local-smoke"
    ):
        raise _error(
            "legacy benchmark v1 is read-only local-smoke evidence; formal or delivery reports require v2"
        )
    _validate_summary_reference_scaled_tolerances(bound)
    try:
        parsed, _ = RUNNER.validate_benchmark_summary(
            path,
            requested,
            manifest["evidence_level"],
            _expected_configuration(manifest),
            samples_csv_path=samples_csv_snapshot,
        )
    except RuntimeError as error:
        raise _error(str(error)) from error
    if parsed != bound:
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


def _pure_path(
    value: object, *, windows: bool
) -> PurePosixPath | PureWindowsPath | None:
    if not isinstance(value, str) or not value:
        return None
    path_type = PureWindowsPath if windows else PurePosixPath
    return path_type(value)


def _absolute_pure_path(
    value: object, *, windows: bool
) -> PurePosixPath | PureWindowsPath | None:
    path = _pure_path(value, windows=windows)
    return path if path is not None and path.is_absolute() else None


def _same_pure_path(left: object, right: object, *, windows: bool) -> bool:
    left_path = _absolute_pure_path(left, windows=windows)
    right_path = _absolute_pure_path(right, windows=windows)
    return left_path is not None and left_path == right_path


def _program_is(value: object, expected: str, *, windows: bool) -> bool:
    path = _pure_path(value, windows=windows)
    if path is None:
        return False
    name = path.name.casefold()
    expected_name = expected.casefold()
    return name in {expected_name, expected_name + ".exe"}


def _formal_command_semantic_errors(
    manifest: Mapping[str, object], commands: Mapping[str, object]
) -> Tuple[str, ...]:
    errors: List[str] = []
    environment = manifest.get("environment")
    environment = environment if isinstance(environment, Mapping) else {}
    windows = environment.get("system") == "Windows"
    command_arrays: Dict[str, List[str]] = {}
    required_names = ("configure", "build", "ctest", "benchmark")
    if set(commands) != set(required_names):
        errors.append("formal evidence command names must be exactly configure, build, ctest, benchmark")
    for name in required_names:
        value = commands.get(name)
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(part, str) or not part for part in value)
        ):
            errors.append(f"formal evidence requires command array {name!r}")
        else:
            command_arrays[name] = value

    toolchain = manifest.get("toolchain")
    toolchain = toolchain if isinstance(toolchain, Mapping) else {}
    build_directory = toolchain.get("build_directory")
    if _absolute_pure_path(build_directory, windows=windows) is None:
        errors.append("formal evidence requires an absolute recorded build directory")

    configure = command_arrays.get("configure")
    if configure is not None and (
        len(configure) != 5
        or not _program_is(configure[0], "cmake", windows=windows)
        or configure[1:4] != ["--preset", "delivery", "-B"]
        or not _same_pure_path(configure[4], build_directory, windows=windows)
    ):
        errors.append("formal configure command is not the delivery preset bound to the build directory")

    build = command_arrays.get("build")
    if build is not None and (
        len(build) != 5
        or not _program_is(build[0], "cmake", windows=windows)
        or build[1] != "--build"
        or not _same_pure_path(build[2], build_directory, windows=windows)
        or build[3:] != ["--config", "Release"]
    ):
        errors.append("formal build command is not the Release build for the recorded directory")

    ctest_output: PurePosixPath | PureWindowsPath | None = None
    ctest = command_arrays.get("ctest")
    if ctest is not None:
        if (
            len(ctest) != 11
            or not _program_is(ctest[0], "ctest", windows=windows)
            or ctest[1] != "--test-dir"
            or not _same_pure_path(ctest[2], build_directory, windows=windows)
            or ctest[3:9]
            != [
                "-C",
                "Release",
                "--label-regex",
                "ci",
                "--output-on-failure",
                "--no-tests=error",
            ]
            or ctest[9] != "--output-junit"
        ):
            errors.append("formal CTest command does not implement the exact ci JUnit contract")
        else:
            ctest_output = _absolute_pure_path(ctest[10], windows=windows)
            if ctest_output is None or ctest_output.name != "ctest.xml":
                errors.append("formal CTest command does not write the bound ctest.xml")

    input_facts = manifest.get("input")
    input_facts = input_facts if isinstance(input_facts, Mapping) else {}
    benchmark_facts = manifest.get("benchmark")
    benchmark_facts = benchmark_facts if isinstance(benchmark_facts, Mapping) else {}
    benchmark = command_arrays.get("benchmark")
    benchmark_samples: PurePosixPath | PureWindowsPath | None = None
    benchmark_summary: PurePosixPath | PureWindowsPath | None = None
    if benchmark is not None:
        expected_arguments = [
            "--case",
            str(input_facts.get("case")),
            "--threads-list",
            ",".join(str(value) for value in benchmark_facts.get("requested_thread_counts", [])),
            "--warmup",
            str(benchmark_facts.get("warmup_count")),
            "--repeat",
            str(benchmark_facts.get("repeat_count")),
            "--amortization-count",
            str(benchmark_facts.get("amortization_count")),
            "--evidence-level",
            str(manifest.get("evidence_level")),
            "--samples-csv",
        ]
        prefix_length = 1 + len(expected_arguments)
        if (
            len(benchmark) < prefix_length + 3
            or not _program_is(
                benchmark[0], "csc3_demo_benchmark", windows=windows
            )
            or _absolute_pure_path(benchmark[0], windows=windows) is None
            or benchmark[1:prefix_length] != expected_arguments
        ):
            errors.append("formal benchmark command does not bind the requested run parameters")
        else:
            benchmark_samples = _absolute_pure_path(
                benchmark[prefix_length], windows=windows
            )
            remaining = benchmark[prefix_length + 1 :]
            if len(remaining) < 2 or remaining[0] != "--summary-json":
                errors.append("formal benchmark command does not bind the summary JSON output")
            else:
                benchmark_summary = _absolute_pure_path(
                    remaining[1], windows=windows
                )
                case = input_facts.get("case")
                if case == "windhub":
                    expected_tail = ["--input", str(input_facts.get("path"))]
                else:
                    grid = input_facts.get("grid")
                    grid = grid if isinstance(grid, Mapping) else {}
                    expected_tail = [
                        "--nx",
                        str(grid.get("nx")),
                        "--ny",
                        str(grid.get("ny")),
                        "--nz",
                        str(grid.get("nz")),
                    ]
                if remaining[2:] != expected_tail:
                    errors.append("formal benchmark command input/grid arguments are not exact")
            if benchmark_samples is None or benchmark_samples.name != "benchmark_samples.csv":
                errors.append("formal benchmark command does not write the bound samples CSV")
            if benchmark_summary is None or benchmark_summary.name != "benchmark_summary.json":
                errors.append("formal benchmark command does not write the bound summary JSON")

    output_paths = (ctest_output, benchmark_samples, benchmark_summary)
    if all(path is not None for path in output_paths):
        parents = [path.parent for path in output_paths if path is not None]
        if any(type(path) is not type(parents[0]) or path != parents[0] for path in parents[1:]):
            errors.append("formal CTest and benchmark outputs do not share one bound output root")
    return tuple(errors)


def _formal_identity_check_errors(
    manifest: Mapping[str, object]
) -> Tuple[str, ...]:
    errors: List[str] = []
    phases = ("after-build", "before-benchmark", "after-benchmark")
    source_keys = (
        "commit_sha",
        "branch",
        "source_dirty_at_start",
        "demo_version",
    )
    input_keys = (
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
    initial_source = manifest.get("source")
    initial_source = initial_source if isinstance(initial_source, Mapping) else {}
    initial_input = manifest.get("input")
    initial_input = initial_input if isinstance(initial_input, Mapping) else {}
    expected_source = {key: initial_source.get(key) for key in source_keys}
    expected_input = {key: initial_input.get(key) for key in input_keys}
    checks = manifest.get("identity_checks")
    if not isinstance(checks, list) or len(checks) != len(phases):
        return ("formal evidence requires exactly three ordered identity checks",)
    for index, phase in enumerate(phases):
        check = checks[index]
        if not isinstance(check, Mapping) or check.get("phase") != phase:
            errors.append(f"formal identity check {index} is not phase {phase!r}")
            continue
        if check.get("status") != "PASS" or check.get("errors") != []:
            errors.append(f"formal identity check {phase!r} did not pass cleanly")
        observed_source = check.get("source")
        if not isinstance(observed_source, Mapping) or dict(observed_source) != expected_source:
            errors.append(f"formal identity check {phase!r} source does not match run start")
        observed_input = check.get("input")
        if not isinstance(observed_input, Mapping) or dict(observed_input) != expected_input:
            errors.append(f"formal identity check {phase!r} input does not match run start")
    return tuple(errors)


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
    windows = environment.get("system") == "Windows"

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
    amortization = benchmark.get("amortization_count")
    requested = benchmark.get("requested_thread_counts")
    requested = requested if isinstance(requested, list) else []
    if warmup != FORMAL_WARMUP_COUNT or isinstance(warmup, bool):
        errors.append("formal evidence requires exactly two warmups")
    if repeat != FORMAL_REPEAT_COUNT or isinstance(repeat, bool):
        errors.append("formal evidence requires exactly seven repeats")
    if (
        amortization != FORMAL_AMORTIZATION_COUNT
        or isinstance(amortization, bool)
    ):
        errors.append("formal evidence requires amortization count one")
    if not {1, 2, 4, 8, 16}.issubset(set(requested)):
        errors.append("formal evidence requires thread counts 1, 2, 4, 8, and 16")
    physical = environment.get("physical_core_count")
    if not _is_int(physical, minimum=1):
        errors.append("formal evidence requires a positive physical-core count")
    elif physical not in requested:
        errors.append("formal evidence must include the physical-core thread count")

    errors.extend(_formal_command_semantic_errors(manifest, commands))
    errors.extend(_formal_identity_check_errors(manifest))
    required_task_names = ("configure", "build", "ctest", "benchmark")
    task_objects = [task for task in tasks if isinstance(task, Mapping)]
    if len(task_objects) != 4 or tuple(
        task.get("name") for task in task_objects
    ) != required_task_names:
        errors.append("formal evidence tasks must be ordered exactly configure, build, ctest, benchmark")
    binding_environment = manifest.get("binding_environment")
    for index, name in enumerate(required_task_names):
        if index >= len(task_objects) or task_objects[index].get("name") != name:
            continue
        task = task_objects[index]
        task_command = task.get("command")
        if (
            not isinstance(task_command, list)
            or not task_command
            or any(not isinstance(part, str) or not part for part in task_command)
        ):
            errors.append(f"formal evidence task {name!r} has no command array")
        elif task_command != commands.get(name):
            errors.append(f"formal evidence task {name!r} command is not bound byte-for-byte")
        if _absolute_pure_path(task.get("cwd"), windows=windows) is None:
            errors.append(f"formal evidence task {name!r} cwd is not absolute")
        environment_value = task.get("environment")
        if (
            not isinstance(environment_value, Mapping)
            or dict(environment_value) != binding_environment
        ):
            errors.append(f"formal evidence task {name!r} environment is not exactly bound")
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
    return tuple(errors)


def _benchmark_task_failed(manifest: Mapping[str, object]) -> bool:
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        return False
    matches = [task for task in tasks if isinstance(task, Mapping) and task.get("name") == "benchmark"]
    return len(matches) == 1 and matches[0].get("status") == "FAIL"


def _technical_evidence_failed(
    summary: Mapping[str, object], gate: Mapping[str, object]
) -> bool:
    correctness = summary.get("correctness")
    if not isinstance(correctness, Mapping) or correctness.get("status") != "PASS":
        return True
    validation_cases = summary.get("validation_cases")
    if not isinstance(validation_cases, list) or any(
        not isinstance(case, Mapping) or case.get("status") != "PASS"
        for case in validation_cases
    ):
        return True
    scatter = summary.get("scatter_correctness")
    if summary.get("schema_version") in {BENCHMARK_SCHEMA_V2, BENCHMARK_SCHEMA_V3} and (
        not isinstance(scatter, Mapping) or scatter.get("status") != "PASS"
    ):
        return True
    return gate.get("status") == "FAIL"


def _validate_status(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    gate: Mapping[str, object],
) -> str:
    evidence_level = str(manifest["evidence_level"])
    report_intent = str(manifest["report_intent"])
    command_failed = _benchmark_task_failed(manifest)
    technical_failed = _technical_evidence_failed(summary, gate)
    if evidence_level != "formal" or report_intent != "delivery":
        other_task_failed = any(
            isinstance(task, Mapping)
            and task.get("name") != "benchmark"
            and task.get("status") != "PASS"
            for task in manifest["tasks"]
        )
        if other_task_failed or (command_failed and not technical_failed):
            raise _error("non-delivery evidence contains a failed workflow task")
    if evidence_level == "formal" and report_intent == "delivery":
        provenance_errors = _formal_provenance_errors(
            manifest, allow_benchmark_failure=technical_failed
        )
        if provenance_errors:
            raise _error("formal provenance is incomplete: " + "; ".join(provenance_errors))
        if command_failed and not technical_failed:
            raise _error(
                "formal benchmark task failure is inconsistent with passing technical evidence"
            )
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
        artifact_contents["benchmark_samples.csv"],
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

    if summary.get("schema_version") in {BENCHMARK_SCHEMA_V2, BENCHMARK_SCHEMA_V3}:
        try:
            canonical = RUNNER.recompute_benchmark_v2_evidence(
                summary,
                artifact_contents["benchmark_samples.csv"],
                requested,
                str(manifest.get("evidence_level")),
                configuration,
            )
        except RuntimeError as error:
            raise _error(str(error)) from error
        csv_rows = tuple(canonical["csv_rows"])
        _validate_cross_file_fields(manifest, summary, csv_rows)
        recomputed_statistics = {
            "serial": canonical["serial"],
            "per_thread": canonical["per_thread"],
            "scatter": canonical["scatter"],
        }
        recomputed_gate = canonical["gate"]
    else:
        csv_rows = _parse_legacy_csv(artifact_contents["benchmark_samples.csv"])
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


_POSIX_PATH_IN_TEXT = re.compile(r"(?<![A-Za-z0-9:/>])/(?:[^\s|`]+)")
_WINDOWS_PATH_IN_TEXT = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/])(?:[^\s|`]+)"
)
_OPTION_PATH_IN_TEXT = re.compile(
    r"(?P<prefix>-(?:isystem|iquote|include|I|L|F))"
    r"(?P<path>/(?:[^\s|`]+)|[A-Za-z]:[\\/](?:[^\s|`]+))"
)


def _format_number(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".10g")
    return str(value)


def _comparison_error_text(matrix: Mapping[str, object], key: str) -> str:
    value = matrix.get(key)
    if value == COMPARISON_FAILURE_ERROR:
        return "不可评估"
    return _format_number(value)


def _comparison_error_summary(matrix: Mapping[str, object]) -> str:
    relative = matrix.get("relative_frobenius_error")
    maximum = matrix.get("max_absolute_error")
    if relative == COMPARISON_FAILURE_ERROR or maximum == COMPARISON_FAILURE_ERROR:
        reason = (
            "矩阵结构不匹配"
            if matrix.get("structure_matches") is False
            else "存在非有限值或比较结果不可表示"
        )
        return f"$e_F$ 与 $e_{{\\max}}$ 不可评估（{reason}）"
    return (
        f"$e_F={_format_number(relative)}$，"
        f"$e_{{\\max}}={_format_number(maximum)}$"
    )


def _plain_text(value: object) -> str:
    return (
        str(value)
        .replace("\r", r"\r")
        .replace("\n", r"\n")
        .replace("\t", r"\t")
        .replace(NON_FORMAL_WARNING, "[reserved warning text omitted]")
    )


def _host_path_placeholder(path_text: str, *, windows: bool) -> str:
    path_type = PureWindowsPath if windows else PurePosixPath
    basename = path_type(path_text).name or "path"
    return f"<host-path>/{basename}"


def _sanitize_command_part(value: object) -> str:
    return _sanitize_free_text(value)


def _sanitize_free_text(value: object) -> str:
    text = _plain_text(value)

    def replace_option(match: re.Match[str]) -> str:
        candidate = match.group("path")
        core = candidate.rstrip(".,;:)]}")
        suffix = candidate[len(core):]
        windows = re.match(r"^[A-Za-z]:[\\/]", core) is not None
        return (
            match.group("prefix")
            + _host_path_placeholder(core, windows=windows)
            + suffix
        )

    def replace_posix(match: re.Match[str]) -> str:
        candidate = match.group(0)
        core = candidate.rstrip(".,;:)]}")
        suffix = candidate[len(core):]
        return _host_path_placeholder(core, windows=False) + suffix

    def replace_windows(match: re.Match[str]) -> str:
        candidate = match.group(0)
        core = candidate.rstrip(".,;:)]}")
        suffix = candidate[len(core):]
        return _host_path_placeholder(core, windows=True) + suffix

    text = _OPTION_PATH_IN_TEXT.sub(replace_option, text)
    text = _WINDOWS_PATH_IN_TEXT.sub(replace_windows, text)
    return _POSIX_PATH_IN_TEXT.sub(replace_posix, text)


def _markdown_cell(value: object) -> str:
    return _sanitize_free_text(value).replace("|", r"\|")


def _format_command(parts: object) -> str:
    if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)):
        return "[invalid command]"
    return shlex.join([_sanitize_command_part(part) for part in parts])


def _ordered_commands(manifest: Mapping[str, object]) -> Tuple[Tuple[str, str], ...]:
    commands = manifest.get("commands")
    if not isinstance(commands, Mapping):
        return ()
    preferred = ("configure", "build", "ctest", "benchmark")
    ordered_names = [name for name in preferred if name in commands]
    ordered_names.extend(sorted(str(name) for name in commands if name not in preferred))
    return tuple(
        (_plain_text(name), _format_command(commands[name])) for name in ordered_names
    )


def _append_commands(lines: List[str], manifest: Mapping[str, object]) -> None:
    lines.extend(("| 命令 | 已脱敏记录 |", "|---|---|"))
    for name, command in _ordered_commands(manifest):
        lines.append(f"| `{_markdown_cell(name)}` | `{_markdown_cell(command)}` |")


def _repository_relative_input(input_facts: Mapping[str, object]) -> str:
    raw = input_facts.get("repository_relative_path")
    if not isinstance(raw, str) or not raw:
        return "未记录可展示的仓库相对路径"
    path = PurePosixPath(raw)
    if raw.startswith("/") or "\\" in raw or ".." in path.parts:
        return "未记录可展示的仓库相对路径"
    return raw


def _compiler_description(toolchain: Mapping[str, object]) -> str:
    raw = _plain_text(toolchain.get("compiler", "unknown"))
    if raw.startswith("/"):
        return PurePosixPath(raw).name or "unknown"
    if re.match(r"^[A-Za-z]:[\\/]", raw):
        return PureWindowsPath(raw).name or "unknown"
    return _sanitize_free_text(raw)


def render_report(bundle: EvidenceBundle) -> str:
    """Render a validated, recomputed evidence bundle as deterministic Markdown."""

    manifest = bundle.manifest
    summary = bundle.benchmark_summary
    source = manifest["source"]
    environment = manifest["environment"]
    toolchain = manifest["toolchain"]
    input_facts = manifest["input"]
    benchmark = manifest["benchmark"]
    binding = manifest["binding_environment"]
    assert isinstance(source, Mapping)
    assert isinstance(environment, Mapping)
    assert isinstance(toolchain, Mapping)
    assert isinstance(input_facts, Mapping)
    assert isinstance(benchmark, Mapping)
    assert isinstance(binding, Mapping)

    lines: List[str] = []
    non_formal = manifest.get("evidence_level") != "formal"
    if non_formal:
        lines.extend((NON_FORMAL_WARNING, ""))
    lines.extend(("# CSC3 并行整体刚度组装测试报告", ""))

    lines.extend(("## 1. 测试结论", ""))
    if bundle.report_status == "PASS":
        lines.append("**测试与性能门槛：PASS**")
    elif bundle.report_status == "FAIL":
        lines.append("**测试与性能门槛：FAIL**")
    else:
        lines.append(f"**测试与性能门槛：{bundle.report_status}**")
    lines.extend(
        (
            "",
            f"- 证据状态：`{bundle.report_status}`。",
            f"- Demo 版本：`{_plain_text(source.get('demo_version'))}`。",
            f"- 完整 commit SHA：`{_plain_text(source.get('commit_sha'))}`。",
            f"- 分支：`{_plain_text(source.get('branch'))}`。",
            "- 运行开始时工作树脏状态："
            f"`{_format_number(source.get('source_dirty_at_start'))}`。",
            f"- 运行 ID：`{_plain_text(manifest.get('run_id'))}`。",
            f"- 开始 UTC：`{_plain_text(manifest.get('started_at_utc'))}`。",
            f"- 结束 UTC：`{_plain_text(manifest.get('ended_at_utc'))}`。",
        )
    )
    if bundle.report_status == "LOCAL_SMOKE":
        lines.append("- `LOCAL_SMOKE` 仅表示本机小规模检查完成，不能代替目标主机测试。")
    elif bundle.report_status == "BLOCKED":
        lines.append("- `BLOCKED` 表示缺少完成测试所需的环境或证据。")
    elif bundle.report_status == "FAIL":
        lines.append("- 测试或性能门槛未通过，本次记录不能作为通过结论。")
    else:
        lines.append(
            "- `PASS` 表示本次记录中的测试和性能门槛均已通过；"
            "是否纳入提交材料由项目负责人根据当次要求决定。"
        )

    lines.extend(
        (
            "",
            "## 2. 算法与 CSC3 数据格式",
            "",
            "- 对称整体刚度矩阵 $K$ 采用上三角 CSC3 存储；第 $j$ 列仅存储满足 $i\\le j$ 的行索 $i$，下三角由对称性隐式给出。",
            "- 确定性符号阶段按列所有权并行：输入归一化 → 构建 DOF-单元邻接 → 并行生成每列候选行 → 排序去重 → 前缀和 → 并行填充行索 → 并行构建 scatter plan。",
            "- 数值阶段使用 OpenMP 按单元并行：每次完整组装先将 $K$ 的数值数组清零，再通过原子 scatter 累加单元矩阵。",
            "- 串行实现仅作为独立正确性参考和性能基线，不是并行实现的 fallback。",
            "",
            "## 3. 公共 API 与命名契约",
            "",
            "- 公共类型：`DofCodingInfo`、`Csc3Matrix`、`HelpInfo`、`ElementStiffness` 与 `AssemblyHelper`。",
            "- 公共操作：`Symbolic()`、`zero_values()` 与逐单元 `add()`。",
            "- 节点、DOF 和 CSC3 索引均从 $0$ 开始。",
            "- 数值阶段先调用一次 `zero_values()`，再在调用方的 OpenMP 循环中逐单元调用 `add()`。",
        )
    )

    openmp = toolchain.get("openmp")
    openmp = openmp if isinstance(openmp, Mapping) else {}
    lines.extend(
        (
            "",
            "## 4. 测试环境与工具链",
            "",
            "| 字段 | 值 |",
            "|---|---|",
            f"| OS | `{_markdown_cell(environment.get('system'))}` |",
            f"| 架构 | `{_markdown_cell(environment.get('architecture'))}` |",
            f"| 主机名 | `{_markdown_cell(environment.get('hostname'))}` |",
            f"| CPU 供应商 / 型号 | `{_markdown_cell(environment.get('cpu_vendor'))}` / `{_markdown_cell(environment.get('cpu_model'))}` |",
            f"| 物理核 / 逻辑核 | {_format_number(environment.get('physical_core_count'))} / {_format_number(environment.get('logical_core_count'))} |",
            f"| 总内存 | {_format_number(environment.get('total_memory_bytes'))} bytes |",
            f"| 编译器 | `{_markdown_cell(_compiler_description(toolchain))}` |",
            f"| 编译器 ID / 版本 | `{_markdown_cell(toolchain.get('compiler_id'))}` / `{_markdown_cell(toolchain.get('compiler_version'))}` |",
            f"| CMake | `{_markdown_cell(toolchain.get('cmake_version'))}` |",
            "| OpenMP required / found / flags | "
            f"`{_format_number(openmp.get('require_openmp'))}` / "
            f"`{_format_number(openmp.get('found'))}` / "
            f"`{_markdown_cell(_sanitize_free_text(openmp.get('flags')))}` |",
            f"| Python | `{_markdown_cell(environment.get('python_version'))}` |",
            f"| 受控主机 ID | `{_markdown_cell(environment.get('controlled_host_id') or '无')}` |",
            "| OpenMP 绑定 | "
            f"`OMP_DYNAMIC={_markdown_cell(binding.get('OMP_DYNAMIC'))}`; "
            f"`OMP_PROC_BIND={_markdown_cell(binding.get('OMP_PROC_BIND'))}`; "
            f"`OMP_PLACES={_markdown_cell(binding.get('OMP_PLACES'))}` |",
        )
    )

    configuration = summary.get("configuration")
    sizes = summary.get("case_sizes")
    configuration = configuration if isinstance(configuration, Mapping) else {}
    sizes = sizes if isinstance(sizes, Mapping) else {}
    case = input_facts.get("case")
    if case in {"generated-tet4", "generated-hex8"}:
        grid = input_facts.get("grid")
        grid = grid if isinstance(grid, Mapping) else {}
        input_description = (
            f"`{_plain_text(case)}`，网格 "
            f"$({ _format_number(grid.get('nx'))},"
            f"{_format_number(grid.get('ny'))},"
            f"{_format_number(grid.get('nz'))})$"
        )
        input_file_facts = "- 输入文件字节数与 SHA-256：不适用（程序生成，无输入文件）。"
    else:
        input_description = (
            "WindHub，仓库相对路径 "
            f"`{_markdown_cell(_repository_relative_input(input_facts))}`"
        )
        input_file_facts = (
            f"- 输入文件字节数：`{_format_number(input_facts.get('size_bytes'))}`；"
            f"SHA-256：`{_plain_text(input_facts.get('sha256'))}`。"
        )
    requested = benchmark.get("requested_thread_counts")
    observed = benchmark.get("observed_thread_counts")
    lines.extend(
        (
            "",
            "## 5. 输入、规模与执行参数",
            "",
            f"- 输入：{input_description}。",
            input_file_facts,
            "- 规模："
            f"节点数 `{_format_number(sizes.get('node_count'))}`，"
            f"单元数 `{_format_number(sizes.get('element_count'))}`，"
            f"DOF 数 `{_format_number(sizes.get('dof_count'))}`，"
            f"NNZ `{_format_number(sizes.get('nnz'))}`。",
            f"- 请求线程数：`{_plain_text(requested)}`；观测线程数：`{_plain_text(observed)}`。",
            f"- 热身次数 $W={_format_number(benchmark.get('warmup_count'))}$，重复次数 $R={_format_number(benchmark.get('repeat_count'))}$，摊销次数 $m={_format_number(benchmark.get('amortization_count'))}$。",
            "",
        )
    )
    _append_commands(lines, manifest)

    junit_testcase_count = len(bundle.junit_testcase_names)
    lines.extend(
        (
            "",
            "## 6. 自动测试结果",
            "",
            f"CTest 精确执行 ${junit_testcase_count}/{junit_testcase_count}$ 个测试：",
            "",
            "| # | testcase | 状态 |",
            "|---:|---|---|",
        )
    )
    for index, name in enumerate(bundle.junit_testcase_names, start=1):
        lines.append(f"| {index} | `{name}` | `PASS` |")
    lines.extend(
        (
            "",
            "验证后的 JUnit 证据中不存在 failure、error、skip、disabled 或 not-run 条目。",
        )
    )

    correctness = summary.get("correctness")
    correctness = correctness if isinstance(correctness, Mapping) else {}
    validation_cases = summary.get("validation_cases")
    validation_cases = validation_cases if isinstance(validation_cases, list) else []
    thresholds = summary.get("validation_thresholds")
    thresholds = thresholds if isinstance(thresholds, Mapping) else {}
    root_error_summary = _comparison_error_summary(correctness)
    lines.extend(
        (
            "",
            "## 7. 整体刚度矩阵正确性",
            "",
            "Benchmark 矩阵：结构匹配 "
            f"`{_format_number(correctness.get('structure_matches'))}`，"
            f"状态 `{_plain_text(correctness.get('status'))}`，"
            f"{root_error_summary}，"
            "$\\max |K_s|="
            f"{_format_number(correctness.get('reference_max_absolute_value'))}$，"
            "$e_{\\max,\\mathrm{tol}}="
            f"{_format_number(correctness.get('max_absolute_tolerance'))}$。"
            "原始字段为 `reference_max_absolute_value`。",
            "",
            "| 验证算例 | 节点 | 单元 | DOF | 线程 | 结构 | $e_F$ | $e_{\\max}$ | $\\max |K_s|$ | $e_{\\max,\\mathrm{tol}}$ | 状态 |",
            "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
        )
    )
    for case_record in validation_cases:
        if not isinstance(case_record, Mapping):
            continue
        matrix = case_record.get("matrix")
        matrix = matrix if isinstance(matrix, Mapping) else {}
        lines.append(
            f"| `{_markdown_cell(case_record.get('element_type'))}` | "
            f"{_format_number(case_record.get('node_count'))} | "
            f"{_format_number(case_record.get('element_count'))} | "
            f"{_format_number(case_record.get('dof_count'))} | "
            f"{_format_number(case_record.get('thread_count'))} | "
            f"`{_format_number(matrix.get('structure_matches'))}` | "
            f"{_comparison_error_text(matrix, 'relative_frobenius_error')} | "
            f"{_comparison_error_text(matrix, 'max_absolute_error')} | "
            f"{_format_number(matrix.get('reference_max_absolute_value'))} | "
            f"{_format_number(matrix.get('max_absolute_tolerance'))} | "
            f"`{_plain_text(matrix.get('status'))}` |"
        )
    lines.extend(
        (
            "",
            "$$",
            "e_F=\\frac{\\lVert K_p-K_s\\rVert_F}",
            "{\\max(\\lVert K_s\\rVert_F,10^{-30})}\\le10^{-8}.",
            "$$",
            "",
            "$$",
            "e_{\\max,\\mathrm{tol}}=10^{-10}+10^{-8}\\max |K_s|,",
            "\\qquad e_{\\max}\\le e_{\\max,\\mathrm{tol}}.",
            "$$",
            "",
            f"验证阈值为 $e_F\\le {_format_number(thresholds.get('relative_frobenius_error_max'))}$；最大绝对误差容差由独立串行参考尺度重算。",
        )
    )

    lines.extend(
        (
            "",
            "## 8. 位移与残差正确性",
            "",
            "| 验证算例 | $e_u$ | 并行 $r_{\\mathrm{rel}}$ | 串行 $r_{\\mathrm{rel}}$ | $\\lVert u_p\\rVert_2$ | $\\lVert u_s\\rVert_2$ | 状态 |",
            "|---|---:|---:|---:|---:|---:|---|",
        )
    )
    for case_record in validation_cases:
        if not isinstance(case_record, Mapping):
            continue
        displacement = case_record.get("displacement")
        displacement = displacement if isinstance(displacement, Mapping) else {}
        lines.append(
            f"| `{_markdown_cell(case_record.get('element_type'))}` | "
            f"{_format_number(displacement.get('relative_displacement_error'))} | "
            f"{_format_number(displacement.get('parallel_relative_residual'))} | "
            f"{_format_number(displacement.get('serial_relative_residual'))} | "
            f"{_format_number(displacement.get('parallel_displacement_norm'))} | "
            f"{_format_number(displacement.get('serial_displacement_norm'))} | "
            f"`{_plain_text(displacement.get('status'))}` |"
        )
    lines.extend(
        (
            "",
            "$$",
            "e_u=\\frac{\\lVert u_p-u_s\\rVert_2}",
            "{\\max(\\lVert u_s\\rVert_2,10^{-30})}\\le10^{-8},",
            "$$",
            "",
            "$$",
            "r_{\\mathrm{rel}}=",
            "\\frac{\\lVert K_{ff}u_f-f'_f\\rVert_2}",
            "{\\max(\\lVert f'_f\\rVert_2,10^{-30})}\\le10^{-10}.",
            "$$",
            "",
            f"验证阈值为 $e_u\\le {_format_number(thresholds.get('relative_displacement_error_max'))}$ 且 $r_{{\\mathrm{{rel}}}}\\le {_format_number(thresholds.get('relative_residual_max'))}$。",
            "",
            "这些结果证明从整体刚度组装到线性求解的一致性，不构成与独立商业求解器的验证。",
        )
    )

    statistics = bundle.recomputed_statistics
    serial = statistics.get("serial") if isinstance(statistics, Mapping) else {}
    serial = serial if isinstance(serial, Mapping) else {}
    serial_symbolic = serial.get("symbolic_total_ms")
    serial_numeric = serial.get("numeric_total_ms")
    serial_symbolic = serial_symbolic if isinstance(serial_symbolic, Mapping) else {}
    serial_numeric = serial_numeric if isinstance(serial_numeric, Mapping) else {}
    per_thread = statistics.get("per_thread") if isinstance(statistics, Mapping) else ()
    per_thread = per_thread if isinstance(per_thread, Sequence) else ()
    scatter = statistics.get("scatter") if isinstance(statistics, Mapping) else {}
    scatter = scatter if isinstance(scatter, Mapping) else {}
    lines.extend(
        (
            "",
            "## 9. 性能结果",
            "",
            f"- 串行符号阶段中位数：`{_format_number(serial_symbolic.get('median_ms'))}` ms。",
            f"- 串行数值阶段中位数：`{_format_number(serial_numeric.get('median_ms'))}` ms。",
            f"- 串行符号 $CV$：`{_format_number(serial_symbolic.get('coefficient_of_variation'))}`。",
            f"- 串行数值 $CV$：`{_format_number(serial_numeric.get('coefficient_of_variation'))}`。",
            "",
            "| 线程 $p$ | 符号中位数 (ms) | 数值中位数 (ms) | 摊销后中位数 (ms) | 符号 $CV$ | 数值 $CV$ | $S_{\\mathrm{symbolic}}$ | $S_{\\mathrm{numeric}}$ |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        )
    )
    for row in per_thread:
        if not isinstance(row, Mapping):
            continue
        symbolic = row.get("symbolic_total_ms")
        numeric = row.get("numeric_algorithm_ms")
        amortized = row.get("amortized_total_ms")
        symbolic = symbolic if isinstance(symbolic, Mapping) else {}
        numeric = numeric if isinstance(numeric, Mapping) else {}
        amortized = amortized if isinstance(amortized, Mapping) else {}
        lines.append(
            f"| {_format_number(row.get('thread_count'))} | "
            f"{_format_number(symbolic.get('median_ms'))} | "
            f"{_format_number(numeric.get('median_ms'))} | "
            f"{_format_number(amortized.get('median_ms'))} | "
            f"{_format_number(symbolic.get('coefficient_of_variation'))} | "
            f"{_format_number(numeric.get('coefficient_of_variation'))} | "
            f"{_format_number(row.get('symbolic_speedup'))} | "
            f"{_format_number(row.get('numeric_speedup'))} |"
        )
    if summary.get("schema_version") in {BENCHMARK_SCHEMA_V2, BENCHMARK_SCHEMA_V3}:
        lines.extend(
            (
                "",
                "### Scatter plan 正确性",
                "",
                "- 根级状态："
                f"`{_plain_text(scatter.get('status'))}`；"
                "符号 plan 匹配 "
                f"${_format_number(scatter.get('symbolic_plan_match_count'))}/"
                f"{_format_number(scatter.get('symbolic_plan_check_count'))}$；"
                "数值 setup plan 匹配 "
                f"${_format_number(scatter.get('numeric_setup_plan_match_count'))}/"
                f"{_format_number(scatter.get('numeric_setup_plan_check_count'))}$。",
                "",
                "| 线程 $p$ | 符号 plan 匹配 / 检查 | 数值 setup plan | 状态 |",
                "|---:|---:|---|---|",
            )
        )
        for row in per_thread:
            if not isinstance(row, Mapping):
                continue
            lines.append(
                f"| {_format_number(row.get('thread_count'))} | "
                f"${_format_number(row.get('symbolic_plan_match_count'))}/"
                f"{_format_number(row.get('symbolic_plan_check_count'))}$ | "
                f"`{_format_number(row.get('numeric_setup_plan_matches_serial'))}` | "
                f"`{_plain_text(row.get('scatter_status'))}` |"
            )
    lines.extend(
        (
            "",
            "$$",
            "S_{\\mathrm{symbolic}}(p)=",
            "\\frac{T_{\\mathrm{symbolic,serial}}}",
            "{T_{\\mathrm{symbolic,parallel}}(p)},",
            "\\qquad",
            "S_{\\mathrm{numeric}}(p)=",
            "\\frac{T_{\\mathrm{numeric,serial}}}",
            "{T_{\\mathrm{numeric,atomic}}(p)}.",
            "$$",
            "",
            "$$",
            "T_{\\mathrm{numeric,atomic}}(p)=",
            "T_{\\mathrm{numeric,reset}}(p)+T_{\\mathrm{numeric,kernel}}(p).",
            "$$",
            "",
            "$$",
            "T_{\\mathrm{amortized}}(p,m)=",
            "\\frac{T_{\\mathrm{symbolic,parallel}}(p)}{m}",
            "+T_{\\mathrm{numeric,total}}(p).",
            "$$",
            "",
            "`numeric_total_ms` 是验证后摊销样本使用的完整候选数值 API 时间；数值加速比、数值 $CV$ 与性能门槛使用 reset 加原子 kernel，即 `numeric_algorithm_ms`。",
        )
    )

    gate = bundle.recomputed_gate
    lines.extend(
        (
            "",
            "## 10. 性能门槛",
            "",
            f"- 门槛状态：`{_plain_text(gate.get('status'))}`；适用：`{_format_number(gate.get('applicable'))}`。",
            f"- 总体要求满足：`{_format_number(gate.get('performance_requirements_met'))}`；符号要求：`{_format_number(gate.get('symbolic_requirement_met'))}`；数值要求：`{_format_number(gate.get('numeric_requirement_met'))}`。",
            f"- 串行符号 $CV$ 要求：`{_format_number(gate.get('serial_symbolic_cv_requirement_met'))}`；串行数值 $CV$ 要求：`{_format_number(gate.get('serial_numeric_cv_requirement_met'))}`；scatter 要求：`{_format_number(gate.get('scatter_requirement_met'))}`；正式总要求：`{_format_number(gate.get('formal_requirements_met'))}`。",
            f"- 符号选中线程 $p={_format_number(gate.get('symbolic_thread_count'))}$；数值选中线程 $p={_format_number(gate.get('numeric_thread_count'))}$。",
            f"- 阈值：$S_{{\\mathrm{{symbolic}}}}> {_format_number(gate.get('symbolic_speedup_threshold'))}$，$S_{{\\mathrm{{numeric}}}}\\ge {_format_number(gate.get('numeric_speedup_threshold'))}$，$CV\\le {_format_number(gate.get('maximum_coefficient_of_variation'))}$。",
            "- 本地或生成数据不是正式性能结论；仅已验证的正式 WindHub 证据可支撑交付性能验收。",
            "",
            "## 11. 内存证据",
            "",
            f"- 持久化 vector payload 估算值：`{_format_number(summary.get('estimated_persistent_bytes'))}` bytes。",
            f"- 证据类型：`{_plain_text(summary.get('estimated_persistent_memory_kind'))}`。",
            "- 该值仅是已拥有 vector 载荷的估算字节数，既不是 RSS，也不是进程内存峰值。",
            "",
            "## 12. 限制、风险与授权状态",
            "",
        )
    )
    blockers = manifest.get("blockers")
    blockers = blockers if isinstance(blockers, list) else []
    if blockers:
        lines.append("- blocker：")
        for blocker in blockers:
            lines.append(f"  - {_sanitize_free_text(blocker)}")
    else:
        lines.append("- blocker：无。")
    lines.extend(
        (
            "- GitHub runner 时序仅是 CI 冒烟证据，不构成正式性能结论。",
            "- MATLAB、Abaqus 与 COMSOL 不在必须 demo 证据范围内。",
            "- 正式 WindHub 验收必须在受控 Linux Intel 主机上执行。",
            f"- 授权状态：`{LICENSE_STATE}`。",
            "",
            "## 13. 原始证据与复现命令",
            "",
            "| 仓库相对 artifact 路径 | 字节数 | SHA-256 |",
            "|---|---:|---|",
        )
    )
    artifacts = manifest.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, list) else []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        lines.append(
            f"| `{_markdown_cell(artifact.get('path'))}` | "
            f"{_format_number(artifact.get('size_bytes'))} | "
            f"`{_markdown_cell(artifact.get('sha256'))}` |"
        )
    lines.append("")
    _append_commands(lines, manifest)
    lines.extend(
        (
            "",
            "本报告不在当前运行 manifest 的 artifact 绑定中，以避免自哈希循环；交付打包时由后续 `MANIFEST.sha256` 绑定本报告。",
        )
    )
    if non_formal:
        lines.extend(("", NON_FORMAL_WARNING))
    return "\n".join(lines) + "\n"


def write_report(manifest_path: Path, output_path: Path) -> str:
    """Validate evidence, atomically create one report, and return its status."""

    manifest_path = Path(manifest_path).expanduser()
    bundle = validate_evidence_bundle(manifest_path)
    requested_output = Path(output_path).expanduser()
    if requested_output.is_symlink():
        raise _error("report output must not be a symbolic link")
    try:
        manifest_resolved = manifest_path.resolve(strict=True)
        output = requested_output.resolve(strict=False)
    except OSError as error:
        raise _error(f"cannot resolve report path: {error}") from error
    forbidden = {manifest_resolved, *bundle.artifact_paths.values()}
    if output in forbidden:
        raise _error("report output overlaps the manifest or a bound artifact")
    if output.exists() or output.is_symlink():
        raise _error(f"report output already exists: {output}")

    content = render_report(bundle).encode("utf-8")
    temporary_path: Path | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=str(output.parent), prefix=f".{output.name}.", suffix=".tmp"
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, output)
        if not output.is_file() or not os.path.samefile(temporary_path, output):
            raise OSError("atomic report publication did not create the destination")
    except FileExistsError as error:
        raise _error(f"report output already exists: {output}") from error
    except OSError as error:
        raise _error(f"cannot write report: {error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    return bundle.report_status


class _CliArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


class _UniquePathAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} may be specified only once")
        setattr(namespace, self.dest, values)


def _argument_parser() -> argparse.ArgumentParser:
    parser = _CliArgumentParser(
        add_help=False,
        allow_abbrev=False,
        description="Validate CSC3 evidence and create a deterministic Markdown report.",
    )
    parser.add_argument(
        "--manifest", required=True, type=Path, action=_UniquePathAction
    )
    parser.add_argument("--out-md", required=True, type=Path, action=_UniquePathAction)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    try:
        status = write_report(arguments.manifest, arguments.out_md)
    except EvidenceValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return {"PASS": 0, "LOCAL_SMOKE": 0, "FAIL": 1, "BLOCKED": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
