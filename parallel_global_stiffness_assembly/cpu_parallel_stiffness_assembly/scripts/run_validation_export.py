#!/usr/bin/env python3
"""Run portable validation exports for the next-step correctness workflow."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_CASES = (
    "cantilever_hex8_small",
    "cantilever_tet4_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_medium",
)


def parse_cases(text: str) -> list[str]:
    return [case.strip() for case in text.split(",") if case.strip()]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation-export",
        type=Path,
        default=Path("build/cpu-release/bin/validation_export"),
        help="Path to the validation_export executable.",
    )
    parser.add_argument(
        "--cases",
        default=",".join(DEFAULT_CASES),
        help="Comma-separated validation cases to export.",
    )
    parser.add_argument("--stiffness-model", dest="stiffness_model", default="linear_elastic_solid")
    parser.add_argument("--kernel", dest="stiffness_model", help="deprecated alias for --stiffness-model")
    parser.add_argument("--out-root", type=Path, default=Path("results/validation-export"))
    parser.add_argument("--run-matlab", action="store_true", help="Run MATLAB solver after each export.")
    parser.add_argument("--matlab-bin", default="matlab", help="MATLAB executable for -batch mode.")
    parser.add_argument("--scripts-dir", type=Path, default=Path("scripts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = parse_cases(args.cases)
    if not cases:
        raise SystemExit("no validation cases requested")
    if not args.validation_export.exists():
        raise SystemExit(f"validation_export executable not found: {args.validation_export}")

    args.out_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "validation-export-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "validation_export": str(args.validation_export),
        "stiffness_model": args.stiffness_model,
        "kernel": args.stiffness_model,
        "cases": [],
        "matlab": {"requested": bool(args.run_matlab), "executable": args.matlab_bin},
    }

    for case in cases:
        prefix = case
        case_dir = args.out_root / case
        case_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                str(args.validation_export),
                "--case",
                case,
                "--stiffness-model",
                args.stiffness_model,
                "--out-dir",
                str(case_dir),
                "--prefix",
                prefix,
            ]
        )
        matlab_outputs = []
        if args.run_matlab:
            batch = (
                f"addpath('{args.scripts_dir.as_posix()}'); "
                f"solve_validation_export_matlab('{case_dir.as_posix()}','{prefix}')"
            )
            run([args.matlab_bin, "-batch", batch])
            matlab_outputs = [
                str(case_dir / f"{prefix}_matlab_displacements.csv"),
                str(case_dir / f"{prefix}_matlab_probe_summary.csv"),
            ]

        manifest["cases"].append(
            {
                "case": case,
                "out_dir": str(case_dir),
                "prefix": prefix,
                "files": {
                    "K": str(case_dir / f"{prefix}_K.mtx"),
                    "force": str(case_dir / f"{prefix}_force.csv"),
                    "bc": str(case_dir / f"{prefix}_bc.csv"),
                    "probes": str(case_dir / f"{prefix}_probes.csv"),
                    "metadata": str(case_dir / f"{prefix}_metadata.json"),
                    "matlab": matlab_outputs,
                },
            }
        )

    manifest_path = args.out_root / "validation_export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
