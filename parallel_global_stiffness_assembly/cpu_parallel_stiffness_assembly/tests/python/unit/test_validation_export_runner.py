from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


CPU_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = CPU_ROOT / "scripts" / "run_validation_export.py"
sys.path.insert(0, str(CPU_ROOT / "scripts"))
DEFAULT_CASES = (
    "cantilever_hex8_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_small",
    "cantilever_tet4_medium",
)


def load_runner() -> ModuleType:
    if not RUNNER_PATH.is_file():
        raise AssertionError(f"missing validation runner: {RUNNER_PATH}")
    spec = importlib.util.spec_from_file_location("run_validation_export", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load validation runner: {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_build(root: Path) -> tuple[Path, Path]:
    build_dir = root / "build"
    executable = build_dir / "bin" / "Release" / "validation_export.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    return build_dir, executable.resolve()


def materialize_export(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    argv = [str(part) for part in command]
    if "--case" in argv:
        case_name = argv[argv.index("--case") + 1]
        out_dir = Path(argv[argv.index("--out-dir") + 1])
        prefix = argv[argv.index("--prefix") + 1]
        out_dir.mkdir(parents=True, exist_ok=True)
        names = {
            "K": f"{prefix}_K.mtx",
            "force": f"{prefix}_force.csv",
            "bc": f"{prefix}_bc.csv",
            "probes": f"{prefix}_probes.csv",
            "nodes": f"{prefix}_nodes.csv",
            "elements": f"{prefix}_elements.csv",
            "metadata": f"{prefix}_metadata.json",
        }
        (out_dir / names["K"]).write_text(
            "%%MatrixMarket matrix coordinate real symmetric\n1 1 1\n1 1 1\n",
            encoding="utf-8",
        )
        for key in ("force", "bc", "probes", "nodes", "elements"):
            (out_dir / names[key]).write_text("fixture\n", encoding="utf-8")
        (out_dir / names["metadata"]).write_text(
            json.dumps(
                {
                    "case_name": case_name,
                    "stiffness_model": "linear_elastic_solid",
                    "index_base": 0,
                    "files": {
                        "K": names["K"],
                        "force": names["force"],
                        "bc": names["bc"],
                        "probes": names["probes"],
                        "nodes": names["nodes"],
                        "elements": names["elements"],
                    },
                }
            ),
            encoding="utf-8",
        )
    elif "-batch" in argv:
        batch = argv[argv.index("-batch") + 1]
        match = re.search(
            r"solve_validation_export_matlab\('([^']*)','([^']*)'\)", batch
        )
        if match is None:
            raise AssertionError(f"unexpected MATLAB batch command: {batch}")
        out_dir = Path(match.group(1))
        prefix = match.group(2)
        (out_dir / f"{prefix}_matlab_displacements.csv").write_text(
            "node,ux,uy,uz,umag\n0,0,0,0,0\n", encoding="utf-8"
        )
        (out_dir / f"{prefix}_matlab_probe_summary.csv").write_text(
            "name,node,ux,uy,uz,umag\nroot_center,0,0,0,0,0\n",
            encoding="utf-8",
        )
        (out_dir / f"{prefix}_matlab_solve_metadata.json").write_text(
            json.dumps(
                {
                    "schema_version": "matlab-validation-solve-v1",
                    "status": "PASS",
                    "residual": {
                        "absolute_free_l2": 0.0,
                        "relative_free_l2": 0.0,
                        "effective_rhs_l2": 1.0,
                    },
                }
            ),
            encoding="utf-8",
        )
    return subprocess.CompletedProcess(argv, 0)


class ValidationExportRunnerTests(unittest.TestCase):
    def test_default_dry_run_lists_four_physical_exports_without_output(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_root = root / "validation"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = runner.main(
                    [
                        "--validation-export",
                        str(root / "missing-validation-export"),
                        "--out-root",
                        str(out_root),
                        "--dry-run",
                    ]
                )

            rendered = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertFalse(out_root.exists())
            for case_name in DEFAULT_CASES:
                self.assertIn(f"--case {case_name}", rendered)
            self.assertEqual(rendered.count("--stiffness-model linear_elastic_solid"), 4)
            self.assertNotIn("--kernel", rendered)
            self.assertNotIn("simplified", rendered)
            self.assertNotIn("SOLVER_RUN_COMPLETE", rendered)
            self.assertNotIn("solver_validation_status", rendered)

    def test_export_only_writes_seven_files_and_explicit_skipped_matlab_state(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, executable = make_build(root)
            out_root = root / "validation"
            with mock.patch.object(
                runner, "run_checked", side_effect=materialize_export
            ) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = runner.main(
                        [
                            "--validation-export",
                            str(build_dir),
                            "--out-root",
                            str(out_root),
                        ]
                    )

            self.assertEqual(result, 0)
            self.assertEqual(run.call_count, 4)
            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["schema_version"], "validation-export-run-v1")
            self.assertEqual(manifest["validation_export"], str(executable))
            self.assertEqual(manifest["run_mode"], "export-only")
            self.assertEqual([case["case"] for case in manifest["cases"]], list(DEFAULT_CASES))
            for case in manifest["cases"]:
                self.assertEqual(case["export"]["status"], "PASS")
                self.assertEqual(case["matlab"]["mode"], "export-only")
                self.assertEqual(case["matlab"]["status"], "SKIPPED")
                self.assertEqual(len(case["files"]), 7)
                self.assertTrue(all(Path(path).is_file() for path in case["files"].values()))
            self.assertNotIn("solver_validation_status", manifest)

    def test_run_matlab_records_solver_outputs_and_pass_state(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"
            with mock.patch.object(
                runner, "run_checked", side_effect=materialize_export
            ) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    runner.main(
                        [
                            "--validation-export",
                            str(build_dir),
                            "--out-root",
                            str(out_root),
                            "--cases",
                            "cantilever_tet4_small",
                            "--run-matlab",
                            "--matlab-bin",
                            "custom-matlab",
                        ]
                    )

            self.assertEqual(run.call_count, 2)
            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["run_mode"], "export-and-matlab")
            matlab = manifest["cases"][0]["matlab"]
            self.assertEqual(matlab["status"], "PASS")
            self.assertEqual(matlab["mode"], "solver-executed")
            self.assertEqual(len(matlab["outputs"]), 3)
            matlab_command = run.call_args_list[1].args[0]
            self.assertEqual(matlab_command[0], "custom-matlab")
            self.assertEqual(matlab_command[1], "-batch")

    def test_first_export_failure_leaves_remaining_cases_pending(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"
            with mock.patch.object(
                runner, "run_checked", side_effect=RuntimeError("synthetic export failure")
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "synthetic export failure"):
                        runner.main(
                            [
                                "--validation-export",
                                str(build_dir),
                                "--out-root",
                                str(out_root),
                            ]
                        )

            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                [case["export"]["status"] for case in manifest["cases"]],
                ["FAIL", "PENDING", "PENDING", "PENDING"],
            )
            self.assertTrue(
                all(case["matlab"]["status"] == "SKIPPED" for case in manifest["cases"])
            )

    def test_requested_matlab_is_skipped_when_export_fails(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"
            with mock.patch.object(
                runner, "run_checked", side_effect=RuntimeError("synthetic export failure")
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "synthetic export failure"):
                        runner.main(
                            [
                                "--validation-export",
                                str(build_dir),
                                "--out-root",
                                str(out_root),
                                "--cases",
                                "cantilever_tet4_small",
                                "--run-matlab",
                            ]
                        )

            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            matlab = manifest["cases"][0]["matlab"]
            self.assertEqual(manifest["run_status"], "FAIL")
            self.assertEqual(matlab["status"], "SKIPPED")
            self.assertEqual(matlab["reason"], "export_failed")
            self.assertEqual(matlab["mode"], "solver-not-executed")
            self.assertNotIn("solver_validation_status", manifest)

    def test_invalid_matlab_metadata_marks_solver_failed(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"

            def invalid_metadata(
                command: list[str], cwd: Path
            ) -> subprocess.CompletedProcess[str]:
                result = materialize_export(command, cwd)
                argv = [str(part) for part in command]
                if "-batch" in argv:
                    case_dir = out_root / "cantilever_hex8_small"
                    metadata = case_dir / "cantilever_hex8_small_matlab_solve_metadata.json"
                    metadata.write_text(
                        json.dumps(
                            {
                                "status": "PASS",
                                "residual": {
                                    "absolute_free_l2": -1.0,
                                    "relative_free_l2": 0.0,
                                    "effective_rhs_l2": 1.0,
                                },
                            }
                        ),
                        encoding="utf-8",
                    )
                return result

            with mock.patch.object(runner, "run_checked", side_effect=invalid_metadata):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "residual"):
                        runner.main(
                            [
                                "--validation-export",
                                str(build_dir),
                                "--out-root",
                                str(out_root),
                                "--cases",
                                "cantilever_hex8_small",
                                "--run-matlab",
                            ]
                        )

            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["run_status"], "FAIL")
            self.assertEqual(manifest["cases"][0]["matlab"]["status"], "FAIL")
            self.assertEqual(
                manifest["cases"][0]["matlab"]["mode"], "solver-failed"
            )
            self.assertNotIn("solver_validation_status", manifest)

    def test_missing_required_export_file_marks_case_failed(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"

            def incomplete(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
                result = materialize_export(command, cwd)
                argv = [str(part) for part in command]
                out_dir = Path(argv[argv.index("--out-dir") + 1])
                prefix = argv[argv.index("--prefix") + 1]
                (out_dir / f"{prefix}_elements.csv").unlink()
                return result

            with mock.patch.object(runner, "run_checked", side_effect=incomplete):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "missing required export"):
                        runner.main(
                            [
                                "--validation-export",
                                str(build_dir),
                                "--out-root",
                                str(out_root),
                                "--cases",
                                "cantilever_hex8_small",
                            ]
                        )
            manifest = json.loads(
                (out_root / "validation_export_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["cases"][0]["export"]["status"], "FAIL")

    def test_existing_output_requires_overwrite_and_preserves_unrelated_files(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_dir, _ = make_build(root)
            out_root = root / "validation"
            out_root.mkdir()
            unrelated = out_root / "keep.txt"
            unrelated.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                runner.main(
                    [
                        "--validation-export",
                        str(build_dir),
                        "--out-root",
                        str(out_root),
                    ]
                )

            with mock.patch.object(
                runner, "run_checked", side_effect=materialize_export
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    runner.main(
                        [
                            "--validation-export",
                            str(build_dir),
                            "--out-root",
                            str(out_root),
                            "--cases",
                            "cantilever_hex8_small",
                            "--overwrite",
                        ]
                    )
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")

    def test_invalid_or_duplicate_case_selection_is_rejected(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for cases in ("unknown_case", "cantilever_hex8_small,cantilever_hex8_small"):
                with self.subTest(cases=cases):
                    with self.assertRaises(ValueError):
                        runner.main(
                            [
                                "--validation-export",
                                str(root / "missing"),
                                "--out-root",
                                str(root / "out"),
                                "--cases",
                                cases,
                                "--dry-run",
                            ]
                        )


if __name__ == "__main__":
    unittest.main()
