#!/usr/bin/env python3
"""Smoke-test validation_export outputs for portable cantilever validation."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def require_file(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing output file: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise AssertionError(f"empty output file: {path}")
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_validation_export.py VALIDATION_EXPORT_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            str(exe),
            "--case",
            "cantilever_hex8_small",
            "--kernel",
            "physics_solid",
            "--out-dir",
            str(out_dir),
            "--prefix",
            "hex8_small",
        ],
        check=True,
    )

    mtx = require_file(out_dir / "hex8_small_K.mtx")
    assert mtx.startswith("%%MatrixMarket matrix coordinate real symmetric")
    metadata = json.loads(require_file(out_dir / "hex8_small_metadata.json"))
    assert metadata["case_name"] == "cantilever_hex8_small"
    assert metadata["kernel"] == "physics_solid"
    assert metadata["element_type"] == "hex8"
    assert metadata["boundary"]["fixed_face"] == "x=0"
    assert metadata["load"]["loaded_face"] == "x=L"
    assert metadata["matrix"]["nnz"] > 0

    forces = read_csv(out_dir / "hex8_small_force.csv")
    bcs = read_csv(out_dir / "hex8_small_bc.csv")
    probes = read_csv(out_dir / "hex8_small_probes.csv")
    assert any(abs(float(row["force"])) > 0.0 for row in forces)
    assert bcs and {"node", "dof", "value"} <= set(bcs[0])
    assert {"free_tip_center", "midspan_center"} <= {row["name"] for row in probes}
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
