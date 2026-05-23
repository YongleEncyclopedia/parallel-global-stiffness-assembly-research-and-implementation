#!/usr/bin/env python3
"""Shared helpers for PGSA cross-platform CPU benchmark packages."""
from __future__ import annotations

import csv
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "pgsa-cross-platform-v1"
BASELINE_CASE_NAME = "3d-WindTurbineHub"
BASELINE_STIFFNESS_MODEL = "linear_elastic_solid"
BASELINE_KERNEL = BASELINE_STIFFNESS_MODEL
LEGACY_BASELINE_KERNELS = ("physics_tet4", "physics_solid")
BASELINE_ALGORITHMS = (
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
)
RUN_PROFILES = ("full_host", "performance_core_only", "efficiency_core_only")
PROFILE_STATUSES = ("available", "missing", "not_applicable", "unknown")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_platform_compact(value: str) -> dict[str, str]:
    parts = [part.strip() for part in value.split(";")]
    while len(parts) < 4:
        parts.append("")
    return {
        "os": parts[0],
        "arch": parts[1],
        "compiler": parts[2],
        "openmp": parts[3],
    }


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def classify_core_profiles(metadata: dict[str, Any]) -> dict[str, str]:
    """Return profile availability for the detected CPU core model."""
    perf = _as_int(metadata.get("performance_core_count") or metadata.get("p_core_count"))
    eff = _as_int(metadata.get("efficiency_core_count") or metadata.get("e_core_count"))
    affinity = str(metadata.get("affinity_control") or "").lower()
    can_isolate = affinity in {"manual", "taskset", "cpuset", "affinity", "processor_affinity"}

    statuses = {
        "full_host": "available",
        "performance_core_only": "not_applicable",
        "efficiency_core_only": "not_applicable",
    }
    if perf > 0 and eff > 0:
        status = "available" if can_isolate else "missing"
        statuses["performance_core_only"] = status
        statuses["efficiency_core_only"] = status
    return statuses


