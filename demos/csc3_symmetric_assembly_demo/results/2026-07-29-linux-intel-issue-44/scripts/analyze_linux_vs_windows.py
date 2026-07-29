#!/usr/bin/env python3
"""复核并比较 Linux 与 Windows 的 WindHub 独立进程 benchmark 证据。

统计只使用 ``sample_kind=measured`` 的样本。Windows process CSV 不直接
携带阶段分解，因此该脚本会读取每条记录的 ``raw_csv_path``；Linux process
CSV 则使用 Issue #44 adapter 追加的阶段字段，并复算残差进行交叉校验。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence


SCHEMA_VERSION = "csc3-demo-linux-windows-analysis-v1"
PLATFORM_ORDER = ("linux", "windows")
PROCESS_SCHEMAS = {
    "linux": "csc3-demo-linux-process-benchmark-v1",
    "windows": "csc3-demo-windows-process-benchmark-v1",
}
SUMMARY_SCHEMAS = dict(PROCESS_SCHEMAS)
REQUIRED_WARMUP_COUNT = 2
REQUIRED_REPEAT_COUNT = 7

METRIC_FIELDS = (
    "serial_total_ms",
    "parallel_total_ms",
    "symbolic_total_ms",
    "numeric_total_ms",
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_residual_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_residual_ms",
    "fixed_residual_ms",
)
PHASE_FIELDS = (
    "symbolic_total_ms",
    "numeric_total_ms",
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_residual_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_residual_ms",
)
FRACTION_FIELDS = (
    "fixed_residual_fraction_of_parallel_total",
    "symbolic_residual_fraction_of_symbolic_total",
    "numeric_residual_fraction_of_numeric_total",
)
LINUX_DETAIL_FIELDS = (
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_residual_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_residual_ms",
)
RAW_DETAIL_FIELDS = (
    "symbolic_pattern_ms",
    "symbolic_scatter_ms",
    "symbolic_total_ms",
    "numeric_reset_ms",
    "numeric_kernel_ms",
    "numeric_total_ms",
    "amortized_total_ms",
)
RAW_REQUIRED_FIELDS = (
    "schema_version",
    "case_name",
    "element_type",
    "node_count",
    "element_count",
    "dof_count",
    "nnz",
    "thread_count",
    "sample_index",
    "sample_kind",
    "serial_symbolic_ms",
    "serial_numeric_ms",
    *RAW_DETAIL_FIELDS,
    "relative_frobenius_error",
    "max_absolute_error",
    "matrix_correctness_status",
    "performance_evidence_level",
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
)
PROCESS_REQUIRED_FIELDS = (
    "schema_version",
    "sample_id",
    "sample_kind",
    "round",
    "order_position",
    "thread_count",
    "exit_code",
    "started_at_utc",
    "ended_at_utc",
    "symbolic_team_size_observed",
    "numeric_team_size_observed",
    "serial_symbolic_ms",
    "serial_numeric_ms",
    "serial_total_ms",
    "parallel_symbolic_ms",
    "parallel_numeric_ms",
    "parallel_total_ms",
    "relative_frobenius_error",
    "max_absolute_error",
    "structure_matches",
    "matrix_correctness_status",
    "scatter_correctness_status",
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
    "raw_csv_path",
)
SUMMARY_STATISTIC_FIELDS = {
    "serial_total_ms": "serial_total_ms",
    "parallel_total_ms": "parallel_total_ms",
    "symbolic_total_ms": "parallel_symbolic_ms",
    "numeric_total_ms": "parallel_numeric_ms",
}

COMPARISON_FIELDS = (
    "platform",
    "thread_count",
    "measured_sample_count",
    *tuple(
        field
        for metric in METRIC_FIELDS
        for field in (
            f"{metric}_median",
            f"{metric}_coefficient_of_variation",
        )
    ),
    "official_total_speedup",
    "candidate_p1_to_p_total_speedup",
    "official_serial_symbolic_ms_median",
    "official_serial_numeric_ms_median",
    "official_symbolic_phase_speedup",
    "official_numeric_phase_speedup",
    *tuple(f"{metric}_p1_to_p_speedup" for metric in PHASE_FIELDS),
    *tuple(
        field
        for fraction in FRACTION_FIELDS
        for field in (
            f"{fraction}_median",
            f"{fraction}_coefficient_of_variation",
        )
    ),
)

RESIDUAL_TOLERANCE_MS = 1.0e-6
RELATIVE_TOLERANCE = 1.0e-10


class AnalysisError(RuntimeError):
    """表示输入证据或复算结果违反比较契约。"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def as_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise AnalysisError(f"{label} 必须是 JSON object")
    return value


def as_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise AnalysisError(f"{label} 必须是 JSON array")
    return value


def json_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} 必须是整数")
    if not math.isfinite(float(value)):
        raise AnalysisError(f"{label} 必须是有限整数")
    normalized = int(value)
    if normalized != value:
        raise AnalysisError(f"{label} 必须是整数")
    return normalized


def json_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} 必须是数值")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise AnalysisError(f"{label} 必须是有限非负数")
    return normalized


def row_integer(row: Mapping[str, str], field: str, label: str) -> int:
    value = row.get(field)
    try:
        normalized = int(value) if value is not None else None
    except (OverflowError, ValueError) as error:
        raise AnalysisError(f"{label}.{field} 必须是整数") from error
    if normalized is None:
        raise AnalysisError(f"{label}.{field} 缺失")
    return normalized


