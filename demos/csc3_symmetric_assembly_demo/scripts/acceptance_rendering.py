#!/usr/bin/env python3
"""根据已填写的决定和机器事实生成固定格式的验收文件。

输出包括验收记录、完成版检查清单和交付说明。三份文件都取自同一份快照，便于
后续重新计算摘要并发现手工改动。
"""

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
DEVIATION_IDENTIFIER_GRAMMAR = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"
DEVIATION_IDENTIFIER_PATTERN = re.compile(DEVIATION_IDENTIFIER_GRAMMAR)
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
CHECKLIST_STATUS_TOKEN = "{{CSC3_CHECKLIST_STATUS_MARKER}}"
CHECKLIST_DECISION_TOKEN = "{{CSC3_CHECKLIST_DECISION}}"
DELIVERY_NOTE_STATUS_TOKEN = "{{CSC3_DELIVERY_NOTE_STATUS_MARKER}}"
CHECKLIST_OBJECTIVE_TOKENS = {
    "distribution": "{{CSC3_CHECKLIST_DISTRIBUTION_ITEM}}",
    "complete_checkout": "{{CSC3_CHECKLIST_COMPLETE_CHECKOUT_ITEM}}",
    "source_head": "{{CSC3_CHECKLIST_SOURCE_HEAD_ITEM}}",
    "clean_worktree": "{{CSC3_CHECKLIST_CLEAN_WORKTREE_ITEM}}",
    "input_path": "{{CSC3_CHECKLIST_INPUT_PATH_ITEM}}",
    "lfs_materialized": "{{CSC3_CHECKLIST_LFS_MATERIALIZED_ITEM}}",
    "input_size": "{{CSC3_CHECKLIST_INPUT_SIZE_ITEM}}",
    "input_sha256": "{{CSC3_CHECKLIST_INPUT_SHA256_ITEM}}",
    "controlled_host_id": "{{CSC3_CHECKLIST_CONTROLLED_HOST_ID_ITEM}}",
    "physical_linux_intel": "{{CSC3_CHECKLIST_PHYSICAL_LINUX_INTEL_ITEM}}",
    "host_preflight": "{{CSC3_CHECKLIST_HOST_PREFLIGHT_ITEM}}",
    "toolchain_versions": "{{CSC3_CHECKLIST_TOOLCHAIN_VERSIONS_ITEM}}",
    "openmp_environment": "{{CSC3_CHECKLIST_OPENMP_ENVIRONMENT_ITEM}}",
    "thread_set": "{{CSC3_CHECKLIST_THREAD_SET_ITEM}}",
    "benchmark_counts": "{{CSC3_CHECKLIST_BENCHMARK_COUNTS_ITEM}}",
    "ctest": "{{CSC3_CHECKLIST_CTEST_ITEM}}",
    "csc3_structure": "{{CSC3_CHECKLIST_CSC3_STRUCTURE_ITEM}}",
    "frobenius_error": "{{CSC3_CHECKLIST_FROBENIUS_ERROR_ITEM}}",
    "maximum_absolute_error": "{{CSC3_CHECKLIST_MAXIMUM_ABSOLUTE_ERROR_ITEM}}",
    "displacement_error": "{{CSC3_CHECKLIST_DISPLACEMENT_ERROR_ITEM}}",
    "relative_residual": "{{CSC3_CHECKLIST_RELATIVE_RESIDUAL_ITEM}}",
    "benchmark_samples": "{{CSC3_CHECKLIST_BENCHMARK_SAMPLES_ITEM}}",
    "benchmark_summary": "{{CSC3_CHECKLIST_BENCHMARK_SUMMARY_ITEM}}",
    "numeric_speedup": "{{CSC3_CHECKLIST_NUMERIC_SPEEDUP_ITEM}}",
    "symbolic_speedup": "{{CSC3_CHECKLIST_SYMBOLIC_SPEEDUP_ITEM}}",
    "coefficient_of_variation": "{{CSC3_CHECKLIST_COEFFICIENT_OF_VARIATION_ITEM}}",
    "timing_coverage": "{{CSC3_CHECKLIST_TIMING_COVERAGE_ITEM}}",
    "no_ci_timing": "{{CSC3_CHECKLIST_NO_CI_TIMING_ITEM}}",
    "run_manifest": "{{CSC3_CHECKLIST_RUN_MANIFEST_ITEM}}",
    "staged_identity_checks": "{{CSC3_CHECKLIST_STAGED_IDENTITY_CHECKS_ITEM}}",
    "report_recomputation": "{{CSC3_CHECKLIST_REPORT_RECOMPUTATION_ITEM}}",
    "report_source_binding": "{{CSC3_CHECKLIST_REPORT_SOURCE_BINDING_ITEM}}",
    "evidence_hashes": "{{CSC3_CHECKLIST_EVIDENCE_HASHES_ITEM}}",
    "source_commit_file": "{{CSC3_CHECKLIST_SOURCE_COMMIT_FILE_ITEM}}",
    "candidate_status": "{{CSC3_CHECKLIST_CANDIDATE_STATUS_ITEM}}",
    "checksums_coverage": "{{CSC3_CHECKLIST_CHECKSUMS_COVERAGE_ITEM}}",
    "deterministic_package": "{{CSC3_CHECKLIST_DETERMINISTIC_PACKAGE_ITEM}}",
    "manifest_only": "{{CSC3_CHECKLIST_MANIFEST_ONLY_ITEM}}",
    "clean_room": "{{CSC3_CHECKLIST_CLEAN_ROOM_ITEM}}",
    "standalone_validator": "{{CSC3_CHECKLIST_STANDALONE_VALIDATOR_ITEM}}",
    "finalizer_contract": "{{CSC3_CHECKLIST_FINALIZER_CONTRACT_ITEM}}",
    "markdown_authority": "{{CSC3_CHECKLIST_MARKDOWN_AUTHORITY_ITEM}}",
    "deviations": "{{CSC3_CHECKLIST_DEVIATIONS_ITEM}}",
    "final_decision": "{{CSC3_CHECKLIST_FINAL_DECISION_ITEM}}",
}
CHECKLIST_NARRATIVE_TOKENS = {
    "authorization_and_recipient_scope": "{{CSC3_CHECKLIST_AUTHORIZATION_SCOPE_ITEM}}",
    "no_public_license_acknowledgement": "{{CSC3_CHECKLIST_NO_PUBLIC_LICENSE_ITEM}}",
    "host_load_and_frequency_policy": "{{CSC3_CHECKLIST_HOST_POLICY_ITEM}}",
    "solver_flow_scope_acknowledgement": "{{CSC3_CHECKLIST_SOLVER_SCOPE_ITEM}}",
    "known_limitations_and_non_goals": "{{CSC3_CHECKLIST_KNOWN_LIMITATIONS_ITEM}}",
    "unresolved_blockers": "{{CSC3_CHECKLIST_UNRESOLVED_BLOCKERS_ITEM}}",
    "rollback_and_reproduction_path": "{{CSC3_CHECKLIST_ROLLBACK_PATH_ITEM}}",
    "final_decision_rationale": "{{CSC3_CHECKLIST_DECISION_RATIONALE_ITEM}}",
}
CHECKLIST_PARTY_TOKENS = {
    "delivery_id": "{{CSC3_CHECKLIST_DELIVERY_ID_ITEM}}",
    "issue_url": "{{CSC3_CHECKLIST_ISSUE_URL_ITEM}}",
    "demo_version": "{{CSC3_CHECKLIST_DEMO_VERSION_ITEM}}",
    "source_commit": "{{CSC3_CHECKLIST_SOURCE_COMMIT_ITEM}}",
    "archive_binding": "{{CSC3_CHECKLIST_ARCHIVE_BINDING_ITEM}}",
    "recipient_organization": "{{CSC3_CHECKLIST_RECIPIENT_ORGANIZATION_ITEM}}",
    "recipient_identity": "{{CSC3_CHECKLIST_RECIPIENT_IDENTITY_ITEM}}",
}
CHECKLIST_APPROVAL_TOKENS = {
    "operator": "{{CSC3_CHECKLIST_OPERATOR_APPROVAL_ITEM}}",
    "technical_reviewer": "{{CSC3_CHECKLIST_REVIEWER_APPROVAL_ITEM}}",
    "delivery_approver": "{{CSC3_CHECKLIST_APPROVER_APPROVAL_ITEM}}",
    "recipient_acknowledgement": "{{CSC3_CHECKLIST_RECIPIENT_APPROVAL_ITEM}}",
}
CHECKLIST_FINAL_TOKENS = {
    "status": "{{CSC3_CHECKLIST_FINAL_STATUS_LINE}}",
    "record": "{{CSC3_CHECKLIST_FINAL_RECORD_LINE}}",
    "archive_sha256": "{{CSC3_CHECKLIST_FINAL_ARCHIVE_SHA256_LINE}}",
}
DELIVERY_NOTE_IDENTITY_TOKENS = {
    "delivery_id": "{{CSC3_DELIVERY_NOTE_DELIVERY_ID_ROW}}",
    "delivery_date": "{{CSC3_DELIVERY_NOTE_DELIVERY_DATE_ROW}}",
    "demo_version": "{{CSC3_DELIVERY_NOTE_DEMO_VERSION_ROW}}",
    "issue_url": "{{CSC3_DELIVERY_NOTE_ISSUE_URL_ROW}}",
    "sender": "{{CSC3_DELIVERY_NOTE_SENDER_ROW}}",
    "recipient": "{{CSC3_DELIVERY_NOTE_RECIPIENT_ROW}}",
    "recipient_identity": "{{CSC3_DELIVERY_NOTE_RECIPIENT_IDENTITY_ROW}}",
    "source_commit": "{{CSC3_DELIVERY_NOTE_SOURCE_COMMIT_ROW}}",
}
DELIVERY_NOTE_ARTIFACT_TOKENS = {
    "delivery_zip": "{{CSC3_DELIVERY_NOTE_ARCHIVE_ROW}}",
    "run_manifest": "{{CSC3_DELIVERY_NOTE_RUN_MANIFEST_ROW}}",
    "canonical_markdown_report": "{{CSC3_DELIVERY_NOTE_REPORT_ROW}}",
    "host_preflight": "{{CSC3_DELIVERY_NOTE_HOST_PREFLIGHT_ROW}}",
    "source_commit_file": "{{CSC3_DELIVERY_NOTE_SOURCE_COMMIT_FILE_ROW}}",
    "sha256sums_file": "{{CSC3_DELIVERY_NOTE_SHA256SUMS_ROW}}",
    "deterministic_package_record": "{{CSC3_DELIVERY_NOTE_DETERMINISTIC_PACKAGE_ROW}}",
    "manifest_only_verifier_output": "{{CSC3_DELIVERY_NOTE_MANIFEST_ONLY_ROW}}",
    "clean_room_verifier_log": "{{CSC3_DELIVERY_NOTE_CLEAN_ROOM_ROW}}",
    "acceptance_record": "{{CSC3_DELIVERY_NOTE_ACCEPTANCE_RECORD_ROW}}",
    "acceptance_checklist": "{{CSC3_DELIVERY_NOTE_ACCEPTANCE_CHECKLIST_ROW}}",
}
DELIVERY_NOTE_APPROVAL_TOKENS = {
    "operator": "{{CSC3_DELIVERY_NOTE_OPERATOR_APPROVAL_ROW}}",
    "technical_reviewer": "{{CSC3_DELIVERY_NOTE_REVIEWER_APPROVAL_ROW}}",
    "delivery_approver": "{{CSC3_DELIVERY_NOTE_APPROVER_APPROVAL_ROW}}",
    "recipient_acknowledgement": "{{CSC3_DELIVERY_NOTE_RECIPIENT_APPROVAL_ROW}}",
}
DELIVERY_NOTE_NARRATIVE_TOKENS = {
    "delivery_purpose_and_authorized_scope": "{{CSC3_DELIVERY_NOTE_PURPOSE_LINE}}",
    "authorization_reference": "{{CSC3_DELIVERY_NOTE_AUTHORIZATION_LINE}}",
    "included_items_confirmation": "{{CSC3_DELIVERY_NOTE_INCLUDED_ITEMS_LINE}}",
    "excluded_items_confirmation": "{{CSC3_DELIVERY_NOTE_EXCLUDED_ITEMS_LINE}}",
    "known_limitations": "{{CSC3_DELIVERY_NOTE_KNOWN_LIMITATIONS_LINE}}",
    "unresolved_risks": "{{CSC3_DELIVERY_NOTE_UNRESOLVED_RISKS_LINE}}",
    "rollback_owner_and_contact": "{{CSC3_DELIVERY_NOTE_ROLLBACK_OWNER_LINE}}",
    "withdrawal_or_replacement_process": "{{CSC3_DELIVERY_NOTE_WITHDRAWAL_LINE}}",
    "sender_approval_statement": "{{CSC3_DELIVERY_NOTE_SENDER_STATEMENT_LINE}}",
    "recipient_acknowledgement_statement": "{{CSC3_DELIVERY_NOTE_RECIPIENT_STATEMENT_LINE}}",
}
DELIVERY_NOTE_SCALAR_TOKENS = {
    "evidence_sha256": "{{CSC3_DELIVERY_NOTE_EVIDENCE_SHA256_LINE}}",
    "report_sha256": "{{CSC3_DELIVERY_NOTE_REPORT_SHA256_LINE}}",
    "archive_sha256": "{{CSC3_DELIVERY_NOTE_ARCHIVE_SHA256_LINE}}",
    "presentation_pdf": "{{CSC3_DELIVERY_NOTE_PRESENTATION_PDF_LINE}}",
    "record_path": "{{CSC3_DELIVERY_NOTE_RECORD_PATH_LINE}}",
    "acceptance_status": "{{CSC3_DELIVERY_NOTE_ACCEPTANCE_STATUS_LINE}}",
    "correctness_summary": "{{CSC3_DELIVERY_NOTE_CORRECTNESS_SUMMARY_LINE}}",
    "performance_summary": "{{CSC3_DELIVERY_NOTE_PERFORMANCE_SUMMARY_LINE}}",
    "verification_summary": "{{CSC3_DELIVERY_NOTE_VERIFICATION_SUMMARY_LINE}}",
    "deviation_summary": "{{CSC3_DELIVERY_NOTE_DEVIATION_SUMMARY_LINE}}",
    "reproduction_source_commit": "{{CSC3_DELIVERY_NOTE_REPRODUCTION_SOURCE_COMMIT_LINE}}",
    "controlled_host_id": "{{CSC3_DELIVERY_NOTE_CONTROLLED_HOST_ID_LINE}}",
    "input_binding": "{{CSC3_DELIVERY_NOTE_INPUT_BINDING_LINE}}",
    "reproduction_record": "{{CSC3_DELIVERY_NOTE_REPRODUCTION_RECORD_LINE}}",
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
_publication = _load_sibling(
    "acceptance_publication.py", "csc3_acceptance_publication"
)

# Kept as a module alias so failure-injection tests exercise the shared primitive.
_write_fsynced_at = _publication.write_fsynced_at


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


def _deviation_identifier(value: object, label: str) -> str:
    """Validate one machine identifier before it reaches any Markdown output."""
    if not isinstance(value, str) or DEVIATION_IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise AcceptanceRenderingError(
            f"{label} must match ASCII identifier grammar "
            f"{DEVIATION_IDENTIFIER_GRAMMAR}"
        )
    return value


def _markdown_text(value: object) -> str:
    """Escape one validated value for literal display in Markdown prose/tables."""
    text = str(value)
    escaped: list[str] = []
    for character in text:
        if character in "\\`*_[]{}<>|":
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


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


def canonical_presentation_pdf_binding(record: Mapping[str, object]) -> str:
    """Return the public canonical Markdown binding for the optional PDF."""
    return _canonical_presentation_pdf_binding(record)


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
        identifier = _deviation_identifier(
            deviation.get("identifier"),
            f"acceptance record deviations[{index}].identifier",
        )
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
        "distribution": context.distribution,
        "complete_checkout": (
            f"source_and_input_identity={source_identity['status']}；"
            f"evidence={source_identity['evidence_reference']}"
        ),
        "source_head": (
            f"HEAD={context.source_commit}；source_and_input_identity={source_identity['status']}"
        ),
        "clean_worktree": (
            f"worktree_clean={source_identity['status']}；runbook={runbook_path}；"
            f"SHA-256={runbook_sha}"
        ),
        "input_path": context.text(
            context.input_facts, "repository_relative_path", "input"
        ),
        "lfs_materialized": (
            f"tracked={context.boolean(context.input_facts, 'tracked', 'input')}；"
            f"materialized={context.boolean(context.input_facts, 'materialized', 'input')}；"
            f"matches_head_lfs={context.boolean(context.input_facts, 'matches_head_lfs', 'input')}"
        ),
        "input_size": (
            f"size_bytes={input_size}；head_lfs_size_bytes={input_lfs_size}"
        ),
        "input_sha256": (
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
        "controlled_host_id": context.text(
            context.controlled_host, "controlled_host_id", "controlled_host"
        ),
        "physical_linux_intel": (
            f"system={context.text(context.controlled_host, 'system', 'controlled_host')}；"
            f"architecture={context.text(context.controlled_host, 'architecture', 'controlled_host')}；"
            f"cpu_vendor={context.text(context.controlled_host, 'cpu_vendor', 'controlled_host')}；"
            f"cpu_model={context.text(context.controlled_host, 'cpu_model', 'controlled_host')}；"
            f"physical_core_count={physical_cores}；logical_core_count={logical_cores}"
        ),
        "host_preflight": f"path={host_preflight_path}；SHA-256={host_preflight_sha}",
        "toolchain_versions": (
            f"compiler={context.text(context.toolchain, 'compiler', 'toolchain')} "
            f"{context.text(context.toolchain, 'compiler_version', 'toolchain')}；"
            f"CMake={context.text(context.toolchain, 'cmake_version', 'toolchain')}；"
            f"Ninja={context.text(context.toolchain, 'ninja_version', 'toolchain')}；"
            f"Python={context.text(context.toolchain, 'python_version', 'toolchain')}；"
            f"Git={context.text(context.toolchain, 'git_version', 'toolchain')}；"
            f"Git LFS={context.text(context.toolchain, 'git_lfs_version', 'toolchain')}"
        ),
        "openmp_environment": (
            f"openmp_found={context.boolean(context.toolchain, 'openmp_found', 'toolchain')}；"
            f"openmp_required={context.boolean(context.toolchain, 'openmp_required', 'toolchain')}；"
            f"OMP_DYNAMIC={context.text(context.execution, 'omp_dynamic', 'execution')}；"
            f"OMP_PROC_BIND={context.text(context.execution, 'omp_proc_bind', 'execution')}；"
            f"OMP_PLACES={context.text(context.execution, 'omp_places', 'execution')}"
        ),
        "thread_set": (
            f"requested_thread_counts={context.requested_threads}；"
            "physical_core_thread_included="
            f"{context.boolean(context.execution, 'physical_core_thread_included', 'execution')}；"
            f"report_recomputation={context.report_recomputation['status']}"
        ),
        "benchmark_counts": (
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
        "ctest": (
            f"status={context.text(context.ctest, 'status', 'verifications.ctest')}；"
            f"test_count={_objective_integer(context.ctest.get('test_count'), 'verifications.ctest.test_count')}；"
            f"failed_count={_objective_integer(context.ctest.get('failed_count'), 'verifications.ctest.failed_count')}；"
            f"skipped_count={_objective_integer(context.ctest.get('skipped_count'), 'verifications.ctest.skipped_count')}；"
            f"not_run_count={_objective_integer(context.ctest.get('not_run_count'), 'verifications.ctest.not_run_count')}；"
            f"test_names={context.ctest_names}；"
            f"evidence={context.text(context.ctest, 'evidence_reference', 'verifications.ctest')}；"
            f"junit={ctest_path}；JUnit_SHA-256={ctest_sha}"
        ),
        "csc3_structure": (
            f"Tet4={context.text(tet4, 'status', 'correctness.tet4')}/"
            f"structure_equal={context.boolean(tet4, 'structure_equal', 'correctness.tet4')}/"
            f"values_finite={context.boolean(tet4, 'values_finite', 'correctness.tet4')}/"
            f"scatter_indices_valid={context.boolean(tet4, 'scatter_indices_valid', 'correctness.tet4')}；"
            f"Hex8={context.text(hex8, 'status', 'correctness.hex8')}/"
            f"structure_equal={context.boolean(hex8, 'structure_equal', 'correctness.hex8')}/"
            f"values_finite={context.boolean(hex8, 'values_finite', 'correctness.hex8')}/"
            f"scatter_indices_valid={context.boolean(hex8, 'scatter_indices_valid', 'correctness.hex8')}"
        ),
        "frobenius_error": (
            f"Tet4={context.number(tet4, 'frobenius_relative_error', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'frobenius_relative_error', 'correctness.hex8')}；"
            "maximum="
            f"{context.number(thresholds, 'frobenius_relative_error_maximum', 'correctness.thresholds')}"
        ),
        "maximum_absolute_error": (
            f"Tet4={context.number(tet4, 'maximum_absolute_error', 'correctness.tet4')}/"
            f"serial_max={context.number(tet4, 'maximum_absolute_serial_entry', 'correctness.tet4')}/"
            f"tolerance={context.number(tet4, 'maximum_absolute_error_tolerance', 'correctness.tet4')}/"
            f"within_tolerance={context.boolean(tet4, 'maximum_absolute_error_within_tolerance', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'maximum_absolute_error', 'correctness.hex8')}/"
            f"serial_max={context.number(hex8, 'maximum_absolute_serial_entry', 'correctness.hex8')}/"
            f"tolerance={context.number(hex8, 'maximum_absolute_error_tolerance', 'correctness.hex8')}/"
            f"within_tolerance={context.boolean(hex8, 'maximum_absolute_error_within_tolerance', 'correctness.hex8')}"
        ),
        "displacement_error": (
            f"Tet4={context.number(tet4, 'displacement_relative_error', 'correctness.tet4')}；"
            f"Hex8={context.number(hex8, 'displacement_relative_error', 'correctness.hex8')}；"
            "maximum="
            f"{context.number(thresholds, 'displacement_relative_error_maximum', 'correctness.thresholds')}"
        ),
        "relative_residual": (
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
        "benchmark_samples": (
            f"path={samples_path}；SHA-256={samples_sha}；"
            f"raw_sample_count={raw_sample_count}；"
            f"repeat_count={_objective_integer(context.execution.get('repeat_count'), 'execution.repeat_count')}；"
            f"threads={context.requested_threads}"
        ),
        "benchmark_summary": (
            f"path={summary_path}；SHA-256={summary_sha}；"
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}"
        ),
        "numeric_speedup": (
            f"p={numeric_thread}；"
            f"speedup={context.number(performance, 'numeric_speedup', 'performance')}；"
            f"minimum={context.number(thresholds, 'numeric_speedup_minimum', 'performance.thresholds')}"
        ),
        "symbolic_speedup": (
            f"p={symbolic_thread}；"
            f"speedup={context.number(performance, 'symbolic_speedup', 'performance')}；"
            "exclusive_minimum="
            f"{context.number(thresholds, 'symbolic_speedup_exclusive_minimum', 'performance.thresholds')}"
        ),
        "coefficient_of_variation": (
            "numeric="
            f"{context.number(performance, 'numeric_coefficient_of_variation', 'performance')}；"
            "symbolic="
            f"{context.number(performance, 'symbolic_coefficient_of_variation', 'performance')}；"
            "maximum="
            f"{context.number(thresholds, 'maximum_coefficient_of_variation', 'performance.thresholds')}"
        ),
        "timing_coverage": (
            f"raw_sample_count={raw_sample_count}；"
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}"
        ),
        "no_ci_timing": (
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
        "run_manifest": (
            f"execution.status={context.text(context.execution, 'status', 'execution')}；"
            f"evidence_level={context.text(context.execution, 'evidence_level', 'execution')}；"
            f"report_intent={context.text(context.execution, 'report_intent', 'execution')}；"
            f"path={run_manifest_path}；SHA-256={run_manifest_sha}"
        ),
        "staged_identity_checks": (
            f"source_and_input_identity={context.source_identity['status']}；"
            f"evidence={context.source_identity['evidence_reference']}"
        ),
        "report_recomputation": (
            f"report_recomputation={context.report_recomputation['status']}；"
            f"evidence={context.report_recomputation['evidence_reference']}；"
            f"path={report_path}；SHA-256={report_sha}"
        ),
        "report_source_binding": (
            f"source_commit={context.source_commit}；"
            f"source_and_input_identity={context.source_identity['status']}；"
            f"delivery_zip={context.archive_name}；SHA-256={context.archive_sha256}"
        ),
        "evidence_hashes": (
            f"run_manifest_SHA256={run_manifest_sha}；report_SHA256={report_sha}；"
            f"SHA256SUMS_SHA256={checksums_sha}"
        ),
        "source_commit_file": (
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
        "candidate_status": (
            f"candidate_status=PACKAGE_CANDIDATE；outcome_record={outcome_path}；"
            f"SHA-256={outcome_sha}"
        ),
        "checksums_coverage": (
            f"deterministic_package={context.deterministic['status']}；"
            f"path={checksums_path}；SHA-256={checksums_sha}"
        ),
        "deterministic_package": (
            f"status={context.deterministic['status']}；"
            f"evidence={context.deterministic['evidence_reference']}；"
            f"path={deterministic_path}；SHA-256={deterministic_sha}"
        ),
        "manifest_only": (
            f"status={context.manifest_only['status']}；"
            f"evidence={context.manifest_only['evidence_reference']}；"
            f"path={manifest_only_path}；SHA-256={manifest_only_sha}"
        ),
        "clean_room": (
            f"status={context.clean_room['status']}；"
            f"evidence={context.clean_room['evidence_reference']}；"
            f"path={clean_room_path}；SHA-256={clean_room_sha}"
        ),
        "standalone_validator": (
            f"validator=PASS；acceptance_record={context.record_relative}；"
            f"SHA-256={context.record_sha256}"
        ),
        "finalizer_contract": (
            "output_precondition=NONEXISTENT；publication=ATOMIC_NO_REPLACE；"
            "final_hash_manifest=FINAL_SHA256SUMS"
        ),
        "markdown_authority": (
            f"canonical_markdown_report={report_path}；SHA-256={report_sha}；"
            f"{_canonical_presentation_pdf_binding(context.record)}"
        ),
        "deviations": _canonical_deviation_summary(context.record),
        "final_decision": context.text(context.record, "status", "record"),
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


def canonical_objective_checklist_values(
    record: Mapping[str, object],
    *,
    archive_name: str,
    archive_sha256: str,
    record_relative: str,
    record_sha256: str,
    objective_artifacts: Mapping[str, tuple[str, str]],
    validation_status: object,
) -> dict[str, str]:
    """Return semantic checklist-field values for public tests and tooling."""
    return _canonical_objective_checklist_values(
        record,
        archive_name=archive_name,
        archive_sha256=archive_sha256,
        record_relative=record_relative,
        record_sha256=record_sha256,
        objective_artifacts=objective_artifacts,
        validation_status=validation_status,
    )


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
        _deviation_identifier(
            deviation.get("identifier"),
            f"decision.deviations[{index}].identifier",
        )
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


def _require_unique_template_token(text: str, token: str) -> None:
    count = text.count(token)
    if count != 1:
        raise AcceptanceRenderingError(
            f"template token {token!r} must occur exactly once; found {count}"
        )


def _replace_template_token(text: str, token: str, replacement: str) -> str:
    _require_unique_template_token(text, token)
    return text.replace(token, replacement, 1)


def _replace_template_line(text: str, token: str, replacement: str) -> str:
    _require_unique_template_token(text, token)
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if token in line]
    if len(matches) != 1:
        raise AcceptanceRenderingError(
            f"template token {token!r} must identify exactly one line"
        )
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _replace_checkbox_block(
    text: str, token: str, values: tuple[str, ...]
) -> str:
    _require_unique_template_token(text, token)
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("- [")]
    matches: list[tuple[int, int]] = []
    for start in starts:
        end = start + 1
        while end < len(lines) and lines[end].startswith("  "):
            end += 1
        block = "\n".join(lines[start:end])
        if token in block:
            matches.append((start, end))
    if len(matches) != 1:
        raise AcceptanceRenderingError(
            f"template token {token!r} identified {len(matches)} checkbox blocks"
        )
    start, end = matches[0]
    block = "\n".join(lines[start:end]).replace(f" <!-- {token} -->", "", 1)
    if block.count(PLACEHOLDER) != len(values):
        raise AcceptanceRenderingError(
            f"template token {token!r} has unexpected value slots"
        )
    block = block.replace("- [ ] ", "- [x] ", 1)
    for value in values:
        if "\n" in value or "\r" in value:
            raise AcceptanceRenderingError(
                f"template token {token!r} has an unsafe value"
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
    if values.keys() != CHECKLIST_OBJECTIVE_TOKENS.keys():
        raise AcceptanceRenderingError(
            "canonical checklist objective fields differ from the token contract"
        )
    for field, value in values.items():
        text = _replace_checkbox_block(
            text, CHECKLIST_OBJECTIVE_TOKENS[field], (value,)
        )
    return text


def _fill_checklist_narratives(
    text: str, decision: Mapping[str, object]
) -> str:
    narratives = _mapping(decision.get("checklist_narratives"), "checklist_narratives")
    for field, token in CHECKLIST_NARRATIVE_TOKENS.items():
        text = _replace_checkbox_block(
            text, token, (_required_text(narratives.get(field), field),)
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
        "delivery_id": str(record["delivery_id"]),
        "issue_url": str(record["issue_url"]),
        "demo_version": _canonical_demo_version(record, archive_name),
        "source_commit": str(record["source_commit"]),
        "archive_binding": f"{archive_name}` `{archive_sha256}",
        "recipient_organization": (
            f"{recipient['organization']}` / `{recipient['department']}"
        ),
        "recipient_identity": str(recipient["identity_reference"]),
    }
    for field, value in fixed.items():
        text = _replace_checkbox_block(
            text, CHECKLIST_PARTY_TOKENS[field], (value,)
        )
    approvals = _mapping(record.get("approvals"), "record.approvals")
    for name, token in CHECKLIST_APPROVAL_TOKENS.items():
        approval = _mapping(approvals.get(name), f"approvals.{name}")
        text = _replace_checkbox_block(
            text,
            token,
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
    text = _replace_template_token(text, CHECKLIST_STATUS_TOKEN, "PASS")
    text = _replace_template_token(text, CHECKLIST_DECISION_TOKEN, "PASS")
    text = _replace_template_line(
        text, CHECKLIST_FINAL_TOKENS["status"], "最终状态：`PASS`"
    )
    text = _replace_template_line(
        text,
        CHECKLIST_FINAL_TOKENS["record"],
        f"最终验收记录文件：`{record_relative_path}` `{record_sha256}`",
    )
    text = _replace_template_line(
        text,
        CHECKLIST_FINAL_TOKENS["archive_sha256"],
        f"最终 ZIP SHA-256：`{archive_sha256}`",
    )
    if PLACEHOLDER in text or "- [ ]" in text or "{{CSC3_" in text:
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
        "delivery_id": f"| 交付 ID | **{_markdown_text(record['delivery_id'])}** |",
        "delivery_date": (
            f"| 交付日期（UTC） | **{_canonical_delivery_date_utc(record)}** |"
        ),
        "demo_version": (
            f"| Demo 版本 | **{_canonical_demo_version(record, archive_name)}** |"
        ),
        "issue_url": (
            f"| Issue #44 URL | **{_markdown_text(record['issue_url'])}** |"
        ),
        "sender": (
            "| 发送组织/部门 | **"
            f"{_markdown_text(operator['organization'])} / "
            f"{_markdown_text(operator['department'])}** |"
        ),
        "recipient": (
            "| 接收组织/部门 | **"
            f"{_markdown_text(recipient['organization'])} / "
            f"{_markdown_text(recipient['department'])}** |"
        ),
        "recipient_identity": (
            "| 指定接收人身份引用 | "
            f"**{_markdown_text(recipient['identity_reference'])}** |"
        ),
        "source_commit": f"| 完整源码 SHA | **{record['source_commit']}** |",
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
        "delivery_zip": "正式源码 ZIP",
        "run_manifest": "原始证据目录/manifest",
        "canonical_markdown_report": "规范 Markdown 报告",
        "host_preflight": "`host-preflight.txt`",
        "source_commit_file": "`SOURCE_COMMIT`",
        "sha256sums_file": "`SHA256SUMS`",
        "deterministic_package_record": "`deterministic-package.txt`",
        "manifest_only_verifier_output": "manifest-only verifier 输出",
        "clean_room_verifier_log": "`clean-room-verification.log`",
    }
    for artifact_name, label in artifact_rows.items():
        path, digest = objective_artifacts[artifact_name]
        rows[artifact_name] = f"| {label} | **{path}** | **{digest}** |"
    rows["acceptance_record"] = (
        f"| 机器可读验收记录 | **{record_relative_path}** | **{record_sha256}** |"
    )
    rows["acceptance_checklist"] = (
        f"| 完成版验收清单 | **{checklist_relative_path}** | "
        f"**{checklist_sha256}** |"
    )
    return rows


def _delivery_note_approval_rows(record: Mapping[str, object]) -> dict[str, str]:
    approvals = _mapping(record.get("approvals"), "record.approvals")
    rows: dict[str, str] = {}
    approval_labels = {
        "operator": "操作员",
        "technical_reviewer": "技术复核人",
        "delivery_approver": "发送方批准/交付批准人",
        "recipient_acknowledgement": "接收方确认",
    }
    for name, label in approval_labels.items():
        approval = _mapping(approvals.get(name), f"approvals.{name}")
        rows[name] = (
            f"| {label} | **{_markdown_text(approval['identity_reference'])}** | "
            f"**{approval['acknowledged_at_utc']}** | "
            f"**{_markdown_text(approval['approval_record_reference'])}** | "
            f"**{approval['acknowledgement']}** |"
        )
    return rows


def _fill_delivery_note_narratives(
    text: str, decision: Mapping[str, object]
) -> str:
    narratives = _mapping(
        decision.get("delivery_note_narratives"), "delivery_note_narratives"
    )
    narrative_labels = {
        "delivery_purpose_and_authorized_scope": "交付目的与允许使用范围：",
        "authorization_reference": "授权文件或内部审批引用：",
        "included_items_confirmation": "最终包含项核对：",
        "excluded_items_confirmation": "最终排除项核对：",
        "known_limitations": "已知限制：",
        "unresolved_risks": "未解决风险（无风险也必须填写“无”）：",
        "rollback_owner_and_contact": "回滚负责人及联系引用：",
        "withdrawal_or_replacement_process": "撤回/替换流程引用：",
        "sender_approval_statement": "发送方批准声明：",
        "recipient_acknowledgement_statement": "接收方确认声明：",
    }
    for field, prefix in narrative_labels.items():
        value = _required_text(narratives.get(field), field)
        text = _replace_template_line(
            text,
            DELIVERY_NOTE_NARRATIVE_TOKENS[field],
            f"{prefix}**{_markdown_text(value)}**",
        )
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
        "evidence_sha256": f"证据 SHA-256：**{objective_artifacts['run_manifest'][1]}**",
        "report_sha256": (
            "报告 SHA-256：**"
            f"{objective_artifacts['canonical_markdown_report'][1]}**"
        ),
        "archive_sha256": f"ZIP SHA-256：**{archive_sha256}**",
        "presentation_pdf": (
            "可选 PDF 路径及 SHA-256：**"
            f"{_canonical_presentation_pdf_binding(record)}**"
        ),
        "record_path": (
            f"机器可读验收记录路径：**{record_relative_path}**"
        ),
        "acceptance_status": "正式验收状态（只能为 `PASS`）：**PASS**",
        "correctness_summary": (
            f"正确性门槛摘要：**{_canonical_correctness_summary(record)}**"
        ),
        "performance_summary": (
            f"性能门槛摘要：**{_canonical_performance_summary(record)}**"
        ),
        "verification_summary": (
            f"确定性打包与 clean-room 结果：**{verification_summary}**"
        ),
        "deviation_summary": (
            "偏差及批准引用（无偏差也必须填写“无”）："
            f"**{_markdown_text(_canonical_deviation_summary(record))}**"
        ),
        "reproduction_source_commit": (
            f"复现所需完整源码 SHA：**{record['source_commit']}**"
        ),
        "controlled_host_id": (
            f"受控主机 ID：**{controlled_host['controlled_host_id']}**"
        ),
        "input_binding": (
            f"输入 SHA-256 与字节数：**{input_facts['sha256']}** / "
            f"**{input_facts['size_bytes']} bytes**"
        ),
        "reproduction_record": (
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
    text = _replace_template_token(
        _template_text(DELIVERY_NOTE_TEMPLATE), DELIVERY_NOTE_STATUS_TOKEN, "PASS"
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
    expected_table_fields = (
        set(DELIVERY_NOTE_IDENTITY_TOKENS)
        | set(DELIVERY_NOTE_ARTIFACT_TOKENS)
        | set(DELIVERY_NOTE_APPROVAL_TOKENS)
    )
    if set(table_lines) != expected_table_fields:
        raise AcceptanceRenderingError(
            "delivery-note table fields differ from the token contract"
        )
    for field, replacement in table_lines.items():
        token = (
            DELIVERY_NOTE_IDENTITY_TOKENS.get(field)
            or DELIVERY_NOTE_ARTIFACT_TOKENS.get(field)
            or DELIVERY_NOTE_APPROVAL_TOKENS.get(field)
        )
        if token is None:
            raise AcceptanceRenderingError(
                f"delivery-note table field {field!r} lacks a template token"
            )
        text = _replace_template_line(text, token, replacement)
    text = _fill_delivery_note_narratives(text, decision)
    scalar_lines = _delivery_note_scalar_lines(
        record,
        objective_artifacts,
        archive_sha256=archive_sha256,
        record_relative_path=record_relative_path,
    )
    if scalar_lines.keys() != DELIVERY_NOTE_SCALAR_TOKENS.keys():
        raise AcceptanceRenderingError(
            "delivery-note scalar fields differ from the token contract"
        )
    for field, replacement in scalar_lines.items():
        text = _replace_template_line(
            text, DELIVERY_NOTE_SCALAR_TOKENS[field], replacement
        )
    if PLACEHOLDER in text or "{{CSC3_" in text:
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
        actual = _publication.read_regular_file_at(staging_descriptor, filename)
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
    staging_name, staging_descriptor = _publication.create_staging_directory(
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
        if not _publication.directory_entry_matches_descriptor(
            parent_descriptor, staging_name, staging_descriptor
        ):
            raise AcceptanceRenderingError(
                "private render staging directory changed before publication"
            )
        _publication.assert_publication_parent_unchanged(
            paths.publication_parent,
            parent_descriptor,
            AcceptanceRenderingError,
        )
        _publication.atomic_publish_directory_no_replace(
            parent_descriptor,
            staging_name,
            paths.output_directory.name,
            AcceptanceRenderingError,
        )
        published = True
        _publication.fsync_published_parent(
            parent_descriptor, paths.output_directory.name
        )
    except BaseException as error:
        if not published:
            quarantine_detail = _publication.retain_unpublished_directory(
                staging_name,
                staging_descriptor,
                staged_names,
            )
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                error.add_note(quarantine_detail)
                raise
            raise AcceptanceRenderingError(
                f"{error}; {quarantine_detail}"
            ) from error
        raise
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
    if not _publication.SECURE_DIRECTORY_PUBLICATION_SUPPORTED:
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
    parent_descriptor = _publication.open_anchored_directory(
        paths.publication_parent, AcceptanceRenderingError
    )
    try:
        _publication.assert_output_absent(
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
