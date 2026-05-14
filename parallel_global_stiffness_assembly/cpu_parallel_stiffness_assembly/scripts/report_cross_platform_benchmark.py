#!/usr/bin/env python3
"""Render a normative cross-platform benchmark schema report."""
from __future__ import annotations

import argparse
from pathlib import Path

from cross_platform_schema import load_package, render_cross_platform_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packages", nargs="+", help="benchmark_package.json files or package directories")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    packages = [load_package(Path(path)) for path in args.packages]
    report = render_cross_platform_report(packages)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"[OK] wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
