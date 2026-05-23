#!/usr/bin/env python3
"""Smoke-test sparse stiffness pattern export."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def read_pattern(path: Path) -> list[tuple[int, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [(int(row["row"]), int(row["col"])) for row in reader]


def read_csr_window(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_pattern_export.py PATTERN_EXPORT_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

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
            "--threads",
            "2",
            "--parallel-algo",
            "atomic",
            "--out-dir",
            str(out_dir),
            "--prefix",
            "pattern_smoke",
        ],
        check=True,
    )

    serial_csv = out_dir / "pattern_smoke_serial_pattern.csv"
    parallel_csv = out_dir / "pattern_smoke_parallel_pattern.csv"
    serial_mtx = out_dir / "pattern_smoke_serial_pattern.mtx"
    parallel_mtx = out_dir / "pattern_smoke_parallel_pattern.mtx"
    metadata_json = out_dir / "pattern_smoke_metadata.json"
    serial_csr_window = out_dir / "pattern_smoke_serial_csr_window.csv"
    parallel_csr_window = out_dir / "pattern_smoke_parallel_csr_window.csv"
    serial_csr_summary = out_dir / "pattern_smoke_serial_csr_window_summary.md"
    original_svg = out_dir / "pattern_smoke_spy_original_raster.svg"
    rcm_svg = out_dir / "pattern_smoke_spy_rcm_raster.svg"
    exact_window_csv = out_dir / "pattern_smoke_exact_window_serial.csv"
    exact_window_svg = out_dir / "pattern_smoke_exact_window_serial.svg"
    exact_window_auto_csv = out_dir / "pattern_smoke_exact_window_auto_serial.csv"
    exact_window_auto_svg = out_dir / "pattern_smoke_exact_window_auto_serial.svg"

    assert read_pattern(serial_csv) == read_pattern(parallel_csv)
    assert serial_mtx.read_text(encoding="utf-8").startswith("%%MatrixMarket matrix coordinate pattern general")
    assert parallel_mtx.read_text(encoding="utf-8").startswith("%%MatrixMarket matrix coordinate pattern general")
    serial_rows = read_csr_window(serial_csr_window)
    parallel_rows = read_csr_window(parallel_csr_window)
    assert serial_rows
    assert len(serial_rows) == len(parallel_rows)
    assert serial_rows[0].keys() == {"row", "row_offset_begin", "row_offset_end", "p", "col", "value"}
    for row in serial_rows:
        begin = int(row["row_offset_begin"])
        end = int(row["row_offset_end"])
        p = int(row["p"])
        assert begin <= p < end
    assert serial_csr_summary.read_text(encoding="utf-8").startswith("# CSR Window Summary")
    metadata = json.loads(metadata_json.read_text(encoding="utf-8"))
    assert metadata["serial"]["nnz"] == metadata["parallel"]["nnz"]
    assert metadata["parallel"]["algorithm"] == "cpu_atomic"
    assert metadata["visualization"]["permutation_algorithm"] == "reverse_cuthill_mckee"
    assert metadata["visualization"]["rcm_nnz"] == metadata["serial"]["nnz"]
    assert metadata["visualization"]["rcm_bandwidth"] <= metadata["visualization"]["original_bandwidth"]
    assert metadata["visualization"]["exact_window_auto"]["size"] == 4096
    assert original_svg.read_text(encoding="utf-8").startswith("<svg")
    assert rcm_svg.read_text(encoding="utf-8").startswith("<svg")
    exact_rows = read_pattern(exact_window_csv)
    assert exact_rows
    assert exact_window_svg.read_text(encoding="utf-8").startswith("<svg")
    for row, col in exact_rows:
        assert 0 <= row < 4096
        assert 0 <= col < 4096
    assert read_pattern(exact_window_auto_csv)
    assert exact_window_auto_svg.read_text(encoding="utf-8").startswith("<svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
