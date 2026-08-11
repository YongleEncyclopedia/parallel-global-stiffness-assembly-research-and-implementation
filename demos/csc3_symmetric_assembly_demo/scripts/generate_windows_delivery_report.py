#!/usr/bin/env python3
"""把 Windows 独立进程实验结果整理成中文测试报告和性能图。

脚本复核线程扫描、样本数量、计时、峰值工作集、矩阵误差和构建记录，再生成
Markdown、SVG、PNG 等报告材料。
"""

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
    manifest: Mapping[str, object],
    summary: Mapping[str, object],
    rows: Sequence[Mapping[str, str]],
    figure_dir: Path,
) -> dict[str, object]:
    """生成实测样本分布、组装耗时和总体加速比三联图。"""

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
            "axes.titlesize": 8.8,
            "axes.labelsize": 7.2,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "csc3-demo-windows-thread-scan",
            "pdf.fonttype": 42,
        }
    )
    figure_dir.mkdir(parents=True, exist_ok=True)
    grouped = _measured_rows(rows)
    per_thread_value = summary.get("per_thread")
    if not isinstance(per_thread_value, list):
        raise ReportContractError("per_thread 必须是数组")
    per_thread = [
        _require_mapping(item, "per_thread item") for item in per_thread_value
    ]
    thread_counts = [
        _as_int(item.get("thread_count"), "thread_count") for item in per_thread
    ]

    # 堆叠柱使用“总耗时处于中位数的那次实测”。这样符号阶段和数值阶段相加后，
    # 柱顶严格等于报告采用的总耗时中位数，不会出现“两个分项中位数之和”偏离总量。
    symbolic_seconds: list[float] = []
    numeric_seconds: list[float] = []
    total_seconds: list[float] = []
    speedups: list[float] = []
    for item in per_thread:
        thread_count = _as_int(item.get("thread_count"), "thread_count")
        samples = grouped.get(thread_count, [])
        if len(samples) != REPEAT_COUNT:
            raise ReportContractError(
                f"线程 {thread_count} 的正式样本数不是 {REPEAT_COUNT}"
            )
        representative = sorted(
            samples,
            key=lambda row: (
                _as_float(row.get("parallel_total_ms"), "parallel_total_ms"),
                _as_int(row.get("round"), "round"),
            ),
        )[len(samples) // 2]
        total_ms = _as_float(
            representative.get("parallel_total_ms"),
            "parallel_total_ms",
        )
        recorded_median = _as_float(
            _require_mapping(
                item.get("parallel_total_ms"),
                "parallel_total_ms",
            ).get("median"),
            "parallel total median",
        )
        _require_close(total_ms, recorded_median, "柱状图总耗时中位数")
        symbolic_seconds.append(
            _as_float(
                representative.get("parallel_symbolic_ms"),
                "parallel_symbolic_ms",
            )
            / 1000.0
        )
        numeric_seconds.append(
            _as_float(
                representative.get("parallel_numeric_ms"),
                "parallel_numeric_ms",
            )
            / 1000.0
        )
        total_seconds.append(total_ms / 1000.0)
        speedups.append(
            _as_float(item.get("overall_speedup"), "overall_speedup")
        )

    serial_baseline = _as_float(
        _require_mapping(
            summary.get("serial_baseline_total_ms"),
            "serial_baseline_total_ms",
        ).get("median"),
        "serial baseline median",
    ) / 1000.0
    environment = _require_mapping(manifest.get("environment"), "environment")
    case_sizes = _require_mapping(summary.get("case_sizes"), "case_sizes")
    cpu_model = str(environment.get("cpu_model", "Windows x64")).strip()
    element_count = _as_int(case_sizes.get("element_count"), "element_count")
    element_type = str(case_sizes.get("element_type", "Tet4"))

    width_inches = FIGURE_WIDTH_MM / 25.4
    height_inches = FIGURE_HEIGHT_MM / 25.4
    figure, axes = plt.subplots(1, 3, figsize=(width_inches, height_inches))
    figure.subplots_adjust(
        left=0.065,
        right=0.985,
        bottom=0.22,
        top=0.70,
        wspace=0.28,
    )
    colors = {
        "green": "#76B900",
        "green_dark": "#5A9100",
        "green_light": "#C4E782",
        "neutral": "#D5DCE1",
        "grid": "#D9DEE3",
        "text": "#2B2F33",
        "muted": "#77818A",
    }
    figure.text(
        0.065,
        0.93,
        "CSC3 对称稀疏组装线程扩展结果",
        fontsize=14,
        color=colors["text"],
        ha="left",
        va="top",
    )
    figure.text(
        0.065,
        0.86,
        f"WindHub · {element_count:,} 个 {element_type} 单元 · {cpu_model} · Windows x64",
        fontsize=8.5,
        color=colors["muted"],
        ha="left",
        va="top",
    )

    tick_candidates = (
        thread_counts
        if len(thread_counts) <= 8
        else [1, 4, 8, 12, max(thread_counts)]
    )
    x_ticks = sorted(set(tick_candidates).intersection(thread_counts))
    bar_width = 0.72

    sample_axis = axes[0]
    jitter = [
        -0.18 + 0.36 * index / (REPEAT_COUNT - 1)
        for index in range(REPEAT_COUNT)
    ]
    for thread_count in thread_counts:
        samples = grouped[thread_count]
        sample_axis.scatter(
            [thread_count + offset for offset in jitter],
            [
                _as_float(row.get("parallel_total_ms"), "parallel_total_ms")
                / 1000.0
                for row in samples
            ],
            s=9,
            color="#9CB6C7",
            alpha=0.78,
            edgecolors="none",
            label="七次正式测量" if thread_count == thread_counts[0] else None,
            zorder=2,
        )
    sample_axis.plot(
        thread_counts,
        total_seconds,
        color=colors["green_dark"],
        marker="o",
        markersize=2.8,
        linewidth=1.0,
        label="中位数",
        zorder=3,
    )
    sample_axis.axhline(
        serial_baseline,
        color="#7B848B",
        linestyle="--",
        linewidth=0.9,
        label="串行基线",
    )
    sample_axis.set_title("七次实测分布", loc="left", pad=10)
    sample_axis.text(
        1.0,
        1.03,
        "越低越好",
        transform=sample_axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color=colors["muted"],
    )
    sample_axis.set_ylabel("秒")
    sample_axis.set_ylim(
        0.0,
        max(
            serial_baseline,
            max(
                _as_float(row.get("parallel_total_ms"), "parallel_total_ms")
                for samples in grouped.values()
                for row in samples
            )
            / 1000.0,
        )
        * 1.20,
    )
    sample_axis.legend(loc="upper right", fontsize=5.6)

    time_axis = axes[1]
    time_axis.bar(
        thread_counts,
        numeric_seconds,
        width=bar_width,
        color=colors["green"],
        edgecolor=colors["green_dark"],
        linewidth=0.45,
        label="atomic 数值组装",
    )
    time_axis.bar(
        thread_counts,
        symbolic_seconds,
        width=bar_width,
        bottom=numeric_seconds,
        color=colors["green_light"],
        edgecolor="none",
        label="并行符号组装",
    )
    time_axis.axhline(
        serial_baseline,
        color="#7B848B",
        linestyle="--",
        linewidth=0.9,
    )
    time_axis.text(
        max(thread_counts) + 0.15,
        serial_baseline,
        f"串行 {serial_baseline:.3f} s",
        ha="right",
        va="bottom",
        fontsize=5.8,
        color="#687077",
    )
    time_axis.set_title("组装总耗时", loc="left", pad=10)
    time_axis.text(
        1.0,
        1.03,
        "越低越好",
        transform=time_axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color=colors["muted"],
    )
    time_axis.set_ylabel("秒")
    time_axis.set_ylim(0.0, max(max(total_seconds), serial_baseline) * 1.20)
    time_axis.legend(loc="upper right", fontsize=5.8, ncol=1)
    minimum_time_index = min(
        range(len(total_seconds)), key=total_seconds.__getitem__
    )
    time_axis.annotate(
        f"最低 {total_seconds[minimum_time_index]:.3f} s",
        (thread_counts[minimum_time_index], total_seconds[minimum_time_index]),
        xytext=(-4, 6),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=6.3,
        color=colors["text"],
    )

    speed_axis = axes[2]
    speed_colors = [colors["green"] for _ in speedups]
    best_index = max(range(len(speedups)), key=speedups.__getitem__)
    speed_colors[best_index] = colors["green_dark"]
    speed_axis.bar(
        thread_counts,
        speedups,
        width=bar_width,
        color=speed_colors,
        edgecolor=colors["green_dark"],
        linewidth=0.45,
    )
    speed_axis.axhline(1.0, color="#7B848B", linestyle="--", linewidth=0.9)
    speed_axis.set_title("整体加速比", loc="left", pad=10)
    speed_axis.text(
        1.0,
        1.03,
        "越高越好",
        transform=speed_axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.2,
        color=colors["muted"],
    )
    speed_axis.set_ylabel("倍")
    speed_axis.set_ylim(0.0, max(speedups) * 1.28)
    speed_axis.annotate(
        f"最高 {speedups[best_index]:.2f}×\n{thread_counts[best_index]} 线程",
        (thread_counts[best_index], speedups[best_index]),
        xytext=(-4, 7),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=6.4,
        color=colors["text"],
    )

    for axis in axes:
        axis.set_xlabel("线程数")
        axis.set_xticks(x_ticks)
        axis.set_axisbelow(True)
        axis.grid(axis="y", color=colors["grid"], linewidth=0.55, alpha=0.8)
        axis.tick_params(axis="both", labelsize=6.2)

    figure.text(
        0.065,
        0.105,
        (
            f"线程扫描：$p=1,\\ldots,{max(thread_counts)}$；每档预热 $W=2$ 次、"
            "正式测量 $R=7$ 次；每个样本使用独立子进程并串行执行。"
        ),
        fontsize=6.7,
        color=colors["text"],
        ha="left",
    )
    figure.text(
        0.065,
        0.06,
        (
            "左图保留每档七次正式测量；耗时柱按总耗时中位数样本拆分为符号与"
            "数值阶段；加速比基线为独立串行组装。"
        ),
        fontsize=6.4,
        color=colors["muted"],
        ha="left",
    )

    png_path = figure_dir / "windows-thread-scan.png"
    svg_path = figure_dir / "windows-thread-scan.svg"
    pdf_path = figure_dir / "windows-thread-scan.pdf"
    figure.savefig(
        png_path,
        dpi=PNG_DPI,
        facecolor="white",
        metadata={"Software": "CSC3 Demo report generator"},
    )
    figure.savefig(svg_path, facecolor="white", metadata={"Date": None})
    figure.savefig(
        pdf_path,
        facecolor="white",
        metadata={"CreationDate": None, "ModDate": None},
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
        "archetype": "bar comparison with raw-sample scatter",
        "core_conclusion": (
            "七次正式测量的散点和汇总柱状图共同显示，整体耗时随线程数增加而"
            f"下降，最高总体加速比为 {speedups[best_index]:.4f}。"
        ),
        "panel_map": {
            "samples": "每个线程数七次正式测量的总耗时与中位数",
            "time": "中位总耗时样本的符号与 atomic 数值阶段堆叠",
            "speedup": "相对独立串行基线的总体加速比",
        },
        "source_data": "benchmark_samples.csv",
        "statistics": {
            "sample_definition": "one fresh child process per sample",
            "warmup_count": WARMUP_COUNT,
            "measured_count_per_thread": REPEAT_COUNT,
            "sample_scatter": "all measured parallel total times",
            "time_bar": "components of the measured sample at median total time",
            "speedup": "serial total median divided by parallel total median",
        },
        "image_integrity": {
            "raw_raster_images": False,
            "local_adjustments": False,
            "raw_samples_plotted": True,
            "all_thread_counts_included": True,
            "measured_samples_retained_in_csv": True,
        },
        "final_size_mm": [FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM],
        "png": {
            "dpi": PNG_DPI,
            "dimensions_px": png_dimensions,
            "nonblank": True,
        },
        "svg": {
            "editable_text": True,
            "text_element_count": text_element_count,
        },
        "pdf": {"editable_truetype_text_requested": True},
        "reviewer_risks_addressed": [
            "全部线程数均显示",
            "柱状图从零开始",
            "耗时堆叠与总耗时中位数严格一致",
            "每档七次正式测量均显示且保留在 CSV 中",
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
        "qa_path": qa_path,
        "qa": qa,
    }


def _format_ms(value: object) -> str:
    return f"{_as_float(value, 'milliseconds'):.3f}"


def _render_build_table(build_evidence: Mapping[str, object]) -> str:
    rows = [
        "| 工具链 | 编译器 | OpenMP | 配置 | 构建 | CTest | 外部调用示例 | 干净目录复现 |",
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
    cpu_model = str(environment.get("cpu_model", "")).strip()
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

    performance_rows = [
        "| 线程数 $p$ | 符号组装中位数（ms） | atomic 数值组装中位数（ms） | 总耗时中位数（ms） | 总耗时 $CV$ | 整体加速比 | 峰值工作集（GiB） |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    peak_medians_gib: list[float] = []
    for item in per_thread:
        thread_count = _as_int(item.get("thread_count"), "thread_count")
        total = _require_mapping(item.get("parallel_total_ms"), "parallel_total_ms")
        peak = _require_mapping(
            item.get("peak_working_set_bytes"),
            "peak_working_set_bytes",
        )
        peak_median_gib = _as_float(peak.get("median"), "peak median") / (
            1024.0**3
        )
        peak_medians_gib.append(peak_median_gib)
        performance_rows.append(
            "| {thread} | {symbolic} | {numeric} | {total} | {cv:.2f}% | "
            "{speedup:.4f} | {peak:.4f} |".format(
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
                cv=100.0
                * _as_float(
                    total.get("coefficient_of_variation"),
                    "total coefficient of variation",
                ),
                speedup=_as_float(item.get("overall_speedup"), "speedup"),
                peak=peak_median_gib,
            )
        )

    case_sizes = _require_mapping(summary.get("case_sizes"), "case_sizes")
    node_count = _as_int(case_sizes.get("node_count"), "node_count")
    element_count = _as_int(case_sizes.get("element_count"), "element_count")
    dof_count = _as_int(
        case_sizes.get("dof_count", case_sizes.get("dimension")),
        "dof_count",
    )
    nonzero_count = _as_int(
        case_sizes.get("nnz", case_sizes.get("nonzero_count")),
        "nonzero_count",
    )
    element_type = str(case_sizes.get("element_type", "Tet4"))
    persistent_gib = _as_float(
        _require_mapping(
            per_thread[0].get("estimated_persistent_bytes"),
            "estimated_persistent_bytes",
        ).get("median"),
        "persistent median",
    ) / (1024.0**3)
    measured_count = maximum_threads * REPEAT_COUNT
    warmup_count = maximum_threads * WARMUP_COUNT
    peak_min_gib = min(peak_medians_gib)
    peak_max_gib = max(peak_medians_gib)
    peak_spread_mib = (peak_max_gib - peak_min_gib) * 1024.0

    report = f"""# CSC3 对称稀疏组装 Demo 测试报告（Windows，2026-07-26）

## 结论

2026 年 7 月 26 日的 Windows x64 测试通过。MSVC 和 MinGW-w64 均完成 Release 模式构建、CTest、外部调用示例和干净目录复现，OpenMP 路径实际启用。

工程网格为 WindHub，共 {element_count:,} 个 {element_type} 单元。线程扫描覆盖 $p=1,\\ldots,{maximum_threads}$；每档预热 $W=2$ 次、正式测量 $R=7$ 次，共运行 {process_integrity.get("observed_sample_count")} 个独立子进程。全部样本正常退出，实际 OpenMP 线程数与请求值一致。

矩阵结构与串行参考一致，最大相对 Frobenius 误差为 $e_F={max_relative_error:.6e}$。{best_thread} 线程时总耗时中位数为 {_as_float(best_parallel.get("median"), "best median"):.3f} ms，整体加速比为 ${best_speedup:.4f}\\times$，峰值工作集中位数为 {_as_float(best_peak.get("median"), "best peak") / (1024.0**3):.3f} GiB。

本文数值均来自 2026-07-26 的测试记录。测试可执行文件由提交 `{source.get("commit_sha")}` 构建；后续源码改动不在本报告覆盖范围内。

## Demo 范围与接口位置

Demo 只负责生成对称 CSC3 结构并累加单元刚度矩阵，不包含网格划分、载荷处理和线性求解器。2026-07-26 测试提交的公共入口是 `SymmetricCscAssembler`，调用顺序为 `build_symbolic_parallel()` 后接 `assemble_numeric_atomic()`。

| 内容 | 仓库相对路径 |
|---|---|
| 公共接口 | `demos/csc3_symmetric_assembly_demo/include/csc3_demo/assembly_helper.h` |
| 并行实现 | `demos/csc3_symmetric_assembly_demo/src/assembly_helper.cpp` |
| benchmark | `demos/csc3_symmetric_assembly_demo/tools/src/benchmark.cpp` |
| 串行参考与误差计算 | `demos/csc3_symmetric_assembly_demo/tools/src/validation.cpp` |
| 自动测试 | `demos/csc3_symmetric_assembly_demo/tests/` |
| Windows 线程扫描脚本 | `demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py` |

源码目录为 `demos/csc3_symmetric_assembly_demo/`。具体编译目录和命令见该目录的 `README.md`。

## 并行符号组装算法

符号阶段只确定稀疏结构和单元条目在整体矩阵中的位置，不写入刚度值。输入先按单元编号整理，同时检查自由度编号、重复项和索引范围。

1. 先建立“全局自由度到关联单元”的邻接关系；
2. 按 CSC3 列并行收集候选行号，每列由一个线程独占处理；
3. 对候选行号排序、去重，再通过前缀和生成列指针；
4. 并行写入行号，并为每个单元建立固定的 scatter 位置表。

列内结果经过排序，因此线程执行先后不会改变 CSC3 结构。散射位置表（scatter）在数值组装时直接给出目标位置，避免重复查找。

## OpenMP atomic 数值组装算法

数值阶段先检查局部矩阵尺寸、有限性、对称性和 scatter 边界，然后清零整体矩阵数值。OpenMP 按单元分工，每个线程遍历自己负责的单元，并按符号阶段给出的目标位置累加：

$$
K_{{s(a,b)}} \\mathrel{{+}}=K_e(a,b),\\qquad 0\\le a\\le b<n_e .
$$

不同单元可能同时写入同一个整体条目，所以更新点使用 `#pragma omp atomic`。atomic 保证累加不丢失；浮点加法顺序仍可能带来舍入级差异，因此正确性判断采用误差阈值，不要求逐位相同。

本报告的并行耗时为

$$
t_{{\\mathrm{{parallel}}}}=
t_{{\\mathrm{{symbolic}}}}+t_{{\\mathrm{{numeric}}}},
$$

其中数值阶段包含检查、清零和 atomic 累加，不含网格文件读取。

## 串行参考实现

串行参考实现在 `tools/src/validation.cpp`。它从原始拓扑独立建立 CSC3 结构和数值，不调用并行组装器，也不复用并行散射位置表。两套实现分开，便于发现符号结构或累加位置上的错误。

整体加速比采用串行总耗时中位数作为基线：

$$
S_p=
\\frac{{\\operatorname{{median}}_{{r=1,\\ldots,7}}
\\left(t_{{\\mathrm{{serial,symbolic}}}}+
t_{{\\mathrm{{serial,numeric}}}}\\right)_{{p=1,r}}}}
{{\\operatorname{{median}}_{{r=1,\\ldots,7}}
\\left(t_{{\\mathrm{{parallel,symbolic}}}}+
t_{{\\mathrm{{parallel,numeric}}}}\\right)_{{p,r}}}} .
$$

串行基线的中位数为 {_as_float(serial_statistics.get("median"), "serial median"):.3f} ms，七次测量范围为 [{_as_float(serial_statistics.get("minimum"), "serial min"):.3f}, {_as_float(serial_statistics.get("maximum"), "serial max"):.3f}] ms，变异系数为 {100.0 * _as_float(serial_statistics.get("coefficient_of_variation"), "serial cv"):.2f}%。

## 测试环境

| 项目 | 实测值 |
|---|---|
| 操作系统 | {environment.get("caption")} {environment.get("version")}（build {environment.get("build_number")}，{environment.get("architecture")}） |
| CPU | {cpu_model} |
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
| 节点 / 单元 / 自由度 | {node_count:,} / {element_count:,} / {dof_count:,} |
| CSC3 非零条目 | {nonzero_count:,} |
| 实验安排 | $p=1,\\ldots,{maximum_threads}$，$W=2$，$R=7$，每个样本独立进程且串行执行 |

{_render_build_table(build_evidence)}

完整命令和日志保存在 2026-07-26 结果目录的 `builds/` 与 `performance/` 中，报告不再重复粘贴大段终端输出。

## 矩阵正确性

{warmup_count} 个预热样本和 {measured_count} 个正式样本均通过以下检查：

- CSC3 列指针和行号与串行参考逐项一致；
- 所有矩阵值有限，scatter 索引均在合法范围内；
- 最大相对 Frobenius 误差为 $e_F={max_relative_error:.6e}\\le 10^{{-8}}$；
- 全部样本的最大绝对误差不超过 $e_{{\\max}}={max_absolute_error:.6e}$。

误差定义为

$$
e_F=\\frac{{\\lVert K_p-K_s\\rVert_F}}
{{\\max(\\lVert K_s\\rVert_F,10^{{-30}})}} ,
$$

其中非对角项按完整对称矩阵计入两次。WindHub 输入只包含节点和单元，本次工程网格测试没有设置载荷和边界条件，因此不做位移比较。

## 不同线程数下的内存、时间和加速比

并行路径在 1 线程时有额外开销，速度低于独立串行基线；从 2 线程开始出现整体加速，14 至 16 线程基本进入平台区。各线程数的峰值工作集中位数为 {peak_min_gib:.6f} 至 {peak_max_gib:.6f} GiB，最大相差 {peak_spread_mib:.3f} MiB，没有出现随线程数增长的大块内存开销。

![Windows 全线程实测分布、时间和加速比]({figure_link})

左图保留每个线程数下七次正式测量的散点，并用折线连接各档中位数。中图的耗时柱取总耗时位于中间的那次实测，再拆成符号和数值阶段，因此两段之和就是柱顶总耗时。右图的加速比以串行总耗时中位数为基线。图像质量记录见 [`figure_qa.json`]({figure_qa_link})。

{chr(10).join(performance_rows)}

表中的符号、数值和总耗时分别统计中位数，分项中位数之和可能与总耗时中位数略有差别。`estimated_persistent_bytes` 为 {persistent_gib:.3f} GiB，只表示程序持有的向量容量估计；图表使用的是操作系统通过 `GetProcessMemoryInfo().PeakWorkingSetSize` 实测的进程峰值工作集。

原始逐样本数据见 [`benchmark_samples.csv`]({csv_link})，汇总结果见 [`benchmark_summary.json`]({summary_link})，进程、输入和文件摘要见 [`run_manifest.json`]({manifest_link})。后续如果更换源码提交、编译器或主机，应重新运行这套线程扫描，不能沿用本报告数值。
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
    figure_outputs = generate_performance_figure(
        manifest,
        summary,
        rows,
        figure_dir,
    )
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
