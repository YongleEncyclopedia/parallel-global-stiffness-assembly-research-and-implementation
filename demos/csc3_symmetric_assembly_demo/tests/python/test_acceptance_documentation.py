#!/usr/bin/env python3
"""Contract tests for the formal Linux acceptance documentation."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
PACKAGING_ROOT = DEMO_ROOT / "packaging"
RUNBOOK = PACKAGING_ROOT / "LINUX_FORMAL_RUNBOOK.zh-CN.md"
CHECKLIST = PACKAGING_ROOT / "ACCEPTANCE_CHECKLIST.zh-CN.md"
RECORD_SCHEMA = PACKAGING_ROOT / "ACCEPTANCE_RECORD.schema.json"
DELIVERY_NOTE = PACKAGING_ROOT / "DELIVERY_NOTE.zh-CN.md"

EXPECTED_TESTS = (
    "Csc3DemoTests",
    "Csc3DemoConsumer",
    "Csc3DemoCorrectness",
    "Csc3DemoBenchmarkTiming",
    "Csc3DemoBenchmarkEngine",
    "Csc3DemoBenchmarkIo",
    "Csc3DemoInpCase",
    "Csc3DemoWindHubBenchmark",
    "Csc3DemoBenchmarkRunner",
    "Csc3DemoAtomicContention",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RequiredDocumentTests(unittest.TestCase):
    def test_all_formal_acceptance_documents_exist(self) -> None:
        for path in (RUNBOOK, CHECKLIST, RECORD_SCHEMA, DELIVERY_NOTE):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"missing acceptance document: {path}")

    def test_packaging_and_demo_readmes_link_every_acceptance_entrypoint(self) -> None:
        packaging_readme = read_text(PACKAGING_ROOT / "README.md")
        demo_readme = read_text(DEMO_ROOT / "README.md")
        for name in (
            RUNBOOK.name,
            CHECKLIST.name,
            RECORD_SCHEMA.name,
            DELIVERY_NOTE.name,
        ):
            with self.subTest(name=name):
                self.assertIn(name, packaging_readme)
        self.assertIn("packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md", demo_readme)
        self.assertIn("packaging/ACCEPTANCE_CHECKLIST.zh-CN.md", demo_readme)
        self.assertIn("INTERNAL EVALUATION ONLY", demo_readme)


class LinuxRunbookContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(RUNBOOK)

    def assertContainsAll(self, values: tuple[str, ...]) -> None:  # noqa: N802
        for value in values:
            with self.subTest(value=value):
                self.assertIn(value, self.text)

    def test_preflight_is_exact_source_controlled_linux_intel_and_lfs_bound(self) -> None:
        self.assertContainsAll(
            (
                "set -euo pipefail",
                "export LC_ALL=C",
                "export TZ=UTC",
                "unset PYTHONOPTIMIZE PYTHONPATH PYTHONHOME",
                "EXPECTED_SOURCE_SHA",
                "CONTROLLED_HOST_ID",
                "BUNDLE_ID",
                "RUN_ROOT",
                "git checkout --detach \"$EXPECTED_SOURCE_SHA\"",
                "git status --porcelain=v1 --untracked-files=all",
                "x86_64|amd64",
                "GenuineIntel",
                "git lfs pull --include=\"examples/3d-WindTurbineHub.inp\" --exclude=''",
                "git show HEAD:examples/3d-WindTurbineHub.inp",
                "sha256sum",
                "stat -c %s",
                "host-preflight.txt",
            )
        )

    def test_preflight_captures_environment_and_derives_required_thread_set(self) -> None:
        self.assertContainsAll(
            (
                "date -u",
                "hostname",
                "uname -a",
                "/etc/os-release",
                "lscpu",
                "numactl",
                "cpuset",
                "/proc/meminfo",
                "g++ --version",
                "cmake --version",
                "ninja --version",
                "python3 --version",
                "git --version",
                "git lfs version",
                "OMP_DYNAMIC",
                "OMP_PROC_BIND",
                "OMP_PLACES",
                "scaling_governor",
                "no_turbo",
                "physical_core_count",
                "[1, 2, 4, 8, 16, physical_core_count]",
            )
        )

    def test_formal_runner_and_report_commands_are_fixed(self) -> None:
        self.assertContainsAll(
            (
                "scripts/run_benchmark.py",
                "--case windhub",
                "--input \"$INPUT\"",
                "--threads-list \"$THREADS\"",
                "--warmup 2",
                "--repeat 7",
                "--amortization-count 1",
                "--evidence-level formal",
                "--preset delivery",
                "--report-intent delivery",
                "--controlled-host-id \"$CONTROLLED_HOST_ID\"",
                "scripts/generate_test_report.py",
                "--manifest \"$EVIDENCE/run_manifest.json\"",
                "--out-md \"$REPORT\"",
            )
        )

    def test_independent_assertions_cover_manifest_identity_and_ten_tests(self) -> None:
        self.assertContainsAll(
            (
                'manifest["status"] == "PASS"',
                'manifest["source"]["commit_sha"] == expected_sha',
                'manifest["source"]["source_dirty_at_start"] is False',
                'manifest["input"]["repository_relative_path"]',
                'manifest["input"]["matches_head_lfs"] is True',
                '"after-build", "before-benchmark", "after-benchmark"',
                'check["status"] == "PASS"',
                "expected-ci-tests.txt",
                "ctest.xml",
                "skipped",
                "disabled",
                "notrun",
            )
        )
        for test_name in EXPECTED_TESTS:
            self.assertIn(test_name, self.text)

    def test_external_formal_package_is_repeated_and_verified_both_ways(self) -> None:
        self.assertGreaterEqual(self.text.count("scripts/create_delivery_package.py"), 2)
        self.assertContainsAll(
            (
                "--external-evidence-dir \"$EVIDENCE\"",
                "--external-report \"$REPORT\"",
                "--bundle-id \"$BUNDLE_ID\"",
                "--out-dir \"$RUN_ROOT/dist-a\"",
                "--out-dir \"$RUN_ROOT/dist-b\"",
                "cmp --silent \"$ZIP_A\" \"$ZIP_B\"",
                "deterministic-package.txt",
                "SOURCE_COMMIT",
                "SHA256SUMS",
                "scripts/verify_delivery_package.py",
                "--manifest-only",
                "clean-room-verification.log",
                '2>&1 | tee "$RUN_ROOT/clean-room-verification.log"',
            )
        )

    def test_failure_policy_retains_evidence_without_creating_acceptance_zip(self) -> None:
        self.assertContainsAll(
            (
                "FAIL",
                "BLOCKED",
                "Issue #44",
                "不得创建或提交验收 ZIP",
                "不得选择性重跑",
                "保留",
                "CI",
                "不得作为正式性能结论",
            )
        )


class AcceptanceChecklistContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(CHECKLIST)

    def test_checklist_has_all_acceptance_domains_and_statuses(self) -> None:
        for value in (
            "授权与接收方范围",
            "源码与 LFS 输入身份",
            "受控主机与环境记录",
            "十项 CTest",
            "Tet4",
            "Hex8",
            "矩阵",
            "位移",
            "残差",
            "原始样本",
            "性能门槛",
            "规范 Markdown 报告",
            "源码 SHA",
            "证据 SHA",
            "确定性打包",
            "clean-room",
            "操作员",
            "技术复核人",
            "交付批准人",
            "接收方确认",
            "偏差",
            "PASS",
            "FAIL",
            "BLOCKED",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.text)

    def test_checklist_states_every_numeric_gate_in_latex(self) -> None:
        for expression in (
            r"$e_F \le 10^{-8}$",
            r"$e_{\max} \le 10^{-10} + 10^{-8}\max |K_s|$",
            r"$e_u \le 10^{-8}$",
            r"$r_{\mathrm{rel}} \le 10^{-10}$",
            r"$S_{\mathrm{numeric}}(p) \ge 1.5$",
            r"$S_{\mathrm{symbolic}}(p) > 1$",
            r"$p > 1$",
            r"$CV \le 0.05$",
        ):
            with self.subTest(expression=expression):
                self.assertIn(expression, self.text)


class AcceptanceRecordSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(read_text(RECORD_SCHEMA))

    def test_schema_uses_draft_2020_12_and_requires_full_record(self) -> None:
        self.assertEqual(
            self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertFalse(self.schema["additionalProperties"])
        required = {
            "schema_version",
            "delivery_id",
            "issue_url",
            "source_commit",
            "distribution",
            "recipient",
            "operator",
            "technical_reviewer",
            "controlled_host",
            "toolchain",
            "input",
            "execution",
            "correctness",
            "performance",
            "artifacts",
            "verifications",
            "deviations",
            "approvals",
            "status",
        }
        self.assertEqual(set(self.schema["required"]), required)

    def test_schema_freezes_distribution_status_sha_and_formal_parameters(self) -> None:
        properties = self.schema["properties"]
        self.assertEqual(properties["distribution"]["const"], "INTERNAL EVALUATION ONLY")
        self.assertEqual(properties["status"]["enum"], ["PASS", "FAIL", "BLOCKED"])
        self.assertEqual(properties["source_commit"]["pattern"], "^[0-9a-f]{40}$")
        definitions = self.schema["$defs"]
        self.assertEqual(definitions["sha256"]["pattern"], "^[0-9a-f]{64}$")
        execution = properties["execution"]["properties"]
        self.assertEqual(execution["warmup_count"]["minimum"], 2)
        self.assertEqual(execution["repeat_count"]["minimum"], 7)
        self.assertEqual(execution["amortization_count"]["const"], 1)
        self.assertEqual(execution["evidence_level"]["const"], "formal")
        self.assertEqual(execution["report_intent"]["const"], "delivery")

    def test_schema_represents_correctness_and_performance_thresholds(self) -> None:
        correctness = self.schema["properties"]["correctness"]["properties"]
        correctness_thresholds = correctness["thresholds"]["properties"]
        self.assertEqual(
            correctness_thresholds["frobenius_relative_error_maximum"]["const"],
            1e-8,
        )
        self.assertEqual(
            correctness_thresholds["displacement_relative_error_maximum"]["const"],
            1e-8,
        )
        self.assertEqual(
            correctness_thresholds["relative_residual_maximum"]["const"], 1e-10
        )
        maximum = correctness_thresholds["maximum_absolute_error"]
        self.assertEqual(maximum["properties"]["absolute_term"]["const"], 1e-10)
        self.assertEqual(maximum["properties"]["scale_term"]["const"], 1e-8)

        performance = self.schema["properties"]["performance"]["properties"]
        performance_thresholds = performance["thresholds"]["properties"]
        self.assertEqual(performance_thresholds["numeric_speedup_minimum"]["const"], 1.5)
        self.assertEqual(
            performance_thresholds["symbolic_speedup_exclusive_minimum"]["const"],
            1.0,
        )
        self.assertEqual(
            performance_thresholds["maximum_coefficient_of_variation"]["const"],
            0.05,
        )
        self.assertEqual(performance["numeric_thread_count"]["exclusiveMinimum"], 1)
        self.assertEqual(performance["symbolic_thread_count"]["exclusiveMinimum"], 1)

    def test_signature_fields_are_references_not_fabricated_signatures(self) -> None:
        approval = self.schema["$defs"]["approval"]
        self.assertIn("identity_reference", approval["required"])
        self.assertIn("acknowledged_at_utc", approval["required"])
        self.assertNotIn("signature", approval["properties"])

    def test_verifier_outputs_are_hash_bound_with_truthful_formats(self) -> None:
        artifacts = self.schema["properties"]["artifacts"]
        self.assertIn("manifest_only_verifier_output", artifacts["required"])
        self.assertIn("clean_room_verifier_log", artifacts["required"])
        self.assertIn("deterministic_package_record", artifacts["required"])
        self.assertEqual(
            artifacts["properties"]["manifest_only_verifier_output"]["description"],
            "JSON output from manifest-only verification.",
        )
        self.assertEqual(
            artifacts["properties"]["clean_room_verifier_log"]["description"],
            "Combined build/test log and final JSON from full clean-room verification.",
        )

    def test_failed_ctest_counts_are_recordable_but_pass_is_strict(self) -> None:
        ctest = self.schema["properties"]["verifications"]["properties"]["ctest"]
        for name in ("failed_count", "skipped_count", "not_run_count"):
            self.assertEqual(
                ctest["properties"][name], {"type": "integer", "minimum": 0}
            )
        pass_ctest = self.schema["allOf"][0]["then"]["properties"]["verifications"][
            "properties"
        ]["ctest"]["properties"]
        self.assertEqual(pass_ctest["test_count"]["const"], 10)
        self.assertEqual(pass_ctest["failed_count"]["const"], 0)
        self.assertEqual(pass_ctest["skipped_count"]["const"], 0)
        self.assertEqual(pass_ctest["not_run_count"]["const"], 0)
        self.assertEqual(tuple(pass_ctest["test_names"]["const"]), EXPECTED_TESTS)


class DeliveryNoteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = read_text(DELIVERY_NOTE)

    def test_template_is_visibly_incomplete_and_covers_delivery_boundary(self) -> None:
        self.assertGreaterEqual(self.text.count("REQUIRED BEFORE DELIVERY"), 12)
        for value in (
            "INTERNAL EVALUATION ONLY",
            "版本",
            "源码 SHA",
            "并行符号组装",
            "OpenMP atomic",
            "包含项",
            "排除项",
            "证据 SHA-256",
            "报告 SHA-256",
            "ZIP SHA-256",
            "不得再分发",
            "商业求解器",
            "已知限制",
            "回滚",
            "复现",
            "发送方批准",
            "接收方确认",
            "Markdown",
            "PDF",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.text)


if __name__ == "__main__":
    unittest.main()
