#!/usr/bin/env python3
"""Finalize an approved CSC3 candidate as a hash-bound delivery directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

try:
    from validate_acceptance_record import (
        AcceptanceRecordError,
        validate_acceptance_record,
    )
except ModuleNotFoundError as import_error:  # Allows a precise error and isolated unit mocks.
    _VALIDATOR_IMPORT_ERROR = import_error

    class AcceptanceRecordError(RuntimeError):
        """The acceptance-record validator is unavailable or rejected the record."""

        def __init__(self, errors: list[str] | str):
            self.errors = [errors] if isinstance(errors, str) else list(errors)
            super().__init__("; ".join(self.errors))

    def validate_acceptance_record(
        record_path: Path, run_root: Path, archive_path: Path
    ) -> dict[str, object]:
        del record_path, run_root, archive_path
        raise AcceptanceRecordError(
            f"cannot import validate_acceptance_record.py: {_VALIDATOR_IMPORT_ERROR}"
        )


FINALIZATION_SCHEMA = "csc3-demo-finalization-v1"
DISTRIBUTION = "INTERNAL EVALUATION ONLY"
CHECKLIST_MARKER = "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS"
DELIVERY_NOTE_MARKER = "CSC3_DELIVERY_NOTE_STATUS=PASS"
PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
OUTPUT_RECORD = "ACCEPTANCE_RECORD.json"
OUTPUT_CHECKLIST = "ACCEPTANCE_CHECKLIST.zh-CN.md"
OUTPUT_NOTE = "DELIVERY_NOTE.zh-CN.md"
OUTPUT_METADATA = "FINALIZATION.json"
OUTPUT_CHECKSUMS = "FINAL_SHA256SUMS"


class FinalizationError(RuntimeError):
    """A candidate package cannot be promoted to a final delivery bundle."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


def _decode_markdown(content: bytes, label: str) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FinalizationError(f"{label} must be UTF-8") from error
    if "\r" in text:
        raise FinalizationError(f"{label} must use LF line endings")
    return text


def _validate_completed_sidecar(
    text: str,
    *,
    label: str,
    status_marker: str,
    record: dict[str, Any],
    archive_name: str,
    archive_sha256: str,
    reject_unchecked_boxes: bool,
) -> None:
    errors: list[str] = []
    if status_marker not in text:
        errors.append(f"missing final status marker {status_marker!r}")
    if PLACEHOLDER in text:
        errors.append(f"contains placeholder {PLACEHOLDER!r}")
    if "STATUS=PENDING" in text or "当前决定：`PENDING`" in text:
        errors.append("still declares PENDING")
    if reject_unchecked_boxes and "- [ ]" in text:
        errors.append("contains unchecked mandatory boxes")
    required_values = {
        "delivery_id": str(record.get("delivery_id", "")),
        "source_commit": str(record.get("source_commit", "")),
        "archive filename": archive_name,
        "archive SHA-256": archive_sha256,
    }
    for name, value in required_values.items():
        if not value or value not in text:
            errors.append(f"does not bind {name} {value!r}")
    if errors:
        raise FinalizationError(f"incomplete {label}: " + "; ".join(errors))


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


