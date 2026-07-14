#!/usr/bin/env python3
"""Finalize an approved CSC3 candidate as a hash-bound delivery directory."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterator

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
CHECKLIST_MARKER = "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS"
DELIVERY_NOTE_MARKER = "CSC3_DELIVERY_NOTE_STATUS=PASS"
PLACEHOLDER = "REQUIRED BEFORE DELIVERY"
OUTPUT_RECORD = "ACCEPTANCE_RECORD.json"
OUTPUT_CHECKLIST = "ACCEPTANCE_CHECKLIST.zh-CN.md"
OUTPUT_NOTE = "DELIVERY_NOTE.zh-CN.md"
OUTPUT_METADATA = "FINALIZATION.json"
OUTPUT_CHECKSUMS = "FINAL_SHA256SUMS"
EVIDENCE_DIRECTORY = "ACCEPTANCE_EVIDENCE"
CHECKLIST_TEMPLATE = "ACCEPTANCE_CHECKLIST.zh-CN.md"
DELIVERY_NOTE_TEMPLATE = "DELIVERY_NOTE_TEMPLATE.zh-CN.md"


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


def _template_text(filename: str) -> str:
    path = Path(__file__).resolve().parent.parent / "packaging" / filename
    return _decode_markdown(_read_without_following(path, filename), filename)


def _headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.fullmatch(r"#{1,6} .+", line)]


def _checkbox_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^- \[[ xX]\] (.+)$", line)
        if match is None:
            continue
        label = match.group(1).split("：", 1)[0].rstrip()
        labels.append(label)
    return labels


def _table_labels(text: str) -> list[str]:
    labels: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or not cells[0] or set(cells[0]) <= {"-", ":"}:
            continue
        labels.append(cells[0])
    return labels


def _validate_template_structure(
    completed: str,
    *,
    template_filename: str,
    label: str,
    checklist: bool,
) -> None:
    template = _template_text(template_filename)
    errors: list[str] = []
    if _headings(completed) != _headings(template):
        errors.append("section heading sequence differs from the committed template")
    minimum_lines = max(1, int(len(template.splitlines()) * 0.9))
    if len(completed.splitlines()) < minimum_lines:
        errors.append(
            f"contains too few lines to preserve the template ({len(completed.splitlines())} < {minimum_lines})"
        )
    if checklist:
        expected_labels = _checkbox_labels(template)
        actual_labels = _checkbox_labels(completed)
        if actual_labels != expected_labels:
            errors.append("mandatory checklist item sequence differs from the template")
        if not expected_labels:
            errors.append("committed checklist template contains no mandatory items")
    else:
        expected_labels = _table_labels(template)
        actual_labels = _table_labels(completed)
        if actual_labels != expected_labels:
            errors.append("delivery-note table row sequence differs from the template")
        if not expected_labels:
            errors.append("committed delivery-note template contains no table rows")
    if errors:
        raise FinalizationError(f"invalid {label} structure: " + "; ".join(errors))


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


def _require_checklist_item_bindings(
    text: str,
    *,
    bindings: dict[str, tuple[str, str, str]],
) -> None:
    """Require one canonical approval item, including indented continuations."""
    lines = text.splitlines()
    errors: list[str] = []
    for prefix, (identity, acknowledged_at, record_reference) in bindings.items():
        matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
        if len(matches) != 1:
            errors.append(f"item {prefix!r} must occur exactly once")
            continue
        start = matches[0]
        block = [lines[start]]
        for line in lines[start + 1 :]:
            if not line.startswith("  "):
                break
            block.append(line)
        rendered = " ".join(line.strip() for line in block).replace(
            "；记录号", "； 记录号"
        )
        expected = (
            f"{prefix}身份引用 `{identity}`；UTC `{acknowledged_at}`； "
            f"记录号 `{record_reference}`"
        )
        if rendered != expected:
            errors.append(f"item {prefix!r} is not the canonical record-bound value")
    if errors:
        raise FinalizationError(
            "invalid acceptance checklist approval bindings: " + "; ".join(errors)
        )


def _require_exact_line_bindings(
    text: str,
    *,
    label: str,
    bindings: dict[str, str],
) -> None:
    lines = text.splitlines()
    errors: list[str] = []
    for prefix, expected in bindings.items():
        matches = [line for line in lines if line.startswith(prefix)]
        if len(matches) != 1:
            errors.append(f"field {prefix!r} must occur exactly once")
        elif matches[0] != expected:
            errors.append(f"field {prefix!r} is not the canonical record-bound value")
    if errors:
        raise FinalizationError(f"invalid {label} exact bindings: " + "; ".join(errors))


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


def _atomic_publish_directory(
    source_name: str,
    destination_name: str,
    *,
    parent_descriptor: int,
    parent_path: Path,
) -> None:
    """Atomically publish a directory without replacing any destination."""
    if os.name == "nt":
        try:
            os.rename(parent_path / source_name, parent_path / destination_name)
        except FileExistsError as error:
            raise FinalizationError(
                f"output directory appeared during finalization: "
                f"{parent_path / destination_name}"
            ) from error
        return

    libc = ctypes.CDLL(None, use_errno=True)
    source = os.fsencode(source_name)
    destination = os.fsencode(destination_name)
    result: int
    if os.sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        renameat2 = libc.renameat2
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            parent_descriptor,
            source,
            parent_descriptor,
            destination,
            1,  # RENAME_NOREPLACE
        )
    elif os.sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        renameatx_np = libc.renameatx_np
        renameatx_np.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameatx_np.restype = ctypes.c_int
        result = renameatx_np(
            parent_descriptor,
            source,
            parent_descriptor,
            destination,
            0x00000004,  # RENAME_EXCL
        )
    else:
        raise FinalizationError(
            "this platform lacks an atomic no-replace directory rename primitive"
        )

    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FinalizationError(
            f"output directory appeared during finalization: "
            f"{parent_path / destination_name}"
        )
    raise OSError(
        error_number,
        os.strerror(error_number),
        str(parent_path / destination_name),
    )


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
        with validated_acceptance_snapshot(
            record_path, run_root, archive_path
        ) as validated_snapshot:
            validation_result = dict(validated_snapshot.result)
            record_content = validated_snapshot.record_content
            record = dict(validated_snapshot.record)
            archive_content = validated_snapshot.archive_content
            artifact_contents = dict(validated_snapshot.artifact_contents)
    except AcceptanceRecordError as error:
        raise FinalizationError(f"acceptance record validation failed: {error}") from error
    if validation_result.get("status") != "PASS":
        raise FinalizationError("acceptance record status must be PASS")
    if record.get("status") != "PASS":
        raise FinalizationError("acceptance record status must be PASS")
    if record.get("distribution") != DISTRIBUTION:
        raise FinalizationError(f"distribution must be {DISTRIBUTION!r}")

    if archive_content is None:
        raise FinalizationError("validated snapshot does not contain the candidate archive")
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
    _validate_template_structure(
        checklist_text,
        template_filename=CHECKLIST_TEMPLATE,
        label="acceptance checklist",
        checklist=True,
    )
    _validate_template_structure(
        note_text,
        template_filename=DELIVERY_NOTE_TEMPLATE,
        label="delivery note",
        checklist=False,
    )
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
    delivery_id = str(record["delivery_id"])
    source_commit = str(record["source_commit"])
    issue_url = str(record["issue_url"])
    operator = record["operator"]
    recipient = record["recipient"]
    approvals = record["approvals"]
    operator_approval = approvals["operator"]
    reviewer_approval = approvals["technical_reviewer"]
    approver_approval = approvals["delivery_approver"]
    recipient_approval = approvals["recipient_acknowledgement"]
    _require_exact_line_bindings(
        checklist_text,
        label="acceptance checklist",
        bindings={
            "- [x] 交付 ID：": f"- [x] 交付 ID：`{delivery_id}`",
            "- [x] Issue #44 URL：": f"- [x] Issue #44 URL：`{issue_url}`",
            "- [x] 完整源码 SHA：": f"- [x] 完整源码 SHA：`{source_commit}`",
            "- [x] 候选源码 ZIP 文件名及 SHA-256：": (
                "- [x] 候选源码 ZIP 文件名及 SHA-256："
                f"`{archive_path.name}` `{archive_sha256}`"
            ),
            "- [x] 接收组织及部门：": (
                "- [x] 接收组织及部门："
                f"`{recipient['organization']}` / `{recipient['department']}`"
            ),
            "- [x] 指定接收人身份引用：": (
                "- [x] 指定接收人身份引用："
                f"`{recipient['identity_reference']}`"
            ),
            "最终状态：": "最终状态：`PASS`",
        },
    )
    _require_checklist_item_bindings(
        checklist_text,
        bindings={
            "- [x] 操作员：": tuple(
                str(operator_approval[field])
                for field in (
                    "identity_reference",
                    "acknowledged_at_utc",
                    "approval_record_reference",
                )
            ),
            "- [x] 技术复核人：": tuple(
                str(reviewer_approval[field])
                for field in (
                    "identity_reference",
                    "acknowledged_at_utc",
                    "approval_record_reference",
                )
            ),
            "- [x] 交付批准人：": tuple(
                str(approver_approval[field])
                for field in (
                    "identity_reference",
                    "acknowledged_at_utc",
                    "approval_record_reference",
                )
            ),
            "- [x] 接收方确认：": tuple(
                str(recipient_approval[field])
                for field in (
                    "identity_reference",
                    "acknowledged_at_utc",
                    "approval_record_reference",
                )
            ),
        },
    )
    _require_exact_line_bindings(
        note_text,
        label="delivery note",
        bindings={
            "| 交付 ID |": f"| 交付 ID | **{delivery_id}** |",
            "| Issue #44 URL |": f"| Issue #44 URL | **{issue_url}** |",
            "| 发送组织/部门 |": (
                "| 发送组织/部门 | "
                f"**{operator['organization']} / {operator['department']}** |"
            ),
            "| 接收组织/部门 |": (
                "| 接收组织/部门 | "
                f"**{recipient['organization']} / {recipient['department']}** |"
            ),
            "| 指定接收人身份引用 |": (
                "| 指定接收人身份引用 | "
                f"**{recipient['identity_reference']}** |"
            ),
            "| 完整源码 SHA |": f"| 完整源码 SHA | **{source_commit}** |",
            "| 正式源码 ZIP |": (
                f"| 正式源码 ZIP | **{archive_path.name}** | "
                f"**{archive_sha256}** |"
            ),
            "| 操作员 |": (
                f"| 操作员 | **{operator_approval['identity_reference']}** | "
                f"**{operator_approval['acknowledged_at_utc']}** | "
                f"**{operator_approval['approval_record_reference']}** | "
                f"**{operator_approval['acknowledgement']}** |"
            ),
            "| 技术复核人 |": (
                f"| 技术复核人 | **{reviewer_approval['identity_reference']}** | "
                f"**{reviewer_approval['acknowledged_at_utc']}** | "
                f"**{reviewer_approval['approval_record_reference']}** | "
                f"**{reviewer_approval['acknowledgement']}** |"
            ),
            "| 发送方批准/交付批准人 |": (
                "| 发送方批准/交付批准人 | "
                f"**{approver_approval['identity_reference']}** | "
                f"**{approver_approval['acknowledged_at_utc']}** | "
                f"**{approver_approval['approval_record_reference']}** | "
                f"**{approver_approval['acknowledgement']}** |"
            ),
            "| 接收方确认 |": (
                f"| 接收方确认 | **{recipient_approval['identity_reference']}** | "
                f"**{recipient_approval['acknowledged_at_utc']}** | "
                f"**{recipient_approval['approval_record_reference']}** | "
                f"**{recipient_approval['acknowledgement']}** |"
            ),
            "正式验收状态（只能为 `PASS`）：": (
                "正式验收状态（只能为 `PASS`）：**PASS**"
            ),
        },
    )

    canonical_inputs = {
        archive_path.name: archive_content,
        OUTPUT_RECORD: record_content,
        OUTPUT_CHECKLIST: checklist_content,
        OUTPUT_NOTE: note_content,
    }
    evidence_contents, evidence_index = _snapshot_record_artifacts(
        record, artifact_contents
    )
    canonical_inputs.update(evidence_contents)
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
        "acceptance_evidence": evidence_index,
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

    parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        parent_flags |= os.O_NOFOLLOW
    try:
        parent_descriptor = os.open(output_parent, parent_flags)
    except OSError as error:
        raise FinalizationError(f"cannot pin output parent {output_parent}: {error}") from error
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_parent)
    )
    try:
        os.chmod(temporary, 0o700)
        if any(name.startswith(f"{EVIDENCE_DIRECTORY}/") for name in final_contents):
            (temporary / EVIDENCE_DIRECTORY).mkdir(mode=0o700)
        for name, content in sorted(final_contents.items()):
            _write_file(temporary / PurePosixPath(name), content)
        _write_file(temporary / OUTPUT_CHECKSUMS, checksum_content)
        for name, content in final_contents.items():
            if _sha256((temporary / PurePosixPath(name)).read_bytes()) != _sha256(content):
                raise FinalizationError(f"post-write hash mismatch for {name}")
        if os.name != "nt":
            for directory in (temporary / EVIDENCE_DIRECTORY, temporary):
                if directory.exists():
                    descriptor = os.open(
                        directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                    )
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
        try:
            os.stat(
                output_directory.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise FinalizationError(
                f"output directory appeared during finalization: {output_directory}"
            )
        _atomic_publish_directory(
            temporary.name,
            output_directory.name,
            parent_descriptor=parent_descriptor,
            parent_path=output_parent,
        )
        if os.name != "nt":
            os.fsync(parent_descriptor)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        os.close(parent_descriptor)

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
    except (FinalizationError, OSError, ValueError) as error:
        print(f"delivery finalization failed: {error}", file=os.sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
