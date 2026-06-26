#!/usr/bin/env python3
"""Verify benchmark_assembly isolated mode reports per-algorithm symbolic/numeric timings."""
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
        print("usage: verify_isolated_benchmark_cli.py BENCHMARK_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "isolated_atomic.csv"
    json_path = out_dir / "isolated_atomic.json"
    md_path = out_dir / "isolated_atomic.md"

    subprocess.run(
        [
            str(exe),
            "--measurement-mode",
            "isolated",
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
            "--case-name",
            "isolated_atomic_smoke",
            "--stiffness-model",
            "linear_elastic_solid",
            "--algo",
            "atomic",
            "--threads",
            "2",
            "--warmup",
            "1",
            "--repeat",
            "1",
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
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["measurement_mode"] == "isolated"
    assert row["algorithm"] == "cpu_atomic"
    assert row["threads"] == "2"
    for field in (
        "mesh_load_ms",
        "symbolic_csr_ms",
        "symbolic_plan_ms",
        "backend_prepare_ms",
        "symbolic_ms",
        "numeric_ms",
        "symbolic_numeric_total_ms",
    ):
        assert field in row, field
        assert math.isfinite(_float(row, field)), field
    expected_symbolic = _float(row, "symbolic_csr_ms") + _float(row, "symbolic_plan_ms") + _float(row, "backend_prepare_ms")
    assert abs(_float(row, "symbolic_ms") - expected_symbolic) < 1.0e-6
    assert abs(_float(row, "symbolic_numeric_total_ms") - (_float(row, "symbolic_ms") + _float(row, "numeric_ms"))) < 1.0e-6
    assert _float(row, "symbolic_numeric_total_ms") > 0.0

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    records = payload["records"]
    assert len(records) == 1
    assert records[0]["measurement_mode"] == "isolated"
    assert records[0]["algorithm"] == "cpu_atomic"
    assert records[0]["threads"] == 2
    for field in ("symbolic_ms", "numeric_ms", "symbolic_numeric_total_ms"):
        assert abs(float(row[field]) - float(records[0][field])) < 1.0e-12, field
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
