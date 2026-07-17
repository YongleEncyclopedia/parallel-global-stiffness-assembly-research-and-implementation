#!/usr/bin/env python3
"""从已归档 local-smoke 证据生成图表、交接报告和确定性外层 ZIP。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import stat
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from statistics import median
from typing import Iterable


WARNING = "NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE"
DEMO_VERSION = "0.2.0"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_FILE_MODE = stat.S_IFREG | 0o644
SHA40 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
REPORT_NAME = "2026-07-17-csc3-demo-macos-local-smoke-test-report.zh-CN.md"
FIGURE_STEM = "csc3-demo-local-smoke-performance-comparison"


class HandoffError(RuntimeError):
    """交接输入不完整、不一致或不能安全生成时抛出。"""


@dataclass(frozen=True)
class CandidateMetrics:
    """一个 OpenMP 线程配置的阶段中位数与相对串行加速比。"""

    thread_count: int
    symbolic_ms: float
    numeric_ms: float
    symbolic_speedup: float
    numeric_speedup: float


@dataclass(frozen=True)
class PerformanceData:
    """绘图和报告共用的、从原始样本重新计算后的只读数据。"""

    evidence_status: str
    evidence_level: str
    evidence_commit: str
    case_name: str
    element_type: str
    cpu_model: str
    architecture: str
    thread_counts: tuple[int, ...]
    warmup_count: int
    repeat_count: int
    amortization_count: int
    serial_symbolic_ms: float
    serial_numeric_ms: float
    candidates: tuple[CandidateMetrics, ...]
    source_hashes: tuple[tuple[str, str], ...]


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"禁止非有限 JSON 常量：{value}")


def _reject_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"禁止重复 JSON key：{key!r}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
            object_pairs_hook=_reject_duplicate_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise HandoffError(f"无法读取严格 JSON：{path}: {error}") from error
    if not isinstance(value, dict):
        raise HandoffError(f"JSON 根节点必须是 object：{path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise HandoffError(f"{label} 必须是 object")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise HandoffError(f"{label} 必须是 array")
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HandoffError(f"{label} 必须是 integer")
    return value


def _require_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HandoffError(f"{label} 必须是 number")
    result = float(value)
    if not math.isfinite(result):
        raise HandoffError(f"{label} 必须是有限数")
    return result


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffError(f"{label} 必须是非空字符串")
    return value


def _expect_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise HandoffError(f"{label} 不匹配：期望 {expected!r}，实际 {actual!r}")


def _expect_close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-15):
        raise HandoffError(
            f"{label} 与原始样本重算值不一致：期望 {expected:.17g}，"
            f"实际 {actual:.17g}"
        )


def _require_commit_sha(value: object, label: str) -> str:
    result = _require_text(value, label)
    if SHA40.fullmatch(result) is None:
        raise HandoffError(f"{label} 必须是 40 位小写 SHA")
    return result


def _float_field(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise HandoffError(f"CSV 字段 {field!r} 无效") from error
    if not math.isfinite(value):
        raise HandoffError(f"CSV 字段 {field!r} 必须是有限数")
    return value


def _int_field(row: dict[str, str], field: str) -> int:
    try:
        text = row[field]
        if not re.fullmatch(r"0|[1-9][0-9]*", text):
            raise ValueError(text)
        return int(text)
    except (KeyError, ValueError) as error:
        raise HandoffError(f"CSV 字段 {field!r} 必须是非负整数") from error


def _artifact_records(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for index, raw_record in enumerate(
        _require_list(manifest.get("artifacts"), "manifest.artifacts")
    ):
        record = _require_mapping(raw_record, f"manifest.artifacts[{index}]")
        path = _require_text(record.get("path"), f"manifest.artifacts[{index}].path")
        if path in records:
            raise HandoffError(f"manifest.artifacts 含重复路径：{path}")
        records[path] = record
    return records


def _verify_bound_artifact(
    evidence_dir: Path,
    records: dict[str, dict[str, object]],
    name: str,
) -> str:
    record = records.get(name)
    if record is None:
        raise HandoffError(f"manifest 未绑定必需 artifact：{name}")
    path = evidence_dir / name
    if not path.is_file() or path.is_symlink():
        raise HandoffError(f"artifact 必须是普通文件：{path}")
    expected_size = _require_int(record.get("size_bytes"), f"artifact {name}.size_bytes")
    expected_sha = _require_text(record.get("sha256"), f"artifact {name}.sha256")
    if SHA256.fullmatch(expected_sha) is None:
        raise HandoffError(f"artifact {name}.sha256 格式无效")
    if path.stat().st_size != expected_size:
        raise HandoffError(f"artifact {name} 字节数与 manifest 不一致")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha:
        raise HandoffError(f"artifact {name} SHA-256 与 manifest 不一致")
    return actual_sha


def load_performance_data(evidence_dir: Path) -> PerformanceData:
    """验证 local-smoke 证据并从 CSV measured 样本重新计算绘图指标。"""

    evidence_dir = evidence_dir.resolve()
    manifest_path = evidence_dir / "run_manifest.json"
    summary_path = evidence_dir / "benchmark_summary.json"
    samples_path = evidence_dir / "benchmark_samples.csv"
    manifest = _read_json(manifest_path)
    summary = _read_json(summary_path)

    _expect_equal(manifest.get("status"), "LOCAL_SMOKE", "manifest.status")
    _expect_equal(manifest.get("evidence_level"), "local-smoke", "manifest.evidence_level")
    _expect_equal(manifest.get("report_intent"), "local-smoke", "manifest.report_intent")
    _expect_equal(
        summary.get("schema_version"),
        "csc3-demo-benchmark-v1",
        "summary.schema_version",
    )

    records = _artifact_records(manifest)
    if "run_manifest.json" in records:
        raise HandoffError("run_manifest.json 不得自我哈希绑定")
    summary_sha = _verify_bound_artifact(evidence_dir, records, "benchmark_summary.json")
    samples_sha = _verify_bound_artifact(evidence_dir, records, "benchmark_samples.csv")

    configuration = _require_mapping(summary.get("configuration"), "summary.configuration")
    benchmark = _require_mapping(manifest.get("benchmark"), "manifest.benchmark")
    environment = _require_mapping(manifest.get("environment"), "manifest.environment")
    source = _require_mapping(manifest.get("source"), "manifest.source")
    case_sizes = _require_mapping(summary.get("case_sizes"), "summary.case_sizes")
    correctness = _require_mapping(summary.get("correctness"), "summary.correctness")

    evidence_commit = _require_commit_sha(source.get("commit_sha"), "source.commit_sha")
    _expect_equal(source.get("demo_version"), DEMO_VERSION, "source.demo_version")
    _expect_equal(source.get("source_dirty_at_start"), False, "source.source_dirty_at_start")
    _require_text(source.get("branch"), "source.branch")
    _expect_equal(
        summary.get("performance_evidence_level"),
        "local-smoke",
        "summary.performance_evidence_level",
    )
    _expect_equal(
        summary.get("performance_gate_status"),
        "NOT_APPLICABLE_GENERATED_CASE",
        "summary.performance_gate_status",
    )
    _expect_equal(correctness.get("status"), "PASS", "summary.correctness.status")
    _expect_equal(
        correctness.get("structure_matches"),
        True,
        "summary.correctness.structure_matches",
    )

    _expect_equal(configuration.get("case"), "generated-tet4", "configuration.case")
    _expect_equal(
        configuration.get("performance_evidence_level"),
        "local-smoke",
        "configuration.performance_evidence_level",
    )
    thread_counts = tuple(
        _require_int(value, "configuration.thread_counts[]")
        for value in _require_list(
            configuration.get("thread_counts"), "configuration.thread_counts"
        )
    )
    _expect_equal(thread_counts, (1, 2), "configuration.thread_counts")
    _expect_equal(
        benchmark.get("requested_thread_counts"),
        list(thread_counts),
        "manifest.benchmark.requested_thread_counts",
    )
    _expect_equal(
        benchmark.get("observed_thread_counts"),
        list(thread_counts),
        "manifest.benchmark.observed_thread_counts",
    )

    warmup_count = _require_int(configuration.get("warmup_count"), "warmup_count")
    repeat_count = _require_int(configuration.get("repeat_count"), "repeat_count")
    amortization_count = _require_int(
        configuration.get("amortization_count"), "amortization_count"
    )
    _expect_equal((warmup_count, repeat_count, amortization_count), (1, 2, 2), "W/R/m")
    _expect_equal(benchmark.get("warmup_count"), warmup_count, "manifest warmup_count")
    _expect_equal(benchmark.get("repeat_count"), repeat_count, "manifest repeat_count")
    _expect_equal(
        benchmark.get("amortization_count"),
        amortization_count,
        "manifest amortization_count",
    )

    case_name = _require_text(case_sizes.get("case_name"), "case_sizes.case_name")
    element_type = _require_text(case_sizes.get("element_type"), "case_sizes.element_type")
    grid_dimensions = tuple(
        _require_int(configuration.get(axis), f"configuration.{axis}")
        for axis in ("nx", "ny", "nz")
    )
    _expect_equal(grid_dimensions, (1, 1, 1), "configuration nx/ny/nz")
    size_fields = {
        name: _require_int(case_sizes.get(name), f"case_sizes.{name}")
        for name in ("node_count", "element_count", "dof_count", "nnz")
    }
    estimated_persistent_bytes = _require_int(
        summary.get("estimated_persistent_bytes"), "estimated_persistent_bytes"
    )
    relative_frobenius_error = _require_number(
        correctness.get("relative_frobenius_error"),
        "correctness.relative_frobenius_error",
    )
    max_absolute_error = _require_number(
        correctness.get("max_absolute_error"), "correctness.max_absolute_error"
    )
    validation_cases = _require_list(summary.get("validation_cases"), "validation_cases")
    if len(validation_cases) != 2:
        raise HandoffError("validation_cases 必须包含 Tet4 和 Hex8 两个算例")
    validation_types: set[str] = set()
    for index, raw_case in enumerate(validation_cases):
        validation = _require_mapping(raw_case, f"validation_cases[{index}]")
        _expect_equal(validation.get("status"), "PASS", f"validation_cases[{index}].status")
        validation_type = _require_text(
            validation.get("element_type"), f"validation_cases[{index}].element_type"
        )
        if validation_type in validation_types:
            raise HandoffError(f"validation_cases 含重复类型：{validation_type}")
        validation_types.add(validation_type)
    _expect_equal(validation_types, {"Tet4", "Hex8"}, "validation element types")

    try:
        with samples_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise HandoffError(f"无法读取 benchmark CSV：{error}") from error
    if not rows or reader.fieldnames is None:
        raise HandoffError("benchmark CSV 为空")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise HandoffError("benchmark CSV 表头包含重复字段")

    expected_sample_keys = {
        (thread, "warmup", sample_index)
        for thread in thread_counts
        for sample_index in range(warmup_count)
    } | {
        (thread, "measured", sample_index)
        for thread in thread_counts
        for sample_index in range(1, repeat_count + 1)
    }
    observed_sample_keys: set[tuple[int, str, int]] = set()
    requested_threads = set(thread_counts)
    expected_measured_count = repeat_count * len(thread_counts)
    for row in rows:
        if None in row:
            raise HandoffError("benchmark CSV 行包含多余列")
        _expect_equal(row.get("schema_version"), "csc3-demo-benchmark-v1", "CSV schema")
        _expect_equal(row.get("performance_evidence_level"), "local-smoke", "CSV level")
        _expect_equal(row.get("case_name"), case_name, "CSV case_name")
        _expect_equal(row.get("element_type"), element_type, "CSV element_type")
        for axis, expected in zip(("nx", "ny", "nz"), grid_dimensions):
            _expect_equal(_int_field(row, axis), expected, f"CSV {axis}")
        for name, expected in size_fields.items():
            _expect_equal(_int_field(row, name), expected, f"CSV {name}")
        _expect_equal(
            _int_field(row, "estimated_persistent_bytes"),
            estimated_persistent_bytes,
            "CSV estimated_persistent_bytes",
        )
        _expect_equal(row.get("matrix_correctness_status"), "PASS", "CSV correctness")
        _expect_close(
            _float_field(row, "relative_frobenius_error"),
            relative_frobenius_error,
            "CSV relative_frobenius_error",
        )
        _expect_close(
            _float_field(row, "max_absolute_error"),
            max_absolute_error,
            "CSV max_absolute_error",
        )
        thread = _int_field(row, "thread_count")
        if thread not in requested_threads:
            raise HandoffError(f"CSV 出现未请求线程数：{thread}")
        sample_kind = row.get("sample_kind")
        if sample_kind not in {"warmup", "measured"}:
            raise HandoffError(f"CSV sample_kind 无效：{sample_kind!r}")
        sample_index = _int_field(row, "sample_index")
        sample_key = (thread, sample_kind, sample_index)
        if sample_key in observed_sample_keys:
            raise HandoffError(f"CSV 含重复样本索引：{sample_key}")
        observed_sample_keys.add(sample_key)
    if observed_sample_keys != expected_sample_keys:
        missing = sorted(expected_sample_keys - observed_sample_keys)
        unexpected = sorted(observed_sample_keys - expected_sample_keys)
        raise HandoffError(
            f"CSV 样本索引集合不完整：missing={missing}, unexpected={unexpected}"
        )

    measured = [row for row in rows if row.get("sample_kind") == "measured"]
    if len(measured) != expected_measured_count:
        raise HandoffError(
            f"measured 样本数错误：期望 {expected_measured_count}，实际 {len(measured)}"
        )

    serial_samples: dict[int, tuple[float, float]] = {}
    by_thread: dict[int, list[dict[str, str]]] = {thread: [] for thread in thread_counts}
    for row in measured:
        thread = _int_field(row, "thread_count")
        if thread not in by_thread:
            raise HandoffError(f"CSV 出现未请求线程数：{thread}")
        sample_index = _int_field(row, "sample_index")
        if sample_index < 1 or sample_index > repeat_count:
            raise HandoffError(f"CSV measured sample_index 越界：{sample_index}")
        serial_pair = (
            _float_field(row, "serial_symbolic_ms"),
            _float_field(row, "serial_numeric_ms"),
        )
        previous = serial_samples.setdefault(sample_index, serial_pair)
        if previous != serial_pair:
            raise HandoffError("不同线程行记录的串行基线样本不一致")
        by_thread[thread].append(row)

    if set(serial_samples) != set(range(1, repeat_count + 1)):
        raise HandoffError("串行基线 measured 样本索引不完整")
    serial_symbolic_ms = median(value[0] for value in serial_samples.values())
    serial_numeric_ms = median(value[1] for value in serial_samples.values())

    candidates: list[CandidateMetrics] = []
    summary_threads = _require_list(
        summary.get("per_thread_measured_statistics"),
        "summary.per_thread_measured_statistics",
    )
    summary_by_thread: dict[int, dict[str, object]] = {}
    for raw_item in summary_threads:
        item = _require_mapping(raw_item, "thread summary")
        thread = _require_int(item.get("thread_count"), "thread_count")
        if thread in summary_by_thread:
            raise HandoffError(f"summary 含重复线程：{thread}")
        summary_by_thread[thread] = item
    _expect_equal(set(summary_by_thread), set(thread_counts), "summary thread set")
    for thread in thread_counts:
        thread_rows = sorted(by_thread[thread], key=lambda row: _int_field(row, "sample_index"))
        if len(thread_rows) != repeat_count:
            raise HandoffError(f"线程 {thread} measured 样本数错误")
        symbolic_ms = median(_float_field(row, "symbolic_total_ms") for row in thread_rows)
        numeric_ms = median(
            _float_field(row, "numeric_reset_ms") + _float_field(row, "numeric_kernel_ms")
            for row in thread_rows
        )
        if symbolic_ms <= 0.0 or numeric_ms <= 0.0:
            raise HandoffError("计时中位数必须为正数")
        symbolic_speedup = serial_symbolic_ms / symbolic_ms
        numeric_speedup = serial_numeric_ms / numeric_ms
        recorded = summary_by_thread.get(thread)
        if recorded is None:
            raise HandoffError(f"summary 缺少线程 {thread} 的统计")
        recorded_symbolic = _require_mapping(
            recorded.get("symbolic_total_ms"), "recorded symbolic_total_ms"
        )
        recorded_numeric = _require_mapping(
            recorded.get("numeric_algorithm_ms"), "recorded numeric_algorithm_ms"
        )
        _expect_close(
            _require_number(recorded_symbolic.get("median_ms"), "symbolic median"),
            symbolic_ms,
            f"线程 {thread} symbolic median",
        )
        _expect_close(
            _require_number(recorded_numeric.get("median_ms"), "numeric median"),
            numeric_ms,
            f"线程 {thread} numeric median",
        )
        _expect_close(
            _require_number(recorded.get("symbolic_speedup"), "symbolic speedup"),
            symbolic_speedup,
            f"线程 {thread} symbolic speedup",
        )
        _expect_close(
            _require_number(recorded.get("numeric_speedup"), "numeric speedup"),
            numeric_speedup,
            f"线程 {thread} numeric speedup",
        )
        candidates.append(
            CandidateMetrics(
                thread_count=thread,
                symbolic_ms=symbolic_ms,
                numeric_ms=numeric_ms,
                symbolic_speedup=symbolic_speedup,
                numeric_speedup=numeric_speedup,
            )
        )

    serial_statistics = _require_mapping(
        summary.get("serial_measured_statistics"), "serial_measured_statistics"
    )
    _expect_close(
        _require_number(
            _require_mapping(
                serial_statistics.get("symbolic_total_ms"), "serial symbolic"
            ).get("median_ms"),
            "serial symbolic median",
        ),
        serial_symbolic_ms,
        "serial symbolic median",
    )
    _expect_close(
        _require_number(
            _require_mapping(
                serial_statistics.get("numeric_total_ms"), "serial numeric"
            ).get("median_ms"),
            "serial numeric median",
        ),
        serial_numeric_ms,
        "serial numeric median",
    )

    return PerformanceData(
        evidence_status="LOCAL_SMOKE",
        evidence_level="local-smoke",
        evidence_commit=evidence_commit,
        case_name=case_name,
        element_type=element_type,
        cpu_model=_require_text(environment.get("cpu_model"), "environment.cpu_model"),
        architecture=_require_text(environment.get("architecture"), "environment.architecture"),
        thread_counts=thread_counts,
        warmup_count=warmup_count,
        repeat_count=repeat_count,
        amortization_count=amortization_count,
        serial_symbolic_ms=serial_symbolic_ms,
        serial_numeric_ms=serial_numeric_ms,
        candidates=tuple(candidates),
        source_hashes=(
            ("run_manifest.json", _sha256(manifest_path)),
            ("benchmark_samples.csv", samples_sha),
            ("benchmark_summary.json", summary_sha),
        ),
    )


def _safe_report_link(target: str, suffix: str) -> str:
    path = PurePosixPath(target)
    if path.is_absolute() or path.suffix.lower() != suffix:
        raise HandoffError(f"报告图片链接无效：{target}")
    if tuple(path.parts[:2]) != ("..", "figures") or len(path.parts) != 3:
        raise HandoffError(f"报告图片必须位于 ../figures/：{target}")
    return target


def _candidate_by_thread(data: PerformanceData, thread_count: int) -> CandidateMetrics:
    matches = [item for item in data.candidates if item.thread_count == thread_count]
    if len(matches) != 1:
        raise HandoffError(f"性能数据必须恰好包含一个 p={thread_count} 配置")
    return matches[0]


def _speedup_relation(speedup: float) -> str:
    if speedup > 1.0:
        return "快于"
    if speedup < 1.0:
        return "慢于"
    return "等于"


def _candidate_conclusion(candidate: CandidateMetrics) -> str:
    symbolic_relation = _speedup_relation(candidate.symbolic_speedup)
    numeric_relation = _speedup_relation(candidate.numeric_speedup)
    prefix = f"$p={candidate.thread_count}$"
    if symbolic_relation == numeric_relation:
        return f"{prefix} 的符号组装和原子数值组装均{symbolic_relation}串行基线"
    return (
        f"{prefix} 的符号组装{symbolic_relation}串行基线，"
        f"原子数值组装{numeric_relation}串行基线"
    )


def render_handoff_report(
    *,
    canonical_report: str,
    data: PerformanceData,
    source_commit: str,
    source_archive_name: str,
    source_archive_sha256: str,
    figure_png_relative: str,
    figure_svg_relative: str,
) -> str:
    """在 canonical local-smoke 报告上增加读者摘要、图表和交接绑定。"""

    if SHA40.fullmatch(source_commit) is None:
        raise HandoffError("source_commit 必须是 40 位小写 SHA")
    if SHA256.fullmatch(source_archive_sha256) is None:
        raise HandoffError("source_archive_sha256 必须是 64 位小写 SHA-256")
    if Path(source_archive_name).name != source_archive_name or not source_archive_name.endswith(
        ".zip"
    ):
        raise HandoffError("source_archive_name 必须是 ZIP basename")
    png_link = _safe_report_link(figure_png_relative, ".png")
    svg_link = _safe_report_link(figure_svg_relative, ".svg")

    title = "# CSC3 并行整体刚度组装测试报告"
    if canonical_report.count(title) != 1:
        raise HandoffError("canonical 报告标题缺失或重复")
    if not canonical_report.startswith(WARNING + "\n") or not canonical_report.endswith(
        "\n" + WARNING + "\n"
    ):
        raise HandoffError("canonical 报告缺少首尾 NON-FORMAL 边界")

    one_thread = _candidate_by_thread(data, 1)
    two_thread = _candidate_by_thread(data, 2)
    two_thread_conclusion = _candidate_conclusion(two_thread)
    if source_commit == data.evidence_commit:
        provenance_statement = (
            "源码提交与性能证据提交相同；但该次运行仍是小规模 local-smoke，"
            "不构成正式性能验收。"
        )
    else:
        provenance_statement = (
            "源码提交与性能证据提交不同，因此本报告不把旧计时冒充为当前源码的"
            "正式性能验收。"
        )

    summary = (
        "# CSC3 Demo 并行组装交付测试报告（macOS ARM64 本地验证）\n\n"
        "## 0. 技术摘要\n\n"
        f"- 本报告使用 `{data.evidence_status}` / `{data.evidence_level}` 证据，"
        "属于 `NON-FORMAL` 内部技术评估材料，不能用于 Linux Intel/WindHub 正式性能验收。\n"
        "- 正确性结论来自归档的 Tet4、Hex8 矩阵、位移与残差检查；性能部分只回答"
        "并行路径和计时链路是否可执行，不回答大规模并行是否加速。\n"
        f"- 当前极小算例中，$p=1$ 的符号阶段相对串行基线为 "
        f"${one_thread.symbolic_speedup:.3f}\\times$，但原子数值阶段仅为 "
        f"${one_thread.numeric_speedup:.3f}\\times$；{two_thread_conclusion}。\n"
        f"- 待交付源码提交：`{source_commit}`；源码 ZIP：`{source_archive_name}`；"
        f"SHA-256：`{source_archive_sha256}`。\n"
        f"- 性能证据提交：`{data.evidence_commit}`。{provenance_statement}\n"
    )
    report = canonical_report.replace(title, summary.rstrip(), 1)

    performance_heading = "## 9. 性能结果\n"
    if report.count(performance_heading) != 1:
        raise HandoffError("canonical 报告性能章节缺失或重复")
    visual = (
        "\n### 9.1 性能对比图\n\n"
        "**阅读结论：** 图中的灰色柱为独立串行基线，绿色柱为 OpenMP 候选路径。"
        "两个耗时面板均为越低越好，加速比面板以 $S=1$ 为基准。当前网格只有 "
        "6 个 Tet4 单元，固定并行管理与原子同步开销相对计算量过大；该现象不能外推到"
        " WindHub 或生产规模。\n\n"
        f"![CSC3 Demo 本地性能对比]({png_link})\n\n"
        f"[SVG 矢量图]({svg_link})\n\n"
    )
    report = report.replace(performance_heading, performance_heading + visual, 1)

    closing = "\n" + WARNING + "\n"
    verification = (
        "\n## 14. 本次交接绑定\n\n"
        f"- 源码 ZIP：`{source_archive_name}`。\n"
        f"- 源码提交：`{source_commit}`。\n"
        f"- 源码 ZIP SHA-256：`{source_archive_sha256}`。\n"
        "- PNG、SVG、manifest-only verifier 输出、clean-room verifier 日志和本报告"
        "由外层 `SHA256SUMS` 统一绑定。\n"
        "- 研究院接收方可基于源码、API 契约和证据继续执行 Linux/实际求解器集成；"
        "这些后续工作不属于本地验证结论。\n"
    )
    report = report[: -len(closing)] + verification + closing
    return report


def _label_time(value: float) -> str:
    if value < 0.01:
        return f"{value:.6f}"
    return f"{value:.4f}"


def write_performance_figure(data: PerformanceData, png_path: Path, svg_path: Path) -> None:
    """按固定三联图契约写出 PNG 与 SVG；Matplotlib 仅在实际绘图时导入。"""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as error:
        raise HandoffError(
            "生成交接图需要 matplotlib；请在交付主机安装 matplotlib>=3.8,<4"
        ) from error

    if png_path.suffix.lower() != ".png" or svg_path.suffix.lower() != ".svg":
        raise HandoffError("图表输出必须分别为 .png 与 .svg")
    if png_path.exists() or svg_path.exists():
        raise HandoffError("拒绝覆盖已有图表输出")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "PingFang SC",
                "Noto Sans CJK SC",
                "Arial Unicode MS",
                "Heiti TC",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "csc3-demo-local-smoke-v1",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    ink = "#202428"
    muted = "#6b747c"
    grid = "#d9dee2"
    baseline = "#cfd5da"
    green = "#75bd00"
    light_green = "#bfe47f"
    labels = ["串行\n基线", "OpenMP\n1 线程", "OpenMP\n2 线程"]
    symbolic = [data.serial_symbolic_ms] + [item.symbolic_ms for item in data.candidates]
    numeric = [data.serial_numeric_ms] + [item.numeric_ms for item in data.candidates]
    symbolic_speedup = [1.0] + [item.symbolic_speedup for item in data.candidates]
    numeric_speedup = [1.0] + [item.numeric_speedup for item in data.candidates]

    figure, axes = plt.subplots(1, 3, figsize=(16, 8.4), dpi=160)
    figure.patch.set_facecolor("#ffffff")
    figure.subplots_adjust(left=0.065, right=0.985, top=0.69, bottom=0.27, wspace=0.24)
    figure.text(
        0.05,
        0.94,
        "CSC3 Demo 组装性能对比（本地验证）",
        fontsize=25,
        color=ink,
        ha="left",
        va="top",
        weight="medium",
    )
    figure.text(
        0.05,
        0.875,
        (
            f"{data.case_name} · {data.element_type} · {data.cpu_model} · "
            f"OpenMP p=1/2 · W={data.warmup_count}, R={data.repeat_count} · NON-FORMAL"
        ),
        fontsize=15,
        color=muted,
        ha="left",
        va="top",
    )

    def style_axis(axis, title: str, ylabel: str, direction: str) -> None:
        axis.set_title(title, loc="left", fontsize=18, color=ink, pad=28)
        axis.text(
            1.0,
            1.11,
            direction,
            transform=axis.transAxes,
            ha="right",
            va="bottom",
            color=muted,
            fontsize=11,
        )
        axis.set_ylabel(ylabel, fontsize=12, color=ink)
        axis.tick_params(axis="x", labelsize=11, colors=ink, length=0, pad=8)
        axis.tick_params(axis="y", labelsize=10, colors=muted)
        axis.grid(axis="y", color=grid, linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines["left"].set_color(ink)
        axis.spines["bottom"].set_color(ink)

    x = np.arange(len(labels))
    for axis, values, title in (
        (axes[0], symbolic, "符号组装总耗时"),
        (axes[1], numeric, "原子数值组装耗时"),
    ):
        colors = [baseline, green, green]
        bars = axis.bar(x, values, width=0.58, color=colors, edgecolor="none")
        axis.set_xticks(x, labels)
        axis.set_ylim(bottom=0.0, top=max(values) * 1.28)
        style_axis(axis, title, "毫秒", "越低越好")
        for bar, value in zip(bars, values):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.035,
                _label_time(value),
                ha="center",
                va="bottom",
                fontsize=11,
                color=ink,
            )

    width = 0.34
    first = axes[2].bar(
        x - width / 2,
        symbolic_speedup,
        width,
        label="符号组装",
        color=green,
        edgecolor="none",
    )
    second = axes[2].bar(
        x + width / 2,
        numeric_speedup,
        width,
        label="原子数值组装",
        color=light_green,
        edgecolor="#75bd00",
        linewidth=0.8,
    )
    axes[2].axhline(1.0, color="#727b83", linewidth=1.0, linestyle="--")
    axes[2].set_xticks(x, labels)
    axes[2].set_ylim(0.0, max(symbolic_speedup + numeric_speedup) * 1.28)
    style_axis(axes[2], "相对串行阶段加速比", "倍", "越高越好")
    axes[2].legend(frameon=False, loc="upper right", fontsize=10)
    for bars in (first, second):
        for bar in bars:
            value = float(bar.get_height())
            axes[2].text(
                bar.get_x() + bar.get_width() / 2,
                value + max(symbolic_speedup + numeric_speedup) * 0.035,
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=9.5,
                color=ink,
            )

    figure.text(
        0.05,
        0.16,
        (
            "口径：灰色为独立串行基线；符号耗时为 symbolic_total_ms；原子数值耗时为 "
            "numeric_reset_ms + numeric_kernel_ms；柱顶为 measured 样本中位数。"
        ),
        fontsize=11.5,
        color=ink,
        ha="left",
    )
    figure.text(
        0.05,
        0.105,
        (
            "限制：生成式 6 单元 Tet4 小网格，W=1、R=2。该图仅验证并行路径与计时链路；"
            "不能用于 Linux Intel/WindHub 正式性能验收，也不能外推生产规模。"
        ),
        fontsize=10.5,
        color=muted,
        ha="left",
    )
    figure.text(
        0.05,
        0.055,
        "数据源 SHA-256："
        + "；".join(f"{name}={digest[:12]}…" for name, digest in data.source_hashes),
        fontsize=9.5,
        color=muted,
        ha="left",
    )

    figure.savefig(
        png_path,
        dpi=260,
        facecolor="white",
        bbox_inches=None,
        metadata={"Software": "CSC3 Demo internal handoff builder"},
    )
    figure.savefig(
        svg_path,
        format="svg",
        facecolor="white",
        bbox_inches=None,
        metadata={"Date": None, "Creator": "CSC3 Demo internal handoff builder"},
    )
    plt.close(figure)
    if png_path.stat().st_size == 0 or svg_path.stat().st_size == 0:
        raise HandoffError("图表输出为空")


def _read_pass_verification(path: Path, label: str) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise HandoffError(f"{label} 不是 UTF-8：{path}") from error

    # verifier 的 clean-room 模式会先打印命令日志，最后输出一个格式化 JSON object。
    # 从后向前寻找能够完整解析到文件末尾的 object，避免把日志或字符串中伪造的
    # `{"status":"PASS"}` 子串误判为成功结果。
    result: dict[str, object] | None = None
    for position in range(len(text) - 1, -1, -1):
        if text[position] != "{":
            continue
        try:
            candidate = json.loads(
                text[position:],
                parse_constant=_reject_json_constant,
                object_pairs_hook=_reject_duplicate_object,
            )
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(candidate, dict) and "status" in candidate:
            result = candidate
            break
    if result is None or result.get("status") != "PASS":
        raise HandoffError(f"{label} 未记录 PASS：{path}")
    return data


def _scope_document(source_commit: str) -> bytes:
    return (
        "# CSC3 Demo 内部交接范围\n\n"
        f"- 源码提交：`{source_commit}`。\n"
        "- 分发状态：`INTERNAL EVALUATION ONLY`。\n"
        "- 性能证据：macOS ARM64 生成式 Tet4 `LOCAL_SMOKE`。\n"
        "- 本包不声明 Linux Intel/WindHub 正式性能通过，不声明四方正式验收完成。\n"
        "- 接收方可使用源码、README、API 契约和测试报告开展后续集成与独立验证。\n"
    ).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIMESTAMP)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = FIXED_FILE_MODE << 16
    return info


def _checksum_manifest(files: dict[str, bytes]) -> bytes:
    lines = [
        f"{hashlib.sha256(files[path]).hexdigest()}  {path}\n"
        for path in sorted(files)
    ]
    return "".join(lines).encode("utf-8")


def create_handoff_archive(
    *,
    source_archive: Path,
    report: Path,
    figure_png: Path,
    figure_svg: Path,
    manifest_verification: Path,
    clean_room_verification: Path,
    source_commit: str,
    output: Path,
) -> str:
    """创建固定顺序、时间戳和权限的外层交接 ZIP，并返回其 SHA-256。"""

    if SHA40.fullmatch(source_commit) is None:
        raise HandoffError("source_commit 必须是 40 位小写 SHA")
    if output.exists():
        raise HandoffError(f"拒绝覆盖已有外层 ZIP：{output}")
    inputs = (
        source_archive,
        report,
        figure_png,
        figure_svg,
        manifest_verification,
        clean_room_verification,
    )
    for path in inputs:
        if not path.is_file() or path.is_symlink():
            raise HandoffError(f"交接输入必须是普通文件：{path}")
    manifest_bytes = _read_pass_verification(
        manifest_verification, "manifest-only verification"
    )
    clean_room_bytes = _read_pass_verification(
        clean_room_verification, "clean-room verification"
    )

    files = {
        f"source/{source_archive.name}": source_archive.read_bytes(),
        f"reports/{report.name}": report.read_bytes(),
        f"figures/{figure_png.name}": figure_png.read_bytes(),
        f"figures/{figure_svg.name}": figure_svg.read_bytes(),
        f"verification/{manifest_verification.name}": manifest_bytes,
        f"verification/{clean_room_verification.name}": clean_room_bytes,
        "DELIVERY_SCOPE.zh-CN.md": _scope_document(source_commit),
    }
    files["SHA256SUMS"] = _checksum_manifest(files)
    package_root = (
        f"csc3-demo-internal-handoff-v{DEMO_VERSION}+{source_commit[:12]}-local-smoke"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED) as archive:
        for relative_path in sorted(files):
            archive.writestr(
                _zip_info(f"{package_root}/{relative_path}"), files[relative_path]
            )
    return _sha256(output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--canonical-report", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--manifest-verification", type=Path, required=True)
    parser.add_argument("--clean-room-verification", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.out_root.exists():
            raise HandoffError(f"--out-root 必须不存在：{args.out_root}")
        if SHA40.fullmatch(args.source_commit) is None:
            raise HandoffError("--source-commit 必须是 40 位小写 SHA")
        source_archive_sha = _sha256(args.source_archive)
        data = load_performance_data(args.evidence_dir)
        figures = args.out_root / "figures"
        reports = args.out_root / "reports"
        png = figures / f"{FIGURE_STEM}.png"
        svg = figures / f"{FIGURE_STEM}.svg"
        report = reports / REPORT_NAME
        write_performance_figure(data, png, svg)
        report_text = render_handoff_report(
            canonical_report=args.canonical_report.read_text(encoding="utf-8"),
            data=data,
            source_commit=args.source_commit,
            source_archive_name=args.source_archive.name,
            source_archive_sha256=source_archive_sha,
            figure_png_relative=f"../figures/{png.name}",
            figure_svg_relative=f"../figures/{svg.name}",
        )
        _write_new(report, report_text.encode("utf-8"))
        archive = args.out_root / (
            f"csc3-demo-internal-handoff-v{DEMO_VERSION}+"
            f"{args.source_commit[:12]}-local-smoke.zip"
        )
        archive_sha = create_handoff_archive(
            source_archive=args.source_archive,
            report=report,
            figure_png=png,
            figure_svg=svg,
            manifest_verification=args.manifest_verification,
            clean_room_verification=args.clean_room_verification,
            source_commit=args.source_commit,
            output=archive,
        )
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "archive": str(archive.resolve()),
                    "sha256": archive_sha,
                    "report": str(report.resolve()),
                    "figure_png": str(png.resolve()),
                    "figure_svg": str(svg.resolve()),
                    "evidence_status": data.evidence_status,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (HandoffError, OSError, UnicodeError) as error:
        print(f"internal handoff generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