def row_nonnegative(row: Mapping[str, str], field: str, label: str) -> float:
    value = row.get(field)
    try:
        normalized = float(value) if value is not None else math.nan
    except ValueError as error:
        raise AnalysisError(f"{label}.{field} 必须是数值") from error
    if not math.isfinite(normalized) or normalized < 0.0:
        raise AnalysisError(f"{label}.{field} 必须是有限非负数")
    return normalized


def row_true(row: Mapping[str, str], field: str, label: str) -> bool:
    value = row.get(field)
    if value is None or value.strip().lower() != "true":
        raise AnalysisError(f"{label}.{field} 必须为 true")
    return True


def require_close(actual: float, expected: float, label: str) -> None:
    tolerance = RELATIVE_TOLERANCE * max(1.0, abs(actual), abs(expected))
    if abs(actual - expected) > tolerance:
        raise AnalysisError(
            f"{label} 不一致：actual={actual:.17g}, expected={expected:.17g}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json_object(path: Path, label: str) -> dict[str, object]:
    path = path.resolve()
    if not path.is_file():
        raise AnalysisError(f"{label} 不存在：{path}")
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise AnalysisError(f"{label} 顶层必须是 JSON object")
    return value


def load_csv_rows(
    path: Path,
    required_fields: Sequence[str],
    label: str,
) -> tuple[list[str], list[dict[str, str]]]:
    path = path.resolve()
    if not path.is_file():
        raise AnalysisError(f"{label} 不存在：{path}")
    with path.open("r", encoding="utf-8", errors="strict", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        if len(set(fieldnames)) != len(fieldnames):
            raise AnalysisError(f"{label} 表头存在重复字段")
        missing = sorted(set(required_fields) - set(fieldnames))
        if missing:
            raise AnalysisError(f"{label} 缺少字段：{', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for index, raw_row in enumerate(reader, start=2):
            if None in raw_row or any(value is None for value in raw_row.values()):
                raise AnalysisError(f"{label} 第 {index} 行列数与表头不一致")
            rows.append({str(key): str(value) for key, value in raw_row.items()})
    return fieldnames, rows


def statistics_summary(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise AnalysisError("统计量至少需要一个样本")
    normalized = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0.0 for value in normalized):
        raise AnalysisError("统计样本必须是有限非负数")
    mean = statistics.fmean(normalized)
    coefficient = 0.0 if mean == 0.0 else statistics.pstdev(normalized) / mean
    return {
        "sample_count": len(normalized),
        "median": statistics.median(normalized),
        "coefficient_of_variation": coefficient,
    }


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0.0:
        return None
    return numerator / denominator


def row_datetime(
    row: Mapping[str, str],
    field: str,
    label: str,
) -> datetime:
    value = row.get(field)
    if value is None:
        raise AnalysisError(f"{label}.{field} 缺失")
    try:
        normalized = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AnalysisError(f"{label}.{field} 不是 ISO 8601 时间") from error
    if normalized.tzinfo is None:
        raise AnalysisError(f"{label}.{field} 必须包含时区")
    return normalized


def expected_schedule(
    maximum_threads: int,
    warmup_count: int,
    repeat_count: int,
) -> list[dict[str, int | str]]:
    schedule: list[dict[str, int | str]] = []
    for sample_kind, round_count in (
        ("warmup", warmup_count),
        ("measured", repeat_count),
    ):
        for round_number in range(1, round_count + 1):
            thread_order = (
                range(1, maximum_threads + 1)
                if round_number % 2 == 1
                else range(maximum_threads, 0, -1)
            )
            for order_position, thread_count in enumerate(thread_order, start=1):
                schedule.append(
                    {
                        "sample_kind": sample_kind,
                        "round": round_number,
                        "order_position": order_position,
                        "thread_count": thread_count,
                    }
                )
    return schedule


def validate_process_schedule(
    platform: str,
    rows: Sequence[Mapping[str, str]],
    maximum_threads: int,
    warmup_count: int,
    repeat_count: int,
) -> None:
    schedule = expected_schedule(maximum_threads, warmup_count, repeat_count)
    require(len(rows) == len(schedule), f"{platform} 调度长度不一致")
    previous_end: datetime | None = None
    for csv_line, (row, expected) in enumerate(zip(rows, schedule), start=2):
        label = f"{platform}.row{csv_line}"
        require(
            row.get("sample_kind") == expected["sample_kind"],
            f"{label} sample_kind 不符合交替调度",
        )
        for field in ("round", "order_position", "thread_count"):
            require(
                row_integer(row, field, label) == int(expected[field]),
                f"{label}.{field} 不符合交替调度",
            )
        expected_id = (
            f"{expected['sample_kind']}-"
            f"r{int(expected['round']):02d}-"
            f"o{int(expected['order_position']):02d}-"
            f"p{int(expected['thread_count']):02d}"
        )
        require(
            row.get("sample_id") == expected_id,
            f"{label}.sample_id 与调度字段不一致",
        )
        started_at = row_datetime(row, "started_at_utc", label)
        ended_at = row_datetime(row, "ended_at_utc", label)
        require(ended_at >= started_at, f"{label} 结束时间早于开始时间")
        if previous_end is not None:
            require(started_at >= previous_end, f"{label} 与前一个样本发生时间重叠")
        previous_end = ended_at


def validate_summary_header(
    platform: str,
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
) -> dict[str, int]:
    require(
        summary.get("schema_version") == SUMMARY_SCHEMAS[platform],
        f"{platform} summary schema_version 不受支持",
    )
    require(summary.get("status") == "PASS", f"{platform} summary 未 PASS")

    configuration = as_mapping(
        summary.get("configuration"), f"{platform}.configuration"
    )
    maximum_threads = json_integer(
        configuration.get("maximum_threads"),
        f"{platform}.configuration.maximum_threads",
    )
    warmup_count = json_integer(
        configuration.get("warmup_count"),
        f"{platform}.configuration.warmup_count",
    )
    repeat_count = json_integer(
        configuration.get("repeat_count"),
        f"{platform}.configuration.repeat_count",
    )
    require(maximum_threads > 0, f"{platform} maximum_threads 必须为正")
    require(
        warmup_count == REQUIRED_WARMUP_COUNT,
        f"{platform} warmup_count 必须为 {REQUIRED_WARMUP_COUNT}",
    )
    require(
        repeat_count == REQUIRED_REPEAT_COUNT,
        f"{platform} repeat_count 必须为 {REQUIRED_REPEAT_COUNT}",
    )
    thread_counts = [
        json_integer(value, f"{platform}.configuration.thread_counts")
        for value in as_list(
            configuration.get("thread_counts"),
            f"{platform}.configuration.thread_counts",
        )
    ]
    require(
        thread_counts == list(range(1, maximum_threads + 1)),
        f"{platform} thread_counts 必须是从 1 开始的连续整数",
    )

    expected_total = maximum_threads * (warmup_count + repeat_count)
    expected_measured = maximum_threads * repeat_count
    expected_warmup = maximum_threads * warmup_count
    require(
        len(rows) == expected_total,
        f"{platform} process CSV 样本数错误："
        f"expected={expected_total}, actual={len(rows)}",
    )
    kinds = [row.get("sample_kind") for row in rows]
    require(
        set(kinds) <= {"warmup", "measured"},
        f"{platform} process CSV 存在未知 sample_kind",
    )
    require(
        kinds.count("measured") == expected_measured,
        f"{platform} measured 样本数错误",
    )
    require(kinds.count("warmup") == expected_warmup, f"{platform} warmup 样本数错误")
    sample_ids = [str(row.get("sample_id", "")) for row in rows]
    require(all(sample_ids), f"{platform} process CSV 存在空 sample_id")
    require(
        len(set(sample_ids)) == len(sample_ids),
        f"{platform} process CSV 存在重复 sample_id",
    )
    validate_process_schedule(
        platform,
        rows,
        maximum_threads,
        warmup_count,
        repeat_count,
    )

    integrity = as_mapping(
        summary.get("process_integrity"), f"{platform}.process_integrity"
    )
    require(
        json_integer(
            integrity.get("expected_sample_count"),
            f"{platform}.process_integrity.expected_sample_count",
        )
        == expected_total,
        f"{platform} summary expected_sample_count 不一致",
    )
    require(
        json_integer(
            integrity.get("observed_sample_count"),
            f"{platform}.process_integrity.observed_sample_count",
        )
        == len(rows),
        f"{platform} summary observed_sample_count 不一致",
    )
    require(
        json_integer(
            integrity.get("measured_sample_count_per_thread"),
            f"{platform}.process_integrity.measured_sample_count_per_thread",
        )
        == repeat_count,
        f"{platform} summary measured_sample_count_per_thread 不一致",
    )
    for field in (
        "unique_sample_ids",
        "samples_overlap",
        "all_exit_codes_zero",
        "all_observed_team_sizes_match",
    ):
        expected = False if field == "samples_overlap" else True
        require(
            integrity.get(field) is expected,
            f"{platform}.process_integrity.{field} 不符合 PASS 契约",
        )

    correctness = as_mapping(
        summary.get("correctness"), f"{platform}.correctness"
    )
    require(
        correctness.get("status") == "PASS",
        f"{platform} summary correctness 未 PASS",
    )
    for field in (
        "all_csc3_structures_match",
        "all_values_finite",
        "all_scatter_indices_legal",
        "all_scatter_plans_match_independent_serial",
    ):
        require(
            correctness.get(field) is True,
            f"{platform}.correctness.{field} 必须为 true",
        )
    maximum_error = json_nonnegative(
        correctness.get("relative_frobenius_error_maximum"),
        f"{platform}.correctness.relative_frobenius_error_maximum",
    )
    threshold = json_nonnegative(
        correctness.get("relative_frobenius_error_threshold"),
        f"{platform}.correctness.relative_frobenius_error_threshold",
    )
    require(maximum_error <= threshold, f"{platform} summary 相对误差超阈值")
    return {
        "maximum_threads": maximum_threads,
        "warmup_count": warmup_count,
        "repeat_count": repeat_count,
        "expected_total": expected_total,
        "expected_measured": expected_measured,
    }


def windows_raw_detail(
    process_csv: Path,
    process_row: Mapping[str, str],
    label: str,
) -> dict[str, object]:
    evidence_root = process_csv.resolve().parent
    relative_text = str(process_row.get("raw_csv_path", "")).replace("\\", "/")
    require(relative_text != "", f"{label}.raw_csv_path 缺失")
    raw_path = (evidence_root / Path(relative_text)).resolve()
    try:
        raw_path.relative_to(evidence_root)
    except ValueError as error:
        raise AnalysisError(f"{label}.raw_csv_path 逃逸 Windows 证据目录") from error
    _, raw_rows = load_csv_rows(raw_path, RAW_REQUIRED_FIELDS, f"{label}.raw_csv")
    require(len(raw_rows) == 1, f"{label}.raw_csv 必须恰好包含一行")
    raw = raw_rows[0]
    require(
        raw.get("schema_version") == "csc3-demo-benchmark-v2",
        f"{label}.raw_csv schema_version 不受支持",
    )
    require(raw.get("sample_kind") == "measured", f"{label}.raw_csv 不是 measured")
    require(
        row_integer(raw, "sample_index", f"{label}.raw_csv") == 0,
        f"{label}.raw_csv sample_index 必须为 0",
    )
    require(
        raw.get("performance_evidence_level") == "local-smoke",
        f"{label}.raw_csv evidence level 不一致",
    )
    require(
        str(raw.get("case_name", "")) != ""
        and str(raw.get("element_type", "")) != "",
        f"{label}.raw_csv case identity 缺失",
    )
    for field in ("node_count", "element_count", "dof_count", "nnz"):
        require(
            row_integer(raw, field, f"{label}.raw_csv") > 0,
            f"{label}.raw_csv {field} 必须为正",
        )
    process_thread = row_integer(process_row, "thread_count", label)
    require(
        row_integer(raw, "thread_count", f"{label}.raw_csv") == process_thread,
        f"{label}.raw_csv thread_count 不一致",
    )
    detail: dict[str, object] = {
        field: row_nonnegative(raw, field, f"{label}.raw_csv")
        for field in RAW_DETAIL_FIELDS
    }
    for process_field, raw_field in (
        ("serial_symbolic_ms", "serial_symbolic_ms"),
        ("serial_numeric_ms", "serial_numeric_ms"),
        ("parallel_symbolic_ms", "symbolic_total_ms"),
        ("parallel_numeric_ms", "numeric_total_ms"),
        ("parallel_total_ms", "amortized_total_ms"),
        ("relative_frobenius_error", "relative_frobenius_error"),
        ("max_absolute_error", "max_absolute_error"),
    ):
        require_close(
            row_nonnegative(process_row, process_field, label),
            row_nonnegative(raw, raw_field, f"{label}.raw_csv"),
            f"{label} process/raw {process_field}",
        )
    require(raw.get("matrix_correctness_status") == "PASS", f"{label}.raw_csv 未 PASS")
    row_true(raw, "symbolic_plan_matches_serial", f"{label}.raw_csv")
    row_true(raw, "numeric_setup_plan_matches_serial", f"{label}.raw_csv")
    detail.update(
        {
            "_source_path": raw_path.relative_to(evidence_root).as_posix(),
            "_source_size_bytes": raw_path.stat().st_size,
            "_source_sha256": sha256_file(raw_path),
        }
    )
    return detail


def normalize_measured_row(
    platform: str,
    process_csv: Path,
    row: Mapping[str, str],
    relative_error_threshold: float,
) -> dict[str, float | int | str]:
    sample_id = str(row.get("sample_id", ""))
    label = f"{platform}.{sample_id}"
    require(row.get("sample_kind") == "measured", f"{label} 不是 measured")
    require(
        row.get("schema_version") == PROCESS_SCHEMAS[platform],
        f"{label} schema_version 不受支持",
    )
    thread_count = row_integer(row, "thread_count", label)
    round_number = row_integer(row, "round", label)
    require(row_integer(row, "exit_code", label) == 0, f"{label} exit_code 非零")
    require(
        row_integer(row, "symbolic_team_size_observed", label) == thread_count,
        f"{label} symbolic team size 不一致",
    )
    require(
        row_integer(row, "numeric_team_size_observed", label) == thread_count,
        f"{label} numeric team size 不一致",
    )
    require(
        row.get("matrix_correctness_status") == "PASS",
        f"{label} matrix correctness 未 PASS",
    )
    require(
        row.get("scatter_correctness_status") == "PASS",
        f"{label} scatter correctness 未 PASS",
    )
    row_true(row, "structure_matches", label)
    row_true(row, "symbolic_plan_matches_serial", label)
    row_true(row, "numeric_setup_plan_matches_serial", label)
    relative_error = row_nonnegative(row, "relative_frobenius_error", label)
    row_nonnegative(row, "max_absolute_error", label)
    require(
        relative_error <= relative_error_threshold,
        f"{label} relative_frobenius_error 超阈值",
    )

    serial_symbolic = row_nonnegative(row, "serial_symbolic_ms", label)
    serial_numeric = row_nonnegative(row, "serial_numeric_ms", label)
    serial_total = row_nonnegative(row, "serial_total_ms", label)
    symbolic_total = row_nonnegative(row, "parallel_symbolic_ms", label)
    numeric_total = row_nonnegative(row, "parallel_numeric_ms", label)
    parallel_total = row_nonnegative(row, "parallel_total_ms", label)
    require_close(
        serial_total,
        serial_symbolic + serial_numeric,
        f"{label}.serial_total_ms",
    )
    require_close(
        parallel_total,
        symbolic_total + numeric_total,
        f"{label}.parallel_total_ms",
    )

    if platform == "windows":
        detail = windows_raw_detail(process_csv, row, label)
        pattern = float(detail["symbolic_pattern_ms"])
        scatter = float(detail["symbolic_scatter_ms"])
        reset = float(detail["numeric_reset_ms"])
        kernel = float(detail["numeric_kernel_ms"])
    else:
        pattern = row_nonnegative(row, "symbolic_pattern_ms", label)
        scatter = row_nonnegative(row, "symbolic_scatter_ms", label)
        reset = row_nonnegative(row, "numeric_reset_ms", label)
        kernel = row_nonnegative(row, "numeric_kernel_ms", label)

    symbolic_residual = symbolic_total - pattern - scatter
    numeric_residual = numeric_total - reset - kernel
    require(
        symbolic_residual >= -RESIDUAL_TOLERANCE_MS,
        f"{label} symbolic residual 为负",
    )
    require(
        numeric_residual >= -RESIDUAL_TOLERANCE_MS,
        f"{label} numeric residual 为负",
    )
    symbolic_residual = max(0.0, symbolic_residual)
    numeric_residual = max(0.0, numeric_residual)
    if platform == "linux":
        require_close(
            symbolic_residual,
            row_nonnegative(row, "symbolic_residual_ms", label),
            f"{label}.symbolic_residual_ms",
        )
        require_close(
            numeric_residual,
            row_nonnegative(row, "numeric_residual_ms", label),
            f"{label}.numeric_residual_ms",
        )

    fixed_residual = symbolic_residual + numeric_residual
    require(symbolic_total > 0.0, f"{label} symbolic_total_ms 必须为正")
    require(numeric_total > 0.0, f"{label} numeric_total_ms 必须为正")
    require(parallel_total > 0.0, f"{label} parallel_total_ms 必须为正")
    normalized: dict[str, float | int | str] = {
        "sample_id": sample_id,
        "thread_count": thread_count,
        "round": round_number,
        "serial_symbolic_ms": serial_symbolic,
        "serial_numeric_ms": serial_numeric,
        "serial_total_ms": serial_total,
        "parallel_total_ms": parallel_total,
        "symbolic_total_ms": symbolic_total,
        "numeric_total_ms": numeric_total,
        "symbolic_pattern_ms": pattern,
        "symbolic_scatter_ms": scatter,
        "symbolic_residual_ms": symbolic_residual,
        "numeric_reset_ms": reset,
        "numeric_kernel_ms": kernel,
        "numeric_residual_ms": numeric_residual,
        "fixed_residual_ms": fixed_residual,
        "fixed_residual_fraction_of_parallel_total": (
            fixed_residual / parallel_total
        ),
        "symbolic_residual_fraction_of_symbolic_total": (
            symbolic_residual / symbolic_total
        ),
        "numeric_residual_fraction_of_numeric_total": (
            numeric_residual / numeric_total
        ),
    }
    if platform == "windows":
        normalized.update(
            {
                "_phase_source_path": str(detail["_source_path"]),
                "_phase_source_size_bytes": int(detail["_source_size_bytes"]),
                "_phase_source_sha256": str(detail["_source_sha256"]),
            }
        )
    return normalized


def validate_summary_statistics(
    platform: str,
    summary: Mapping[str, object],
    per_thread: Sequence[Mapping[str, object]],
    official_baseline: Mapping[str, float | int],
) -> None:
    serial_baseline = as_mapping(
        summary.get("serial_baseline_total_ms"),
        f"{platform}.serial_baseline_total_ms",
    )
    for field in ("sample_count", "median", "coefficient_of_variation"):
        if field == "sample_count":
            require(
                json_integer(
                    serial_baseline.get(field),
                    f"{platform}.serial_baseline_total_ms.{field}",
                )
                == int(official_baseline[field]),
                f"{platform} serial baseline sample_count 不一致",
            )
        else:
            require_close(
                json_nonnegative(
                    serial_baseline.get(field),
                    f"{platform}.serial_baseline_total_ms.{field}",
                ),
                float(official_baseline[field]),
                f"{platform}.serial_baseline_total_ms.{field}",
            )

    summary_threads = as_list(summary.get("per_thread"), f"{platform}.per_thread")
    require(
        len(summary_threads) == len(per_thread),
        f"{platform} summary per_thread 数量不一致",
    )
    summary_by_thread: dict[int, Mapping[str, object]] = {}
    for item in summary_threads:
        normalized = as_mapping(item, f"{platform}.per_thread item")
        thread_count = json_integer(
            normalized.get("thread_count"), f"{platform}.per_thread.thread_count"
        )
        require(
            thread_count not in summary_by_thread,
            f"{platform} summary thread_count 重复",
        )
        summary_by_thread[thread_count] = normalized

    for computed in per_thread:
        thread_count = int(computed["thread_count"])
        expected = summary_by_thread.get(thread_count)
        require(expected is not None, f"{platform} summary 缺少 p={thread_count}")
        require(
            expected.get("observed_team_sizes") == [thread_count],
            f"{platform} summary p={thread_count} observed_team_sizes 不一致",
        )
        computed_statistics = as_mapping(
            computed.get("statistics"),
            f"{platform}.computed p={thread_count}.statistics",
        )
        for computed_field, summary_field in SUMMARY_STATISTIC_FIELDS.items():
            actual_statistics = as_mapping(
                computed_statistics.get(computed_field),
                f"{platform}.computed p={thread_count}.{computed_field}",
            )
            expected_statistics = as_mapping(
                expected.get(summary_field),
                f"{platform}.summary p={thread_count}.{summary_field}",
            )
            require(
                json_integer(
                    expected_statistics.get("sample_count"),
                    f"{platform}.summary p={thread_count}.{summary_field}.sample_count",
                )
                == int(actual_statistics["sample_count"]),
                f"{platform} p={thread_count} {summary_field} sample_count 不一致",
            )
            for field in ("median", "coefficient_of_variation"):
                require_close(
                    json_nonnegative(
                        expected_statistics.get(field),
                        f"{platform}.summary p={thread_count}.{summary_field}.{field}",
                    ),
                    float(actual_statistics[field]),
                    f"{platform} p={thread_count} {summary_field}.{field}",
                )
        speedups = as_mapping(
            computed.get("speedups"), f"{platform}.computed p={thread_count}.speedups"
        )
        require_close(
            json_nonnegative(
                expected.get("overall_speedup"),
                f"{platform}.summary p={thread_count}.overall_speedup",
            ),
            float(speedups["official_total_speedup"]),
            f"{platform} p={thread_count} official speedup",
        )


def analyze_platform(
    platform: str,
    process_csv: Path,
    summary_path: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    required_fields = list(PROCESS_REQUIRED_FIELDS)
    if platform == "linux":
        required_fields.extend(LINUX_DETAIL_FIELDS)
    _, all_rows = load_csv_rows(
        process_csv,
        required_fields,
        f"{platform} process CSV",
    )
    summary = load_json_object(summary_path, f"{platform} summary")
    contract = validate_summary_header(platform, summary, all_rows)
    for index, row in enumerate(all_rows, start=2):
        require(
            row.get("schema_version") == PROCESS_SCHEMAS[platform],
            f"{platform} process CSV 第 {index} 行 schema_version 不受支持",
        )
        require(
            row_integer(row, "exit_code", f"{platform}.row{index}") == 0,
            f"{platform} process CSV 第 {index} 行 exit_code 非零",
        )

    correctness = as_mapping(
        summary.get("correctness"), f"{platform}.correctness"
    )
    relative_error_threshold = json_nonnegative(
        correctness.get("relative_frobenius_error_threshold"),
        f"{platform}.correctness.relative_frobenius_error_threshold",
    )
    measured = [
        normalize_measured_row(
            platform,
            process_csv.resolve(),
            row,
            relative_error_threshold,
        )
        for row in all_rows
        if row.get("sample_kind") == "measured"
    ]
    if platform == "windows":
        phase_source_files = sorted(
            (
                {
                    "sample_id": str(record["sample_id"]),
                    "path": str(record["_phase_source_path"]),
                    "size_bytes": int(record["_phase_source_size_bytes"]),
                    "sha256": str(record["_phase_source_sha256"]),
                }
                for record in measured
            ),
            key=lambda item: str(item["sample_id"]),
        )
        phase_source_provenance: dict[str, object] = {
            "kind": "per-sample raw CSV",
            "file_count": len(phase_source_files),
            "files": phase_source_files,
        }
    else:
        phase_source_provenance = {
            "kind": "aggregate process CSV columns",
            "file_count": 1,
        }
    maximum_threads = contract["maximum_threads"]
    repeat_count = contract["repeat_count"]
    by_thread: dict[int, list[dict[str, float | int | str]]] = {
        thread: [] for thread in range(1, maximum_threads + 1)
    }
    for record in measured:
        thread_count = int(record["thread_count"])
        require(
            thread_count in by_thread,
            f"{platform} measured 样本 thread_count 超出配置",
        )
        by_thread[thread_count].append(record)
    for thread_count, records in by_thread.items():
        require(
            len(records) == repeat_count,
            f"{platform} p={thread_count} measured 样本数不是 {repeat_count}",
        )
        rounds = sorted(int(record["round"]) for record in records)
        require(
            rounds == list(range(1, repeat_count + 1)),
            f"{platform} p={thread_count} measured round 不完整或重复",
        )

    official_baseline = statistics_summary(
        [float(record["serial_total_ms"]) for record in by_thread[1]]
    )
    official_phase_baselines = {
        "serial_symbolic_ms": statistics_summary(
            [float(record["serial_symbolic_ms"]) for record in by_thread[1]]
        ),
        "serial_numeric_ms": statistics_summary(
            [float(record["serial_numeric_ms"]) for record in by_thread[1]]
        ),
    }
    p1_medians = {
        metric: float(
            statistics_summary(
                [float(record[metric]) for record in by_thread[1]]
            )["median"]
        )
        for metric in METRIC_FIELDS
    }

    per_thread: list[dict[str, object]] = []
    comparison_rows: list[dict[str, object]] = []
    for thread_count in range(1, maximum_threads + 1):
        records = by_thread[thread_count]
        metric_statistics = {
            metric: statistics_summary(
                [float(record[metric]) for record in records]
            )
            for metric in METRIC_FIELDS
        }
        fraction_statistics = {
            fraction: statistics_summary(
                [float(record[fraction]) for record in records]
            )
            for fraction in FRACTION_FIELDS
        }
        parallel_total_median = float(
            metric_statistics["parallel_total_ms"]["median"]
        )
        official_speedup = ratio(
            float(official_baseline["median"]),
            parallel_total_median,
        )
        require(
            official_speedup is not None,
            f"{platform} p={thread_count} official speedup 分母为零",
        )
        candidate_speedup = ratio(
            p1_medians["parallel_total_ms"],
            parallel_total_median,
        )
        require(
            candidate_speedup is not None,
            f"{platform} p={thread_count} candidate speedup 分母为零",
        )
        official_phase_speedups = {
            "symbolic": ratio(
                float(official_phase_baselines["serial_symbolic_ms"]["median"]),
                float(metric_statistics["symbolic_total_ms"]["median"]),
            ),
            "numeric": ratio(
                float(official_phase_baselines["serial_numeric_ms"]["median"]),
                float(metric_statistics["numeric_total_ms"]["median"]),
            ),
        }
        phase_speedups = {
            metric: ratio(
                p1_medians[metric],
                float(metric_statistics[metric]["median"]),
            )
            for metric in PHASE_FIELDS
        }
        result = {
            "thread_count": thread_count,
            "statistics": metric_statistics,
            "speedups": {
                "official_total_speedup": official_speedup,
                "candidate_p1_to_p_total_speedup": candidate_speedup,
                "official_phase_speedup": official_phase_speedups,
                "phase_p1_to_p_speedup": phase_speedups,
            },
            "residual_fractions": fraction_statistics,
        }
        per_thread.append(result)

        comparison: dict[str, object] = {
            "platform": platform,
            "thread_count": thread_count,
            "measured_sample_count": len(records),
            "official_total_speedup": official_speedup,
            "candidate_p1_to_p_total_speedup": candidate_speedup,
            "official_serial_symbolic_ms_median": official_phase_baselines[
                "serial_symbolic_ms"
            ]["median"],
            "official_serial_numeric_ms_median": official_phase_baselines[
                "serial_numeric_ms"
            ]["median"],
            "official_symbolic_phase_speedup": official_phase_speedups[
                "symbolic"
            ],
            "official_numeric_phase_speedup": official_phase_speedups["numeric"],
        }
        for metric in METRIC_FIELDS:
            comparison[f"{metric}_median"] = metric_statistics[metric]["median"]
            comparison[f"{metric}_coefficient_of_variation"] = (
                metric_statistics[metric]["coefficient_of_variation"]
            )
        for metric in PHASE_FIELDS:
            comparison[f"{metric}_p1_to_p_speedup"] = phase_speedups[metric]
        for fraction in FRACTION_FIELDS:
            comparison[f"{fraction}_median"] = fraction_statistics[fraction][
                "median"
            ]
            comparison[f"{fraction}_coefficient_of_variation"] = (
                fraction_statistics[fraction]["coefficient_of_variation"]
            )
        comparison_rows.append(comparison)

    validate_summary_statistics(
        platform,
        summary,
        per_thread,
        official_baseline,
    )
    maximum_result = per_thread[-1]
    maximum_speedups = as_mapping(
        maximum_result["speedups"], f"{platform}.maximum speedups"
    )
    maximum_fractions = as_mapping(
        maximum_result["residual_fractions"],
        f"{platform}.maximum residual_fractions",
    )
    validation = {
        "status": "PASS",
        "process_schema_version": PROCESS_SCHEMAS[platform],
        "summary_schema_version": SUMMARY_SCHEMAS[platform],
        "total_sample_count": len(all_rows),
        "measured_sample_count": len(measured),
        "measured_sample_count_per_thread": repeat_count,
        "all_sample_ids_unique": True,
        "all_exit_codes_zero": True,
        "all_measured_team_sizes_match": True,
        "all_measured_correctness_checks_pass": True,
        "sample_count_median_cv_and_speedup_match_summary": True,
        "exact_alternating_schedule_matches": True,
        "samples_do_not_overlap": True,
    }
    result = {
        "platform": platform,
        "maximum_threads": maximum_threads,
        "warmup_count": contract["warmup_count"],
        "repeat_count": repeat_count,
        "official_serial_baseline_total_ms": official_baseline,
        "official_serial_phase_baselines_ms": official_phase_baselines,
        "phase_source_provenance": phase_source_provenance,
        "validation": validation,
        "maximum_thread_result": {
            "thread_count": maximum_threads,
            "official_total_speedup": maximum_speedups["official_total_speedup"],
            "candidate_p1_to_p_total_speedup": maximum_speedups[
                "candidate_p1_to_p_total_speedup"
            ],
            "phase_p1_to_p_speedup": maximum_speedups[
                "phase_p1_to_p_speedup"
            ],
            "official_phase_speedup": maximum_speedups[
                "official_phase_speedup"
            ],
            "fixed_residual_fraction_of_parallel_total": as_mapping(
                maximum_fractions[
                    "fixed_residual_fraction_of_parallel_total"
                ],
                f"{platform}.maximum fixed residual fraction",
            )["median"],
        },
        "per_thread": per_thread,
    }
    return result, comparison_rows


def validate_cross_platform_input_contract(
    linux_summary: Mapping[str, object],
    windows_summary: Mapping[str, object],
    linux_result: Mapping[str, object],
    windows_result: Mapping[str, object],
) -> dict[str, object]:
    linux_input = as_mapping(linux_summary.get("input"), "linux.input")
    windows_input = as_mapping(windows_summary.get("input"), "windows.input")
    for field in ("sha256", "size_bytes"):
        require(
            linux_input.get(field) == windows_input.get(field),
            f"Linux/Windows input.{field} 不一致",
        )
    linux_sizes = as_mapping(linux_summary.get("case_sizes"), "linux.case_sizes")
    windows_sizes = as_mapping(
        windows_summary.get("case_sizes"), "windows.case_sizes"
    )
    require(linux_sizes == windows_sizes, "Linux/Windows case_sizes 不一致")
    require(
        linux_result.get("warmup_count") == windows_result.get("warmup_count"),
        "Linux/Windows warmup_count 不一致",
    )
    require(
        linux_result.get("repeat_count") == windows_result.get("repeat_count"),
        "Linux/Windows repeat_count 不一致",
    )
    return {
        "status": "PASS",
        "scope": (
            "仅验证输入实体、case sizes、warmup/repeat；"
            "不声明源码、构建或计时实现等价"
        ),
        "input_sha256_matches": True,
        "input_size_matches": True,
        "case_sizes_match": True,
        "warmup_count_matches": True,
        "repeat_count_matches": True,
    }


def canonical_json(value: object) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=COMPARISON_FIELDS,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def input_record(process_csv: Path, summary_path: Path) -> dict[str, object]:
    process_csv = process_csv.resolve()
    summary_path = summary_path.resolve()
    return {
        "process_csv_path": str(process_csv),
        "process_csv_sha256": sha256_file(process_csv),
        "process_csv_size_bytes": process_csv.stat().st_size,
        "summary_json_path": str(summary_path),
        "summary_json_sha256": sha256_file(summary_path),
        "summary_json_size_bytes": summary_path.stat().st_size,
    }


def build_analysis(
    options: argparse.Namespace,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    linux_process_csv = options.linux_process_csv.resolve()
    linux_summary_path = options.linux_summary.resolve()
    windows_process_csv = options.windows_process_csv.resolve()
    windows_summary_path = options.windows_summary.resolve()

    linux_result, linux_rows = analyze_platform(
        "linux", linux_process_csv, linux_summary_path
    )
    windows_result, windows_rows = analyze_platform(
        "windows", windows_process_csv, windows_summary_path
    )
    linux_summary = load_json_object(linux_summary_path, "linux summary")
    windows_summary = load_json_object(windows_summary_path, "windows summary")
    cross_platform_input_contract = validate_cross_platform_input_contract(
        linux_summary,
        windows_summary,
        linux_result,
        windows_result,
    )

    comparison_rows = sorted(
        [*linux_rows, *windows_rows],
        key=lambda row: (
            int(row["thread_count"]),
            PLATFORM_ORDER.index(str(row["platform"])),
        ),
    )
    common_maximum_threads = min(
        int(linux_result["maximum_threads"]),
        int(windows_result["maximum_threads"]),
    )
    analysis = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "definitions": {
            "sample_scope": "仅 sample_kind=measured 的独立子进程样本参与统计",
            "statistics": (
                "median 为样本中位数；coefficient_of_variation "
                "为总体标准差除以均值"
            ),
            "sampling_contract": "固定 W=2、R=7，轮次按线程数升序/降序交替",
            "official_total_speedup": (
                "median(serial_total_ms, measured p=1) / "
                "median(parallel_total_ms, measured p)"
            ),
            "candidate_p1_to_p_total_speedup": (
                "median(parallel_total_ms, measured p=1) / "
                "median(parallel_total_ms, measured p)"
            ),
            "official_phase_speedup": (
                "symbolic 或 numeric 的 measured p=1 串行阶段中位数 / "
                "同一候选阶段 measured p 中位数"
            ),
            "phase_p1_to_p_speedup": (
                "指定阶段 measured p=1 中位数 / 同阶段 measured p 中位数"
            ),
            "symbolic_residual_ms": (
                "symbolic_total_ms - symbolic_pattern_ms - symbolic_scatter_ms"
            ),
            "numeric_residual_ms": (
                "numeric_total_ms - numeric_reset_ms - numeric_kernel_ms"
            ),
            "fixed_residual_ms": (
                "symbolic_residual_ms + numeric_residual_ms；它是未分项时间，"
                "不能仅凭该字段断言全部为串行工作"
            ),
            "fixed_residual_fraction_of_parallel_total": (
                "每个 measured 样本先计算 fixed_residual_ms / parallel_total_ms，"
                "再按 p 汇总 median/CV"
            ),
            "windows_phase_source": (
                "Windows process CSV 每条 measured 记录的 raw_csv_path"
            ),
            "linux_phase_source": "Linux process CSV 的 adapter 阶段分解字段",
            "cross_platform_limit": (
                "本分析只验证输入与数据契约一致；源码、构建、OpenMP runtime "
                "和主机环境等价性必须由两侧 manifest 与实验报告另行证明"
            ),
        },
        "inputs": {
            "linux": input_record(linux_process_csv, linux_summary_path),
            "windows": input_record(windows_process_csv, windows_summary_path),
        },
        "cross_platform_input_contract_validation": (
            cross_platform_input_contract
        ),
        "comparison_scope": {
            "linux_maximum_threads": linux_result["maximum_threads"],
            "windows_maximum_threads": windows_result["maximum_threads"],
            "common_maximum_threads": common_maximum_threads,
        },
        "platforms": [linux_result, windows_result],
        "comparison_csv_sort": ["thread_count ascending", "linux before windows"],
    }
    return analysis, comparison_rows


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-process-csv", type=Path, required=True)
    parser.add_argument("--linux-summary", type=Path, required=True)
    parser.add_argument("--windows-process-csv", type=Path, required=True)
    parser.add_argument("--windows-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        options = build_argument_parser().parse_args(arguments)
        analysis, comparison_rows = build_analysis(options)
        output_dir = options.output_dir.resolve()
        analysis_path = output_dir / "analysis_summary.json"
        comparison_path = output_dir / "comparison.csv"
        atomic_write_text(analysis_path, canonical_json(analysis))
        atomic_write_csv(comparison_path, comparison_rows)
    except (AnalysisError, OSError, UnicodeError, csv.Error, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        canonical_json(
            {
                "status": "PASS",
                "analysis_summary": str(analysis_path),
                "comparison_csv": str(comparison_path),
                "comparison_row_count": len(comparison_rows),
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
