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
        runbook_sha = hashlib.sha256(self.runbook_log.read_bytes()).hexdigest()
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
                "runbook_log": {
                    "path": self.runbook_log.name,
                    "size_bytes": self.runbook_log.stat().st_size,
                    "sha256": runbook_sha,
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
        shared = f"{DELIVERY_ID}\n{SOURCE_SHA}\n{self.archive.name}\n{self.archive_sha}\n"
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
            .replace("REQUIRED BEFORE DELIVERY", "COMPLETED")
            .replace("- [x] 交付 ID：`COMPLETED`", f"- [x] 交付 ID：`{DELIVERY_ID}`")
            .replace("- [x] 完整源码 SHA：`COMPLETED`", f"- [x] 完整源码 SHA：`{SOURCE_SHA}`")
            .replace(
                "- [x] 候选源码 ZIP 文件名及 SHA-256：`COMPLETED`",
                f"- [x] 候选源码 ZIP 文件名及 SHA-256：`{self.archive.name}` `{self.archive_sha}`",
            )
            .replace(
                "- [x] Issue #44 URL：`COMPLETED`",
                f"- [x] Issue #44 URL：`{ISSUE_URL}`",
            )
            .replace(
                "- [x] 接收组织及部门：`COMPLETED`",
                f"- [x] 接收组织及部门：`{RECIPIENT_ORGANIZATION}` / `{RECIPIENT_DEPARTMENT}`",
            )
            .replace(
                "- [x] 指定接收人身份引用：`COMPLETED`",
                f"- [x] 指定接收人身份引用：`{RECIPIENT_IDENTITY}`",
            )
            .replace(
                "- [x] 操作员：身份引用 `COMPLETED`；UTC `COMPLETED`；\n"
                "  记录号 `COMPLETED`",
                f"- [x] 操作员：身份引用 `{OPERATOR_IDENTITY}`；UTC "
                f"`{ACKNOWLEDGED_AT_UTC}`；\n  记录号 "
                f"`approval:{OPERATOR_IDENTITY}:001`",
            )
            .replace(
                "- [x] 技术复核人：身份引用 `COMPLETED`；UTC\n"
                "  `COMPLETED`；记录号 `COMPLETED`",
                f"- [x] 技术复核人：身份引用 `{REVIEWER_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{REVIEWER_IDENTITY}:001`",
            )
            .replace(
                "- [x] 交付批准人：身份引用 `COMPLETED`；UTC\n"
                "  `COMPLETED`；记录号 `COMPLETED`",
                f"- [x] 交付批准人：身份引用 `{APPROVER_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{APPROVER_IDENTITY}:001`",
            )
            .replace(
                "- [x] 接收方确认：身份引用 `COMPLETED`；UTC\n"
                "  `COMPLETED`；记录号 `COMPLETED`",
                f"- [x] 接收方确认：身份引用 `{RECIPIENT_IDENTITY}`；UTC\n"
                f"  `{ACKNOWLEDGED_AT_UTC}`；记录号 "
                f"`approval:{RECIPIENT_IDENTITY}:001`",
            )
            .replace("最终状态：`COMPLETED`", "最终状态：`PASS`")
        )
        self.checklist.write_text(completed_checklist + "\n" + shared, encoding="utf-8")
        self.note = self.run_root / "completed-delivery-note.md"
        note_template = (
            DEMO_ROOT / "packaging" / "DELIVERY_NOTE_TEMPLATE.zh-CN.md"
        ).read_text(encoding="utf-8")
        completed_note = (
            note_template.replace(
                "CSC3_DELIVERY_NOTE_STATUS=PENDING",
                "CSC3_DELIVERY_NOTE_STATUS=PASS",
            )
            .replace("REQUIRED BEFORE DELIVERY", "COMPLETED")
            .replace(
                "| 交付 ID | **COMPLETED** |",
                f"| 交付 ID | **{DELIVERY_ID}** |",
            )
            .replace(
                "| 完整源码 SHA | **COMPLETED** |",
                f"| 完整源码 SHA | **{SOURCE_SHA}** |",
            )
            .replace(
                "| 正式源码 ZIP | **COMPLETED** | **COMPLETED** |",
                f"| 正式源码 ZIP | **{self.archive.name}** | **{self.archive_sha}** |",
            )
            .replace(
                "| Issue #44 URL | **COMPLETED** |",
                f"| Issue #44 URL | **{ISSUE_URL}** |",
            )
            .replace(
                "| 发送组织/部门 | **COMPLETED** |",
                f"| 发送组织/部门 | **{OPERATOR_ORGANIZATION} / {OPERATOR_DEPARTMENT}** |",
            )
            .replace(
                "| 接收组织/部门 | **COMPLETED** |",
                f"| 接收组织/部门 | **{RECIPIENT_ORGANIZATION} / {RECIPIENT_DEPARTMENT}** |",
            )
            .replace(
                "| 指定接收人身份引用 | **COMPLETED** |",
                f"| 指定接收人身份引用 | **{RECIPIENT_IDENTITY}** |",
            )
            .replace(
                "| 操作员 | **COMPLETED** | **COMPLETED** | **COMPLETED** | **COMPLETED** |",
                f"| 操作员 | **{OPERATOR_IDENTITY}** | **{ACKNOWLEDGED_AT_UTC}** | "
                f"**approval:{OPERATOR_IDENTITY}:001** | **ACKNOWLEDGED** |",
            )
            .replace(
                "| 技术复核人 | **COMPLETED** | **COMPLETED** | **COMPLETED** | **COMPLETED** |",
                f"| 技术复核人 | **{REVIEWER_IDENTITY}** | **{ACKNOWLEDGED_AT_UTC}** | "
                f"**approval:{REVIEWER_IDENTITY}:001** | **ACKNOWLEDGED** |",
            )
            .replace(
                "| 发送方批准/交付批准人 | **COMPLETED** | **COMPLETED** | **COMPLETED** | **COMPLETED** |",
                f"| 发送方批准/交付批准人 | **{APPROVER_IDENTITY}** | "
                f"**{ACKNOWLEDGED_AT_UTC}** | **approval:{APPROVER_IDENTITY}:001** | "
                "**ACKNOWLEDGED** |",
            )
            .replace(
                "| 接收方确认 | **COMPLETED** | **COMPLETED** | **COMPLETED** | **COMPLETED** |",
                f"| 接收方确认 | **{RECIPIENT_IDENTITY}** | "
                f"**{ACKNOWLEDGED_AT_UTC}** | **approval:{RECIPIENT_IDENTITY}:001** | "
                "**ACKNOWLEDGED** |",
            )
            .replace(
                "正式验收状态（只能为 `PASS`）：**COMPLETED**",
                "正式验收状态（只能为 `PASS`）：**PASS**",
            )
        )
        self.note.write_text(completed_note + "\n" + shared, encoding="utf-8")

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
        self.assertEqual(
            (expected_files - {"FINAL_SHA256SUMS", "ACCEPTANCE_EVIDENCE"})
            | {"ACCEPTANCE_EVIDENCE/runbook_log.log"},
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
                artifact_contents={
                    "delivery_zip": archive_content,
                    "runbook_log": runbook_content,
                },
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
