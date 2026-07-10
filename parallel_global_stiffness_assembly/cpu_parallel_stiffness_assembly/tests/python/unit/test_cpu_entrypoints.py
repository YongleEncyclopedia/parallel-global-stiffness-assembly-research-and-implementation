from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


CPU_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = CPU_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load_script(filename: str, module_name: str) -> ModuleType:
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load entrypoint: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_fake_build(root: Path) -> Path:
    build_dir = root / "build"
    executable = build_dir / "bin" / "benchmark_assembly"
    executable.parent.mkdir(parents=True)
    executable.touch()
    return build_dir


def materialize_benchmark_outputs(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    argv = [str(part) for part in command]
    if "--json" in argv:
        json_path = Path(argv[argv.index("--json") + 1])
        csv_path = Path(argv[argv.index("--csv") + 1])
        summary_path = Path(argv[argv.index("--summary-md") + 1])
        for path in (json_path, csv_path, summary_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        algorithm_names = {
            "serial": "cpu_serial",
            "atomic": "cpu_atomic",
            "lock_guard": "cpu_lock_guard",
            "private_csr": "cpu_private_csr",
            "coo_sort_reduce": "cpu_coo_sort_reduce",
            "graph_coloring": "cpu_graph_coloring",
            "row_owner": "cpu_row_owner",
        }
        algorithms = argv[argv.index("--algo") + 1].split(",")
        if "--threads-list" in argv:
            threads = [
                int(value)
                for value in argv[argv.index("--threads-list") + 1].split(",")
            ]
        else:
            threads = [1, 2]
        records = [
            {
                "algorithm": algorithm_names[algorithm],
                "threads": thread,
                "status": "PASS",
            }
            for thread in threads
            for algorithm in algorithms
        ]
        json_path.write_text(
            json.dumps(
                {
                    "baseline": {"stiffness_model": "linear_elastic_solid"},
                    "platform": {
                        "compiler": "test-compiler",
                        "openmp": "test-openmp",
                    },
                    "records": records,
                }
            ),
            encoding="utf-8",
        )
        csv_path.write_text(
            "stiffness_model,status\nlinear_elastic_solid,PASS\n",
            encoding="utf-8",
        )
        summary_path.write_text("# synthetic summary\n", encoding="utf-8")
    return subprocess.CompletedProcess(argv, 0)


class CpuSmokeEntrypointTests(unittest.TestCase):
    def test_dry_run_covers_tet4_hex8_and_threads_one_two_without_output(self) -> None:
        smoke = load_script("run_cpu_smoke.py", "run_cpu_smoke_dry_run")
        with tempfile.TemporaryDirectory() as tmp:
            out_root = Path(tmp) / "smoke"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = smoke.main(["--dry-run", "--out-root", str(out_root)])

            rendered = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertFalse(out_root.exists())
            self.assertIn("--element tet4", rendered)
            self.assertIn("--element hex8", rendered)
            self.assertIn("--threads-list 1", rendered)
            self.assertIn("--threads-list 1,2", rendered)
            self.assertIn("--stiffness-model linear_elastic_solid", rendered)
            self.assertNotIn("--kernel", rendered)
            self.assertNotIn("simplified", rendered)

    def test_smoke_writes_manifest_only_after_all_records_pass(self) -> None:
        smoke = load_script("run_cpu_smoke.py", "run_cpu_smoke_success")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            build_dir = make_fake_build(tmp_path)
            out_root = tmp_path / "smoke"
            with mock.patch.object(
                smoke, "run_checked", side_effect=materialize_benchmark_outputs
            ) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = smoke.main(
                        [
                            "--skip-build",
                            "--build-dir",
                            str(build_dir),
                            "--out-root",
                            str(out_root),
                        ]
                    )

            self.assertEqual(result, 0)
            self.assertEqual(run.call_count, 4)
            manifest = json.loads(
                (out_root / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["tasks"]), 4)
            self.assertEqual({task["status"] for task in manifest["tasks"]}, {"PASS"})
            self.assertEqual(manifest["threads"], [1, 2])

    def test_smoke_rejects_missing_skipped_or_failed_records(self) -> None:
        smoke = load_script("run_cpu_smoke.py", "run_cpu_smoke_status")
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "result.json"
            for records in (
                [],
                [{"algorithm": "cpu_atomic", "status": "SKIP"}],
                [{"algorithm": "cpu_atomic", "status": "FAIL"}],
                [{"algorithm": "cpu_atomic"}],
            ):
                result_path.write_text(
                    json.dumps(
                        {
                            "baseline": {
                                "stiffness_model": "linear_elastic_solid"
                            },
                            "records": records,
                        }
                    ),
                    encoding="utf-8",
                )
                with self.subTest(records=records):
                    with self.assertRaises(RuntimeError):
                        smoke.assert_all_pass(result_path)

    def test_smoke_failure_manifest_keeps_unstarted_tasks_pending(self) -> None:
        smoke = load_script("run_cpu_smoke.py", "run_cpu_smoke_failure_manifest")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            build_dir = make_fake_build(tmp_path)
            out_root = tmp_path / "smoke"
            with mock.patch.object(
                smoke, "run_checked", side_effect=RuntimeError("synthetic failure")
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                        smoke.main(
                            [
                                "--skip-build",
                                "--build-dir",
                                str(build_dir),
                                "--out-root",
                                str(out_root),
                            ]
                        )

            manifest = json.loads(
                (out_root / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["tasks"]), 4)
            self.assertEqual(
                [task["status"] for task in manifest["tasks"]],
                ["FAIL", "PENDING", "PENDING", "PENDING"],
            )


class CpuExperimentsEntrypointTests(unittest.TestCase):
    def test_dry_run_prefers_existing_multi_config_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / "build"
            release_executable = (
                build_dir / "bin" / "Release" / "benchmark_assembly.exe"
            )
            release_executable.parent.mkdir(parents=True)
            release_executable.touch()
            for filename, module_name in (
                ("run_cpu_smoke.py", "run_cpu_smoke_multiconfig"),
                ("run_cpu_experiments.py", "run_cpu_experiments_multiconfig"),
            ):
                entrypoint = load_script(filename, module_name)
                with self.subTest(filename=filename):
                    self.assertEqual(
                        entrypoint._predicted_executable(build_dir),
                        release_executable.resolve(),
                    )

    def test_thread_selection_flags_are_mutually_exclusive(self) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_mutex"
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                experiments.main(
                    ["--threads-all", "--threads-list", "1,2", "--dry-run"]
                )

    def test_default_dry_run_uses_all_threads_and_canonical_cube_outputs(self) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_default"
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_root = Path(tmp) / "results"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = experiments.main(
                    [
                        "--profile",
                        "cube",
                        "--dry-run",
                        "--out-root",
                        str(out_root),
                    ]
                )

            rendered = stdout.getvalue()
            resolved_out_root = out_root.resolve()
            self.assertEqual(result, 0)
            self.assertFalse(out_root.exists())
            self.assertIn("--threads-all", rendered)
            self.assertNotIn("--threads-list", rendered)
            self.assertIn("--stiffness-model linear_elastic_solid", rendered)
            self.assertIn(
                str(resolved_out_root / "cube_tet4" / "results.csv"), rendered
            )
            self.assertIn(
                str(resolved_out_root / "cube_tet4" / "results.json"), rendered
            )
            self.assertNotIn("--kernel", rendered)
            self.assertNotIn("simplified", rendered)

    def test_threads_list_is_reachable_and_exact(self) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_threads_list"
        )
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                experiments.main(
                    [
                        "--profile",
                        "cube",
                        "--threads-list",
                        "1,2",
                        "--dry-run",
                        "--out-root",
                        str(Path(tmp) / "results"),
                    ]
                )

            rendered = stdout.getvalue()
            self.assertIn("--threads-list 1,2", rendered)
            self.assertNotIn("--threads-all", rendered)

    def test_lfs_pointer_fails_before_output_directory_is_created(self) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_lfs"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pointer = tmp_path / "windhub.inp"
            pointer.write_text(
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:0123456789abcdef\n"
                "size 123\n",
                encoding="utf-8",
            )
            out_root = tmp_path / "results"

            with self.assertRaisesRegex(RuntimeError, "Git LFS pointer"):
                experiments.main(
                    [
                        "--profile",
                        "windhub",
                        "--skip-build",
                        "--windhub-input",
                        str(pointer),
                        "--out-root",
                        str(out_root),
                    ]
                )
            self.assertFalse(out_root.exists())

    def test_standard_profile_writes_canonical_manifest_and_excludes_windhub_coo(
        self,
    ) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_standard"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            build_dir = make_fake_build(tmp_path)
            windhub = tmp_path / "windhub.inp"
            windhub.write_text("*Heading\n*Node\n", encoding="utf-8")
            out_root = tmp_path / "results"
            out_root.mkdir()
            marker = out_root / "stale.txt"
            marker.write_text("stale", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                experiments.main(
                    [
                        "--profile",
                        "standard",
                        "--skip-build",
                        "--build-dir",
                        str(build_dir),
                        "--windhub-input",
                        str(windhub),
                        "--out-root",
                        str(out_root),
                    ]
                )
            self.assertTrue(marker.exists())

            with mock.patch.object(
                experiments, "run_checked", side_effect=materialize_benchmark_outputs
            ) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = experiments.main(
                        [
                            "--profile",
                            "standard",
                            "--skip-build",
                            "--build-dir",
                            str(build_dir),
                            "--windhub-input",
                            str(windhub),
                            "--threads-list",
                            "1,2",
                            "--out-root",
                            str(out_root),
                            "--overwrite",
                        ]
                    )

            self.assertEqual(result, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "stale")
            self.assertTrue((out_root / "cube_tet4" / "results.csv").is_file())
            self.assertTrue((out_root / "windhub" / "results.json").is_file())
            self.assertFalse((out_root / "windhub_coo").exists())
            manifest = json.loads(
                (out_root / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["commit_sha"], subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=CPU_ROOT, text=True
            ).strip())
            self.assertEqual(manifest["build"]["compiler"], "test-compiler")
            self.assertEqual(manifest["build"]["openmp"], "test-openmp")
            self.assertEqual(manifest["threads"], {"mode": "list", "values": [1, 2]})
            self.assertEqual(
                {task["name"] for task in manifest["tasks"]},
                {"cube_tet4", "windhub"},
            )
            benchmark_commands = [
                [str(part) for part in call.args[0]]
                for call in run.call_args_list
                if "--json" in [str(part) for part in call.args[0]]
            ]
            self.assertEqual(len(benchmark_commands), 2)
            cube_command = next(
                command
                for command in benchmark_commands
                if "cube_tet4_8x8x8" in command
            )
            cube_algorithms = cube_command[cube_command.index("--algo") + 1]
            self.assertIn("coo_sort_reduce", cube_algorithms)
            windhub_command = next(
                command
                for command in benchmark_commands
                if "3d-WindTurbineHub" in command
            )
            algorithms = windhub_command[windhub_command.index("--algo") + 1]
            self.assertIn("serial", algorithms)
            self.assertIn("lock_guard", algorithms)
            self.assertNotIn("coo_sort_reduce", algorithms)

    def test_entrypoints_do_not_emit_deprecated_kernel_arguments(self) -> None:
        for filename in ("run_cpu_smoke.py", "run_cpu_experiments.py"):
            source = (SCRIPTS_DIR / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertNotIn('"--kernel"', source)
                self.assertNotIn('"simplified"', source)
                self.assertNotIn('"python3"', source)

    def test_experiment_failure_manifest_keeps_unstarted_tasks_pending(self) -> None:
        experiments = load_script(
            "run_cpu_experiments.py", "run_cpu_experiments_failure_manifest"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            build_dir = make_fake_build(tmp_path)
            windhub = tmp_path / "windhub.inp"
            windhub.write_text("*Heading\n*Node\n", encoding="utf-8")
            out_root = tmp_path / "results"
            with mock.patch.object(
                experiments,
                "run_checked",
                side_effect=RuntimeError("synthetic failure"),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                        experiments.main(
                            [
                                "--profile",
                                "standard",
                                "--skip-build",
                                "--build-dir",
                                str(build_dir),
                                "--windhub-input",
                                str(windhub),
                                "--out-root",
                                str(out_root),
                            ]
                        )

            manifest = json.loads(
                (out_root / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["tasks"]), 2)
            self.assertEqual(
                [task["status"] for task in manifest["tasks"]],
                ["FAIL", "PENDING"],
            )
            self.assertEqual(manifest["postprocess"]["status"], "PENDING")


if __name__ == "__main__":
    unittest.main()
