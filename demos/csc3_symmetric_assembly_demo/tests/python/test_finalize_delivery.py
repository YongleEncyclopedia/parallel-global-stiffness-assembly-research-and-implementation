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
            "controlled_host": {"controlled_host_id": "linux-intel-host-01"},
            "input": {"sha256": "e" * 64, "size_bytes": 123456},
            "execution": {
                "status": "PASS",
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
                "tet4": {"status": "PASS"},
                "hex8": {"status": "PASS"},
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
            },
            "verifications": {
                "status": "PASS",
                "deterministic_package": {"status": "PASS"},
                "manifest_only": {"status": "PASS"},
                "clean_room": {"status": "PASS"},
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
        completed_checklist = fill_remaining_placeholders(
            completed_checklist,
            [
                "authorization-record:internal-evaluation-001",
                "INTERNAL EVALUATION ONLY",
                "确认：无公开许可证，禁止公开、转授权或再分发",
                "PASS（完整且非 shallow/non-sparse checkout）",
                "PASS（HEAD 与交付 SHA 一致）",
                "PASS（开始与结束时工作树均干净）",
                "examples/3d-WindTurbineHub.inp",
                "PASS（Git LFS 实体已物化）",
                "PASS（字节数与 HEAD LFS pointer 一致）",
                "PASS（SHA-256 与 HEAD LFS oid 一致）",
                "linux-intel-host-01",
                "PASS（Linux x86_64 GenuineIntel）",
                "PASS（host-preflight.txt 已完整记录）",
                "PASS（GCC/CMake/Ninja/Python/Git/Git LFS 版本已绑定）",
                "PASS（OpenMP 绑定环境逐项一致）",
                "PASS（线程集合含 1,2,4,8,16 及物理核数）",
                "PASS（W=2、R=7、m=1）",
                "PASS（主机负载与频率策略符合受控实验规则）",
                "PASS（十项 CTest 全部通过，无 skip/not-run）",
                "PASS（Tet4/Hex8 结构、scatter 与有限值检查通过）",
                "PASS（记录值满足 Frobenius 相对误差门槛）",
                "PASS（记录值满足尺度相关最大绝对误差门槛）",
                "PASS（Tet4/Hex8 位移相对误差通过）",
                "PASS（Tet4/Hex8 相对残差通过）",
                "确认：该测试不等同于独立商业求解器验证",
                "PASS（完整保留全部正式重复原始样本）",
                "PASS（统计量已从原始样本重算）",
                "PASS（numeric speedup=1.75，p=8）",
                "PASS（symbolic speedup=1.2，p=8）",
                "PASS（numeric CV=0.02，symbolic CV=0.03）",
                "PASS（symbolic/numeric/端到端/摊销时间完整）",
                "PASS（CI runner 计时未进入正式结论）",
                "PASS（manifest 为 formal/delivery）",
                "PASS（三阶段源码与输入身份检查通过）",
                "PASS（报告由当前提交脚本从原始证据生成）",
                "PASS（报告、证据与 ZIP 源码 SHA 一致）",
                "PASS（证据哈希与报告、manifest、SHA256SUMS 一致）",
                "PASS（SOURCE_COMMIT 与交付 SHA 一致）",
                "PASS（自动阶段保持 PACKAGE_CANDIDATE）",
                "PASS（候选 SHA256SUMS 完整且校验通过）",
                "PASS（两次打包 ZIP 字节级一致）",
                "PASS（manifest-only verifier 通过）",
                "PASS（clean-room 十项 CTest 与 consumer 通过）",
                "PASS（四方批准后已运行独立验收记录复验）",
                "PASS（finalizer 输入与原子发布条件已核对）",
                "PASS（Markdown 为权威报告，不提供 PDF）",
                "已知限制：仅内部评估，不含商业求解器验证",
                "无未解决 blocker；全部强制门槛通过",
                "按交付 ID、源码 SHA 与 ZIP SHA-256 撤回并从新 RUN_ROOT 重跑",
                "PASS",
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
                "不提供",
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
