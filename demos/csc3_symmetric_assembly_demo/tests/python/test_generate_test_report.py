#!/usr/bin/env python3
"""Contract tests for artifact-backed report evidence validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIRECTORY = Path(__file__).resolve().parent
if str(TEST_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_DIRECTORY))

from report_test_fixture import (  # noqa: E402
    CSV_HEADER,
    EvidenceFixture,
    FIXTURE_WINDHUB_SIZE,
    JUNIT_NAMES,
)


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_test_report.py"
SPEC = importlib.util.spec_from_file_location("csc3_generate_test_report", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load report verifier: {SCRIPT}")
REPORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPORT
SPEC.loader.exec_module(REPORT)


class TemporaryDirectory(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-report-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()


class HappyPathTests(TemporaryDirectory):
    def test_local_happy_path_recomputes_local_smoke_without_writing(self) -> None:
        fixture = EvidenceFixture(self.root)
        before = {path.relative_to(self.root) for path in self.root.rglob("*")}
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        after = {path.relative_to(self.root) for path in self.root.rglob("*")}

        self.assertEqual(bundle.report_status, "LOCAL_SMOKE")
        self.assertEqual(bundle.manifest["status"], "LOCAL_SMOKE")
        self.assertEqual(bundle.benchmark_summary["schema_version"], "csc3-demo-benchmark-v1")
        self.assertEqual(len(bundle.csv_rows), 6)
        self.assertEqual(bundle.junit_testcase_names, JUNIT_NAMES)
        self.assertEqual(
            set(bundle.artifact_paths),
            {"ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md"},
        )
        self.assertEqual(bundle.recomputed_gate["status"], "NOT_APPLICABLE_GENERATED_CASE")
        self.assertIn("serial", bundle.recomputed_statistics)
        self.assertEqual(before, after)

    def test_delivery_intent_with_nonformal_evidence_is_blocked(self) -> None:
        fixture = EvidenceFixture(self.root, report_intent="delivery")
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "BLOCKED")

    def test_generated_threshold_eligible_data_remains_entirely_not_applicable(self) -> None:
        fixture = EvidenceFixture(self.root)
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(
            bundle.recomputed_gate,
            {
                "status": "NOT_APPLICABLE_GENERATED_CASE",
                "applicable": False,
                "performance_requirements_met": False,
                "numeric_requirement_met": False,
                "symbolic_requirement_met": False,
                "numeric_thread_count": 0,
                "symbolic_thread_count": 0,
                "numeric_speedup_threshold": 1.5,
                "symbolic_speedup_threshold": 1.0,
                "maximum_coefficient_of_variation": 0.05,
            },
        )

    def test_nonformal_windhub_retains_eligibility_without_claiming_requirements(self) -> None:
        fixture = EvidenceFixture(self.root, windhub=True)
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "LOCAL_SMOKE")
        self.assertEqual(bundle.recomputed_gate["status"], "NON_FORMAL_LOCAL_SMOKE")
        self.assertTrue(bundle.recomputed_gate["numeric_requirement_met"])
        self.assertTrue(bundle.recomputed_gate["symbolic_requirement_met"])
        self.assertFalse(bundle.recomputed_gate["performance_requirements_met"])

    def test_nonformal_hex8_windhub_uses_windows_input_basename(self) -> None:
        fixture = EvidenceFixture(self.root, windhub=True)
        input_facts = fixture.manifest["input"]
        self.assertIsInstance(input_facts, dict)
        input_facts["path"] = r"C:\evidence\tiny-hex8.inp"
        input_facts.pop("repository_relative_path")
        fixture.manifest["environment"]["system"] = "Windows"
        fixture.summary["case_sizes"].update(
            {"case_name": "tiny-hex8.inp", "element_type": "Hex8"}
        )
        for row in fixture.rows:
            row.update({"case_name": "tiny-hex8.inp", "element_type": "Hex8"})
        fixture.write_csv()
        fixture.write_summary()
        fixture.refresh_artifacts()
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "LOCAL_SMOKE")

    def test_windhub_repository_relative_path_has_basename_priority(self) -> None:
        fixture = EvidenceFixture(self.root, windhub=True)
        input_facts = fixture.manifest["input"]
        self.assertIsInstance(input_facts, dict)
        input_facts["path"] = r"C:\unrelated\wrong-name.inp"
        fixture.write_manifest()
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(
            bundle.benchmark_summary["case_sizes"]["case_name"],
            "3d-WindTurbineHub.inp",
        )
        self.assertEqual(bundle.recomputed_gate["numeric_thread_count"], 2)

    def test_complete_formal_gate_pass_is_pass(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "PASS")
        self.assertEqual(bundle.recomputed_gate["numeric_thread_count"], 2)
        self.assertEqual(bundle.recomputed_gate["symbolic_thread_count"], 2)

    def test_formal_gate_fail_with_retained_evidence_is_fail(self) -> None:
        fixture = EvidenceFixture(
            self.root,
            evidence_level="formal",
            report_intent="delivery",
            formal_gate_pass=False,
        )
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "FAIL")
        self.assertEqual(bundle.recomputed_gate["status"], "FAIL")

    def test_formal_evidence_with_non_delivery_intent_is_blocked(self) -> None:
        fixture = EvidenceFixture(
            self.root, evidence_level="formal", report_intent="local-smoke"
        )
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "BLOCKED")

    def test_amd64_is_an_allowed_formal_architecture(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        fixture.manifest["environment"]["architecture"] = "amd64"
        fixture.write_manifest()
        self.assertEqual(
            REPORT.validate_evidence_bundle(fixture.manifest_path).report_status,
            "PASS",
        )

    def test_serial_statistics_take_each_measured_index_once(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(
            bundle.recomputed_statistics["serial"]["symbolic_total_ms"]["sample_count"],
            fixture.repeat,
        )

    def test_csv_row_order_does_not_select_the_formal_gate(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        fixture.rows.reverse()
        fixture.write_csv()
        fixture.refresh_artifacts()
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.recomputed_gate["numeric_thread_count"], 2)

    def test_requested_order_selects_the_first_eligible_formal_thread(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        requested = [1, 4, 2, 8, 16]
        fixture.manifest["benchmark"]["requested_thread_counts"] = requested
        fixture.manifest["benchmark"]["observed_thread_counts"] = requested
        fixture.summary["configuration"]["thread_counts"] = requested
        rows_by_thread = {
            row["thread_count"]: row
            for row in fixture.summary["per_thread_measured_statistics"]
        }
        fixture.summary["per_thread_measured_statistics"] = [
            rows_by_thread[thread] for thread in requested
        ]
        fixture.summary["performance_gate"]["numeric_thread_count"] = 4
        fixture.summary["performance_gate"]["symbolic_thread_count"] = 4
        fixture.write_summary()
        fixture.refresh_artifacts()
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.recomputed_gate["numeric_thread_count"], 4)
        self.assertEqual(bundle.recomputed_gate["symbolic_thread_count"], 4)


class ManifestAndArtifactTests(TemporaryDirectory):
    def test_manifest_schema_types_source_and_time_are_strict(self) -> None:
        variants = (
            (("schema_version",), "wrong"),
            (("status",), "PENDING"),
            (("source", "commit_sha"), "abc"),
            (("source", "source_dirty_at_start"), 0),
            (("source", "branch"), ""),
            (("source", "demo_version"), "0.2"),
            (("started_at_utc",), "2026-07-13T00:00:00+00:00"),
            (("ended_at_utc",), "2026-07-12T23:59:59Z"),
            (("tasks",), {}),
            (("commands",), []),
        )
        for path, value in variants:
            with self.subTest(path=path, value=value):
                case_root = self.root / "-".join(path)
                fixture = EvidenceFixture(case_root)
                target = fixture.manifest
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                fixture.write_manifest()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_thread_counts_and_binding_environment_are_exact(self) -> None:
        for mutate in (
            lambda manifest: manifest["benchmark"].update(
                {"requested_thread_counts": [1, 1]}
            ),
            lambda manifest: manifest["benchmark"].update(
                {"observed_thread_counts": [1]}
            ),
            lambda manifest: manifest["benchmark"].update(
                {"observed_thread_counts": [2, 1]}
            ),
            lambda manifest: manifest["benchmark"].update({"warmup_count": -1}),
            lambda manifest: manifest["benchmark"].update({"repeat_count": 0}),
            lambda manifest: manifest["benchmark"].update({"amortization_count": 0}),
            lambda manifest: manifest["binding_environment"].update(
                {"OMP_DYNAMIC": "true"}
            ),
            lambda manifest: manifest["binding_environment"].update({"EXTRA": "1"}),
        ):
            with self.subTest(mutate=mutate):
                fixture = EvidenceFixture(self.root / str(id(mutate)))
                mutate(fixture.manifest)
                fixture.write_manifest()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_unsafe_duplicate_and_missing_artifact_bindings_are_rejected(self) -> None:
        unsafe_paths = ("../ctest.xml", "/tmp/ctest.xml", "C:/ctest.xml", "nested\\ctest.xml", "a//b")
        for unsafe in unsafe_paths:
            with self.subTest(path=unsafe):
                fixture = EvidenceFixture(self.root / str(len(list(self.root.iterdir()))))
                fixture.manifest["artifacts"][0]["path"] = unsafe
                fixture.write_manifest()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

        duplicate = EvidenceFixture(self.root / "duplicate")
        duplicate.manifest["artifacts"].append(copy.deepcopy(duplicate.manifest["artifacts"][0]))
        duplicate.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(duplicate.manifest_path)

        missing = EvidenceFixture(self.root / "missing")
        missing.manifest["artifacts"] = [
            item for item in missing.manifest["artifacts"]
            if item["path"] != "summary.md"
        ]
        missing.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(missing.manifest_path)

    def test_size_sha_and_additional_artifact_are_validated(self) -> None:
        size = EvidenceFixture(self.root / "size")
        size.manifest["artifacts"][0]["size_bytes"] += 1
        size.write_manifest()
        with self.assertRaisesRegex(REPORT.EvidenceValidationError, "size"):
            REPORT.validate_evidence_bundle(size.manifest_path)

        digest = EvidenceFixture(self.root / "digest")
        digest.manifest["artifacts"][0]["sha256"] = "0" * 64
        digest.write_manifest()
        with self.assertRaisesRegex(REPORT.EvidenceValidationError, "SHA-256"):
            REPORT.validate_evidence_bundle(digest.manifest_path)

        additional = EvidenceFixture(self.root / "additional")
        (additional.root / "extra.txt").write_text("extra", encoding="utf-8")
        additional.refresh_artifacts(
            ["ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md", "extra.txt"]
        )
        additional.manifest["artifacts"][-1]["sha256"] = "f" * 64
        additional.write_manifest()
        with self.assertRaisesRegex(REPORT.EvidenceValidationError, "SHA-256"):
            REPORT.validate_evidence_bundle(additional.manifest_path)

    def test_all_artifacts_are_hashed_before_any_content_is_parsed(self) -> None:
        fixture = EvidenceFixture(self.root)
        (fixture.root / "ctest.xml").write_text("not xml", encoding="utf-8")
        fixture.refresh_artifacts()
        fixture.manifest["artifacts"][1]["sha256"] = "0" * 64
        fixture.write_manifest()
        with self.assertRaisesRegex(REPORT.EvidenceValidationError, "SHA-256"):
            REPORT.validate_evidence_bundle(fixture.manifest_path)


class JunitContractTests(TemporaryDirectory):
    def assert_junit_rejected(self, fixture: EvidenceFixture) -> None:
        fixture.refresh_artifacts()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_missing_extra_duplicate_and_empty_names_are_rejected(self) -> None:
        variants = (
            JUNIT_NAMES[:-1],
            JUNIT_NAMES + ("ExtraTest",),
            JUNIT_NAMES[:-1] + (JUNIT_NAMES[0],),
            JUNIT_NAMES[:-1] + ("",),
        )
        for index, names in enumerate(variants):
            with self.subTest(names=names):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.write_junit(names=names)
                self.assert_junit_rejected(fixture)

    def test_failure_error_skip_disabled_and_notrun_are_rejected(self) -> None:
        variants = (
            ({"failures": "1"}, {}, {0: "<failure/>"}),
            ({"errors": "1"}, {}, {0: "<error/>"}),
            ({"skipped": "1"}, {}, {0: "<skipped/>"}),
            ({"disabled": "1"}, {0: {"disabled": "true"}}, {}),
            ({}, {0: {"status": "notrun"}}, {}),
            ({}, {0: {"status": "not-run"}}, {}),
            ({}, {0: {"result": "skipped"}}, {}),
            ({}, {0: {"status": "failed"}}, {}),
            ({}, {0: {"result": "error"}}, {}),
        )
        for index, (counts, attributes, children) in enumerate(variants):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.write_junit(
                    root_counts=counts,
                    testcase_attributes=attributes,
                    testcase_children=children,
                )
                self.assert_junit_rejected(fixture)

    def test_root_declared_counts_must_be_zero_integers(self) -> None:
        for value in ("-1", "false", "0.0"):
            with self.subTest(value=value):
                fixture = EvidenceFixture(self.root / value.replace(".", "_"))
                fixture.write_junit(root_counts={"disabled": value})
                self.assert_junit_rejected(fixture)

    def test_optional_undeclared_error_count_matches_real_ctest_junit(self) -> None:
        fixture = EvidenceFixture(self.root)
        junit_path = fixture.root / "ctest.xml"
        junit_path.write_text(
            junit_path.read_text(encoding="utf-8").replace(' errors="0"', ""),
            encoding="utf-8",
        )
        fixture.refresh_artifacts()
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.junit_testcase_names, JUNIT_NAMES)


class CsvContractTests(TemporaryDirectory):
    def validate_after_csv_write(self, fixture: EvidenceFixture) -> None:
        fixture.refresh_artifacts()
        REPORT.validate_evidence_bundle(fixture.manifest_path)

    def assert_csv_rejected(self, fixture: EvidenceFixture) -> None:
        fixture.refresh_artifacts()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_header_drift_duplicate_fields_and_trailing_data_are_rejected(self) -> None:
        for index, header in enumerate((CSV_HEADER[:-1], CSV_HEADER[:-1] + (CSV_HEADER[0],))):
            with self.subTest(header=header):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.write_csv(header)
                self.assert_csv_rejected(fixture)

        trailing = EvidenceFixture(self.root / "trailing")
        with (trailing.root / "benchmark_samples.csv").open("a", encoding="utf-8") as stream:
            stream.write(",unexpected\n")
        self.assert_csv_rejected(trailing)

    def test_bad_integer_and_float_text_are_rejected(self) -> None:
        variants = (
            ("thread_count", "true"),
            ("sample_index", "+1"),
            ("estimated_persistent_bytes", "1_000"),
            ("symbolic_total_ms", "nan"),
            ("numeric_total_ms", "inf"),
            ("amortized_total_ms", "-1"),
        )
        for index, (field, value) in enumerate(variants):
            with self.subTest(field=field, value=value):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.rows[0][field] = value
                fixture.write_csv()
                self.assert_csv_rejected(fixture)

    def test_sample_identity_kind_count_and_serial_drift_are_rejected(self) -> None:
        mutations = (
            lambda fixture: fixture.rows[1].update({"sample_index": fixture.rows[0]["sample_index"]}),
            lambda fixture: fixture.rows[0].update({"sample_kind": "measured"}),
            lambda fixture: fixture.rows.pop(),
            lambda fixture: fixture.rows[-1].update({"serial_symbolic_ms": "10.25"}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / str(index))
                mutate(fixture)
                fixture.write_csv()
                self.assert_csv_rejected(fixture)

    def test_phase_and_amortized_identities_are_rejected(self) -> None:
        variants = (
            ("symbolic_total_ms", "0"),
            ("numeric_total_ms", "0"),
            ("amortized_total_ms", "999"),
        )
        for index, (field, value) in enumerate(variants):
            with self.subTest(field=field):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.rows[0][field] = value
                fixture.write_csv()
                self.assert_csv_rejected(fixture)

    def test_amortized_tolerance_uses_expected_value_only(self) -> None:
        fixture = EvidenceFixture(self.root)
        expected = float(fixture.rows[0]["amortized_total_ms"])
        fixture.rows[0]["amortized_total_ms"] = str(
            expected + 1.0002e-12 * max(1.0, abs(expected))
        )
        fixture.write_csv()
        self.assert_csv_rejected(fixture)

    def test_cross_file_fields_and_csv_speedups_are_bound(self) -> None:
        variants = (
            ("case_name", "forged"),
            ("element_type", "Hex8"),
            ("nnz", "301"),
            ("relative_frobenius_error", "2e-15"),
            ("estimated_persistent_bytes", "123457"),
            ("performance_evidence_level", "ci-smoke"),
            ("symbolic_speedup", "99"),
            ("numeric_speedup", "99"),
        )
        for index, (field, value) in enumerate(variants):
            with self.subTest(field=field):
                fixture = EvidenceFixture(self.root / str(index))
                fixture.rows[0][field] = value
                fixture.write_csv()
                self.assert_csv_rejected(fixture)

    def test_coordinated_csv_and_json_case_forgery_is_rejected(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.summary["case_sizes"].update(
            {
                "case_name": "cube_hex8_1x1x1",
                "element_type": "Hex8",
                "element_count": 1,
            }
        )
        for row in fixture.rows:
            row.update(
                {
                    "case_name": "cube_hex8_1x1x1",
                    "element_type": "Hex8",
                    "element_count": "1",
                }
            )
        fixture.write_csv()
        fixture.write_summary()
        fixture.refresh_artifacts()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)


class StatisticsGateAndValidationTests(TemporaryDirectory):
    def test_every_summary_statistic_class_is_recomputed_from_csv(self) -> None:
        statistic_keys = (
            "sample_count",
            "mean_ms",
            "median_ms",
            "population_standard_deviation_ms",
            "minimum_ms",
            "maximum_ms",
            "coefficient_of_variation",
        )
        for index, key in enumerate(statistic_keys):
            with self.subTest(key=key):
                fixture = EvidenceFixture(self.root / str(index))
                statistics = fixture.summary["per_thread_measured_statistics"][1]["symbolic_total_ms"]
                statistics[key] = statistics[key] + 1
                fixture.write_summary()
                fixture.refresh_artifacts()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_serial_statistics_numeric_algorithm_speedup_cv_and_gate_are_recomputed(self) -> None:
        mutations = (
            lambda summary: summary["serial_measured_statistics"]["numeric_total_ms"].update({"mean_ms": 9.0}),
            lambda summary: summary["per_thread_measured_statistics"][1]["numeric_algorithm_ms"].update({"median_ms": 4.1}),
            lambda summary: summary["per_thread_measured_statistics"][1].update({"symbolic_speedup": 1.9}),
            lambda summary: summary["per_thread_measured_statistics"][1]["numeric_algorithm_ms"].update({"coefficient_of_variation": 0.01}),
            lambda summary: summary["performance_gate"].update({"numeric_thread_count": 2}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / str(index))
                mutate(fixture.summary)
                fixture.write_summary()
                fixture.refresh_artifacts()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_per_thread_summary_order_matches_requested_order(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.summary["per_thread_measured_statistics"].reverse()
        fixture.write_summary()
        fixture.refresh_artifacts()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_validation_case_schema_order_metric_and_status_are_rejected(self) -> None:
        mutations = (
            lambda summary: summary.update({"validation_cases_schema_version": "wrong"}),
            lambda summary: summary["validation_cases"].reverse(),
            lambda summary: summary["validation_cases"][0]["displacement"].update({"parallel_relative_residual": 1.1e-10}),
            lambda summary: summary["validation_cases"][1].update({"status": "FAIL"}),
            lambda summary: summary["validation_thresholds"].update({"relative_displacement_error_max": 1e-7}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / str(index))
                mutate(fixture.summary)
                fixture.write_summary()
                fixture.refresh_artifacts()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)


class FormalProvenanceTests(TemporaryDirectory):
    def test_each_formal_provenance_condition_prevents_pass(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        manifest = fixture.manifest
        mutations = (
            lambda data: data["environment"].update({"system": "Darwin"}),
            lambda data: data["environment"].update({"architecture": "arm64"}),
            lambda data: data["environment"].update({"cpu_vendor": "AuthenticAMD"}),
            lambda data: data["environment"].update({"controlled_host_id": ""}),
            lambda data: data["source"].update({"source_dirty_at_start": True}),
            lambda data: data["toolchain"].update({"compiler": "unknown", "compiler_id": "unknown"}),
            lambda data: data["toolchain"].update({"cmake_version": "unknown"}),
            lambda data: data["toolchain"]["openmp"].update({"found": False}),
            lambda data: data["toolchain"]["openmp"].update({"require_openmp": False}),
            lambda data: data["input"].update({"repository_relative_path": "other.inp"}),
            lambda data: data["input"].update({"size_bytes": FIXTURE_WINDHUB_SIZE - 1}),
            lambda data: data["input"].update({"sha256": "0" * 64}),
            lambda data: data["input"].update({"head_lfs_size_bytes": FIXTURE_WINDHUB_SIZE - 1}),
            lambda data: data["input"].update({"head_lfs_oid_sha256": "0" * 64}),
            lambda data: data["input"].update({"materialized": False}),
            lambda data: data["input"].update({"tracked": False}),
            lambda data: data["input"].update({"matches_head_lfs": False}),
            lambda data: data["benchmark"].update({"warmup_count": 1}),
            lambda data: data["benchmark"].update({"repeat_count": 6}),
            lambda data: data["benchmark"].update({"requested_thread_counts": [1, 2, 4, 8]}),
            lambda data: data["environment"].update({"physical_core_count": 0}),
            lambda data: data["environment"].update({"physical_core_count": 32}),
            lambda data: data["commands"].pop("configure"),
            lambda data: data["tasks"].pop(0),
            lambda data: data["tasks"].append(copy.deepcopy(data["tasks"][0])),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                bad = copy.deepcopy(manifest)
                mutate(bad)
                self.assertTrue(REPORT._formal_provenance_errors(bad))

    def test_formal_pass_manifest_rejects_any_provenance_defect(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        fixture.manifest["input"]["sha256"] = "0" * 64
        fixture.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_formal_fail_requires_consistent_nonzero_benchmark_exit(self) -> None:
        fixture = EvidenceFixture(
            self.root,
            evidence_level="formal",
            report_intent="delivery",
            formal_gate_pass=False,
        )
        fixture.manifest["tasks"][-1].update({"returncode": 0, "exit_code": 0})
        fixture.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_formal_pass_requires_matching_task_return_and_exit_codes(self) -> None:
        fixture = EvidenceFixture(self.root, evidence_level="formal", report_intent="delivery")
        fixture.manifest["tasks"][0]["exit_code"] = 9
        fixture.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)


class DiscoveryContractTests(unittest.TestCase):
    def test_cmake_keeps_one_runner_ctest_and_discovers_all_python_tests(self) -> None:
        cmake = (Path(__file__).resolve().parents[2] / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        self.assertEqual(cmake.count("NAME Csc3DemoBenchmarkRunner"), 1)
        self.assertIn("-p test_*.py", cmake)
        self.assertNotIn("-p test_run_benchmark.py", cmake)


if __name__ == "__main__":
    unittest.main()
