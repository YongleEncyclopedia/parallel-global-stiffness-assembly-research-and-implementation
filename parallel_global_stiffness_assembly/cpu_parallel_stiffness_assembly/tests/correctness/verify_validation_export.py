#!/usr/bin/env python3
"""Smoke-test validation_export files used by solver and visualization workflows."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_case(exe: Path, out_root: Path, case: str, extra: list[str]) -> None:
    out_dir = out_root / case
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(exe),
            "--case",
            case,
            "--E",
            "1",
            "--nu",
            "0.3",
            "--total-load",
            "-1",
            "--load-dof",
            "2",
            "--out-dir",
            str(out_dir),
            "--prefix",
            case,
            *extra,
        ],
        check=True,
    )

    required = [
        f"{case}_K.mtx",
        f"{case}_force.csv",
        f"{case}_bc.csv",
        f"{case}_probes.csv",
        f"{case}_nodes.csv",
        f"{case}_elements.csv",
        f"{case}_metadata.json",
    ]
    for name in required:
        assert (out_dir / name).is_file(), f"missing {name}"

    metadata = json.loads((out_dir / f"{case}_metadata.json").read_text(encoding="utf-8"))
    nodes = read_csv(out_dir / f"{case}_nodes.csv")
    elements = read_csv(out_dir / f"{case}_elements.csv")
    assert len(nodes) == metadata["mesh"]["nodes"]
    assert len(elements) == metadata["mesh"]["elements"]
    assert metadata["mesh"]["dofs"] == 3 * len(nodes)
    assert metadata["files"]["nodes"] == f"{case}_nodes.csv"
    assert metadata["files"]["elements"] == f"{case}_elements.csv"
    assert (out_dir / f"{case}_K.mtx").read_text(encoding="utf-8").startswith(
        "%%MatrixMarket matrix coordinate real symmetric"
    )


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_validation_export.py VALIDATION_EXPORT_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_root = Path(sys.argv[2])
    out_root.mkdir(parents=True, exist_ok=True)

    run_case(exe, out_root, "cantilever_tet4_small", ["--stiffness-model", "linear_elastic_solid"])
    run_case(
        exe,
        out_root,
        "cantilever_hex8_small",
        ["--stiffness-model", "linear_elastic_solid"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
