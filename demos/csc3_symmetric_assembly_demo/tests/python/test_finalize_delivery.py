#!/usr/bin/env python3
"""Tests for the post-approval CSC3 delivery finalizer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "finalize_delivery.py"
SOURCE_SHA = "b" * 40
DELIVERY_ID = "controlled-linux-intel-001"


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
        self.record = self.run_root / "acceptance-record.json"
        self.record_data = {
            "schema_version": "csc3-demo-formal-acceptance-v1",
            "delivery_id": DELIVERY_ID,
            "source_commit": SOURCE_SHA,
            "distribution": "INTERNAL EVALUATION ONLY",
            "artifacts": {
                "delivery_zip": {
                    "path": self.archive.name,
                    "size_bytes": self.archive.stat().st_size,
                    "sha256": self.archive_sha,
                }
            },
            "status": "PASS",
        }
        self.record.write_text(
            json.dumps(self.record_data, sort_keys=True) + "\n", encoding="utf-8"
        )
        shared = f"{DELIVERY_ID}\n{SOURCE_SHA}\n{self.archive.name}\n{self.archive_sha}\n"
        self.checklist = self.run_root / "completed-checklist.md"
        self.checklist.write_text(
            "# Completed checklist\n"
            "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS\n"
            "- [x] all mandatory checks completed\n"
            + shared,
            encoding="utf-8",
        )
        self.note = self.run_root / "completed-delivery-note.md"
        self.note.write_text(
            "# Completed delivery note\n"
            "CSC3_DELIVERY_NOTE_STATUS=PASS\n"
            + shared,
            encoding="utf-8",
        )

    def finalize(self, out_name: str = "final-delivery") -> tuple[dict[str, object], Path]:
        output = self.root / out_name
        with mock.patch.object(
            self.module,
            "validate_acceptance_record",
            return_value=self.record_data,
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
        }
        self.assertEqual(expected_files, {path.name for path in output.iterdir()})

        finalization = json.loads((output / "FINALIZATION.json").read_text(encoding="utf-8"))
        self.assertEqual("csc3-demo-finalization-v1", finalization["schema"])
        self.assertEqual("PASS", finalization["status"])
        self.assertEqual(SOURCE_SHA, finalization["source_commit"])
        self.assertNotIn("created", finalization)

        checksum_lines = (output / "FINAL_SHA256SUMS").read_text(
            encoding="utf-8"
        ).splitlines()
        checksum_names = [line.split("  ", 1)[1] for line in checksum_lines]
        self.assertEqual(sorted(checksum_names), checksum_names)
        self.assertNotIn("FINAL_SHA256SUMS", checksum_names)
        self.assertEqual(expected_files - {"FINAL_SHA256SUMS"}, set(checksum_names))
        for line in checksum_lines:
            digest, name = line.split("  ", 1)
            self.assertEqual(
                digest, hashlib.sha256((output / name).read_bytes()).hexdigest()
            )

    def test_same_inputs_produce_identical_final_files(self) -> None:
        _, first = self.finalize("first")
        _, second = self.finalize("second")
        self.assertEqual(
            {path.name: path.read_bytes() for path in first.iterdir()},
            {path.name: path.read_bytes() for path in second.iterdir()},
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
                    "validate_acceptance_record",
                    return_value=self.record_data,
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

    def test_validator_failure_and_existing_output_fail_before_write(self) -> None:
        rejected = self.root / "validator-rejected"
        with mock.patch.object(
            self.module,
            "validate_acceptance_record",
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
            "validate_acceptance_record",
            return_value=self.record_data,
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
            "validate_acceptance_record",
            return_value=self.record_data,
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
            "validate_acceptance_record",
            return_value=self.record_data,
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
