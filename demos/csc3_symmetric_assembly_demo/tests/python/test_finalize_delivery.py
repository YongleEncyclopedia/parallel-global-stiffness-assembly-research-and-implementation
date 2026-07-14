#!/usr/bin/env python3
"""Tests for the post-approval CSC3 delivery finalizer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "finalize_delivery.py"
SOURCE_SHA = "b" * 40
DELIVERY_ID = "controlled-linux-intel-001"
ISSUE_URL = "https://github.com/example/repository/issues/44"
OPERATOR_ORGANIZATION = "Sender Research Organization"
OPERATOR_DEPARTMENT = "Numerical Software Team"
RECIPIENT_ORGANIZATION = "Research Institute"
RECIPIENT_DEPARTMENT = "Solver Development Department"
OPERATOR_IDENTITY = "operator-id"
REVIEWER_IDENTITY = "reviewer-id"
APPROVER_IDENTITY = "approver-id"
RECIPIENT_IDENTITY = "recipient-id"
ACKNOWLEDGED_AT_UTC = "2026-07-13T12:00:00Z"
DEMO_VERSION = "0.2.0"
DELIVERY_DATE_UTC = "2026-07-13"
CORRECTNESS_SUMMARY = (
    "status=PASS；Tet4=PASS；Hex8=PASS；$e_F \\le 1e-08$；"
    "$e_{\\max} \\le 1e-10 + 1e-08\\max |K_s|$；"
    "$e_u \\le 1e-08$；$r_{\\mathrm{rel}} \\le 1e-10$"
)
PERFORMANCE_SUMMARY = (
    "status=PASS；$S_{\\mathrm{numeric}}(8)=1.75 \\ge 1.5$，"
    "$CV=0.02 \\le 0.05$；$S_{\\mathrm{symbolic}}(8)=1.2 > 1$，"
    "$CV=0.03 \\le 0.05$；原始样本数 $N=70$"
)
DEVIATION_SUMMARY = (
    "DEV-001=ACCEPTED_INTERNAL_ONLY（批准引用 deviation-approval:DEV-001）"
)
EXPECTED_CTEST_TESTS = (
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


def fill_remaining_placeholders(text: str, values: list[str]) -> str:
    """Fill each remaining test-template slot with one explicit value."""
    for value in values:
        if "REQUIRED BEFORE DELIVERY" not in text:
            raise AssertionError("too many completed-sidecar fixture values")
        text = text.replace("REQUIRED BEFORE DELIVERY", value, 1)
    if "REQUIRED BEFORE DELIVERY" in text:
        raise AssertionError(
            "completed-sidecar fixture still has "
            f"{text.count('REQUIRED BEFORE DELIVERY')} unfilled slots"
        )
    return text


def fill_checklist_objective_items(
    text: str, values_by_selector: dict[str, str]
) -> str:
    """Fill exactly one placeholder in each selected checkbox block."""
    lines = text.splitlines(keepends=True)
    for selector, value in values_by_selector.items():
        matches: list[tuple[int, int]] = []
        index = 0
        while index < len(lines):
            if not lines[index].startswith("- [x] "):
                index += 1
                continue
            end = index + 1
            while end < len(lines) and lines[end].startswith("  "):
                end += 1
            block = "".join(lines[index:end])
            if selector in block and "REQUIRED BEFORE DELIVERY" in block:
                matches.append((index, end))
            index = end
        if len(matches) != 1:
            raise AssertionError(
                f"objective selector {selector!r} matched {len(matches)} checklist items"
            )
        start, end = matches[0]
        block = "".join(lines[start:end])
        if block.count("REQUIRED BEFORE DELIVERY") != 1:
            raise AssertionError(
                f"objective selector {selector!r} does not have exactly one placeholder"
            )
        lines[start:end] = [block.replace("REQUIRED BEFORE DELIVERY", value, 1)]
    return "".join(lines)


def replace_checklist_objective_value(
    text: str, selector: str, replacement: str
) -> str:
    """Replace one selected completed value while preserving its immutable block."""
    template = (
        DEMO_ROOT / "packaging" / "ACCEPTANCE_CHECKLIST.zh-CN.md"
    ).read_text(encoding="utf-8")

    def spans(document: str) -> tuple[list[str], list[tuple[int, int]]]:
        lines = document.splitlines(keepends=True)
        blocks: list[str] = []
        locations: list[tuple[int, int]] = []
        index = 0
        while index < len(lines):
            if not lines[index].startswith(("- [ ] ", "- [x] ")):
                index += 1
                continue
            end = index + 1
            while end < len(lines) and lines[end].startswith("  "):
                end += 1
            blocks.append("".join(lines[index:end]))
            locations.append((index, end))
            index = end
        return blocks, locations

    template_blocks, _ = spans(template)
    actual_blocks, actual_spans = spans(text)
    matches = [
        index
        for index, block in enumerate(template_blocks)
        if selector in block and "REQUIRED BEFORE DELIVERY" in block
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"objective selector {selector!r} matched {len(matches)} template blocks"
        )
    index = matches[0]
    if len(actual_blocks) != len(template_blocks):
        raise AssertionError("completed checklist block count differs from template")
    forged_block = (
        template_blocks[index]
        .replace("- [ ] ", "- [x] ", 1)
        .replace("REQUIRED BEFORE DELIVERY", replacement, 1)
    )
    lines = text.splitlines(keepends=True)
    start, end = actual_spans[index]
    lines[start:end] = [forged_block]
    return "".join(lines)


def acknowledgement(identity: str, record_reference: str) -> dict[str, str]:
    return {
        "identity_reference": identity,
        "acknowledgement": "ACKNOWLEDGED",
        "acknowledged_at_utc": ACKNOWLEDGED_AT_UTC,
        "approval_record_reference": record_reference,
        "delivery_id": DELIVERY_ID,
        "source_commit": SOURCE_SHA,
        "archive_filename": "csc3-symmetric-assembly-demo-v0.2.0+bbbbbbbbbbbb.zip",
        "archive_sha256": "",
        "candidate_status": "PACKAGE_CANDIDATE",
        "clean_room_status": "PASS",
    }


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("csc3_finalize_delivery", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load finalize_delivery.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FinalizeDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.run_root = self.root / "run"
        self.run_root.mkdir()
        self.archive = self.run_root / "csc3-symmetric-assembly-demo-v0.2.0+bbbbbbbbbbbb.zip"
        self.archive.write_bytes(b"candidate archive bytes")
        self.archive_sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.runbook_log = self.run_root / "runbook.log"
        self.runbook_log.write_text("candidate run complete\n", encoding="utf-8")
        artifact_paths = {
            "run_manifest": "evidence/run_manifest.json",
            "ctest_junit": "evidence/ctest.xml",
            "benchmark_samples": "evidence/benchmark_samples.csv",
            "benchmark_summary": "evidence/benchmark_summary.json",
            "evidence_summary": "evidence/summary.md",
            "canonical_markdown_report": "csc3-test-report.zh-CN.md",
            "host_preflight": "host-preflight.txt",
            "runbook_log": self.runbook_log.name,
            "outcome_record": "acceptance-outcome.json",
            "source_commit_file": "SOURCE_COMMIT",
            "sha256sums_file": "SHA256SUMS",
            "deterministic_package_record": "deterministic-package.txt",
            "manifest_only_verifier_output": "manifest-only-verification.json",
            "clean_room_verifier_log": "clean-room-verification.log",
        }
        artifact_payloads = {
            "run_manifest": json.dumps(
                {
                    "status": "PASS",
                    "source": {"demo_version": DEMO_VERSION},
                },
                sort_keys=True,
            )
            + "\n",
            "benchmark_summary": json.dumps(
                {"status": "PASS", "performance_gate_status": "PASS"},
                sort_keys=True,
            )
            + "\n",
            "outcome_record": json.dumps(
                {
                    "status": "PACKAGE_CANDIDATE",
                    "candidate_completed_at_utc": "2026-07-13T11:59:59Z",
                },
                sort_keys=True,
            )
            + "\n",
            "deterministic_package_record": "status=PASS\narchives_byte_identical=true\n",
            "manifest_only_verifier_output": '{"status":"PASS"}\n',
            "clean_room_verifier_log": "clean-room status=PASS; ctest=10/10; consumer=PASS\n",
        }
        for name, relative in artifact_paths.items():
            path = self.run_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(
                    artifact_payloads.get(name, f"formal fixture artifact: {name}\n"),
                    encoding="utf-8",
                )
        self.record = self.run_root / "acceptance-record.json"
        self.record_data = {
            "schema_version": "csc3-demo-formal-acceptance-v1",
            "delivery_id": DELIVERY_ID,
            "source_commit": SOURCE_SHA,
            "distribution": "INTERNAL EVALUATION ONLY",
            "issue_url": ISSUE_URL,
            "operator": {
                "organization": OPERATOR_ORGANIZATION,
                "department": OPERATOR_DEPARTMENT,
                "identity_reference": OPERATOR_IDENTITY,
            },
            "technical_reviewer": {
                "organization": OPERATOR_ORGANIZATION,
                "department": OPERATOR_DEPARTMENT,
                "identity_reference": REVIEWER_IDENTITY,
            },
            "controlled_host": {
                "controlled_host_id": "linux-intel-host-01",
                "system": "Linux",
                "architecture": "x86_64",
                "hostname": "solver-linux-01",
                "cpu_vendor": "GenuineIntel",
                "cpu_model": "Intel Xeon Gold 6338",
                "physical_core_count": 32,
                "logical_core_count": 64,
                "total_memory_bytes": 137438953472,
                "preflight_sha256": hashlib.sha256(
                    (self.run_root / artifact_paths["host_preflight"]).read_bytes()
                ).hexdigest(),
            },
            "toolchain": {
                "compiler": "GCC",
                "compiler_version": "13.2.0",
                "cmake_version": "3.30.5",
                "ninja_version": "1.12.1",
                "python_version": "3.11.10",
                "git_version": "2.47.1",
                "git_lfs_version": "3.6.1",
                "openmp_found": True,
                "openmp_required": True,
            },
            "input": {
                "case": "windhub",
                "repository_relative_path": "examples/3d-WindTurbineHub.inp",
                "sha256": "e" * 64,
                "size_bytes": 123456,
                "tracked": True,
                "materialized": True,
                "matches_head_lfs": True,
                "head_lfs_oid_sha256": "e" * 64,
                "head_lfs_size_bytes": 123456,
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
                "started_at_utc": "2026-07-13T10:00:00Z",
                "ended_at_utc": "2026-07-13T11:30:00Z",
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
                "tet4": {
                    "status": "PASS",
                    "structure_equal": True,
                    "values_finite": True,
                    "scatter_indices_valid": True,
                    "frobenius_relative_error": 1e-16,
                    "maximum_absolute_error": 1e-12,
                    "maximum_absolute_serial_entry": 100.0,
                    "maximum_absolute_error_tolerance": 1.0001e-6,
                    "maximum_absolute_error_within_tolerance": True,
                    "displacement_relative_error": 0.0,
                    "relative_residual": 1e-14,
                    "evidence_reference": "benchmark_summary.json#tet4",
                },
                "hex8": {
                    "status": "PASS",
                    "structure_equal": True,
                    "values_finite": True,
                    "scatter_indices_valid": True,
                    "frobenius_relative_error": 2e-16,
                    "maximum_absolute_error": 2e-12,
                    "maximum_absolute_serial_entry": 200.0,
                    "maximum_absolute_error_tolerance": 2.0001e-6,
                    "maximum_absolute_error_within_tolerance": True,
                    "displacement_relative_error": 0.0,
                    "relative_residual": 2e-14,
                    "evidence_reference": "benchmark_summary.json#hex8",
                },
            },
            "performance": {
                "status": "PASS",
                "thresholds": {
                    "numeric_speedup_minimum": 1.5,
                    "symbolic_speedup_exclusive_minimum": 1.0,
                    "maximum_coefficient_of_variation": 0.05,
                    "thread_count_exclusive_minimum": 1,
                },
                "numeric_thread_count": 8,
                "numeric_speedup": 1.75,
                "numeric_coefficient_of_variation": 0.02,
                "symbolic_thread_count": 8,
                "symbolic_speedup": 1.2,
                "symbolic_coefficient_of_variation": 0.03,
                "raw_sample_count": 70,
                "samples_sha256": hashlib.sha256(
                    (self.run_root / artifact_paths["benchmark_samples"]).read_bytes()
                ).hexdigest(),
                "summary_sha256": hashlib.sha256(
                    (self.run_root / artifact_paths["benchmark_summary"]).read_bytes()
                ).hexdigest(),
            },
            "verifications": {
                "status": "PASS",
                "source_and_input_identity": {
                    "status": "PASS",
                    "evidence_reference": "run_manifest.json#identity_checks",
                },
                "ctest": {
                    "status": "PASS",
                    "test_count": 10,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "not_run_count": 0,
                    "test_names": list(EXPECTED_CTEST_TESTS),
                    "evidence_reference": "ctest.xml",
                },
                "report_recomputation": {
                    "status": "PASS",
                    "evidence_reference": "csc3-test-report.zh-CN.md",
                },
                "deterministic_package": {
                    "status": "PASS",
                    "evidence_reference": "deterministic-package.txt",
                },
                "manifest_only": {
                    "status": "PASS",
                    "evidence_reference": "manifest-only-verification.json",
                },
                "clean_room": {
                    "status": "PASS",
                    "evidence_reference": "clean-room-verification.log",
                },
            },
            "deviations": [
                {
                    "identifier": "DEV-001",
                    "description": "Internal handoff retains internal-only distribution.",
                    "impact": "No public redistribution is permitted.",
                    "disposition": "ACCEPTED_INTERNAL_ONLY",
                    "approval_reference": "deviation-approval:DEV-001",
                }
            ],
            "recipient": {
                "organization": RECIPIENT_ORGANIZATION,
                "department": RECIPIENT_DEPARTMENT,
                "identity_reference": RECIPIENT_IDENTITY,
            },
            "artifacts": {
                "delivery_zip": {
                    "path": self.archive.name,
                    "size_bytes": self.archive.stat().st_size,
                    "sha256": self.archive_sha,
                },
                **{
                    name: {
                        "path": relative,
                        "size_bytes": (self.run_root / relative).stat().st_size,
                        "sha256": hashlib.sha256(
                            (self.run_root / relative).read_bytes()
                        ).hexdigest(),
                    }
                    for name, relative in artifact_paths.items()
                },
            },
            "approvals": {
                "operator": acknowledgement(
                    OPERATOR_IDENTITY, f"approval:{OPERATOR_IDENTITY}:001"
                ),
                "technical_reviewer": acknowledgement(
                    REVIEWER_IDENTITY, f"approval:{REVIEWER_IDENTITY}:001"
                ),
                "delivery_approver": acknowledgement(
                    APPROVER_IDENTITY, f"approval:{APPROVER_IDENTITY}:001"
                ),
                "recipient_acknowledgement": acknowledgement(
                    RECIPIENT_IDENTITY, f"approval:{RECIPIENT_IDENTITY}:001"
                ),
            },
            "status": "PASS",
        }
        for approval in self.record_data["approvals"].values():
            approval["archive_sha256"] = self.archive_sha
        self.record.write_text(
            json.dumps(self.record_data, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.checklist = self.run_root / "completed-checklist.md"
        checklist_template = (
            DEMO_ROOT / "packaging" / "ACCEPTANCE_CHECKLIST.zh-CN.md"
        ).read_text(encoding="utf-8")
        completed_checklist = (
            checklist_template.replace(
                "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PENDING",
                "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS",
            )
            .replace("当前决定：`PENDING`", "当前决定：`PASS`")
            .replace("- [ ]", "- [x]")
            .replace(
                "- [x] 交付 ID：`REQUIRED BEFORE DELIVERY`",
                f"- [x] 交付 ID：`{DELIVERY_ID}`",
            )
            .replace(
                "- [x] Issue #44 URL：`REQUIRED BEFORE DELIVERY`",
                f"- [x] Issue #44 URL：`{ISSUE_URL}`",
            )
            .replace(
                "- [x] Demo 版本：`REQUIRED BEFORE DELIVERY`",
                f"- [x] Demo 版本：`{DEMO_VERSION}`",
            )
            .replace(
                "- [x] 完整源码 SHA：`REQUIRED BEFORE DELIVERY`",
                f"- [x] 完整源码 SHA：`{SOURCE_SHA}`",
            )
            .replace(
                "- [x] 候选源码 ZIP 文件名及 SHA-256：`REQUIRED BEFORE DELIVERY`",
                f"- [x] 候选源码 ZIP 文件名及 SHA-256：`{self.archive.name}` `{self.archive_sha}`",
            )
            .replace(
                "- [x] 接收组织及部门：`REQUIRED BEFORE DELIVERY`",
                f"- [x] 接收组织及部门：`{RECIPIENT_ORGANIZATION}` / `{RECIPIENT_DEPARTMENT}`",
            )
            .replace(
                "- [x] 指定接收人身份引用：`REQUIRED BEFORE DELIVERY`",
                f"- [x] 指定接收人身份引用：`{RECIPIENT_IDENTITY}`",
            )
            .replace(
                "- [x] 偏差清单（无偏差也必须写“无”并说明）："
                "`REQUIRED BEFORE DELIVERY`；`PASS`",
                f"- [x] 偏差清单（无偏差也必须写“无”并说明）："
                f"`{DEVIATION_SUMMARY}`；`PASS`",
            )
            .replace(
                "- [x] 操作员：身份引用 `REQUIRED BEFORE DELIVERY`；UTC "
                "`REQUIRED BEFORE DELIVERY`；\n  记录号 `REQUIRED BEFORE DELIVERY`",
                f"- [x] 操作员：身份引用 `{OPERATOR_IDENTITY}`；UTC "
                f"`{ACKNOWLEDGED_AT_UTC}`；\n  记录号 "
                f"`approval:{OPERATOR_IDENTITY}:001`",
            )
            .replace(
                "- [x] 技术复核人：身份引用 `REQUIRED BEFORE DELIVERY`；UTC\n"
                "  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`",
                f"- [x] 技术复核人：身份引用 `{REVIEWER_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{REVIEWER_IDENTITY}:001`",
            )
            .replace(
                "- [x] 交付批准人：身份引用 `REQUIRED BEFORE DELIVERY`；UTC\n"
                "  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`",
                f"- [x] 交付批准人：身份引用 `{APPROVER_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{APPROVER_IDENTITY}:001`",
            )
            .replace(
                "- [x] 接收方确认：身份引用 `REQUIRED BEFORE DELIVERY`；UTC\n"
                "  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`",
                f"- [x] 接收方确认：身份引用 `{RECIPIENT_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{RECIPIENT_IDENTITY}:001`",
            )
            .replace("最终状态：`REQUIRED BEFORE DELIVERY`", "最终状态：`PASS`")
            .replace(
                "最终验收记录文件：`REQUIRED BEFORE DELIVERY`",
                f"最终验收记录文件：`{self.record.name}` "
                f"`{hashlib.sha256(self.record.read_bytes()).hexdigest()}`",
            )
            .replace(
                "最终 ZIP SHA-256：`REQUIRED BEFORE DELIVERY`",
                f"最终 ZIP SHA-256：`{self.archive_sha}`",
            )
        )
        artifacts = self.record_data["artifacts"]
        record_sha = hashlib.sha256(self.record.read_bytes()).hexdigest()
        source_identity = self.record_data["verifications"][
            "source_and_input_identity"
        ]
        report_recomputation = self.record_data["verifications"][
            "report_recomputation"
        ]
        self.objective_checklist_values = {
            "分发标记逐字": "INTERNAL EVALUATION ONLY",
            "完整、非 shallow": (
                f"source_and_input_identity={source_identity['status']}；"
                f"evidence={source_identity['evidence_reference']}"
            ),
            "git rev-parse HEAD": (
                f"HEAD={SOURCE_SHA}；source_and_input_identity={source_identity['status']}"
            ),
            "git status --porcelain": (
                f"worktree_clean={source_identity['status']}；"
                f"runbook={artifacts['runbook_log']['path']}；"
                f"SHA-256={artifacts['runbook_log']['sha256']}"
            ),
            "输入路径严格为": "examples/3d-WindTurbineHub.inp",
            "Git LFS 实体化": "tracked=true；materialized=true；matches_head_lfs=true",
            "字节数与 `HEAD`": "size_bytes=123456；head_lfs_size_bytes=123456",
            "SHA-256 与 `HEAD`": f"sha256={'e' * 64}；head_lfs_oid_sha256={'e' * 64}",
            "受控主机 ID": "linux-intel-host-01",
            "物理 Linux": (
                "system=Linux；architecture=x86_64；cpu_vendor=GenuineIntel；"
                "cpu_model=Intel Xeon Gold 6338；physical_core_count=32；"
                "logical_core_count=64"
            ),
            "host-preflight.txt": (
                f"path={artifacts['host_preflight']['path']}；"
                f"SHA-256={artifacts['host_preflight']['sha256']}"
            ),
            "GCC、CMake": (
                "compiler=GCC 13.2.0；CMake=3.30.5；Ninja=1.12.1；"
                "Python=3.11.10；Git=2.47.1；Git LFS=3.6.1"
            ),
            "OMP_DYNAMIC=false": (
                "openmp_found=true；openmp_required=true；OMP_DYNAMIC=false；"
                "OMP_PROC_BIND=close；OMP_PLACES=cores"
            ),
            "正式线程集合": (
                "requested_thread_counts=1,2,4,8,16,32；"
                "physical_core_thread_included=true；report_recomputation=PASS"
            ),
            "预热 $W": "warmup_count=2；repeat_count=7；amortization_count=1",
            "CTest 精确执行": (
                "status=PASS；test_count=10；failed_count=0；skipped_count=0；"
                "not_run_count=0；test_names="
                + ",".join(EXPECTED_CTEST_TESTS)
                + f"；evidence=ctest.xml；junit={artifacts['ctest_junit']['path']}"
                + f"；JUnit_SHA-256={artifacts['ctest_junit']['sha256']}"
            ),
            "CSC3 结构逐项一致": (
                "Tet4=PASS/structure_equal=true/values_finite=true/"
                "scatter_indices_valid=true；Hex8=PASS/structure_equal=true/"
                "values_finite=true/scatter_indices_valid=true"
            ),
            "Frobenius 相对误差": "Tet4=1e-16；Hex8=2e-16；maximum=1e-08",
            "最大绝对误差满足": (
                "Tet4=1e-12/serial_max=100/tolerance=1.0001e-06/"
                "within_tolerance=true；Hex8=2e-12/serial_max=200/"
                "tolerance=2.0001e-06/within_tolerance=true"
            ),
            "位移相对误差满足": "Tet4=0；Hex8=0；maximum=1e-08",
            "自由度方程相对残差": "Tet4=1e-14；Hex8=2e-14；maximum=1e-10",
            "benchmark_samples.csv": (
                f"path={artifacts['benchmark_samples']['path']}；"
                f"SHA-256={artifacts['benchmark_samples']['sha256']}；"
                "raw_sample_count=70；repeat_count=7；threads=1,2,4,8,16,32"
            ),
            "benchmark_summary.json": (
                f"path={artifacts['benchmark_summary']['path']}；"
                f"SHA-256={artifacts['benchmark_summary']['sha256']}；"
                f"report_recomputation={report_recomputation['status']}；"
                f"evidence={report_recomputation['evidence_reference']}"
            ),
            "S_{\\mathrm{numeric}}": "p=8；speedup=1.75；minimum=1.5",
            "S_{\\mathrm{symbolic}}": "p=8；speedup=1.2；exclusive_minimum=1",
            "$CV \\le 0.05$": "numeric=0.02；symbolic=0.03；maximum=0.05",
            "symbolic、numeric": (
                "raw_sample_count=70；report_recomputation=PASS；"
                "evidence=csc3-test-report.zh-CN.md"
            ),
            "CI runner 计时": (
                "evidence_level=formal；report_intent=delivery；"
                "controlled_host_id=linux-intel-host-01"
            ),
            "run_manifest.json": (
                f"execution.status=PASS；evidence_level=formal；report_intent=delivery；"
                f"path={artifacts['run_manifest']['path']}；"
                f"SHA-256={artifacts['run_manifest']['sha256']}"
            ),
            "after-build": (
                "source_and_input_identity=PASS；"
                "evidence=run_manifest.json#identity_checks"
            ),
            "generate_test_report.py": (
                f"report_recomputation=PASS；"
                f"evidence=csc3-test-report.zh-CN.md；"
                f"path={artifacts['canonical_markdown_report']['path']}；"
                f"SHA-256={artifacts['canonical_markdown_report']['sha256']}"
            ),
            "报告中的源码 SHA": (
                f"source_commit={SOURCE_SHA}；source_and_input_identity=PASS；"
                f"delivery_zip={self.archive.name}；SHA-256={self.archive_sha}"
            ),
            "证据 SHA 与报告": (
                f"run_manifest_SHA256={artifacts['run_manifest']['sha256']}；"
                f"report_SHA256={artifacts['canonical_markdown_report']['sha256']}；"
                f"SHA256SUMS_SHA256={artifacts['sha256sums_file']['sha256']}"
            ),
            "SOURCE_COMMIT": (
                f"source_commit={SOURCE_SHA}；path={artifacts['source_commit_file']['path']}；"
                f"SHA-256={artifacts['source_commit_file']['sha256']}"
            ),
            "PACKAGE_CANDIDATE": (
                f"candidate_status=PACKAGE_CANDIDATE；outcome_record="
                f"{artifacts['outcome_record']['path']}；"
                f"SHA-256={artifacts['outcome_record']['sha256']}"
            ),
            "候选 `SHA256SUMS`": (
                f"deterministic_package=PASS；path={artifacts['sha256sums_file']['path']}；"
                f"SHA-256={artifacts['sha256sums_file']['sha256']}"
            ),
            "确定性打包": (
                f"status=PASS；evidence=deterministic-package.txt；"
                f"path={artifacts['deterministic_package_record']['path']}；"
                f"SHA-256={artifacts['deterministic_package_record']['sha256']}"
            ),
            "manifest-only 验证": (
                f"status=PASS；evidence=manifest-only-verification.json；"
                f"path={artifacts['manifest_only_verifier_output']['path']}；"
                f"SHA-256={artifacts['manifest_only_verifier_output']['sha256']}"
            ),
            "完整 clean-room": (
                f"status=PASS；evidence=clean-room-verification.log；"
                f"path={artifacts['clean_room_verifier_log']['path']}；"
                f"SHA-256={artifacts['clean_room_verifier_log']['sha256']}"
            ),
            "validate_acceptance_record.py": (
                f"validator=PASS；acceptance_record={self.record.name}；"
                f"SHA-256={record_sha}"
            ),
            "finalize_delivery.py": (
                "output_precondition=NONEXISTENT；publication=ATOMIC_NO_REPLACE；"
                "final_hash_manifest=FINAL_SHA256SUMS"
            ),
            "Markdown 是权威报告": (
                f"canonical_markdown_report={artifacts['canonical_markdown_report']['path']}；"
                f"SHA-256={artifacts['canonical_markdown_report']['sha256']}；"
                "presentation_pdf=ABSENT"
            ),
            "最终决定只能为": "PASS",
        }
        completed_checklist = fill_checklist_objective_items(
            completed_checklist, self.objective_checklist_values
        )
        completed_checklist = fill_remaining_placeholders(
            completed_checklist,
            [
                "authorization-record:internal-evaluation-001",
                "确认：无公开许可证，禁止公开、转授权或再分发",
                "受控实验记录：host-policy-2026-07-13",
                "复核声明：该测试不等同于独立商业求解器验证",
                "已知限制：仅内部评估，不含商业求解器验证",
                "无未解决 blocker；全部强制门槛通过",
                "按交付 ID、源码 SHA 与 ZIP SHA-256 撤回并从新 RUN_ROOT 重跑",
                "全部强制证据、门槛与四方确认均通过",
            ],
        )
        self.assertNotIn("COMPLETED", completed_checklist)
        self.checklist.write_text(completed_checklist, encoding="utf-8")
        checklist_sha = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
        self.note = self.run_root / "completed-delivery-note.md"
        note_template = (
            DEMO_ROOT / "packaging" / "DELIVERY_NOTE_TEMPLATE.zh-CN.md"
        ).read_text(encoding="utf-8")
        completed_note = (
            note_template.replace(
                "CSC3_DELIVERY_NOTE_STATUS=PENDING",
                "CSC3_DELIVERY_NOTE_STATUS=PASS",
            )
            .replace(
                "| 交付 ID | **REQUIRED BEFORE DELIVERY** |",
                f"| 交付 ID | **{DELIVERY_ID}** |",
            )
            .replace(
                "| 交付日期（UTC） | **REQUIRED BEFORE DELIVERY** |",
                f"| 交付日期（UTC） | **{DELIVERY_DATE_UTC}** |",
            )
            .replace(
                "| Demo 版本 | **REQUIRED BEFORE DELIVERY** |",
                f"| Demo 版本 | **{DEMO_VERSION}** |",
            )
            .replace(
                "| 完整源码 SHA | **REQUIRED BEFORE DELIVERY** |",
                f"| 完整源码 SHA | **{SOURCE_SHA}** |",
            )
            .replace(
                "| Issue #44 URL | **REQUIRED BEFORE DELIVERY** |",
                f"| Issue #44 URL | **{ISSUE_URL}** |",
            )
            .replace(
                "| 发送组织/部门 | **REQUIRED BEFORE DELIVERY** |",
                f"| 发送组织/部门 | **{OPERATOR_ORGANIZATION} / {OPERATOR_DEPARTMENT}** |",
            )
            .replace(
                "| 接收组织/部门 | **REQUIRED BEFORE DELIVERY** |",
                f"| 接收组织/部门 | **{RECIPIENT_ORGANIZATION} / {RECIPIENT_DEPARTMENT}** |",
            )
            .replace(
                "| 指定接收人身份引用 | **REQUIRED BEFORE DELIVERY** |",
                f"| 指定接收人身份引用 | **{RECIPIENT_IDENTITY}** |",
            )
            .replace(
                "| 操作员 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                f"| 操作员 | **{OPERATOR_IDENTITY}** | **{ACKNOWLEDGED_AT_UTC}** | "
                f"**approval:{OPERATOR_IDENTITY}:001** | **ACKNOWLEDGED** |",
            )
            .replace(
                "| 技术复核人 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                f"| 技术复核人 | **{REVIEWER_IDENTITY}** | **{ACKNOWLEDGED_AT_UTC}** | "
                f"**approval:{REVIEWER_IDENTITY}:001** | **ACKNOWLEDGED** |",
            )
            .replace(
                "| 发送方批准/交付批准人 | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** |",
                f"| 发送方批准/交付批准人 | **{APPROVER_IDENTITY}** | "
                f"**{ACKNOWLEDGED_AT_UTC}** | **approval:{APPROVER_IDENTITY}:001** | "
                "**ACKNOWLEDGED** |",
            )
            .replace(
                "| 接收方确认 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                f"| 接收方确认 | **{RECIPIENT_IDENTITY}** | "
                f"**{ACKNOWLEDGED_AT_UTC}** | **approval:{RECIPIENT_IDENTITY}:001** | "
                "**ACKNOWLEDGED** |",
            )
            .replace(
                "正式验收状态（只能为 `PASS`）：**REQUIRED BEFORE DELIVERY**",
                "正式验收状态（只能为 `PASS`）：**PASS**",
            )
            .replace(
                "正确性门槛摘要：**REQUIRED BEFORE DELIVERY**",
                f"正确性门槛摘要：**{CORRECTNESS_SUMMARY}**",
            )
            .replace(
                "性能门槛摘要：**REQUIRED BEFORE DELIVERY**",
                f"性能门槛摘要：**{PERFORMANCE_SUMMARY}**",
            )
            .replace(
                "偏差及批准引用（无偏差也必须填写“无”）：**REQUIRED BEFORE DELIVERY**",
                f"偏差及批准引用（无偏差也必须填写“无”）：**{DEVIATION_SUMMARY}**",
            )
            .replace(
                "证据 SHA-256：**REQUIRED BEFORE DELIVERY**",
                "证据 SHA-256：**"
                + self.record_data["artifacts"]["run_manifest"]["sha256"]
                + "**",
            )
            .replace(
                "报告 SHA-256：**REQUIRED BEFORE DELIVERY**",
                "报告 SHA-256：**"
                + self.record_data["artifacts"]["canonical_markdown_report"]["sha256"]
                + "**",
            )
            .replace(
                "ZIP SHA-256：**REQUIRED BEFORE DELIVERY**",
                f"ZIP SHA-256：**{self.archive_sha}**",
            )
            .replace(
                "机器可读验收记录路径：**REQUIRED BEFORE DELIVERY**",
                f"机器可读验收记录路径：**{self.record.name}**",
            )
            .replace(
                "复现所需完整源码 SHA：**REQUIRED BEFORE DELIVERY**",
                f"复现所需完整源码 SHA：**{SOURCE_SHA}**",
            )
            .replace(
                "受控主机 ID：**REQUIRED BEFORE DELIVERY**",
                "受控主机 ID：**linux-intel-host-01**",
            )
            .replace(
                "输入 SHA-256 与字节数：**REQUIRED BEFORE DELIVERY**",
                f"输入 SHA-256 与字节数：**{'e' * 64}** / **123456 bytes**",
            )
            .replace(
                "完整复现命令/记录位置：**REQUIRED BEFORE DELIVERY**",
                "完整复现命令/记录位置：**runbook.log** / **"
                + self.record_data["artifacts"]["runbook_log"]["sha256"]
                + "**",
            )
            .replace(
                "可选 PDF 路径及 SHA-256：**REQUIRED BEFORE DELIVERY**",
                "可选 PDF 路径及 SHA-256：**presentation_pdf=ABSENT**",
            )
        )
        artifact_rows = {
            "原始证据目录/manifest": "run_manifest",
            "规范 Markdown 报告": "canonical_markdown_report",
            "正式源码 ZIP": "delivery_zip",
            "`host-preflight.txt`": "host_preflight",
            "`SOURCE_COMMIT`": "source_commit_file",
            "`SHA256SUMS`": "sha256sums_file",
            "`deterministic-package.txt`": "deterministic_package_record",
            "manifest-only verifier 输出": "manifest_only_verifier_output",
            "`clean-room-verification.log`": "clean_room_verifier_log",
        }
        for label, artifact_name in artifact_rows.items():
            binding = self.record_data["artifacts"][artifact_name]
            completed_note = completed_note.replace(
                f"| {label} | **REQUIRED BEFORE DELIVERY** | "
                "**REQUIRED BEFORE DELIVERY** |",
                f"| {label} | **{binding['path']}** | **{binding['sha256']}** |",
            )
        completed_note = completed_note.replace(
            "| 机器可读验收记录 | **REQUIRED BEFORE DELIVERY** | "
            "**REQUIRED BEFORE DELIVERY** |",
            f"| 机器可读验收记录 | **{self.record.name}** | "
            f"**{hashlib.sha256(self.record.read_bytes()).hexdigest()}** |",
        ).replace(
            "| 完成版验收清单 | **REQUIRED BEFORE DELIVERY** | "
            "**REQUIRED BEFORE DELIVERY** |",
            f"| 完成版验收清单 | **{self.checklist.name}** | "
            f"**{checklist_sha}** |",
        )
        deterministic = self.record_data["artifacts"]["deterministic_package_record"]
        manifest_only = self.record_data["artifacts"]["manifest_only_verifier_output"]
        clean_room = self.record_data["artifacts"]["clean_room_verifier_log"]
        self.deterministic_summary = (
            f"deterministic_package=PASS（{deterministic['path']}；SHA-256 "
            f"{deterministic['sha256']}）；manifest_only=PASS（{manifest_only['path']}；"
            f"SHA-256 {manifest_only['sha256']}）；clean_room=PASS（{clean_room['path']}；"
            f"SHA-256 {clean_room['sha256']}）"
        )
        completed_note = completed_note.replace(
            "确定性打包与 clean-room 结果：**REQUIRED BEFORE DELIVERY**",
            f"确定性打包与 clean-room 结果：**{self.deterministic_summary}**",
        )
        completed_note = fill_remaining_placeholders(
            completed_note,
            [
                "供研究院求解器开发部门在书面授权范围内进行内部技术评估",
                "authorization-record:internal-evaluation-001",
                "PASS：白名单源码、文档、测试、证据与 manifest 已逐项核对",
                "PASS：不含预编译二进制、商业求解器或外部发布授权",
                "仅证明组装正确性与受控主机性能，不替代商业求解器验证",
                "无未解决风险；全部强制门槛与四方确认均已通过",
                "operator-id / approval:operator-id:001",
                "issue-44-replacement-procedure-v1",
                "批准按 INTERNAL EVALUATION ONLY 向指定接收部门交付",
                "确认仅在内部评估范围接收，且不公开或再分发",
            ],
        )
        self.assertNotIn("COMPLETED", completed_note)
        self.note.write_text(completed_note, encoding="utf-8")

    @contextmanager
    def validated_snapshot(self, *_args: object, **_kwargs: object):
        yield SimpleNamespace(
            result={"status": "PASS"},
            record=self.record_data,
            record_content=self.record.read_bytes(),
            archive_content=self.archive.read_bytes(),
            artifact_contents={
                name: (self.run_root / binding["path"]).read_bytes()
                for name, binding in self.record_data["artifacts"].items()
            },
        )

    def finalize(self, out_name: str = "final-delivery") -> tuple[dict[str, object], Path]:
        output = self.root / out_name
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ) as validator:
            result = self.module.finalize_delivery(
                record_path=self.record,
                run_root=self.run_root,
                archive_path=self.archive,
                checklist_path=self.checklist,
                delivery_note_path=self.note,
                output_directory=output,
            )
        validator.assert_called_once_with(self.record, self.run_root, self.archive)
        return result, output

    def test_valid_approved_bundle_is_finalized_and_hash_bound(self) -> None:
        result, output = self.finalize()
        self.assertEqual("PASS", result["status"])
        self.assertEqual(DELIVERY_ID, result["delivery_id"])
        expected_files = {
            self.archive.name,
            "ACCEPTANCE_RECORD.json",
            "ACCEPTANCE_CHECKLIST.zh-CN.md",
            "DELIVERY_NOTE.zh-CN.md",
            "FINALIZATION.json",
            "FINAL_SHA256SUMS",
            "ACCEPTANCE_EVIDENCE",
        }
        self.assertEqual(expected_files, {path.name for path in output.iterdir()})
        self.assertEqual(
            self.runbook_log.read_bytes(),
            (output / "ACCEPTANCE_EVIDENCE" / "runbook_log.log").read_bytes(),
        )

        finalization = json.loads((output / "FINALIZATION.json").read_text(encoding="utf-8"))
        self.assertEqual("csc3-demo-finalization-v1", finalization["schema"])
        self.assertEqual("PASS", finalization["status"])
        self.assertEqual(SOURCE_SHA, finalization["source_commit"])
        self.assertNotIn("created", finalization)
        self.assertEqual(
            {
                "bundled_path": "ACCEPTANCE_EVIDENCE/runbook_log.log",
                "record_path": "runbook.log",
                "sha256": hashlib.sha256(self.runbook_log.read_bytes()).hexdigest(),
                "size_bytes": self.runbook_log.stat().st_size,
            },
            finalization["acceptance_evidence"]["runbook_log"],
        )

        checksum_lines = (output / "FINAL_SHA256SUMS").read_text(
            encoding="utf-8"
        ).splitlines()
        checksum_names = [line.split("  ", 1)[1] for line in checksum_lines]
        self.assertEqual(sorted(checksum_names), checksum_names)
        self.assertNotIn("FINAL_SHA256SUMS", checksum_names)
        expected_evidence = {
            str(binding["bundled_path"])
            for binding in finalization["acceptance_evidence"].values()
        }
        self.assertEqual(
            (expected_files - {"FINAL_SHA256SUMS", "ACCEPTANCE_EVIDENCE"})
            | expected_evidence,
            set(checksum_names),
        )
        for line in checksum_lines:
            digest, name = line.split("  ", 1)
            self.assertEqual(
                digest, hashlib.sha256((output / Path(name)).read_bytes()).hexdigest()
            )

    def test_same_inputs_produce_identical_final_files(self) -> None:
        _, first = self.finalize("first")
        _, second = self.finalize("second")
        self.assertEqual(
            {
                path.relative_to(first).as_posix(): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            },
            {
                path.relative_to(second).as_posix(): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            },
        )

    def test_source_exchange_after_validation_cannot_change_final_bytes(self) -> None:
        record_content = self.record.read_bytes()
        archive_content = self.archive.read_bytes()
        runbook_content = self.runbook_log.read_bytes()
        artifact_contents = {
            name: (self.run_root / binding["path"]).read_bytes()
            for name, binding in self.record_data["artifacts"].items()
        }

        def exchange_sources() -> None:
            self.record.write_text('{"status":"PASS","forged":true}\n', encoding="utf-8")
            self.archive.write_bytes(b"forged archive bytes")
            self.runbook_log.write_bytes(b"forged evidence bytes\n")

        @contextmanager
        def immutable_snapshot(*_args: object, **_kwargs: object):
            exchange_sources()
            yield SimpleNamespace(
                result={"status": "PASS"},
                record=self.record_data,
                record_content=record_content,
                archive_content=archive_content,
                artifact_contents=artifact_contents,
            )

        output = self.root / "source-exchange"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=immutable_snapshot,
        ):
            result = self.module.finalize_delivery(
                self.record,
                self.run_root,
                self.archive,
                self.checklist,
                self.note,
                output,
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            (output / "ACCEPTANCE_RECORD.json").read_bytes(), record_content
        )
        self.assertEqual((output / self.archive.name).read_bytes(), archive_content)
        self.assertEqual(
            (output / "ACCEPTANCE_EVIDENCE" / "runbook_log.log").read_bytes(),
            runbook_content,
        )

    def test_incomplete_sidecars_fail_before_output_creation(self) -> None:
        attacks = {
            "pending checklist": (self.checklist, "PASS", "PENDING"),
            "unchecked item": (self.checklist, "- [x]", "- [ ]"),
            "placeholder": (self.note, DELIVERY_ID, "REQUIRED BEFORE DELIVERY"),
            "missing delivery id": (self.note, DELIVERY_ID, "different-delivery"),
            "missing source": (self.note, SOURCE_SHA, "c" * 40),
            "missing archive digest": (self.note, self.archive_sha, "d" * 64),
        }
        for index, (name, (path, old, new)) in enumerate(attacks.items()):
            with self.subTest(name=name):
                original = path.read_text(encoding="utf-8")
                path.write_text(original.replace(old, new, 1), encoding="utf-8")
                output = self.root / f"rejected-{index}"
                with mock.patch.object(
                    self.module,
                    "validated_acceptance_snapshot",
                    side_effect=self.validated_snapshot,
                ):
                    with self.assertRaises(self.module.FinalizationError):
                        self.module.finalize_delivery(
                            self.record,
                            self.run_root,
                            self.archive,
                            self.checklist,
                            self.note,
                            output,
                        )
                self.assertFalse(output.exists())
                path.write_text(original, encoding="utf-8")

    def test_dummy_objective_sidecar_values_fail_before_output_creation(self) -> None:
        original = self.note.read_text(encoding="utf-8")
        run_manifest = self.record_data["artifacts"]["run_manifest"]
        canonical = (
            f"| 原始证据目录/manifest | **{run_manifest['path']}** | "
            f"**{run_manifest['sha256']}** |"
        )
        self.assertIn(canonical, original)
        self.note.write_text(
            original.replace(
                canonical,
                "| 原始证据目录/manifest | **COMPLETED** | **COMPLETED** |",
            ),
            encoding="utf-8",
        )
        output = self.root / "dummy-objective-values"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"objective|artifact|canonical record-bound|exact bindings|dummy|incomplete",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_each_objective_sidecar_slot_is_bound_to_validated_facts(self) -> None:
        attacks = (
            (
                self.checklist,
                f"- [x] Demo 版本：`{DEMO_VERSION}`",
                "- [x] Demo 版本：`COMPLETED`",
            ),
            (
                self.note,
                f"| 交付日期（UTC） | **{DELIVERY_DATE_UTC}** |",
                "| 交付日期（UTC） | **COMPLETED** |",
            ),
            (
                self.note,
                f"| Demo 版本 | **{DEMO_VERSION}** |",
                "| Demo 版本 | **COMPLETED** |",
            ),
            (
                self.note,
                f"正确性门槛摘要：**{CORRECTNESS_SUMMARY}**",
                "正确性门槛摘要：**COMPLETED**",
            ),
            (
                self.note,
                f"性能门槛摘要：**{PERFORMANCE_SUMMARY}**",
                "性能门槛摘要：**PASS**",
            ),
            (
                self.note,
                f"确定性打包与 clean-room 结果：**{self.deterministic_summary}**",
                "确定性打包与 clean-room 结果：**COMPLETED**",
            ),
            (
                self.checklist,
                "- [x] 偏差清单（无偏差也必须写“无”并说明）："
                f"`{DEVIATION_SUMMARY}`；`PASS`",
                "- [x] 偏差清单（无偏差也必须写“无”并说明）："
                "`PASS`；`PASS`",
            ),
            (
                self.note,
                "偏差及批准引用（无偏差也必须填写“无”）："
                f"**{DEVIATION_SUMMARY}**",
                "偏差及批准引用（无偏差也必须填写“无”）：**PASS**",
            ),
        )
        for index, (path, canonical, forged) in enumerate(attacks):
            with self.subTest(index=index, path=path.name):
                original = path.read_text(encoding="utf-8")
                original_note = self.note.read_text(encoding="utf-8")
                self.assertIn(canonical, original)
                path.write_text(original.replace(canonical, forged, 1), encoding="utf-8")
                if path == self.checklist:
                    old_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
                    new_digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    self.note.write_text(
                        original_note.replace(
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{old_digest}** |",
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{new_digest}** |",
                            1,
                        ),
                        encoding="utf-8",
                    )
                output = self.root / f"objective-slot-rejected-{index}"
                with mock.patch.object(
                    self.module,
                    "validated_acceptance_snapshot",
                    side_effect=self.validated_snapshot,
                ):
                    with self.assertRaisesRegex(
                        self.module.FinalizationError,
                        r"objective|canonical|dummy|exact bindings",
                    ):
                        self.module.finalize_delivery(
                            self.record,
                            self.run_root,
                            self.archive,
                            self.checklist,
                            self.note,
                            output,
                        )
                self.assertFalse(output.exists())
                path.write_text(original, encoding="utf-8")
                self.note.write_text(original_note, encoding="utf-8")

    def test_controlled_host_id_checklist_item_is_record_bound(self) -> None:
        original = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        canonical = "- [x] 受控主机 ID：`linux-intel-host-01`"
        forged = "- [x] 受控主机 ID：`PASS`"
        self.assertIn(canonical, original)
        self.checklist.write_text(
            original.replace(canonical, forged, 1), encoding="utf-8"
        )
        old_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
        new_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
        self.note.write_text(
            original_note.replace(
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{old_digest}** |",
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{new_digest}** |",
                1,
            ),
            encoding="utf-8",
        )
        output = self.root / "forged-controlled-host-id"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"checklist|canonical|record-bound|objective",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_ctest_nested_name_sequence_is_immutable(self) -> None:
        original = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        canonical = "  10. `Csc3DemoAtomicContention`"
        forged = "  10. `ForgedAcceptanceTest`"
        self.assertIn(canonical, original)
        self.checklist.write_text(
            original.replace(canonical, forged, 1), encoding="utf-8"
        )
        old_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
        new_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
        self.note.write_text(
            original_note.replace(
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{old_digest}** |",
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{new_digest}** |",
                1,
            ),
            encoding="utf-8",
        )
        output = self.root / "forged-ctest-name"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"nested|CTest|template|structure|objective",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_deviation_item_suffix_is_immutable(self) -> None:
        original = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        canonical = (
            "  只能包含带非空批准引用的 `ACCEPTED_INTERNAL_ONLY`，"
            "`REJECTED` 必须对应 `FAIL`，"
        )
        forged = "  任意偏差均可接受，"
        self.assertIn(canonical, original)
        self.checklist.write_text(
            original.replace(canonical, forged, 1), encoding="utf-8"
        )
        old_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
        new_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
        self.note.write_text(
            original_note.replace(
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{old_digest}** |",
                f"| 完成版验收清单 | **{self.checklist.name}** | "
                f"**{new_digest}** |",
                1,
            ),
            encoding="utf-8",
        )
        output = self.root / "forged-deviation-suffix"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"objective|canonical|template|structure",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_each_record_derived_checklist_item_rejects_independent_forgery(self) -> None:
        original_checklist = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        old_digest = hashlib.sha256(original_checklist.encode("utf-8")).hexdigest()
        for index, selector in enumerate(self.objective_checklist_values):
            with self.subTest(selector=selector):
                forged = replace_checklist_objective_value(
                    original_checklist, selector, "OK"
                )
                self.checklist.write_text(forged, encoding="utf-8")
                new_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
                self.note.write_text(
                    original_note.replace(
                        f"| 完成版验收清单 | **{self.checklist.name}** | "
                        f"**{old_digest}** |",
                        f"| 完成版验收清单 | **{self.checklist.name}** | "
                        f"**{new_digest}** |",
                        1,
                    ),
                    encoding="utf-8",
                )
                output = self.root / f"record-derived-forgery-{index}"
                with mock.patch.object(
                    self.module,
                    "validated_acceptance_snapshot",
                    side_effect=self.validated_snapshot,
                ):
                    with self.assertRaisesRegex(
                        self.module.FinalizationError,
                        r"objective|canonical|record-bound|checklist",
                    ):
                        self.module.finalize_delivery(
                            self.record,
                            self.run_root,
                            self.archive,
                            self.checklist,
                            self.note,
                            output,
                        )
                self.assertFalse(output.exists())
                self.checklist.write_text(original_checklist, encoding="utf-8")
                self.note.write_text(original_note, encoding="utf-8")

    def test_human_checklist_fields_reject_generic_dummy_tokens(self) -> None:
        selectors = (
            "授权与接收方范围",
            "已确认当前无公开许可证",
            "主机负载和频率策略",
            "复核人理解",
            "已知限制与非目标",
            "未解决 blocker",
            "回滚与复现路径",
            "最终决定理由",
        )
        generic_values = ("PASS", "OK", "DONE", "COMPLETED", "N/A")
        original_checklist = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        old_digest = hashlib.sha256(original_checklist.encode("utf-8")).hexdigest()
        for index, selector in enumerate(selectors):
            for generic in generic_values:
                with self.subTest(selector=selector, generic=generic):
                    forged = replace_checklist_objective_value(
                        original_checklist, selector, generic
                    )
                    self.checklist.write_text(forged, encoding="utf-8")
                    new_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
                    self.note.write_text(
                        original_note.replace(
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{old_digest}** |",
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{new_digest}** |",
                            1,
                        ),
                        encoding="utf-8",
                    )
                    output = self.root / f"human-dummy-{index}-{generic.replace('/', '_')}"
                    with mock.patch.object(
                        self.module,
                        "validated_acceptance_snapshot",
                        side_effect=self.validated_snapshot,
                    ):
                        with self.assertRaisesRegex(
                            self.module.FinalizationError,
                            r"human|dummy|generic|checklist",
                        ):
                            self.module.finalize_delivery(
                                self.record,
                                self.run_root,
                                self.archive,
                                self.checklist,
                                self.note,
                                output,
                            )
                    self.assertFalse(output.exists())
                    self.checklist.write_text(
                        original_checklist, encoding="utf-8"
                    )
                    self.note.write_text(original_note, encoding="utf-8")

    def test_human_sidecar_fields_reject_punctuated_or_markdown_dummy_tokens(
        self,
    ) -> None:
        variants = (
            "PASS。",
            "OK。",
            "N/A。",
            "`PASS`。",
            "**DONE；**",
            "  COMPLETED;  ",
            "PASS；OK",
            "PASS/OK",
            "`PASS` / **OK**",
            "PASS，DONE",
            "> **PASS**",
            "+ PASS",
            "1. PASS",
            "Ｎ／Ａ",
            "✅PASS",
            "PASS✅",
            "[x] PASS",
            "- [X] **PASS**",
            "✔\ufe0f PASS",
            "✅\ufe0fPASS",
            "PASS✅\ufe0f",
            "P\u200bASS",
            "PASS\u200d",
            "\ufeffPASS",
            "PASS\u200bDONE",
            "PASS\u200dOK",
            "COMPLETED\ufeffPASS",
            "P\u200bASS\u200dOK",
        )
        original_checklist = self.checklist.read_text(encoding="utf-8")
        original_note = self.note.read_text(encoding="utf-8")
        old_checklist_digest = hashlib.sha256(
            original_checklist.encode("utf-8")
        ).hexdigest()
        for index, variant in enumerate(variants):
            with self.subTest(sidecar="checklist", variant=variant):
                forged = replace_checklist_objective_value(
                    original_checklist, "授权与接收方范围", variant
                )
                self.checklist.write_text(forged, encoding="utf-8")
                new_checklist_digest = hashlib.sha256(
                    self.checklist.read_bytes()
                ).hexdigest()
                self.note.write_text(
                    original_note.replace(
                        f"| 完成版验收清单 | **{self.checklist.name}** | "
                        f"**{old_checklist_digest}** |",
                        f"| 完成版验收清单 | **{self.checklist.name}** | "
                        f"**{new_checklist_digest}** |",
                        1,
                    ),
                    encoding="utf-8",
                )
                try:
                    output = self.root / f"punctuated-checklist-dummy-{index}"
                    with mock.patch.object(
                        self.module,
                        "validated_acceptance_snapshot",
                        side_effect=self.validated_snapshot,
                    ):
                        with self.assertRaisesRegex(
                            self.module.FinalizationError,
                            r"human|dummy|generic|checklist",
                        ):
                            self.module.finalize_delivery(
                                self.record,
                                self.run_root,
                                self.archive,
                                self.checklist,
                                self.note,
                                output,
                            )
                    self.assertFalse(output.exists())
                finally:
                    self.checklist.write_text(
                        original_checklist, encoding="utf-8"
                    )
                    self.note.write_text(original_note, encoding="utf-8")

            with self.subTest(sidecar="delivery note", variant=variant):
                prefix = "交付目的与允许使用范围："
                canonical = (
                    prefix
                    + "**供研究院求解器开发部门在书面授权范围内进行内部技术评估**"
                )
                self.assertIn(canonical, original_note)
                self.note.write_text(
                    original_note.replace(canonical, prefix + f"**{variant}**", 1),
                    encoding="utf-8",
                )
                try:
                    output = self.root / f"punctuated-note-dummy-{index}"
                    with mock.patch.object(
                        self.module,
                        "validated_acceptance_snapshot",
                        side_effect=self.validated_snapshot,
                    ):
                        with self.assertRaisesRegex(
                            self.module.FinalizationError,
                            r"human|dummy|generic|delivery note",
                        ):
                            self.module.finalize_delivery(
                                self.record,
                                self.run_root,
                                self.archive,
                                self.checklist,
                                self.note,
                                output,
                            )
                    self.assertFalse(output.exists())
                finally:
                    self.note.write_text(original_note, encoding="utf-8")

    def test_human_sidecar_fields_allow_substantive_narrative_with_pass_word(
        self,
    ) -> None:
        original = self.note.read_text(encoding="utf-8")
        canonical = (
            "交付目的与允许使用范围："
            "**供研究院求解器开发部门在书面授权范围内进行内部技术评估**"
        )
        narratives = (
            "评审结论为 PASS；仅允许指定部门内部技术评估。",
            "N/A 不适用，因为本次交付不包含商业求解器验证；"
            "边界已由审批记录 AUTH-2026-07-14 确认。",
            "PASS — authorized only for internal evaluation by the named "
            "recipient department; redistribution is prohibited.",
            "性能证据为 PASS；数值组装加速比 1.75，计时单位 ms，"
            "受控主机使用 32 cores。",
            "门槛说明：$e_F \\le 10^{-8}$，$CV \\le 5\\%$，"
            "样本数为 70；技术结论 PASS。",
            "Approval AUTH-2026-07-14 permits the named recipient to evaluate "
            "the demo internally for 30 days; redistribution remains prohibited.",
            "证据保留期为 180 天，撤回流程引用 Issue #44；仅指定接收部门可访问。",
        )
        self.assertIn(canonical, original)
        for index, narrative in enumerate(narratives):
            with self.subTest(narrative=narrative):
                substantive = f"交付目的与允许使用范围：**{narrative}**"
                self.note.write_text(
                    original.replace(canonical, substantive, 1), encoding="utf-8"
                )
                result, _ = self.finalize(
                    f"substantive-human-narrative-{index}"
                )
                self.assertEqual(result["status"], "PASS")
                self.note.write_text(original, encoding="utf-8")

    def test_absent_presentation_pdf_binding_rejects_forged_note_value(self) -> None:
        original = self.note.read_text(encoding="utf-8")
        canonical = "可选 PDF 路径及 SHA-256：**presentation_pdf=ABSENT**"
        forged = (
            "可选 PDF 路径及 SHA-256：**presentation_pdf=forged.pdf；"
            f"PDF_SHA-256={'f' * 64}**"
        )
        self.assertIn(canonical, original)
        self.note.write_text(
            original.replace(canonical, forged, 1), encoding="utf-8"
        )
        output = self.root / "forged-absent-presentation-pdf"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"PDF|presentation_pdf|exact bindings|record-bound",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_present_presentation_pdf_binding_rejects_note_mismatch(self) -> None:
        old_record_digest = hashlib.sha256(self.record.read_bytes()).hexdigest()
        old_checklist_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()
        pdf_path = "evidence/csc3-test-report.zh-CN.pdf"
        pdf = self.run_root / pdf_path
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"presentation derivative\n")
        pdf_digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        self.record_data["artifacts"]["presentation_pdf"] = {
            "path": pdf_path,
            "size_bytes": pdf.stat().st_size,
            "sha256": pdf_digest,
        }
        self.record.write_text(
            json.dumps(self.record_data, sort_keys=True) + "\n", encoding="utf-8"
        )
        new_record_digest = hashlib.sha256(self.record.read_bytes()).hexdigest()

        checklist_text = self.checklist.read_text(encoding="utf-8").replace(
            "presentation_pdf=ABSENT",
            f"presentation_pdf={pdf_path}；PDF_SHA-256={pdf_digest}",
            1,
        )
        checklist_text = checklist_text.replace(
            old_record_digest, new_record_digest
        )
        self.checklist.write_text(checklist_text, encoding="utf-8")
        new_checklist_digest = hashlib.sha256(self.checklist.read_bytes()).hexdigest()

        note_text = self.note.read_text(encoding="utf-8")
        note_text = note_text.replace(old_record_digest, new_record_digest)
        note_text = note_text.replace(old_checklist_digest, new_checklist_digest)
        note_text = note_text.replace(
            "可选 PDF 路径及 SHA-256：**presentation_pdf=ABSENT**",
            f"可选 PDF 路径及 SHA-256：**presentation_pdf={pdf_path}；"
            f"PDF_SHA-256={pdf_digest}**",
            1,
        )
        self.note.write_text(note_text, encoding="utf-8")
        result, _ = self.finalize("canonical-present-presentation-pdf")
        self.assertEqual(result["status"], "PASS")

        note_text = note_text.replace(
            f"可选 PDF 路径及 SHA-256：**presentation_pdf={pdf_path}；"
            f"PDF_SHA-256={pdf_digest}**",
            "可选 PDF 路径及 SHA-256：**presentation_pdf=forged.pdf；"
            f"PDF_SHA-256={'f' * 64}**",
            1,
        )
        self.note.write_text(note_text, encoding="utf-8")

        output = self.root / "forged-present-presentation-pdf"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaisesRegex(
                self.module.FinalizationError,
                r"PDF|presentation_pdf|exact bindings|record-bound",
            ):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_completed_dummy_sentinel_is_rejected_anywhere_in_sidecars(self) -> None:
        attacks = (
            (
                self.checklist,
                "已知限制：仅内部评估，不含商业求解器验证",
                "COMPLETED",
            ),
            (
                self.note,
                "仅证明组装正确性与受控主机性能，不替代商业求解器验证",
                "COMPLETED",
            ),
        )
        for index, (path, old, new) in enumerate(attacks):
            with self.subTest(index=index, path=path.name):
                original = path.read_text(encoding="utf-8")
                original_note = self.note.read_text(encoding="utf-8")
                self.assertIn(old, original)
                path.write_text(original.replace(old, new, 1), encoding="utf-8")
                if path == self.checklist:
                    old_digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
                    new_digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    self.note.write_text(
                        original_note.replace(
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{old_digest}** |",
                            f"| 完成版验收清单 | **{self.checklist.name}** | "
                            f"**{new_digest}** |",
                            1,
                        ),
                        encoding="utf-8",
                    )
                output = self.root / f"dummy-sentinel-rejected-{index}"
                with mock.patch.object(
                    self.module,
                    "validated_acceptance_snapshot",
                    side_effect=self.validated_snapshot,
                ):
                    with self.assertRaisesRegex(
                        self.module.FinalizationError, r"dummy|COMPLETED|incomplete"
                    ):
                        self.module.finalize_delivery(
                            self.record,
                            self.run_root,
                            self.archive,
                            self.checklist,
                            self.note,
                            output,
                        )
                self.assertFalse(output.exists())
                path.write_text(original, encoding="utf-8")
                self.note.write_text(original_note, encoding="utf-8")

    def test_designated_sidecar_fields_must_match_the_acceptance_record(self) -> None:
        attacks = (
            (self.checklist, ISSUE_URL, "https://example.invalid/issues/44"),
            (self.checklist, RECIPIENT_IDENTITY, "unrelated-recipient"),
            (self.checklist, ACKNOWLEDGED_AT_UTC, "2026-07-13T13:00:00Z"),
            (
                self.checklist,
                f"approval:{OPERATOR_IDENTITY}:001",
                f"approval:{OPERATOR_IDENTITY}:999",
            ),
            (self.checklist, "最终状态：`PASS`", "最终状态：`FAIL`"),
            (self.note, OPERATOR_ORGANIZATION, "Unrelated Sender"),
            (self.note, RECIPIENT_DEPARTMENT, "Unrelated Department"),
            (self.note, REVIEWER_IDENTITY, "unrelated-reviewer"),
            (
                self.note,
                f"approval:{APPROVER_IDENTITY}:001",
                f"approval:{APPROVER_IDENTITY}:999",
            ),
            (
                self.note,
                "正式验收状态（只能为 `PASS`）：**PASS**",
                "正式验收状态（只能为 `PASS`）：**FAIL**",
            ),
        )
        for index, (path, old, new) in enumerate(attacks):
            with self.subTest(index=index, path=path.name):
                original = path.read_text(encoding="utf-8")
                self.assertIn(old, original)
                path.write_text(original.replace(old, new, 1), encoding="utf-8")
                output = self.root / f"binding-rejected-{index}"
                with mock.patch.object(
                    self.module,
                    "validated_acceptance_snapshot",
                    side_effect=self.validated_snapshot,
                ):
                    with self.assertRaises(self.module.FinalizationError):
                        self.module.finalize_delivery(
                            self.record,
                            self.run_root,
                            self.archive,
                            self.checklist,
                            self.note,
                            output,
                        )
                self.assertFalse(output.exists())
                path.write_text(original, encoding="utf-8")

    def test_keyword_only_sidecars_cannot_forge_template_structure(self) -> None:
        self.checklist.write_text(
            "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS\n"
            f"{DELIVERY_ID}\n{SOURCE_SHA}\n{self.archive.name}\n{self.archive_sha}\n",
            encoding="utf-8",
        )
        self.note.write_text(
            "CSC3_DELIVERY_NOTE_STATUS=PASS\n"
            f"{DELIVERY_ID}\n{SOURCE_SHA}\n{self.archive.name}\n{self.archive_sha}\n",
            encoding="utf-8",
        )
        output = self.root / "structure-rejected"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())

    def test_write_failure_never_publishes_partial_final_directory(self) -> None:
        output = self.root / "write-failure"
        original_write = self.module._write_file
        call_count = 0

        def fail_second_write(path: Path, content: bytes) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError("injected write failure")
            original_write(path, content)

        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ), mock.patch.object(
            self.module, "_write_file", side_effect=fail_second_write
        ):
            with self.assertRaises(OSError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )
        self.assertFalse(output.exists())
        self.assertEqual([], list(self.root.glob(".write-failure.*")))

    @unittest.skipUnless(os.name == "posix", "atomic no-replace publication is POSIX-only")
    def test_destination_race_never_clobbers_a_new_directory(self) -> None:
        output = self.root / "destination-race"
        real_stat = self.module.os.stat
        injected = False

        def inject_destination(path: object, *args: object, **kwargs: object):
            nonlocal injected
            if (
                path == output.name
                and kwargs.get("dir_fd") is not None
                and not injected
            ):
                injected = True
                output.mkdir()
                raise FileNotFoundError(output)
            return real_stat(path, *args, **kwargs)

        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ), mock.patch.object(self.module.os, "stat", side_effect=inject_destination):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    output,
                )

        self.assertTrue(injected)
        self.assertTrue(output.is_dir())
        self.assertEqual([], list(output.iterdir()))
        self.assertEqual([], list(self.root.glob(".destination-race.*")))

    def test_real_validator_rejects_incomplete_record_without_output(self) -> None:
        output = self.root / "real-validator-rejected"
        with self.assertRaises(self.module.FinalizationError):
            self.module.finalize_delivery(
                self.record,
                self.run_root,
                self.archive,
                self.checklist,
                self.note,
                output,
            )
        self.assertFalse(output.exists())

    def test_validator_failure_and_existing_output_fail_before_write(self) -> None:
        rejected = self.root / "validator-rejected"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.module.AcceptanceRecordError(["forged PASS"]),
        ):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    rejected,
                )
        self.assertFalse(rejected.exists())

        existing = self.root / "existing"
        existing.mkdir()
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.note,
                    existing,
                )
        self.assertEqual([], list(existing.iterdir()))

    def test_aliased_inputs_are_rejected(self) -> None:
        output = self.root / "alias-rejected"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    self.checklist,
                    output,
                )
        self.assertFalse(output.exists())

    def test_symlink_input_is_rejected_when_supported(self) -> None:
        symlink = self.run_root / "note-link.md"
        try:
            symlink.symlink_to(self.note)
        except (AttributeError, NotImplementedError, OSError):
            return
        output = self.root / "symlink-rejected"
        with mock.patch.object(
            self.module,
            "validated_acceptance_snapshot",
            side_effect=self.validated_snapshot,
        ):
            with self.assertRaises(self.module.FinalizationError):
                self.module.finalize_delivery(
                    self.record,
                    self.run_root,
                    self.archive,
                    self.checklist,
                    symlink,
                    output,
                )
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
