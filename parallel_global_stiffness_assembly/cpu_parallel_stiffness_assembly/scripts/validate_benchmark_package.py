#!/usr/bin/env python3
"""Validate one or more cross-platform benchmark packages."""
from __future__ import annotations

import argparse
from pathlib import Path

from cross_platform_schema import load_package, validate_packages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packages", nargs="+", help="benchmark_package.json files or package directories")
    args = parser.parse_args()

    packages = [load_package(Path(path)) for path in args.packages]
    result = validate_packages(packages)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.errors:
        return 1
    print(f"[OK] validated {len(packages)} package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
