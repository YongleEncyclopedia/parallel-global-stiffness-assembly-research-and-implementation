#!/usr/bin/env python3
"""Verify isolated symbolic memory runner emits per-strategy peak RSS rows."""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: verify_isolated_symbolic_memory_runner.py RUNNER SYMBOLIC_EXE OUT_DIR",
            file=sys.stderr,
        )
        return 2

    runner = Path(sys.argv[1])
    exe = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    subprocess.run(
        [
            sys.executable,
            str(runner),
            "--symbolic-exe",
            str(exe),
            "--out-root",
            str(out_dir),
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
            "symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse",
        ],
        check=True,
    )

    csv_path = out_dir / "isolated_symbolic_memory.csv"
    md_path = out_dir / "isolated_symbolic_memory.md"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    for field in (
        "strategy_label",
        "mode",
        "threads",
        "estimated_peak_bytes",
        "delta_vs_serial_symbolic_serial_numeric_bytes",
        "isolated_peak_rss_mb",
        "isolated_memory_metric",
        "isolated_memory_measurement_source",
    ):
        assert field in rows[0], field
    assert all(float(row["isolated_peak_rss_mb"]) > 0.0 for row in rows)
    assert all(
        row["isolated_memory_metric"] in {"process_ru_maxrss", "windows_peak_working_set"}
        for row in rows
    )
    if sys.platform == "win32":
        for field in ("isolated_peak_working_set_mb", "isolated_peak_private_bytes_mb"):
            assert field in rows[0], field
            assert all(float(row[field]) > 0.0 for row in rows)
    assert any(row["strategy_label"] == "serial_symbolic_serial_numeric" for row in rows)
    assert any(row["strategy_label"] == "serial_symbolic_parallel_numeric" for row in rows)
    assert any(row["strategy_label"] == "parallel_symbolic_parallel_numeric" for row in rows)
    assert any(
        row["mode"] == "parallel_symbolic_reuse" and int(float(row["symbolic_temporary_bytes"])) > 0
        for row in rows
    )
    assert "isolated peak RSS" in md_path.read_text(encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
