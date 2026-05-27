#!/usr/bin/env python3
"""Tests for the benchmark presentation-figure redraw workflow."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from benchmark_figure_style import assert_english_text, contains_cjk  # noqa: E402
from replot_benchmark_figures import benchmark_targets, planned_output_files  # noqa: E402


class BenchmarkFigureRedesignTests(unittest.TestCase):
    def test_english_text_guard_flags_cjk_text(self) -> None:
        self.assertFalse(contains_cjk("Best speedup vs serial baseline"))
        self.assertTrue(contains_cjk("线程扩展总览"))

        assert_english_text(["Core-profile comparison", "lower is better"])
        with self.assertRaises(ValueError):
            assert_english_text(["Core-profile comparison", "线程扩展总览"])

    def test_replot_manifest_covers_benchmark_roots_only(self) -> None:
        targets = benchmark_targets(PROJECT_ROOT)
        target_roots = {target.root.relative_to(PROJECT_ROOT).as_posix() for target in targets}

        self.assertEqual(
            target_roots,
            {
                "results/2026-04-22",
                "results/2026-05-11-thread-scaling",
                "results/2026-05-11-thread-scaling-linux-intel",
                "results/2026-05-12-thread-scaling-linux-intel-pcore",
                "results/2026-05-12-thread-scaling-linux-intel-ecore",
                "results/2026-05-14-thread-scaling-macos-m4max-performance-qos",
                "results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos",
                "results/cross-platform-v1",
            },
        )
        self.assertTrue(all("presentation_charts" not in str(target.root) for target in targets))

    def test_planned_outputs_match_benchmark_figure_inventory(self) -> None:
        outputs = planned_output_files(PROJECT_ROOT)
        relative_outputs = {path.relative_to(PROJECT_ROOT).as_posix() for path in outputs}

        self.assertEqual(len(outputs), 164)
        self.assertTrue(all("presentation_charts" not in item for item in relative_outputs))
        self.assertIn("results/2026-04-22/figures/cross_kernel_best_speedup.svg", relative_outputs)
        self.assertIn("results/2026-05-11-thread-scaling/figures/thread_scaling_contact_sheet.png", relative_outputs)
        self.assertIn(
            "results/cross-platform-v1/figures/core_profile_speedup_comparison_apple_m4_max.png",
            relative_outputs,
        )


if __name__ == "__main__":
    unittest.main()
