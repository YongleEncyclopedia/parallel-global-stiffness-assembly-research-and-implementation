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
from unittest import mock


TEST_DIRECTORY = Path(__file__).resolve().parent
if str(TEST_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_DIRECTORY))

from report_test_fixture import (  # noqa: E402
    BENCHMARK_SCHEMA_V1,
    BENCHMARK_SCHEMA_V2,
    BENCHMARK_SCHEMA_V3,
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
        self.assertEqual(bundle.benchmark_summary["schema_version"], BENCHMARK_SCHEMA_V2)
        self.assertEqual(len(bundle.csv_rows), 6)
        self.assertEqual(bundle.junit_testcase_names, JUNIT_NAMES)
        self.assertEqual(
            set(bundle.artifact_paths),
            {"ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md"},
        )
        self.assertEqual(bundle.recomputed_gate["status"], "NOT_APPLICABLE_GENERATED_CASE")
        self.assertIn("serial", bundle.recomputed_statistics)
        self.assertEqual(before, after)

    def test_v2_uses_manifest_bound_csv_snapshot_after_path_swap(self) -> None:
        fixture = EvidenceFixture(self.root)
        csv_path = fixture.root / "benchmark_samples.csv"
        bound_csv = csv_path.read_bytes()
        validate_artifacts = REPORT._validate_artifacts

        def swap_path_after_hash_validation(*args, **kwargs):
            paths, contents = validate_artifacts(*args, **kwargs)
            lines = csv_path.read_text(encoding="utf-8").splitlines()
            csv_path.write_text(
                "\n".join([lines[0], *reversed(lines[1:])]) + "\n",
                encoding="utf-8",
            )
            return paths, contents

        with mock.patch.object(
            REPORT,
            "_validate_artifacts",
            side_effect=swap_path_after_hash_validation,
        ):
            bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)

        self.assertNotEqual(csv_path.read_bytes(), bound_csv)
        self.assertEqual(
            (bundle.csv_rows[0]["thread_count"], bundle.csv_rows[0]["sample_index"]),
            (1, 0),
        )

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
                "serial_symbolic_cv_requirement_met": False,
                "serial_numeric_cv_requirement_met": False,
                "scatter_requirement_met": False,
                "formal_requirements_met": False,
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

    def test_complete_formal_technical_evidence_gate_is_pass(self) -> None:
        fixture = EvidenceFixture(
            self.root,
            evidence_level="formal",
            report_intent="delivery",
            schema_version=BENCHMARK_SCHEMA_V3,
        )
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "PASS")
        self.assertEqual(bundle.recomputed_gate["numeric_thread_count"], 2)
        self.assertEqual(bundle.recomputed_gate["symbolic_thread_count"], 2)

        report = REPORT.render_report(bundle)
        self.assertIn("Scatter plan 正确性", report)
        self.assertIn("串行符号 $CV$", report)
        self.assertIn("串行数值 $CV$", report)

    def test_v1_local_smoke_remains_read_only_compatible(self) -> None:
        fixture = EvidenceFixture(self.root, schema_version=BENCHMARK_SCHEMA_V1)
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "LOCAL_SMOKE")
        self.assertEqual(bundle.benchmark_summary["schema_version"], BENCHMARK_SCHEMA_V1)

    def test_v1_formal_or_delivery_evidence_is_rejected(self) -> None:
        variants = (
            {"evidence_level": "formal", "report_intent": "delivery"},
            {"evidence_level": "local-smoke", "report_intent": "delivery"},
        )
        for index, arguments in enumerate(variants):
            with self.subTest(arguments=arguments):
                fixture = EvidenceFixture(
                    self.root / str(index),
                    schema_version=BENCHMARK_SCHEMA_V1,
                    **arguments,
                )
                with self.assertRaisesRegex(
                    REPORT.EvidenceValidationError, "v1|legacy|formal|delivery"
                ):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_schema_valid_nonzero_correctness_evidence_is_retained_as_fail(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.summary["correctness"].update(
            {"relative_frobenius_error": 2.0e-8, "status": "FAIL"}
        )
        for row in fixture.rows:
            row.update(
                {
                    "relative_frobenius_error": "2e-8",
                    "matrix_correctness_status": "FAIL",
                }
            )
        fixture.manifest["status"] = "FAIL"
        fixture.manifest["tasks"][-1].update(
            {
                "status": "FAIL",
                "returncode": 1,
                "exit_code": 1,
                "error": "matrix correctness status is not PASS",
            }
        )
        fixture.write_csv()
        fixture.write_summary()
        fixture.refresh_artifacts()

        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "FAIL")

    def test_schema_valid_root_structure_failure_is_retained_as_fail(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.summary["correctness"].update(
            {
                "structure_matches": False,
                "relative_frobenius_error": sys.float_info.max,
                "max_absolute_error": sys.float_info.max,
                "status": "FAIL",
            }
        )
        for row in fixture.rows:
            row.update(
                {
                    "relative_frobenius_error": repr(sys.float_info.max),
                    "max_absolute_error": repr(sys.float_info.max),
                    "matrix_correctness_status": "FAIL",
                }
            )
        fixture.manifest["status"] = "FAIL"
        fixture.manifest["tasks"][-1].update(
            {
                "status": "FAIL",
                "returncode": 1,
                "exit_code": 1,
                "error": "matrix structure does not match",
            }
        )
        fixture.write_csv()
        fixture.write_summary()
        fixture.refresh_artifacts()

        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        self.assertEqual(bundle.report_status, "FAIL")
        report = REPORT.render_report(bundle)
        self.assertIn("不可评估", report)
        self.assertNotIn(repr(sys.float_info.max), report)

    def test_formal_technical_evidence_gate_fail_with_retained_evidence_is_fail(self) -> None:
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
        for command in (
            fixture.manifest["commands"]["benchmark"],
            fixture.manifest["tasks"][3]["command"],
        ):
            command[command.index("--threads-list") + 1] = "1,4,2,8,16"
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
    def test_identity_checks_is_a_stable_manifest_list(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.manifest.pop("identity_checks")
        fixture.write_manifest()
        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

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

    def test_v2_boolean_text_is_exact_lowercase_and_bound_to_summary(self) -> None:
        for index, value in enumerate(("True", "FALSE", "1")):
            with self.subTest(value=value):
                fixture = EvidenceFixture(self.root / f"text-{index}")
                fixture.rows[0]["symbolic_plan_matches_serial"] = value
                fixture.write_csv()
                self.assert_csv_rejected(fixture)

        fixture = EvidenceFixture(self.root / "false-tamper")
        fixture.rows[0]["symbolic_plan_matches_serial"] = "false"
        fixture.write_csv()
        self.assert_csv_rejected(fixture)

    def test_raw_thread_and_root_scatter_tampering_is_rejected(self) -> None:
        mutations = (
            lambda fixture: fixture.summary["raw_samples"][0].update(
                {"symbolic_plan_matches_serial": False}
            ),
            lambda fixture: fixture.summary["per_thread_measured_statistics"][0].update(
                {"symbolic_plan_match_count": 0}
            ),
            lambda fixture: fixture.summary["per_thread_measured_statistics"][0].update(
                {"scatter_status": "FAIL"}
            ),
            lambda fixture: fixture.summary["scatter_correctness"].update(
                {"numeric_setup_plan_match_count": 0}
            ),
            lambda fixture: fixture.summary["scatter_correctness"].update(
                {"status": "FAIL"}
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / f"scatter-{index}")
                mutate(fixture)
                fixture.write_summary()
                fixture.refresh_artifacts()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

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
    def test_serial_cv_cannot_be_forged_to_formal_pass(self) -> None:
        fixture = EvidenceFixture(
            self.root, evidence_level="formal", report_intent="delivery"
        )
        serial_values = [5.0, 10.0, 10.0, 10.0, 10.0, 10.0, 15.0]
        for row in fixture.rows:
            sample_index = int(row["sample_index"])
            if sample_index >= fixture.warmup:
                row["serial_symbolic_ms"] = str(
                    serial_values[sample_index - fixture.warmup]
                )
        fixture.summary["serial_measured_statistics"]["symbolic_total_ms"] = (
            REPORT._statistics(serial_values)
        )
        fixture.write_csv()
        fixture.write_summary()
        fixture.refresh_artifacts()

        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_root_tet4_and_hex8_reference_scaled_tolerances_are_recomputed(self) -> None:
        targets = (
            ("root", lambda fixture: fixture.summary["correctness"]),
            (
                "Tet4",
                lambda fixture: fixture.summary["validation_cases"][0]["matrix"],
            ),
            (
                "Hex8",
                lambda fixture: fixture.summary["validation_cases"][1]["matrix"],
            ),
        )
        mutations = (
            lambda matrix: matrix.update({"max_absolute_tolerance": 2.0e-8}),
            lambda matrix: matrix.update({"reference_max_absolute_value": 0.5}),
            lambda matrix: matrix.update(
                {"max_absolute_error": 1.0, "max_absolute_tolerance": 2.0}
            ),
        )
        for target_name, select in targets:
            for mutation_index, mutate in enumerate(mutations):
                with self.subTest(target=target_name, mutation=mutation_index):
                    fixture = EvidenceFixture(
                        self.root / f"{target_name}-{mutation_index}"
                    )
                    mutate(select(fixture))
                    if target_name == "root" and mutation_index == 2:
                        for row in fixture.rows:
                            row["max_absolute_error"] = "1.0"
                        fixture.write_csv()
                    fixture.write_summary()
                    fixture.refresh_artifacts()
                    with self.assertRaises(REPORT.EvidenceValidationError):
                        REPORT.validate_evidence_bundle(fixture.manifest_path)

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
    def test_formal_identity_checks_are_ordered_successful_and_bound_to_start(self) -> None:
        mutations = (
            lambda data: data.pop("identity_checks"),
            lambda data: data["identity_checks"].reverse(),
            lambda data: data["identity_checks"][0].update(
                {"status": "FAIL", "errors": ["source drift"]}
            ),
            lambda data: data["identity_checks"][1]["source"].update(
                {"commit_sha": "b" * 40}
            ),
            lambda data: data["identity_checks"][2]["input"].update(
                {"sha256": "0" * 64}
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(
                    self.root / str(index),
                    evidence_level="formal",
                    report_intent="delivery",
                )
                mutate(fixture.manifest)
                fixture.write_manifest()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

    def test_formal_command_paths_use_host_independent_pure_path_semantics(self) -> None:
        self.assertIsNotNone(
            REPORT._absolute_pure_path(r"C:\build\delivery", windows=True)
        )
        self.assertIsNotNone(
            REPORT._absolute_pure_path(r"\\server\share\evidence", windows=True)
        )
        self.assertIsNone(
            REPORT._absolute_pure_path(r"C:relative\build", windows=True)
        )
        self.assertIsNone(REPORT._absolute_pure_path("/posix/build", windows=True))
        self.assertIsNotNone(
            REPORT._absolute_pure_path("/posix/build", windows=False)
        )
        self.assertIsNone(
            REPORT._absolute_pure_path(r"C:\build\delivery", windows=False)
        )
        self.assertTrue(
            REPORT._same_pure_path(
                r"C:\BUILD\delivery", r"c:\build\delivery", windows=True
            )
        )
        self.assertTrue(
            REPORT._program_is(r"C:\tools\cmake.exe", "cmake", windows=True)
        )
        self.assertTrue(
            REPORT._program_is(
                r"C:\build\bin\Release\csc3_demo_benchmark.exe",
                "csc3_demo_benchmark",
                windows=True,
            )
        )

    def test_generated_grid_command_semantics_are_bound(self) -> None:
        fixture = EvidenceFixture(self.root)
        self.assertEqual(
            REPORT._formal_command_semantic_errors(
                fixture.manifest, fixture.manifest["commands"]
            ),
            (),
        )
        for command in (
            fixture.manifest["commands"]["benchmark"],
            fixture.manifest["tasks"][3]["command"],
        ):
            command[command.index("--nx") + 1] = "2"
        self.assertTrue(
            REPORT._formal_command_semantic_errors(
                fixture.manifest, fixture.manifest["commands"]
            )
        )

    def test_formal_task_and_command_schema_semantics_are_exact(self) -> None:
        def update_bound_command(data: dict[str, object], name: str, command: list[str]) -> None:
            data["commands"][name] = command
            task = next(task for task in data["tasks"] if task["name"] == name)
            task["command"] = list(command)

        def replace_argument(
            data: dict[str, object], name: str, option: str, replacement: str
        ) -> None:
            command = list(data["commands"][name])
            command[command.index(option) + 1] = replacement
            update_bound_command(data, name, command)

        mutations = (
            lambda data: data["tasks"].reverse(),
            lambda data: data["tasks"][0].pop("command"),
            lambda data: data["tasks"][0].pop("cwd"),
            lambda data: data["tasks"][0].update({"cwd": "relative/source"}),
            lambda data: data["tasks"][0].update({"cwd": r"C:\source"}),
            lambda data: data["tasks"][0].pop("environment"),
            lambda data: data["tasks"][0]["environment"].update(
                {"OMP_DYNAMIC": "true"}
            ),
            lambda data: data["tasks"][0].update({"command": ["true"]}),
            lambda data: update_bound_command(data, "configure", ["true"]),
            lambda data: update_bound_command(
                data,
                "configure",
                [
                    data["commands"]["configure"][0],
                    "-B",
                    data["commands"]["configure"][4],
                    "--preset",
                    "delivery",
                ],
            ),
            lambda data: replace_argument(data, "configure", "--preset", "debug"),
            lambda data: replace_argument(
                data, "configure", "-B", str(self.root / "other-build")
            ),
            lambda data: replace_argument(
                data, "build", "--config", "RelWithDebInfo"
            ),
            lambda data: replace_argument(
                data, "build", "--build", str(self.root / "other-build")
            ),
            lambda data: replace_argument(
                data, "ctest", "--test-dir", str(self.root / "other-build")
            ),
            lambda data: replace_argument(
                data, "ctest", "--label-regex", "not-ci"
            ),
            lambda data: replace_argument(
                data, "ctest", "--output-junit", str(self.root / "other.xml")
            ),
            lambda data: replace_argument(data, "benchmark", "--case", "generated-tet4"),
            lambda data: replace_argument(data, "benchmark", "--threads-list", "1,4,2,8,16"),
            lambda data: replace_argument(data, "benchmark", "--warmup", "3"),
            lambda data: replace_argument(data, "benchmark", "--repeat", "8"),
            lambda data: replace_argument(data, "benchmark", "--amortization-count", "3"),
            lambda data: replace_argument(data, "benchmark", "--evidence-level", "local-smoke"),
            lambda data: replace_argument(
                data,
                "benchmark",
                "--samples-csv",
                str(self.root / "other.csv"),
            ),
            lambda data: replace_argument(
                data,
                "benchmark",
                "--summary-json",
                str(self.root / "other.json"),
            ),
            lambda data: replace_argument(
                data,
                "benchmark",
                "--input",
                "/controlled/input/other.inp",
            ),
            lambda data: update_bound_command(
                data,
                "benchmark",
                [str(self.root / "not_the_benchmark")]
                + list(data["commands"]["benchmark"])[1:],
            ),
            lambda data: update_bound_command(
                data,
                "benchmark",
                list(data["commands"]["benchmark"]) + ["--unknown"],
            ),
            lambda data: data["commands"].update({"unknown": ["true"]}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(
                    self.root / str(index),
                    evidence_level="formal",
                    report_intent="delivery",
                )
                mutate(fixture.manifest)
                fixture.write_manifest()
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.validate_evidence_bundle(fixture.manifest_path)

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
            lambda data: data["benchmark"].update({"warmup_count": 3}),
            lambda data: data["benchmark"].update({"repeat_count": 6}),
            lambda data: data["benchmark"].update({"repeat_count": 8}),
            lambda data: data["benchmark"].update({"amortization_count": 2}),
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
    def test_report_inventory_matches_ordered_ci_contract(self) -> None:
        expected_path = (
            Path(__file__).resolve().parents[1]
            / "ctest"
            / "expected-ci-tests.txt"
        )
        expected_names = tuple(
            line.strip()
            for line in expected_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

        self.assertEqual(REPORT.JUNIT_NAMES, expected_names)
        self.assertEqual(JUNIT_NAMES, expected_names)

    def test_cmake_keeps_one_python_ctest_and_discovers_all_python_tests(self) -> None:
        cmake = (Path(__file__).resolve().parents[2] / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )
        self.assertEqual(cmake.count("NAME Csc3DemoPythonTests"), 1)
        self.assertIn("-p test_*.py", cmake)
        self.assertNotIn("-p test_run_benchmark.py", cmake)


if __name__ == "__main__":
    unittest.main()
