#!/usr/bin/env python3
"""Contract tests for the formal Linux acceptance documentation."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


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

SHA256 = "a" * 64
SOURCE_SHA = "b" * 40


def party(identity: str) -> dict[str, str]:
    return {
        "organization": "Example Institute",
        "department": "Solver Development",
        "identity_reference": identity,
    }


def artifact(path: str) -> dict[str, object]:
    return {"path": path, "size_bytes": 1, "sha256": SHA256}


def pending_approval(identity: str) -> dict[str, str]:
    return {"identity_reference": identity, "acknowledgement": "PENDING"}


def acknowledged_approval(identity: str) -> dict[str, str]:
    return {
        "identity_reference": identity,
        "acknowledgement": "ACKNOWLEDGED",
        "acknowledged_at_utc": "2026-07-13T12:00:00Z",
        "approval_record_reference": f"issue-44/{identity}",
    }


def early_preflight_blocked_record() -> dict[str, object]:
    """A truthful record stopped before Intel/tool/input checks completed."""
    return {
        "schema_version": "csc3-demo-formal-acceptance-v1",
        "delivery_id": "linux-preflight-blocked",
        "issue_url": "https://github.com/example/repository/issues/44",
        "source_commit": SOURCE_SHA,
        "distribution": "INTERNAL EVALUATION ONLY",
        "recipient": party("recipient-id"),
        "operator": party("operator-id"),
        "technical_reviewer": party("reviewer-id"),
        "controlled_host": {
            "controlled_host_id": "host-under-test",
            "system": "Linux",
            "architecture": "aarch64",
            "hostname": None,
            "cpu_vendor": "ARM",
            "cpu_model": None,
            "physical_core_count": None,
            "logical_core_count": None,
            "total_memory_bytes": None,
            "preflight_sha256": SHA256,
        },
        "toolchain": {
            "compiler": None,
            "compiler_version": None,
            "cmake_version": None,
            "ninja_version": None,
            "python_version": None,
            "git_version": "git version 2.50.0",
            "git_lfs_version": None,
            "openmp_found": None,
            "openmp_required": True,
        },
        "input": {
            "case": "windhub",
            "repository_relative_path": "examples/3d-WindTurbineHub.inp",
            "size_bytes": None,
            "sha256": None,
            "tracked": None,
            "materialized": None,
            "matches_head_lfs": None,
            "head_lfs_oid_sha256": None,
            "head_lfs_size_bytes": None,
        },
        "execution": {
            "status": "BLOCKED",
            "started_at_utc": "2026-07-13T11:59:00Z",
            "ended_at_utc": "2026-07-13T11:59:01Z",
        },
        "correctness": {"status": "NOT_RUN"},
        "performance": {"status": "NOT_RUN"},
        "artifacts": {
            "host_preflight": artifact("host-preflight.txt"),
            "runbook_log": artifact("runbook.log"),
            "outcome_record": artifact("acceptance-outcome.json"),
        },
        "verifications": {"status": "BLOCKED"},
        "deviations": [
            {
                "identifier": "ARCH-001",
                "description": "Observed architecture is not x86_64.",
                "impact": "Formal run did not start.",
                "disposition": "OPEN_BLOCKER",
            }
        ],
        "approvals": {
            "operator": pending_approval("operator-id"),
            "technical_reviewer": pending_approval("reviewer-id"),
            "delivery_approver": pending_approval("approver-id"),
            "recipient_acknowledgement": pending_approval("recipient-id"),
        },
        "status": "BLOCKED",
    }


def correctness_case() -> dict[str, object]:
    return {
        "status": "PASS",
        "structure_equal": True,
        "values_finite": True,
        "scatter_indices_valid": True,
        "frobenius_relative_error": 1e-12,
        "maximum_absolute_error": 1e-12,
        "maximum_absolute_serial_entry": 10.0,
        "maximum_absolute_error_tolerance": 1.001e-7,
        "maximum_absolute_error_within_tolerance": True,
        "displacement_relative_error": 1e-12,
        "relative_residual": 1e-12,
        "evidence_reference": "evidence/benchmark_summary.json",
    }


def complete_pass_record() -> dict[str, object]:
    verification = {
        "status": "PASS",
        "evidence_reference": "evidence/run_manifest.json",
    }
    artifacts = {
        name: artifact(path)
        for name, path in {
            "run_manifest": "evidence/run_manifest.json",
            "ctest_junit": "evidence/ctest.xml",
            "benchmark_samples": "evidence/benchmark_samples.csv",
            "benchmark_summary": "evidence/benchmark_summary.json",
            "evidence_summary": "evidence/summary.md",
            "canonical_markdown_report": "report.zh-CN.md",
            "host_preflight": "host-preflight.txt",
            "runbook_log": "runbook.log",
            "outcome_record": "acceptance-outcome.json",
            "source_commit_file": "SOURCE_COMMIT",
            "sha256sums_file": "SHA256SUMS",
            "deterministic_package_record": "deterministic-package.txt",
            "manifest_only_verifier_output": "manifest-only-verification.json",
            "clean_room_verifier_log": "clean-room-verification.log",
            "delivery_zip": "dist-a/delivery.zip",
        }.items()
    }
    return {
        "schema_version": "csc3-demo-formal-acceptance-v1",
        "delivery_id": "linux-formal-pass",
        "issue_url": "https://github.com/example/repository/issues/44",
        "source_commit": SOURCE_SHA,
        "distribution": "INTERNAL EVALUATION ONLY",
        "recipient": party("recipient-id"),
        "operator": party("operator-id"),
        "technical_reviewer": party("reviewer-id"),
        "controlled_host": {
            "controlled_host_id": "linux-intel-host",
            "system": "Linux",
            "architecture": "x86_64",
            "hostname": "controlled-host",
            "cpu_vendor": "GenuineIntel",
            "cpu_model": "Intel Xeon",
            "physical_core_count": 32,
            "logical_core_count": 64,
            "total_memory_bytes": 137438953472,
            "preflight_sha256": SHA256,
        },
        "toolchain": {
            "compiler": "GCC",
            "compiler_version": "13.2.0",
            "cmake_version": "3.29.0",
            "ninja_version": "1.12.0",
            "python_version": "3.11.9",
            "git_version": "2.50.0",
            "git_lfs_version": "3.7.0",
            "openmp_found": True,
            "openmp_required": True,
        },
        "input": {
            "case": "windhub",
            "repository_relative_path": "examples/3d-WindTurbineHub.inp",
            "size_bytes": 100,
            "sha256": SHA256,
            "tracked": True,
            "materialized": True,
            "matches_head_lfs": True,
            "head_lfs_oid_sha256": SHA256,
            "head_lfs_size_bytes": 100,
        },
        "execution": {
            "status": "PASS",
            "evidence_level": "formal",
            "report_intent": "delivery",
            "preset": "delivery",
            "warmup_count": 2,
            "repeat_count": 7,
            "amortization_count": 1,
            "requested_thread_counts": [1, 2, 4, 8, 16, 32],
            "physical_core_thread_included": True,
            "omp_dynamic": "false",
            "omp_proc_bind": "close",
            "omp_places": "cores",
            "started_at_utc": "2026-07-13T12:00:00Z",
            "ended_at_utc": "2026-07-13T12:30:00Z",
        },
        "correctness": {
            "status": "PASS",
            "thresholds": {
                "frobenius_relative_error_maximum": 1e-8,
                "maximum_absolute_error": {
                    "absolute_term": 1e-10,
                    "scale_term": 1e-8,
                    "scale_quantity": "max_abs_serial_matrix_entry",
                },
                "displacement_relative_error_maximum": 1e-8,
                "relative_residual_maximum": 1e-10,
            },
            "tet4": correctness_case(),
            "hex8": correctness_case(),
        },
        "performance": {
            "status": "PASS",
            "thresholds": {
                "numeric_speedup_minimum": 1.5,
                "symbolic_speedup_exclusive_minimum": 1.0,
                "maximum_coefficient_of_variation": 0.05,
                "thread_count_exclusive_minimum": 1,
            },
            "numeric_thread_count": 16,
            "numeric_speedup": 1.8,
            "numeric_coefficient_of_variation": 0.02,
            "symbolic_thread_count": 8,
            "symbolic_speedup": 1.1,
            "symbolic_coefficient_of_variation": 0.02,
            "raw_sample_count": 84,
            "samples_sha256": SHA256,
            "summary_sha256": SHA256,
        },
        "artifacts": artifacts,
        "verifications": {
            "status": "PASS",
            "source_and_input_identity": copy.deepcopy(verification),
            "ctest": {
                "status": "PASS",
                "test_count": 10,
                "failed_count": 0,
                "skipped_count": 0,
                "not_run_count": 0,
                "test_names": list(EXPECTED_TESTS),
                "evidence_reference": "evidence/ctest.xml",
            },
            "report_recomputation": copy.deepcopy(verification),
            "deterministic_package": copy.deepcopy(verification),
            "manifest_only": copy.deepcopy(verification),
            "clean_room": copy.deepcopy(verification),
        },
        "deviations": [],
        "approvals": {
            "operator": acknowledged_approval("operator-id"),
            "technical_reviewer": acknowledged_approval("reviewer-id"),
            "delivery_approver": acknowledged_approval("approver-id"),
            "recipient_acknowledgement": acknowledged_approval("recipient-id"),
        },
        "status": "PASS",
    }


def completed_fail_record() -> dict[str, object]:
    record = complete_pass_record()
    record["delivery_id"] = "linux-formal-performance-fail"
    record["status"] = "FAIL"
    record["execution"]["status"] = "FAIL"
    record["performance"]["status"] = "FAIL"
    record["performance"]["numeric_speedup"] = 1.2
    for name in (
        "source_commit_file",
        "sha256sums_file",
        "deterministic_package_record",
        "manifest_only_verifier_output",
        "clean_room_verifier_log",
        "delivery_zip",
    ):
        del record["artifacts"][name]
    record["verifications"] = {
        "status": "FAIL",
        "source_and_input_identity": {
            "status": "PASS",
            "evidence_reference": "evidence/run_manifest.json",
        },
        "ctest": copy.deepcopy(record["verifications"]["ctest"]),
        "report_recomputation": {
            "status": "PASS",
            "evidence_reference": "report.zh-CN.md",
        },
    }
    record["deviations"] = [
        {
            "identifier": "PERF-001",
            "description": "Numeric speedup did not reach the gate.",
            "impact": "The package must not be created.",
            "disposition": "REJECTED",
        }
    ]
    record["approvals"] = {
        "operator": pending_approval("operator-id"),
        "technical_reviewer": pending_approval("reviewer-id"),
        "delivery_approver": pending_approval("approver-id"),
        "recipient_acknowledgement": pending_approval("recipient-id"),
    }
    return record


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

    def test_packaging_readme_distinguishes_mode_specific_evidence_files(self) -> None:
        text = read_text(PACKAGING_ROOT / "README.md")
        self.assertIn("four required evidence files", text)
        self.assertIn("optional `summary.md`", text)
        self.assertIn("five required evidence files", text)
        external_section = text.split("## Create an external formal archive", 1)[0]
        self.assertIn("`summary.md`", external_section)


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

    def test_preflight_enforces_documented_python_and_gcc_minimums(self) -> None:
        self.assertContainsAll(
            (
                "sys.version_info < (3, 11)",
                '"$CXX" -dumpfullversion -dumpversion',
                "GCC_MAJOR",
                "GCC 9 or newer is required",
            )
        )

    def test_cpu_vendor_probe_is_pipefail_safe(self) -> None:
        self.assertNotIn("| head -n 1", self.text)
        self.assertIn("CPU_VENDOR=\"$(awk ", self.text)

    def test_early_preflight_failures_always_leave_blocker_evidence(self) -> None:
        self.assertContainsAll(
            (
                "runbook.log",
                "acceptance-outcome.json",
                "RUNBOOK_STATUS=BLOCKED",
                "RUNBOOK_REASON",
                "on_runbook_error",
                "on_runbook_exit",
                "trap 'on_runbook_error",
                "trap 'on_runbook_exit",
                'exec > >(tee -a "$RUNBOOK_LOG") 2>&1',
                '"status": "%s"',
                '"reason": "%s"',
                '"exit_code": %s',
            )
        )
        root_created = self.text.index('install -d -m 0700 "$RUN_ROOT"')
        trap_installed = self.text.find("trap 'on_runbook_error")
        self.assertNotEqual(-1, trap_installed)
        architecture_gate = self.text.index('ARCH="$(uname -m)"')
        vendor_gate = self.text.index("GenuineIntel")
        compiler_gate = self.text.index('[[ -x "$CC" && -x "$CXX" ]]')
        self.assertLess(root_created, trap_installed)
        self.assertLess(trap_installed, compiler_gate)
        self.assertLess(trap_installed, architecture_gate)
        self.assertLess(trap_installed, vendor_gate)
        self.assertGreater(
            self.text.rindex("RUNBOOK_STATUS=PASS"),
            self.text.index("clean-room-verification.log"),
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

        correctness_case = self.schema["$defs"]["correctness_case"]
        self.assertIn("allOf", correctness_case)
        correctness_case_required = set(
            correctness_case["allOf"][0]["then"]["required"]
        )
        self.assertIn("maximum_absolute_error_tolerance", correctness_case_required)
        self.assertIn(
            "maximum_absolute_error_within_tolerance", correctness_case_required
        )

    def test_signature_fields_are_references_not_fabricated_signatures(self) -> None:
        approval = self.schema["$defs"]["approval"]
        self.assertIn("identity_reference", approval["required"])
        self.assertIn("acknowledgement", approval["required"])
        self.assertNotIn("acknowledged_at_utc", approval["required"])
        self.assertNotIn("approval_record_reference", approval["required"])
        decided = approval["allOf"][0]["then"]["required"]
        self.assertIn("acknowledged_at_utc", decided)
        self.assertIn("approval_record_reference", decided)
        self.assertNotIn("signature", approval["properties"])

    def test_verifier_outputs_are_hash_bound_with_truthful_formats(self) -> None:
        artifacts = self.schema["properties"]["artifacts"]
        self.assertNotIn("manifest_only_verifier_output", artifacts["required"])
        self.assertNotIn("clean_room_verifier_log", artifacts["required"])
        self.assertNotIn("deterministic_package_record", artifacts["required"])
        self.assertNotIn("delivery_zip", artifacts["required"])
        self.assertIn("runbook_log", artifacts["required"])
        self.assertIn("outcome_record", artifacts["required"])
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

    def test_draft_validator_accepts_complete_pass_fail_and_blocked_records(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        validator = Draft202012Validator(self.schema)
        for record in (
            complete_pass_record(),
            completed_fail_record(),
            early_preflight_blocked_record(),
        ):
            with self.subTest(status=record["status"]):
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
                self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def test_draft_validator_rejects_incomplete_or_dishonest_pass(self) -> None:
        validator = Draft202012Validator(self.schema)

        missing_zip = complete_pass_record()
        del missing_zip["artifacts"]["delivery_zip"]

        failed_absolute_gate = complete_pass_record()
        failed_absolute_gate["correctness"]["tet4"][
            "maximum_absolute_error"
        ] = 1e100
        failed_absolute_gate["correctness"]["tet4"][
            "maximum_absolute_error_within_tolerance"
        ] = False

        open_blocker = complete_pass_record()
        open_blocker["deviations"] = [
            {
                "identifier": "OPEN-001",
                "description": "Unresolved blocker.",
                "impact": "Acceptance is unsafe.",
                "disposition": "OPEN_BLOCKER",
            }
        ]

        pending_record = complete_pass_record()
        pending_record["approvals"]["recipient_acknowledgement"] = pending_approval(
            "recipient-id"
        )

        for name, record in (
            ("missing delivery ZIP", missing_zip),
            ("failed maximum absolute error gate", failed_absolute_gate),
            ("open blocker", open_blocker),
            ("pending approval", pending_record),
        ):
            with self.subTest(name=name):
                self.assertFalse(validator.is_valid(record))


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
