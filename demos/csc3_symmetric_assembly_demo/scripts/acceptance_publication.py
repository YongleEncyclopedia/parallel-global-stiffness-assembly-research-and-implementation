#!/usr/bin/env python3
"""把验收目录安全地发布到最终位置。

实现使用目录句柄逐级检查路径，并通过同一文件系统内的原子操作完成发布。脚本
拒绝符号链接、路径替换和已有目标，避免把半成品当成交付目录。
"""

from __future__ import annotations

import ctypes
import errno
import os
import secrets
import stat
import sys
from pathlib import Path


SECURE_DIRECTORY_PUBLICATION_SUPPORTED = (
    (sys.platform.startswith("linux") or sys.platform == "darwin")
    and os.name == "posix"
    and os.open in os.supports_dir_fd
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and all(
        operation in os.supports_dir_fd
        for operation in (os.mkdir, os.stat, os.unlink)
    )
)


class PublishedButDurabilityUnknownError(RuntimeError):
    """The directory is visible after rename, but its parent fsync failed."""

    def __init__(self, destination_name: str, cause: OSError) -> None:
        self.destination_name = destination_name
        self.cause = cause
        super().__init__(
            "output directory was published but durability is unknown: "
            f"{destination_name}: {cause}"
        )


def directory_open_flags() -> int:
    """Return flags used for every anchored directory descriptor."""
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def open_anchored_directory(
    path: Path,
    error_type: type[RuntimeError],
    *,
    label: str = "output parent",
) -> int:
    """Open an absolute directory by walking every component without symlinks."""
    if not path.is_absolute():
        raise error_type(f"{label} must be an absolute path")
    flags = directory_open_flags()
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


def directory_identity(descriptor: int) -> tuple[int, int]:
    """Return a stable device/inode identity for an anchored directory."""
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("anchored descriptor is not a directory")
    return metadata.st_dev, metadata.st_ino


def _created_directory_identity(
    parent_descriptor: int,
    entry_name: str,
) -> tuple[int, int]:
    """Capture the identity created by the immediately preceding mkdir."""
    metadata = os.stat(
        entry_name,
        dir_fd=parent_descriptor,
        follow_symlinks=False,
    )
    if not stat.S_ISDIR(metadata.st_mode):
        raise OSError(errno.ENOTDIR, f"created entry is not a directory: {entry_name}")
    return metadata.st_dev, metadata.st_ino


def _retained_directory_detail(
    entry_name: str,
    cleanup_errors: tuple[str, ...] = (),
) -> str:
    """Describe a fail-closed directory quarantine and any member-cleanup errors."""
    detail = (
        "unpublished directory retained for manual cleanup at relative name "
        f"{entry_name!r}"
    )
    if cleanup_errors:
        detail += "; known-member cleanup failed: " + "; ".join(cleanup_errors)
    return detail


def _raise_retained_directory_error(
    entry_name: str,
    error_type: type[RuntimeError],
    operation: str,
    operation_error: BaseException,
) -> None:
    """Preserve the root error while refusing a pathname-based directory delete."""
    raise error_type(
        f"{operation}: {operation_error}; {_retained_directory_detail(entry_name)}"
    ) from operation_error


def assert_publication_parent_unchanged(
    path: Path,
    anchored_descriptor: int,
    error_type: type[RuntimeError],
) -> None:
    """Fail closed if the lexical publication parent no longer matches its fd."""
    try:
        current_descriptor = open_anchored_directory(path, error_type)
    except error_type as error:
        raise error_type(
            f"output parent was moved, replaced, or changed: {error}"
        ) from error
    try:
        if directory_identity(current_descriptor) != directory_identity(
            anchored_descriptor
        ):
            raise error_type("output parent was moved, replaced, or changed")
    finally:
        os.close(current_descriptor)


def assert_output_absent(
    parent_descriptor: int,
    output_name: str,
    output_path: Path,
    error_type: type[RuntimeError],
) -> None:
    """Refuse any pre-existing destination, including a symlink."""
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


def directory_entry_matches_descriptor(
    parent_descriptor: int,
    entry_name: str,
    directory_descriptor: int,
) -> bool:
    """Return whether one dirfd-relative name still denotes an anchored fd."""
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


