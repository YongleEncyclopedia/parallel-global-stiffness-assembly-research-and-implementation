#!/usr/bin/env python3
"""Verify isolated backend thread sweep runner measures each runnable combination separately."""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: verify_isolated_backend_thread_sweep_runner.py RUNNER BENCHMARK_EXE OUT_DIR",
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
            "--benchmark-exe",
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
            "--kernel",
            "linear_elastic_solid",
            "--case-name",
            "isolated_runner_smoke",
            "--algorithms",
            "serial,atomic",
            "--threads-list",
            "1,2",
            "--process-repeat",
            "2",
            "--warmup",
            "1",
        ],
        check=True,
    )

    repeat_csv = out_dir / "windhub_backend_thread_sweep_intel_isolated_repeats.csv"
    summary_csv = out_dir / "windhub_backend_thread_sweep_intel_isolated_summary.csv"
    with repeat_csv.open(newline="", encoding="utf-8") as handle:
        repeat_rows = list(csv.DictReader(handle))
    with summary_csv.open(newline="", encoding="utf-8") as handle:
        summary_rows = list(csv.DictReader(handle))

    assert len(summary_rows) == 4
    statuses = {(row["algorithm"], row["threads"]): row["status"] for row in summary_rows}
    assert statuses[("cpu_serial", "1")] == "PASS"
    assert statuses[("cpu_serial", "2")] == "SKIP"
    assert statuses[("cpu_atomic", "1")] == "PASS"
    assert statuses[("cpu_atomic", "2")] == "PASS"
    assert len(repeat_rows) == 6
    for row in repeat_rows:
        symbolic = float(row["symbolic_ms"])
        numeric = float(row["numeric_ms"])
        total = float(row["symbolic_numeric_total_ms"])
        assert abs((symbolic + numeric) - total) < 1.0e-6
        assert float(row["isolated_peak_rss_mb"]) > 0.0
        assert row["measurement_mode"] == "isolated"
    assert not any(row["algorithm"] == "cpu_coo_sort_reduce" for row in repeat_rows + summary_rows)
    assert not any("direct_no_symbolic" in row.get("algorithm", "") for row in repeat_rows + summary_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
