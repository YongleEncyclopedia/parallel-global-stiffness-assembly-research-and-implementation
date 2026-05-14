#!/usr/bin/env python3
"""Package existing thread-scaling results into the cross-platform schema."""
from __future__ import annotations

import argparse
from pathlib import Path

from cross_platform_schema import SCHEMA_VERSION, package_from_thread_scaling_root, validate_package, write_package


def parse_status(values: list[str]) -> dict[str, str]:
    statuses = {
        "full_host": "available",
        "performance_core_only": "unknown",
        "efficiency_core_only": "unknown",
    }
    for item in values:
        if "=" not in item:
            raise ValueError(f"invalid profile status: {item}")
        key, value = item.split("=", 1)
        statuses[key.strip()] = value.strip()
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--platform-id", required=True)
    parser.add_argument("--run-profile", choices=("full_host", "performance_core_only", "efficiency_core_only"), required=True)
    parser.add_argument("--profile-note", default="")
    parser.add_argument("--schema-version", default=SCHEMA_VERSION)
    parser.add_argument("--profile-status", action="append", default=[])
    args = parser.parse_args()

    package = package_from_thread_scaling_root(
        Path(args.source_root),
        platform_id=args.platform_id,
        run_profile=args.run_profile,
        profile_note=args.profile_note,
        core_profile_status=parse_status(args.profile_status),
        schema_version=args.schema_version,
    )
    result = validate_package(package)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    if result.errors:
        for error in result.errors:
            print(f"ERROR: {error}")
        return 1
    path = write_package(package, Path(args.out_dir))
    print(f"[OK] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
