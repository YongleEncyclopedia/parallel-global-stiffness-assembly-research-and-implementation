#!/usr/bin/env python3
"""Verify symbolic_numeric_eval exposes parallel symbolic/direct modes."""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path


def _float(row: dict[str, str], field: str) -> float:
    return float(row[field])


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
    assert "parallel_symbolic_reuse" in modes
    assert "direct_no_symbolic_parallel" in modes
    assert any(row["numeric_backend"] == "cpu_lock_guard" for row in rows)
    assert any(row["threads"] == "2" for row in rows)
    assert "direct_bucket_merge_ms" in rows[0]
    assert "symbolic_temporary_bytes" in rows[0]
    for field in (
        "backend_prepare_ms",
        "assembly_numeric_ms",
        "legacy_numeric_ms_without_prepare",
        "numeric_backend_extra_bytes",
    ):
        assert field in rows[0], field
    lock_rows = [
        row
        for row in rows
        if row["mode"] == "parallel_symbolic_reuse"
        and row["numeric_backend"] == "cpu_lock_guard"
        and row["threads"] == "2"
    ]
    assert lock_rows
    for row in lock_rows:
        assert _float(row, "numeric_backend_extra_bytes") > 0.0
        assert math.isfinite(_float(row, "backend_prepare_ms"))
        assert math.isfinite(_float(row, "assembly_numeric_ms"))
        assert abs(
            _float(row, "numeric_ms")
            - (_float(row, "backend_prepare_ms") + _float(row, "assembly_numeric_ms"))
        ) < 1.0e-6
        assert abs(
            _float(row, "legacy_numeric_ms_without_prepare")
            - _float(row, "assembly_numeric_ms")
        ) < 1.0e-6
        assert abs(
            _float(row, "amortized_total_ms")
            - (_float(row, "symbolic_total_ms") + _float(row, "numeric_ms"))
        ) < 1.0e-6

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    json_modes = {record["mode"] for record in payload["records"]}
    assert "parallel_symbolic_reuse" in json_modes
    assert "direct_no_symbolic_parallel" in json_modes
    json_lock = [
        record
        for record in payload["records"]
        if record["mode"] == "parallel_symbolic_reuse"
        and record["numeric_backend"] == "cpu_lock_guard"
        and record["threads"] == 2
    ]
    assert json_lock
    assert json_lock[0]["numeric_backend_extra_bytes"] > 0
    assert "backend_prepare_ms" in json_lock[0]
    assert "assembly_numeric_ms" in json_lock[0]
    assert "legacy_numeric_ms_without_prepare" in json_lock[0]
    assert md_path.read_text(encoding="utf-8").count("parallel_symbolic_reuse") >= 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