def _run_text(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _cpu_model() -> str:
    system = platform.system()
    if system == "Darwin":
        value = _run_text(["sysctl", "-n", "machdep.cpu.brand_string"])
        return value or _run_text(["sysctl", "-n", "hw.model"]) or "Unknown CPU"
    if system == "Linux":
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            for line in cpuinfo.read_text(errors="ignore").splitlines():
                if line.lower().startswith(("model name", "hardware")) and ":" in line:
                    return line.split(":", 1)[1].strip()
        return "Unknown CPU"
    if system == "Windows":
        return os.environ.get("PROCESSOR_IDENTIFIER", "Windows CPU")
    return "Unknown CPU"


def _sysctl_int(name: str) -> int:
    value = _run_text(["sysctl", "-n", name])
    return _as_int(value)


def _linux_cpu_capacity_groups() -> dict[int, list[int]]:
    groups: dict[int, list[int]] = {}
    root = Path("/sys/devices/system/cpu")
    for cpu_dir in root.glob("cpu[0-9]*"):
        match = re.fullmatch(r"cpu(\d+)", cpu_dir.name)
        if not match:
            continue
        capacity_path = cpu_dir / "cpu_capacity"
        if not capacity_path.exists():
            continue
        capacity = _as_int(capacity_path.read_text(errors="ignore").strip())
        groups.setdefault(capacity, []).append(int(match.group(1)))
    return {key: sorted(value) for key, value in sorted(groups.items())}


def current_platform_metadata() -> dict[str, Any]:
    """Inspect the current host with conservative, stdlib-only probes."""
    system = platform.system()
    metadata: dict[str, Any] = {
        "os": system or "UnknownOS",
        "arch": platform.machine() or "unknown_arch",
        "cpu_model": _cpu_model(),
        "logical_cores": os.cpu_count() or 0,
        "physical_cores": os.cpu_count() or 0,
        "affinity_control": "manual" if system == "Darwin" else "unknown",
        "performance_core_count": 0,
        "efficiency_core_count": 0,
        "evidence": [],
    }

    if system == "Darwin":
        physical = _sysctl_int("hw.physicalcpu")
        logical = _sysctl_int("hw.logicalcpu")
        perf = _sysctl_int("hw.perflevel0.physicalcpu")
        eff = _sysctl_int("hw.perflevel1.physicalcpu")
        if physical:
            metadata["physical_cores"] = physical
        if logical:
            metadata["logical_cores"] = logical
        if perf and eff:
            metadata["performance_core_count"] = perf
            metadata["efficiency_core_count"] = eff
            metadata["evidence"].append("sysctl hw.perflevel0/1.physicalcpu")
        else:
            metadata["evidence"].append("sysctl did not expose perflevel core counts")
    elif system == "Linux":
        groups = _linux_cpu_capacity_groups()
        metadata["affinity_control"] = "taskset" if shutil.which("taskset") else "unknown"
        if len(groups) >= 2:
            capacities = sorted(groups)
            eff_cpus = groups[capacities[0]]
            perf_cpus = groups[capacities[-1]]
            metadata["performance_core_count"] = len(perf_cpus)
            metadata["efficiency_core_count"] = len(eff_cpus)
            metadata["performance_core_cpus"] = perf_cpus
            metadata["efficiency_core_cpus"] = eff_cpus
            metadata["cpu_capacity_groups"] = {str(k): v for k, v in groups.items()}
            metadata["evidence"].append("/sys/devices/system/cpu/cpu*/cpu_capacity")
        else:
            metadata["evidence"].append("no heterogeneous cpu_capacity groups detected")
    elif system == "Windows":
        metadata["affinity_control"] = "processor_affinity"
        metadata["evidence"].append("Windows stdlib probe cannot reliably classify P/E cores")

    metadata["core_profile_status"] = classify_core_profiles(metadata)
    return metadata


def _require_dict(value: Any, name: str, result: ValidationResult) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    result.errors.append(f"{name} must be an object")
    return {}


def validate_package(package: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    for key in ("schema_version", "platform_id", "run_profile", "baseline", "platform", "records"):
        if key not in package:
            result.errors.append(f"missing top-level field: {key}")

    if package.get("schema_version") != SCHEMA_VERSION:
        result.errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if package.get("run_profile") not in RUN_PROFILES:
        result.errors.append(f"run_profile must be one of {', '.join(RUN_PROFILES)}")

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
        algorithms = tuple(baseline.get("algorithms") or ())
        if algorithms != BASELINE_ALGORITHMS:
            result.errors.append("baseline.algorithms must match the v1 CPU/OpenMP baseline")

    platform_info = _require_dict(package.get("platform"), "platform", result)
    statuses = platform_info.get("core_profile_status") if platform_info else {}
    if not isinstance(statuses, dict):
        result.errors.append("platform.core_profile_status must be an object")
        statuses = {}
    else:
        for profile in RUN_PROFILES:
            status = statuses.get(profile)
            if status not in PROFILE_STATUSES:
                result.errors.append(f"invalid status for {profile}: {status}")
            if status == "missing":
                result.warnings.append(f"{package.get('platform_id', '<unknown>')} is missing {profile}")

    records = package.get("records")
    if not isinstance(records, list) or not records:
        result.errors.append("records must be a non-empty list")
    else:
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                result.errors.append(f"records[{index}] must be an object")
                continue
            for key in ("schema_version", "platform_id", "run_profile", "env_group", "algorithm", "threads", "status"):
                if key not in record:
                    result.errors.append(f"records[{index}] missing field: {key}")
            if record.get("schema_version") != package.get("schema_version"):
                result.errors.append(f"records[{index}] schema_version does not match package")
            if record.get("platform_id") != package.get("platform_id"):
                result.errors.append(f"records[{index}] platform_id does not match package")
            if record.get("run_profile") != package.get("run_profile"):
                result.errors.append(f"records[{index}] run_profile does not match package")
            if record.get("algorithm") not in BASELINE_ALGORITHMS and record.get("algorithm") != "cpu_serial":
                result.errors.append(f"records[{index}] algorithm is outside the v1 baseline")
    return result


def validate_packages(packages: list[dict[str, Any]]) -> ValidationResult:
    combined = ValidationResult()
    by_platform: dict[str, set[str]] = {}
    status_by_platform: dict[str, dict[str, str]] = {}
    for package in packages:
        result = validate_package(package)
        combined.errors.extend(result.errors)
        combined.warnings.extend(result.warnings)
        platform_id = str(package.get("platform_id", ""))
        profile = str(package.get("run_profile", ""))
        if platform_id and profile:
            by_platform.setdefault(platform_id, set()).add(profile)
        platform_info = package.get("platform") if isinstance(package.get("platform"), dict) else {}
        statuses = platform_info.get("core_profile_status") if isinstance(platform_info, dict) else {}
        if isinstance(statuses, dict):
            status_by_platform.setdefault(platform_id, {}).update(statuses)

    for platform_id, statuses in status_by_platform.items():
        present = by_platform.get(platform_id, set())
        if statuses.get("full_host") == "available" and "full_host" not in present:
            combined.errors.append(f"{platform_id} lacks required full_host package")
        for profile in ("performance_core_only", "efficiency_core_only"):
            if statuses.get(profile) == "available" and profile not in present:
                combined.warnings.append(f"{platform_id} declares {profile} available but package is absent")
    return combined


def load_package(path: Path | str) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "benchmark_package.json"
    return json.loads(candidate.read_text(encoding="utf-8"))


def _convert_value(value: str) -> Any:
    if value is None or value == "":
        return ""
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            return value
    if re.fullmatch(r"-?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?", value):
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _platform_from_source_root(source_root: Path, fallback_row: dict[str, str]) -> dict[str, Any]:
    raw_csv = source_root / "default" / "thread_scaling_default.csv"
    compact = ""
    if raw_csv.exists():
        rows = _read_csv(raw_csv)
        if rows:
            compact = rows[0].get("platform", "")
    platform_fields = parse_platform_compact(compact)
    platform_fields.update(
        {
            "cpu_model": fallback_row.get("cpu_model", "Unknown CPU"),
            "physical_cores": _convert_value(fallback_row.get("physical_cores", "")),
            "logical_cores": _convert_value(fallback_row.get("logical_cores", "")),
        }
    )
    return platform_fields


def package_from_thread_scaling_root(
    source_root: Path,
    *,
    platform_id: str,
    run_profile: str,
    profile_note: str,
    core_profile_status: dict[str, str],
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    combined_csv = source_root / "thread_scaling_combined.csv"
    rows = _read_csv(combined_csv)
    if not rows:
        raise ValueError(f"no records in {combined_csv}")

    records: list[dict[str, Any]] = []
    for row in rows:
        algorithm = row.get("algorithm", "")
        if algorithm not in BASELINE_ALGORITHMS:
            continue
        record = {key: _convert_value(value) for key, value in row.items()}
        record.update(
            {
                "schema_version": schema_version,
                "platform_id": platform_id,
                "run_profile": run_profile,
                "profile_note": profile_note,
                "source_root": str(source_root),
            }
        )
        records.append(record)

    platform_info = _platform_from_source_root(source_root, rows[0])
    platform_info["core_profile_status"] = core_profile_status

    return {
        "schema_version": schema_version,
        "platform_id": platform_id,
        "run_profile": run_profile,
        "profile_note": profile_note,
        "env_group": "combined",
        "baseline": {
            "case_name": BASELINE_CASE_NAME,
            "stiffness_model": BASELINE_STIFFNESS_MODEL,
            "kernel": BASELINE_KERNEL,
            "algorithms": list(BASELINE_ALGORITHMS),
        },
        "platform": platform_info,
        "source": {
            "kind": "legacy_thread_scaling_root",
            "path": str(source_root),
            "combined_csv": str(combined_csv),
        },
        "records": records,
    }


def write_package(package: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_package.json"
    out_path.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def render_cross_platform_report(packages: list[dict[str, Any]]) -> str:
    validation = validate_packages(packages)
    lines = [
        "# Cross-Platform CPU Benchmark Schema Report",
        "",
        "This report checks schema compatibility, baseline completeness, and interpretation guardrails.",
        "It is not a platform performance ranking.",
        "",
        "## Guardrails",
        "",
        "- Do not interpret hardware, compiler, operating-system, affinity, or OpenMP runtime differences as pure algorithm differences.",
        "- Do not compare incomplete platform profiles as if they were complete CPU characterizations.",
        "- Treat `full_host`, `performance_core_only`, and `efficiency_core_only` as resource profiles under one CPU platform, not separate CPU models.",
        "",
        "## Packages",
        "",
        "| Platform | Run profile | CPU model | Records | Profile status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for package in packages:
        platform_info = package.get("platform", {})
        statuses = platform_info.get("core_profile_status", {}) if isinstance(platform_info, dict) else {}
        status_text = ", ".join(f"{key}={statuses.get(key, 'unknown')}" for key in RUN_PROFILES)
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} |".format(
                package.get("platform_id", ""),
                package.get("run_profile", ""),
                platform_info.get("cpu_model", "") if isinstance(platform_info, dict) else "",
                len(package.get("records", [])),
                status_text,
            )
        )

    lines.extend(["", "## Validation", ""])
    if validation.errors:
        lines.append("### Errors")
        lines.append("")
        lines.extend(f"- {error}" for error in validation.errors)
        lines.append("")
    if validation.warnings:
        lines.append("### Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in validation.warnings)
        lines.append("")
    if not validation.errors and not validation.warnings:
        lines.append("- No schema errors or completeness warnings.")
        lines.append("")

    lines.extend(
        [
            "## Current Interpretation Boundary",
            "",
            "The package set is ready for merge/compatibility checks only. A performance conclusion table should be written only after each target CPU has its required `full_host` result and all applicable conditional core profiles are present or explicitly marked `not_applicable`.",
            "",
        ]
    )
    return "\n".join(lines)
