#!/usr/bin/env python3
"""Inspect the current CPU platform before running PGSA benchmarks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cross_platform_schema import current_platform_metadata


def render_markdown(metadata: dict) -> str:
    statuses = metadata.get("core_profile_status", {})
    lines = [
        "# CPU Platform Inspection",
        "",
        f"- OS: `{metadata.get('os', '')}`",
        f"- Arch: `{metadata.get('arch', '')}`",
        f"- CPU model: `{metadata.get('cpu_model', '')}`",
        f"- physical_cores: `{metadata.get('physical_cores', 0)}`",
        f"- logical_cores: `{metadata.get('logical_cores', 0)}`",
        f"- performance_core_count: `{metadata.get('performance_core_count', 0)}`",
        f"- efficiency_core_count: `{metadata.get('efficiency_core_count', 0)}`",
        f"- affinity_control: `{metadata.get('affinity_control', 'unknown')}`",
        "",
        "## Required AI Pre-Run Statement",
        "",
        "Before running benchmarks on this CPU, state the detected core model and which profiles will be run. If P/E-only profiles are unavailable or not applicable, state why.",
        "",
        "## Recommended Profiles",
        "",
        "| Profile | Status |",
        "| --- | --- |",
    ]
    for profile in ("full_host", "performance_core_only", "efficiency_core_only"):
        lines.append(f"| `{profile}` | `{statuses.get(profile, 'unknown')}` |")
    evidence = metadata.get("evidence") or []
    if evidence:
        lines.extend(["", "## Evidence", ""])
        lines.extend(f"- {item}" for item in evidence)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--markdown", dest="markdown_path", default=None)
    args = parser.parse_args()

    metadata = current_platform_metadata()
    payload = json.dumps(metadata, indent=2, ensure_ascii=False)
    print(payload)
    if args.json_path:
        Path(args.json_path).write_text(payload + "\n", encoding="utf-8")
    if args.markdown_path:
        Path(args.markdown_path).write_text(render_markdown(metadata), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
