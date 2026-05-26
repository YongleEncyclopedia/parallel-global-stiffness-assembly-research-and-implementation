#!/usr/bin/env python3
"""Verify symbolic_numeric_eval exposes parallel symbolic/direct modes."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_symbolic_parallel_cli.py SYMBOLIC_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "symbolic_parallel.csv"
    json_path = out_dir / "symbolic_parallel.json"
    md_path = out_dir / "symbolic_parallel.md"

    subprocess.run(
        [
            str(exe),
            "--mesh",
            "cube",
            "--element",
            "tet4",
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
            "--stiffness-model",
            "linear_elastic_solid",
            "--assemblies-list",
            "1",
            "--threads-list",
            "1,2",
            "--backend-list",
            "atomic,lock_guard",
            "--mode-list",
            "direct_no_symbolic_serial,symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel",
            "--csv",
            str(csv_path),
            "--json",
            str(json_path),
            "--summary-md",
            str(md_path),
        ],
        check=True,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    modes = {row["mode"] for row in rows}
    strategy_labels = {row["strategy_label"] for row in rows}
    assert "parallel_symbolic_reuse" in modes
    assert "serial_symbolic_parallel_numeric" in modes
    assert "direct_no_symbolic_parallel" in modes
    assert "direct_no_symbolic_serial" in modes
    assert "serial_symbolic_serial_numeric" in strategy_labels
    assert "serial_symbolic_parallel_numeric" in strategy_labels
    assert "parallel_symbolic_parallel_numeric" in strategy_labels
    assert "direct_no_symbolic_background" in strategy_labels
    assert any(row["numeric_backend"] == "cpu_lock_guard" for row in rows)
    assert any(row["threads"] == "2" for row in rows)
    assert "direct_bucket_merge_ms" in rows[0]
    assert "symbolic_temporary_bytes" in rows[0]
    for field in (
        "symbolic_persistent_bytes",
        "common_output_matrix_bytes",
        "numeric_backend_extra_bytes",
        "estimated_peak_bytes",
        "delta_vs_serial_symbolic_serial_numeric_bytes",
        "delta_vs_serial_direct_bytes",
        "isolated_peak_rss_mb",
        "evaluation_schema_version",
        "metric_contract",
        "matrix_correctness_status",
        "matrix_correctness_reference_strategy",
        "memory_reference_strategy",
        "time_scope",
        "speedup_baseline_strategy",
        "serial_direct_baseline_ms",
        "speedup_vs_serial_direct",
    ):
        assert field in rows[0], field
    assert {row["evaluation_schema_version"] for row in rows} == {"pgsa-basic-metrics-v1"}
    assert {row["metric_contract"] for row in rows} == {"correctness_memory_time_v1"}
    assert {row["time_scope"] for row in rows} == {"mesh_ready_to_matrix_assembled"}
    assert all(row["matrix_correctness_status"] == "PASS" for row in rows)
    assert all(row["matrix_correctness_reference_strategy"] for row in rows)
    assert all(row["memory_reference_strategy"] == "direct_no_symbolic_serial" for row in rows)
    assert all(row["speedup_baseline_strategy"] == "direct_no_symbolic_serial" for row in rows)
    assert all(float(row["serial_direct_baseline_ms"]) > 0.0 for row in rows)
    assert all(float(row["speedup_vs_serial_direct"]) > 0.0 for row in rows)
    assert any(
        int(float(row["symbolic_temporary_bytes"])) > 0
        for row in rows
        if row["mode"] == "parallel_symbolic_reuse"
    )
    assert any(
        int(float(row["numeric_backend_extra_bytes"])) > 0
        for row in rows
        if row["numeric_backend"] == "cpu_lock_guard"
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    json_modes = {record["mode"] for record in payload["records"]}
    assert "parallel_symbolic_reuse" in json_modes
    assert "serial_symbolic_parallel_numeric" in json_modes
    assert "direct_no_symbolic_parallel" in json_modes
    assert "direct_no_symbolic_serial" in json_modes
    assert "estimated_peak_bytes" in payload["records"][0]
    assert payload["evaluation_schema_version"] == "pgsa-basic-metrics-v1"
    assert payload["metric_contract"] == "correctness_memory_time_v1"
    assert "speedup_vs_serial_direct" in payload["records"][0]
    assert md_path.read_text(encoding="utf-8").count("parallel_symbolic_reuse") >= 1
    assert "三项基础评价指标" in md_path.read_text(encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
