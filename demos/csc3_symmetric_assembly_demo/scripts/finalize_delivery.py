#!/usr/bin/env python3
"""把已批准且复验通过的候选包固化为最终交付目录。

脚本重新验证验收记录和配套文件，复制已绑定的证据，生成最终 SHA-256 清单，
再通过安全发布流程写入一个此前不存在的目标目录。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterator, Mapping

try:
    from validate_acceptance_record import (
        AcceptanceRecordError,
        ValidatedAcceptanceSnapshot,
        validated_acceptance_snapshot,
    )
except ModuleNotFoundError as import_error:  # Allows a precise error and isolated unit mocks.
    _VALIDATOR_IMPORT_ERROR = import_error

    class AcceptanceRecordError(RuntimeError):
        """The acceptance-record validator is unavailable or rejected the record."""

        def __init__(self, errors: list[str] | str):
            self.errors = [errors] if isinstance(errors, str) else list(errors)
            super().__init__("; ".join(self.errors))

    class ValidatedAcceptanceSnapshot:  # type: ignore[no-redef]
        """Fallback type used only to report the missing validator import."""

    @contextmanager
    def validated_acceptance_snapshot(
        record_path: Path, run_root: Path, archive_path: Path
    ) -> Iterator[ValidatedAcceptanceSnapshot]:
        del record_path, run_root, archive_path
        raise AcceptanceRecordError(
            f"cannot import validate_acceptance_record.py: {_VALIDATOR_IMPORT_ERROR}"
        )
        yield ValidatedAcceptanceSnapshot()


FINALIZATION_SCHEMA = "csc3-demo-finalization-v1"
DISTRIBUTION = "INTERNAL EVALUATION ONLY"
OUTPUT_RECORD = "ACCEPTANCE_RECORD.json"
OUTPUT_CHECKLIST = "ACCEPTANCE_CHECKLIST.zh-CN.md"
OUTPUT_NOTE = "DELIVERY_NOTE.zh-CN.md"
OUTPUT_METADATA = "FINALIZATION.json"
OUTPUT_CHECKSUMS = "FINAL_SHA256SUMS"
EVIDENCE_DIRECTORY = "ACCEPTANCE_EVIDENCE"
OUTPUT_MACHINE_FACTS = "acceptance-machine-facts.json"
OUTPUT_DECISION = "acceptance-decision.json"
RECORD_VERSION = "csc3-demo-formal-acceptance-v2"


class FinalizationError(RuntimeError):
    """A candidate package cannot be promoted to a final delivery bundle."""


@dataclass(frozen=True)
class _FinalizationPaths:
    """Canonical paths pinned at the finalization trust boundary."""

    machine_facts: Path
    decision: Path
    record: Path
    run_root: Path
    archive: Path
    checklist: Path
    delivery_note: Path
    output_directory: Path
    output_parent: Path
    output_parent_descriptor: int


@dataclass(frozen=True)
class _ValidatedFinalizationInputs:
    """Read-only snapshots and canonical bindings accepted for publication."""

    machine_facts: Mapping[str, Any]
    decision: Mapping[str, Any]
    record: Mapping[str, Any]
    machine_facts_content: bytes
    decision_content: bytes
    record_content: bytes
    archive_content: bytes
    checklist_content: bytes
    delivery_note_content: bytes
    evidence_contents: Mapping[str, bytes]
    evidence_index: Mapping[str, Mapping[str, object]]
    candidate_contents: Mapping[str, bytes]
    record_relative: str
    checklist_relative: str
    archive_sha256: str


@dataclass(frozen=True)
class _FinalDeliveryContents:
    """Immutable file plan ready for one atomic directory publication."""

    files: tuple[tuple[str, bytes], ...]


def _load_sibling(filename: str, module_name: str) -> Any:
    path = Path(__file__).resolve().with_name(filename)
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise FinalizationError(f"cannot load required finalization helper: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


acceptance_core = _load_sibling("acceptance_core.py", "csc3_acceptance_core")
acceptance_rendering = _load_sibling(
    "acceptance_rendering.py", "csc3_acceptance_rendering"
)
acceptance_publication = _load_sibling(
    "acceptance_publication.py", "csc3_acceptance_publication"
)
validated_candidate_snapshot = acceptance_core.validated_candidate_snapshot


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_final_relative(raw: str, label: str) -> PurePosixPath:
    pure = PurePosixPath(raw)
    if (
        not raw
        or pure.is_absolute()
        or pure.as_posix() != raw
        or "\\" in raw
        or ":" in raw
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise FinalizationError(f"{label} has unsafe path {raw!r}")
    return pure


def _reject_path_prefix_collisions(paths: set[str], label: str) -> None:
    for raw in sorted(paths):
        pure = _safe_final_relative(raw, label)
        for length in range(1, len(pure.parts)):
            prefix = PurePosixPath(*pure.parts[:length]).as_posix()
            if prefix in paths:
                raise FinalizationError(
                    f"{label} path prefix collision: {prefix!r} is a file and "
                    f"a parent of {raw!r}"
                )


def materialize_candidate_checksum_closure(
    checksum_content: bytes,
    entry_contents: Mapping[str, bytes],
) -> dict[str, bytes]:
    """Validate and return one exact candidate checksum-relative file plan."""
    try:
        checksum_entries = acceptance_core._parse_sha256sums(checksum_content)
    except Exception as error:
        raise FinalizationError(f"candidate SHA256SUMS is invalid: {error}") from error
    if "SHA256SUMS" in checksum_entries:
        raise FinalizationError("candidate SHA256SUMS contains reserved path 'SHA256SUMS'")
    deterministic_content = entry_contents.get("deterministic-package.txt")
    if deterministic_content is None:
        raise FinalizationError(
            "candidate closure is missing deterministic-package.txt"
        )
    try:
        deterministic = acceptance_core._parse_deterministic_package(
            deterministic_content
        )
    except Exception as error:
        raise FinalizationError(
            f"candidate deterministic-package.txt is invalid: {error}"
        ) from error
    zip_b_relative = deterministic["zip_b"]
    expected_paths = set(checksum_entries) | {zip_b_relative}
    actual_paths = set(entry_contents)
    missing = sorted(expected_paths - actual_paths)
    unexpected = sorted(actual_paths - expected_paths)
    if missing:
        raise FinalizationError(
            "candidate closure is missing checksum-relative paths: "
            + ", ".join(missing)
        )
    if unexpected:
        raise FinalizationError(
            "candidate closure contains unlisted or unexpected paths: "
            + ", ".join(unexpected)
        )
    _reject_path_prefix_collisions(
        actual_paths | {"SHA256SUMS"}, "candidate closure"
    )
    for relative, expected_digest in checksum_entries.items():
        actual_digest = _sha256(entry_contents[relative])
        if actual_digest != expected_digest:
            raise FinalizationError(
                f"candidate closure SHA-256 mismatch for {relative!r}: "
                f"expected {expected_digest}, found {actual_digest}"
            )
    zip_a_relative = deterministic["zip_a"]
    if (
        zip_a_relative not in checksum_entries
        or entry_contents[zip_b_relative] != entry_contents[zip_a_relative]
    ):
        raise FinalizationError(
            "candidate deterministic zip_b is not byte-identical to the delivery ZIP"
        )
    return {
        "SHA256SUMS": checksum_content,
        **{relative: entry_contents[relative] for relative in sorted(actual_paths)},
    }


def _canonical_directory(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise FinalizationError(f"{label} must be an absolute path: {path}")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise FinalizationError(f"cannot inspect {label} {path}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise FinalizationError(f"{label} must be a real directory, not a symlink: {path}")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise FinalizationError(f"{label} must use its canonical path: {path}")
    return resolved


def _canonical_regular_file(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise FinalizationError(f"{label} must be an absolute path: {path}")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise FinalizationError(f"cannot inspect {label} {path}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise FinalizationError(f"{label} must be a regular file, not a symlink: {path}")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise FinalizationError(f"{label} must use its canonical path: {path}")
    return resolved


def _read_without_following(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise FinalizationError(f"cannot open {label} {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise FinalizationError(f"{label} changed and is no longer a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _snapshot_record_artifacts(
    record: dict[str, Any], artifact_contents: dict[str, bytes]
) -> tuple[dict[str, bytes], dict[str, dict[str, object]]]:
    raw_artifacts = record.get("artifacts")
    if not isinstance(raw_artifacts, dict):
        raise FinalizationError("acceptance record artifacts must be an object")
    snapshots: dict[str, bytes] = {}
    index: dict[str, dict[str, object]] = {}
    for name, raw in sorted(raw_artifacts.items()):
        if name == "delivery_zip":
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or not isinstance(raw, dict):
            raise FinalizationError(f"invalid acceptance artifact entry: {name!r}")
        relative = raw.get("path")
        if not isinstance(relative, str):
            raise FinalizationError(f"artifacts.{name}.path must be a string")
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or pure.as_posix() != relative
            or "\\" in relative
            or any(part in {"", ".", ".."} for part in pure.parts)
        ):
            raise FinalizationError(f"artifacts.{name}.path is unsafe: {relative!r}")
        content = artifact_contents.get(name)
        if content is None:
            raise FinalizationError(
                f"artifacts.{name} is absent from the validated immutable snapshot"
            )
        if raw.get("size_bytes") != len(content) or raw.get("sha256") != _sha256(content):
            raise FinalizationError(
                f"artifacts.{name} snapshot bytes disagree with the acceptance record"
            )
        suffix = PurePosixPath(relative).suffix
        if not re.fullmatch(r"(?:\.[A-Za-z0-9_-]+)?", suffix):
            suffix = ".bin"
        bundled = f"{EVIDENCE_DIRECTORY}/{name}{suffix}"
        if bundled in snapshots:
            raise FinalizationError(f"duplicate bundled evidence path: {bundled}")
        snapshots[bundled] = content
        index[name] = {
            "record_path": relative,
            "bundled_path": bundled,
            "size_bytes": len(content),
            "sha256": _sha256(content),
        }
    return snapshots, index


def _run_root_relative(path: Path, run_root: Path, label: str) -> str:
    try:
        relative = path.relative_to(run_root).as_posix()
    except ValueError as error:
        raise FinalizationError(f"{label} must be inside the run root") from error
    if not relative or relative.startswith("../"):
        raise FinalizationError(f"{label} has an unsafe run-root-relative path")
    return relative


def _reject_aliases(paths: dict[str, Path]) -> None:
    items = list(paths.items())
    for index, (left_name, left_path) in enumerate(items):
        for right_name, right_path in items[index + 1 :]:
            try:
                aliases = os.path.samefile(left_path, right_path)
            except OSError as error:
                raise FinalizationError(
                    f"cannot compare {left_name} and {right_name}: {error}"
                ) from error
            if aliases:
                raise FinalizationError(
                    f"{left_name} and {right_name} must be distinct files"
                )


def _atomic_publish_directory(
    source_name: str,
    destination_name: str,
    *,
    source_descriptor: int,
    anchored_children: tuple[tuple[str, int], ...],
    parent_descriptor: int,
    parent_path: Path,
) -> None:
    """Atomically publish a directory without replacing any destination."""
    acceptance_publication.assert_publication_parent_unchanged(
        parent_path, parent_descriptor, FinalizationError
    )
    for child_name, child_descriptor in anchored_children:
        if not acceptance_publication.directory_entry_matches_descriptor(
            source_descriptor,
            child_name,
            child_descriptor,
        ):
            raise FinalizationError(
                f"private finalization staging directory changed: {child_name}"
            )
    if not acceptance_publication.directory_entry_matches_descriptor(
        parent_descriptor,
        source_name,
        source_descriptor,
    ):
        raise FinalizationError(
            "private finalization staging directory changed before publication"
        )
    acceptance_publication.atomic_publish_directory_no_replace(
        parent_descriptor,
        source_name,
        destination_name,
        FinalizationError,
    )


def _normalize_finalization_paths(
    machine_facts_path: Path,
    decision_path: Path,
    record_path: Path,
    run_root: Path,
    archive_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
    output_directory: Path,
) -> _FinalizationPaths:
    """Canonicalize every path before reading any acceptance input."""
    run_root = _canonical_directory(Path(run_root), "run root")
    machine_facts_path = _canonical_regular_file(
        Path(machine_facts_path), "acceptance machine facts"
    )
    decision_path = _canonical_regular_file(Path(decision_path), "acceptance decision")
    record_path = _canonical_regular_file(Path(record_path), "acceptance record")
    archive_path = _canonical_regular_file(Path(archive_path), "candidate archive")
    checklist_path = _canonical_regular_file(Path(checklist_path), "acceptance checklist")
    delivery_note_path = _canonical_regular_file(
        Path(delivery_note_path), "delivery note"
    )
    _reject_aliases(
        {
            "acceptance machine facts": machine_facts_path,
            "acceptance decision": decision_path,
            "acceptance record": record_path,
            "candidate archive": archive_path,
            "acceptance checklist": checklist_path,
            "delivery note": delivery_note_path,
        }
    )

    output_directory = Path(output_directory)
    if not output_directory.is_absolute():
        raise FinalizationError("output directory must be an absolute path")
    if output_directory.exists() or output_directory.is_symlink():
        raise FinalizationError(f"output directory already exists: {output_directory}")
    output_parent = _canonical_directory(output_directory.parent, "output parent")
    if output_directory.parent != output_parent:
        raise FinalizationError("output directory must use a canonical parent path")
    output_parent_descriptor = acceptance_publication.open_anchored_directory(
        output_parent,
        FinalizationError,
    )

    return _FinalizationPaths(
        machine_facts=machine_facts_path,
        decision=decision_path,
        record=record_path,
        run_root=run_root,
        archive=archive_path,
        checklist=checklist_path,
        delivery_note=delivery_note_path,
        output_directory=output_directory,
        output_parent=output_parent,
        output_parent_descriptor=output_parent_descriptor,
    )


def _cross_checked_candidate_contents(
    machine_facts: Mapping[str, object],
    immutable_entries: Mapping[str, bytes],
    immutable_artifacts: Mapping[str, bytes],
    accepted_entries: Mapping[str, bytes],
    accepted_artifacts: Mapping[str, bytes],
) -> dict[str, bytes]:
    """Bind both immutable snapshots to one exact materialization plan."""
    candidate_artifacts = machine_facts.get("artifacts")
    if not isinstance(candidate_artifacts, Mapping):
        raise FinalizationError("immutable machine facts lack candidate artifacts")
    zip_b_binding = candidate_artifacts.get("deterministic_zip_b")
    if not isinstance(zip_b_binding, Mapping) or not isinstance(
        zip_b_binding.get("path"), str
    ):
        raise FinalizationError("immutable machine facts lack deterministic zip_b path")
    zip_b_content = immutable_artifacts.get("deterministic_zip_b")
    checksum_content = immutable_artifacts.get("sha256sums_file")
    if zip_b_content is None or checksum_content is None:
        raise FinalizationError(
            "immutable candidate snapshot lacks checksum or deterministic zip_b bytes"
        )
    expected_entries = dict(immutable_entries)
    expected_entries[str(zip_b_binding["path"])] = zip_b_content
    if dict(accepted_entries) != expected_entries:
        raise FinalizationError(
            "candidate checksum closure differs between immutable validation snapshots"
        )
    if accepted_artifacts.get("sha256sums_file") != checksum_content:
        raise FinalizationError(
            "candidate SHA256SUMS differs between immutable validation snapshots"
        )
    return materialize_candidate_checksum_closure(checksum_content, accepted_entries)


def _validate_finalization_inputs(
    paths: _FinalizationPaths,
) -> _ValidatedFinalizationInputs:
    """Capture immutable snapshots and validate every non-Markdown binding."""

    machine_facts_content = _read_without_following(
        paths.machine_facts, "acceptance machine facts"
    )
    decision_content = _read_without_following(paths.decision, "acceptance decision")
    try:
        machine_facts = acceptance_core._strict_json(
            machine_facts_content, "acceptance machine facts"
        )
        decision = acceptance_core._strict_json(
            decision_content, "acceptance decision"
        )
    except Exception as error:
        raise FinalizationError(f"acceptance inputs are invalid: {error}") from error
    if not isinstance(machine_facts, dict) or not isinstance(decision, dict):
        raise FinalizationError("acceptance machine facts and decision must be objects")
    if machine_facts_content != acceptance_core.canonical_json_bytes(machine_facts):
        raise FinalizationError("acceptance machine facts must use canonical JSON bytes")
    if decision_content != acceptance_core.canonical_json_bytes(decision):
        raise FinalizationError("acceptance decision must use canonical JSON bytes")
    candidate = machine_facts.get("candidate")
    frozen_at_utc = candidate.get("frozen_at_utc") if isinstance(candidate, dict) else None
    if not isinstance(frozen_at_utc, str):
        raise FinalizationError("acceptance machine facts lack candidate.frozen_at_utc")
    try:
        with validated_candidate_snapshot(
            paths.run_root,
            paths.archive,
            frozen_at_utc=frozen_at_utc,
        ) as candidate_snapshot:
            if candidate_snapshot.machine_facts_content != machine_facts_content:
                raise FinalizationError(
                    "acceptance machine facts differ from the immutable candidate snapshot"
                )
            immutable_machine_facts = candidate_snapshot.machine_facts
            immutable_candidate_archive = candidate_snapshot.archive_content
            immutable_candidate_entries = dict(candidate_snapshot.relative_contents)
            immutable_candidate_artifacts = dict(candidate_snapshot.artifact_contents)
    except FinalizationError:
        raise
    except Exception as error:
        raise FinalizationError(f"candidate snapshot validation failed: {error}") from error

    try:
        with validated_acceptance_snapshot(
            paths.record, paths.run_root, paths.archive
        ) as validated_snapshot:
            validation_result = dict(validated_snapshot.result)
            record_content = validated_snapshot.record_content
            record = dict(validated_snapshot.record)
            archive_content = validated_snapshot.archive_content
            artifact_contents = dict(validated_snapshot.artifact_contents)
            candidate_checksum_contents = dict(
                validated_snapshot.candidate_checksum_contents
            )
    except AcceptanceRecordError as error:
        raise FinalizationError(f"acceptance record validation failed: {error}") from error
    if validation_result.get("status") != "PASS":
        raise FinalizationError("acceptance record status must be PASS")
    if record.get("status") != "PASS":
        raise FinalizationError("acceptance record status must be PASS")
    if record.get("schema_version") != RECORD_VERSION:
        raise FinalizationError(
            f"acceptance record schema_version must be {RECORD_VERSION}; v1 PASS is rejected"
        )
    if record.get("distribution") != DISTRIBUTION:
        raise FinalizationError(f"distribution must be {DISTRIBUTION!r}")

    if archive_content is None:
        raise FinalizationError("validated snapshot does not contain the candidate archive")
    checklist_content = _read_without_following(paths.checklist, "acceptance checklist")
    note_content = _read_without_following(paths.delivery_note, "delivery note")
    acceptance_inputs = record.get("acceptance_inputs")
    if not isinstance(acceptance_inputs, dict):
        raise FinalizationError("acceptance record lacks v2 acceptance_inputs")
    for name, expected_path, content in (
        ("machine_facts", OUTPUT_MACHINE_FACTS, machine_facts_content),
        ("decision", OUTPUT_DECISION, decision_content),
    ):
        binding = acceptance_inputs.get(name)
        if not isinstance(binding, dict):
            raise FinalizationError(f"acceptance_inputs.{name} must be an artifact")
        expected = {
            "path": expected_path,
            "size_bytes": len(content),
            "sha256": _sha256(content),
        }
        if binding != expected:
            raise FinalizationError(
                f"acceptance_inputs.{name} does not bind the supplied bytes"
            )
    archive_sha256 = _sha256(archive_content)
    delivery_zip = record.get("artifacts", {}).get("delivery_zip", {})
    if (
        delivery_zip.get("sha256") != archive_sha256
        or delivery_zip.get("size_bytes") != len(archive_content)
    ):
        raise FinalizationError(
            "candidate archive bytes no longer match acceptance-record delivery_zip"
        )
    evidence_contents, evidence_index = _snapshot_record_artifacts(
        record, artifact_contents
    )

    candidate_contents = _cross_checked_candidate_contents(
        immutable_machine_facts,
        immutable_candidate_entries,
        immutable_candidate_artifacts,
        candidate_checksum_contents,
        artifact_contents,
    )

    record_relative = _run_root_relative(paths.record, paths.run_root, "acceptance record")
    checklist_relative = _run_root_relative(
        paths.checklist, paths.run_root, "acceptance checklist"
    )
    if immutable_candidate_archive != archive_content:
        raise FinalizationError(
            "candidate archive differs between immutable validation snapshots"
        )

    return _ValidatedFinalizationInputs(
        machine_facts=immutable_machine_facts,
        decision=decision,
        record=record,
        machine_facts_content=machine_facts_content,
        decision_content=decision_content,
        record_content=record_content,
        archive_content=archive_content,
        checklist_content=checklist_content,
        delivery_note_content=note_content,
        evidence_contents=evidence_contents,
        evidence_index=evidence_index,
        candidate_contents=candidate_contents,
        record_relative=record_relative,
        checklist_relative=checklist_relative,
        archive_sha256=archive_sha256,
    )


def _verify_canonical_acceptance_bytes(
    inputs: _ValidatedFinalizationInputs,
) -> None:
    """Delegate canonical Markdown ownership to the renderer and compare bytes."""
    try:
        rendered = acceptance_rendering.render_acceptance_bytes(
            inputs.machine_facts,
            inputs.decision,
            record_relative_path=inputs.record_relative,
            checklist_relative_path=inputs.checklist_relative,
        )
    except FinalizationError:
        raise
    except Exception as error:
        raise FinalizationError(f"acceptance re-rendering failed: {error}") from error
    comparisons = (
        ("acceptance record", inputs.record_content, rendered.record_content),
        ("acceptance checklist", inputs.checklist_content, rendered.checklist_content),
        (
            "delivery note",
            inputs.delivery_note_content,
            rendered.delivery_note_content,
        ),
    )
    for label, supplied, expected in comparisons:
        if supplied != expected:
            raise FinalizationError(
                f"{label} bytes differ from the re-rendered approved inputs"
            )


def _build_final_delivery_contents(
    inputs: _ValidatedFinalizationInputs,
    archive_name: str,
) -> _FinalDeliveryContents:
    """Build one immutable, hash-bound file plan after canonical comparison."""
    canonical_inputs = {
        archive_name: inputs.archive_content,
        OUTPUT_MACHINE_FACTS: inputs.machine_facts_content,
        OUTPUT_DECISION: inputs.decision_content,
        OUTPUT_RECORD: inputs.record_content,
        OUTPUT_CHECKLIST: inputs.checklist_content,
        OUTPUT_NOTE: inputs.delivery_note_content,
    }
    canonical_inputs.update(inputs.evidence_contents)
    for relative, content in inputs.candidate_contents.items():
        bundled = f"{EVIDENCE_DIRECTORY}/candidate/{relative}"
        if bundled in canonical_inputs:
            raise FinalizationError(f"duplicate candidate evidence path: {bundled}")
        canonical_inputs[bundled] = content
    reserved = {
        OUTPUT_MACHINE_FACTS,
        OUTPUT_DECISION,
        OUTPUT_RECORD,
        OUTPUT_CHECKLIST,
        OUTPUT_NOTE,
        OUTPUT_METADATA,
        OUTPUT_CHECKSUMS,
    }
    if archive_name in reserved:
        raise FinalizationError(f"candidate archive name is reserved: {archive_name}")

    file_metadata = {
        name: {"sha256": _sha256(content), "size_bytes": len(content)}
        for name, content in sorted(canonical_inputs.items())
    }
    metadata: dict[str, object] = {
        "schema": FINALIZATION_SCHEMA,
        "status": "PASS",
        "distribution": DISTRIBUTION,
        "delivery_id": inputs.record["delivery_id"],
        "source_commit": inputs.record["source_commit"],
        "acceptance_evidence": inputs.evidence_index,
        "files": file_metadata,
    }
    metadata_content = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    final_contents = dict(canonical_inputs)
    final_contents[OUTPUT_METADATA] = metadata_content
    return _FinalDeliveryContents(files=tuple(sorted(final_contents.items())))


def _staged_tree_plan(
    delivery: _FinalDeliveryContents,
) -> tuple[tuple[str, ...], tuple[tuple[str, bytes], ...]]:
    """Return exact directory and file plans for recursive anchored staging."""
    files = dict(delivery.files)
    if OUTPUT_CHECKSUMS in files:
        raise FinalizationError(f"duplicate final delivery path: {OUTPUT_CHECKSUMS}")
    _reject_path_prefix_collisions(set(files), "final delivery")
    directories: set[str] = set()
    for name in files:
        pure = _safe_final_relative(name, "final delivery member")
        for length in range(1, len(pure.parts)):
            directories.add(PurePosixPath(*pure.parts[:length]).as_posix())
    return (
        tuple(sorted(directories, key=lambda item: (item.count("/"), item))),
        tuple(sorted(files.items())),
    )


def _checksum_content_from_staged(
    directory_descriptors: Mapping[str, int],
    members: tuple[tuple[str, bytes], ...],
) -> bytes:
    """Derive canonical checksums from the exact staged regular-file bytes."""
    lines: list[str] = []
    for relative, _ in sorted(members):
        pure = PurePosixPath(relative)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        observed = acceptance_publication.read_regular_file_at(
            directory_descriptors[parent], pure.name
        )
        lines.append(f"{_sha256(observed)}  {relative}\n")
    return "".join(lines).encode("utf-8")


def _write_and_verify_staged_members(
    directory_descriptors: Mapping[str, int],
    members: tuple[tuple[str, bytes], ...],
) -> None:
    """Write recursive fixed names and read exact bytes through pinned dirfds."""
    for relative, content in members:
        pure = PurePosixPath(relative)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        acceptance_publication.write_fsynced_at(
            directory_descriptors[parent],
            pure.name,
            content,
            mode=0o644,
        )
    for relative, expected in members:
        pure = PurePosixPath(relative)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        observed = acceptance_publication.read_regular_file_at(
            directory_descriptors[parent],
            pure.name,
        )
        if observed != expected:
            raise FinalizationError(f"post-write byte mismatch for {relative}")


def _verify_staged_checksum_manifest(
    directory_descriptors: Mapping[str, int],
    manifest_relative: str,
) -> None:
    """Run an in-process ``sha256sum -c`` against one staged manifest."""
    manifest = PurePosixPath(manifest_relative)
    manifest_parent = (
        PurePosixPath(*manifest.parts[:-1]).as_posix()
        if len(manifest.parts) > 1
        else ""
    )
    content = acceptance_publication.read_regular_file_at(
        directory_descriptors[manifest_parent], manifest.name
    )
    try:
        entries = acceptance_core._parse_sha256sums(content)
    except Exception as error:
        raise FinalizationError(
            f"staged checksum manifest {manifest_relative!r} is invalid: {error}"
        ) from error
    for relative, expected_digest in entries.items():
        target = manifest.parent / PurePosixPath(relative)
        target_relative = target.as_posix()
        parent = (
            PurePosixPath(*target.parts[:-1]).as_posix()
            if len(target.parts) > 1
            else ""
        )
        descriptor = directory_descriptors.get(parent)
        if descriptor is None:
            raise FinalizationError(
                f"staged checksum path has no anchored parent: {target_relative}"
            )
        observed = acceptance_publication.read_regular_file_at(
            descriptor, target.name
        )
        actual_digest = _sha256(observed)
        if actual_digest != expected_digest:
            raise FinalizationError(
                f"staged checksum mismatch for {target_relative}: expected "
                f"{expected_digest}, found {actual_digest}"
            )


def _verify_exact_staged_inventory(
    directory_descriptors: Mapping[str, int],
    members: tuple[tuple[str, bytes], ...],
) -> None:
    """Reject every missing, extra, or non-regular staged tree member."""
    expected_files: dict[str, set[str]] = {
        directory: set() for directory in directory_descriptors
    }
    expected_directories: dict[str, set[str]] = {
        directory: set() for directory in directory_descriptors
    }
    for relative, _ in members:
        pure = PurePosixPath(relative)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        expected_files[parent].add(pure.name)
    for directory in directory_descriptors:
        if not directory:
            continue
        pure = PurePosixPath(directory)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        expected_directories[parent].add(pure.name)
    for directory, descriptor in directory_descriptors.items():
        expected = expected_files[directory] | expected_directories[directory]
        observed = set(os.listdir(descriptor))
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        if missing or unexpected:
            location = directory or "."
            raise FinalizationError(
                f"exact staged inventory mismatch at {location!r}; "
                f"missing={missing!r}, unexpected staged members={unexpected!r}"
            )
        for filename in expected_files[directory]:
            metadata = os.stat(filename, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise FinalizationError(
                    f"exact staged inventory member is not regular: "
                    f"{directory}/{filename}"
                )
        for child in expected_directories[directory]:
            child_relative = f"{directory}/{child}" if directory else child
            if not acceptance_publication.directory_entry_matches_descriptor(
                descriptor,
                child,
                directory_descriptors[child_relative],
            ):
                raise FinalizationError(
                    f"exact staged inventory directory changed: {child_relative}"
                )


def _retain_unpublished_staging(
    staging_name: str,
    staging_descriptor: int,
    directory_descriptors: Mapping[str, int],
    members: tuple[tuple[str, bytes], ...],
) -> str:
    """Clean known files by pinned dirfd and retain every directory quarantine."""
    details: list[str] = []
    members_by_parent: dict[str, list[str]] = {}
    for relative, _ in members:
        pure = PurePosixPath(relative)
        parent = PurePosixPath(*pure.parts[:-1]).as_posix() if len(pure.parts) > 1 else ""
        members_by_parent.setdefault(parent, []).append(pure.name)
    for directory in sorted(
        (name for name in directory_descriptors if name),
        key=lambda item: (item.count("/"), item),
        reverse=True,
    ):
        details.append(
            acceptance_publication.retain_unpublished_directory(
                directory,
                directory_descriptors[directory],
                tuple(sorted(members_by_parent.get(directory, []))),
            )
        )
    details.append(
        acceptance_publication.retain_unpublished_directory(
            staging_name,
            staging_descriptor,
            tuple(sorted(members_by_parent.get("", []))),
        )
    )
    return "; ".join(details)


def _publish_final_delivery_contents(
    paths: _FinalizationPaths,
    delivery: _FinalDeliveryContents,
) -> None:
    """Write, verify, and atomically publish one immutable final file plan."""
    directories, members = _staged_tree_plan(delivery)
    staged_members = members
    parent_descriptor = paths.output_parent_descriptor
    staging_name = ""
    staging_descriptor = -1
    directory_descriptors: dict[str, int] = {}
    published = False
    try:
        acceptance_publication.assert_publication_parent_unchanged(
            paths.output_parent,
            parent_descriptor,
            FinalizationError,
        )
        acceptance_publication.assert_output_absent(
            parent_descriptor,
            paths.output_directory.name,
            paths.output_directory,
            FinalizationError,
        )
        staging_name, staging_descriptor = (
            acceptance_publication.create_staging_directory(
                parent_descriptor,
                paths.output_directory.name,
                FinalizationError,
            )
        )
        directory_descriptors[""] = staging_descriptor
        for directory in directories:
            pure = PurePosixPath(directory)
            parent = (
                PurePosixPath(*pure.parts[:-1]).as_posix()
                if len(pure.parts) > 1
                else ""
            )
            directory_descriptors[directory] = (
                acceptance_publication.create_anchored_subdirectory(
                    directory_descriptors[parent],
                    pure.name,
                    FinalizationError,
                )
            )
        _write_and_verify_staged_members(directory_descriptors, members)
        _verify_exact_staged_inventory(directory_descriptors, members)
        final_checksum_content = _checksum_content_from_staged(
            directory_descriptors, members
        )
        acceptance_publication.write_fsynced_at(
            staging_descriptor,
            OUTPUT_CHECKSUMS,
            final_checksum_content,
            mode=0o644,
        )
        staged_members = tuple(
            sorted((*members, (OUTPUT_CHECKSUMS, final_checksum_content)))
        )
        _verify_exact_staged_inventory(directory_descriptors, staged_members)
        _verify_staged_checksum_manifest(
            directory_descriptors,
            f"{EVIDENCE_DIRECTORY}/candidate/SHA256SUMS",
        )
        _verify_staged_checksum_manifest(
            directory_descriptors,
            OUTPUT_CHECKSUMS,
        )
        for descriptor in directory_descriptors.values():
            os.fsync(descriptor)
        os.fsync(staging_descriptor)
        acceptance_publication.assert_output_absent(
            parent_descriptor,
            paths.output_directory.name,
            paths.output_directory,
            FinalizationError,
        )
        for directory in directories:
            pure = PurePosixPath(directory)
            parent = (
                PurePosixPath(*pure.parts[:-1]).as_posix()
                if len(pure.parts) > 1
                else ""
            )
            if not acceptance_publication.directory_entry_matches_descriptor(
                directory_descriptors[parent],
                pure.name,
                directory_descriptors[directory],
            ):
                raise FinalizationError(
                    f"private finalization staging directory changed: {directory}"
                )
        evidence_descriptor = directory_descriptors.get(EVIDENCE_DIRECTORY)
        _atomic_publish_directory(
            staging_name,
            paths.output_directory.name,
            source_descriptor=staging_descriptor,
            anchored_children=(
                ((EVIDENCE_DIRECTORY, evidence_descriptor),)
                if evidence_descriptor is not None
                else ()
            ),
            parent_descriptor=parent_descriptor,
            parent_path=paths.output_parent,
        )
        published = True
        acceptance_publication.fsync_published_parent(
            parent_descriptor, paths.output_directory.name
        )
    except BaseException as error:
        if staging_descriptor >= 0 and not published:
            quarantine_detail = _retain_unpublished_staging(
                staging_name,
                staging_descriptor,
                directory_descriptors,
                staged_members,
            )
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                error.add_note(quarantine_detail)
                raise
            raise FinalizationError(f"{error}; {quarantine_detail}") from error
        raise
    finally:
        for directory, descriptor in sorted(
            directory_descriptors.items(),
            key=lambda item: (item[0].count("/"), item[0]),
            reverse=True,
        ):
            if directory:
                os.close(descriptor)
        if staging_descriptor >= 0:
            os.close(staging_descriptor)


def finalize_delivery(
    machine_facts_path: Path,
    decision_path: Path,
    record_path: Path,
    run_root: Path,
    archive_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Validate and atomically create one final, approved delivery directory."""
    if not acceptance_publication.SECURE_DIRECTORY_PUBLICATION_SUPPORTED:
        raise FinalizationError(
            "this platform does not support secure acceptance-directory publication"
        )
    paths = _normalize_finalization_paths(
        machine_facts_path,
        decision_path,
        record_path,
        run_root,
        archive_path,
        checklist_path,
        delivery_note_path,
        output_directory,
    )
    try:
        inputs = _validate_finalization_inputs(paths)
        _verify_canonical_acceptance_bytes(inputs)
        delivery = _build_final_delivery_contents(inputs, paths.archive.name)
        _publish_final_delivery_contents(paths, delivery)
    finally:
        os.close(paths.output_parent_descriptor)

    return {
        "schema": FINALIZATION_SCHEMA,
        "status": "PASS",
        "distribution": DISTRIBUTION,
        "delivery_id": inputs.record["delivery_id"],
        "source_commit": inputs.record["source_commit"],
        "archive": str(paths.output_directory / paths.archive.name),
        "archive_sha256": inputs.archive_sha256,
        "final_sha256sums": str(paths.output_directory / OUTPUT_CHECKSUMS),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize an approved CSC3 candidate into a hash-bound directory."
    )
    parser.add_argument("--machine-facts", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--checklist", type=Path, required=True)
    parser.add_argument("--delivery-note", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    try:
        result = finalize_delivery(
            arguments.machine_facts,
            arguments.decision,
            arguments.record,
            arguments.run_root,
            arguments.archive,
            arguments.checklist,
            arguments.delivery_note,
            arguments.out_dir,
        )
    except (
        FinalizationError,
        acceptance_publication.PublishedButDurabilityUnknownError,
        OSError,
        ValueError,
    ) as error:
        print(f"delivery finalization failed: {error}", file=os.sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
