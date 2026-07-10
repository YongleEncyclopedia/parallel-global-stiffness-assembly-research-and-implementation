#!/usr/bin/env python3
"""Validate the exact test and outcome counts in CTest JUnit XML."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple


class JUnitSummary(NamedTuple):
    tests: int
    failures: int
    errors: int
    skipped: int
    not_run: int


def read_junit_summary(path: Path) -> JUnitSummary:
    """Count testcases and non-passing outcomes in a JUnit document."""

    root = ET.parse(path).getroot()
    testcases = list(root.iter("testcase"))
    return JUnitSummary(
        tests=len(testcases),
        failures=sum(case.find("failure") is not None for case in testcases),
        errors=sum(case.find("error") is not None for case in testcases),
        skipped=sum(case.find("skipped") is not None for case in testcases),
        not_run=sum(
            case.get("status", "").lower().replace("-", "").replace("_", "")
            == "notrun"
            for case in testcases
        ),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--expected-tests", required=True, type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = read_junit_summary(args.junit)
    violations: list[str] = []
    if summary.tests != args.expected_tests:
        violations.append(
            f"expected {args.expected_tests} tests, found {summary.tests}"
        )
    if summary.failures:
        violations.append(f"failures: {summary.failures}")
    if summary.errors:
        violations.append(f"errors: {summary.errors}")
    if summary.skipped:
        violations.append(f"skipped: {summary.skipped}")
    if summary.not_run:
        violations.append(f"not-run: {summary.not_run}")

    if violations:
        print("CTest JUnit validation failed:", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1

    print(f"CTest JUnit validation passed: {summary.tests} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
