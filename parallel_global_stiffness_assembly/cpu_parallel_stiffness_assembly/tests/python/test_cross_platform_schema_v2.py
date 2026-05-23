#!/usr/bin/env python3
"""Unit tests for the v2 mentor action-item benchmark package model."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from cross_platform_schema_v2 import (  # noqa: E402
    SCHEMA_VERSION_V2,
    BASELINE_STIFFNESS_MODEL,
    EXPERIMENT_FAMILIES,
    group_records_by_family,
    render_v2_report,
    validate_v2_package,
)


class CrossPlatformSchemaV2Tests(unittest.TestCase):
    def test_v2_validation_requires_all_mentor_experiment_families(self) -> None:
        package = {
            "schema_version": SCHEMA_VERSION_V2,
            "platform_id": "unit-test-platform",
            "baseline": {
                "case_name": "3d-WindTurbineHub",
                "stiffness_model": BASELINE_STIFFNESS_MODEL,
                "kernel": BASELINE_STIFFNESS_MODEL,
            },
            "experiments": [
                {
                    "experiment_family": family,
                    "records": [{"status": "PASS", "algorithm": "cpu_atomic", "threads": 1}],
                }
                for family in EXPERIMENT_FAMILIES
            ],
        }
        result = validate_v2_package(package)
        self.assertFalse(result.errors)
        self.assertFalse(result.warnings)

    def test_v2_validation_flags_missing_family_without_weakening_v1(self) -> None:
        package = {
            "schema_version": SCHEMA_VERSION_V2,
            "platform_id": "unit-test-platform",
            "baseline": {
                "case_name": "3d-WindTurbineHub",
                "stiffness_model": BASELINE_STIFFNESS_MODEL,
                "kernel": BASELINE_STIFFNESS_MODEL,
            },
            "experiments": [
                {
                    "experiment_family": "thread_scaling",
                    "records": [{"status": "PASS", "algorithm": "cpu_atomic", "threads": 1}],
                }
            ],
        }
        result = validate_v2_package(package)
        self.assertTrue(result.errors)
        self.assertIn("symbolic_direct", "\n".join(result.errors))

    def test_grouping_and_report_are_family_first(self) -> None:
        records = [
            {"experiment_family": "lock_vs_atomic", "algorithm": "cpu_lock_guard", "status": "PASS"},
            {"experiment_family": "lock_vs_atomic", "algorithm": "cpu_atomic", "status": "PASS"},
            {"experiment_family": "memory_lifecycle", "item": "CSR values", "status": "PASS"},
        ]
        grouped = group_records_by_family(records)
        self.assertEqual(len(grouped["lock_vs_atomic"]), 2)
        report = render_v2_report(
            {
                "schema_version": SCHEMA_VERSION_V2,
                "platform_id": "unit-test-platform",
                "experiments": [
                    {"experiment_family": "lock_vs_atomic", "records": grouped["lock_vs_atomic"]},
                    {"experiment_family": "memory_lifecycle", "records": grouped["memory_lifecycle"]},
                ],
            }
        )
        self.assertIn("PGSA Cross-Platform Benchmark Schema v2", report)
        self.assertIn("lock_vs_atomic", report)
        self.assertIn("memory_lifecycle", report)

    def test_symbolic_memory_rows_preserve_strategy_and_measurement_source(self) -> None:
        from package_cross_platform_results_v2 import memory_lifecycle_records

        records = memory_lifecycle_records(
            [
                {
                    "mode": "parallel_symbolic_reuse",
                    "strategy_label": "parallel_symbolic_parallel_numeric",
                    "numeric_backend": "cpu_atomic",
                    "threads": "2",
                    "symbolic_temporary_bytes": "128",
                    "symbolic_persistent_bytes": "512",
                    "numeric_backend_extra_bytes": "64",
                    "estimated_peak_bytes": "768",
                    "isolated_peak_rss_mb": "12.5",
                },
                {
                    "mode": "direct_no_symbolic_parallel",
                    "strategy_label": "direct_no_symbolic_background",
                    "threads": "2",
                    "direct_transient_bytes": "2048",
                    "estimated_peak_bytes": "2560",
                    "isolated_peak_rss_mb": "20.0",
                },
            ],
            [],
        )

        items = {record["item"] for record in records}
        self.assertIn("parallel symbolic temporary rows/counts", items)
        self.assertIn("symbolic persistent CSR/plan", items)
        self.assertIn("numeric backend extra memory", items)
        self.assertIn("estimated peak memory", items)
        self.assertIn("isolated peak RSS", items)
        self.assertIn("direct/no-symbolic contribution buffer", items)
        peak = next(record for record in records if record["item"] == "estimated peak memory")
        self.assertEqual(peak["strategy_label"], "parallel_symbolic_parallel_numeric")
        self.assertEqual(peak["source_field"], "estimated_peak_bytes")


if __name__ == "__main__":
    unittest.main()
