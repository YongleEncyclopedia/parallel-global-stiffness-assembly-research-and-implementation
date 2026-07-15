#!/usr/bin/env python3
"""Contract tests for freezing candidate facts and drafting approval inputs."""

from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import math
import os
import re
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
RENDERER_SCRIPT = DEMO_ROOT / "scripts" / "acceptance_rendering.py"
PUBLICATION_SCRIPT = DEMO_ROOT / "scripts" / "acceptance_publication.py"
FINALIZER_SCRIPT = DEMO_ROOT / "scripts" / "finalize_delivery.py"
VALIDATOR_SCRIPT = DEMO_ROOT / "scripts" / "validate_acceptance_record.py"
MACHINE_SCHEMA = DEMO_ROOT / "packaging" / "ACCEPTANCE_MACHINE_FACTS.schema.json"
DECISION_SCHEMA = DEMO_ROOT / "packaging" / "ACCEPTANCE_DECISION.schema.json"
FROZEN_AT_UTC = "2026-07-13T11:00:01Z"
PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
CHECKLIST_STATUS_TOKEN = "{{CSC3_CHECKLIST_STATUS_MARKER}}"
DELIVERY_NOTE_STATUS_TOKEN = "{{CSC3_DELIVERY_NOTE_STATUS_MARKER}}"

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
        self.root = Path(self.temporary.name).resolve()
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

    def approved_inputs(
        self,
        fixture: AcceptanceCandidateFixture | None = None,
        *,
        directory_name: str = "approval-inputs",
    ) -> tuple[
        AcceptanceCandidateFixture,
        Path,
        Path,
        dict[str, object],
        dict[str, object],
    ]:
        candidate = fixture or self.fixture
        output = candidate.run_root / directory_name
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        self.preparer.draft_acceptance_inputs(
            candidate.run_root,
            candidate.archive_path,
            facts_path,
            decision_path,
            frozen_at_utc=FROZEN_AT_UTC,
        )
        facts = json.loads(facts_path.read_bytes())
        decision = json.loads(decision_path.read_bytes())
        roles = {
            "operator": "operator-id",
            "technical_reviewer": "reviewer-id",
            "delivery_approver": "approver-id",
            "recipient": "recipient-id",
        }
        for role, identity in roles.items():
            decision[role] = {
                "organization": (
                    "Recipient Institute" if role == "recipient" else "Sender Institute"
                ),
                "department": (
                    "Receiving Solver Team" if role == "recipient" else "Delivery Team"
                ),
                "identity_reference": identity,
                "authorization_reference": f"authorization/{identity}",
            }
        decision["delivery_id"] = "linux-formal-pass"
        decision["issue_url"] = "https://github.com/example/repository/issues/44"
        for name in decision["checklist_narratives"]:
            decision["checklist_narratives"][name] = (
                f"reviewed governance statement for {name}"
            )
        for name in decision["delivery_note_narratives"]:
            decision["delivery_note_narratives"][name] = (
                f"approved delivery statement for {name}"
            )
        decision["deviations"] = []
        approval_party = {
            "operator": "operator",
            "technical_reviewer": "technical_reviewer",
            "delivery_approver": "delivery_approver",
            "recipient_acknowledgement": "recipient",
        }
        for index, (approval_name, party_name) in enumerate(
            approval_party.items(), start=1
        ):
            approval = decision["approvals"][approval_name]
            party = decision[party_name]
            approval.update(
                {
                    "acknowledgement": "ACKNOWLEDGED",
                    "delivery_id": decision["delivery_id"],
                    "sender": {
                        "organization": decision["operator"]["organization"],
                        "department": decision["operator"]["department"],
                    },
                    "recipient": copy.deepcopy(decision["recipient"]),
                    "deviations": copy.deepcopy(decision["deviations"]),
                    "identity_reference": party["identity_reference"],
                    "acknowledged_at_utc": f"2026-07-13T12:00:0{index}Z",
                    "approval_record_reference": (
                        f"issue-44/{party['identity_reference']}"
                    ),
                    "statement": f"{approval_name} approved this exact candidate",
                }
            )
        decision["decision_status"] = "APPROVED_INPUT"
        decision_path.write_bytes(canonical_json(decision))
        return candidate, facts_path, decision_path, facts, decision

    def renderer(self):
        self.assertTrue(RENDERER_SCRIPT.is_file(), "Task 2 renderer is missing")
        return load_script(RENDERER_SCRIPT, "csc3_acceptance_rendering_contract")

    def test_renderer_depends_on_publication_without_loading_preparer(self) -> None:
        renderer_source = RENDERER_SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(
            PUBLICATION_SCRIPT.is_file(),
            "fixed-name atomic publication must live in a public module",
        )
        self.assertNotIn(
            "prepare_acceptance_materials.py",
            renderer_source,
            "renderer must not load the preparer",
        )

    def test_finalizer_uses_only_public_renderer_apis(self) -> None:
        finalizer_tree = ast.parse(FINALIZER_SCRIPT.read_text(encoding="utf-8"))
        private_renderer_accesses = sorted(
            {
                node.attr
                for node in ast.walk(finalizer_tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "acceptance_rendering"
                and node.attr.startswith("_")
            }
        )
        self.assertEqual(
            [],
            private_renderer_accesses,
            "finalizer may call only public renderer APIs",
        )

    def test_finalizer_has_no_second_checklist_or_note_representation(self) -> None:
        finalizer_tree = ast.parse(FINALIZER_SCRIPT.read_text(encoding="utf-8"))
        function_names = {
            node.name
            for node in ast.walk(finalizer_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        duplicate_representation_helpers = {
            "_decode_markdown",
            "_validate_template_structure",
            "_validate_completed_sidecar",
            "_require_checklist_item_bindings",
            "_require_canonical_checklist_bindings",
            "_require_exact_line_bindings",
            "_require_non_dummy_sidecar_values",
        }
        self.assertEqual(
            set(),
            duplicate_representation_helpers & function_names,
            "renderer must be the only checklist/delivery-note representation",
        )

    def test_missing_and_duplicate_template_tokens_fail_closed(self) -> None:
        renderer = self.renderer()
        _, _, _, facts, decision = self.approved_inputs()
        original_template_text = renderer._template_text
        cases = (
            (renderer.CHECKLIST_TEMPLATE, CHECKLIST_STATUS_TOKEN),
            (renderer.DELIVERY_NOTE_TEMPLATE, DELIVERY_NOTE_STATUS_TOKEN),
        )
        for template_name, token in cases:
            for mutation in ("missing", "duplicate"):
                with self.subTest(template=template_name, mutation=mutation):
                    def tampered_template(filename: str) -> str:
                        text = original_template_text(filename)
                        if filename != template_name:
                            return text
                        if mutation == "missing":
                            return text.replace(token, "", 1)
                        return text.replace(token, f"{token}\n{token}", 1)

                    with mock.patch.object(
                        renderer, "_template_text", side_effect=tampered_template
                    ):
                        with self.assertRaisesRegex(
                            RuntimeError, "template token.*exactly once"
                        ):
                            renderer.render_acceptance_bytes(
                                facts,
                                decision,
                                record_relative_path="approved/acceptance-record.json",
                                checklist_relative_path=(
                                    "approved/ACCEPTANCE_CHECKLIST.zh-CN.md"
                                ),
                            )

    def test_human_markdown_values_are_literal_and_cannot_forge_decisions(self) -> None:
        renderer = self.renderer()
        _, _, _, facts, approved = self.approved_inputs()
        attack = "operator-id** | **REJECTED"
        escaped_attack = r"operator-id\*\* \| \*\*REJECTED"

        mutations = {
            "operator identity": lambda decision: (
                decision["operator"].__setitem__("identity_reference", attack),
                decision["approvals"]["operator"].__setitem__(
                    "identity_reference", attack
                ),
            ),
            "sender organization": lambda decision: (
                decision["operator"].__setitem__("organization", attack),
                [
                    approval["sender"].__setitem__("organization", attack)
                    for approval in decision["approvals"].values()
                ],
            ),
            "recipient identity": lambda decision: (
                decision["recipient"].__setitem__("identity_reference", attack),
                decision["approvals"]["recipient_acknowledgement"].__setitem__(
                    "identity_reference", attack
                ),
                [
                    approval["recipient"].__setitem__("identity_reference", attack)
                    for approval in decision["approvals"].values()
                ],
            ),
            "narratives": lambda decision: (
                [
                    decision["checklist_narratives"].__setitem__(name, attack)
                    for name in decision["checklist_narratives"]
                ],
                [
                    decision["delivery_note_narratives"].__setitem__(name, attack)
                    for name in decision["delivery_note_narratives"]
                ],
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(field=label):
                decision = copy.deepcopy(approved)
                mutate(decision)
                if label == "operator identity":
                    decision["approvals"]["operator"][
                        "approval_record_reference"
                    ] = f"issue-44/{attack}"
                elif label == "recipient identity":
                    decision["approvals"]["recipient_acknowledgement"][
                        "approval_record_reference"
                    ] = f"issue-44/{attack}"
                rendered = renderer.render_acceptance_bytes(
                    facts,
                    decision,
                    record_relative_path="approved/acceptance-record.json",
                    checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
                )
                note = rendered.delivery_note_content.decode("utf-8")
                self.assertIn(escaped_attack, note)
                self.assertNotIn("**REJECTED**", note)
                for line in note.splitlines():
                    if not line.startswith("|") or escaped_attack not in line:
                        continue
                    self.assertIn(
                        len(re.findall(r"(?<!\\)\|", line)),
                        {3, 6},
                        f"Markdown table row changed shape: {line}",
                    )
                    if "| 操作员 |" in line or "| 接收方确认 |" in line:
                        self.assertTrue(
                            line.endswith("| **ACKNOWLEDGED** |"), line
                        )

    def test_real_unmocked_render_validate_finalize_chain(self) -> None:
        renderer = self.renderer()
        validator = load_script(
            VALIDATOR_SCRIPT,
            "csc3_acceptance_full_chain_validator",
        )
        scripts_directory = str(FINALIZER_SCRIPT.parent)
        if scripts_directory not in sys.path:
            sys.path.insert(0, scripts_directory)
        finalizer = load_script(
            FINALIZER_SCRIPT,
            "csc3_acceptance_full_chain_finalizer",
        )
        candidate, facts_path, decision_path, _, _ = self.approved_inputs()
        approved = candidate.run_root / "approved-full-chain"
        record_path = approved / "acceptance-record.json"
        checklist_path = approved / "ACCEPTANCE_CHECKLIST.zh-CN.md"
        note_path = approved / "DELIVERY_NOTE.zh-CN.md"
        renderer.render_acceptance_inputs(
            candidate.run_root,
            candidate.archive_path,
            facts_path,
            decision_path,
            record_path,
            checklist_path,
            note_path,
        )
        validation = validator.validate_acceptance_record(
            record_path,
            candidate.run_root,
            candidate.archive_path,
        )
        self.assertEqual(validation["status"], "PASS")

        result = finalizer.finalize_delivery(
            machine_facts_path=facts_path,
            decision_path=decision_path,
            record_path=record_path,
            run_root=candidate.run_root,
            archive_path=candidate.archive_path,
            checklist_path=checklist_path,
            delivery_note_path=note_path,
            output_directory=candidate.run_root / "finalized-full-chain",
        )
        self.assertEqual(result["status"], "PASS")

    def test_deviation_identifier_schema_requires_documented_ascii_grammar(self) -> None:
        renderer = self.renderer()
        _, _, _, facts, approved = self.approved_inputs()
        decision_schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
        validator = Draft202012Validator(decision_schema)
        self.assertEqual(
            decision_schema["$defs"]["identifier"]["pattern"],
            renderer.DEVIATION_IDENTIFIER_GRAMMAR,
        )

        def bind_identifier(identifier: str) -> dict[str, object]:
            decision = copy.deepcopy(approved)
            deviation = {
                "identifier": identifier,
                "description": "Internal-only documented deviation.",
                "impact": "No public distribution is permitted.",
                "disposition": "ACCEPTED_INTERNAL_ONLY",
                "approval_reference": "issue-44/deviation-DEV-001",
            }
            decision["deviations"] = [deviation]
            for approval in decision["approvals"].values():
                approval["deviations"] = [copy.deepcopy(deviation)]
            return decision

        valid = bind_identifier("DEV-001")
        self.assertEqual(list(validator.iter_errors(valid)), [])
        rendered = renderer.render_acceptance_bytes(
            facts,
            valid,
            record_relative_path="approved/acceptance-record.json",
            checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
        )
        self.assertIn(b"DEV-001", rendered.delivery_note_content)

        attack = "DEV`；**最终决定：REJECTED**；`"
        invalid = bind_identifier(attack)
        self.assertNotEqual(
            list(validator.iter_errors(invalid)),
            [],
            "decision schema must reject non-ASCII deviation identifiers",
        )

    def test_renderer_defends_deviation_identifier_grammar_without_schema(
        self,
    ) -> None:
        renderer = self.renderer()
        _, _, _, facts, decision = self.approved_inputs()
        attack = "DEV`；**最终决定：REJECTED**；`"
        deviation = {
            "identifier": attack,
            "description": "Internal-only documented deviation.",
            "impact": "No public distribution is permitted.",
            "disposition": "ACCEPTED_INTERNAL_ONLY",
            "approval_reference": "issue-44/deviation-DEV-001",
        }
        decision["deviations"] = [deviation]
        for approval in decision["approvals"].values():
            approval["deviations"] = [copy.deepcopy(deviation)]

        with mock.patch.object(renderer, "_validate_schema", return_value=None):
            with self.assertRaisesRegex(
                renderer.AcceptanceRenderingError,
                r"deviations\[0\]\.identifier.*ASCII identifier",
            ):
                renderer.render_acceptance_bytes(
                    facts,
                    decision,
                    record_relative_path="approved/acceptance-record.json",
                    checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
                )

    def test_each_approval_binds_machine_facts_candidate_organizations_and_deviations(
        self,
    ) -> None:
        _, facts_path, _, facts, decision = self.approved_inputs()
        decision["deviations"] = [
            {
                "identifier": "DEV-001",
                "description": "Internal-only documented deviation.",
                "impact": "No public distribution is permitted.",
                "disposition": "ACCEPTED_INTERNAL_ONLY",
                "approval_reference": "issue-44/deviation-DEV-001",
            }
        ]
        for approval in decision["approvals"].values():
            approval["deviations"] = copy.deepcopy(decision["deviations"])
        rendered = self.renderer().render_acceptance_bytes(
            facts,
            decision,
            record_relative_path="approved/acceptance-record.json",
            checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
        )
        record = json.loads(rendered.record_content)
        facts_sha = hashlib.sha256(facts_path.read_bytes()).hexdigest()
        for approval in record["approvals"].values():
            self.assertEqual(approval["machine_facts_sha256"], facts_sha)
            self.assertEqual(
                approval["sender"],
                {
                    "organization": decision["operator"]["organization"],
                    "department": decision["operator"]["department"],
                },
            )
            self.assertEqual(
                approval["recipient"],
                {
                    key: decision["recipient"][key]
                    for key in ("organization", "department", "identity_reference")
                },
            )
            self.assertEqual(approval["deviations"], decision["deviations"])

    def test_render_rejects_duplicate_role_identities(self) -> None:
        _, _, _, facts, decision = self.approved_inputs()
        decision["technical_reviewer"]["identity_reference"] = decision["operator"][
            "identity_reference"
        ]
        decision["approvals"]["technical_reviewer"]["identity_reference"] = decision[
            "operator"
        ]["identity_reference"]
        with self.assertRaisesRegex(RuntimeError, "distinct|identity"):
            self.renderer().render_acceptance_bytes(
                facts,
                decision,
                record_relative_path="approved/acceptance-record.json",
                checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
            )

    def test_render_rejects_approval_not_after_candidate_and_freeze_times(self) -> None:
        _, _, _, facts, decision = self.approved_inputs()
        for invalid_time in (
            facts["candidate"]["completed_at_utc"],
            facts["candidate"]["frozen_at_utc"],
        ):
            with self.subTest(invalid_time=invalid_time):
                invalid = copy.deepcopy(decision)
                invalid["approvals"]["operator"]["acknowledged_at_utc"] = invalid_time
                with self.assertRaisesRegex(RuntimeError, "strictly later|after"):
                    self.renderer().render_acceptance_bytes(
                        facts,
                        invalid,
                        record_relative_path="approved/acceptance-record.json",
                        checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
                    )

    def test_render_derives_objective_fields_and_ignores_no_human_override(self) -> None:
        _, _, _, facts, decision = self.approved_inputs()
        decision["approvals"]["operator"]["source_commit"] = "f" * 40
        with self.assertRaisesRegex(RuntimeError, "source_commit|candidate"):
            self.renderer().render_acceptance_bytes(
                facts,
                decision,
                record_relative_path="approved/acceptance-record.json",
                checklist_relative_path="approved/ACCEPTANCE_CHECKLIST.zh-CN.md",
            )

    def test_rendered_record_passes_standalone_validator_without_mocks(self) -> None:
        renderer = self.renderer()
        validator = load_script(
            VALIDATOR_SCRIPT,
            "csc3_acceptance_rendered_record_integration_validator",
        )
        candidate, facts_path, decision_path, _, _ = self.approved_inputs()
        output = candidate.run_root / "approved-for-validator"
        record_path = output / "acceptance-record.json"
        renderer.render_acceptance_inputs(
            candidate.run_root,
            candidate.archive_path,
            facts_path,
            decision_path,
            record_path,
            output / "ACCEPTANCE_CHECKLIST.zh-CN.md",
            output / "DELIVERY_NOTE.zh-CN.md",
        )

        result = validator.validate_acceptance_record(
            record_path,
            candidate.run_root,
            candidate.archive_path,
        )
        self.assertEqual(result["status"], "PASS")

    def test_render_is_byte_identical_in_two_fresh_directories(self) -> None:
        renderer = self.renderer()
        outputs: list[tuple[bytes, bytes, bytes]] = []
        for name in ("fresh-a", "fresh-b"):
            candidate = self.copy_candidate(name)
            _, facts_path, decision_path, _, _ = self.approved_inputs(candidate)
            output = candidate.run_root / "approved"
            renderer.render_acceptance_inputs(
                candidate.run_root,
                candidate.archive_path,
                facts_path,
                decision_path,
                output / "acceptance-record.json",
                output / "ACCEPTANCE_CHECKLIST.zh-CN.md",
                output / "DELIVERY_NOTE.zh-CN.md",
            )
            outputs.append(
                (
                    (output / "acceptance-record.json").read_bytes(),
                    (output / "ACCEPTANCE_CHECKLIST.zh-CN.md").read_bytes(),
                    (output / "DELIVERY_NOTE.zh-CN.md").read_bytes(),
                )
            )
        self.assertEqual(outputs[0], outputs[1])

        cli_output = candidate.run_root / "approved-cli"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = self.preparer.main(
                [
                    "render",
                    "--run-root",
                    str(candidate.run_root),
                    "--archive",
                    str(candidate.archive_path),
                    "--machine-facts",
                    str(facts_path),
                    "--decision",
                    str(decision_path),
                    "--record",
                    str(cli_output / "acceptance-record.json"),
                    "--checklist",
                    str(cli_output / "ACCEPTANCE_CHECKLIST.zh-CN.md"),
                    "--delivery-note",
                    str(cli_output / "DELIVERY_NOTE.zh-CN.md"),
                ]
            )
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "PASS")
        self.assertEqual(
            {path.name for path in cli_output.iterdir()},
            {
                "acceptance-record.json",
                "ACCEPTANCE_CHECKLIST.zh-CN.md",
                "DELIVERY_NOTE.zh-CN.md",
            },
        )

    def test_render_failure_publishes_none_of_three_outputs(self) -> None:
        renderer = self.renderer()
        candidate, facts_path, decision_path, _, _ = self.approved_inputs()
        output = candidate.run_root / "approved"
        real_write = renderer._write_fsynced_at
        writes = 0

        def fail_on_second_write(*args: object, **kwargs: object) -> None:
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("injected render staging failure")
            real_write(*args, **kwargs)

        with mock.patch.object(
            renderer, "_write_fsynced_at", side_effect=fail_on_second_write
        ):
            with self.assertRaisesRegex(
                renderer.AcceptanceRenderingError,
                r"injected render staging failure.*manual cleanup.*"
                r"\.approved\.staging-",
            ):
                renderer.render_acceptance_inputs(
                    candidate.run_root,
                    candidate.archive_path,
                    facts_path,
                    decision_path,
                    output / "acceptance-record.json",
                    output / "ACCEPTANCE_CHECKLIST.zh-CN.md",
                    output / "DELIVERY_NOTE.zh-CN.md",
                )
        self.assertFalse(output.exists())
        failed_render_quarantines = list(
            candidate.run_root.glob(".approved.staging-*")
        )
        self.assertEqual(1, len(failed_render_quarantines))
        self.assertEqual([], list(failed_render_quarantines[0].iterdir()))

        corrupt_output = candidate.run_root / "approved-corrupt"

        def corrupt_schema_valid_record(
            directory_descriptor: int, filename: str, content: bytes
        ) -> None:
            if filename == "acceptance-record.json":
                record = json.loads(content)
                record["delivery_id"] = "schema-valid-but-forged"
                content = canonical_json(record)
            real_write(directory_descriptor, filename, content)

        with mock.patch.object(
            renderer,
            "_write_fsynced_at",
            side_effect=corrupt_schema_valid_record,
        ):
            with self.assertRaisesRegex(
                renderer.AcceptanceRenderingError,
                r"staged rendered output changed.*manual cleanup.*"
                r"\.approved-corrupt\.staging-",
            ):
                renderer.render_acceptance_inputs(
                    candidate.run_root,
                    candidate.archive_path,
                    facts_path,
                    decision_path,
                    corrupt_output / "acceptance-record.json",
                    corrupt_output / "ACCEPTANCE_CHECKLIST.zh-CN.md",
                    corrupt_output / "DELIVERY_NOTE.zh-CN.md",
                )
        self.assertFalse(corrupt_output.exists())
        corrupt_render_quarantines = list(
            candidate.run_root.glob(".approved-corrupt.staging-*")
        )
        self.assertEqual(1, len(corrupt_render_quarantines))
        self.assertEqual([], list(corrupt_render_quarantines[0].iterdir()))

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
        for invalid_path in (
            "machine-facts.json",
            "..\\acceptance-machine-facts.json",
            "C:\\acceptance-machine-facts.json",
        ):
            with self.subTest(invalid_machine_facts_path=invalid_path):
                invalid_decision = copy.deepcopy(decision)
                invalid_decision["machine_facts"]["path"] = invalid_path
                self.assertNotEqual(
                    list(
                        Draft202012Validator(decision_schema).iter_errors(
                            invalid_decision
                        )
                    ),
                    [],
                )
        rejected_decision = copy.deepcopy(decision)
        rejected_decision["decision_status"] = "REJECTED"
        self.assertNotEqual(
            list(Draft202012Validator(decision_schema).iter_errors(rejected_decision)),
            [],
        )
        for invalid_overall in ({}, {"status": "PASS"}):
            with self.subTest(invalid_overall_matrix=invalid_overall):
                invalid_facts = copy.deepcopy(facts)
                invalid_facts["correctness"]["overall_matrix"] = invalid_overall
                self.assertNotEqual(
                    list(
                        Draft202012Validator(machine_schema).iter_errors(
                            invalid_facts
                        )
                    ),
                    [],
                )
        for invalid_path in ("g++", " ", "REQUIRED BEFORE DELIVERY"):
            with self.subTest(invalid_compiler_path=invalid_path):
                invalid_facts = copy.deepcopy(facts)
                invalid_facts["toolchain"]["compiler_path"] = invalid_path
                self.assertNotEqual(
                    list(
                        Draft202012Validator(machine_schema).iter_errors(
                            invalid_facts
                        )
                    ),
                    [],
                )
        for invalid_identity in (" ", "REQUIRED BEFORE DELIVERY"):
            with self.subTest(invalid_mainline_identity=invalid_identity):
                invalid_facts = copy.deepcopy(facts)
                invalid_facts["source"]["mainline_identity"] = invalid_identity
                self.assertNotEqual(
                    list(
                        Draft202012Validator(machine_schema).iter_errors(
                            invalid_facts
                        )
                    ),
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
            with self.assertRaises(TypeError):
                snapshot.machine_facts["source"]["branch"] = "mutated"
            with self.assertRaises(AttributeError):
                snapshot.machine_facts["candidate_closure"].append({})

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
        output = self.root / "existing-output"
        output.mkdir()
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        marker = output / "owner-marker.txt"
        marker.write_bytes(b"existing directory\n")
        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"output directory.*already exists",
        ):
            self.preparer.draft_acceptance_inputs(
                self.fixture.run_root,
                self.fixture.archive_path,
                facts_path,
                decision_path,
                frozen_at_utc=FROZEN_AT_UTC,
            )
        self.assertEqual(marker.read_bytes(), b"existing directory\n")
        self.assertFalse(facts_path.exists())
        self.assertFalse(decision_path.exists())
        self.assertEqual(
            [path for path in self.root.rglob("*") if ".staging-" in path.name],
            [],
        )

    def test_draft_publishes_both_files_with_one_atomic_directory_operation(self) -> None:
        output = self.root / "atomic-pair"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        real_publish = self.preparer._atomic_publish_directory_no_replace
        observed_staging_members: list[list[str]] = []

        def capture_pair(
            parent_descriptor: int,
            staging_name: str,
            destination_name: str,
            error_type,
        ) -> None:
            self.assertEqual(destination_name, output.name)
            self.assertFalse(output.exists())
            staging_descriptor = os.open(
                staging_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_descriptor,
            )
            try:
                observed_staging_members.append(sorted(os.listdir(staging_descriptor)))
            finally:
                os.close(staging_descriptor)
            real_publish(
                parent_descriptor,
                staging_name,
                destination_name,
                error_type,
            )

        with mock.patch.object(
            self.preparer,
            "_atomic_publish_directory_no_replace",
            side_effect=capture_pair,
        ) as publish:
            self.preparer.draft_acceptance_inputs(
                self.fixture.run_root,
                self.fixture.archive_path,
                facts_path,
                decision_path,
                frozen_at_utc=FROZEN_AT_UTC,
            )
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(
            observed_staging_members,
            [["acceptance-decision.json", "acceptance-machine-facts.json"]],
        )
        self.assertTrue(facts_path.is_file())
        self.assertTrue(decision_path.is_file())

    def test_draft_leaves_no_pair_if_atomic_directory_publish_races(self) -> None:
        output = self.root / "publish-race"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        real_publish = self.preparer._atomic_publish_directory_no_replace

        def raced_publish(
            parent_descriptor: int,
            staging_name: str,
            destination_name: str,
            error_type,
        ) -> None:
            os.mkdir(destination_name, 0o700, dir_fd=parent_descriptor)
            destination_descriptor = os.open(
                destination_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_descriptor,
            )
            try:
                self.preparer._write_fsynced_at(
                    destination_descriptor,
                    "owner-marker.txt",
                    b"competing directory\n",
                )
            finally:
                os.close(destination_descriptor)
            real_publish(
                parent_descriptor,
                staging_name,
                destination_name,
                error_type,
            )

        with mock.patch.object(
            self.preparer,
            "_atomic_publish_directory_no_replace",
            side_effect=raced_publish,
        ):
            with self.assertRaisesRegex(
                self.core.AcceptanceCandidateError,
                r"output directory appeared during publication.*manual cleanup.*"
                r"\.publish-race\.staging-",
            ):
                self.preparer.draft_acceptance_inputs(
                    self.fixture.run_root,
                    self.fixture.archive_path,
                    facts_path,
                    decision_path,
                    frozen_at_utc=FROZEN_AT_UTC,
                )
        self.assertFalse(facts_path.exists())
        self.assertFalse(decision_path.exists())
        self.assertEqual(
            (output / "owner-marker.txt").read_bytes(), b"competing directory\n"
        )
        quarantines = [
            path for path in self.root.iterdir() if ".staging-" in path.name
        ]
        self.assertEqual(1, len(quarantines))
        self.assertEqual([], list(quarantines[0].iterdir()))

    def test_draft_leaves_no_output_if_atomic_directory_publish_fails(self) -> None:
        output = self.root / "publish-failure"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        with mock.patch.object(
            self.preparer,
            "_atomic_publish_directory_no_replace",
            side_effect=self.core.AcceptanceCandidateError("injected publish failure"),
        ):
            with self.assertRaisesRegex(
                self.core.AcceptanceCandidateError,
                r"injected publish failure.*manual cleanup.*"
                r"\.publish-failure\.staging-",
            ):
                self.preparer.draft_acceptance_inputs(
                    self.fixture.run_root,
                    self.fixture.archive_path,
                    facts_path,
                    decision_path,
                    frozen_at_utc=FROZEN_AT_UTC,
                )
        self.assertFalse(output.exists())
        quarantines = [
            path for path in self.root.iterdir() if ".staging-" in path.name
        ]
        self.assertEqual(1, len(quarantines))
        self.assertEqual([], list(quarantines[0].iterdir()))

    def test_post_rename_parent_fsync_reports_published_durability_unknown(
        self,
    ) -> None:
        output = self.root / "published-durability-unknown"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        real_publish = self.preparer._atomic_publish_directory_no_replace
        real_fsync = os.fsync
        renamed = False

        def publish_then_mark(*args: object, **kwargs: object) -> None:
            nonlocal renamed
            real_publish(*args, **kwargs)
            renamed = True

        def fail_parent_fsync(descriptor: int) -> None:
            if renamed:
                raise OSError("injected parent fsync failure")
            real_fsync(descriptor)

        with mock.patch.object(
            self.preparer,
            "_atomic_publish_directory_no_replace",
            side_effect=publish_then_mark,
        ), mock.patch.object(self.preparer.os, "fsync", side_effect=fail_parent_fsync):
            with self.assertRaisesRegex(
                RuntimeError, "published but durability (?:is )?unknown"
            ):
                self.preparer.draft_acceptance_inputs(
                    self.fixture.run_root,
                    self.fixture.archive_path,
                    facts_path,
                    decision_path,
                    frozen_at_utc=FROZEN_AT_UTC,
                )
        self.assertTrue(facts_path.is_file())
        self.assertTrue(decision_path.is_file())
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"acceptance-machine-facts.json", "acceptance-decision.json"},
        )

    def test_draft_fails_closed_if_publication_parent_is_swapped(self) -> None:
        publication_parent = self.root / "publication-parent"
        publication_parent.mkdir()
        moved_parent = self.root / "moved-publication-parent"
        replacement_target = self.root / "replacement-target"
        replacement_target.mkdir()
        output = publication_parent / "parent-swap-output"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"
        real_snapshot = self.core.validated_candidate_snapshot

        @contextlib.contextmanager
        def swap_parent_after_validation(*args, **kwargs):
            with real_snapshot(*args, **kwargs) as snapshot:
                publication_parent.rename(moved_parent)
                os.symlink(
                    replacement_target,
                    publication_parent,
                    target_is_directory=True,
                )
                yield snapshot

        with mock.patch.object(
            self.core,
            "validated_candidate_snapshot",
            side_effect=swap_parent_after_validation,
        ):
            with self.assertRaisesRegex(
                self.core.AcceptanceCandidateError,
                r"output parent.*(?:moved|replaced|changed).*manual cleanup.*"
                r"\.parent-swap-output\.staging-",
            ):
                self.preparer.draft_acceptance_inputs(
                    self.fixture.run_root,
                    self.fixture.archive_path,
                    facts_path,
                    decision_path,
                    frozen_at_utc=FROZEN_AT_UTC,
                )

        self.assertFalse((moved_parent / output.name).exists())
        self.assertFalse((replacement_target / output.name).exists())
        moved_quarantines = [
            path for path in moved_parent.iterdir() if ".staging-" in path.name
        ]
        self.assertEqual(1, len(moved_quarantines))
        self.assertEqual([], list(moved_quarantines[0].iterdir()))
        self.assertEqual(
            [],
            [
                path
                for path in replacement_target.iterdir()
                if ".staging-" in path.name
            ],
        )

    def test_draft_rejects_symbolic_link_in_publication_parent_ancestry(self) -> None:
        real_ancestor = self.root / "real-ancestor"
        publication_parent = real_ancestor / "publication-parent"
        publication_parent.mkdir(parents=True)
        linked_ancestor = self.root / "linked-ancestor"
        os.symlink(real_ancestor, linked_ancestor, target_is_directory=True)
        output = linked_ancestor / publication_parent.name / "symlink-ancestor-output"
        facts_path = output / "acceptance-machine-facts.json"
        decision_path = output / "acceptance-decision.json"

        with self.assertRaisesRegex(
            self.core.AcceptanceCandidateError,
            r"output parent.*symbolic link",
        ):
            self.preparer.draft_acceptance_inputs(
                self.fixture.run_root,
                self.fixture.archive_path,
                facts_path,
                decision_path,
                frozen_at_utc=FROZEN_AT_UTC,
            )

        self.assertFalse((publication_parent / output.name).exists())
        self.assertEqual(
            [path for path in publication_parent.iterdir() if ".staging-" in path.name],
            [],
        )

    def test_draft_requires_fixed_output_basenames(self) -> None:
        output = self.root / "invalid-output-names"
        for facts_name, decision_name in (
            ("machine-facts.json", "acceptance-decision.json"),
            ("acceptance-machine-facts.json", "decision.json"),
        ):
            with self.subTest(facts_name=facts_name, decision_name=decision_name):
                with self.assertRaisesRegex(
                    self.core.AcceptanceCandidateError,
                    r"must be named",
                ):
                    self.preparer.draft_acceptance_inputs(
                        self.fixture.run_root,
                        self.fixture.archive_path,
                        output / facts_name,
                        output / decision_name,
                        frozen_at_utc=FROZEN_AT_UTC,
                    )

    def test_draft_rejects_nonobjective_preflight_values(self) -> None:
        cases = (
            ("compiler=/usr/bin/g++", "compiler=g++", r"compiler.*absolute POSIX"),
            (
                "compiler=/usr/bin/g++",
                "compiler= ",
                r"compiler.*(?:absolute POSIX|nonblank)",
            ),
            (
                "<mainline-identity>",
                "REQUIRED BEFORE DELIVERY",
                r"mainline_identity.*placeholder",
            ),
        )
        for index, (old, new, message) in enumerate(cases):
            with self.subTest(new=new):
                fixture = self.copy_candidate(f"invalid-preflight-{index}")
                preflight_path = fixture.run_root / "host-preflight.txt"
                content = preflight_path.read_text(encoding="utf-8")
                if old == "<mainline-identity>":
                    old = next(
                        line
                        for line in content.splitlines()
                        if line.startswith("branch=") and "is_mainline=" in line
                    )
                self.assertIn(old, content)
                preflight_path.write_text(
                    content.replace(old, new, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                replace_checksum(fixture.run_root, "host-preflight.txt")
                with self.assertRaisesRegex(
                    self.core.AcceptanceCandidateError,
                    message,
                ):
                    self.draft(
                        fixture,
                        output_name=f"invalid-preflight-output-{index}",
                    )

    def test_draft_rejects_modified_placeholder_variants(self) -> None:
        _, valid_facts_path, _ = self.draft(output_name="placeholder-control")
        valid_facts = json.loads(valid_facts_path.read_bytes())
        machine_schema = json.loads(MACHINE_SCHEMA.read_text(encoding="utf-8"))
        schema_validator = Draft202012Validator(machine_schema)
        self.assertEqual(list(schema_validator.iter_errors(valid_facts)), [])

        cases = (
            (
                "mainline",
                "branch=",
                "TBD pending measurement",
                ("source", "mainline_identity"),
            ),
            (
                "kernel",
                "Linux controlled-host 6.8.0-fixture #1 SMP x86_64 GNU/Linux",
                "<placeholder>",
                ("controlled_host", "kernel"),
            ),
            (
                "cpuset",
                "cpuset_cpus: 0-31",
                "cpuset_cpus: REQUIRED BEFORE DELIVERY (pending)",
                ("cpu_scope", "cpuset_cpus"),
            ),
        )
        for index, (label, old_prefix, replacement, fact_path) in enumerate(cases):
            with self.subTest(placeholder=label):
                fixture = self.copy_candidate(f"modified-placeholder-{index}")
                preflight_path = fixture.run_root / "host-preflight.txt"
                content = preflight_path.read_text(encoding="utf-8")
                old = old_prefix
                if old_prefix == "branch=":
                    old = next(
                        line
                        for line in content.splitlines()
                        if line.startswith(old_prefix) and "is_mainline=" in line
                    )
                self.assertIn(old, content)
                preflight_path.write_text(
                    content.replace(old, replacement, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                replace_checksum(fixture.run_root, "host-preflight.txt")
                with self.assertRaisesRegex(
                    self.core.AcceptanceCandidateError,
                    r"placeholder",
                ):
                    self.draft(
                        fixture,
                        output_name=f"modified-placeholder-output-{index}",
                    )

                invalid_facts = copy.deepcopy(valid_facts)
                container = invalid_facts
                for key in fact_path[:-1]:
                    container = container[key]
                container[fact_path[-1]] = (
                    replacement.removeprefix("cpuset_cpus: ")
                )
                self.assertNotEqual(
                    list(schema_validator.iter_errors(invalid_facts)),
                    [],
                )

    def test_objective_placeholder_filter_allows_legitimate_tokens(self) -> None:
        _, valid_facts_path, _ = self.draft(output_name="legitimate-token-control")
        valid_facts = json.loads(valid_facts_path.read_bytes())
        machine_schema = json.loads(MACHINE_SCHEMA.read_text(encoding="utf-8"))
        schema_validator = Draft202012Validator(machine_schema)
        cases = (
            (("source", "branch"), "feature/todo-parser"),
            (("source", "mainline_identity"), "feature/unknown-field-support"),
            (("controlled_host", "kernel"), "Measure with the none backend disabled"),
        )

        for fact_path, value in cases:
            with self.subTest(value=value):
                python_error = None
                try:
                    observed = self.core._objective_text(value, "legitimate objective")
                except self.core.AcceptanceCandidateError as error:
                    python_error = str(error)
                    observed = None

                facts = copy.deepcopy(valid_facts)
                container = facts
                for key in fact_path[:-1]:
                    container = container[key]
                container[fact_path[-1]] = value
                schema_errors = list(schema_validator.iter_errors(facts))

                self.assertIsNone(python_error)
                self.assertEqual(observed, value)
                self.assertEqual(schema_errors, [])

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


class AcceptancePublicationFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication = load_script(
            PUBLICATION_SCRIPT,
            "csc3_acceptance_publication_failure_contract",
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="csc3-publication-failure-test-"
        )
        self.root = Path(self.temporary.name).resolve()
        self.parent_descriptor = os.open(
            self.root,
            self.publication.directory_open_flags(),
        )

    def tearDown(self) -> None:
        os.close(self.parent_descriptor)
        self.temporary.cleanup()

    def test_staging_open_failure_retains_a_named_quarantine_directory(self) -> None:
        staging_name = ".draft.staging-fixedtoken"
        real_open = self.publication.os.open

        def fail_staging_open(path: object, *args: object, **kwargs: object) -> int:
            if (
                path == staging_name
                and kwargs.get("dir_fd") == self.parent_descriptor
            ):
                raise OSError("injected staging open failure")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(
            self.publication.secrets,
            "token_hex",
            return_value="fixedtoken",
        ), mock.patch.object(
            self.publication.os,
            "open",
            side_effect=fail_staging_open,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                r"cannot anchor.*injected staging open failure.*"
                r"manual cleanup.*\.draft\.staging-fixedtoken",
            ):
                self.publication.create_staging_directory(
                    self.parent_descriptor,
                    "draft",
                    RuntimeError,
                )

        self.assertTrue((self.root / staging_name).is_dir())
        self.assertEqual([], list((self.root / staging_name).iterdir()))

    def test_failure_path_never_rmdirs_a_name_after_identity_check(self) -> None:
        staging_name = ".draft.staging-swapatrmdir"
        owned_name = f"{staging_name}.owned"
        real_open = self.publication.os.open
        real_rmdir = self.publication.os.rmdir
        swapped = False

        def fail_staging_open(path: object, *args: object, **kwargs: object) -> int:
            if (
                path == staging_name
                and kwargs.get("dir_fd") == self.parent_descriptor
            ):
                raise OSError("injected staging open failure")
            return real_open(path, *args, **kwargs)

        def swap_immediately_before_rmdir(
            path: object, *args: object, **kwargs: object
        ) -> None:
            nonlocal swapped
            if (
                path == staging_name
                and kwargs.get("dir_fd") == self.parent_descriptor
            ):
                os.rename(
                    staging_name,
                    owned_name,
                    src_dir_fd=self.parent_descriptor,
                    dst_dir_fd=self.parent_descriptor,
                )
                os.mkdir(staging_name, 0o700, dir_fd=self.parent_descriptor)
                swapped = True
            real_rmdir(path, *args, **kwargs)

        try:
            with mock.patch.object(
                self.publication.secrets,
                "token_hex",
                return_value="swapatrmdir",
            ), mock.patch.object(
                self.publication.os,
                "open",
                side_effect=fail_staging_open,
            ), mock.patch.object(
                self.publication.os,
                "rmdir",
                side_effect=swap_immediately_before_rmdir,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    r"injected staging open failure.*manual cleanup.*"
                    r"\.draft\.staging-swapatrmdir",
                ):
                    self.publication.create_staging_directory(
                        self.parent_descriptor,
                        "draft",
                        RuntimeError,
                    )
            self.assertFalse(
                swapped,
                "failure handling must not call pathname rmdir after an inode check",
            )
            self.assertTrue((self.root / staging_name).is_dir())
            self.assertFalse((self.root / owned_name).exists())
        finally:
            for name in (staging_name, owned_name):
                if (self.root / name).exists():
                    real_rmdir(name, dir_fd=self.parent_descriptor)

    def test_identity_capture_failure_retains_the_created_directory(self) -> None:
        staging_name = ".draft.staging-identityfailure"
        with mock.patch.object(
            self.publication.secrets,
            "token_hex",
            return_value="identityfailure",
        ), mock.patch.object(
            self.publication,
            "_created_directory_identity",
            side_effect=OSError("injected identity capture failure"),
        ), mock.patch.object(
            self.publication.os,
            "rmdir",
        ) as pathname_rmdir:
            with self.assertRaisesRegex(
                RuntimeError,
                r"identity capture failure.*manual cleanup.*"
                r"\.draft\.staging-identityfailure",
            ):
                self.publication.create_staging_directory(
                    self.parent_descriptor,
                    "draft",
                    RuntimeError,
                )

        pathname_rmdir.assert_not_called()
        self.assertTrue((self.root / staging_name).is_dir())

    def test_failure_cleanup_api_unlinks_known_files_but_retains_directory(
        self,
    ) -> None:
        staging_name = ".draft.staging-knownmembers"
        os.mkdir(staging_name, 0o700, dir_fd=self.parent_descriptor)
        descriptor = os.open(
            staging_name,
            self.publication.directory_open_flags(),
            dir_fd=self.parent_descriptor,
        )
        try:
            for filename in ("known-a", "known-b"):
                self.publication.write_fsynced_at(
                    descriptor,
                    filename,
                    b"known\n",
                )
            with mock.patch.object(self.publication.os, "rmdir") as pathname_rmdir:
                detail = self.publication.retain_unpublished_directory(
                    staging_name,
                    descriptor,
                    ("known-a", "known-b"),
                )
            pathname_rmdir.assert_not_called()
            self.assertRegex(detail, r"manual cleanup.*\.draft\.staging-knownmembers")
            self.assertEqual([], os.listdir(descriptor))
            self.assertTrue((self.root / staging_name).is_dir())
        finally:
            os.close(descriptor)

    def test_quarantine_detail_reports_known_member_cleanup_failure(self) -> None:
        staging_name = ".draft.staging-unlinkfailure"
        os.mkdir(staging_name, 0o700, dir_fd=self.parent_descriptor)
        descriptor = os.open(
            staging_name,
            self.publication.directory_open_flags(),
            dir_fd=self.parent_descriptor,
        )
        try:
            self.publication.write_fsynced_at(
                descriptor,
                "known-member",
                b"known\n",
            )
            real_unlink = self.publication.os.unlink

            def fail_known_member_unlink(
                path: object, *args: object, **kwargs: object
            ) -> None:
                if path == "known-member" and kwargs.get("dir_fd") == descriptor:
                    raise OSError("injected known-member cleanup failure")
                real_unlink(path, *args, **kwargs)

            with mock.patch.object(
                self.publication.os,
                "unlink",
                side_effect=fail_known_member_unlink,
            ):
                detail = self.publication.retain_unpublished_directory(
                    staging_name,
                    descriptor,
                    ("known-member",),
                )

            self.assertRegex(
                detail,
                r"manual cleanup.*\.draft\.staging-unlinkfailure.*"
                r"known-member cleanup failed.*known-member.*"
                r"injected known-member cleanup failure",
            )
            self.assertTrue((self.root / staging_name / "known-member").is_file())
        finally:
            os.close(descriptor)

    def test_publication_module_has_no_pathname_rmdir_failure_cleanup(self) -> None:
        source = PUBLICATION_SCRIPT.read_text(encoding="utf-8")
        finalizer_source = FINALIZER_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("os.rmdir(", source)
        self.assertNotIn("os.rmdir(", finalizer_source)

    def test_failed_creation_cleanup_never_removes_a_replacement_directory(
        self,
    ) -> None:
        cases = (
            (
                "staging",
                ".draft.staging-swaptoken",
                lambda: self.publication.create_staging_directory(
                    self.parent_descriptor,
                    "draft",
                    RuntimeError,
                ),
            ),
            (
                "anchored child",
                "ACCEPTANCE_EVIDENCE",
                lambda: self.publication.create_anchored_subdirectory(
                    self.parent_descriptor,
                    "ACCEPTANCE_EVIDENCE",
                    RuntimeError,
                ),
            ),
        )
        for label, entry_name, create in cases:
            with self.subTest(label=label):
                moved_name = f"{entry_name}.owned"
                real_open = self.publication.os.open

                def swap_then_fail_open(
                    path: object, *args: object, **kwargs: object
                ) -> int:
                    if (
                        path == entry_name
                        and kwargs.get("dir_fd") == self.parent_descriptor
                    ):
                        os.rename(
                            entry_name,
                            moved_name,
                            src_dir_fd=self.parent_descriptor,
                            dst_dir_fd=self.parent_descriptor,
                        )
                        os.mkdir(entry_name, 0o700, dir_fd=self.parent_descriptor)
                        raise OSError("injected post-mkdir replacement")
                    return real_open(path, *args, **kwargs)

                try:
                    with mock.patch.object(
                        self.publication.secrets,
                        "token_hex",
                        return_value="swaptoken",
                    ), mock.patch.object(
                        self.publication.os,
                        "open",
                        side_effect=swap_then_fail_open,
                    ):
                        with self.assertRaisesRegex(
                            RuntimeError,
                            r"injected post-mkdir replacement",
                        ):
                            create()

                    self.assertTrue(
                        (self.root / entry_name).is_dir(),
                        "cleanup must not delete the replacement directory",
                    )
                    self.assertTrue((self.root / moved_name).is_dir())
                finally:
                    for name in (entry_name, moved_name):
                        if (self.root / name).exists():
                            os.rmdir(name, dir_fd=self.parent_descriptor)

    def test_identity_mismatch_cleanup_never_removes_a_replacement_directory(
        self,
    ) -> None:
        entry_name = "ACCEPTANCE_EVIDENCE"
        moved_name = f"{entry_name}.owned"
        real_identity = self.publication.directory_identity
        swapped = False

        def capture_then_swap(descriptor: int) -> tuple[int, int]:
            nonlocal swapped
            identity = real_identity(descriptor)
            if not swapped:
                os.rename(
                    entry_name,
                    moved_name,
                    src_dir_fd=self.parent_descriptor,
                    dst_dir_fd=self.parent_descriptor,
                )
                os.mkdir(entry_name, 0o700, dir_fd=self.parent_descriptor)
                swapped = True
            return identity

        try:
            with mock.patch.object(
                self.publication,
                "directory_identity",
                side_effect=capture_then_swap,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    r"anchored subdirectory changed while being opened",
                ):
                    self.publication.create_anchored_subdirectory(
                        self.parent_descriptor,
                        entry_name,
                        RuntimeError,
                    )
            self.assertTrue(swapped)
            self.assertTrue((self.root / entry_name).is_dir())
            self.assertTrue((self.root / moved_name).is_dir())
        finally:
            for name in (entry_name, moved_name):
                if (self.root / name).exists():
                    os.rmdir(name, dir_fd=self.parent_descriptor)


class AcceptanceDraftPlatformContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = load_script(CORE_SCRIPT, "csc3_acceptance_core")
        cls.preparer = load_script(
            PREPARER_SCRIPT, "csc3_acceptance_preparer_platform_contract"
        )

    def test_unsupported_platform_fails_before_reading_candidate_or_outputs(self) -> None:
        with mock.patch.object(
            self.preparer,
            "SECURE_CANDIDATE_CAPTURE_SUPPORTED",
            False,
        ):
            with self.assertRaisesRegex(
                self.core.AcceptanceCandidateError,
                r"platform.*not support.*secure candidate capture",
            ):
                self.preparer.draft_acceptance_inputs(
                    Path("missing-run-root"),
                    Path("missing-archive.zip"),
                    Path("missing-output") / "acceptance-machine-facts.json",
                    Path("missing-output") / "acceptance-decision.json",
                    frozen_at_utc=FROZEN_AT_UTC,
                )
        if os.name == "nt":
            self.assertFalse(self.preparer.SECURE_CANDIDATE_CAPTURE_SUPPORTED)

    def test_cli_reports_unsupported_platform_without_creating_outputs(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(
            self.preparer,
            "SECURE_CANDIDATE_CAPTURE_SUPPORTED",
            False,
        ), contextlib.redirect_stderr(stderr):
            status = self.preparer.main(
                [
                    "draft",
                    "--run-root",
                    "missing-run-root",
                    "--archive",
                    "missing-archive.zip",
                    "--machine-facts",
                    "missing-output/acceptance-machine-facts.json",
                    "--decision",
                    "missing-output/acceptance-decision.json",
                    "--frozen-at-utc",
                    FROZEN_AT_UTC,
                ]
            )
        self.assertEqual(status, 1)
        self.assertRegex(
            stderr.getvalue(),
            r"platform.*not support.*secure candidate capture",
        )


def load_tests(
    loader: unittest.TestLoader,
    standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    del pattern
    if os.name == "nt":
        return loader.loadTestsFromTestCase(AcceptanceDraftPlatformContractTests)
    return standard_tests


if __name__ == "__main__":
    unittest.main()
