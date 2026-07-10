#!/usr/bin/env python3
"""导出四个有限元 validation case，并可选调用 MATLAB 求解。"""
from __future__ import annotations

import argparse
import json
import math
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from pgsa_workflow import prepare_output_root, resolve_executable, run_checked


DEFAULT_CASES = (
    "cantilever_hex8_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_small",
    "cantilever_tet4_medium",
)
MANIFEST_NAME = "validation_export_manifest.json"
SCHEMA_VERSION = "validation-export-run-v1"


def split_cases(text: str) -> list[str]:
    cases = [token.strip() for token in text.split(",") if token.strip()]
    if not cases:
        raise ValueError("at least one validation case is required")
    if len(set(cases)) != len(cases):
        raise ValueError(f"duplicate validation case in --cases: {text}")
    unknown = [case for case in cases if case not in DEFAULT_CASES]
    if unknown:
        raise ValueError(f"unsupported validation case(s): {', '.join(unknown)}")
    return cases


def _resolve_user_path(value: Path) -> Path:
    return value.expanduser().resolve()


def resolve_validation_export(value: Path, *, dry_run: bool) -> Path:
    path = _resolve_user_path(value)
    if path.is_dir():
        try:
            return resolve_executable(path, "validation_export")
        except FileNotFoundError:
            if dry_run:
                return path / "bin" / "validation_export"
            raise
    if path.is_file():
        return path
    if path.parent.name == "bin":
        try:
            return resolve_executable(path.parent.parent, "validation_export")
        except FileNotFoundError:
            pass
    if dry_run:
        return path
    raise FileNotFoundError(f"validation_export executable not found: {path}")


def required_files(case_dir: Path, prefix: str) -> dict[str, Path]:
    return {
        "K": case_dir / f"{prefix}_K.mtx",
        "force": case_dir / f"{prefix}_force.csv",
        "bc": case_dir / f"{prefix}_bc.csv",
        "probes": case_dir / f"{prefix}_probes.csv",
        "nodes": case_dir / f"{prefix}_nodes.csv",
        "elements": case_dir / f"{prefix}_elements.csv",
        "metadata": case_dir / f"{prefix}_metadata.json",
    }


def matlab_outputs(case_dir: Path, prefix: str) -> dict[str, Path]:
    return {
        "displacements": case_dir / f"{prefix}_matlab_displacements.csv",
        "probe_summary": case_dir / f"{prefix}_matlab_probe_summary.csv",
        "metadata": case_dir / f"{prefix}_matlab_solve_metadata.json",
    }


def export_command(executable: Path, case_dir: Path, case_name: str) -> list[str]:
    return [
        str(executable),
        "--case",
        case_name,
        "--stiffness-model",
        "linear_elastic_solid",
        "--out-dir",
        str(case_dir),
        "--prefix",
        case_name,
    ]


def _matlab_quote(value: str) -> str:
    return value.replace("'", "''")


def matlab_command(matlab_bin: str, case_dir: Path, case_name: str) -> list[str]:
    scripts_dir = Path(__file__).resolve().parent
    batch = (
        f"addpath('{_matlab_quote(scripts_dir.as_posix())}'); "
        f"solve_validation_export_matlab('{_matlab_quote(case_dir.as_posix())}',"
        f"'{_matlab_quote(case_name)}')"
    )
    return [matlab_bin, "-batch", batch]


def verify_export_files(files: dict[str, Path], case_name: str) -> None:
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise RuntimeError("missing required export file(s): " + ", ".join(missing))
    with files["K"].open(encoding="utf-8") as handle:
        header = handle.readline().strip()
    if header != "%%MatrixMarket matrix coordinate real symmetric":
        raise RuntimeError(f"invalid Matrix Market header for {case_name}: {header!r}")
    metadata = json.loads(files["metadata"].read_text(encoding="utf-8"))
    if metadata.get("case_name") != case_name:
        raise RuntimeError(f"metadata case_name mismatch for {case_name}")
    if metadata.get("stiffness_model") != "linear_elastic_solid":
        raise RuntimeError(f"metadata stiffness_model mismatch for {case_name}")
    if metadata.get("index_base") != 0:
        raise RuntimeError(f"metadata index_base must be zero for {case_name}")
    metadata_files = metadata.get("files", {})
    for key in ("K", "force", "bc", "probes", "nodes", "elements"):
        if metadata_files.get(key) != files[key].name:
            raise RuntimeError(f"metadata file mapping mismatch for {case_name}: {key}")


