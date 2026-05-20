#!/usr/bin/env python3
"""Validate a PGSA cross-platform schema v2 package."""
from __future__ import annotations

import argparse
from pathlib import Path

from cross_platform_schema_v2 import load_v2_package, validate_v2_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="benchmark_package_v2.json or package directory")
    args = parser.parse_args()

    result = validate_v2_package(load_v2_package(Path(args.package)))
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.errors:
        return 1
    print("[OK] validated v2 package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
