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


def memory_lifecycle_records(symbolic_rows: list[dict[str, Any]], benchmark_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in symbolic_rows:
        mode = row.get("mode", "")
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
        {"experiment_family": "thread_scaling", "records": select_records(thread_rows, "thread_scaling") or [{"experiment_family": "thread_scaling", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "symbolic_direct", "records": select_records(symbolic_rows, "symbolic_direct") or [{"experiment_family": "symbolic_direct", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "lock_vs_atomic", "records": select_records(lock_rows, "lock_vs_atomic") or [{"experiment_family": "lock_vs_atomic", "status": "INFO", "note": "not provided"}]},
        {"experiment_family": "correctness_sparse", "records": correctness_records},
        {"experiment_family": "memory_lifecycle", "records": memory_lifecycle_records(symbolic_rows, lock_rows)},
    ]
    package = {
        "schema_version": SCHEMA_VERSION_V2,
        "platform_id": args.platform_id,
        "baseline": {"case_name": BASELINE_CASE_NAME, "kernel": BASELINE_KERNEL},
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