def verify_matlab_outputs(outputs: dict[str, Path], case_name: str) -> None:
    missing = [str(path) for path in outputs.values() if not path.is_file()]
    if missing:
        raise RuntimeError(
            f"MATLAB did not produce required outputs for {case_name}: "
            + ", ".join(missing)
        )
    try:
        metadata = json.loads(outputs["metadata"].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"invalid MATLAB solve metadata for {case_name}: {exc}") from exc
    if metadata.get("status") != "PASS":
        raise RuntimeError(
            f"MATLAB solve metadata status must be PASS for {case_name}, "
            f"got {metadata.get('status')!r}"
        )
    residual = metadata.get("residual")
    if not isinstance(residual, dict):
        raise RuntimeError(f"MATLAB solve metadata residual is missing for {case_name}")
    for key in ("absolute_free_l2", "relative_free_l2", "effective_rhs_l2"):
        value = residual.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0.0:
            raise RuntimeError(
                f"MATLAB solve metadata residual.{key} must be finite and non-negative "
                f"for {case_name}, got {value!r}"
            )


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _case_record(
    case_name: str,
    out_root: Path,
    executable: Path,
    *,
    run_matlab: bool,
    matlab_bin: str,
) -> dict[str, object]:
    case_dir = out_root / case_name
    files = required_files(case_dir, case_name)
    outputs = matlab_outputs(case_dir, case_name)
    return {
        "case": case_name,
        "out_dir": str(case_dir),
        "prefix": case_name,
        "files": {key: str(path) for key, path in files.items()},
        "export": {
            "status": "PENDING",
            "command": export_command(executable, case_dir, case_name),
        },
        "matlab": {
            "requested": run_matlab,
            "mode": "solver-requested" if run_matlab else "export-only",
            "status": "PENDING" if run_matlab else "SKIPPED",
            "reason": "requested" if run_matlab else "not_requested",
            "command": matlab_command(matlab_bin, case_dir, case_name)
            if run_matlab
            else None,
            "outputs": {key: str(path) for key, path in outputs.items()},
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-export", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--cases", default=",".join(DEFAULT_CASES))
    parser.add_argument("--run-matlab", action="store_true")
    parser.add_argument("--matlab-bin", default="matlab")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cases = split_cases(args.cases)
    root = Path(__file__).resolve().parents[1]
    out_root = _resolve_user_path(args.out_root)
    executable = resolve_validation_export(args.validation_export, dry_run=args.dry_run)
    records = [
        _case_record(
            case_name,
            out_root,
            executable,
            run_matlab=args.run_matlab,
            matlab_bin=args.matlab_bin,
        )
        for case_name in cases
    ]

    if args.dry_run:
        for record in records:
            print("+", shlex.join(record["export"]["command"]))
            matlab = record["matlab"]
            if matlab["requested"]:
                print("+", shlex.join(matlab["command"]))
        return 0

    prepare_output_root(
        out_root,
        args.overwrite,
        root,
        (*DEFAULT_CASES, MANIFEST_NAME),
    )
    manifest_path = out_root / MANIFEST_NAME
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "commit_sha": _git_commit(root),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "validation_export": str(executable),
        "stiffness_model": "linear_elastic_solid",
        "run_mode": "export-and-matlab" if args.run_matlab else "export-only",
        "run_status": "PENDING",
        "cases": records,
    }
    _write_manifest(manifest_path, manifest)

    try:
        for record in records:
            export = record["export"]
            export["status"] = "RUNNING"
            _write_manifest(manifest_path, manifest)
            try:
                run_checked(export["command"], root)
                files = {key: Path(path) for key, path in record["files"].items()}
                verify_export_files(files, record["case"])
            except Exception as exc:
                export["status"] = "FAIL"
                export["error"] = str(exc)
                matlab = record["matlab"]
                if matlab["requested"]:
                    matlab["status"] = "SKIPPED"
                    matlab["reason"] = "export_failed"
                    matlab["mode"] = "solver-not-executed"
                manifest["run_status"] = "FAIL"
                _write_manifest(manifest_path, manifest)
                raise
            export["status"] = "PASS"
            _write_manifest(manifest_path, manifest)

            matlab = record["matlab"]
            if matlab["requested"]:
                matlab["status"] = "RUNNING"
                matlab["mode"] = "solver-running"
                _write_manifest(manifest_path, manifest)
                try:
                    run_checked(matlab["command"], root)
                    outputs = {
                        key: Path(path) for key, path in matlab["outputs"].items()
                    }
                    verify_matlab_outputs(outputs, record["case"])
                except Exception as exc:
                    matlab["status"] = "FAIL"
                    matlab["mode"] = "solver-failed"
                    matlab["error"] = str(exc)
                    manifest["run_status"] = "FAIL"
                    _write_manifest(manifest_path, manifest)
                    raise
                matlab["status"] = "PASS"
                matlab["mode"] = "solver-executed"
                _write_manifest(manifest_path, manifest)
    except Exception:
        raise

    manifest["run_status"] = (
        "SOLVER_RUN_COMPLETE" if args.run_matlab else "EXPORT_COMPLETE"
    )
    _write_manifest(manifest_path, manifest)
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
