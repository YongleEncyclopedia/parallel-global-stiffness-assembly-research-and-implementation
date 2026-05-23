#!/usr/bin/env python3
"""Schema v2 helpers for mentor action-item benchmark packages.

The v2 layer groups existing C++ CSV/JSON outputs by experiment family without
weakening the v1 package validation contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION_V2 = "pgsa-cross-platform-v2"
BASELINE_CASE_NAME = "3d-WindTurbineHub"
BASELINE_STIFFNESS_MODEL = "linear_elastic_solid"
BASELINE_KERNEL = BASELINE_STIFFNESS_MODEL
LEGACY_BASELINE_KERNELS = ("physics_tet4", "physics_solid")
EXPERIMENT_FAMILIES = (
    "thread_scaling",
    "symbolic_direct",
    "lock_vs_atomic",
    "correctness_sparse",
    "memory_lifecycle",
)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def group_records_by_family(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {family: [] for family in EXPERIMENT_FAMILIES}
    for record in records:
        family = str(record.get("experiment_family", ""))
        grouped.setdefault(family, []).append(record)
    return grouped


def _require_dict(value: Any, name: str, result: ValidationResult) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    result.errors.append(f"{name} must be an object")
    return {}


def validate_v2_package(package: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    if package.get("schema_version") != SCHEMA_VERSION_V2:
        result.errors.append(f"schema_version must be {SCHEMA_VERSION_V2}")
    if not package.get("platform_id"):
        result.errors.append("platform_id is required")

    baseline = _require_dict(package.get("baseline"), "baseline", result)
    if baseline:
        if baseline.get("case_name") != BASELINE_CASE_NAME:
            result.errors.append(f"baseline.case_name must be {BASELINE_CASE_NAME}")
        model = baseline.get("stiffness_model") or baseline.get("kernel")
        if model != BASELINE_STIFFNESS_MODEL:
            if model in LEGACY_BASELINE_KERNELS:
                result.warnings.append(
                    f"baseline.kernel={model} is a legacy physical stiffness-model alias; prefer {BASELINE_STIFFNESS_MODEL}"
                )
            else:
                result.errors.append(f"baseline.stiffness_model must be {BASELINE_STIFFNESS_MODEL}")

    experiments = package.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        result.errors.append("experiments must be a non-empty list")
        experiments = []

    seen: set[str] = set()
    for index, experiment in enumerate(experiments):
        if not isinstance(experiment, dict):
            result.errors.append(f"experiments[{index}] must be an object")
            continue
        family = experiment.get("experiment_family")
        if family not in EXPERIMENT_FAMILIES:
            result.errors.append(f"experiments[{index}] has unknown experiment_family: {family}")
            continue
        seen.add(str(family))
        records = experiment.get("records")
        if not isinstance(records, list) or not records:
            result.errors.append(f"{family} records must be a non-empty list")
            continue
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                result.errors.append(f"{family}.records[{record_index}] must be an object")
                continue
            if record.get("status") not in {"PASS", "FAIL", "SKIP", "WARN", "INFO", None}:
                result.errors.append(f"{family}.records[{record_index}] has invalid status")

    missing = [family for family in EXPERIMENT_FAMILIES if family not in seen]
    if missing:
        result.errors.append("missing experiment families: " + ", ".join(missing))
    return result


def load_v2_package(path: Path | str) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "benchmark_package_v2.json"
    return json.loads(candidate.read_text(encoding="utf-8"))


def write_v2_package(package: dict[str, Any], out_dir: Path | str) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    package_path = out_path / "benchmark_package_v2.json"
    package_path.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return package_path


def render_v2_report(package: dict[str, Any]) -> str:
    result = validate_v2_package(package)
    lines = [
        "# PGSA Cross-Platform Benchmark Schema v2",
        "",
        "This v2 report groups mentor action-item evidence by experiment family while preserving v1 raw CSV/JSON compatibility.",
        "",
        "## Experiment Families",
        "",
        "| Family | Records | Status |",
        "| --- | ---: | --- |",
    ]
    for experiment in package.get("experiments", []):
        if not isinstance(experiment, dict):
            continue
        family = experiment.get("experiment_family", "")
        records = experiment.get("records", [])
        pass_count = sum(1 for record in records if isinstance(record, dict) and record.get("status") == "PASS")
        lines.append(f"| `{family}` | {len(records) if isinstance(records, list) else 0} | PASS rows: {pass_count} |")

    lines.extend(["", "## Validation", ""])
    if result.errors:
        lines.append("### Errors")
        lines.append("")
        lines.extend(f"- {error}" for error in result.errors)
        lines.append("")
    if result.warnings:
        lines.append("### Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in result.warnings)
        lines.append("")
    if not result.errors and not result.warnings:
        lines.append("- No schema v2 errors or warnings.")
        lines.append("")
    return "\n".join(lines)
