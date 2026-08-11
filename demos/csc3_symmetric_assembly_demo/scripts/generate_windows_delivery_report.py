#!/usr/bin/env python3
"""根据 Windows 独立进程实测证据生成 Issue #54 中文报告与性能图。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Mapping, Sequence


EXPECTED_TOP_LEVEL_HEADINGS = (
    "结论",
    "Demo 范围与接口位置",
    "并行符号组装算法",
    "OpenMP atomic 数值组装算法",
    "串行参考实现",
    "测试环境",
    "矩阵正确性",
    "不同线程数下的内存、时间和加速比",
)
WARMUP_COUNT = 2
REPEAT_COUNT = 7
RELATIVE_FROBENIUS_TOLERANCE = 1.0e-8
FIGURE_WIDTH_MM = 183.0
FIGURE_HEIGHT_MM = 125.0
PNG_DPI = 300
TIFF_DPI = 600
REPORT_SCHEMA_VERSION = "csc3-demo-windows-report-v1"
PROCESS_SCHEMA_VERSION = "csc3-demo-windows-process-benchmark-v1"
MANIFEST_SCHEMA_VERSION = "csc3-demo-windows-process-manifest-v1"
BUILD_EVIDENCE_SCHEMA_VERSION = "csc3-demo-windows-build-evidence-v1"
PROCESS_CSV_FIELDS = (
    "schema_version",
    "sample_id",
    "sample_kind",
    "round",
    "order_position",
    "thread_count",
    "pid",
    "started_at_utc",
    "ended_at_utc",
    "wall_time_seconds",
    "exit_code",
    "peak_working_set_bytes",
    "peak_working_set_source",
    "symbolic_team_size_observed",
    "numeric_team_size_observed",
    "input_prepare_ms",
    "serial_symbolic_ms",
    "serial_numeric_ms",
    "serial_total_ms",
    "parallel_symbolic_ms",
    "parallel_numeric_ms",
    "parallel_total_ms",
    "estimated_persistent_bytes",
    "relative_frobenius_error",
    "max_absolute_error",
    "structure_matches",
    "matrix_correctness_status",
    "scatter_correctness_status",
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
    "raw_csv_path",
    "raw_json_path",
    "stdout_log_path",
    "stderr_log_path",
)
STATISTIC_FIELDS = (
    "median",
    "mean",
    "population_standard_deviation",
    "minimum",
    "maximum",
    "coefficient_of_variation",
)


class ReportContractError(RuntimeError):
    """输入证据或生成结果违反 Issue #54 报告契约。"""


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReportContractError(f"无法读取 JSON：{path.name}") from error
    if not isinstance(value, dict):
        raise ReportContractError(f"JSON 顶层必须是对象：{path.name}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as error:
        raise ReportContractError(f"无法读取 CSV：{path.name}") from error
    if not rows:
        raise ReportContractError("性能 CSV 不得为空")
    return rows


def _as_int(value: object, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ReportContractError(f"{label} 不是整数") from error
    return result


def _as_float(value: object, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ReportContractError(f"{label} 不是数值") from error
    if not math.isfinite(result):
        raise ReportContractError(f"{label} 不是有限数")
    return result


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ReportContractError(f"{label} 必须是对象")
    return value


def _relative_link(target: Path, report_parent: Path) -> str:
    return Path(os.path.relpath(target.resolve(), report_parent.resolve())).as_posix()


def _extract_headings(report: str) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## ([^\r\n]+)$", report, flags=re.MULTILINE)
    )


def validate_report_headings(report: str) -> None:
    headings = _extract_headings(report)
    if headings != EXPECTED_TOP_LEVEL_HEADINGS:
        raise ReportContractError(
            "报告一级章节必须严格按 Issue #54 的八章顺序生成："
            f"实际为 {headings!r}"
        )


def _validate_statistics(value: object, label: str, expected_count: int) -> None:
    statistics_object = _require_mapping(value, label)
    if _as_int(statistics_object.get("sample_count"), f"{label}.sample_count") != expected_count:
        raise ReportContractError(f"{label} 的样本数不是 {expected_count}")
    for field in STATISTIC_FIELDS:
        number = _as_float(statistics_object.get(field), f"{label}.{field}")
        if number < 0.0:
            raise ReportContractError(f"{label}.{field} 不得为负数")


def _as_bool(value: object, label: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ReportContractError(f"{label} 不是布尔值")


def _statistics(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise ReportContractError("重新统计时没有正式样本")
    normalized = [float(value) for value in values]
    mean = statistics.fmean(normalized)
    standard_deviation = statistics.pstdev(normalized)
    return {
        "sample_count": len(normalized),
        "median": statistics.median(normalized),
        "mean": mean,
        "population_standard_deviation": standard_deviation,
        "minimum": min(normalized),
        "maximum": max(normalized),
        "coefficient_of_variation": (
            0.0 if mean == 0.0 else standard_deviation / mean
        ),
    }


def _require_close(actual: object, expected: float, label: str) -> None:
    number = _as_float(actual, label)
    if not math.isclose(number, expected, rel_tol=1.0e-12, abs_tol=1.0e-9):
        raise ReportContractError(
            f"{label} 与 CSV 重新计算结果不一致：记录值 {number!r}，"
            f"重算值 {expected!r}"
        )


def _validate_statistics_match(
    value: object,
    label: str,
    expected: Mapping[str, float | int],
) -> None:
    statistics_object = _require_mapping(value, label)
    if _as_int(
        statistics_object.get("sample_count"),
        f"{label}.sample_count",
    ) != int(expected["sample_count"]):
        raise ReportContractError(f"{label}.sample_count 与 CSV 不一致")
    for field in STATISTIC_FIELDS:
        _require_close(
            statistics_object.get(field),
            float(expected[field]),
            f"{label}.{field}",
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: object, label: str) -> str:
    text = str(value).replace("\\", "/")
    path = PurePosixPath(text)
    if (
        not text
        or text.startswith("/")
        or re.match(r"^[A-Za-z]:", text)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ReportContractError(f"{label} 不是安全的相对路径")
    return path.as_posix()


def _validate_artifact_hashes(
    manifest: Mapping[str, object],
    performance_root: Path,
) -> set[str]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReportContractError("manifest 缺少性能工件清单")

    performance_root = performance_root.resolve()
    indexed: dict[str, Mapping[str, object]] = {}
    for raw_record in artifacts:
        record = _require_mapping(raw_record, "manifest artifact")
        relative = _safe_relative_path(record.get("path"), "artifact.path")
        if relative in indexed:
            raise ReportContractError(f"manifest 工件路径重复：{relative}")
        path = (performance_root / PurePosixPath(relative)).resolve()
        try:
            path.relative_to(performance_root)
        except ValueError as error:
            raise ReportContractError(f"manifest 工件越出证据目录：{relative}") from error
        if not path.is_file():
            raise ReportContractError(f"manifest 工件不存在：{relative}")
        if _as_int(record.get("size_bytes"), f"{relative}.size_bytes") != path.stat().st_size:
            raise ReportContractError(f"manifest 工件大小不匹配：{relative}")
        expected_sha256 = str(record.get("sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ReportContractError(f"manifest 工件 SHA-256 非法：{relative}")
        if _sha256_file(path) != expected_sha256:
            raise ReportContractError(f"manifest 工件 SHA-256 不匹配：{relative}")
        indexed[relative] = record

    actual_files = {
        path.relative_to(performance_root).as_posix()
        for path in performance_root.rglob("*")
        if path.is_file() and path.name != "run_manifest.json"
    }
    recorded_files = set(indexed)
    if recorded_files != actual_files:
        missing = sorted(actual_files - recorded_files)
        stale = sorted(recorded_files - actual_files)
        raise ReportContractError(
            "manifest 工件清单没有完整覆盖性能目录："
            f"未记录={missing}，不存在={stale}"
        )
    for required in ("benchmark_samples.csv", "benchmark_summary.json"):
        if required not in indexed:
            raise ReportContractError(f"manifest 工件清单缺少 {required}")
    return recorded_files


def _expected_schedule(maximum_threads: int) -> list[dict[str, int | str]]:
    schedule: list[dict[str, int | str]] = []
    for sample_kind, round_count in (
        ("warmup", WARMUP_COUNT),
        ("measured", REPEAT_COUNT),
    ):
        for round_number in range(1, round_count + 1):
            threads = list(range(1, maximum_threads + 1))
            if round_number % 2 == 0:
                threads.reverse()
            for order_position, thread_count in enumerate(threads, start=1):
                schedule.append(
                    {
                        "sample_kind": sample_kind,
                        "round": round_number,
                        "order_position": order_position,
                        "thread_count": thread_count,
                    }
                )
    return schedule


def _validate_manifest_samples(
    manifest: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    maximum_threads: int,
    artifact_paths: set[str] | None,
) -> None:
    expected_schedule = _expected_schedule(maximum_threads)
    manifest_configuration = _require_mapping(
        manifest.get("configuration"),
        "manifest.configuration",
    )
    if manifest_configuration.get("schedule") != expected_schedule:
        raise ReportContractError("manifest 调度表不符合 W=2、R=7 交替扫描")
    if manifest_configuration.get("thread_counts") != list(
        range(1, maximum_threads + 1)
    ):
        raise ReportContractError("manifest 线程列表没有完整覆盖 1..Pmax")
    for field, expected in (
        ("maximum_threads", maximum_threads),
        ("warmup_count", WARMUP_COUNT),
        ("repeat_count", REPEAT_COUNT),
    ):
        if _as_int(manifest_configuration.get(field), f"manifest.{field}") != expected:
            raise ReportContractError(f"manifest.{field} 与报告契约不一致")
    if (
        manifest_configuration.get("sample_process_model")
        != "one_fresh_child_process_per_sample"
        or manifest_configuration.get("samples_are_serialized") is not True
    ):
        raise ReportContractError("manifest 未确认独立进程串行采样")

    samples = manifest.get("samples")
    if not isinstance(samples, list) or len(samples) != len(rows):
        raise ReportContractError("manifest 样本记录与 CSV 数量不一致")
    previous_end: datetime | None = None
    identity_fields = (
        "sample_id",
        "sample_kind",
        "round",
        "order_position",
        "thread_count",
        "pid",
        "started_at_utc",
        "ended_at_utc",
        "exit_code",
        "peak_working_set_bytes",
        "symbolic_team_size_observed",
        "numeric_team_size_observed",
        "raw_csv_path",
        "raw_json_path",
    )
    for index, (row, expected, raw_sample) in enumerate(
        zip(rows, expected_schedule, samples),
        start=1,
    ):
        if set(row) != set(PROCESS_CSV_FIELDS):
            raise ReportContractError("性能 CSV 字段不符合固定 schema")
        if row.get("schema_version") != PROCESS_SCHEMA_VERSION:
            raise ReportContractError("性能 CSV schema_version 不受支持")
        for field, expected_value in expected.items():
            actual: object = row.get(field)
            if field in {"round", "order_position", "thread_count"}:
                actual = _as_int(actual, field)
            if actual != expected_value:
                raise ReportContractError(f"CSV 第 {index} 条样本不符合交替扫描顺序")
        expected_id = (
            f"{expected['sample_kind']}-r{int(expected['round']):02d}-"
            f"o{int(expected['order_position']):02d}-"
            f"p{int(expected['thread_count']):02d}"
        )
        if row.get("sample_id") != expected_id:
            raise ReportContractError(f"CSV 第 {index} 条样本 ID 与调度不一致")

        sample = _require_mapping(raw_sample, "manifest sample")
        for field in identity_fields:
            manifest_value = sample.get(field)
            csv_value: object = row.get(field)
            if field in {
                "round",
                "order_position",
                "thread_count",
                "pid",
                "exit_code",
                "peak_working_set_bytes",
                "symbolic_team_size_observed",
                "numeric_team_size_observed",
            }:
                csv_value = _as_int(csv_value, field)
            if manifest_value != csv_value:
                raise ReportContractError(
                    f"manifest 样本与 CSV 不一致：{expected_id}.{field}"
                )

        try:
            started = datetime.fromisoformat(
                str(row.get("started_at_utc")).replace("Z", "+00:00")
            )
            ended = datetime.fromisoformat(
                str(row.get("ended_at_utc")).replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ReportContractError(f"{expected_id} 时间戳非法") from error
        if ended < started or (previous_end is not None and started < previous_end):
            raise ReportContractError("性能样本发生重叠或时间倒置")
        previous_end = ended

        if artifact_paths is not None:
            for field in (
                "raw_csv_path",
                "raw_json_path",
                "stdout_log_path",
                "stderr_log_path",
            ):
                relative = _safe_relative_path(row.get(field), f"{expected_id}.{field}")
                if relative not in artifact_paths:
                    raise ReportContractError(
                        f"manifest 工件清单缺少样本原始文件：{relative}"
                    )


def _validate_summary_against_csv(
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    maximum_threads: int,
) -> None:
    measured = _measured_rows(rows)
    serial_values = [
        _as_float(row.get("serial_total_ms"), "serial_total_ms")
        for row in measured[1]
    ]
    serial_statistics = _statistics(serial_values)
    _validate_statistics_match(
        summary.get("serial_baseline_total_ms"),
        "serial_baseline_total_ms",
        serial_statistics,
    )
    serial_median = float(serial_statistics["median"])

    per_thread_value = summary.get("per_thread")
    if not isinstance(per_thread_value, list):
        raise ReportContractError("per_thread 必须是数组")
    per_thread = {
        _as_int(_require_mapping(item, "per_thread item").get("thread_count"), "thread_count"):
        _require_mapping(item, "per_thread item")
        for item in per_thread_value
    }
    field_map = {
        "serial_total_ms": "serial_total_ms",
        "parallel_symbolic_ms": "parallel_symbolic_ms",
        "parallel_numeric_ms": "parallel_numeric_ms",
        "parallel_total_ms": "parallel_total_ms",
        "peak_working_set_bytes": "peak_working_set_bytes",
        "estimated_persistent_bytes": "estimated_persistent_bytes",
    }
    for thread_count in range(1, maximum_threads + 1):
        item = per_thread[thread_count]
        samples = measured[thread_count]
        expected_by_field: dict[str, Mapping[str, float | int]] = {}
        for summary_field, csv_field in field_map.items():
            expected = _statistics(
                [_as_float(row.get(csv_field), csv_field) for row in samples]
            )
            expected_by_field[summary_field] = expected
            _validate_statistics_match(
                item.get(summary_field),
                f"p={thread_count}.{summary_field}",
                expected,
            )
        parallel_median = float(expected_by_field["parallel_total_ms"]["median"])
        _require_close(
            item.get("overall_speedup"),
            serial_median / parallel_median,
            f"p={thread_count}.overall_speedup",
        )

    maximum_error = max(
        _as_float(row.get("relative_frobenius_error"), "relative_frobenius_error")
        for row in rows
    )
    correctness = _require_mapping(summary.get("correctness"), "correctness")
    _require_close(
        correctness.get("relative_frobenius_error_maximum"),
        maximum_error,
        "correctness.relative_frobenius_error_maximum",
    )


def _validate_build_evidence(
    build_evidence: Mapping[str, object],
    build_root: Path | None,
) -> None:
    if build_evidence.get("schema_version") != BUILD_EVIDENCE_SCHEMA_VERSION:
        raise ReportContractError("构建证据 schema_version 不受支持")
    if build_evidence.get("issue") != 54:
        raise ReportContractError("构建证据未绑定 Issue #54")
    builds = build_evidence.get("builds")
    if not isinstance(builds, list) or len(builds) != 2:
        raise ReportContractError("构建证据必须同时包含 MSVC 与 MinGW 两套工具链")
    indexed = {
        str(_require_mapping(item, "build item").get("id")):
        _require_mapping(item, "build item")
        for item in builds
    }
    if set(indexed) != {"msvc", "mingw"}:
        raise ReportContractError("构建证据缺少 msvc 或 mingw")
    for build_id, build in indexed.items():
        for field in (
            "configure_status",
            "build_status",
            "app_status",
            "ctest_status",
            "consumer_status",
            "openmp_off_gate_status",
            "openmp_missing_gate_status",
            "clean_room_status",
        ):
            if build.get(field) != "PASS":
                raise ReportContractError(f"{build_id} 的 {field} 不是 PASS")
        expected_counts = {
            "ctest_passed": 10,
            "ctest_failed": 0,
            "consumer_passed": 1,
            "consumer_failed": 0,
            "clean_room_ctest_passed": 10,
            "clean_room_consumer_passed": 1,
        }
        for field, expected in expected_counts.items():
            if _as_int(build.get(field), f"{build_id}.{field}") != expected:
                raise ReportContractError(
                    f"{build_id}.{field} 不是预期值 {expected}"
                )

    commands = build_evidence.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ReportContractError("构建证据缺少可复制命令")
    for command_value in commands:
        command = _require_mapping(command_value, "command item")
        if command.get("status") != "PASS" or not str(command.get("command", "")).strip():
            raise ReportContractError("构建命令记录不完整")
        relative_log = _safe_relative_path(command.get("log"), "command.log")
        if build_root is not None and not (build_root.resolve() / relative_log).is_file():
            raise ReportContractError(f"构建命令日志不存在：{relative_log}")


def validate_evidence(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    build_evidence: Mapping[str, object],
    *,
    performance_root: Path | None = None,
    build_root: Path | None = None,
) -> int:
    """验证报告只消费满足 Issue #54 的完整证据。"""

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ReportContractError("性能 manifest schema_version 不受支持")
    if summary.get("schema_version") != PROCESS_SCHEMA_VERSION:
        raise ReportContractError("性能 summary schema_version 不受支持")
    if manifest.get("issue") != 54:
        raise ReportContractError("性能 manifest 未绑定 Issue #54")
    if manifest.get("status") != "PASS":
        raise ReportContractError("性能运行 manifest 不是 PASS")
    if summary.get("status") != "PASS":
        raise ReportContractError("性能汇总不是 PASS")
    if build_evidence.get("status") != "PASS":
        raise ReportContractError("构建证据不是 PASS")
    if manifest.get("summary_status") != "PASS":
        raise ReportContractError("性能 manifest 未确认 summary PASS")
    if manifest.get("input") != summary.get("input"):
        raise ReportContractError("性能 manifest 与 summary 的输入追溯不一致")

    artifact_paths: set[str] | None = None
    if performance_root is not None:
        artifact_paths = _validate_artifact_hashes(manifest, performance_root)
    elif not isinstance(manifest.get("artifacts"), list) or not manifest.get("artifacts"):
        raise ReportContractError("manifest 缺少性能工件清单")

    configuration = _require_mapping(summary.get("configuration"), "summary.configuration")
    maximum_threads = _as_int(
        configuration.get("maximum_threads"),
        "summary.configuration.maximum_threads",
    )
    if maximum_threads <= 0:
        raise ReportContractError("最大线程数必须为正数")
    if _as_int(configuration.get("warmup_count"), "warmup_count") != WARMUP_COUNT:
        raise ReportContractError("报告只接受 W=2 的证据")
    if _as_int(configuration.get("repeat_count"), "repeat_count") != REPEAT_COUNT:
        raise ReportContractError("报告只接受 R=7 的证据")
    if configuration.get("sample_process_model") != "one_fresh_child_process_per_sample":
        raise ReportContractError("每个样本必须来自新子进程")
    if configuration.get("samples_are_serialized") is not True:
        raise ReportContractError("样本必须串行执行")
    if configuration.get("measured_round_order") != "alternating_ascending_descending":
        raise ReportContractError("正式轮次必须升序/降序交替")

    manifest_environment = _require_mapping(
        manifest.get("environment"),
        "manifest.environment",
    )
    logical_processors = _as_int(
        manifest_environment.get("logical_processor_count"),
        "logical_processor_count",
    )
    if maximum_threads != logical_processors:
        raise ReportContractError("线程扫描上限不是 Windows 逻辑处理器数")

    _validate_manifest_samples(
        manifest,
        rows,
        maximum_threads,
        artifact_paths,
    )

    integrity = _require_mapping(summary.get("process_integrity"), "process_integrity")
    expected_samples = maximum_threads * (WARMUP_COUNT + REPEAT_COUNT)
    required_integrity = {
        "expected_sample_count": expected_samples,
        "observed_sample_count": expected_samples,
        "measured_sample_count_per_thread": REPEAT_COUNT,
        "unique_sample_ids": True,
        "samples_overlap": False,
        "all_exit_codes_zero": True,
        "all_observed_team_sizes_match": True,
    }
    for key, expected in required_integrity.items():
        if integrity.get(key) != expected:
            raise ReportContractError(f"进程完整性字段不通过：{key}")
    if len(rows) != expected_samples:
        raise ReportContractError(
            f"CSV 样本数不完整：期望 {expected_samples}，实际 {len(rows)}"
        )

    sample_ids: set[str] = set()
    measured_counts: defaultdict[int, int] = defaultdict(int)
    warmup_counts: defaultdict[int, int] = defaultdict(int)
    for row in rows:
        sample_id = str(row.get("sample_id", ""))
        if not sample_id or sample_id in sample_ids:
            raise ReportContractError("CSV 样本身份缺失或重复")
        sample_ids.add(sample_id)
        thread_count = _as_int(row.get("thread_count"), "thread_count")
        if thread_count not in range(1, maximum_threads + 1):
            raise ReportContractError("CSV 包含扫描范围之外的线程数")
        if _as_int(row.get("pid"), "pid") <= 0:
            raise ReportContractError("CSV PID 非法")
        if _as_int(row.get("exit_code"), "exit_code") != 0:
            raise ReportContractError("CSV 存在失败子进程")
        if (
            _as_int(row.get("symbolic_team_size_observed"), "symbolic team")
            != thread_count
            or _as_int(row.get("numeric_team_size_observed"), "numeric team")
            != thread_count
        ):
            raise ReportContractError("CSV 存在实际 team size 不符样本")
        if row.get("peak_working_set_source") != (
            "GetProcessMemoryInfo.PeakWorkingSetSize"
        ):
            raise ReportContractError("峰值内存来源不是 Windows PeakWorkingSetSize")
        if _as_float(row.get("peak_working_set_bytes"), "peak working set") <= 0.0:
            raise ReportContractError("峰值工作集必须为正数")
        for field in (
            "wall_time_seconds",
            "input_prepare_ms",
            "serial_symbolic_ms",
            "serial_numeric_ms",
            "serial_total_ms",
            "parallel_symbolic_ms",
            "parallel_numeric_ms",
            "parallel_total_ms",
            "estimated_persistent_bytes",
            "max_absolute_error",
        ):
            if _as_float(row.get(field), field) < 0.0:
                raise ReportContractError(f"CSV {field} 不得为负数")
        _require_close(
            row.get("serial_total_ms"),
            _as_float(row.get("serial_symbolic_ms"), "serial_symbolic_ms")
            + _as_float(row.get("serial_numeric_ms"), "serial_numeric_ms"),
            "serial_total_ms",
        )
        _require_close(
            row.get("parallel_total_ms"),
            _as_float(row.get("parallel_symbolic_ms"), "parallel_symbolic_ms")
            + _as_float(row.get("parallel_numeric_ms"), "parallel_numeric_ms"),
            "parallel_total_ms",
        )
        if _as_float(row.get("relative_frobenius_error"), "e_F") > (
            RELATIVE_FROBENIUS_TOLERANCE
        ):
            raise ReportContractError("CSV 中的相对 Frobenius 误差超限")
        for field in (
            "structure_matches",
            "symbolic_plan_matches_serial",
            "numeric_setup_plan_matches_serial",
        ):
            if _as_bool(row.get(field), field) is not True:
                raise ReportContractError(f"CSV 正确性字段不通过：{field}")
        for field in ("matrix_correctness_status", "scatter_correctness_status"):
            if row.get(field) != "PASS":
                raise ReportContractError(f"CSV 正确性状态不通过：{field}")
        if row.get("sample_kind") == "measured":
            measured_counts[thread_count] += 1
        elif row.get("sample_kind") == "warmup":
            warmup_counts[thread_count] += 1
        else:
            raise ReportContractError("CSV 样本类型必须是 warmup 或 measured")

    for thread_count in range(1, maximum_threads + 1):
        if measured_counts[thread_count] != REPEAT_COUNT:
            raise ReportContractError(f"线程 {thread_count} 的 measured 样本不完整")
        if warmup_counts[thread_count] != WARMUP_COUNT:
            raise ReportContractError(f"线程 {thread_count} 的 warmup 样本不完整")

    correctness = _require_mapping(summary.get("correctness"), "correctness")
    if correctness.get("status") != "PASS":
        raise ReportContractError("矩阵正确性汇总不是 PASS")
    if _as_float(
        correctness.get("relative_frobenius_error_maximum"),
        "e_F maximum",
    ) > RELATIVE_FROBENIUS_TOLERANCE:
        raise ReportContractError("矩阵正确性汇总中的 e_F 超限")
    for field in (
        "all_csc3_structures_match",
        "all_values_finite",
        "all_scatter_indices_legal",
        "all_scatter_plans_match_independent_serial",
    ):
        if correctness.get(field) is not True:
            raise ReportContractError(f"矩阵正确性字段不通过：{field}")

    memory_definition = _require_mapping(
        summary.get("memory_definition"),
        "memory_definition",
    )
    if memory_definition.get("peak_working_set") != (
        "GetProcessMemoryInfo.PeakWorkingSetSize"
    ):
        raise ReportContractError("汇总中的峰值内存口径错误")
    if memory_definition.get("peak_working_set_is_os_measured") is not True:
        raise ReportContractError("峰值内存未标记为操作系统实测")

    per_thread = summary.get("per_thread")
    if not isinstance(per_thread, list) or len(per_thread) != maximum_threads:
        raise ReportContractError("每线程汇总不完整")
    observed_threads: list[int] = []
    for item_value in per_thread:
        item = _require_mapping(item_value, "per_thread item")
        thread_count = _as_int(item.get("thread_count"), "per_thread.thread_count")
        observed_threads.append(thread_count)
        if item.get("observed_team_sizes") != [thread_count]:
            raise ReportContractError("汇总中的实际 team size 与请求不符")
        for field in (
            "serial_total_ms",
            "parallel_symbolic_ms",
            "parallel_numeric_ms",
            "parallel_total_ms",
            "peak_working_set_bytes",
            "estimated_persistent_bytes",
        ):
            _validate_statistics(item.get(field), f"p={thread_count}.{field}", REPEAT_COUNT)
        if _as_float(item.get("overall_speedup"), "overall_speedup") < 0.0:
            raise ReportContractError("加速比不得为负数")
    if observed_threads != list(range(1, maximum_threads + 1)):
        raise ReportContractError("每线程汇总没有完整覆盖 1..Pmax")
    _validate_statistics(
        summary.get("serial_baseline_total_ms"),
        "serial_baseline_total_ms",
        REPEAT_COUNT,
    )

    _validate_summary_against_csv(summary, rows, maximum_threads)
    _validate_build_evidence(build_evidence, build_root)

    return maximum_threads


def _load_plotting_backend():
    # Python 3.13 下部分 matplotlib/pyparsing 组合会报告上游弃用提醒；
    # 只过滤这两个依赖模块，不屏蔽本脚本自己的运行时警告。
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"^(matplotlib|pyparsing)(\.|$)",
    )
    try:
        import matplotlib as mpl

        mpl.use("Agg")
        import matplotlib.pyplot as plt
        from PIL import Image, ImageStat
    except ImportError as error:
        raise ReportContractError(
            "生成报告图需要 Python 包 matplotlib 与 Pillow"
        ) from error
    return mpl, plt, Image, ImageStat


def _measured_rows(
    rows: Sequence[Mapping[str, str]],
) -> dict[int, list[Mapping[str, str]]]:
    grouped: defaultdict[int, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("sample_kind") == "measured":
            grouped[_as_int(row.get("thread_count"), "thread_count")].append(row)
    for samples in grouped.values():
        samples.sort(key=lambda row: _as_int(row.get("round"), "round"))
    return dict(grouped)


def generate_performance_figure(
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    figure_dir: Path,
) -> dict[str, object]:
    """用 Python 生成时间、加速比与 Windows 峰值工作集三联图。"""

    mpl, plt, Image, ImageStat = _load_plotting_backend()
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Microsoft YaHei",
                "PingFang SC",
                "Noto Sans CJK SC",
                "SimHei",
                "Arial",
                "DejaVu Sans",
                "sans-serif",
            ],
            "font.size": 7,
            "axes.titlesize": 8,
            "axes.labelsize": 7,
            "axes.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    figure_dir.mkdir(parents=True, exist_ok=True)
    grouped = _measured_rows(rows)
    per_thread = summary["per_thread"]
    if not isinstance(per_thread, list):
        raise ReportContractError("per_thread 必须是数组")
    thread_counts = [
        _as_int(_require_mapping(item, "per_thread item").get("thread_count"), "thread")
        for item in per_thread
    ]
    parallel_medians = [
        _as_float(
            _require_mapping(
                _require_mapping(item, "per_thread item").get("parallel_total_ms"),
                "parallel_total_ms",
            ).get("median"),
            "parallel median",
        )
        / 1000.0
        for item in per_thread
    ]
    speedups = [
        _as_float(
            _require_mapping(item, "per_thread item").get("overall_speedup"),
            "speedup",
        )
        for item in per_thread
    ]
    peak_medians = [
        _as_float(
            _require_mapping(
                _require_mapping(item, "per_thread item").get(
                    "peak_working_set_bytes"
                ),
                "peak_working_set_bytes",
            ).get("median"),
            "peak median",
        )
        / (1024.0**3)
        for item in per_thread
    ]
    serial_baseline = _as_float(
        _require_mapping(
            summary.get("serial_baseline_total_ms"),
            "serial_baseline_total_ms",
        ).get("median"),
        "serial baseline median",
    ) / 1000.0

    width_inches = FIGURE_WIDTH_MM / 25.4
    height_inches = FIGURE_HEIGHT_MM / 25.4
    figure, axes = plt.subplots(
        1,
        3,
        figsize=(width_inches, height_inches),
        constrained_layout=True,
    )
    colors = {
        "raw": "#9CB6C7",
        "median": "#356A8A",
        "serial": "#8D6A9F",
        "accent": "#C27755",
        "memory": "#6C8C78",
        "grid": "#D9DEE3",
    }
    jitter = [
        -0.18 + 0.36 * index / (REPEAT_COUNT - 1)
        for index in range(REPEAT_COUNT)
    ]

    time_axis = axes[0]
    for thread_count in thread_counts:
        samples = grouped[thread_count]
        for offset, row in zip(jitter, samples):
            time_axis.scatter(
                thread_count + offset,
                _as_float(row.get("parallel_total_ms"), "parallel_total_ms")
                / 1000.0,
                s=8,
                color=colors["raw"],
                alpha=0.75,
                edgecolors="none",
                zorder=2,
            )
    time_axis.plot(
        thread_counts,
        parallel_medians,
        color=colors["median"],
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="并行总时间中位数",
        zorder=3,
    )
    time_axis.axhline(
        serial_baseline,
        color=colors["serial"],
        linestyle="--",
        linewidth=1.0,
        label="串行基线中位数",
    )
    time_axis.set_title("组装总时间")
    time_axis.set_xlabel("OpenMP 线程数 $p$")
    time_axis.set_ylabel("时间（s）")
    time_axis.legend(loc="best", fontsize=6)

    speed_axis = axes[1]
    speed_axis.plot(
        thread_counts,
        thread_counts,
        color=colors["grid"],
        linestyle="--",
        linewidth=0.9,
        label="理想线性加速比",
    )
    speed_axis.plot(
        thread_counts,
        speedups,
        color=colors["accent"],
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="实测总体加速比",
    )
    speed_axis.axhline(1.0, color="#777777", linewidth=0.7)
    speed_axis.set_title("总体加速比")
    speed_axis.set_xlabel("OpenMP 线程数 $p$")
    speed_axis.set_ylabel("$S_p$")
    speed_axis.legend(loc="best", fontsize=6)

    memory_axis = axes[2]
    for thread_count in thread_counts:
        samples = grouped[thread_count]
        for offset, row in zip(jitter, samples):
            memory_axis.scatter(
                thread_count + offset,
                _as_float(
                    row.get("peak_working_set_bytes"),
                    "peak_working_set_bytes",
                )
                / (1024.0**3),
                s=8,
                color="#ABC3B2",
                alpha=0.75,
                edgecolors="none",
                zorder=2,
            )
    memory_axis.plot(
        thread_counts,
        peak_medians,
        color=colors["memory"],
        marker="o",
        markersize=3,
        linewidth=1.2,
        label="峰值工作集中位数",
        zorder=3,
    )
    memory_axis.set_title("Windows 峰值工作集")
    memory_axis.set_xlabel("OpenMP 线程数 $p$")
    memory_axis.set_ylabel("峰值工作集（GiB）")
    memory_axis.legend(loc="best", fontsize=6)

    for axis in axes:
        axis.set_xticks(thread_counts)
        axis.tick_params(axis="x", labelrotation=45, labelsize=5.7)
        axis.grid(axis="y", color=colors["grid"], linewidth=0.5, alpha=0.7)
        axis.text(
            0.99,
            0.02,
            "每个 $p$：$n=7$，独立子进程",
            transform=axis.transAxes,
            ha="right",
            va="bottom",
            fontsize=5.7,
            color="#555555",
        )

    png_path = figure_dir / "windows-thread-scan.png"
    svg_path = figure_dir / "windows-thread-scan.svg"
    pdf_path = figure_dir / "windows-thread-scan.pdf"
    tiff_path = figure_dir / "windows-thread-scan.tiff"
    figure.savefig(png_path, dpi=PNG_DPI, facecolor="white")
    figure.savefig(svg_path, facecolor="white")
    figure.savefig(pdf_path, facecolor="white")
    figure.savefig(
        tiff_path,
        dpi=TIFF_DPI,
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(figure)

    with Image.open(png_path) as image:
        expected_width = round(width_inches * PNG_DPI)
        expected_height = round(height_inches * PNG_DPI)
        if abs(image.width - expected_width) > 3 or abs(image.height - expected_height) > 3:
            raise ReportContractError("PNG 尺寸不符合 183 mm × 125 mm、300 dpi 契约")
        grayscale = image.convert("L")
        extrema = ImageStat.Stat(grayscale).extrema[0]
        if extrema[1] - extrema[0] < 40:
            raise ReportContractError("PNG 疑似空白或对比度不足")
        png_dimensions = [image.width, image.height]
    with Image.open(tiff_path) as image:
        expected_width = round(width_inches * TIFF_DPI)
        expected_height = round(height_inches * TIFF_DPI)
        if abs(image.width - expected_width) > 3 or abs(image.height - expected_height) > 3:
            raise ReportContractError("TIFF 尺寸不符合 183 mm × 125 mm、600 dpi 契约")
        tiff_dimensions = [image.width, image.height]
    svg_text = svg_path.read_text(encoding="utf-8")
    text_element_count = len(re.findall(r"<text(?:\s|>)", svg_text))
    if text_element_count < 20:
        raise ReportContractError("SVG 没有保留足够的可编辑文本元素")
    if pdf_path.stat().st_size < 10_000:
        raise ReportContractError("PDF 输出异常小")

    qa = {
        "schema_version": "csc3-demo-figure-qa-v1",
        "status": "PASS",
        "backend": "Python/matplotlib",
        "backend_exclusive": True,
        "archetype": "quantitative grid",
        "core_conclusion": (
            "完整线程扫描用同一组独立子进程样本同时展示组装时间、总体加速比与 "
            "Windows 峰值工作集，不筛除不利线程数。"
        ),
        "panel_map": {
            "a": "并行符号与 atomic 数值组装总时间及串行基线",
            "b": "总体加速比与理想线性参考",
            "c": "Windows PeakWorkingSetSize",
        },
        "source_data": "benchmark_samples.csv",
        "statistics": {
            "sample_definition": "one fresh child process per sample",
            "warmup_count": WARMUP_COUNT,
            "measured_count_per_thread": REPEAT_COUNT,
            "center": "median",
            "spread_in_report": "population standard deviation and range",
        },
        "image_integrity": {
            "raw_raster_images": False,
            "local_adjustments": False,
            "data_points_omitted": False,
        },
        "final_size_mm": [FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM],
        "png": {
            "dpi": PNG_DPI,
            "dimensions_px": png_dimensions,
            "nonblank": True,
        },
        "tiff": {
            "dpi": TIFF_DPI,
            "dimensions_px": tiff_dimensions,
            "compression": "tiff_lzw",
        },
        "svg": {
            "editable_text": True,
            "text_element_count": text_element_count,
        },
        "pdf": {"editable_truetype_text_requested": True},
        "reviewer_risks_addressed": [
            "显示全部线程数而非只展示最优点",
            "原始七个正式样本与中位数同时可见",
            "峰值工作集与持久容量估计明确分离",
            "线程 team size 与进程隔离由 manifest 和 CSV 追溯",
        ],
    }
    qa_path = figure_dir / "figure_qa.json"
    qa_path.write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "png_path": png_path,
        "svg_path": svg_path,
        "pdf_path": pdf_path,
        "tiff_path": tiff_path,
        "qa_path": qa_path,
        "qa": qa,
    }


def _format_ms(value: object) -> str:
    return f"{_as_float(value, 'milliseconds'):.3f}"


def _format_stat_row(
    thread_count: int,
    statistics_object: Mapping[str, object],
    scale: float = 1.0,
) -> str:
    values = [
        _as_float(statistics_object.get("median"), "median") / scale,
        _as_float(statistics_object.get("mean"), "mean") / scale,
        _as_float(
            statistics_object.get("population_standard_deviation"),
            "population_standard_deviation",
        )
        / scale,
        _as_float(statistics_object.get("minimum"), "minimum") / scale,
        _as_float(statistics_object.get("maximum"), "maximum") / scale,
        100.0
        * _as_float(
            statistics_object.get("coefficient_of_variation"),
            "coefficient_of_variation",
        ),
    ]
    return (
        f"| {thread_count} | {values[0]:.3f} | {values[1]:.3f} | "
        f"{values[2]:.3f} | {values[3]:.3f} | {values[4]:.3f} | "
        f"{values[5]:.2f}% |"
    )


def _render_build_table(build_evidence: Mapping[str, object]) -> str:
    rows = [
        "| 工具链 | 编译器 | OpenMP | 配置 | 构建 | CTest | consumer | clean-room |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    builds = build_evidence["builds"]
    if not isinstance(builds, list):
        raise ReportContractError("builds 必须是数组")
    for build_value in builds:
        build = _require_mapping(build_value, "build item")
        rows.append(
            "| {name} | `{compiler}` | `{openmp}` | {configure} | {build_status} | "
            "{ctest} | {consumer} | {clean_room} |".format(
                name=build.get("name"),
                compiler=build.get("compiler"),
                openmp=build.get("openmp"),
                configure=build.get("configure_status"),
                build_status=build.get("build_status"),
                ctest=build.get("ctest_status"),
                consumer=build.get("consumer_status"),
                clean_room=build.get("clean_room_status"),
            )
        )
    return "\n".join(rows)


def _render_commands(build_evidence: Mapping[str, object]) -> str:
    commands = build_evidence["commands"]
    if not isinstance(commands, list):
        raise ReportContractError("commands 必须是数组")
    blocks: list[str] = []
    for command_value in commands:
        command = _require_mapping(command_value, "command item")
        blocks.extend(
            [
                f"**{command.get('purpose')} — {command.get('status')}**",
                "",
                "```powershell",
                str(command.get("command")),
                "```",
                "",
                f"日志：`{command.get('log')}`",
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


def _case_size_text(case_sizes: object) -> str:
    mapping = _require_mapping(case_sizes, "case_sizes")
    items = [f"`{key}={value}`" for key, value in sorted(mapping.items())]
    return "、".join(items)


def render_report(
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    build_evidence: Mapping[str, object],
    report_path: Path,
    samples_csv_path: Path,
    summary_path: Path,
    manifest_path: Path,
    figure_outputs: Mapping[str, object],
) -> str:
    maximum_threads = validate_evidence(
        manifest,
        summary,
        rows,
        build_evidence,
    )
    per_thread_value = summary["per_thread"]
    if not isinstance(per_thread_value, list):
        raise ReportContractError("per_thread 必须是数组")
    per_thread = [
        _require_mapping(item, "per_thread item") for item in per_thread_value
    ]
    best = max(
        per_thread,
        key=lambda item: _as_float(item.get("overall_speedup"), "overall_speedup"),
    )
    best_thread = _as_int(best.get("thread_count"), "best thread")
    best_speedup = _as_float(best.get("overall_speedup"), "best speedup")
    best_parallel = _require_mapping(best.get("parallel_total_ms"), "parallel total")
    best_peak = _require_mapping(best.get("peak_working_set_bytes"), "peak memory")
    serial_statistics = _require_mapping(
        summary.get("serial_baseline_total_ms"),
        "serial baseline",
    )
    correctness = _require_mapping(summary.get("correctness"), "correctness")
    max_relative_error = _as_float(
        correctness.get("relative_frobenius_error_maximum"),
        "maximum relative error",
    )
    max_absolute_error = max(
        _as_float(row.get("max_absolute_error"), "max_absolute_error")
        for row in rows
    )
    environment = _require_mapping(manifest.get("environment"), "environment")
    source = _require_mapping(manifest.get("source"), "source")
    toolchain = _require_mapping(manifest.get("toolchain"), "toolchain")
    input_facts = _require_mapping(manifest.get("input"), "input")
    process_integrity = _require_mapping(
        summary.get("process_integrity"),
        "process_integrity",
    )

    report_parent = report_path.parent
    csv_link = _relative_link(samples_csv_path, report_parent)
    summary_link = _relative_link(summary_path, report_parent)
    manifest_link = _relative_link(manifest_path, report_parent)
    figure_link = _relative_link(
        Path(figure_outputs["png_path"]),
        report_parent,
    )
    figure_qa_link = _relative_link(
        Path(figure_outputs["qa_path"]),
        report_parent,
    )

    time_rows = [
        "| $p$ | 中位数（ms） | 均值（ms） | 总体标准差（ms） | 最小值（ms） | 最大值（ms） | 变异系数 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    memory_rows = [
        "| $p$ | 中位数（GiB） | 均值（GiB） | 总体标准差（GiB） | 最小值（GiB） | 最大值（GiB） | 变异系数 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    phase_rows = [
        "| $p$ | 符号中位数（ms） | 数值中位数（ms） | 并行总时间中位数（ms） | 总体加速比 | 持久容量估计中位数（GiB） |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for item in per_thread:
        thread_count = _as_int(item.get("thread_count"), "thread_count")
        total = _require_mapping(item.get("parallel_total_ms"), "parallel_total_ms")
        peak = _require_mapping(
            item.get("peak_working_set_bytes"),
            "peak_working_set_bytes",
        )
        time_rows.append(_format_stat_row(thread_count, total))
        memory_rows.append(
            _format_stat_row(thread_count, peak, scale=1024.0**3)
        )
        phase_rows.append(
            "| {thread} | {symbolic} | {numeric} | {total} | {speedup:.4f} | "
            "{persistent:.3f} |".format(
                thread=thread_count,
                symbolic=_format_ms(
                    _require_mapping(
                        item.get("parallel_symbolic_ms"),
                        "parallel_symbolic_ms",
                    ).get("median")
                ),
                numeric=_format_ms(
                    _require_mapping(
                        item.get("parallel_numeric_ms"),
                        "parallel_numeric_ms",
                    ).get("median")
                ),
                total=_format_ms(total.get("median")),
                speedup=_as_float(item.get("overall_speedup"), "speedup"),
                persistent=_as_float(
                    _require_mapping(
                        item.get("estimated_persistent_bytes"),
                        "estimated_persistent_bytes",
                    ).get("median"),
                    "persistent median",
                )
                / (1024.0**3),
            )
        )

    report = f"""# CSC3 对称稀疏组装 Demo Windows 交付测试报告

> 报告 schema：`{REPORT_SCHEMA_VERSION}`。所有性能结论均来自同一份 Windows 原始 CSV、汇总 JSON 与运行 manifest；没有删除、并发执行或挑选样本。

## 结论

本次 Windows x64 交付验证结论为 **PASS**。MSVC 与 MinGW-w64 均完成 Ninja 配置、Release 构建、CTest、独立 consumer 和 clean-room 构建；OpenMP 为强制依赖，任一工具链找不到 OpenMP 都会在 CMake 配置阶段失败。

WindHub 全线程实验覆盖 $p=1,\\ldots,{maximum_threads}$，每个线程数先预热 $W=2$ 次，再正式测量 $R=7$ 次。每个样本使用一个新子进程，全部样本串行执行，正式轮次按升序、降序交替。共执行 {process_integrity.get("observed_sample_count")} 个样本，退出码、样本身份、时间区间和实际 OpenMP team size 检查全部通过。

矩阵最大相对 Frobenius 误差为 $e_F={max_relative_error:.6e}$，满足 $e_F\\le 10^{{-8}}$。实测最优总体加速比出现在 $p={best_thread}$：$S_p={best_speedup:.4f}$，并行符号加数值总时间中位数为 {_as_float(best_parallel.get("median"), "best median"):.3f} ms，对应 Windows 峰值工作集中位数为 {_as_float(best_peak.get("median"), "best peak") / (1024.0**3):.3f} GiB。

需要明确的边界：该 Demo 只实现对称 CSC3 整体刚度矩阵的符号组装与 OpenMP atomic 数值组装，不包含生产级有限元求解器；性能数字只代表本报告所列主机、输入、提交和工具链，不外推到其他硬件。

## Demo 范围与接口位置

### 主要文件

| 内容 | 仓库相对路径 |
|---|---|
| 公共接口与所有权/索引/异常/线程安全注释 | `demos/csc3_symmetric_assembly_demo/include/csc3_demo/assembly_helper.h` |
| 完整并行实现 | `demos/csc3_symmetric_assembly_demo/src/assembly_helper.cpp` |
| WindHub benchmark 与独立串行比较 | `demos/csc3_symmetric_assembly_demo/tools/src/benchmark.cpp` |
| 独立串行参考实现 | `demos/csc3_symmetric_assembly_demo/tools/src/validation.cpp` |
| C++ 正确性与契约测试 | `demos/csc3_symmetric_assembly_demo/tests/` |
| Windows 独立进程实验 runner | `demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py` |

源码目录为 `demos/csc3_symmetric_assembly_demo/`。从仓库根目录进入该目录后再执行 README 中的构建命令。MSVC 和 MinGW 使用不同构建目录。

### 最小调用顺序

```cpp
#include <csc3_demo/assembly_helper.h>

csc3_demo::DofCodingInfo dof_coding_info = /* 单元到节点、节点到自由度 */;
csc3_demo::Csc3Matrix csc3;
csc3_demo::HelpInfo help_info;
csc3_demo::AssemblyHelper helper;

helper.Symbolic(csc3, help_info, dof_coding_info);
helper.zero_values(csc3);

#pragma omp parallel for schedule(static)
for (std::int64_t e = 0; e < element_count; ++e) {{
    helper.add(csc3, help_info, element_stiffness[e]);
}}
```

`Symbolic(...)` 输出 CSC3 结构与 `HelpInfo`。每轮数值组装先清零 `values`，随后由调用方并行遍历单元；`add(...)` 用 atomic 更新共享条目。

## 并行符号组装算法

输入由 `DofCodingInfo::elems` 和 `DofCodingInfo::node_dofs` 给出。程序按单元编号升序整理数据，检查全局自由度连续覆盖 $[0,n)$，并保留单元内节点和自由度顺序。矩阵与辅助表在临时对象中构造，成功后再写回输出参数。

1. 串行两遍计数构造“全局自由度到关联单元”的压缩邻接，并为每列候选行预留容量。
2. 第一个 OpenMP 区域按列静态分工；每个线程独占一列容器，收集满足 $i\\le j$ 的上三角行号，再排序去重。不同线程没有共享写入。
3. 串行前缀和形成 CSC3 `col_ptr`；第二个 OpenMP 区域把已排序行号写入互不重叠的 `row_idx` 列区间。
4. 第三个 OpenMP 区域按单元静态分工，对每个局部上三角条目 $(a,b)$，用列内二分搜索定位唯一 CSC3 目标，写入该单元独占的 `HelpInfo::scatter` 区间。

三个并行区都记录实际线程数。正式样本要求实际线程数与请求值一致。列所有权、排序去重和固定 scatter 区间保证不同线程数下生成相同结构。

## OpenMP atomic 数值组装算法

每轮数值组装先调用 `zero_values(...)`。调用方用 `schedule(static)` 遍历单元，并把单元编号、行主序数据指针和长度包装为 `ElementStiffness` 传给 `add(...)`。目标位置由 `HelpInfo::scatter` 给出：

$$
K_{{s(a,b)}} \\mathrel{{+}}=K_e(a,b),\\qquad 0\\le a\\le b<n_e .
$$

不同单元可能写入同一整体条目，因此累加点使用 `#pragma omp atomic`。由于浮点加法不满足结合律，不同线程数可能出现舍入差异；验收比较 $e_F$ 和最大绝对误差，不要求逐位相同。

报告时间口径为

$$
t_{{\\mathrm{{parallel}}}}=
t_{{\\mathrm{{symbolic}}}}+t_{{\\mathrm{{numeric}}}},
$$

其中数值总时间包含输入校验、整体值清零与 atomic kernel；图表和加速比不混入输入解析或串行参考构造时间。

## 串行参考实现

串行参考实现在 `tools/src/validation.cpp`，不调用 `AssemblyHelper`，也不复用 `HelpInfo::scatter`。它从原始拓扑独立建立列结构并组装数值，再与并行结果比较，避免两条路径共享同一个符号或散射错误。

串行基线也使用每个样本子进程内的独立串行路径，正式加速比固定为：

$$
S_p=
\\frac{{\\operatorname{{median}}_{{r=1,\\ldots,7}}
\\left(t_{{\\mathrm{{serial,symbolic}}}}+
t_{{\\mathrm{{serial,numeric}}}}\\right)_{{p=1,r}}}}
{{\\operatorname{{median}}_{{r=1,\\ldots,7}}
\\left(t_{{\\mathrm{{parallel,symbolic}}}}+
t_{{\\mathrm{{parallel,numeric}}}}\\right)_{{p,r}}}} .
$$

串行基线七个样本的中位数为 {_as_float(serial_statistics.get("median"), "serial median"):.3f} ms，均值为 {_as_float(serial_statistics.get("mean"), "serial mean"):.3f} ms，总体标准差为 {_as_float(serial_statistics.get("population_standard_deviation"), "serial std"):.3f} ms，范围为 [{_as_float(serial_statistics.get("minimum"), "serial min"):.3f}, {_as_float(serial_statistics.get("maximum"), "serial max"):.3f}] ms，变异系数为 {100.0 * _as_float(serial_statistics.get("coefficient_of_variation"), "serial cv"):.2f}%。

## 测试环境

### Windows 主机与输入

| 项目 | 实测值 |
|---|---|
| 操作系统 | {environment.get("caption")} {environment.get("version")}（build {environment.get("build_number")}，{environment.get("architecture")}） |
| CPU | {environment.get("cpu_model")} |
| 物理核 / 逻辑处理器 | {environment.get("physical_core_count")} / {environment.get("logical_processor_count")} |
| 物理内存 | {_as_float(environment.get("total_physical_memory_bytes"), "physical memory") / (1024.0**3):.3f} GiB |
| Python | {environment.get("python_version")} |
| 性能编译器 | {toolchain.get("compiler")} |
| CMake / Ninja | {toolchain.get("cmake")} / {toolchain.get("ninja")} |
| OpenMP 运行时 | {toolchain.get("openmp_runtime")} |
| 分支 / 提交 | `{source.get("branch")}` / `{source.get("commit_sha")}` |
| WindHub 输入 | `{input_facts.get("repository_relative_path")}` |
| 输入大小 / SHA-256 | {input_facts.get("size_bytes")} bytes / `{input_facts.get("sha256")}` |
| Git LFS | 实体已物化且与 HEAD 指针匹配 |
| 问题规模 | {_case_size_text(summary.get("case_sizes"))} |

### 双工具链验证

{_render_build_table(build_evidence)}

### 可复制验证命令

{_render_commands(build_evidence)}

## 矩阵正确性

所有 {process_integrity.get("observed_sample_count")} 个 warmup/measured 子进程都完成以下检查：

- CSC3 `col_ptr`、`row_idx` 与独立串行结构完全一致，列内行号严格递增且满足 $0\\le i\\le j$；
- 所有矩阵值有限，所有 scatter 索引落在 `values` 合法范围；
- 候选 scatter 计划与独立串行定位逐项一致；
- 完整对称矩阵上的最大相对 Frobenius 误差为 $e_F={max_relative_error:.6e}\\le 10^{{-8}}$；
- 全部样本最大绝对误差上界为 $e_{{\\max}}={max_absolute_error:.6e}$。

误差定义为

$$
e_F=\\frac{{\\lVert K_p-K_s\\rVert_F}}
{{\\max(\\lVert K_s\\rVert_F,10^{{-30}})}} ,
$$

其中非对角项在完整对称矩阵的上下三角各计一次。原始逐样本结果保存在 [`benchmark_samples.csv`]({csv_link})，统计汇总保存在 [`benchmark_summary.json`]({summary_link})，进程与工件追溯保存在 [`run_manifest.json`]({manifest_link})。

## 不同线程数下的内存、时间和加速比

![Windows 全线程时间、加速比和峰值工作集]({figure_link})

图像由 Python/matplotlib 从原始 CSV 直接生成，成图尺寸为 183 mm × 125 mm；每个线程数的七个正式样本均以散点显示，并叠加中位数。SVG 保留可编辑文本，PNG 为 300 dpi，TIFF 为 600 dpi；自动质量检查见 [`figure_qa.json`]({figure_qa_link})。

### 并行总时间统计

{chr(10).join(time_rows)}

### 分阶段中位数、加速比与容量估计

{chr(10).join(phase_rows)}

`estimated_persistent_bytes` 只按所拥有向量的 payload capacity 估计持久容量，不是进程常驻集，也不是峰值内存。它与操作系统实测的 `PeakWorkingSetSize` 分栏报告。

### Windows 峰值工作集统计

{chr(10).join(memory_rows)}

峰值内存来自每个存活子进程句柄上的 `GetProcessMemoryInfo().PeakWorkingSetSize`，不是模型估算、任务管理器截图或进程退出后的采样。每个正式样本独占运行时段；manifest 已检查无重叠、无缺失、无重复、全部退出码为零且实际 team size 等于请求值。
"""
    validate_report_headings(report)
    absolute_windows_path = re.search(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]", report)
    if absolute_windows_path:
        raise ReportContractError("报告正文不得包含接收方不可复现的绝对路径")
    return report


def generate_report(options: argparse.Namespace) -> int:
    manifest_path = options.manifest.resolve()
    summary_path = options.summary.resolve()
    samples_csv_path = options.samples_csv.resolve()
    build_evidence_path = options.build_evidence.resolve()
    report_path = options.output_report.resolve()
    figure_dir = options.figure_dir.resolve()
    performance_root = manifest_path.parent
    if summary_path != performance_root / "benchmark_summary.json":
        raise ReportContractError(
            "summary 必须是 manifest 同目录下的 benchmark_summary.json"
        )
    if samples_csv_path != performance_root / "benchmark_samples.csv":
        raise ReportContractError(
            "samples-csv 必须是 manifest 同目录下的 benchmark_samples.csv"
        )
    manifest, summary, rows, build_evidence = load_and_validate_evidence(
        performance_root,
        build_evidence_path,
    )
    figure_outputs = generate_performance_figure(summary, rows, figure_dir)
    report = render_report(
        manifest,
        summary,
        rows,
        build_evidence,
        report_path,
        samples_csv_path,
        summary_path,
        manifest_path,
        figure_outputs,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    result = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "PASS",
        "report": str(report_path),
        "headings": list(EXPECTED_TOP_LEVEL_HEADINGS),
        "figure_outputs": {
            key: str(value)
            for key, value in figure_outputs.items()
            if key.endswith("_path")
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def load_and_validate_evidence(
    performance_root: Path,
    build_evidence_path: Path,
) -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, str]],
    dict[str, object],
]:
    """读取并交叉校验报告和交付打包共同使用的正式证据。"""

    performance_root = performance_root.resolve()
    build_evidence_path = build_evidence_path.resolve()
    manifest = _read_json(performance_root / "run_manifest.json")
    summary = _read_json(performance_root / "benchmark_summary.json")
    rows = _read_csv(performance_root / "benchmark_samples.csv")
    build_evidence = _read_json(build_evidence_path)
    validate_evidence(
        manifest,
        summary,
        rows,
        build_evidence,
        performance_root=performance_root,
        build_root=build_evidence_path.parent,
    )
    return manifest, summary, rows, build_evidence


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--samples-csv", type=Path, required=True)
    parser.add_argument("--build-evidence", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--figure-dir", type=Path, required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        options = build_argument_parser().parse_args(arguments)
        return generate_report(options)
    except (ReportContractError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
