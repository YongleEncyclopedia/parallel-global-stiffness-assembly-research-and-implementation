#!/usr/bin/env python3
"""Freeze CSC3 candidate facts and prepare human approval inputs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType


PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
DECISION_SCHEMA = "ACCEPTANCE_DECISION.schema.json"
CORE_MODULE_NAME = "csc3_acceptance_core"


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
    machine_facts_filename: str,
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
            "path": machine_facts_filename,
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
) -> tuple[Path, Path, Path]:
    facts = _lexical_absolute(Path(machine_facts_path))
    decision = _lexical_absolute(Path(decision_path))
    if facts == decision:
        raise error_type("machine facts and decision outputs must be distinct")
    if facts.parent != decision.parent:
        raise error_type("machine facts and decision outputs must share one parent")
    parent = facts.parent
    try:
        metadata = os.lstat(parent)
    except OSError as error:
        raise error_type(f"output parent cannot be inspected: {parent}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise error_type("output parent must be a real directory, not a symbolic link")
    for path in (facts, decision):
        try:
            os.lstat(path)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise error_type(f"output cannot be inspected: {path}: {error}") from error
        raise error_type(f"output already exists and will not be replaced: {path}")
    return parent, facts, decision


def _write_fsynced(path: Path, content: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_pair(
    *,
    parent: Path,
    machine_facts_path: Path,
    machine_facts_content: bytes,
    decision_path: Path,
    decision_content: bytes,
    machine_facts: dict[str, object],
    decision: dict[str, object],
    core: ModuleType,
    schema_validator: ModuleType,
) -> None:
    published: list[Path] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix=".acceptance-draft-staging-",
            dir=parent,
        ) as staging_name:
            staging = Path(staging_name)
            os.chmod(staging, stat.S_IRWXU)
            staged_facts = staging / machine_facts_path.name
            staged_decision = staging / decision_path.name
            _write_fsynced(staged_facts, machine_facts_content)
            _write_fsynced(staged_decision, decision_content)
            _fsync_directory(staging)

            facts_round_trip = core._strict_json(
                staged_facts.read_bytes(), "staged acceptance-machine-facts.json"
            )
            decision_round_trip = core._strict_json(
                staged_decision.read_bytes(), "staged acceptance-decision.json"
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

            for staged, destination in (
                (staged_facts, machine_facts_path),
                (staged_decision, decision_path),
            ):
                try:
                    os.link(staged, destination)
                except FileExistsError as error:
                    raise core.AcceptanceCandidateError(
                        f"output appeared during publication and was not replaced: "
                        f"{destination}"
                    ) from error
                except OSError as error:
                    raise core.AcceptanceCandidateError(
                        f"cannot publish output without replacement: {destination}: "
                        f"{error}"
                    ) from error
                published.append(destination)
            _fsync_directory(parent)
    except Exception:
        for path in reversed(published):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        if published:
            try:
                _fsync_directory(parent)
            except OSError:
                pass
        raise


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
    schema_validator = _load_sibling(
        "validate_acceptance_record.py", "csc3_acceptance_draft_schema_validator"
    )
    parent, facts_destination, decision_destination = _preflight_outputs(
        machine_facts_path,
        decision_path,
        core.AcceptanceCandidateError,
    )
    if frozen_at_utc is None:
        frozen_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with core.validated_candidate_snapshot(
        Path(run_root),
        Path(archive_path),
        frozen_at_utc=frozen_at_utc,
    ) as snapshot:
        machine_facts = dict(snapshot.machine_facts)
        machine_facts_content = snapshot.machine_facts_content
        machine_facts_sha256 = hashlib.sha256(machine_facts_content).hexdigest()
        decision = _decision_template(
            machine_facts,
            machine_facts_filename=facts_destination.name,
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
            parent=parent,
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


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    draft = subparsers.add_parser("draft", help="freeze one PACKAGE_CANDIDATE")
    draft.add_argument("--run-root", required=True, type=Path)
    draft.add_argument("--archive", required=True, type=Path)
    draft.add_argument("--machine-facts", required=True, type=Path)
    draft.add_argument("--decision", required=True, type=Path)
    draft.add_argument("--frozen-at-utc")
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = _argument_parser().parse_args(arguments)
    core = _load_sibling("acceptance_core.py", CORE_MODULE_NAME)
    try:
        result = draft_acceptance_inputs(
            options.run_root,
            options.archive,
            options.machine_facts,
            options.decision,
            frozen_at_utc=options.frozen_at_utc,
        )
    except (core.AcceptanceCandidateError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
