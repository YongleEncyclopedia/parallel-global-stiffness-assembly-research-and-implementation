#!/usr/bin/env python3
"""Render a PGSA cross-platform schema v2 report."""
from __future__ import annotations

import argparse
from pathlib import Path

from cross_platform_schema_v2 import load_v2_package, render_v2_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="benchmark_package_v2.json or package directory")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    report = render_v2_report(load_v2_package(Path(args.package)))
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"[OK] wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
