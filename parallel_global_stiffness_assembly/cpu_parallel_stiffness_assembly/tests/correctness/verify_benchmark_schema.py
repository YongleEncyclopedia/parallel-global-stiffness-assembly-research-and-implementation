#!/usr/bin/env python3
"""Verify benchmark_assembly emits the cross-platform schema fields."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_benchmark_schema.py BENCHMARK_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "schema_smoke.csv"
    json_path = out_dir / "schema_smoke.json"
    md_path = out_dir / "schema_smoke.md"

    subprocess.run(
        [
            str(exe),
            "--mesh",
            "cube",
            "--element",
            "tet4",
            "--nx",
            "1",
            "--ny",
            "1",
            "--nz",
            "1",
            "--case-name",
            "schema_smoke",
            "--stiffness-model",
            "linear_elastic_solid",
            "--algo",
            "serial,lock_guard",
            "--threads",
            "1",
            "--schema-version",
            "pgsa-cross-platform-v1",
            "--platform-id",
            "unit-test-platform",
            "--run-profile",
            "full_host",
            "--profile-note",
            "unit test profile",
            "--env-group",
            "default",
            "--json",
            str(json_path),
            "--csv",
            str(csv_path),
            "--summary-md",
            str(md_path),
        ],
        check=True,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pgsa-cross-platform-v1"
    assert payload["platform_id"] == "unit-test-platform"
    assert payload["run_profile"] == "full_host"
    assert payload["profile_note"] == "unit test profile"
    assert payload["env_group"] == "default"
    assert payload["baseline"]["case_name"] == "schema_smoke"
    assert payload["baseline"]["kernel"] == "linear_elastic_solid"
    assert payload["platform"]["os"]
    assert payload["platform"]["arch"]
    assert payload["platform"]["compiler"]
    assert payload["platform"]["openmp"]
    algorithms = {record["algorithm"] for record in payload["records"]}
    assert "cpu_serial" in algorithms
    assert "cpu_lock_guard" in algorithms
    assert payload["records"][0]["schema_version"] == "pgsa-cross-platform-v1"
    assert payload["records"][0]["platform_id"] == "unit-test-platform"
    assert payload["records"][0]["run_profile"] == "full_host"
    assert payload["records"][0]["env_group"] == "default"

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        first = next(reader)
    for field in (
        "schema_version",
        "platform_id",
        "run_profile",
        "profile_note",
        "env_group",
    ):
        assert field in first, f"missing CSV schema field: {field}"
    assert first["schema_version"] == "pgsa-cross-platform-v1"
    assert first["platform_id"] == "unit-test-platform"
    assert first["run_profile"] == "full_host"
    assert first["env_group"] == "default"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
