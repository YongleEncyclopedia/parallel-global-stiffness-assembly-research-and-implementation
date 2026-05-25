#!/usr/bin/env python3
"""Build a schema v2 mentor action-item package from generated artifacts."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from cross_platform_schema_v2 import (
    BASELINE_CASE_NAME,
    BASELINE_KERNEL,
    BASELINE_STIFFNESS_MODEL,
    EXPERIMENT_FAMILIES,
    SCHEMA_VERSION_V2,
    render_v2_report,
    validate_v2_package,
    write_v2_package,
)


def read_csv(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def select_records(rows: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        record["experiment_family"] = family
        record.setdefault("status", "PASS")
        if record["status"] == "":
            record["status"] = "PASS"
        out.append(record)
    return out


def first_present(row: dict[str, Any], *names: str, default: str = "0") -> Any:
    for name in names:
        value = row.get(name)
        if value not in {None, ""}:
            return value
    return default


def basic_metric_records(symbolic_rows: list[dict[str, Any]], benchmark_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in symbolic_rows:
        strategy = row.get("strategy_label") or row.get("mode", "")
        records.append(
            {
                "experiment_family": "basic_metrics",
                "status": row.get("matrix_correctness_status", "PASS"),
                "case_name": row.get("case_name", ""),
                "mesh": row.get("mesh", ""),
                "element_type": row.get("element_type", ""),
                "stiffness_model": row.get("stiffness_model", ""),
                "algorithm_or_strategy": strategy,
                "threads": row.get("threads", ""),
                "repeat_or_assemblies": row.get("assemblies_per_symbolic", ""),
                "matrix_correctness_status": row.get("matrix_correctness_status", "PASS"),
                "rel_l2": row.get("rel_l2", "0"),
                "max_abs": row.get("max_abs", "0"),
                "memory_reference_strategy": row.get("memory_reference_strategy", "direct_no_symbolic_serial"),
                "estimated_peak_bytes": row.get("estimated_peak_bytes", "0"),
                "extra_or_backend_memory_bytes": row.get("numeric_backend_extra_bytes", "0"),
                "transient_memory_bytes": first_present(
                    row,
                    "direct_transient_bytes",
                    "symbolic_temporary_bytes",
                    default="0",
                ),
                "rss_peak_mb": row.get("isolated_peak_rss_mb", "0"),
                "rss_measurement_source": "isolated_process"
                if float(row.get("isolated_peak_rss_mb", "0") or 0.0) > 0.0
                else "not_measured",
                "time_scope": row.get("time_scope", "mesh_ready_to_matrix_assembled"),
                "assembly_or_amortized_ms": row.get("amortized_total_ms", "0"),
                "serial_direct_baseline_ms": row.get("serial_direct_baseline_ms", "0"),
                "speedup_baseline_strategy": row.get("speedup_baseline_strategy", "direct_no_symbolic_serial"),
                "speedup_vs_serial_direct": row.get("speedup_vs_serial_direct", row.get("symbolic_gain_vs_direct", "0")),
                "source_mode": row.get("mode", ""),
                "source_numeric_backend": row.get("numeric_backend", ""),
            }
        )
    for row in benchmark_rows:
        records.append(
            {
                "experiment_family": "basic_metrics",
                "status": row.get("status", "PASS"),
                "case_name": row.get("case_name", ""),
                "mesh": row.get("mesh", ""),
                "element_type": row.get("element_type", ""),
                "stiffness_model": row.get("stiffness_model", ""),
                "algorithm_or_strategy": row.get("algorithm", ""),
                "threads": row.get("threads", ""),
                "repeat_or_assemblies": row.get("run_count", ""),
                "matrix_correctness_status": "PASS" if row.get("status", "PASS") == "PASS" else row.get("status", ""),
                "rel_l2": row.get("rel_l2", "0"),
                "max_abs": row.get("max_abs", "0"),
                "memory_reference_strategy": "direct_no_symbolic_serial",
                "estimated_peak_bytes": row.get("estimated_peak_bytes", row.get("extra_memory_bytes", "0")),
                "extra_or_backend_memory_bytes": row.get("extra_memory_bytes", "0"),
                "transient_memory_bytes": "0",
                "rss_peak_mb": row.get("peak_rss_mb", "0"),
                "rss_measurement_source": "process_ru_maxrss",
                "time_scope": "mesh_ready_to_matrix_assembled",
                "assembly_or_amortized_ms": row.get("assembly_mean_ms", row.get("assembly_ms", "0")),
                "serial_direct_baseline_ms": row.get("serial_direct_baseline_ms", "0"),
                "speedup_baseline_strategy": "direct_no_symbolic_serial",
                "speedup_vs_serial_direct": row.get("speedup_vs_serial_direct", "0"),
                "source_algorithm": row.get("algorithm", ""),
            }
        )
    if not records:
        records.append(
            {
                "experiment_family": "basic_metrics",
                "status": "INFO",
                "case_name": BASELINE_CASE_NAME,
                "mesh": BASELINE_CASE_NAME,
                "element_type": "unknown",
                "stiffness_model": BASELINE_STIFFNESS_MODEL,
                "algorithm_or_strategy": "not_provided",
                "threads": "0",
                "repeat_or_assemblies": "0",
                "matrix_correctness_status": "INFO",
                "rel_l2": "0",
                "max_abs": "0",
                "memory_reference_strategy": "direct_no_symbolic_serial",
                "estimated_peak_bytes": "0",
                "extra_or_backend_memory_bytes": "0",
                "transient_memory_bytes": "0",
                "rss_peak_mb": "0",
                "rss_measurement_source": "not_measured",
                "time_scope": "mesh_ready_to_matrix_assembled",
                "assembly_or_amortized_ms": "0",
                "serial_direct_baseline_ms": "0",
                "speedup_baseline_strategy": "direct_no_symbolic_serial",
                "speedup_vs_serial_direct": "0",
                "note": "No benchmark or symbolic rows were provided.",
            }
        )
    return records


def memory_lifecycle_records(symbolic_rows: list[dict[str, Any]], benchmark_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in symbolic_rows:
        mode = row.get("mode", "")
        strategy_label = row.get("strategy_label", mode)
        common = {
            "strategy_label": strategy_label,
            "mode": mode,
            "numeric_backend": row.get("numeric_backend", ""),
            "threads": row.get("threads", ""),
            "assemblies_per_symbolic": row.get("assemblies_per_symbolic", ""),
        }
        if mode == "parallel_symbolic_reuse":
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "parallel symbolic temporary rows/counts",
                    "lifecycle": "transient",
                    "measurement": "estimated",
                    "bytes": row.get("symbolic_temporary_bytes", "0"),
                    "source_field": "symbolic_temporary_bytes",
                    "status": "PASS",
                    **common,
                }
            )
        if row.get("symbolic_persistent_bytes") not in {None, ""}:
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "symbolic persistent CSR/plan",
                    "lifecycle": "persistent",
                    "measurement": "exact",
                    "bytes": row.get("symbolic_persistent_bytes", "0"),
                    "source_field": "symbolic_persistent_bytes",
                    "status": "PASS",
                    **common,
                }
            )
        if row.get("numeric_backend_extra_bytes") not in {None, ""}:
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "numeric backend extra memory",
                    "lifecycle": "backend_prepare_or_assemble",
                    "measurement": "estimated",
                    "bytes": row.get("numeric_backend_extra_bytes", "0"),
                    "source_field": "numeric_backend_extra_bytes",
                    "status": "PASS",
                    **common,
                }
            )
        if row.get("estimated_peak_bytes") not in {None, ""}:
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "estimated peak memory",
                    "lifecycle": "peak_model",
                    "measurement": "estimated",
                    "bytes": row.get("estimated_peak_bytes", "0"),
                    "source_field": "estimated_peak_bytes",
                    "status": "PASS",
                    **common,
                }
            )
        if row.get("isolated_peak_rss_mb") not in {None, ""}:
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "isolated peak RSS",
                    "lifecycle": "process",
                    "measurement": "os_observed",
                    "mb": row.get("isolated_peak_rss_mb", "0"),
                    "source_field": "isolated_peak_rss_mb",
                    "status": "PASS",
                    **common,
                }
            )
        if mode.startswith("direct_no_symbolic"):
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": "direct/no-symbolic contribution buffer",
                    "lifecycle": "transient",
                    "measurement": "estimated",
                    "bytes": row.get("direct_transient_bytes", "0"),
                    "source_field": "direct_transient_bytes",
                    "status": "PASS",
                    **common,
                }
            )
    for row in benchmark_rows:
        algorithm = row.get("algorithm", "")
        if algorithm in {"cpu_private_csr", "cpu_lock_guard"}:
            records.append(
                {
                    "experiment_family": "memory_lifecycle",
                    "item": algorithm,
                    "lifecycle": "persistent" if algorithm == "cpu_lock_guard" else "transient",
                    "measurement": "estimated",
                    "bytes": row.get("extra_memory_bytes", "0"),
                    "source_field": "extra_memory_bytes",
                    "status": row.get("status", "INFO"),
                }
            )
    if not records:
        records.append(
            {
                "experiment_family": "memory_lifecycle",
                "item": "memory lifecycle",
                "status": "INFO",
                "note": "No memory source rows were provided.",
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--platform-id", default="local")
    parser.add_argument("--thread-scaling-csv", default=None)
    parser.add_argument("--symbolic-csv", default=None)
    parser.add_argument("--lock-benchmark-csv", default=None)
    parser.add_argument("--pattern-metadata", default=None)
    args = parser.parse_args()

    thread_rows = read_csv(Path(args.thread_scaling_csv) if args.thread_scaling_csv else None)
    symbolic_rows = read_csv(Path(args.symbolic_csv) if args.symbolic_csv else None)
    lock_rows = read_csv(Path(args.lock_benchmark_csv) if args.lock_benchmark_csv else None)
    pattern_metadata = read_json(Path(args.pattern_metadata) if args.pattern_metadata else None)

    correctness_records: list[dict[str, Any]]
    if pattern_metadata:
        correctness_records = [
            {
                "experiment_family": "correctness_sparse",
                "status": "PASS" if pattern_metadata.get("correctness", {}).get("same_structure") else "FAIL",
                "case_name": pattern_metadata.get("case_name", ""),
                "serial_nnz": pattern_metadata.get("serial", {}).get("nnz", 0),
                "parallel_nnz": pattern_metadata.get("parallel", {}).get("nnz", 0),
                "relative_l2": pattern_metadata.get("correctness", {}).get("relative_l2", 0),
                "max_abs": pattern_metadata.get("correctness", {}).get("max_abs", 0),
                "source": str(args.pattern_metadata),
            }
        ]
    else:
        correctness_records = [
            {
                "experiment_family": "correctness_sparse",
                "status": "INFO",
                "note": "No sparse-pattern metadata was provided.",
            }
        ]

    experiments = [
        {"experiment_family": "basic_metrics", "records": basic_metric_records(symbolic_rows, thread_rows)},
        {"experiment_family": "thread_scaling", "records": select_records(thread_rows, "thread_scaling") or [{"experiment_family": "thread_scaling", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "symbolic_direct", "records": select_records(symbolic_rows, "symbolic_direct") or [{"experiment_family": "symbolic_direct", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "lock_vs_atomic", "records": select_records(lock_rows, "lock_vs_atomic") or [{"experiment_family": "lock_vs_atomic", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "correctness_sparse", "records": correctness_records},
        {"experiment_family": "memory_lifecycle", "records": memory_lifecycle_records(symbolic_rows, lock_rows)},
    ]
    package = {
        "schema_version": SCHEMA_VERSION_V2,
        "platform_id": args.platform_id,
        "baseline": {
            "case_name": BASELINE_CASE_NAME,
            "stiffness_model": BASELINE_STIFFNESS_MODEL,
            "kernel": BASELINE_KERNEL,
        },
        "experiment_families": list(EXPERIMENT_FAMILIES),
        "experiments": experiments,
    }

    result = validate_v2_package(package)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.errors:
        return 1
    out_dir = Path(args.out_dir)
    path = write_v2_package(package, out_dir)
    report = render_v2_report(package)
    (out_dir / "cross_platform_schema_v2_report.md").write_text(report, encoding="utf-8")
    print(f"[OK] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
