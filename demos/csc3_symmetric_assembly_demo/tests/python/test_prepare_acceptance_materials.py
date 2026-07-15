#!/usr/bin/env python3
"""Contract tests for freezing candidate facts and drafting approval inputs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator


DEMO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
CORE_SCRIPT = DEMO_ROOT / "scripts" / "acceptance_core.py"
PREPARER_SCRIPT = DEMO_ROOT / "scripts" / "prepare_acceptance_materials.py"
MACHINE_SCHEMA = DEMO_ROOT / "packaging" / "ACCEPTANCE_MACHINE_FACTS.schema.json"
DECISION_SCHEMA = DEMO_ROOT / "packaging" / "ACCEPTANCE_DECISION.schema.json"
FROZEN_AT_UTC = "2026-07-13T11:00:01Z"
PLACEHOLDER = "REQUIRED BEFORE DELIVERY"

if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from acceptance_test_fixture import (  # noqa: E402
    CHECKSUM_ONLY_CONTENT,
    CHECKSUM_ONLY_RELATIVE,
    AcceptanceCandidateFixture,
    build_acceptance_candidate_fixture,
)


def load_script(path: Path, module_name: str):
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def replace_checksum(run_root: Path, relative: str) -> None:
    target = run_root.joinpath(*Path(relative).parts)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum_path = run_root / "SHA256SUMS"
    lines = checksum_path.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if line.endswith(f"  {relative}\n")
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one checksum line for {relative!r}")
    lines[matches[0]] = f"{digest}  {relative}\n"
    checksum_path.write_text("".join(lines), encoding="utf-8", newline="\n")


class AcceptanceDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = load_script(CORE_SCRIPT, "csc3_acceptance_core")
        cls.preparer = load_script(PREPARER_SCRIPT, "csc3_acceptance_preparer_contract")
        cls.base_temporary = tempfile.TemporaryDirectory(
            prefix="csc3-acceptance-draft-base-"
        )
        cls.base_fixture = build_acceptance_candidate_fixture(
            Path(cls.base_temporary.name)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.base_temporary.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="csc3-acceptance-draft-test-"
        )
        self.root = Path(self.temporary.name)
        self.fixture = self.copy_candidate("candidate")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def copy_candidate(self, name: str) -> AcceptanceCandidateFixture:
        run_root = self.root / name / "run-root"
        shutil.copytree(self.base_fixture.run_root, run_root, symlinks=True)
        archive_relative = self.base_fixture.archive_path.relative_to(
            self.base_fixture.run_root
        )
        return AcceptanceCandidateFixture(
            run_root=run_root,
            archive_path=run_root / archive_relative,
            source_commit=self.base_fixture.source_commit,
        )

    def draft(
        self,
        fixture: AcceptanceCandidateFixture | None = None,
        *,
        output_name: str = "draft",
        frozen_at_utc: str = FROZEN_AT_UTC,
    ) -> tuple[dict[str, object], Path, Path]:
        candidate = fixture or self.fixture
        output = self.root / output_name
        output.mkdir(parents=True, exist_ok=True)
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        result = self.preparer.draft_acceptance_inputs(
            candidate.run_root,
            candidate.archive_path,
            facts_path,
            decision_path,
            frozen_at_utc=frozen_at_utc,
        )
        return result, facts_path, decision_path

    def test_draft_derives_deterministic_machine_facts_from_candidate(self) -> None:
        result_a, facts_a_path, decision_a_path = self.draft(output_name="draft-a")
        result_b, facts_b_path, decision_b_path = self.draft(output_name="draft-b")

        facts_a_content = facts_a_path.read_bytes()
        decision_a_content = decision_a_path.read_bytes()
        self.assertEqual(facts_a_content, facts_b_path.read_bytes())
        self.assertEqual(decision_a_content, decision_b_path.read_bytes())
        facts = json.loads(facts_a_content)
        decision = json.loads(decision_a_content)
        self.assertEqual(facts_a_content, canonical_json(facts))
        self.assertEqual(decision_a_content, canonical_json(decision))
        self.assertEqual(
            self.core.canonical_json_bytes(facts),
            facts_a_content,
        )
        with self.assertRaises(ValueError):
            self.core.canonical_json_bytes({"invalid": math.nan})

        machine_schema = json.loads(MACHINE_SCHEMA.read_text(encoding="utf-8"))
        decision_schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(machine_schema)
        Draft202012Validator.check_schema(decision_schema)
        self.assertEqual(
            list(Draft202012Validator(machine_schema).iter_errors(facts)),
            [],
        )
        self.assertEqual(
            list(Draft202012Validator(decision_schema).iter_errors(decision)),
            [],
        )

        self.assertEqual(result_a["status"], "APPROVAL_INPUT_READY")
        self.assertEqual(facts["schema_version"], "csc3-demo-acceptance-machine-facts-v1")
        self.assertEqual(facts["workflow_state"], "APPROVAL_INPUT_READY")
        self.assertEqual(facts["source_commit"], self.fixture.source_commit)
        self.assertFalse(facts["source"]["source_dirty_at_start"])
        self.assertEqual(facts["source"]["demo_version"], "0.2.0")
        self.assertEqual(facts["input"]["case"], "windhub")
        self.assertTrue(facts["input"]["matches_head_lfs"])
        self.assertEqual(facts["execution"]["warmup_count"], 2)
        self.assertEqual(facts["execution"]["repeat_count"], 7)
        self.assertEqual(facts["execution"]["amortization_count"], 1)
        self.assertEqual(facts["ctest"]["test_count"], 10)
        self.assertEqual(facts["ctest"]["failed_count"], 0)
        self.assertEqual(facts["ctest"]["skipped_count"], 0)
        self.assertEqual(facts["ctest"]["disabled_count"], 0)
        self.assertEqual(facts["ctest"]["not_run_count"], 0)
        self.assertEqual(facts["correctness"]["status"], "PASS")
        self.assertGreaterEqual(facts["performance"]["numeric_speedup"], 1.5)
        self.assertGreater(facts["performance"]["symbolic_speedup"], 1.0)
        self.assertLessEqual(
            facts["performance"]["numeric_coefficient_of_variation"], 0.05
        )
        self.assertLessEqual(
            facts["performance"]["symbolic_coefficient_of_variation"], 0.05
        )
        self.assertEqual(facts["candidate"]["status"], "PACKAGE_CANDIDATE")
        self.assertEqual(
            facts["candidate"]["completed_at_utc"], "2026-07-13T11:00:00Z"
        )
        self.assertEqual(facts["candidate"]["frozen_at_utc"], FROZEN_AT_UTC)
        self.assertEqual(facts["verifications"]["clean_room"]["status"], "PASS")
        self.assertTrue(
            facts["verifications"]["clean_room"]["clean_room_executed"]
        )
        self.assertNotIn("operator", facts)
        self.assertNotIn("approvals", facts)

        facts_sha = hashlib.sha256(facts_a_content).hexdigest()
        self.assertEqual(decision["schema_version"], "csc3-demo-acceptance-decision-v1")
        self.assertEqual(
            decision["machine_facts"],
            {"path": facts_a_path.name, "sha256": facts_sha},
        )
        self.assertEqual(decision["delivery_id"], PLACEHOLDER)
        self.assertEqual(decision["issue_url"], PLACEHOLDER)
        self.assertEqual(decision["decision_status"], "PENDING")
        for role in (
            "operator",
            "technical_reviewer",
            "delivery_approver",
            "recipient_acknowledgement",
        ):
            approval = decision["approvals"][role]
            self.assertEqual(approval["acknowledgement"], "PENDING")
            self.assertEqual(approval["source_commit"], self.fixture.source_commit)
            self.assertEqual(
                approval["archive_filename"], self.fixture.archive_path.name
            )
            self.assertEqual(
                approval["archive_sha256"],
                facts["artifacts"]["delivery_zip"]["sha256"],
            )
            self.assertEqual(approval["candidate_status"], "PACKAGE_CANDIDATE")
            self.assertEqual(approval["clean_room_status"], "PASS")
            self.assertEqual(approval["machine_facts_sha256"], facts_sha)

    def test_draft_keeps_checksum_only_bytes_in_snapshot(self) -> None:
        with self.core.validated_candidate_snapshot(
            self.fixture.run_root,
            self.fixture.archive_path,
            frozen_at_utc=FROZEN_AT_UTC,
        ) as snapshot:
            self.assertEqual(
                snapshot.relative_contents[CHECKSUM_ONLY_RELATIVE],
                CHECKSUM_ONLY_CONTENT,
            )
            self.assertNotIn(CHECKSUM_ONLY_RELATIVE, snapshot.artifact_contents)
            self.assertIn(
                CHECKSUM_ONLY_RELATIVE,
                {
                    binding["path"]
                    for binding in snapshot.machine_facts["candidate_closure"]
                },
            )
            self.fixture.run_root.joinpath(
                *Path(CHECKSUM_ONLY_RELATIVE).parts
            ).write_bytes(b"source changed after snapshot\n")
            self.assertEqual(
                snapshot.relative_contents[CHECKSUM_ONLY_RELATIVE],
                CHECKSUM_ONLY_CONTENT,
            )
            self.assertEqual(
                snapshot.machine_facts_content,
                self.core.canonical_json_bytes(snapshot.machine_facts),
            )

    def test_draft_rejects_non_candidate_outcome(self) -> None:
        outcome_path = self.fixture.run_root / "acceptance-outcome.json"
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        outcome["status"] = "FAIL"
        outcome["reason"] = "formal gate failed"
        outcome_path.write_bytes(canonical_json(outcome))
        replace_checksum(self.fixture.run_root, "acceptance-outcome.json")

        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"acceptance-outcome\.json.*PACKAGE_CANDIDATE",
        ):
            self.draft()

    def test_draft_rejects_tampered_checksum_member(self) -> None:
        self.fixture.run_root.joinpath(
            *Path(CHECKSUM_ONLY_RELATIVE).parts
        ).write_bytes(b"tampered bytes\n")
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"SHA256SUMS.*checksum-only\.txt.*SHA-256 mismatch",
        ):
            self.draft()

    def test_draft_rejects_one_archive_path_claimed_as_both_packages(self) -> None:
        deterministic_path = self.fixture.run_root / "deterministic-package.txt"
        lines = deterministic_path.read_text(encoding="utf-8").splitlines()
        zip_a = next(
            line.removeprefix("zip_a=")
            for line in lines
            if line.startswith("zip_a=")
        )
        deterministic_path.write_text(
            "\n".join(
                f"zip_b={zip_a}" if line.startswith("zip_b=") else line
                for line in lines
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        replace_checksum(self.fixture.run_root, "deterministic-package.txt")

        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"zip_b.*dist-b",
        ):
            self.draft()

    def test_draft_rejects_existing_output_without_partial_publication(self) -> None:
        output = self.root / "existing-machine-facts"
        output.mkdir()
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        facts_path.write_bytes(b"existing facts\n")
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"already exists.*acceptance-machine-facts\.json",
        ):
            self.preparer.draft_acceptance_inputs(
                self.fixture.run_root,
                self.fixture.archive_path,
                facts_path,
                decision_path,
                frozen_at_utc=FROZEN_AT_UTC,
            )
        self.assertEqual(facts_path.read_bytes(), b"existing facts\n")
        self.assertFalse(decision_path.exists())

        second_output = self.root / "existing-decision"
        second_output.mkdir()
        second_facts = second_output / "acceptance-machine-facts.json"
        second_decision = second_output / "acceptance-decision.json"
        second_decision.write_bytes(b"existing decision\n")
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"already exists.*acceptance-decision\.json",
        ):
            self.preparer.draft_acceptance_inputs(
                self.fixture.run_root,
                self.fixture.archive_path,
                second_facts,
                second_decision,
                frozen_at_utc=FROZEN_AT_UTC,
            )
        self.assertFalse(second_facts.exists())
        self.assertEqual(second_decision.read_bytes(), b"existing decision\n")
        self.assertEqual(
            [path for path in self.root.rglob("*") if ".staging-" in path.name],
            [],
        )

    def test_draft_rolls_back_first_output_if_second_publish_races(self) -> None:
        output = self.root / "publish-race"
        output.mkdir()
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        real_link = os.link

        def raced_link(source: Path, destination: Path) -> None:
            if Path(destination) == decision_path:
                decision_path.write_bytes(b"competing decision\n")
                raise FileExistsError(decision_path)
            real_link(source, destination)

        with mock.patch.object(self.preparer.os, "link", side_effect=raced_link):
            with self.assertRaisesRegex(
                self.core.AcceptanceCandidateError,
                r"appeared during publication.*acceptance-decision\.json",
            ):
                self.preparer.draft_acceptance_inputs(
                    self.fixture.run_root,
                    self.fixture.archive_path,
                    facts_path,
                    decision_path,
                    frozen_at_utc=FROZEN_AT_UTC,
                )
        self.assertFalse(facts_path.exists())
        self.assertEqual(decision_path.read_bytes(), b"competing decision\n")

    def test_draft_rejects_symlink_and_path_escape(self) -> None:
        symlink_fixture = self.copy_candidate("symlink-candidate")
        symlink_target = self.root / "outside-checksum-only.txt"
        symlink_target.write_bytes(CHECKSUM_ONLY_CONTENT)
        checksum_member = symlink_fixture.run_root.joinpath(
            *Path(CHECKSUM_ONLY_RELATIVE).parts
        )
        checksum_member.unlink()
        os.symlink(symlink_target, checksum_member)
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"checksum-only\.txt.*symbolic link",
        ):
            self.draft(symlink_fixture, output_name="symlink-output")

        escape_fixture = self.copy_candidate("escape-candidate")
        checksum_path = escape_fixture.run_root / "SHA256SUMS"
        checksum_text = checksum_path.read_text(encoding="utf-8")
        checksum_path.write_text(
            checksum_text.replace(CHECKSUM_ONLY_RELATIVE, "../outside.txt"),
            encoding="utf-8",
            newline="\n",
        )
        (escape_fixture.run_root.parent / "outside.txt").write_bytes(
            CHECKSUM_ONLY_CONTENT
        )
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"SHA256SUMS.*unsafe.*\.\./outside\.txt",
        ):
            self.draft(escape_fixture, output_name="escape-output")

    def test_draft_requires_freeze_strictly_after_candidate_completion(self) -> None:
        for frozen_at_utc in (
            "2026-07-13T10:59:59Z",
            "2026-07-13T11:00:00Z",
        ):
            with self.subTest(frozen_at_utc=frozen_at_utc):
                with self.assertRaisesRegex(
                    self.core.AcceptanceCandidateError,
                    r"frozen_at_utc.*strictly later",
                ):
                    self.draft(
                        output_name="invalid-freeze-" + str(abs(hash(frozen_at_utc))),
                        frozen_at_utc=frozen_at_utc,
                    )
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"frozen_at_utc.*canonical UTC",
        ):
            self.draft(
                output_name="invalid-freeze-format",
                frozen_at_utc="2026-07-13T11:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()
