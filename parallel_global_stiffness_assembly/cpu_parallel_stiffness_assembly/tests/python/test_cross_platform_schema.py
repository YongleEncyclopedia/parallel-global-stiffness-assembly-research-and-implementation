#!/usr/bin/env python3
"""Unit tests for the cross-platform benchmark schema helpers."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from cross_platform_schema import (  # noqa: E402
    BASELINE_ALGORITHMS,
    BASELINE_CASE_NAME,
    BASELINE_KERNEL,
    BASELINE_STIFFNESS_MODEL,
    SCHEMA_VERSION,
    classify_core_profiles,
    load_package,
    render_cross_platform_report,
    validate_package,
)


def minimal_package(platform_id: str, run_profile: str, profile_statuses: dict[str, str]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "platform_id": platform_id,
        "run_profile": run_profile,
        "profile_note": "",
        "env_group": "combined",
        "baseline": {
            "case_name": BASELINE_CASE_NAME,
            "stiffness_model": BASELINE_STIFFNESS_MODEL,
            "kernel": BASELINE_KERNEL,
            "algorithms": list(BASELINE_ALGORITHMS),
        },
        "platform": {
            "cpu_model": platform_id,
            "os": "fixture-os",
            "arch": "fixture-arch",
            "compiler": "fixture-compiler",
            "openmp": "fixture-openmp",
            "core_profile_status": profile_statuses,
        },
        "records": [
            {
                "schema_version": SCHEMA_VERSION,
                "platform_id": platform_id,
                "run_profile": run_profile,
                "env_group": "bound",
                "algorithm": "cpu_atomic",
                "threads": 1,
                "assembly_mean_ms": 1.0,
                "status": "PASS",
            }
        ],
    }


class CrossPlatformSchemaTests(unittest.TestCase):
    def test_core_profile_classification_distinguishes_hybrid_and_homogeneous_cpus(self) -> None:
        apple = classify_core_profiles(
            {
                "cpu_model": "Apple M4 Max",
                "performance_core_count": 10,
                "efficiency_core_count": 4,
                "affinity_control": "manual",
            }
        )
        self.assertEqual(apple["full_host"], "available")
        self.assertEqual(apple["performance_core_only"], "available")
        self.assertEqual(apple["efficiency_core_only"], "available")

        intel = classify_core_profiles(
            {
                "cpu_model": "Intel(R) Core(TM) Ultra 7 265KF",
                "performance_core_count": 8,
                "efficiency_core_count": 12,
                "affinity_control": "taskset",
            }
        )
        self.assertEqual(intel["performance_core_only"], "available")
        self.assertEqual(intel["efficiency_core_only"], "available")

        amd = classify_core_profiles(
            {
                "cpu_model": "AMD Ryzen 9 9950X",
                "physical_cores": 16,
                "logical_cores": 32,
                "affinity_control": "taskset",
            }
        )
        self.assertEqual(amd["full_host"], "available")
        self.assertEqual(amd["performance_core_only"], "not_applicable")
        self.assertEqual(amd["efficiency_core_only"], "not_applicable")

    def test_validate_package_reports_missing_conditional_profiles_without_failing_schema(self) -> None:
        package = minimal_package(
            "apple-m4-max",
            "full_host",
            {
                "full_host": "available",
                "performance_core_only": "missing",
                "efficiency_core_only": "missing",
            },
        )
        result = validate_package(package)
        self.assertFalse(result.errors)
        self.assertIn("performance_core_only", "\n".join(result.warnings))
        self.assertIn("efficiency_core_only", "\n".join(result.warnings))

    def test_report_is_normative_and_does_not_rank_incomplete_platforms(self) -> None:
        apple = minimal_package(
            "apple-m4-max",
            "full_host",
            {
                "full_host": "available",
                "performance_core_only": "missing",
                "efficiency_core_only": "missing",
            },
        )
        intel = minimal_package(
            "intel-u7-265kf",
            "full_host",
            {
                "full_host": "available",
                "performance_core_only": "available",
                "efficiency_core_only": "available",
            },
        )
        report = render_cross_platform_report([apple, intel])
        self.assertIn("Cross-Platform CPU Benchmark Schema Report", report)
        self.assertIn("Do not interpret", report)
        self.assertIn("not a platform performance ranking", report)
        self.assertNotIn("fastest platform", report.lower())

    def test_load_package_reads_json_package(self) -> None:
        package = minimal_package(
            "intel-u7-265kf",
            "performance_core_only",
            {
                "full_host": "available",
                "performance_core_only": "available",
                "efficiency_core_only": "available",
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "benchmark_package.json"
            path.write_text(json.dumps(package), encoding="utf-8")
            self.assertEqual(load_package(path)["run_profile"], "performance_core_only")


if __name__ == "__main__":
    unittest.main()
