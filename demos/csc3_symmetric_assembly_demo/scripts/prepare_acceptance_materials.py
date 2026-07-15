#!/usr/bin/env python3
"""Freeze CSC3 candidate facts and prepare human approval inputs."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType


PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
DECISION_SCHEMA = "ACCEPTANCE_DECISION.schema.json"
CORE_MODULE_NAME = "csc3_acceptance_core"
MACHINE_FACTS_FILENAME = "acceptance-machine-facts.json"
DECISION_FILENAME = "acceptance-decision.json"
SECURE_CANDIDATE_CAPTURE_SUPPORTED = (
    (sys.platform.startswith("linux") or sys.platform == "darwin")
    and os.name == "posix"
    and os.open in os.supports_dir_fd
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and all(
        operation in os.supports_dir_fd
        for operation in (os.mkdir, os.stat, os.unlink, os.rmdir)
    )
)


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


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_anchored_directory(
    path: Path,
    error_type: type[RuntimeError],
    *,
    label: str = "output parent",
) -> int:
    """Open an absolute directory by walking every component without symlinks."""
    if not path.is_absolute():
        raise error_type(f"{label} must be an absolute path")
    flags = _directory_open_flags()
    try:
        descriptor = os.open(os.sep, flags)
    except OSError as error:
        raise error_type(f"{label} root cannot be opened safely: {error}") from error
    try:
        for component in path.parts[1:]:
            if component in {"", ".", ".."}:
                raise error_type(f"{label} contains an unsafe path component")
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    detail = "contains a symbolic link or non-directory component"
                else:
                    detail = "cannot be opened safely"
                raise error_type(
                    f"{label} path {detail}: {component!r}: {error}"
                ) from error
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _directory_identity(descriptor: int) -> tuple[int, int]:
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("anchored descriptor is not a directory")
    return metadata.st_dev, metadata.st_ino


def _assert_publication_parent_unchanged(
    path: Path,
    anchored_descriptor: int,
    error_type: type[RuntimeError],
) -> None:
    try:
        current_descriptor = _open_anchored_directory(path, error_type)
    except error_type as error:
        raise error_type(
            f"output parent was moved, replaced, or changed: {error}"
        ) from error
    try:
        if _directory_identity(current_descriptor) != _directory_identity(
            anchored_descriptor
        ):
            raise error_type("output parent was moved, replaced, or changed")
    finally:
        os.close(current_descriptor)


def _assert_output_absent(
    parent_descriptor: int,
    output_name: str,
    output_path: Path,
    error_type: type[RuntimeError],
) -> None:
    try:
        os.stat(output_name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as error:
        raise error_type(
            f"output directory cannot be inspected safely: {output_path}: {error}"
        ) from error
    raise error_type(
        f"output directory already exists and will not be replaced: {output_path}"
    )


def _directory_entry_matches_descriptor(
    parent_descriptor: int,
    entry_name: str,
    directory_descriptor: int,
) -> bool:
    try:
        entry = os.stat(
            entry_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError:
        return False
    opened = os.fstat(directory_descriptor)
    return (
        stat.S_ISDIR(entry.st_mode)
        and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino)
    )


def _create_staging_directory(
    parent_descriptor: int,
    output_name: str,
    error_type: type[RuntimeError],
) -> tuple[str, int]:
    for _ in range(100):
        staging_name = f".{output_name}.staging-{secrets.token_hex(16)}"
        try:
            os.mkdir(staging_name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as error:
            raise error_type(
                f"cannot create private acceptance staging directory: {error}"
            ) from error
        try:
            staging_descriptor = os.open(
                staging_name,
                _directory_open_flags(),
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            raise error_type(
                f"cannot anchor private acceptance staging directory: {error}"
            ) from error
        if not _directory_entry_matches_descriptor(
            parent_descriptor,
            staging_name,
            staging_descriptor,
        ):
            os.close(staging_descriptor)
            raise error_type(
                "private acceptance staging directory changed while being opened"
            )
        return staging_name, staging_descriptor
    raise error_type("cannot allocate a unique acceptance staging directory")


def _write_fsynced_at(
    directory_descriptor: int,
    filename: str,
    content: bytes,
) -> None:
    descriptor = os.open(
        filename,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0),
        0o600,
        dir_fd=directory_descriptor,
    )
    try:
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_regular_file_at(directory_descriptor: int, filename: str) -> bytes:
    descriptor = os.open(
        filename,
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0),
        dir_fd=directory_descriptor,
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(errno.EINVAL, f"staged member is not regular: {filename}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _cleanup_staging_directory(
    parent_descriptor: int,
    staging_name: str,
    staging_descriptor: int,
    filenames: tuple[str, ...],
) -> None:
    for filename in filenames:
        try:
            os.unlink(filename, dir_fd=staging_descriptor)
        except FileNotFoundError:
            pass
    if _directory_entry_matches_descriptor(
        parent_descriptor,
        staging_name,
        staging_descriptor,
    ):
        os.rmdir(staging_name, dir_fd=parent_descriptor)


def _atomic_publish_directory_no_replace(
    parent_descriptor: int,
    staging_name: str,
    destination_name: str,
    error_type: type[RuntimeError],
) -> None:
    """Atomically publish one directory while refusing any existing target."""
    source_bytes = os.fsencode(staging_name)
    destination_bytes = os.fsencode(destination_name)
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise error_type(
                "platform does not expose renameat2(RENAME_NOREPLACE) for atomic "
                "directory publication"
            )
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        result = renameat2(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            destination_bytes,
            1,
        )
    elif sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        renameatx_np = getattr(libc, "renameatx_np", None)
        if renameatx_np is None:
            raise error_type(
                "platform does not expose renameatx_np(RENAME_EXCL) for atomic "
                "directory publication"
            )
        renameatx_np.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameatx_np.restype = ctypes.c_int
        result = renameatx_np(
            parent_descriptor,
            source_bytes,
            parent_descriptor,
            destination_bytes,
            0x00000004,
        )
    else:
        raise error_type(
            "platform does not support a no-replace atomic directory rename"
        )

    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise error_type(
            f"output directory appeared during publication: {destination_name}"
        )
    if error_number in {errno.ENOSYS, errno.ENOTSUP}:
        raise error_type(
            "platform does not support the required no-replace atomic directory "
            "rename"
        )
    raise error_type(
        "atomic output directory publication failed: "
        + os.strerror(error_number)
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
        os.fsync(publication_parent_descriptor)
    finally:
        try:
            if not published:
                _cleanup_staging_directory(
                    publication_parent_descriptor,
                    staging_name,
                    staging_descriptor,
                    staged_filenames,
                )
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
