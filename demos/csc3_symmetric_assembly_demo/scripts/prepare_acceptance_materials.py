#!/usr/bin/env python3
"""准备并渲染正式验收使用的机器事实和决定文件。

`draft` 固定候选事实并生成待填写的决定模板；`render` 在决定填写后重新验证
输入，再生成验收记录、完成版清单和交付说明。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType


PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
DECISION_SCHEMA = "ACCEPTANCE_DECISION.schema.json"
CORE_MODULE_NAME = "csc3_acceptance_core"
MACHINE_FACTS_FILENAME = "acceptance-machine-facts.json"
DECISION_FILENAME = "acceptance-decision.json"

def _load_sibling(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load required acceptance helper: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _party_placeholder() -> dict[str, str]:
    return {
        "organization": PLACEHOLDER,
        "department": PLACEHOLDER,
        "identity_reference": PLACEHOLDER,
        "authorization_reference": PLACEHOLDER,
    }


def _decision_template(
    machine_facts: dict[str, object],
    *,
    machine_facts_sha256: str,
) -> dict[str, object]:
    operator = _party_placeholder()
    technical_reviewer = _party_placeholder()
    delivery_approver = _party_placeholder()
    recipient = _party_placeholder()
    artifacts = machine_facts["artifacts"]
    delivery_zip = artifacts["delivery_zip"]
    candidate = machine_facts["candidate"]
    clean_room = machine_facts["verifications"]["clean_room"]
    sender = {
        "organization": operator["organization"],
        "department": operator["department"],
    }

    def pending_approval() -> dict[str, object]:
        return {
            "acknowledgement": "PENDING",
            "delivery_id": PLACEHOLDER,
            "source_commit": machine_facts["source_commit"],
            "archive_filename": Path(delivery_zip["path"]).name,
            "archive_sha256": delivery_zip["sha256"],
            "candidate_status": candidate["status"],
            "clean_room_status": clean_room["status"],
            "machine_facts_sha256": machine_facts_sha256,
            "sender": dict(sender),
            "recipient": dict(recipient),
            "deviations": [],
            "identity_reference": PLACEHOLDER,
            "acknowledged_at_utc": PLACEHOLDER,
            "approval_record_reference": PLACEHOLDER,
            "statement": PLACEHOLDER,
        }

    return {
        "schema_version": "csc3-demo-acceptance-decision-v1",
        "machine_facts": {
            "path": MACHINE_FACTS_FILENAME,
            "sha256": machine_facts_sha256,
        },
        "delivery_id": PLACEHOLDER,
        "issue_url": PLACEHOLDER,
        "operator": operator,
        "technical_reviewer": technical_reviewer,
        "delivery_approver": delivery_approver,
        "recipient": recipient,
        "checklist_narratives": {
            "authorization_and_recipient_scope": PLACEHOLDER,
            "no_public_license_acknowledgement": PLACEHOLDER,
            "host_load_and_frequency_policy": PLACEHOLDER,
            "solver_flow_scope_acknowledgement": PLACEHOLDER,
            "known_limitations_and_non_goals": PLACEHOLDER,
            "unresolved_blockers": PLACEHOLDER,
            "rollback_and_reproduction_path": PLACEHOLDER,
            "final_decision_rationale": PLACEHOLDER,
        },
        "delivery_note_narratives": {
            "delivery_purpose_and_authorized_scope": PLACEHOLDER,
            "authorization_reference": PLACEHOLDER,
            "included_items_confirmation": PLACEHOLDER,
            "excluded_items_confirmation": PLACEHOLDER,
            "known_limitations": PLACEHOLDER,
            "unresolved_risks": PLACEHOLDER,
            "rollback_owner_and_contact": PLACEHOLDER,
            "withdrawal_or_replacement_process": PLACEHOLDER,
            "sender_approval_statement": PLACEHOLDER,
            "recipient_acknowledgement_statement": PLACEHOLDER,
        },
        "deviations": [],
        "approvals": {
            "operator": pending_approval(),
            "technical_reviewer": pending_approval(),
            "delivery_approver": pending_approval(),
            "recipient_acknowledgement": pending_approval(),
        },
        "decision_status": "PENDING",
    }


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _preflight_outputs(
    machine_facts_path: Path,
    decision_path: Path,
    error_type: type[RuntimeError],
) -> tuple[Path, Path, Path, Path]:
    facts = _lexical_absolute(Path(machine_facts_path))
    decision = _lexical_absolute(Path(decision_path))
    if facts.name != MACHINE_FACTS_FILENAME:
        raise error_type(
            f"machine facts output must be named {MACHINE_FACTS_FILENAME}"
        )
    if decision.name != DECISION_FILENAME:
        raise error_type(f"decision output must be named {DECISION_FILENAME}")
    if facts == decision:
        raise error_type("machine facts and decision outputs must be distinct")
    if facts.parent != decision.parent:
        raise error_type("machine facts and decision outputs must share one parent")
    output_directory = facts.parent
    publication_parent = output_directory.parent
    return publication_parent, output_directory, facts, decision


_publication = _load_sibling(
    "acceptance_publication.py", "csc3_acceptance_publication"
)
SECURE_CANDIDATE_CAPTURE_SUPPORTED = (
    _publication.SECURE_DIRECTORY_PUBLICATION_SUPPORTED
)
_directory_open_flags = _publication.directory_open_flags
_open_anchored_directory = _publication.open_anchored_directory
_directory_identity = _publication.directory_identity
_assert_publication_parent_unchanged = (
    _publication.assert_publication_parent_unchanged
)
_assert_output_absent = _publication.assert_output_absent
_directory_entry_matches_descriptor = (
    _publication.directory_entry_matches_descriptor
)
_create_staging_directory = _publication.create_staging_directory
_write_fsynced_at = _publication.write_fsynced_at
_read_regular_file_at = _publication.read_regular_file_at
_retain_unpublished_directory = _publication.retain_unpublished_directory
_atomic_publish_directory_no_replace = (
    _publication.atomic_publish_directory_no_replace
)


def _publish_pair(
    *,
    publication_parent: Path,
    publication_parent_descriptor: int,
    output_directory: Path,
    machine_facts_path: Path,
    machine_facts_content: bytes,
    decision_path: Path,
    decision_content: bytes,
    machine_facts: dict[str, object],
    decision: dict[str, object],
    core: ModuleType,
    schema_validator: ModuleType,
) -> None:
    staging_name, staging_descriptor = _create_staging_directory(
        publication_parent_descriptor,
        output_directory.name,
        core.AcceptanceCandidateError,
    )
    staged_filenames = (machine_facts_path.name, decision_path.name)
    published = False
    try:
        _write_fsynced_at(
            staging_descriptor,
            machine_facts_path.name,
            machine_facts_content,
        )
        _write_fsynced_at(
            staging_descriptor,
            decision_path.name,
            decision_content,
        )
        os.fsync(staging_descriptor)

        facts_round_trip = core._strict_json(
            _read_regular_file_at(staging_descriptor, machine_facts_path.name),
            "staged acceptance-machine-facts.json",
        )
        decision_round_trip = core._strict_json(
            _read_regular_file_at(staging_descriptor, decision_path.name),
            "staged acceptance-decision.json",
        )
        if facts_round_trip != machine_facts or decision_round_trip != decision:
            raise core.AcceptanceCandidateError(
                "staged acceptance JSON changed during canonical revalidation"
            )
        schema_validator.validate_schema_document(
            facts_round_trip,
            core.MACHINE_FACTS_SCHEMA,
            schema_label="acceptance-machine-facts schema",
        )
        schema_validator.validate_schema_document(
            decision_round_trip,
            DECISION_SCHEMA,
            schema_label="acceptance-decision schema",
        )

        if not _directory_entry_matches_descriptor(
            publication_parent_descriptor,
            staging_name,
            staging_descriptor,
        ):
            raise core.AcceptanceCandidateError(
                "private acceptance staging directory changed before publication"
            )
        _assert_publication_parent_unchanged(
            publication_parent,
            publication_parent_descriptor,
            core.AcceptanceCandidateError,
        )
        _atomic_publish_directory_no_replace(
            publication_parent_descriptor,
            staging_name,
            output_directory.name,
            core.AcceptanceCandidateError,
        )
        published = True
        _publication.fsync_published_parent(
            publication_parent_descriptor, output_directory.name
        )
    except BaseException as error:
        if not published:
            quarantine_detail = _retain_unpublished_directory(
                staging_name,
                staging_descriptor,
                staged_filenames,
            )
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                error.add_note(quarantine_detail)
                raise
            raise core.AcceptanceCandidateError(
                f"{error}; {quarantine_detail}"
            ) from error
        raise
    finally:
        os.close(staging_descriptor)


def draft_acceptance_inputs(
    run_root: Path,
    archive_path: Path,
    machine_facts_path: Path,
    decision_path: Path,
    *,
    frozen_at_utc: str | None = None,
) -> dict[str, object]:
    """Freeze objective facts and publish a pending decision template."""
    core = _load_sibling("acceptance_core.py", CORE_MODULE_NAME)
    if not SECURE_CANDIDATE_CAPTURE_SUPPORTED:
        raise core.AcceptanceCandidateError(
            "this platform does not support secure candidate capture and atomic "
            "acceptance-directory publication"
        )
    schema_validator = _load_sibling(
        "validate_acceptance_record.py", "csc3_acceptance_draft_schema_validator"
    )
    (
        publication_parent,
        output_directory,
        facts_destination,
        decision_destination,
    ) = _preflight_outputs(
        machine_facts_path,
        decision_path,
        core.AcceptanceCandidateError,
    )
    publication_parent_descriptor = _open_anchored_directory(
        publication_parent,
        core.AcceptanceCandidateError,
    )
    try:
        _assert_output_absent(
            publication_parent_descriptor,
            output_directory.name,
            output_directory,
            core.AcceptanceCandidateError,
        )
        if frozen_at_utc is None:
            frozen_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with core.validated_candidate_snapshot(
            Path(run_root),
            Path(archive_path),
            frozen_at_utc=frozen_at_utc,
        ) as snapshot:
            machine_facts_content = snapshot.machine_facts_content
            machine_facts = core._strict_json(
                machine_facts_content, "acceptance-machine-facts.json"
            )
            if not isinstance(machine_facts, dict):
                raise core.AcceptanceCandidateError(
                    "acceptance-machine-facts.json must be a JSON object"
                )
            machine_facts_sha256 = hashlib.sha256(machine_facts_content).hexdigest()
            decision = _decision_template(
                machine_facts,
                machine_facts_sha256=machine_facts_sha256,
            )
            decision_content = core.canonical_json_bytes(decision)
            try:
                schema_validator.validate_schema_document(
                    decision,
                    DECISION_SCHEMA,
                    schema_label="acceptance-decision schema",
                )
            except Exception as error:
                raise core.AcceptanceCandidateError(
                    f"acceptance decision schema validation failed: {error}"
                ) from error
            _publish_pair(
                publication_parent=publication_parent,
                publication_parent_descriptor=publication_parent_descriptor,
                output_directory=output_directory,
                machine_facts_path=facts_destination,
                machine_facts_content=machine_facts_content,
                decision_path=decision_destination,
                decision_content=decision_content,
                machine_facts=machine_facts,
                decision=decision,
                core=core,
                schema_validator=schema_validator,
            )
            return {
                "status": "APPROVAL_INPUT_READY",
                "machine_facts": str(facts_destination),
                "machine_facts_sha256": machine_facts_sha256,
                "decision": str(decision_destination),
                "decision_sha256": hashlib.sha256(decision_content).hexdigest(),
                "archive_sha256": hashlib.sha256(snapshot.archive_content).hexdigest(),
            }
    finally:
        os.close(publication_parent_descriptor)


def render_acceptance_inputs(
    run_root: Path,
    archive_path: Path,
    machine_facts_path: Path,
    decision_path: Path,
    record_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
) -> dict[str, object]:
    """Render and atomically publish the three approved acceptance materials."""
    renderer = _load_sibling(
        "acceptance_rendering.py", "csc3_acceptance_rendering"
    )
    return renderer.render_acceptance_inputs(
        run_root,
        archive_path,
        machine_facts_path,
        decision_path,
        record_path,
        checklist_path,
        delivery_note_path,
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    draft = subparsers.add_parser("draft", help="freeze one PACKAGE_CANDIDATE")
    draft.add_argument("--run-root", required=True, type=Path)
    draft.add_argument("--archive", required=True, type=Path)
    draft.add_argument("--machine-facts", required=True, type=Path)
    draft.add_argument("--decision", required=True, type=Path)
    draft.add_argument("--frozen-at-utc")
    render = subparsers.add_parser(
        "render", help="render one approved decision into three bound outputs"
    )
    render.add_argument("--run-root", required=True, type=Path)
    render.add_argument("--archive", required=True, type=Path)
    render.add_argument("--machine-facts", required=True, type=Path)
    render.add_argument("--decision", required=True, type=Path)
    render.add_argument("--record", required=True, type=Path)
    render.add_argument("--checklist", required=True, type=Path)
    render.add_argument("--delivery-note", required=True, type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = _argument_parser().parse_args(arguments)
    try:
        if options.command == "draft":
            result = draft_acceptance_inputs(
                options.run_root,
                options.archive,
                options.machine_facts,
                options.decision,
                frozen_at_utc=options.frozen_at_utc,
            )
        else:
            result = render_acceptance_inputs(
                options.run_root,
                options.archive,
                options.machine_facts,
                options.decision,
                options.record,
                options.checklist,
                options.delivery_note,
            )
    except (RuntimeError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
