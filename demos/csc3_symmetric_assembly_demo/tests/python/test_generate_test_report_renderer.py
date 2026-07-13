#!/usr/bin/env python3
"""Contract tests for deterministic CSC3 delivery-report rendering."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_DIRECTORY = Path(__file__).resolve().parent
if str(TEST_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_DIRECTORY))

from report_test_fixture import EvidenceFixture, JUNIT_NAMES  # noqa: E402


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_test_report.py"
SPEC = importlib.util.spec_from_file_location("csc3_generate_test_report_renderer", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load report renderer: {SCRIPT}")
REPORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPORT
SPEC.loader.exec_module(REPORT)

WARNING = "NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE"
SECTIONS = (
    "交付验收结论",
    "算法与 CSC3 数据格式",
    "公共 API 与命名契约",
    "测试环境与工具链",
    "输入、规模与执行参数",
    "自动测试结果",
    "整体刚度矩阵正确性",
    "位移与残差正确性",
    "性能结果",
    "性能门槛",
    "内存证据",
    "限制、风险与授权状态",
    "原始证据与复现命令",
)


class TemporaryDirectory(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-renderer-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def evidence_bytes(fixture: EvidenceFixture) -> dict[str, bytes]:
        paths = [fixture.manifest_path]
        paths.extend(
            fixture.root / str(record["path"])
            for record in fixture.manifest["artifacts"]
        )
        return {str(path.relative_to(fixture.root)): path.read_bytes() for path in paths}


class RendererContractTests(TemporaryDirectory):
    def test_local_report_has_all_sections_and_exact_boundary_warnings(self) -> None:
        fixture = EvidenceFixture(self.root)
        report = REPORT.render_report(REPORT.validate_evidence_bundle(fixture.manifest_path))

        self.assertTrue(report.startswith(WARNING + "\n"))
        self.assertTrue(report.endswith("\n" + WARNING + "\n"))
        self.assertEqual(report.count(WARNING), 2)
        self.assertIn("LOCAL_SMOKE", report)
        self.assertIn(
            "输入文件字节数与 SHA-256：不适用（程序生成，无输入文件）",
            report,
        )
        for number, title in enumerate(SECTIONS, start=1):
            with self.subTest(section=title):
                self.assertIn(f"## {number}. {title}", report)

    def test_report_contains_auditable_contract_metrics_and_provenance(self) -> None:
        fixture = EvidenceFixture(self.root)
        for name, command in fixture.manifest["commands"].items():
            command.append(str(self.root / "secret-working-tree" / name))
        fixture.manifest["commands"]["build"].append(
            "-I" + str(self.root / "secret-working-tree" / "include")
        )
        fixture.manifest["environment"]["cpu_model"] = (
            "processor metadata " + str(self.root / "secret-working-tree" / "cpu.txt")
        )
        fixture.manifest["toolchain"]["openmp"]["flags"] = (
            "-fopenmp -I" + str(self.root / "secret-working-tree" / "omp")
        )
        fixture.manifest["blockers"].append(
            "missing " + str(self.root / "secret-working-tree" / "input.inp")
        )
        fixture.write_manifest()

        report = REPORT.render_report(REPORT.validate_evidence_bundle(fixture.manifest_path))

        for text in (
            "Tet4",
            "Hex8",
            "ElementDofMap",
            "ElementMatrixBatch",
            "AssemblyPlan",
            "SymmetricCscAssembler",
            "build_symbolic_parallel()",
            "assemble_numeric_atomic()",
            "0.2.0",
            "a" * 40,
            "OMP_DYNAMIC=false",
            "OMP_PROC_BIND=close",
            "OMP_PLACES=cores",
            "INTERNAL EVALUATION ONLY",
            "owned_vector_payload_bytes_not_rss",
            "1e-08",
            "1e-10",
            r"\max |K_s|",
            "reference_max_absolute_value",
        ):
            with self.subTest(text=text):
                self.assertIn(text, report)
        for name in JUNIT_NAMES:
            self.assertIn(name, report)
        for artifact in fixture.manifest["artifacts"]:
            self.assertIn(str(artifact["sha256"]), report)
        self.assertNotIn(str(self.root), report)
        self.assertIn("<host-path>/configure", report)
        self.assertIn("<host-path>/include", report)
        self.assertIn("<host-path>/cpu.txt", report)
        self.assertIn("<host-path>/input.inp", report)

    def test_formal_pass_has_explicit_acceptance_without_nonformal_warning(self) -> None:
        fixture = EvidenceFixture(
            self.root, evidence_level="formal", report_intent="delivery"
        )

        report = REPORT.render_report(REPORT.validate_evidence_bundle(fixture.manifest_path))

        self.assertIn("DELIVERY ACCEPTANCE: PASS", report)
        self.assertNotIn(WARNING, report)

    def test_identical_validated_evidence_renders_identical_bytes(self) -> None:
        fixture = EvidenceFixture(self.root)
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)

        first = REPORT.render_report(bundle).encode("utf-8")
        second = REPORT.render_report(bundle).encode("utf-8")

        self.assertEqual(first, second)
        self.assertNotIn(b"\r\n", first)
        self.assertTrue(first.endswith(b"\n"))
        self.assertFalse(first.endswith(b"\n\n"))

    def test_performance_uses_only_recomputed_statistics_and_gate(self) -> None:
        fixture = EvidenceFixture(self.root)
        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        expected = REPORT.render_report(bundle)

        bundle.benchmark_summary["serial_measured_statistics"][
            "symbolic_total_ms"
        ]["median_ms"] = 999.0
        bundle.benchmark_summary["per_thread_measured_statistics"][0][
            "numeric_algorithm_ms"
        ]["median_ms"] = 888.0
        bundle.benchmark_summary["performance_gate"]["status"] = "FORGED"
        bundle.csv_rows[0]["numeric_total_ms"] = 777.0

        self.assertEqual(REPORT.render_report(bundle), expected)

    def test_numeric_timing_basis_and_amortized_formula_are_explicit(self) -> None:
        fixture = EvidenceFixture(self.root)

        report = REPORT.render_report(REPORT.validate_evidence_bundle(fixture.manifest_path))

        self.assertIn("| 1 | 10 | 8 | 13.5 |", report)
        self.assertIn(r"T_{\mathrm{numeric,atomic}}(p)=", report)
        self.assertIn(r"T_{\mathrm{numeric,reset}}(p)+T_{\mathrm{numeric,kernel}}(p)", report)
        self.assertIn(r"+T_{\mathrm{numeric,total}}(p).", report)
        self.assertIn("numeric_total_ms", report)
        self.assertIn("numeric_algorithm_ms", report)

    def test_ctest_table_uses_validated_bundle_name_order(self) -> None:
        fixture = EvidenceFixture(self.root)
        fixture.write_junit(names=reversed(JUNIT_NAMES))
        fixture.refresh_artifacts()

        bundle = REPORT.validate_evidence_bundle(fixture.manifest_path)
        report = REPORT.render_report(bundle)

        self.assertLess(report.index(JUNIT_NAMES[-1]), report.index(JUNIT_NAMES[0]))

    def test_ctest_table_reports_all_ten_validated_tests(self) -> None:
        fixture = EvidenceFixture(self.root)

        report = REPORT.render_report(
            REPORT.validate_evidence_bundle(fixture.manifest_path)
        )

        self.assertIn("CTest 精确执行 $10/10$ 个测试：", report)
        self.assertEqual(len(JUNIT_NAMES), 10)
        for index, name in enumerate(JUNIT_NAMES, start=1):
            self.assertIn(f"| {index} | `{name}` | `PASS` |", report)


class WriterContractTests(TemporaryDirectory):
    def test_formal_fail_and_nonformal_delivery_blocked_are_written(self) -> None:
        cases = (
            (
                "fail",
                {
                    "evidence_level": "formal",
                    "report_intent": "delivery",
                    "formal_gate_pass": False,
                },
                "FAIL",
                "DELIVERY ACCEPTANCE: FAIL",
            ),
            (
                "blocked",
                {"report_intent": "delivery"},
                "BLOCKED",
                "BLOCKED",
            ),
        )
        for name, arguments, expected_status, marker in cases:
            with self.subTest(status=expected_status):
                fixture = EvidenceFixture(self.root / name, **arguments)
                output = self.root / "reports" / f"{name}.md"

                status = REPORT.write_report(fixture.manifest_path, output)

                self.assertEqual(status, expected_status)
                self.assertTrue(output.is_file())
                self.assertIn(marker, output.read_text(encoding="utf-8"))

    def test_existing_output_is_refused_without_mutating_evidence(self) -> None:
        fixture = EvidenceFixture(self.root)
        output = self.root / "report.md"
        output.write_bytes(b"sentinel\n")
        before = self.evidence_bytes(fixture)

        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.write_report(fixture.manifest_path, output)

        self.assertEqual(output.read_bytes(), b"sentinel\n")
        self.assertEqual(self.evidence_bytes(fixture), before)

    def test_manifest_and_every_bound_artifact_are_refused_as_output(self) -> None:
        fixture = EvidenceFixture(self.root)
        before = self.evidence_bytes(fixture)
        overlaps = [fixture.manifest_path]
        overlaps.extend(
            fixture.root / str(record["path"])
            for record in fixture.manifest["artifacts"]
        )

        for output in overlaps:
            with self.subTest(output=output.name):
                with self.assertRaises(REPORT.EvidenceValidationError):
                    REPORT.write_report(fixture.manifest_path, output)
                self.assertEqual(self.evidence_bytes(fixture), before)

    def test_validation_error_precedes_output_directory_creation(self) -> None:
        fixture = EvidenceFixture(self.root / "invalid")
        fixture.manifest["source"]["commit_sha"] = "invalid"
        fixture.write_manifest()
        before = self.evidence_bytes(fixture)
        output = self.root / "must-not-exist" / "report.md"

        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.write_report(fixture.manifest_path, output)

        self.assertFalse(output.parent.exists())
        self.assertEqual(self.evidence_bytes(fixture), before)

    def test_write_failure_leaves_evidence_and_destination_unmodified(self) -> None:
        fixture = EvidenceFixture(self.root / "valid")
        parent_file = self.root / "not-a-directory"
        parent_file.write_bytes(b"sentinel\n")
        output = parent_file / "report.md"
        before = self.evidence_bytes(fixture)

        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.write_report(fixture.manifest_path, output)

        self.assertEqual(parent_file.read_bytes(), b"sentinel\n")
        self.assertFalse(output.exists())
        self.assertEqual(self.evidence_bytes(fixture), before)

    def test_dangling_output_symlink_is_refused_without_writing_its_target(self) -> None:
        fixture = EvidenceFixture(self.root / "valid")
        output = self.root / "report.md"
        target = self.root / "missing-target.md"
        output.symlink_to(target.name)
        before = self.evidence_bytes(fixture)

        with self.assertRaises(REPORT.EvidenceValidationError):
            REPORT.write_report(fixture.manifest_path, output)

        self.assertTrue(output.is_symlink())
        self.assertFalse(target.exists())
        self.assertEqual(self.evidence_bytes(fixture), before)

    def test_atomic_publish_requires_the_destination_hard_link_to_exist(self) -> None:
        fixture = EvidenceFixture(self.root / "valid")
        output = self.root / "reports" / "report.md"
        before = self.evidence_bytes(fixture)

        with mock.patch.object(REPORT.os, "link", return_value=None):
            with self.assertRaises(REPORT.EvidenceValidationError):
                REPORT.write_report(fixture.manifest_path, output)

        self.assertFalse(output.exists())
        self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])
        self.assertEqual(self.evidence_bytes(fixture), before)


class CliContractTests(TemporaryDirectory):
    def run_cli(self, *arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_cli_works_from_unrelated_directory_and_maps_valid_statuses(self) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        cases = (
            ("local", {}, 0),
            (
                "fail",
                {
                    "evidence_level": "formal",
                    "report_intent": "delivery",
                    "formal_gate_pass": False,
                },
                1,
            ),
            ("blocked", {"report_intent": "delivery"}, 2),
        )
        for name, fixture_arguments, expected_exit in cases:
            with self.subTest(name=name):
                fixture = EvidenceFixture(self.root / name, **fixture_arguments)
                output = self.root / "cli-output" / f"{name}.md"

                completed = self.run_cli(
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(output),
                    cwd=unrelated,
                )

                self.assertEqual(completed.returncode, expected_exit, completed.stderr)
                self.assertTrue(output.is_file())

    def test_cli_rejects_usage_errors_with_exit_one_and_no_report(self) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        fixture = EvidenceFixture(self.root / "fixture")

        cases = (
            (
                "unknown",
                (
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(self.root / "unknown.md"),
                    "--extra",
                    "value",
                ),
                (self.root / "unknown.md",),
            ),
            (
                "extra-positional",
                (
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(self.root / "extra.md"),
                    "extra",
                ),
                (self.root / "extra.md",),
            ),
            (
                "abbreviated-options",
                (
                    "--man",
                    str(fixture.manifest_path),
                    "--out",
                    str(self.root / "abbreviated.md"),
                ),
                (self.root / "abbreviated.md",),
            ),
            (
                "duplicate-manifest",
                (
                    "--manifest",
                    str(fixture.manifest_path),
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(self.root / "duplicate-manifest.md"),
                ),
                (self.root / "duplicate-manifest.md",),
            ),
            (
                "duplicate-output",
                (
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(self.root / "duplicate-output-a.md"),
                    "--out-md",
                    str(self.root / "duplicate-output-b.md"),
                ),
                (
                    self.root / "duplicate-output-a.md",
                    self.root / "duplicate-output-b.md",
                ),
            ),
            (
                "missing-manifest",
                ("--out-md", str(self.root / "missing-manifest.md")),
                (self.root / "missing-manifest.md",),
            ),
            (
                "missing-output",
                ("--manifest", str(fixture.manifest_path)),
                (),
            ),
        )
        for name, arguments, outputs in cases:
            with self.subTest(name=name):
                completed = self.run_cli(*arguments, cwd=unrelated)
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertTrue(all(not output.exists() for output in outputs))

    def test_cli_validation_error_exits_one_without_report(self) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        fixture = EvidenceFixture(self.root / "fixture")

        fixture.manifest["source"]["commit_sha"] = "invalid"
        fixture.write_manifest()
        invalid_output = self.root / "invalid.md"
        invalid = self.run_cli(
            "--manifest",
            str(fixture.manifest_path),
            "--out-md",
            str(invalid_output),
            cwd=unrelated,
        )
        self.assertEqual(invalid.returncode, 1)
        self.assertFalse(invalid_output.exists())

    def test_cli_rejects_forged_or_incomplete_formal_command_provenance(self) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()

        def replace_required_argument(fixture: EvidenceFixture) -> None:
            for command in (
                fixture.manifest["commands"]["benchmark"],
                fixture.manifest["tasks"][3]["command"],
            ):
                repeat_index = command.index("--repeat") + 1
                command[repeat_index] = "99"

        cases = (
            (
                "true-commands",
                lambda fixture: fixture.manifest.update(
                    {
                        "commands": {
                            name: ["true"]
                            for name in ("configure", "build", "ctest", "benchmark")
                        }
                    }
                ),
            ),
            (
                "missing-task-provenance",
                lambda fixture: [
                    fixture.manifest["tasks"][0].pop(key)
                    for key in ("command", "cwd", "environment")
                ],
            ),
            ("drifted-required-argument", replace_required_argument),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                fixture = EvidenceFixture(
                    self.root / name,
                    evidence_level="formal",
                    report_intent="delivery",
                )
                mutate(fixture)
                fixture.write_manifest()
                output = self.root / "reports" / f"{name}.md"

                completed = self.run_cli(
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(output),
                    cwd=unrelated,
                )

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertFalse(output.exists())

    def test_cli_rejects_huge_json_numbers_without_traceback_or_report(self) -> None:
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        huge = 10**400
        targets = (
            (
                "correctness",
                lambda summary: summary["correctness"].__setitem__(
                    "relative_frobenius_error", huge
                ),
            ),
            (
                "statistics",
                lambda summary: summary["serial_measured_statistics"][
                    "symbolic_total_ms"
                ].__setitem__("mean_ms", huge),
            ),
            (
                "gate-threshold",
                lambda summary: summary["performance_gate"].__setitem__(
                    "numeric_speedup_threshold", huge
                ),
            ),
            (
                "speedup",
                lambda summary: summary["per_thread_measured_statistics"][0].__setitem__(
                    "symbolic_speedup", huge
                ),
            ),
            (
                "validation-matrix",
                lambda summary: summary["validation_cases"][0]["matrix"].__setitem__(
                    "relative_frobenius_error", huge
                ),
            ),
            (
                "validation-displacement",
                lambda summary: summary["validation_cases"][0][
                    "displacement"
                ].__setitem__("parallel_relative_residual", huge),
            ),
        )
        for name, mutate in targets:
            with self.subTest(name=name):
                fixture = EvidenceFixture(self.root / name)
                mutate(fixture.summary)
                fixture.write_summary()
                fixture.refresh_artifacts()
                output = self.root / "reports" / f"{name}.md"

                completed = self.run_cli(
                    "--manifest",
                    str(fixture.manifest_path),
                    "--out-md",
                    str(output),
                    cwd=unrelated,
                )

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
