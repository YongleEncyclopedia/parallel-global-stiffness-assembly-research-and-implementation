#!/usr/bin/env python3
"""Validate local destinations in every tracked Markdown file.

The checker intentionally validates destination paths, not heading fragments.  A
link such as ``guide.md#heading`` therefore passes when ``guide.md`` exists even
if ``heading`` is absent.  This keeps the dependency-free gate deterministic
while still enforcing repository containment, exact path case, and existence.
"""

from __future__ import annotations

import argparse
import os
import re
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


_FENCE_OPEN = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
_REFERENCE_DEFINITION = re.compile(
    r"^[ \t]{0,3}\[(?:\\.|[^\]])+\]:[ \t]*(.*)$"
)
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_MARKDOWN_ESCAPE = re.compile(
    r"\\([" + re.escape(string.punctuation) + r"])",
)


@dataclass(frozen=True, order=True)
class Violation:
    """One stable, sortable Markdown destination violation."""

    file: str
    line: int
    destination: str
    reason: str

    def render(self) -> str:
        return f"{self.file}:{self.line}:{self.destination}:{self.reason}"


def _run_git(repository_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def discover_repository_root(start: Path) -> Path:
    """Return Git's canonical worktree root for *start*."""

    return Path(_run_git(start, "rev-parse", "--show-toplevel").strip()).resolve()


def tracked_markdown_files(repository_root: Path) -> list[Path]:
    """Return tracked ``*.md`` paths in Git's deterministic order."""

    output = _run_git(repository_root, "ls-files", "-z", "--", "*.md")
    return [Path(value) for value in output.split("\0") if value]


def _mask_inline_code(line: str) -> str:
    """Replace complete CommonMark-style backtick spans with spaces."""

    masked = list(line)
    cursor = 0
    while cursor < len(line):
        opening = line.find("`", cursor)
        if opening < 0:
            break

        opening_end = opening
        while opening_end < len(line) and line[opening_end] == "`":
            opening_end += 1
        delimiter_length = opening_end - opening

        search = opening_end
        closing_start = -1
        closing_end = -1
        while search < len(line):
            candidate = line.find("`", search)
            if candidate < 0:
                break
            candidate_end = candidate
            while candidate_end < len(line) and line[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - candidate == delimiter_length:
                closing_start = candidate
                closing_end = candidate_end
                break
            search = candidate_end

        if closing_start < 0:
            cursor = opening_end
            continue

        for index in range(opening, closing_end):
            masked[index] = " "
        cursor = closing_end

    return "".join(masked)


def _reference_destination(tail: str) -> str | None:
    """Extract the destination prefix from a reference definition tail."""

    text = tail.lstrip(" \t")
    if not text:
        return None
    if text.startswith("<"):
        cursor = 1
        while cursor < len(text):
            if text[cursor] == "\\":
                cursor += 2
                continue
            if text[cursor] == ">":
                return text[1:cursor]
            cursor += 1
        return None

    cursor = 0
    while cursor < len(text):
        if text[cursor] == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if text[cursor].isspace():
            break
        cursor += 1
    return text[:cursor] if cursor else None


def _label_end(line: str, opening: int) -> int | None:
    depth = 0
    cursor = opening
    while cursor < len(line):
        character = line[cursor]
        if character == "\\":
            cursor += 2
            continue
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return None


def _link_closer(line: str, start: int) -> int | None:
    """Find the closing parenthesis after a destination and optional title."""

    quote: str | None = None
    nested_parentheses = 0
    cursor = start
    while cursor < len(line):
        character = line[cursor]
        if character == "\\":
            cursor += 2
            continue
        if quote is not None:
            if character == quote:
                quote = None
            cursor += 1
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "(":
            nested_parentheses += 1
        elif character == ")":
            if nested_parentheses == 0:
                return cursor
            nested_parentheses -= 1
        cursor += 1
    return None


def _inline_destination(line: str, start: int) -> tuple[str, int] | None:
    """Extract one inline link destination and its closing parenthesis."""

    cursor = start
    while cursor < len(line) and line[cursor] in " \t":
        cursor += 1
    destination_start = cursor

    if cursor < len(line) and line[cursor] == "<":
        destination_start = cursor + 1
        cursor += 1
        while cursor < len(line):
            if line[cursor] == "\\":
                cursor += 2
                continue
            if line[cursor] == ">":
                closer = _link_closer(line, cursor + 1)
                if closer is None:
                    return None
                return line[destination_start:cursor], closer
            cursor += 1
        return None

    nested_parentheses = 0
    while cursor < len(line):
        character = line[cursor]
        if character == "\\":
            cursor += 2
            continue
        if character == "(":
            nested_parentheses += 1
        elif character == ")":
            if nested_parentheses == 0:
                return line[destination_start:cursor], cursor
            nested_parentheses -= 1
        elif character.isspace() and nested_parentheses == 0:
            closer = _link_closer(line, cursor)
            if closer is None:
                return None
            return line[destination_start:cursor], closer
        cursor += 1
    return None


def _inline_destinations(line: str) -> list[str]:
    destinations: list[str] = []
    cursor = 0
    while cursor < len(line):
        opening = line.find("[", cursor)
        if opening < 0:
            break
        closing = _label_end(line, opening)
        if closing is None:
            break
        if closing + 1 < len(line) and line[closing + 1] == "(":
            parsed = _inline_destination(line, closing + 2)
            if parsed is not None:
                destination, link_end = parsed
                destinations.append(destination)
                cursor = link_end + 1
                continue
        cursor = closing + 1
    return destinations


def extract_destinations(markdown: str) -> list[tuple[int, str]]:
    """Return ``(line, destination)`` pairs outside code spans and fences."""

    destinations: list[tuple[int, str]] = []
    fence_character: str | None = None
    fence_length = 0

    for line_number, line in enumerate(markdown.splitlines(), 1):
        if fence_character is not None:
            closing_fence = re.compile(
                rf"^[ ]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*$"
            )
            if closing_fence.match(line):
                fence_character = None
                fence_length = 0
            continue

        opening_fence = _FENCE_OPEN.match(line)
        if opening_fence:
            delimiter = opening_fence.group(1)
            fence_character = delimiter[0]
            fence_length = len(delimiter)
            continue

        visible_line = _mask_inline_code(line)
        reference = _REFERENCE_DEFINITION.match(visible_line)
        if reference:
            destination = _reference_destination(reference.group(1))
            if destination is not None:
                destinations.append((line_number, destination))
        destinations.extend(
            (line_number, destination)
            for destination in _inline_destinations(visible_line)
        )

    return destinations


def _is_host_local_absolute(value: str) -> bool:
    return (
        value.startswith("/")
        or value.startswith("\\\\")
        or bool(_WINDOWS_DRIVE.match(value))
        or value.lower().startswith("file:")
    )


def _is_results_markdown(source_relative: Path) -> bool:
    return "results" in source_relative.parent.parts


def _path_status(repository_root: Path, relative_target: Path) -> str:
    """Return ``ok``, ``case``, or ``missing`` using exact directory entries."""

    current = repository_root
    for component in relative_target.parts:
        try:
            entries = os.listdir(current)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return "missing"
        if component in entries:
            current = current / component
            continue
        if any(entry.casefold() == component.casefold() for entry in entries):
            return "case"
        return "missing"
    return "ok" if current.exists() else "missing"


def _validate_destination(
    repository_root: Path,
    source_relative: Path,
    line: int,
    destination: str,
) -> Violation | None:
    raw_destination = destination.strip()
    source_display = source_relative.as_posix()

    raw_host_local = _is_host_local_absolute(raw_destination)
    try:
        parsed = urlsplit(raw_destination)
        decoded_path = unquote(parsed.path, errors="strict")
    except (UnicodeDecodeError, ValueError):
        return Violation(source_display, line, destination, "destination is not a valid URI")

    if raw_destination.startswith("//") and parsed.netloc:
        return None
    if parsed.scheme and parsed.scheme.lower() != "file" and not raw_host_local:
        return None

    decoded_path = _MARKDOWN_ESCAPE.sub(r"\1", decoded_path)
    host_local = (
        raw_host_local
        or parsed.scheme.lower() == "file"
        or _is_host_local_absolute(decoded_path)
    )
    if host_local:
        if _is_results_markdown(source_relative):
            return None
        return Violation(
            source_display,
            line,
            destination,
            "host-local absolute destination is forbidden outside results/",
        )

    if "\0" in decoded_path:
        return Violation(source_display, line, destination, "destination path is invalid")

    source_path = repository_root / source_relative
    target_path = source_path if not decoded_path else source_path.parent / decoded_path
    lexical_target = Path(os.path.abspath(os.path.normpath(target_path)))
    try:
        relative_target = lexical_target.relative_to(repository_root)
    except ValueError:
        return Violation(source_display, line, destination, "path escapes repository")

    status = _path_status(repository_root, relative_target)
    if status == "case":
        return Violation(
            source_display,
            line,
            destination,
            "path component has incorrect case",
        )
    if status == "missing":
        return Violation(source_display, line, destination, "target does not exist")

    try:
        lexical_target.resolve(strict=True).relative_to(repository_root.resolve(strict=True))
    except ValueError:
        return Violation(source_display, line, destination, "path escapes repository")
    except (FileNotFoundError, OSError):
        return Violation(source_display, line, destination, "target does not exist")
    return None


def check_repository(repository_root: Path) -> tuple[int, list[Violation]]:
    """Check tracked Markdown files beneath *repository_root*."""

    markdown_files = tracked_markdown_files(repository_root)
    violations: list[Violation] = []
    for source_relative in markdown_files:
        source_path = repository_root / source_relative
        try:
            markdown = source_path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError) as error:
            violations.append(
                Violation(
                    source_relative.as_posix(),
                    1,
                    source_relative.as_posix(),
                    f"cannot read tracked Markdown file ({error.__class__.__name__})",
                )
            )
            continue
        for line, destination in extract_destinations(markdown):
            violation = _validate_destination(
                repository_root,
                source_relative,
                line,
                destination,
            )
            if violation is not None:
                violations.append(violation)
    return len(markdown_files), sorted(violations)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        help="Git worktree to inspect (default: discover from the current directory)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start = args.repository_root or Path.cwd()
    try:
        repository_root = discover_repository_root(start.resolve())
        file_count, violations = check_repository(repository_root)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Markdown link check could not run: {error}", file=sys.stderr)
        return 2

    if violations:
        for violation in violations:
            print(violation.render(), file=sys.stderr)
        return 1

    print(f"Markdown link check passed: {file_count} tracked Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