def _write_file(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def finalize_delivery(
    record_path: Path,
    run_root: Path,
    archive_path: Path,
    checklist_path: Path,
    delivery_note_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Validate and atomically create one final, approved delivery directory."""

    run_root = _canonical_directory(Path(run_root), "run root")
    record_path = _canonical_regular_file(Path(record_path), "acceptance record")
    archive_path = _canonical_regular_file(Path(archive_path), "candidate archive")
    checklist_path = _canonical_regular_file(Path(checklist_path), "acceptance checklist")
    delivery_note_path = _canonical_regular_file(
        Path(delivery_note_path), "delivery note"
    )
    _reject_aliases(
        {
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

    try:
        record = validate_acceptance_record(record_path, run_root, archive_path)
    except AcceptanceRecordError as error:
        raise FinalizationError(f"acceptance record validation failed: {error}") from error
    if record.get("status") != "PASS":
        raise FinalizationError("acceptance record status must be PASS")
    if record.get("distribution") != DISTRIBUTION:
        raise FinalizationError(f"distribution must be {DISTRIBUTION!r}")

    record_content = _read_without_following(record_path, "acceptance record")
    try:
        reread_record = json.loads(record_content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FinalizationError("acceptance record changed or is not valid UTF-8 JSON") from error
    if reread_record != record:
        raise FinalizationError("acceptance record changed after validation")

    archive_content = _read_without_following(archive_path, "candidate archive")
    checklist_content = _read_without_following(checklist_path, "acceptance checklist")
    note_content = _read_without_following(delivery_note_path, "delivery note")
    archive_sha256 = _sha256(archive_content)
    delivery_zip = record.get("artifacts", {}).get("delivery_zip", {})
    if (
        delivery_zip.get("sha256") != archive_sha256
        or delivery_zip.get("size_bytes") != len(archive_content)
    ):
        raise FinalizationError(
            "candidate archive bytes no longer match acceptance-record delivery_zip"
        )

    checklist_text = _decode_markdown(checklist_content, "acceptance checklist")
    note_text = _decode_markdown(note_content, "delivery note")
    _validate_completed_sidecar(
        checklist_text,
        label="acceptance checklist",
        status_marker=CHECKLIST_MARKER,
        record=record,
        archive_name=archive_path.name,
        archive_sha256=archive_sha256,
        reject_unchecked_boxes=True,
    )
    _validate_completed_sidecar(
        note_text,
        label="delivery note",
        status_marker=DELIVERY_NOTE_MARKER,
        record=record,
        archive_name=archive_path.name,
        archive_sha256=archive_sha256,
        reject_unchecked_boxes=False,
    )

    canonical_inputs = {
        archive_path.name: archive_content,
        OUTPUT_RECORD: record_content,
        OUTPUT_CHECKLIST: checklist_content,
        OUTPUT_NOTE: note_content,
    }
    reserved = {OUTPUT_RECORD, OUTPUT_CHECKLIST, OUTPUT_NOTE, OUTPUT_METADATA, OUTPUT_CHECKSUMS}
    if archive_path.name in reserved:
        raise FinalizationError(f"candidate archive name is reserved: {archive_path.name}")

    file_metadata = {
        name: {"sha256": _sha256(content), "size_bytes": len(content)}
        for name, content in sorted(canonical_inputs.items())
    }
    metadata: dict[str, object] = {
        "schema": FINALIZATION_SCHEMA,
        "status": "PASS",
        "distribution": DISTRIBUTION,
        "delivery_id": record["delivery_id"],
        "source_commit": record["source_commit"],
        "files": file_metadata,
    }
    metadata_content = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    final_contents = dict(canonical_inputs)
    final_contents[OUTPUT_METADATA] = metadata_content
    checksum_content = "".join(
        f"{_sha256(content)}  {name}\n"
        for name, content in sorted(final_contents.items())
    ).encode("utf-8")

    try:
        os.mkdir(output_directory, 0o700)
    except OSError as error:
        raise FinalizationError(
            f"cannot exclusively create output directory {output_directory}: {error}"
        ) from error
    try:
        for name, content in sorted(final_contents.items()):
            _write_file(output_directory / name, content)
        _write_file(output_directory / OUTPUT_CHECKSUMS, checksum_content)
        for name, content in final_contents.items():
            if _sha256((output_directory / name).read_bytes()) != _sha256(content):
                raise FinalizationError(f"post-write hash mismatch for {name}")
    except BaseException:
        shutil.rmtree(output_directory, ignore_errors=True)
        raise

    return {
        "schema": FINALIZATION_SCHEMA,
        "status": "PASS",
        "distribution": DISTRIBUTION,
        "delivery_id": record["delivery_id"],
        "source_commit": record["source_commit"],
        "archive": str(output_directory / archive_path.name),
        "archive_sha256": archive_sha256,
        "final_sha256sums": str(output_directory / OUTPUT_CHECKSUMS),
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize an approved CSC3 candidate into a hash-bound directory."
    )
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
            arguments.record,
            arguments.run_root,
            arguments.archive,
            arguments.checklist,
            arguments.delivery_note,
            arguments.out_dir,
        )
    except FinalizationError as error:
        print(f"delivery finalization failed: {error}", file=os.sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