def create_staging_directory(
    parent_descriptor: int,
    output_name: str,
    error_type: type[RuntimeError],
) -> tuple[str, int]:
    """Create and anchor one private sibling staging directory."""
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
            created_identity = _created_directory_identity(
                parent_descriptor,
                staging_name,
            )
        except OSError as error:
            _raise_retained_directory_error(
                staging_name,
                error_type,
                "cannot record private acceptance staging directory identity",
                error,
            )
        try:
            staging_descriptor = os.open(
                staging_name,
                directory_open_flags(),
                dir_fd=parent_descriptor,
            )
        except OSError as error:
            _raise_retained_directory_error(
                staging_name,
                error_type,
                "cannot anchor private acceptance staging directory",
                error,
            )
        try:
            opened_identity = directory_identity(staging_descriptor)
            current_identity = _created_directory_identity(
                parent_descriptor,
                staging_name,
            )
        except BaseException as error:
            os.close(staging_descriptor)
            _raise_retained_directory_error(
                staging_name,
                error_type,
                "cannot verify private acceptance staging directory identity",
                error,
            )
        if opened_identity != created_identity or current_identity != created_identity:
            os.close(staging_descriptor)
            _raise_retained_directory_error(
                staging_name,
                error_type,
                "private acceptance staging directory changed while being opened",
                OSError(errno.ESTALE, "directory identity changed"),
            )
        return staging_name, staging_descriptor
    raise error_type("cannot allocate a unique acceptance staging directory")


def create_anchored_subdirectory(
    parent_descriptor: int,
    directory_name: str,
    error_type: type[RuntimeError],
) -> int:
    """Create and anchor one fixed-name private child directory."""
    if (
        not directory_name
        or directory_name in {".", ".."}
        or os.sep in directory_name
    ):
        raise error_type(f"unsafe anchored subdirectory name: {directory_name!r}")
    try:
        os.mkdir(directory_name, 0o700, dir_fd=parent_descriptor)
    except OSError as error:
        raise error_type(
            f"cannot create anchored subdirectory {directory_name!r}: {error}"
        ) from error
    try:
        created_identity = _created_directory_identity(
            parent_descriptor,
            directory_name,
        )
    except OSError as error:
        _raise_retained_directory_error(
            directory_name,
            error_type,
            f"cannot record anchored subdirectory identity {directory_name!r}",
            error,
        )
    try:
        descriptor = os.open(
            directory_name,
            directory_open_flags(),
            dir_fd=parent_descriptor,
        )
    except OSError as error:
        _raise_retained_directory_error(
            directory_name,
            error_type,
            f"cannot open anchored subdirectory {directory_name!r}",
            error,
        )
    try:
        opened_identity = directory_identity(descriptor)
        current_identity = _created_directory_identity(
            parent_descriptor,
            directory_name,
        )
    except BaseException as error:
        os.close(descriptor)
        _raise_retained_directory_error(
            directory_name,
            error_type,
            f"cannot verify anchored subdirectory identity {directory_name!r}",
            error,
        )
    if opened_identity != created_identity or current_identity != created_identity:
        os.close(descriptor)
        _raise_retained_directory_error(
            directory_name,
            error_type,
            f"anchored subdirectory changed while being opened: {directory_name!r}",
            OSError(errno.ESTALE, "directory identity changed"),
        )
    return descriptor


def write_fsynced_at(
    directory_descriptor: int,
    filename: str,
    content: bytes,
    *,
    mode: int = 0o600,
) -> None:
    """Create one fixed-name regular file without following or replacing links."""
    descriptor = os.open(
        filename,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0),
        mode,
        dir_fd=directory_descriptor,
    )
    try:
        offset = 0
        while offset < len(content):
            offset += os.write(descriptor, content[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_regular_file_at(directory_descriptor: int, filename: str) -> bytes:
    """Read one fixed-name staged regular file without following links."""
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


def retain_unpublished_directory(
    directory_name: str,
    directory_descriptor: int,
    filenames: tuple[str, ...],
) -> str:
    """Remove known members by pinned dirfd, but retain the directory quarantine."""
    cleanup_errors: list[str] = []
    for filename in filenames:
        try:
            os.unlink(filename, dir_fd=directory_descriptor)
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_errors.append(f"{filename!r}: {error}")
    return _retained_directory_detail(directory_name, tuple(cleanup_errors))


def atomic_publish_directory_no_replace(
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


def fsync_published_parent(parent_descriptor: int, destination_name: str) -> None:
    """Durably commit a successful rename or report its precise ambiguous state."""
    try:
        os.fsync(parent_descriptor)
    except OSError as error:
        raise PublishedButDurabilityUnknownError(destination_name, error) from error
