#!/usr/bin/env python3
"""Tests for the revised monthly assembly quadrant figure package."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from plot_monthly_assembly_quadrants_revised import (  # noqa: E402
    DEFAULT_SOURCE_CSV,
    DEFAULT_OUT_ROOT,
    compute_metrics,
    load_rows,
    planned_output_files,
)


class MonthlyAssemblyQuadrantsRevisedTests(unittest.TestCase):
    def test_source_rows_and_metrics_match_existing_contract(self) -> None:
        rows = load_rows(DEFAULT_SOURCE_CSV)
        metrics = compute_metrics(rows)

        self.assertEqual(
            set(rows),
            {"serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"},
        )
        self.assertAlmostEqual(rows["serial_direct"].total_ms, 5203.104000, places=6)
        self.assertAlmostEqual(rows["serial_symbolic"].total_ms, 3092.295792, places=6)
        self.assertAlmostEqual(rows["parallel_direct"].total_ms, 1669.417125, places=6)
        self.assertAlmostEqual(rows["parallel_symbolic"].total_ms, 662.423459, places=6)
        self.assertAlmostEqual(metrics["serial_symbolic_vs_serial_direct"], 1.6826022961518814)
        self.assertAlmostEqual(metrics["parallel_symbolic_vs_serial_symbolic"], 4.668155618564831)
        self.assertAlmostEqual(metrics["parallel_symbolic_vs_parallel_direct"], 2.520166069480942)
        self.assertAlmostEqual(metrics["parallel_symbolic_vs_serial_direct"], 7.85464936259149)
        self.assertAlmostEqual(rows["parallel_symbolic"].persistent_symbolic_gib, 0.961274, places=6)
        self.assertAlmostEqual(rows["parallel_symbolic"].symbolic_temp_gib, 0.139468, places=6)
        self.assertAlmostEqual(rows["parallel_direct"].direct_transient_gib, 2.389707, places=6)

    def test_planned_outputs_cover_python_r_and_matlab_candidates(self) -> None:
        outputs = planned_output_files(DEFAULT_OUT_ROOT, ("svg", "pdf", "png"))
        rel = {path.relative_to(DEFAULT_OUT_ROOT).as_posix() for path in outputs}

        for backend in ("python", "r", "matlab"):
            self.assertIn(f"{backend}/assembly_quadrants_revised.{backend}.svg", rel)
            self.assertIn(f"{backend}/assembly_quadrants_revised.{backend}.pdf", rel)
            self.assertIn(f"{backend}/assembly_quadrants_revised.{backend}.png", rel)
            self.assertIn(f"{backend}/direct_assembly_schematic.{backend}.svg", rel)
            self.assertIn(f"{backend}/two_stage_assembly_schematic.{backend}.svg", rel)

        self.assertIn("source_data/quadrant_selected_rows.csv", rel)
        self.assertIn("qa_notes.md", rel)

    def test_all_backend_script_entrypoints_are_present(self) -> None:
        scripts = PROJECT_ROOT / "scripts"
        python_script = scripts / "plot_monthly_assembly_quadrants_revised.py"
        r_script = scripts / "plot_monthly_assembly_quadrants_revised.R"
        matlab_script = scripts / "plot_monthly_assembly_quadrants_revised_matlab.m"

        self.assertTrue(python_script.exists())
        self.assertTrue(r_script.exists())
        self.assertTrue(matlab_script.exists())

        python_text = python_script.read_text(encoding="utf-8")
        r_text = r_script.read_text(encoding="utf-8")
        matlab_text = matlab_script.read_text(encoding="utf-8")
        for flag in ("--source-csv", "--out-root", "--format"):
            self.assertIn(flag, python_text)
            self.assertIn(flag, r_text)
        self.assertIn("function plot_monthly_assembly_quadrants_revised_matlab", matlab_text)
        self.assertIn("source_csv", matlab_text)
        self.assertIn("out_root", matlab_text)


if __name__ == "__main__":
    unittest.main()
