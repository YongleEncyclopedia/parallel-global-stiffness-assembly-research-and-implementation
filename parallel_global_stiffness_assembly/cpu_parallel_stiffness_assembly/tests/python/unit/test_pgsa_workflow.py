from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


CPU_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = CPU_ROOT / "scripts" / "pgsa_workflow.py"


def load_workflow() -> ModuleType:
    if not WORKFLOW_PATH.is_file():
        raise AssertionError(f"missing workflow helper: {WORKFLOW_PATH}")
    spec = importlib.util.spec_from_file_location("pgsa_workflow", WORKFLOW_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load workflow helper: {WORKFLOW_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PgsaWorkflowTests(unittest.TestCase):
    def test_run_checked_reports_command_cwd_and_exit_code(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            command = [sys.executable, "-c", "raise SystemExit(7)"]

            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(workflow.WorkflowCommandError) as raised:
                    workflow.run_checked(command, cwd)

            self.assertEqual(raised.exception.command, tuple(command))
            self.assertEqual(raised.exception.cwd, cwd.resolve())
            self.assertEqual(raised.exception.returncode, 7)
            message = str(raised.exception)
            self.assertIn("exit code 7", message)
            self.assertIn(str(cwd.resolve()), message)
            self.assertIn(sys.executable, message)

    def test_run_checked_returns_completed_process_on_success(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                result = workflow.run_checked(
                    [sys.executable, "-c", "raise SystemExit(0)"], Path(tmp)
                )
        self.assertEqual(result.returncode, 0)

    def test_resolve_executable_supports_single_and_multi_config_layouts(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp)
            candidates = (
                build_dir / "bin" / "benchmark_assembly",
                build_dir / "bin" / "benchmark_assembly.exe",
                build_dir / "bin" / "Release" / "benchmark_assembly.exe",
            )
            for expected in candidates:
                expected.parent.mkdir(parents=True, exist_ok=True)
                expected.touch()
                self.assertEqual(
                    workflow.resolve_executable(build_dir, "benchmark_assembly"),
                    expected.resolve(),
                )
                expected.unlink()

    def test_resolve_executable_reports_all_checked_paths(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp)
            resolved_build_dir = build_dir.resolve()
            with self.assertRaises(FileNotFoundError) as raised:
                workflow.resolve_executable(build_dir, "benchmark_assembly")
        self.assertIn(
            str(resolved_build_dir / "bin" / "benchmark_assembly"),
            str(raised.exception),
        )
        self.assertIn(
            str(
                resolved_build_dir
                / "bin"
                / "Release"
                / "benchmark_assembly.exe"
            ),
            str(raised.exception),
        )

    def test_configure_and_build_uses_the_same_preset(self) -> None:
        workflow = load_workflow()
        source_dir = CPU_ROOT.resolve()
        with mock.patch.object(workflow, "run_checked") as run:
            build_dir = workflow.configure_and_build(source_dir, "cpu-release")

        self.assertEqual(build_dir, source_dir / "build" / "cpu-release")
        self.assertEqual(
            run.call_args_list,
            [
                mock.call(["cmake", "--preset", "cpu-release"], source_dir),
                mock.call(
                    [
                        "cmake",
                        "--build",
                        "--preset",
                        "cpu-release",
                        "--config",
                        "Release",
                    ],
                    source_dir,
                ),
            ],
        )

    def test_configure_and_build_selects_debug_for_debug_preset(self) -> None:
        workflow = load_workflow()
        source_dir = CPU_ROOT.resolve()
        with mock.patch.object(workflow, "run_checked") as run:
            workflow.configure_and_build(source_dir, "cpu-debug")

        self.assertEqual(
            run.call_args_list[-1],
            mock.call(
                [
                    "cmake",
                    "--build",
                    "--preset",
                    "cpu-debug",
                    "--config",
                    "Debug",
                ],
                source_dir,
            ),
        )

    def test_assert_lfs_materialized_rejects_pointer_and_missing_input(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pointer = tmp_path / "mesh.inp"
            pointer.write_text(
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:0123456789abcdef\n"
                "size 123\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "Git LFS pointer"):
                workflow.assert_lfs_materialized(pointer)
            with self.assertRaises(FileNotFoundError):
                workflow.assert_lfs_materialized(tmp_path / "missing.inp")

    def test_assert_lfs_materialized_accepts_real_input(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            mesh = Path(tmp) / "mesh.inp"
            mesh.write_text("*Heading\n*Node\n", encoding="utf-8")
            self.assertEqual(workflow.assert_lfs_materialized(mesh), mesh.resolve())

    def test_prepare_output_root_only_removes_workflow_owned_entries(self) -> None:
        workflow = load_workflow()
        with tempfile.TemporaryDirectory() as tmp:
            out_root = Path(tmp) / "results"
            owned_dir = out_root / "cube_tet4"
            owned_dir.mkdir(parents=True)
            (owned_dir / "stale.csv").write_text("stale", encoding="utf-8")
            owned_file = out_root / "run_manifest.json"
            owned_file.write_text("{}", encoding="utf-8")
            unrelated = out_root / "keep.txt"
            unrelated.write_text("keep", encoding="utf-8")

            workflow.prepare_output_root(
                out_root,
                overwrite=True,
                source_root=CPU_ROOT,
                owned_entries=("cube_tet4", "run_manifest.json"),
            )

            self.assertTrue(out_root.is_dir())
            self.assertFalse(owned_dir.exists())
            self.assertFalse(owned_file.exists())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")

    def test_prepare_output_root_rejects_protected_roots_without_deleting(self) -> None:
        workflow = load_workflow()
        protected = (CPU_ROOT, CPU_ROOT.parent, Path.home(), Path.cwd())
        with mock.patch.object(workflow.shutil, "rmtree") as remove:
            for path in protected:
                with self.subTest(path=path):
                    with self.assertRaises(ValueError):
                        workflow.prepare_output_root(
                            path,
                            overwrite=True,
                            source_root=CPU_ROOT,
                            owned_entries=("cube_tet4",),
                        )
            remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
