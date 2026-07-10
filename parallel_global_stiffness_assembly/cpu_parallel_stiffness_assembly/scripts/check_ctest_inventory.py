#!/usr/bin/env python3
"""Check the exact set of CTest tests carrying a requested label."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def compare_test_names(
    actual: Iterable[str], expected: Iterable[str]
) -> tuple[list[str], list[str]]:
    """Return sorted missing and unexpected test names."""

    actual_names = set(actual)
    expected_names = set(expected)
    return sorted(expected_names - actual_names), sorted(actual_names - expected_names)


def select_labeled_test_names(document: Mapping[str, Any], label: str) -> set[str]:
    """Extract test names carrying *label* from CTest json-v1 output."""

    selected: set[str] = set()
    for test in document.get("tests", []):
        labels: list[str] = []
        for prop in test.get("properties", []):
            if prop.get("name") != "LABELS":
                continue
            value = prop.get("value", [])
            labels.extend(value if isinstance(value, list) else [value])
        if label in labels:
            selected.add(test["name"])
    return selected


def read_expected_names(path: Path) -> set[str]:
    """Read the non-empty one-name-per-line inventory contract."""

    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def read_ctest_document(build_dir: Path) -> Mapping[str, Any]:
    """Run CTest and parse its json-v1 test inventory."""

    result = subprocess.run(
        ["ctest", "--test-dir", str(build_dir), "--show-only=json-v1"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--label", default="ci")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    document = read_ctest_document(args.build_dir)
    actual = select_labeled_test_names(document, args.label)
    expected = read_expected_names(args.expected)
    missing, unexpected = compare_test_names(actual, expected)
    if missing or unexpected:
        print(f"CTest inventory mismatch for label {args.label!r}", file=sys.stderr)
        if missing:
            print("missing:", file=sys.stderr)
            for name in missing:
                print(f"  {name}", file=sys.stderr)
        if unexpected:
            print("unexpected:", file=sys.stderr)
            for name in unexpected:
                print(f"  {name}", file=sys.stderr)
        return 1

    print(f"CTest inventory matches {len(expected)} expected {args.label!r} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
