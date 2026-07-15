#!/usr/bin/env python3
"""Render one approved CSC3 acceptance decision into three canonical files."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import ModuleType


CORE_MODULE_NAME = "csc3_acceptance_core"
DECISION_SCHEMA = "ACCEPTANCE_DECISION.schema.json"
RECORD_SCHEMA = "ACCEPTANCE_RECORD.schema.json"
RECORD_VERSION = "csc3-demo-formal-acceptance-v2"
MACHINE_FACTS_FILENAME = "acceptance-machine-facts.json"
DECISION_FILENAME = "acceptance-decision.json"
CHECKLIST_TEMPLATE = "ACCEPTANCE_CHECKLIST.zh-CN.md"
DELIVERY_NOTE_TEMPLATE = "DELIVERY_NOTE_TEMPLATE.zh-CN.md"
PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
APPROVAL_ROLES = (
    "operator",
    "technical_reviewer",
    "delivery_approver",
    "recipient_acknowledgement",
)
PARTY_BY_APPROVAL = {
    "operator": "operator",
    "technical_reviewer": "technical_reviewer",
    "delivery_approver": "delivery_approver",
    "recipient_acknowledgement": "recipient",
}


class AcceptanceRenderingError(RuntimeError):
    """Approved inputs cannot be rendered without weakening their bindings."""


@dataclass(frozen=True)
class RenderedAcceptance:
    record_content: bytes
    checklist_content: bytes
    delivery_note_content: bytes


def _load_sibling(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise AcceptanceRenderingError(f"cannot load required helper: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


_core = _load_sibling("acceptance_core.py", CORE_MODULE_NAME)
_validator = _load_sibling(
    "validate_acceptance_record.py", "csc3_acceptance_render_schema_validator"
)
_preparer = _load_sibling(
    "prepare_acceptance_materials.py", "csc3_acceptance_render_publisher"
)

# The renderer intentionally uses the exact Task 1 anchored publication primitive.
_write_fsynced_at = _preparer._write_fsynced_at


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AcceptanceRenderingError(f"{label} must be a JSON object")
    return value


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(child) for child in value]
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceRenderingError(f"{label} must be a nonblank string")
    if value == PLACEHOLDER or value.strip().upper() in {
        "COMPLETED",
        "DONE",
        "N/A",
        "OK",
        "PASS",
        "PENDING",
    }:
        raise AcceptanceRenderingError(f"{label} must not be a placeholder")
    if any(character in value for character in ("`", "\r", "\n")):
        raise AcceptanceRenderingError(
            f"{label} must be one safe Markdown line without backticks"
        )
    return value


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _artifact(record: Mapping[str, object], name: str) -> tuple[str, str]:
    artifacts = _mapping(record.get("artifacts"), "artifacts")
    binding = _mapping(artifacts.get(name), f"artifacts.{name}")
    path = binding.get("path")
    digest = binding.get("sha256")
    if not isinstance(path, str) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise AcceptanceRenderingError(f"artifacts.{name} lacks path/SHA-256")
    return path, str(digest)


def _objective_artifact_binding(
    record: Mapping[str, object], name: str
) -> tuple[str, str]:
    try:
        return _artifact(record, name)
    except AcceptanceRenderingError as error:
        raise AcceptanceRenderingError(
            f"acceptance record lacks canonical objective artifact {name}: {error}"
        ) from error


def _required_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AcceptanceRenderingError(
            f"acceptance record lacks objective {label} mapping"
        )
    return value


def _objective_number(value: object, label: str) -> str:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise AcceptanceRenderingError(
            f"acceptance record objective {label} is not finite"
        )
    return format(float(value), ".15g")


def _objective_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(
        character in value for character in ("`", "\n", "\r")
    ):
        raise AcceptanceRenderingError(
            f"acceptance record objective {label} is not a safe nonblank string"
        )
    return value


def _objective_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AcceptanceRenderingError(
            f"acceptance record objective {label} is not an integer"
        )
    return value


def _objective_boolean(value: object, label: str) -> str:
    if not isinstance(value, bool):
        raise AcceptanceRenderingError(
            f"acceptance record objective {label} is not a boolean"
        )
    return "true" if value else "false"


def _canonical_presentation_pdf_binding(record: Mapping[str, object]) -> str:
    """Return the one delivery-note/checklist value for the optional PDF."""
    artifacts = record.get("artifacts")
    pdf = artifacts.get("presentation_pdf") if isinstance(artifacts, Mapping) else None
    if pdf is None:
        return "presentation_pdf=ABSENT"
    pdf_path, pdf_sha = _objective_artifact_binding(record, "presentation_pdf")
    return f"presentation_pdf={pdf_path}；PDF_SHA-256={pdf_sha}"


def _canonical_demo_version(
    record: Mapping[str, object], archive_name: str
) -> str:
    delivery_path, _ = _objective_artifact_binding(record, "delivery_zip")
    recorded_name = PurePosixPath(delivery_path).name
    if recorded_name != archive_name:
        raise AcceptanceRenderingError(
            "acceptance record delivery_zip filename differs from the candidate archive"
        )
    match = re.fullmatch(
        r"csc3-symmetric-assembly-demo-v(\d+\.\d+\.\d+)\+[0-9a-f]{12}\.zip",
        recorded_name,
    )
    if match is None:
        raise AcceptanceRenderingError(
            "acceptance record delivery_zip filename lacks a canonical demo version"
        )
    return match.group(1)


def _canonical_delivery_date_utc(record: Mapping[str, object]) -> str:
    approvals = _required_mapping(record.get("approvals"), "approvals")
    timestamps: list[datetime] = []
    for name in APPROVAL_ROLES:
        approval = _required_mapping(approvals.get(name), f"approvals.{name}")
        raw = approval.get("acknowledged_at_utc")
        if not isinstance(raw, str):
            raise AcceptanceRenderingError(
                f"acceptance record approvals.{name}.acknowledged_at_utc is missing"
            )
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as error:
            raise AcceptanceRenderingError(
                f"acceptance record approvals.{name}.acknowledged_at_utc is invalid"
            ) from error
        if parsed.tzinfo is None:
            raise AcceptanceRenderingError(
                f"acceptance record approvals.{name}.acknowledged_at_utc lacks a timezone"
            )
        timestamps.append(parsed.astimezone(timezone.utc))
    return max(timestamps).date().isoformat()


def _canonical_correctness_summary(record: Mapping[str, object]) -> str:
    correctness = _required_mapping(record.get("correctness"), "correctness")
    thresholds = _required_mapping(
        correctness.get("thresholds"), "correctness.thresholds"
    )
    maximum_absolute = _required_mapping(
        thresholds.get("maximum_absolute_error"),
        "correctness.thresholds.maximum_absolute_error",
    )
    if maximum_absolute.get("scale_quantity") != "max_abs_serial_matrix_entry":
        raise AcceptanceRenderingError(
            "acceptance record correctness maximum-absolute scale quantity is invalid"
        )
    tet4 = _required_mapping(correctness.get("tet4"), "correctness.tet4")
    hex8 = _required_mapping(correctness.get("hex8"), "correctness.hex8")
    frobenius_maximum = _objective_number(
        thresholds.get("frobenius_relative_error_maximum"),
        "correctness.thresholds.frobenius_relative_error_maximum",
    )
    absolute_term = _objective_number(
        maximum_absolute.get("absolute_term"),
        "correctness.thresholds.maximum_absolute_error.absolute_term",
    )
    scale_term = _objective_number(
        maximum_absolute.get("scale_term"),
        "correctness.thresholds.maximum_absolute_error.scale_term",
    )
    displacement_maximum = _objective_number(
        thresholds.get("displacement_relative_error_maximum"),
        "correctness.thresholds.displacement_relative_error_maximum",
    )
    residual_maximum = _objective_number(
        thresholds.get("relative_residual_maximum"),
        "correctness.thresholds.relative_residual_maximum",
    )
    return (
        f"status={correctness.get('status')}；Tet4={tet4.get('status')}；"
        f"Hex8={hex8.get('status')}；"
        f"$e_F \\le {frobenius_maximum}$；"
        f"$e_{{\\max}} \\le {absolute_term} + {scale_term}\\max |K_s|$；"
        f"$e_u \\le {displacement_maximum}$；"
        f"$r_{{\\mathrm{{rel}}}} \\le {residual_maximum}$"
    )


def _canonical_performance_summary(record: Mapping[str, object]) -> str:
    performance = _required_mapping(record.get("performance"), "performance")
    thresholds = _required_mapping(
        performance.get("thresholds"), "performance.thresholds"
    )
    numeric_threads = performance.get("numeric_thread_count")
    symbolic_threads = performance.get("symbolic_thread_count")
    sample_count = performance.get("raw_sample_count")
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in (numeric_threads, symbolic_threads, sample_count)
    ):
        raise AcceptanceRenderingError(
            "acceptance record performance thread/sample counts are invalid"
        )
    maximum_cv = _objective_number(
        thresholds.get("maximum_coefficient_of_variation"),
        "performance.thresholds.maximum_coefficient_of_variation",
    )
    numeric_speedup = _objective_number(
        performance.get("numeric_speedup"), "performance.numeric_speedup"
    )
    numeric_minimum = _objective_number(
        thresholds.get("numeric_speedup_minimum"),
        "performance.thresholds.numeric_speedup_minimum",
    )
    numeric_cv = _objective_number(
        performance.get("numeric_coefficient_of_variation"),
        "performance.numeric_coefficient_of_variation",
    )
    symbolic_speedup = _objective_number(
        performance.get("symbolic_speedup"), "performance.symbolic_speedup"
    )
    symbolic_minimum = _objective_number(
        thresholds.get("symbolic_speedup_exclusive_minimum"),
        "performance.thresholds.symbolic_speedup_exclusive_minimum",
    )
    symbolic_cv = _objective_number(
        performance.get("symbolic_coefficient_of_variation"),
        "performance.symbolic_coefficient_of_variation",
    )
    return (
        f"status={performance.get('status')}；"
        f"$S_{{\\mathrm{{numeric}}}}({numeric_threads})="
        f"{numeric_speedup} \\ge {numeric_minimum}$，"
        f"$CV={numeric_cv} \\le {maximum_cv}$；"
        f"$S_{{\\mathrm{{symbolic}}}}({symbolic_threads})="
        f"{symbolic_speedup} > {symbolic_minimum}$，"
        f"$CV={symbolic_cv} \\le {maximum_cv}$；"
        f"原始样本数 $N={sample_count}$"
    )


def _canonical_verification_summary(
    record: Mapping[str, object],
    objective_artifacts: Mapping[str, tuple[str, str]],
) -> str:
    verifications = _required_mapping(record.get("verifications"), "verifications")
    fields = (
        ("deterministic_package", "deterministic_package_record"),
        ("manifest_only", "manifest_only_verifier_output"),
        ("clean_room", "clean_room_verifier_log"),
    )
    rendered: list[str] = []
    for verification_name, artifact_name in fields:
        verification = _required_mapping(
            verifications.get(verification_name),
            f"verifications.{verification_name}",
        )
        try:
            path, digest = objective_artifacts[artifact_name]
        except KeyError as error:
            raise AcceptanceRenderingError(
                f"acceptance record lacks objective artifact {artifact_name}"
            ) from error
        rendered.append(
            f"{verification_name}={verification.get('status')}（{path}；SHA-256 {digest}）"
        )
    return "；".join(rendered)


def _canonical_deviation_summary(record: Mapping[str, object]) -> str:
    deviations = record.get("deviations")
    if not isinstance(deviations, list):
        raise AcceptanceRenderingError("acceptance record deviations must be an array")
    if not deviations:
        return "无（验收记录 deviations 为空）"
    rendered: list[str] = []
    for index, raw in enumerate(deviations):
        deviation = _required_mapping(raw, f"deviations[{index}]")
        identifier = deviation.get("identifier")
        disposition = deviation.get("disposition")
        approval_reference = deviation.get("approval_reference")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (identifier, disposition, approval_reference)
        ):
            raise AcceptanceRenderingError(
                f"acceptance record deviations[{index}] lacks canonical disposition binding"
            )
        rendered.append(
            f"{identifier}={disposition}（批准引用 {approval_reference}）"
        )
    return "；".join(rendered)


def _canonical_verification(
    record: Mapping[str, object], name: str
) -> Mapping[str, object]:
    verifications = _required_mapping(record.get("verifications"), "verifications")
    verification = _required_mapping(
        verifications.get(name), f"verifications.{name}"
    )
    _objective_text(verification.get("status"), f"verifications.{name}.status")
    _objective_text(
        verification.get("evidence_reference"),
        f"verifications.{name}.evidence_reference",
    )
    return verification


@dataclass(frozen=True)
class _ChecklistContext:
    record: Mapping[str, object]
    archive_name: str
    archive_sha256: str
    record_relative: str
    record_sha256: str
    artifacts: Mapping[str, tuple[str, str]]
    source_commit: str
    distribution: str
    controlled_host: Mapping[str, object]
    toolchain: Mapping[str, object]
    input_facts: Mapping[str, object]
    execution: Mapping[str, object]
    correctness: Mapping[str, object]
    performance: Mapping[str, object]
    correctness_thresholds: Mapping[str, object]
    performance_thresholds: Mapping[str, object]
    tet4: Mapping[str, object]
    hex8: Mapping[str, object]
    ctest: Mapping[str, object]
    source_identity: Mapping[str, object]
    report_recomputation: Mapping[str, object]
    deterministic: Mapping[str, object]
    manifest_only: Mapping[str, object]
    clean_room: Mapping[str, object]
    requested_threads: str
    ctest_names: str

    def artifact(self, name: str) -> tuple[str, str]:
        try:
            return self.artifacts[name]
        except KeyError as error:
            raise AcceptanceRenderingError(
                f"acceptance record lacks canonical checklist artifact {name}"
            ) from error

    @staticmethod
    def number(mapping: Mapping[str, object], field: str, prefix: str) -> str:
        return _objective_number(mapping.get(field), f"{prefix}.{field}")

    @staticmethod
    def boolean(mapping: Mapping[str, object], field: str, prefix: str) -> str:
        return _objective_boolean(mapping.get(field), f"{prefix}.{field}")

    @staticmethod
    def text(mapping: Mapping[str, object], field: str, prefix: str) -> str:
        return _objective_text(mapping.get(field), f"{prefix}.{field}")


def _build_checklist_context(
    record: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative: str,
    record_sha256: str,
    objective_artifacts: Mapping[str, tuple[str, str]],
    validation_status: object,
) -> _ChecklistContext:
    controlled_host = _required_mapping(record.get("controlled_host"), "controlled_host")
    toolchain = _required_mapping(record.get("toolchain"), "toolchain")
    input_facts = _required_mapping(record.get("input"), "input")
    execution = _required_mapping(record.get("execution"), "execution")
    correctness = _required_mapping(record.get("correctness"), "correctness")
    performance = _required_mapping(record.get("performance"), "performance")
    verifications = _required_mapping(record.get("verifications"), "verifications")
    requested_raw = execution.get("requested_thread_counts")
    if not isinstance(requested_raw, list) or not requested_raw:
        raise AcceptanceRenderingError(
            "acceptance record objective execution.requested_thread_counts is invalid"
        )
    ctest = _required_mapping(verifications.get("ctest"), "verifications.ctest")
    ctest_names_raw = ctest.get("test_names")
    if not isinstance(ctest_names_raw, list) or not ctest_names_raw:
        raise AcceptanceRenderingError(
            "acceptance record objective verifications.ctest.test_names is invalid"
        )
    if validation_status != "PASS":
        raise AcceptanceRenderingError("acceptance record validator status must be PASS")
    return _ChecklistContext(
        record=record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative=record_relative,
        record_sha256=record_sha256,
        artifacts=objective_artifacts,
        source_commit=_objective_text(record.get("source_commit"), "source_commit"),
        distribution=_objective_text(record.get("distribution"), "distribution"),
        controlled_host=controlled_host,
        toolchain=toolchain,
        input_facts=input_facts,
        execution=execution,
        correctness=correctness,
        performance=performance,
        correctness_thresholds=_required_mapping(
            correctness.get("thresholds"), "correctness.thresholds"
        ),
        performance_thresholds=_required_mapping(
            performance.get("thresholds"), "performance.thresholds"
        ),
        tet4=_required_mapping(correctness.get("tet4"), "correctness.tet4"),
        hex8=_required_mapping(correctness.get("hex8"), "correctness.hex8"),
        ctest=ctest,
        source_identity=_canonical_verification(record, "source_and_input_identity"),
        report_recomputation=_canonical_verification(record, "report_recomputation"),
        deterministic=_canonical_verification(record, "deterministic_package"),
        manifest_only=_canonical_verification(record, "manifest_only"),
        clean_room=_canonical_verification(record, "clean_room"),
        requested_threads=",".join(
            str(_objective_integer(value, "execution.requested_thread_counts[]"))
            for value in requested_raw
        ),
        ctest_names=",".join(
            _objective_text(value, "verifications.ctest.test_names[]")
            for value in ctest_names_raw
        ),
    )


def _canonical_source_and_input_values(context: _ChecklistContext) -> dict[str, str]:
    runbook_path, runbook_sha = context.artifact("runbook_log")
    input_size = _objective_integer(
        context.input_facts.get("size_bytes"), "input.size_bytes"
    )
    input_lfs_size = _objective_integer(
        context.input_facts.get("head_lfs_size_bytes"), "input.head_lfs_size_bytes"
    )
    source_identity = context.source_identity
    return {
        "分发标记逐字": context.distribution,
        "完整、非 shallow": (
            f"source_and_input_identity={source_identity['status']}；"
            f"evidence={source_identity['evidence_reference']}"
        ),
        "git rev-parse HEAD": (
            f"HEAD={context.source_commit}；source_and_input_identity={source_identity['status']}"
        ),
        "git status --porcelain": (
            f"worktree_clean={source_identity['status']}；runbook={runbook_path}；"
            f"SHA-256={runbook_sha}"
        ),
        "输入路径严格为": context.text(
            context.input_facts, "repository_relative_path", "input"
        ),
        "Git LFS 实体化": (
            f"tracked={context.boolean(context.input_facts, 'tracked', 'input')}；"
            f"materialized={context.boolean(context.input_facts, 'materialized', 'input')}；"
            f"matches_head_lfs={context.boolean(context.input_facts, 'matches_head_lfs', 'input')}"
        ),
        "字节数与 `HEAD`": (
            f"size_bytes={input_size}；head_lfs_size_bytes={input_lfs_size}"
        ),
        "SHA-256 与 `HEAD`": (
            f"sha256={context.text(context.input_facts, 'sha256', 'input')}；"
            "head_lfs_oid_sha256="
            f"{context.text(context.input_facts, 'head_lfs_oid_sha256', 'input')}"
        ),
    }


def _canonical_environment_values(context: _ChecklistContext) -> dict[str, str]:
    host_preflight_path, host_preflight_sha = context.artifact("host_preflight")
    physical_cores = _objective_integer(
        context.controlled_host.get("physical_core_count"),
        "controlled_host.physical_core_count",
    )
    logical_cores = _objective_integer(
        context.controlled_host.get("logical_core_count"),
        "controlled_host.logical_core_count",
    )
    return {
        "受控主机 ID": context.text(
            context.controlled_host, "controlled_host_id", "controlled_host"
        ),
        "物理 Linux": (
            f"system={context.text(context.controlled_host, 'system', 'controlled_host')}；"
            f"architecture={context.text(context.controlled_host, 'architecture', 'controlled_host')}；"
            f"cpu_vendor={context.text(context.controlled_host, 'cpu_vendor', 'controlled_host')}；"
            f"cpu_model={context.text(context.controlled_host, 'cpu_model', 'controlled_host')}；"
            f"physical_core_count={physical_cores}；logical_core_count={logical_cores}"
        ),
        "host-preflight.txt": f"path={host_preflight_path}；SHA-256={host_preflight_sha}",
        "GCC、CMake": (
            f"compiler={context.text(context.toolchain, 'compiler', 'toolchain')} "
            f"{context.text(context.toolchain, 'compiler_version', 'toolchain')}；"
            f"CMake={context.text(context.toolchain, 'cmake_version', 'toolchain')}；"
            f"Ninja={context.text(context.toolchain, 'ninja_version', 'toolchain')}；"
            f"Python={context.text(context.toolchain, 'python_version', 'toolchain')}；"
            f"Git={context.text(context.toolchain, 'git_version', 'toolchain')}；"
            f"Git LFS={context.text(context.toolchain, 'git_lfs_version', 'toolchain')}"
        ),
        "OMP_DYNAMIC=false": (
            f"openmp_found={context.boolean(context.toolchain, 'openmp_found', 'toolchain')}；"
            f"openmp_required={context.boolean(context.toolchain, 'openmp_required', 'toolchain')}；"
            f"OMP_DYNAMIC={context.text(context.execution, 'omp_dynamic', 'execution')}；"
            f"OMP_PROC_BIND={context.text(context.execution, 'omp_proc_bind', 'execution')}；"
            f"OMP_PLACES={context.text(context.execution, 'omp_places', 'execution')}"
        ),
        "正式线程集合": (
            f"requested_thread_counts={context.requested_threads}；"
            "physical_core_thread_included="
            f"{context.boolean(context.execution, 'physical_core_thread_included', 'execution')}；"
            f"report_recomputation={context.report_recomputation['status']}"
        ),
        "预热 $W": (
            f"warmup_count={_objective_integer(context.execution.get('warmup_count'), 'execution.warmup_count')}；"
            f"repeat_count={_objective_integer(context.execution.get('repeat_count'), 'execution.repeat_count')}；"
            f"amortization_count={_objective_integer(context.execution.get('amortization_count'), 'execution.amortization_count')}"
        ),
    }


def _canonical_correctness_values(context: _ChecklistContext) -> dict[str, str]:
    ctest_path, ctest_sha = context.artifact("ctest_junit")
    tet4 = context.tet4
    hex8 = context.hex8
    thresholds = context.correctness_thresholds
    return {
        "CTest 精确执行": (
            f"status={context.text(context.ctest, 'status', 'verifications.ctest')}；"
            f"test_count={_objective_integer(context.ctest.get('test_count'), 'verifications.ctest.test_count')}；"
            f"failed_count={_objective_integer(context.ctest.get('failed_count'), 'verifications.ctest.failed_count')}；"
            f"skipped_count={_objective_integer(context.ctest.get('skipped_count'), 'verifications.ctest.skipped_count')}；"
            f"not_run_count={_objective_integer(context.ctest.get('not_run_count'), 'verifications.ctest.not_run_count')}；"
            f"test_names={context.ctest_names}；"
            f"evidence={context.text(context.ctest, 'evidence_reference', 'verifications.ctest')}；"
            f"junit={ctest_path}；JUnit_SHA-256={ctest_sha}"
        ),
        "CSC3 结构逐项一致": (
            f"Tet4={context.text(tet4, 'status', 'correctness.tet4')}/"
            f"structure_equal={context.boolean(tet4, 'structure_equal', 'correctness.tet4')}/"
            f"values_finite={context.boolean(tet4, 'values_finite', 'correctness.tet4')}/"
            f"scatter_indices_valid={context.boolean(tet4, 'scatter_indices_valid', 'correctness.tet4')}；"
            f"Hex8={context.text(hex8, 'status', 'correctness.hex8')}/"
            f"structure_equal={context.boolean(hex8, 'structure_equal', 'correctness.hex8')}/"
            f"values_finite={context.boolean(hex8, 'values_finite', 'correctness.hex8')}/"
            f"scatter_indices_valid={context.boolean(hex8, 'scatter_indices_valid', 'correctness.hex8')}"
        ),
        "Frobenius 相对误差": (
            f"Tet4={context.number(tet4, 'frobenius_relative_error', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'frobenius_relative_error', 'correctness.hex8')}；"
            "maximum="
            f"{context.number(thresholds, 'frobenius_relative_error_maximum', 'correctness.thresholds')}"
        ),
        "最大绝对误差满足": (
            f"Tet4={context.number(tet4, 'maximum_absolute_error', 'correctness.tet4')}/"
            f"serial_max={context.number(tet4, 'maximum_absolute_serial_entry', 'correctness.tet4')}/"
            f"tolerance={context.number(tet4, 'maximum_absolute_error_tolerance', 'correctness.tet4')}/"
            f"within_tolerance={context.boolean(tet4, 'maximum_absolute_error_within_tolerance', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'maximum_absolute_error', 'correctness.hex8')}/"
            f"serial_max={context.number(hex8, 'maximum_absolute_serial_entry', 'correctness.hex8')}/"
            f"tolerance={context.number(hex8, 'maximum_absolute_error_tolerance', 'correctness.hex8')}/"
            f"within_tolerance={context.boolean(hex8, 'maximum_absolute_error_within_tolerance', 'correctness.hex8')}"
        ),
        "位移相对误差满足": (
            f"Tet4={context.number(tet4, 'displacement_relative_error', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'displacement_relative_error', 'correctness.hex8')}；"
            "maximum="
            f"{context.number(thresholds, 'displacement_relative_error_maximum', 'correctness.thresholds')}"
        ),
        "自由度方程相对残差": (
            f"Tet4={context.number(tet4, 'relative_residual', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'relative_residual', 'correctness.hex8')}；"
            "maximum="
            f"{context.number(thresholds, 'relative_residual_maximum', 'correctness.thresholds')}"
        ),
    }


def _canonical_performance_values(context: _ChecklistContext) -> dict[str, str]:
    samples_path, samples_sha = context.artifact("benchmark_samples")
    summary_path, summary_sha = context.artifact("benchmark_summary")
    performance = context.performance
    thresholds = context.performance_thresholds
    raw_sample_count = _objective_integer(
        performance.get("raw_sample_count"), "performance.raw_sample_count"
    )
    numeric_thread = _objective_integer(
        performance.get("numeric_thread_count"), "performance.numeric_thread_count"
    )
    symbolic_thread = _objective_integer(
        performance.get("symbolic_thread_count"),
        "performance.symbolic_thread_count",
    )
    return {
        "benchmark_samples.csv": (
            f"path={samples_path}；SHA-256={samples_sha}；"
            f"raw_sample_count={raw_sample_count}；"
            f"repeat_count={_objective_integer(context.execution.get('repeat_count'), 'execution.repeat_count')}；"
            f"threads={context.requested_threads}"
        ),
        "benchmark_summary.json": (
            f"path={summary_path}；SHA-256={summary_sha}；"
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}"
        ),
        "S_{\\mathrm{numeric}}": (
            f"p={numeric_thread}；"
            f"speedup={context.number(performance, 'numeric_speedup', 'performance')}；"
            f"minimum={context.number(thresholds, 'numeric_speedup_minimum', 'performance.thresholds')}"
        ),
        "S_{\\mathrm{symbolic}}": (
            f"p={symbolic_thread}；"
            f"speedup={context.number(performance, 'symbolic_speedup', 'performance')}；"
            "exclusive_minimum="
            f"{context.number(thresholds, 'symbolic_speedup_exclusive_minimum', 'performance.thresholds')}"
        ),
        "$CV \\le 0.05$": (
            "numeric="
            f"{context.number(performance, 'numeric_coefficient_of_variation', 'performance')}；"
            "symbolic="
            f"{context.number(performance, 'symbolic_coefficient_of_variation', 'performance')}；"
            "maximum="
            f"{context.number(thresholds, 'maximum_coefficient_of_variation', 'performance.thresholds')}"
        ),
        "symbolic、numeric": (
            f"raw_sample_count={raw_sample_count}；"
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}"
        ),
        "CI runner 计时": (
            f"evidence_level={context.text(context.execution, 'evidence_level', 'execution')}；"
            f"report_intent={context.text(context.execution, 'report_intent', 'execution')}；"
            "controlled_host_id="
            f"{context.text(context.controlled_host, 'controlled_host_id', 'controlled_host')}"
        ),
    }


def _canonical_evidence_values(context: _ChecklistContext) -> dict[str, str]:
    run_manifest_path, run_manifest_sha = context.artifact("run_manifest")
    report_path, report_sha = context.artifact("canonical_markdown_report")
    source_file_path, source_file_sha = context.artifact("source_commit_file")
    checksums_path, checksums_sha = context.artifact("sha256sums_file")
    return {
        "run_manifest.json": (
            f"execution.status={context.text(context.execution, 'status', 'execution')}；"
            f"evidence_level={context.text(context.execution, 'evidence_level', 'execution')}；"
            f"report_intent={context.text(context.execution, 'report_intent', 'execution')}；"
            f"path={run_manifest_path}；SHA-256={run_manifest_sha}"
        ),
        "after-build": (
            f"source_and_input_identity={context.source_identity['status']}；"
            f"evidence={context.source_identity['evidence_reference']}"
        ),
        "generate_test_report.py": (
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}；"
            f"path={report_path}；SHA-256={report_sha}"
        ),
        "报告中的源码 SHA": (
            f"source_commit={context.source_commit}；"
            f"source_and_input_identity={context.source_identity['status']}；"
            f"delivery_zip={context.archive_name}；SHA-256={context.archive_sha256}"
        ),
        "证据 SHA 与报告": (
            f"run_manifest_SHA256={run_manifest_sha}；report_SHA256={report_sha}；"
            f"SHA256SUMS_SHA256={checksums_sha}"
        ),
        "SOURCE_COMMIT": (
            f"source_commit={context.source_commit}；path={source_file_path}；"
            f"SHA-256={source_file_sha}"
        ),
    }


def _canonical_packaging_values(context: _ChecklistContext) -> dict[str, str]:
    report_path, report_sha = context.artifact("canonical_markdown_report")
    checksums_path, checksums_sha = context.artifact("sha256sums_file")
    outcome_path, outcome_sha = context.artifact("outcome_record")
    deterministic_path, deterministic_sha = context.artifact(
        "deterministic_package_record"
    )
    manifest_only_path, manifest_only_sha = context.artifact(
        "manifest_only_verifier_output"
    )
    clean_room_path, clean_room_sha = context.artifact("clean_room_verifier_log")
    return {
        "PACKAGE_CANDIDATE": (
            f"candidate_status=PACKAGE_CANDIDATE；outcome_record={outcome_path}；"
            f"SHA-256={outcome_sha}"
        ),
        "候选 `SHA256SUMS`": (
            f"deterministic_package={context.deterministic['status']}；"
            f"path={checksums_path}；SHA-256={checksums_sha}"
        ),
        "确定性打包": (
            f"status={context.deterministic['status']}；"
            f"evidence={context.deterministic['evidence_reference']}；"
            f"path={deterministic_path}；SHA-256={deterministic_sha}"
        ),
        "manifest-only 验证": (
            f"status={context.manifest_only['status']}；"
            f"evidence={context.manifest_only['evidence_reference']}；"
            f"path={manifest_only_path}；SHA-256={manifest_only_sha}"
        ),
        "完整 clean-room": (
            f"status={context.clean_room['status']}；"
            f"evidence={context.clean_room['evidence_reference']}；"
            f"path={clean_room_path}；SHA-256={clean_room_sha}"
        ),
        "validate_acceptance_record.py": (
            f"validator=PASS；acceptance_record={context.record_relative}；"
            f"SHA-256={context.record_sha256}"
        ),
        "finalize_delivery.py": (
            "output_precondition=NONEXISTENT；publication=ATOMIC_NO_REPLACE；"
            "final_hash_manifest=FINAL_SHA256SUMS"
        ),
        "Markdown 是权威报告": (
            f"canonical_markdown_report={report_path}；SHA-256={report_sha}；"
            f"{_canonical_presentation_pdf_binding(context.record)}"
        ),
        "偏差清单": _canonical_deviation_summary(context.record),
        "最终决定只能为": context.text(context.record, "status", "record"),
    }


def _canonical_objective_checklist_values(
    record: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative: str,
    record_sha256: str,
    objective_artifacts: Mapping[str, tuple[str, str]],
    validation_status: object,
) -> dict[str, str]:
    """Build every machine-verifiable checklist value from validated facts."""
    context = _build_checklist_context(
        record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative=record_relative,
        record_sha256=record_sha256,
        objective_artifacts=objective_artifacts,
        validation_status=validation_status,
    )
    values: dict[str, str] = {}
    for section in (
        _canonical_source_and_input_values,
        _canonical_environment_values,
        _canonical_correctness_values,
        _canonical_performance_values,
        _canonical_evidence_values,
        _canonical_packaging_values,
    ):
        values.update(section(context))
    return values


def _safe_relative(value: str, label: str) -> str:
    try:
        relative = _core._safe_relative(value, label)
    except Exception as error:
        raise AcceptanceRenderingError(str(error)) from error
    return relative.as_posix()


def _validate_schema(document: object, filename: str, label: str) -> None:
    try:
        _validator.validate_schema_document(
            document,
            filename,
            schema_label=label,
        )
    except Exception as error:
        raise AcceptanceRenderingError(f"{label} validation failed: {error}") from error


def _validated_candidate_state(
    machine_facts: Mapping[str, object], decision: Mapping[str, object]
) -> Mapping[str, object]:
    if machine_facts.get("schema_version") != _core.MACHINE_FACTS_VERSION:
        raise AcceptanceRenderingError("unsupported machine facts schema_version")
    if machine_facts.get("workflow_state") != "APPROVAL_INPUT_READY":
        raise AcceptanceRenderingError("machine facts are not approval inputs")
    candidate = _mapping(machine_facts.get("candidate"), "machine_facts.candidate")
    if candidate.get("status") != "PACKAGE_CANDIDATE":
        raise AcceptanceRenderingError("automatic state must remain PACKAGE_CANDIDATE")
    if decision.get("decision_status") != "APPROVED_INPUT":
        raise AcceptanceRenderingError("decision_status must be APPROVED_INPUT")
    return candidate


def _validated_parties(
    decision: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    parties = {
        name: _mapping(decision.get(name), f"decision.{name}")
        for name in ("operator", "technical_reviewer", "delivery_approver", "recipient")
    }
    identities = []
    for name, party in parties.items():
        identities.append(
            _required_text(
                party.get("identity_reference"),
                f"decision.{name}.identity_reference",
            )
        )
        for field in ("organization", "department", "authorization_reference"):
            _required_text(party.get(field), f"decision.{name}.{field}")
    if len(set(identities)) != len(identities):
        raise AcceptanceRenderingError("all four role identities must be pairwise distinct")
    return parties


def _validated_deviations(decision: Mapping[str, object]) -> list[object]:
    deviations = decision.get("deviations")
    if not isinstance(deviations, list):
        raise AcceptanceRenderingError("decision.deviations must be an array")
    for index, raw in enumerate(deviations):
        deviation = _mapping(raw, f"decision.deviations[{index}]")
        if deviation.get("disposition") != "ACCEPTED_INTERNAL_ONLY":
            raise AcceptanceRenderingError(
                "PASS rendering permits only ACCEPTED_INTERNAL_ONLY deviations"
            )
        _required_text(
            deviation.get("approval_reference"),
            f"decision.deviations[{index}].approval_reference",
        )
    return deviations


def _validate_human_narratives(decision: Mapping[str, object]) -> None:
    _required_text(decision.get("delivery_id"), "decision.delivery_id")
    _required_text(decision.get("issue_url"), "decision.issue_url")
    for group_name in ("checklist_narratives", "delivery_note_narratives"):
        group = _mapping(decision.get(group_name), f"decision.{group_name}")
        for field, value in group.items():
            _required_text(value, f"decision.{group_name}.{field}")


def _validate_approval(
    name: str,
    approval: Mapping[str, object],
    *,
    party: Mapping[str, object],
    expected_common: Mapping[str, object],
    expected_sender: Mapping[str, object],
    expected_recipient: object,
    deviations: list[object],
    completed: datetime,
    frozen: datetime,
) -> None:
    label = f"decision.approvals.{name}"
    if approval.get("acknowledgement") != "ACKNOWLEDGED":
        raise AcceptanceRenderingError(f"{label} must be ACKNOWLEDGED")
    for field, expected in expected_common.items():
        if approval.get(field) != expected:
            raise AcceptanceRenderingError(
                f"{label}.{field} does not match the candidate"
            )
    if approval.get("identity_reference") != party.get("identity_reference"):
        raise AcceptanceRenderingError(
            f"{label}.identity_reference does not match its role"
        )
    if _plain(approval.get("sender")) != expected_sender:
        raise AcceptanceRenderingError(
            f"{label}.sender does not match the sender organization"
        )
    if _plain(approval.get("recipient")) != expected_recipient:
        raise AcceptanceRenderingError(f"{label}.recipient does not match the recipient")
    if _plain(approval.get("deviations")) != deviations:
        raise AcceptanceRenderingError(
            f"{label}.deviations must exactly preserve decision order"
        )
    acknowledged = _core._parse_utc(
        approval.get("acknowledged_at_utc"), f"{label}.acknowledged_at_utc"
    )
    if acknowledged <= completed or acknowledged <= frozen:
        raise AcceptanceRenderingError(
            f"{label}.acknowledged_at_utc must be strictly later "
            "than candidate completion and fact freeze"
        )
    identity = _required_text(
        approval.get("identity_reference"), f"{label}.identity_reference"
    )
    reference = _required_text(
        approval.get("approval_record_reference"),
        f"{label}.approval_record_reference",
    )
    if identity not in reference:
        raise AcceptanceRenderingError(
            f"{label}.approval_record_reference must bind identity"
        )
    _required_text(approval.get("statement"), f"{label}.statement")


def _validated_machine_facts_reference(
    machine_facts: Mapping[str, object], decision: Mapping[str, object]
) -> str:
    facts_sha256 = _sha256(_core.canonical_json_bytes(machine_facts))
    decision_facts = _mapping(decision.get("machine_facts"), "decision.machine_facts")
    if decision_facts.get("path") != MACHINE_FACTS_FILENAME:
        raise AcceptanceRenderingError(
            f"decision.machine_facts.path must be {MACHINE_FACTS_FILENAME}"
        )
    if decision_facts.get("sha256") != facts_sha256:
        raise AcceptanceRenderingError(
            "decision does not bind the machine facts bytes"
        )
    return facts_sha256


def _validate_all_approvals(
    machine_facts: Mapping[str, object],
    decision: Mapping[str, object],
    candidate: Mapping[str, object],
    parties: Mapping[str, Mapping[str, object]],
    deviations: list[object],
    facts_sha256: str,
) -> None:
    artifacts = _mapping(machine_facts.get("artifacts"), "machine_facts.artifacts")
    delivery_zip = _mapping(artifacts.get("delivery_zip"), "artifacts.delivery_zip")
    verifications = _mapping(
        machine_facts.get("verifications"), "machine_facts.verifications"
    )
    clean_room = _mapping(
        verifications.get("clean_room"),
        "machine_facts.verifications.clean_room",
    )
    expected_common = {
        "delivery_id": decision.get("delivery_id"),
        "source_commit": machine_facts.get("source_commit"),
        "archive_filename": PurePosixPath(str(delivery_zip.get("path"))).name,
        "archive_sha256": delivery_zip.get("sha256"),
        "candidate_status": "PACKAGE_CANDIDATE",
        "clean_room_status": clean_room.get("status"),
        "machine_facts_sha256": facts_sha256,
    }
    expected_sender = {
        "organization": parties["operator"].get("organization"),
        "department": parties["operator"].get("department"),
    }
    approvals = _mapping(decision.get("approvals"), "decision.approvals")
    completed = _core._parse_utc(
        candidate.get("completed_at_utc"),
        "machine_facts.candidate.completed_at_utc",
    )
    frozen = _core._parse_utc(
        candidate.get("frozen_at_utc"), "machine_facts.candidate.frozen_at_utc"
    )
    for name in APPROVAL_ROLES:
        approval = _mapping(approvals.get(name), f"decision.approvals.{name}")
        _validate_approval(
            name,
            approval,
            party=parties[PARTY_BY_APPROVAL[name]],
            expected_common=expected_common,
            expected_sender=expected_sender,
            expected_recipient=_plain(parties["recipient"]),
            deviations=deviations,
            completed=completed,
            frozen=frozen,
        )


def validate_approved_decision(
    machine_facts: Mapping[str, object],
    decision: Mapping[str, object],
) -> None:
    """Reject any approval input that is not bound to one immutable candidate."""
    _validate_schema(
        _plain(machine_facts),
        _core.MACHINE_FACTS_SCHEMA,
        "acceptance-machine-facts schema",
    )
    _validate_schema(_plain(decision), DECISION_SCHEMA, "acceptance-decision schema")
    candidate = _validated_candidate_state(machine_facts, decision)
    parties = _validated_parties(decision)
    _validate_human_narratives(decision)
    deviations = _validated_deviations(decision)
    _validate_all_approvals(
        machine_facts,
        decision,
        candidate,
        parties,
        deviations,
        _validated_machine_facts_reference(machine_facts, decision),
    )


def _selected(mapping: Mapping[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: _plain(mapping[field]) for field in fields if field in mapping}


def _record_artifacts(machine_facts: Mapping[str, object]) -> dict[str, object]:
    artifacts_raw = _mapping(machine_facts.get("artifacts"), "machine_facts.artifacts")
    allowed_artifacts = {
        "run_manifest",
        "ctest_junit",
        "benchmark_samples",
        "benchmark_summary",
        "evidence_summary",
        "canonical_markdown_report",
        "host_preflight",
        "runbook_log",
        "outcome_record",
        "source_commit_file",
        "sha256sums_file",
        "deterministic_package_record",
        "manifest_only_verifier_output",
        "clean_room_verifier_log",
        "delivery_zip",
        "presentation_pdf",
    }
    return {
        name: _selected(
            _mapping(raw, f"artifacts.{name}"),
            ("path", "size_bytes", "sha256"),
        )
        for name, raw in artifacts_raw.items()
        if name in allowed_artifacts
    }


def _record_controlled_host(
    machine_facts: Mapping[str, object],
) -> dict[str, object]:
    return _selected(
        _mapping(machine_facts.get("controlled_host"), "controlled_host"),
        (
            "controlled_host_id",
            "system",
            "architecture",
            "hostname",
            "cpu_vendor",
            "cpu_model",
            "physical_core_count",
            "logical_core_count",
            "total_memory_bytes",
            "preflight_sha256",
        ),
    )


def _record_toolchain(machine_facts: Mapping[str, object]) -> dict[str, object]:
    toolchain_raw = _mapping(machine_facts.get("toolchain"), "toolchain")
    openmp = _mapping(toolchain_raw.get("openmp"), "toolchain.openmp")
    toolchain = _selected(
        toolchain_raw,
        (
            "compiler",
            "compiler_version",
            "cmake_version",
            "ninja_version",
            "python_version",
            "git_version",
            "git_lfs_version",
        ),
    )
    toolchain["openmp_found"] = _plain(openmp.get("found"))
    toolchain["openmp_required"] = _plain(openmp.get("required"))
    return toolchain


def _record_execution(machine_facts: Mapping[str, object]) -> dict[str, object]:
    return _selected(
        _mapping(machine_facts.get("execution"), "execution"),
        (
            "status",
            "evidence_level",
            "report_intent",
            "preset",
            "warmup_count",
            "repeat_count",
            "amortization_count",
            "requested_thread_counts",
            "physical_core_thread_included",
            "omp_dynamic",
            "omp_proc_bind",
            "omp_places",
            "started_at_utc",
            "ended_at_utc",
        ),
    )


def _record_correctness(machine_facts: Mapping[str, object]) -> dict[str, object]:
    correctness_raw = _mapping(machine_facts.get("correctness"), "correctness")
    correctness = _selected(correctness_raw, ("status", "thresholds"))
    case_fields = (
        "status",
        "structure_equal",
        "values_finite",
        "scatter_indices_valid",
        "frobenius_relative_error",
        "maximum_absolute_error",
        "maximum_absolute_serial_entry",
        "maximum_absolute_error_tolerance",
        "maximum_absolute_error_within_tolerance",
        "displacement_relative_error",
        "relative_residual",
        "evidence_reference",
    )
    for name in ("tet4", "hex8"):
        correctness[name] = _selected(
            _mapping(correctness_raw.get(name), f"correctness.{name}"), case_fields
        )
    return correctness


def _record_performance(machine_facts: Mapping[str, object]) -> dict[str, object]:
    return _selected(
        _mapping(machine_facts.get("performance"), "performance"),
        (
            "status",
            "thresholds",
            "numeric_thread_count",
            "numeric_speedup",
            "numeric_coefficient_of_variation",
            "symbolic_thread_count",
            "symbolic_speedup",
            "symbolic_coefficient_of_variation",
            "raw_sample_count",
            "samples_sha256",
            "summary_sha256",
        ),
    )


def _record_verifications(
    machine_facts: Mapping[str, object], artifacts: Mapping[str, object]
) -> dict[str, object]:
    facts_verifications = _mapping(
        machine_facts.get("verifications"), "verifications"
    )

    def verification(name: str, artifact_name: str) -> dict[str, object]:
        raw = _mapping(facts_verifications.get(name), f"verifications.{name}")
        artifact = _mapping(artifacts.get(artifact_name), f"artifacts.{artifact_name}")
        return {
            "status": raw.get("status"),
            "evidence_reference": artifact.get("path"),
        }

    ctest = _selected(
        _mapping(machine_facts.get("ctest"), "ctest"),
        (
            "status",
            "test_count",
            "failed_count",
            "skipped_count",
            "not_run_count",
            "test_names",
            "evidence_reference",
        ),
    )
    return {
        "status": facts_verifications.get("status"),
        "source_and_input_identity": verification(
            "source_and_input_identity", "run_manifest"
        ),
        "ctest": ctest,
        "report_recomputation": verification(
            "report_recomputation", "benchmark_summary"
        ),
        "deterministic_package": verification(
            "deterministic_package", "deterministic_package_record"
        ),
        "manifest_only": verification(
            "manifest_only", "manifest_only_verifier_output"
        ),
        "clean_room": verification("clean_room", "clean_room_verifier_log"),
    }


def _record_approvals(decision: Mapping[str, object]) -> dict[str, object]:
    approvals_raw = _mapping(decision.get("approvals"), "decision.approvals")
    recipient = _mapping(decision.get("recipient"), "decision.recipient")
    approvals: dict[str, object] = {}
    for name in APPROVAL_ROLES:
        raw = _mapping(approvals_raw.get(name), f"decision.approvals.{name}")
        approvals[name] = _selected(
            raw,
            (
                "identity_reference",
                "acknowledgement",
                "acknowledged_at_utc",
                "approval_record_reference",
                "delivery_id",
                "source_commit",
                "archive_filename",
                "archive_sha256",
                "candidate_status",
                "clean_room_status",
                "machine_facts_sha256",
                "sender",
                "deviations",
                "statement",
            ),
        )
        approvals[name]["recipient"] = _selected(
            recipient, ("organization", "department", "identity_reference")
        )
    return approvals


def _record_acceptance_inputs(
    machine_facts: Mapping[str, object], decision: Mapping[str, object]
) -> dict[str, object]:
    facts_content = _core.canonical_json_bytes(machine_facts)
    decision_content = _core.canonical_json_bytes(decision)
    return {
        "machine_facts": {
            "path": MACHINE_FACTS_FILENAME,
            "size_bytes": len(facts_content),
            "sha256": _sha256(facts_content),
        },
        "decision": {
            "path": DECISION_FILENAME,
            "size_bytes": len(decision_content),
            "sha256": _sha256(decision_content),
        },
    }


def _record_from_inputs(
    machine_facts: Mapping[str, object], decision: Mapping[str, object]
) -> dict[str, object]:
    artifacts = _record_artifacts(machine_facts)
    return {
        "schema_version": RECORD_VERSION,
        "acceptance_inputs": _record_acceptance_inputs(machine_facts, decision),
        "delivery_id": decision.get("delivery_id"),
        "issue_url": decision.get("issue_url"),
        "source_commit": machine_facts.get("source_commit"),
        "distribution": machine_facts.get("distribution"),
        "recipient": _plain(decision.get("recipient")),
        "operator": _plain(decision.get("operator")),
        "technical_reviewer": _plain(decision.get("technical_reviewer")),
        "controlled_host": _record_controlled_host(machine_facts),
        "toolchain": _record_toolchain(machine_facts),
        "input": _selected(
            _mapping(machine_facts.get("input"), "input"),
            (
                "case",
                "repository_relative_path",
                "size_bytes",
                "sha256",
                "tracked",
                "materialized",
                "matches_head_lfs",
                "head_lfs_oid_sha256",
                "head_lfs_size_bytes",
            ),
        ),
        "execution": _record_execution(machine_facts),
        "correctness": _record_correctness(machine_facts),
        "performance": _record_performance(machine_facts),
        "artifacts": artifacts,
        "verifications": _record_verifications(machine_facts, artifacts),
        "deviations": _plain(decision.get("deviations")),
        "approvals": _record_approvals(decision),
        "status": "PASS",
    }


def _template_text(filename: str) -> str:
    path = Path(__file__).resolve().parent.parent / "packaging" / filename
    try:
        content = _core._read_regular_file_once(path, filename)
        text = content.decode("utf-8")
    except Exception as error:
        raise AcceptanceRenderingError(f"cannot read committed template {filename}: {error}") from error
    if "\r" in text:
        raise AcceptanceRenderingError(f"committed template {filename} must use LF")
    return text


def _replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise AcceptanceRenderingError(f"template field {prefix!r} must occur once")
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _replace_checkbox_block(
    text: str, selector: str, values: tuple[str, ...]
) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("- [")]
    matches: list[tuple[int, int]] = []
    for start in starts:
        end = start + 1
        while end < len(lines) and lines[end].startswith("  "):
            end += 1
        block = "\n".join(lines[start:end])
        if selector in block and PLACEHOLDER in block:
            matches.append((start, end))
    if len(matches) != 1:
        raise AcceptanceRenderingError(
            f"checklist selector {selector!r} matched {len(matches)} blocks"
        )
    start, end = matches[0]
    block = "\n".join(lines[start:end])
    if block.count(PLACEHOLDER) != len(values):
        raise AcceptanceRenderingError(
            f"checklist selector {selector!r} has unexpected value slots"
        )
    block = block.replace("- [ ] ", "- [x] ", 1)
    for value in values:
        if "\n" in value or "\r" in value:
            raise AcceptanceRenderingError(
                f"checklist selector {selector!r} has an unsafe value"
            )
        block = block.replace(PLACEHOLDER, value, 1)
    lines[start:end] = block.splitlines()
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _checklist_objective_artifacts(
    record: Mapping[str, object],
) -> dict[str, tuple[str, str]]:
    return {
        name: _artifact(record, name)
        for name in (
            "run_manifest",
            "ctest_junit",
            "benchmark_samples",
            "benchmark_summary",
            "evidence_summary",
            "canonical_markdown_report",
            "delivery_zip",
            "host_preflight",
            "outcome_record",
            "source_commit_file",
            "sha256sums_file",
            "deterministic_package_record",
            "manifest_only_verifier_output",
            "clean_room_verifier_log",
            "runbook_log",
        )
    }


def _fill_checklist_objective_values(
    text: str,
    record: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative_path: str,
    record_sha256: str,
) -> str:
    values = _canonical_objective_checklist_values(
        record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative=record_relative_path,
        record_sha256=record_sha256,
        objective_artifacts=_checklist_objective_artifacts(record),
        validation_status="PASS",
    )
    for selector, value in values.items():
        text = _replace_checkbox_block(text, selector, (value,))
    return text


def _fill_checklist_narratives(
    text: str, decision: Mapping[str, object]
) -> str:
    narratives = _mapping(decision.get("checklist_narratives"), "checklist_narratives")
    narrative_selectors = {
        "authorization_and_recipient_scope": "授权与接收方范围已由仓库所有者书面确认",
        "no_public_license_acknowledgement": "已确认当前无公开许可证",
        "host_load_and_frequency_policy": "测试期间主机负载和频率策略",
        "solver_flow_scope_acknowledgement": "复核人理解：位移测试",
        "known_limitations_and_non_goals": "已知限制与非目标",
        "unresolved_blockers": "未解决 blocker",
        "rollback_and_reproduction_path": "回滚与复现路径",
        "final_decision_rationale": "最终决定理由",
    }
    for field, selector in narrative_selectors.items():
        text = _replace_checkbox_block(
            text, selector, (_required_text(narratives.get(field), field),)
        )
    return text


def _fill_checklist_party_bindings(
    text: str,
    record: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
) -> str:
    recipient = _mapping(record.get("recipient"), "record.recipient")
    fixed = {
        "交付 ID：": str(record["delivery_id"]),
        "Issue #44 URL：": str(record["issue_url"]),
        "Demo 版本：": _canonical_demo_version(record, archive_name),
        "完整源码 SHA：": str(record["source_commit"]),
        "候选源码 ZIP 文件名及 SHA-256：": f"{archive_name}` `{archive_sha256}",
        "接收组织及部门：": (
            f"{recipient['organization']}` / `{recipient['department']}"
        ),
        "指定接收人身份引用：": str(recipient["identity_reference"]),
    }
    for selector, value in fixed.items():
        text = _replace_checkbox_block(text, selector, (value,))
    approvals = _mapping(record.get("approvals"), "record.approvals")
    approval_selectors = {
        "operator": "操作员：",
        "technical_reviewer": "技术复核人：",
        "delivery_approver": "交付批准人：",
        "recipient_acknowledgement": "接收方确认：",
    }
    for name, selector in approval_selectors.items():
        approval = _mapping(approvals.get(name), f"approvals.{name}")
        text = _replace_checkbox_block(
            text,
            selector,
            tuple(
                str(approval[field])
                for field in (
                    "identity_reference",
                    "acknowledged_at_utc",
                    "approval_record_reference",
                )
            ),
        )
    return text


def _complete_checklist(
    text: str, *, record_relative_path: str, record_sha256: str, archive_sha256: str
) -> str:
    text = text.replace(
        "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PENDING",
        "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS",
        1,
    ).replace("当前决定：`PENDING`", "当前决定：`PASS`", 1)
    text = _replace_line(text, "最终状态：", "最终状态：`PASS`")
    text = _replace_line(
        text,
        "最终验收记录文件：",
        f"最终验收记录文件：`{record_relative_path}` `{record_sha256}`",
    )
    text = _replace_line(
        text, "最终 ZIP SHA-256：", f"最终 ZIP SHA-256：`{archive_sha256}`"
    )
    if PLACEHOLDER in text or "- [ ]" in text:
        raise AcceptanceRenderingError("canonical checklist still contains an unfilled slot")
    return text


def _render_checklist(
    record: dict[str, object],
    decision: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative_path: str,
    record_sha256: str,
) -> bytes:
    text = _template_text(CHECKLIST_TEMPLATE)
    text = _fill_checklist_objective_values(
        text,
        record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative_path=record_relative_path,
        record_sha256=record_sha256,
    )
    text = _fill_checklist_narratives(text, decision)
    text = _fill_checklist_party_bindings(
        text,
        record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
    )
    return _complete_checklist(
        text,
        record_relative_path=record_relative_path,
        record_sha256=record_sha256,
        archive_sha256=archive_sha256,
    ).encode("utf-8")


def _delivery_note_objective_artifacts(
    record: Mapping[str, object],
) -> dict[str, tuple[str, str]]:
    return {
        name: _artifact(record, name)
        for name in (
            "run_manifest",
            "canonical_markdown_report",
            "delivery_zip",
            "host_preflight",
            "source_commit_file",
            "sha256sums_file",
            "deterministic_package_record",
            "manifest_only_verifier_output",
            "clean_room_verifier_log",
            "runbook_log",
        )
    }


def _delivery_note_identity_rows(
    record: Mapping[str, object], archive_name: str
) -> dict[str, str]:
    operator = _mapping(record.get("operator"), "record.operator")
    recipient = _mapping(record.get("recipient"), "record.recipient")
    return {
        "| 交付 ID |": f"| 交付 ID | **{record['delivery_id']}** |",
        "| 交付日期（UTC） |": (
            f"| 交付日期（UTC） | **{_canonical_delivery_date_utc(record)}** |"
        ),
        "| Demo 版本 |": (
            f"| Demo 版本 | **{_canonical_demo_version(record, archive_name)}** |"
        ),
        "| Issue #44 URL |": f"| Issue #44 URL | **{record['issue_url']}** |",
        "| 发送组织/部门 |": (
            f"| 发送组织/部门 | **{operator['organization']} / "
            f"{operator['department']}** |"
        ),
        "| 接收组织/部门 |": (
            f"| 接收组织/部门 | **{recipient['organization']} / "
            f"{recipient['department']}** |"
        ),
        "| 指定接收人身份引用 |": (
            f"| 指定接收人身份引用 | **{recipient['identity_reference']}** |"
        ),
        "| 完整源码 SHA |": f"| 完整源码 SHA | **{record['source_commit']}** |",
    }


def _delivery_note_artifact_rows(
    objective_artifacts: Mapping[str, tuple[str, str]],
    *,
    record_relative_path: str,
    record_sha256: str,
    checklist_relative_path: str,
    checklist_sha256: str,
) -> dict[str, str]:
    rows: dict[str, str] = {}
    artifact_rows = {
        "| 正式源码 ZIP |": "delivery_zip",
        "| 原始证据目录/manifest |": "run_manifest",
        "| 规范 Markdown 报告 |": "canonical_markdown_report",
        "| `host-preflight.txt` |": "host_preflight",
        "| `SOURCE_COMMIT` |": "source_commit_file",
        "| `SHA256SUMS` |": "sha256sums_file",
        "| `deterministic-package.txt` |": "deterministic_package_record",
        "| manifest-only verifier 输出 |": "manifest_only_verifier_output",
        "| `clean-room-verification.log` |": "clean_room_verifier_log",
    }
    for prefix, artifact_name in artifact_rows.items():
        path, digest = objective_artifacts[artifact_name]
        label = prefix.rstrip("|").rstrip()
        rows[prefix] = f"{label}| **{path}** | **{digest}** |"
    rows["| 机器可读验收记录 |"] = (
        f"| 机器可读验收记录 | **{record_relative_path}** | **{record_sha256}** |"
    )
    rows["| 完成版验收清单 |"] = (
        f"| 完成版验收清单 | **{checklist_relative_path}** | "
        f"**{checklist_sha256}** |"
    )
    return rows


def _delivery_note_approval_rows(record: Mapping[str, object]) -> dict[str, str]:
    approvals = _mapping(record.get("approvals"), "record.approvals")
    rows: dict[str, str] = {}
    approval_rows = {
        "operator": "| 操作员 |",
        "technical_reviewer": "| 技术复核人 |",
        "delivery_approver": "| 发送方批准/交付批准人 |",
        "recipient_acknowledgement": "| 接收方确认 |",
    }
    for name, prefix in approval_rows.items():
        approval = _mapping(approvals.get(name), f"approvals.{name}")
        label = prefix.rstrip("|").rstrip()
        rows[prefix] = (
            f"{label}| **{approval['identity_reference']}** | "
            f"**{approval['acknowledged_at_utc']}** | "
            f"**{approval['approval_record_reference']}** | "
            f"**{approval['acknowledgement']}** |"
        )
    return rows


def _fill_delivery_note_narratives(
    text: str, decision: Mapping[str, object]
) -> str:
    narratives = _mapping(
        decision.get("delivery_note_narratives"), "delivery_note_narratives"
    )
    narrative_lines = {
        "交付目的与允许使用范围：": "delivery_purpose_and_authorized_scope",
        "授权文件或内部审批引用：": "authorization_reference",
        "最终包含项核对：": "included_items_confirmation",
        "最终排除项核对：": "excluded_items_confirmation",
        "已知限制：": "known_limitations",
        "未解决风险（无风险也必须填写“无”）：": "unresolved_risks",
        "回滚负责人及联系引用：": "rollback_owner_and_contact",
        "撤回/替换流程引用：": "withdrawal_or_replacement_process",
        "发送方批准声明：": "sender_approval_statement",
        "接收方确认声明：": "recipient_acknowledgement_statement",
    }
    for prefix, field in narrative_lines.items():
        value = _required_text(narratives.get(field), field)
        text = _replace_line(text, prefix, f"{prefix}**{value}**")
    return text


def _delivery_note_scalar_lines(
    record: Mapping[str, object],
    objective_artifacts: Mapping[str, tuple[str, str]],
    *,
    archive_sha256: str,
    record_relative_path: str,
) -> dict[str, str]:
    controlled_host = _mapping(record.get("controlled_host"), "controlled_host")
    input_facts = _mapping(record.get("input"), "input")
    verification_summary = _canonical_verification_summary(
        record,
        {
            name: objective_artifacts[name]
            for name in (
                "deterministic_package_record",
                "manifest_only_verifier_output",
                "clean_room_verifier_log",
            )
        },
    )
    return {
        "证据 SHA-256：": f"证据 SHA-256：**{objective_artifacts['run_manifest'][1]}**",
        "报告 SHA-256：": (
            "报告 SHA-256：**"
            f"{objective_artifacts['canonical_markdown_report'][1]}**"
        ),
        "ZIP SHA-256：": f"ZIP SHA-256：**{archive_sha256}**",
        "可选 PDF 路径及 SHA-256：": (
            "可选 PDF 路径及 SHA-256：**"
            f"{_canonical_presentation_pdf_binding(record)}**"
        ),
        "机器可读验收记录路径：": (
            f"机器可读验收记录路径：**{record_relative_path}**"
        ),
        "正式验收状态（只能为 `PASS`）：": "正式验收状态（只能为 `PASS`）：**PASS**",
        "正确性门槛摘要：": (
            f"正确性门槛摘要：**{_canonical_correctness_summary(record)}**"
        ),
        "性能门槛摘要：": (
            f"性能门槛摘要：**{_canonical_performance_summary(record)}**"
        ),
        "确定性打包与 clean-room 结果：": (
            f"确定性打包与 clean-room 结果：**{verification_summary}**"
        ),
        "偏差及批准引用（无偏差也必须填写“无”）：": (
            "偏差及批准引用（无偏差也必须填写“无”）："
            f"**{_canonical_deviation_summary(record)}**"
        ),
        "复现所需完整源码 SHA：": (
            f"复现所需完整源码 SHA：**{record['source_commit']}**"
        ),
        "受控主机 ID：": (
            f"受控主机 ID：**{controlled_host['controlled_host_id']}**"
        ),
        "输入 SHA-256 与字节数：": (
            f"输入 SHA-256 与字节数：**{input_facts['sha256']}** / "
            f"**{input_facts['size_bytes']} bytes**"
        ),
        "完整复现命令/记录位置：": (
            "完整复现命令/记录位置："
            f"**{objective_artifacts['runbook_log'][0]}** / "
            f"**{objective_artifacts['runbook_log'][1]}**"
        ),
    }


def _render_delivery_note(
    record: dict[str, object],
    decision: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative_path: str,
    record_sha256: str,
    checklist_relative_path: str,
    checklist_sha256: str,
) -> bytes:
    text = _template_text(DELIVERY_NOTE_TEMPLATE).replace(
        "CSC3_DELIVERY_NOTE_STATUS=PENDING", "CSC3_DELIVERY_NOTE_STATUS=PASS", 1
    )
    objective_artifacts = _delivery_note_objective_artifacts(record)
    table_lines = _delivery_note_identity_rows(record, archive_name)
    table_lines.update(
        _delivery_note_artifact_rows(
            objective_artifacts,
            record_relative_path=record_relative_path,
            record_sha256=record_sha256,
            checklist_relative_path=checklist_relative_path,
            checklist_sha256=checklist_sha256,
        )
    )
    table_lines.update(_delivery_note_approval_rows(record))
    for prefix, replacement in table_lines.items():
        text = _replace_line(text, prefix, replacement)
    text = _fill_delivery_note_narratives(text, decision)
    for prefix, replacement in _delivery_note_scalar_lines(
        record,
        objective_artifacts,
        archive_sha256=archive_sha256,
        record_relative_path=record_relative_path,
    ).items():
        text = _replace_line(text, prefix, replacement)
    if PLACEHOLDER in text:
        raise AcceptanceRenderingError(
            "canonical delivery note still contains an unfilled slot"
        )
    return text.encode("utf-8")


def render_acceptance_bytes(
    machine_facts: Mapping[str, object],
    decision: Mapping[str, object],
    *,
    record_relative_path: str,
    checklist_relative_path: str,
) -> RenderedAcceptance:
    """Return byte-stable v2 record, checklist, and delivery note content."""
    record_relative_path = _safe_relative(record_relative_path, "acceptance record")
    checklist_relative_path = _safe_relative(
        checklist_relative_path, "acceptance checklist"
    )
    if record_relative_path == checklist_relative_path:
        raise AcceptanceRenderingError("record and checklist paths must be distinct")
    validate_approved_decision(machine_facts, decision)
    record = _record_from_inputs(machine_facts, decision)
    _validate_schema(record, RECORD_SCHEMA, "acceptance-record schema")
    record_content = _core.canonical_json_bytes(record)
    delivery_zip = _mapping(
        _mapping(record.get("artifacts"), "artifacts").get("delivery_zip"),
        "artifacts.delivery_zip",
    )
    archive_name = PurePosixPath(str(delivery_zip.get("path"))).name
    archive_sha256 = str(delivery_zip.get("sha256"))
    checklist_content = _render_checklist(
        record,
        decision,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative_path=record_relative_path,
        record_sha256=_sha256(record_content),
    )
    delivery_note_content = _render_delivery_note(
        record,
        decision,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative_path=record_relative_path,
        record_sha256=_sha256(record_content),
        checklist_relative_path=checklist_relative_path,
        checklist_sha256=_sha256(checklist_content),
    )
    return RenderedAcceptance(
        record_content=record_content,
        checklist_content=checklist_content,
        delivery_note_content=delivery_note_content,
    )


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _run_root_relative(path: Path, run_root: Path, label: str) -> str:
    try:
        relative = path.relative_to(run_root).as_posix()
    except ValueError as error:
        raise AcceptanceRenderingError(f"{label} must be inside --run-root") from error
    return _safe_relative(relative, label)


@dataclass(frozen=True)
class _RenderPaths:
    run_root: Path
    archive_path: Path
    facts_path: Path
    decision_path: Path
    record_path: Path
    checklist_path: Path
    delivery_note_path: Path
    output_directory: Path
    publication_parent: Path
    record_relative: str
    checklist_relative: str


@dataclass(frozen=True)
class _CanonicalInputs:
    facts_content: bytes
    decision_content: bytes
    facts: Mapping[str, object]
    decision: Mapping[str, object]
    frozen_at_utc: str


def _normalized_render_paths(
    run_root: Path,
    archive_path: Path,
    machine_facts_path: Path,
    decision_path: Path,
    record_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
) -> _RenderPaths:
    run_root = _lexical_absolute(Path(run_root))
    facts_path = _lexical_absolute(Path(machine_facts_path))
    decision_path = _lexical_absolute(Path(decision_path))
    record_path = _lexical_absolute(Path(record_path))
    checklist_path = _lexical_absolute(Path(checklist_path))
    delivery_note_path = _lexical_absolute(Path(delivery_note_path))
    if facts_path.name != MACHINE_FACTS_FILENAME:
        raise AcceptanceRenderingError(
            f"machine facts input must be named {MACHINE_FACTS_FILENAME}"
        )
    if decision_path.name != DECISION_FILENAME:
        raise AcceptanceRenderingError(
            f"decision input must be named {DECISION_FILENAME}"
        )
    if len({record_path, checklist_path, delivery_note_path}) != 3:
        raise AcceptanceRenderingError("the three rendered outputs must be distinct")
    if record_path.parent != checklist_path.parent or (
        record_path.parent != delivery_note_path.parent
    ):
        raise AcceptanceRenderingError(
            "the three rendered outputs must share one parent"
        )
    output_directory = record_path.parent
    return _RenderPaths(
        run_root=run_root,
        archive_path=Path(archive_path),
        facts_path=facts_path,
        decision_path=decision_path,
        record_path=record_path,
        checklist_path=checklist_path,
        delivery_note_path=delivery_note_path,
        output_directory=output_directory,
        publication_parent=output_directory.parent,
        record_relative=_run_root_relative(
            record_path, run_root, "acceptance record"
        ),
        checklist_relative=_run_root_relative(
            checklist_path, run_root, "acceptance checklist"
        ),
    )


def _load_canonical_inputs(paths: _RenderPaths) -> _CanonicalInputs:
    facts_content = _core._read_regular_file_once(paths.facts_path, "machine facts")
    decision_content = _core._read_regular_file_once(paths.decision_path, "decision")
    facts = _core._strict_json(facts_content, "machine facts")
    decision = _core._strict_json(decision_content, "decision")
    if not isinstance(facts, Mapping) or not isinstance(decision, Mapping):
        raise AcceptanceRenderingError("machine facts and decision must be JSON objects")
    if facts_content != _core.canonical_json_bytes(facts):
        raise AcceptanceRenderingError("machine facts must use canonical JSON bytes")
    if decision_content != _core.canonical_json_bytes(decision):
        raise AcceptanceRenderingError("decision must use canonical JSON bytes")
    candidate = _mapping(facts.get("candidate"), "machine_facts.candidate")
    frozen_at_utc = candidate.get("frozen_at_utc")
    if not isinstance(frozen_at_utc, str):
        raise AcceptanceRenderingError("machine facts lack frozen_at_utc")
    return _CanonicalInputs(
        facts_content=facts_content,
        decision_content=decision_content,
        facts=facts,
        decision=decision,
        frozen_at_utc=frozen_at_utc,
    )


def _verify_staged_outputs(
    staging_descriptor: int,
    paths: _RenderPaths,
    rendered: RenderedAcceptance,
) -> None:
    for filename, expected in (
        (paths.record_path.name, rendered.record_content),
        (paths.checklist_path.name, rendered.checklist_content),
        (paths.delivery_note_path.name, rendered.delivery_note_content),
    ):
        actual = _preparer._read_regular_file_at(staging_descriptor, filename)
        if actual != expected:
            raise AcceptanceRenderingError(
                f"staged rendered output changed: {filename}"
            )
        if filename == paths.record_path.name:
            staged_record = _core._strict_json(actual, "staged acceptance record")
            _validate_schema(
                staged_record, RECORD_SCHEMA, "staged acceptance-record schema"
            )


def _publish_rendered_outputs(
    parent_descriptor: int,
    paths: _RenderPaths,
    rendered: RenderedAcceptance,
) -> None:
    staging_name, staging_descriptor = _preparer._create_staging_directory(
        parent_descriptor,
        paths.output_directory.name,
        AcceptanceRenderingError,
    )
    staged_names = (
        paths.record_path.name,
        paths.checklist_path.name,
        paths.delivery_note_path.name,
    )
    published = False
    try:
        for filename, content in (
            (paths.record_path.name, rendered.record_content),
            (paths.checklist_path.name, rendered.checklist_content),
            (paths.delivery_note_path.name, rendered.delivery_note_content),
        ):
            _write_fsynced_at(staging_descriptor, filename, content)
        os.fsync(staging_descriptor)
        _verify_staged_outputs(staging_descriptor, paths, rendered)
        if not _preparer._directory_entry_matches_descriptor(
            parent_descriptor, staging_name, staging_descriptor
        ):
            raise AcceptanceRenderingError(
                "private render staging directory changed before publication"
            )
        _preparer._assert_publication_parent_unchanged(
            paths.publication_parent,
            parent_descriptor,
            AcceptanceRenderingError,
        )
        _preparer._atomic_publish_directory_no_replace(
            parent_descriptor,
            staging_name,
            paths.output_directory.name,
            AcceptanceRenderingError,
        )
        published = True
        os.fsync(parent_descriptor)
    finally:
        try:
            if not published:
                _preparer._cleanup_staging_directory(
                    parent_descriptor,
                    staging_name,
                    staging_descriptor,
                    staged_names,
                )
        finally:
            os.close(staging_descriptor)


def _render_result(
    paths: _RenderPaths,
    inputs: _CanonicalInputs,
    rendered: RenderedAcceptance,
    archive_content: bytes,
) -> dict[str, object]:
    return {
        "status": "PASS",
        "record": str(paths.record_path),
        "record_sha256": _sha256(rendered.record_content),
        "checklist": str(paths.checklist_path),
        "checklist_sha256": _sha256(rendered.checklist_content),
        "delivery_note": str(paths.delivery_note_path),
        "delivery_note_sha256": _sha256(rendered.delivery_note_content),
        "machine_facts_sha256": _sha256(inputs.facts_content),
        "decision_sha256": _sha256(inputs.decision_content),
        "archive_sha256": _sha256(archive_content),
    }


def render_acceptance_inputs(
    run_root: Path,
    archive_path: Path,
    machine_facts_path: Path,
    decision_path: Path,
    record_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
) -> dict[str, object]:
    """Revalidate one immutable candidate and atomically publish all three outputs."""
    if not _preparer.SECURE_CANDIDATE_CAPTURE_SUPPORTED:
        raise AcceptanceRenderingError(
            "this platform lacks secure candidate capture and atomic publication"
        )
    paths = _normalized_render_paths(
        run_root,
        archive_path,
        machine_facts_path,
        decision_path,
        record_path,
        checklist_path,
        delivery_note_path,
    )
    inputs = _load_canonical_inputs(paths)
    parent_descriptor = _preparer._open_anchored_directory(
        paths.publication_parent, AcceptanceRenderingError
    )
    try:
        _preparer._assert_output_absent(
            parent_descriptor,
            paths.output_directory.name,
            paths.output_directory,
            AcceptanceRenderingError,
        )
        with _core.validated_candidate_snapshot(
            paths.run_root,
            paths.archive_path,
            frozen_at_utc=inputs.frozen_at_utc,
        ) as snapshot:
            if inputs.facts_content != snapshot.machine_facts_content:
                raise AcceptanceRenderingError(
                    "machine facts bytes differ from the immutable candidate snapshot"
                )
            rendered = render_acceptance_bytes(
                snapshot.machine_facts,
                inputs.decision,
                record_relative_path=paths.record_relative,
                checklist_relative_path=paths.checklist_relative,
            )
            _publish_rendered_outputs(parent_descriptor, paths, rendered)
            return _render_result(
                paths, inputs, rendered, snapshot.archive_content
            )
    finally:
        os.close(parent_descriptor)
