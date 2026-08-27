#!/usr/bin/env python3
"""WindHub 一键示例的路径、构建和结果文本测试。"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "examples" / "run_windhub.py"
POWERSHELL_SCRIPT = DEMO_ROOT / "examples" / "run_windhub.ps1"


def load_example():
    specification = importlib.util.spec_from_file_location(
        "csc3_windhub_example_test",
        SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("无法加载 WindHub 示例脚本")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


example = load_example()


class PathAndBuildTests(unittest.TestCase):
    def test_discovers_repository_and_shared_windhub_from_script_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "pgsa"
            script = (
                repository
                / "demos"
                / "csc3_symmetric_assembly_demo"
                / "examples"
                / "run_windhub.py"
            )
            paths = example.discover_paths(script)
            resolved_repository = repository.resolve()
        self.assertEqual(
            paths.demo_root,
            resolved_repository / "demos" / "csc3_symmetric_assembly_demo",
        )
        self.assertEqual(paths.repository_root, resolved_repository)
        self.assertEqual(
            paths.input_path,
            resolved_repository / "examples" / "3d-WindTurbineHub.inp",
        )

    def test_missing_cache_points_back_to_readme_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "README 的五行命令"):
                example._cache_entries(Path(temporary) / "CMakeCache.txt")

    def test_cache_parser_keeps_generator_and_openmp_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "CMakeCache.txt"
            path.write_text(
                "# comment\n"
                "CMAKE_GENERATOR:INTERNAL=Visual Studio 17 2022\n"
                "OpenMP_CXX_FLAGS:STRING=-openmp\n",
                encoding="utf-8",
            )
            entries = example._cache_entries(path)
        self.assertEqual(entries["CMAKE_GENERATOR"], "Visual Studio 17 2022")
        self.assertEqual(entries["OpenMP_CXX_FLAGS"], "-openmp")

    def test_release_build_uses_existing_build_and_benchmark_target(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="MSBuild version 17.14\n",
        )
        with mock.patch.object(example.subprocess, "run", return_value=completed) as run:
            output = example._build_release(Path("C:/src/demo/build"), Path("C:/src/demo"))
        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "cmake",
                "--build",
                str(Path("C:/src/demo/build")),
                "--config",
                "Release",
                "--target",
                "csc3_demo_benchmark",
            ],
        )
        self.assertIn("MSBuild", output)

    def test_missing_git_has_a_specific_chinese_error(self) -> None:
        with mock.patch.object(example.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Git for Windows"):
                example._git_tools(Path("."))

    def test_missing_git_lfs_is_not_reported_as_a_dirty_worktree(self) -> None:
        with (
            mock.patch.object(example.shutil, "which", return_value="git.exe"),
            mock.patch.object(
                example,
                "_run_text",
                side_effect=[
                    "git version 2.51.0.windows.1",
                    example.ExampleError("git: 'lfs' is not a git command"),
                ],
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "安装 Git LFS"):
                example._git_tools(Path("."))

    def test_output_root_is_unique_build_artifact_path(self) -> None:
        path = example._output_root(
            Path("C:/src/demo/build"),
            datetime(2026, 8, 27, 13, 45, 6, 123456),
        )
        self.assertEqual(
            path,
            Path("C:/src/demo/build/example-results/20260827-134506-123456"),
        )

    def test_powershell_launcher_has_no_user_parameters(self) -> None:
        text = POWERSHELL_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("param()", text)
        self.assertIn('Join-Path $PSScriptRoot "run_windhub.py"', text)
        self.assertIn("py.exe", text)
        self.assertIn("python.exe", text)
        self.assertNotIn("repository-root", text)
        self.assertNotIn("maximum-threads", text)
        self.assertIn("Stop-WithFailure", text)
        self.assertIn("sys.version_info < (3, 10)", text)
        self.assertIn("struct.calcsize('P') != 8", text)
        self.assertIn("32 位 Python", text)
        self.assertIn("failure.json", text)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell test")
    def test_missing_python_is_chinese_and_keeps_a_failure_record(self) -> None:
        powershell = (
            Path(os.environ["SystemRoot"])
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "powershell.exe"
        )
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ)
            environment["Path"] = ""
            environment["TEMP"] = temporary
            environment["TMP"] = temporary
            completed = subprocess.run(
                [
                    str(powershell),
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL_SCRIPT),
                ],
                check=False,
                env=environment,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            records = list(Path(temporary).rglob("failure.json"))
            self.assertEqual(completed.returncode, 1)
            self.assertIn("没有找到 Python", completed.stderr)
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text(encoding="utf-8-sig"))
            self.assertEqual(record["status"], "FAIL")
            self.assertEqual(record["error_type"], "PythonPreflight")

    def test_python_failure_record_keeps_the_chinese_cause(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "result"
            path = example._write_failure_record(
                root,
                example.ExampleError("实际线程数与计划不符。"),
            )
            record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "FAIL")
        self.assertEqual(record["message"], "实际线程数与计划不符。")

    def test_missing_build_keeps_failure_record_outside_the_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "pgsa"
            paths = example.ExamplePaths(
                demo_root=repository / "demo",
                repository_root=repository,
                build_root=repository / "demo" / "build",
                input_path=repository / "examples" / "windhub.inp",
            )
            proposed = paths.build_root / "example-results" / "candidate"
            with mock.patch.object(example.tempfile, "gettempdir", return_value=str(root)):
                failure_root = example._failure_root(paths, proposed)
                failure_path = example._write_failure_record(
                    failure_root,
                    example.ExampleError("没有找到 build/CMakeCache.txt。"),
                )
            self.assertFalse(paths.build_root.exists())
            self.assertTrue(failure_path.is_file())
            self.assertIn("csc3-windhub-example-failures", str(failure_path))

    def test_main_preserves_preflight_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "pgsa"
            build_root = repository / "demo" / "build"
            build_root.mkdir(parents=True)
            paths = example.ExamplePaths(
                demo_root=repository / "demo",
                repository_root=repository,
                build_root=build_root,
                input_path=repository / "examples" / "windhub.inp",
            )
            output_root = build_root / "example-results" / "candidate"
            error = example.ExampleError("实际线程数与本机不符。")
            standard_error = io.StringIO()
            with (
                mock.patch.object(example, "discover_paths", return_value=paths),
                mock.patch.object(example, "_output_root", return_value=output_root),
                mock.patch.object(example, "run_example", side_effect=error),
                redirect_stderr(standard_error),
            ):
                exit_code = example.main([])
            record = json.loads(
                (output_root / "failure.json").read_text(encoding="utf-8")
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("实际线程数", standard_error.getvalue())
        self.assertIn("失败记录", standard_error.getvalue())
        self.assertEqual(record["status"], "FAIL")

    def test_main_records_keyboard_interrupt_and_returns_130(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "pgsa"
            build_root = repository / "demo" / "build"
            build_root.mkdir(parents=True)
            paths = example.ExamplePaths(
                demo_root=repository / "demo",
                repository_root=repository,
                build_root=build_root,
                input_path=repository / "examples" / "windhub.inp",
            )
            output_root = build_root / "example-results" / "interrupted"
            standard_error = io.StringIO()
            with (
                mock.patch.object(example, "discover_paths", return_value=paths),
                mock.patch.object(example, "_output_root", return_value=output_root),
                mock.patch.object(example, "run_example", side_effect=KeyboardInterrupt),
                redirect_stderr(standard_error),
            ):
                exit_code = example.main([])
            record = json.loads(
                (output_root / "failure.json").read_text(encoding="utf-8")
            )
        self.assertEqual(exit_code, 130)
        self.assertIn("当前样本子进程已经停止", standard_error.getvalue())
        self.assertIn("用户中断", record["message"])


class SummaryRenderingTests(unittest.TestCase):
    @staticmethod
    def _statistics(value: float) -> dict[str, float | int]:
        return {
            "sample_count": 7,
            "median": value,
            "mean": value,
            "population_standard_deviation": 0.0,
            "minimum": value,
            "maximum": value,
            "coefficient_of_variation": 0.02,
        }

    def _summary(self, maximum_threads: int = 2) -> dict[str, object]:
        return {
            "status": "PASS",
            "case_sizes": {
                "node_count": 228384,
                "element_count": 1113684,
                "dof_count": 685152,
                "nnz": 14093676,
            },
            "correctness": {
                "status": "PASS",
                "relative_frobenius_error_maximum": 1.0e-16,
            },
            "configuration": {
                "thread_counts": list(range(1, maximum_threads + 1)),
                "maximum_threads": maximum_threads,
                "warmup_count": 2,
                "repeat_count": 7,
                "sample_process_model": "one_fresh_child_process_per_sample",
                "measured_round_order": "alternating_ascending_descending",
                "samples_are_serialized": True,
            },
            "process_integrity": {
                "expected_sample_count": 9 * maximum_threads,
                "observed_sample_count": 9 * maximum_threads,
                "measured_sample_count_per_thread": 7,
                "unique_sample_ids": True,
                "samples_overlap": False,
                "all_exit_codes_zero": True,
                "all_observed_team_sizes_match": True,
            },
            "memory_definition": {
                "peak_working_set": "GetProcessMemoryInfo.PeakWorkingSetSize",
                "peak_working_set_is_os_measured": True,
            },
            "per_thread": [
                {
                    "thread_count": thread_count,
                    "parallel_symbolic_ms": self._statistics(20.0 / thread_count),
                    "parallel_numeric_ms": self._statistics(10.0 / thread_count),
                    "parallel_total_ms": self._statistics(30.0 / thread_count),
                    "overall_speedup": float(thread_count),
                    "peak_working_set_bytes": self._statistics(
                        5.0 * 1024.0**3
                    ),
                }
                for thread_count in range(1, maximum_threads + 1)
            ],
        }

    @staticmethod
    def _manifest() -> dict[str, object]:
        return {
            "status": "PASS",
            "source": {"commit_sha": "a" * 40},
            "environment": {
                "caption": "Windows 11",
                "version": "10.0",
                "architecture": "64-bit",
                "cpu_model": "Example CPU",
            },
            "toolchain": {
                "compiler": "MSVC 19.44",
                "cmake": "cmake version 4.3.3",
                "cmake_generator": "Visual Studio 17 2022",
                "build_tool": "MSBuild 17.14",
                "openmp_runtime": "vcomp140.dll 14.51",
            },
        }

    def test_markdown_contains_case_protocol_and_every_thread(self) -> None:
        text = example.render_summary_markdown(self._summary(), self._manifest())
        self.assertIn("228384 个节点", text)
        self.assertIn("$W=2$", text)
        self.assertIn("$R=7$", text)
        self.assertIn("| 1 | 20.000 | 10.000 | 30.000", text)
        self.assertIn("| 2 | 10.000 | 5.000 | 15.000", text)
        self.assertIn("5.0000 |", text)
        self.assertIn("不同电脑", text)

    def test_missing_thread_results_fail_instead_of_writing_empty_report(self) -> None:
        summary = self._summary()
        summary["per_thread"] = []
        with self.assertRaisesRegex(RuntimeError, "没有线程数据"):
            example.render_summary_markdown(summary, self._manifest())

    def test_missing_thread_row_is_rejected(self) -> None:
        summary = self._summary(3)
        summary["per_thread"] = summary["per_thread"][:-1]
        with self.assertRaisesRegex(RuntimeError, "线程表不完整"):
            example.render_summary_markdown(summary, self._manifest())

    def test_non_windows_peak_memory_source_is_rejected(self) -> None:
        summary = self._summary()
        summary["memory_definition"] = {
            "peak_working_set": "estimated bytes",
            "peak_working_set_is_os_measured": False,
        }
        with self.assertRaisesRegex(RuntimeError, "Windows 进程接口"):
            example.render_summary_markdown(summary, self._manifest())


class ExampleOrchestrationTests(unittest.TestCase):
    @staticmethod
    def _paths(repository: Path) -> example.ExamplePaths:
        demo_root = repository / "demos" / "csc3_symmetric_assembly_demo"
        return example.ExamplePaths(
            demo_root=demo_root,
            repository_root=repository,
            build_root=demo_root / "build",
            input_path=repository / "examples" / "3d-WindTurbineHub.inp",
        )

    def test_lightweight_runner_receives_full_protocol(self) -> None:
        fixture = SummaryRenderingTests()
        summary = fixture._summary(3)
        manifest = fixture._manifest()
        captured: dict[str, object] = {}

        def write_text(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        def run_benchmark(options) -> int:
            captured["options"] = options
            options.out_dir.mkdir(parents=True)
            sample_count = options.maximum_threads * (options.warmup + options.repeat)
            (options.out_dir / "benchmark_samples.csv").write_text(
                "sample_id\n"
                + "".join(f"fake-{index}\n" for index in range(sample_count)),
                encoding="utf-8",
            )
            (options.out_dir / "benchmark_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False),
                encoding="utf-8",
            )
            run_manifest = dict(manifest)
            run_manifest["schema_version"] = "csc3-demo-windows-process-manifest-v2"
            run_manifest["issue"] = options.issue
            (options.out_dir / "run_manifest.json").write_text(
                json.dumps(run_manifest, ensure_ascii=False),
                encoding="utf-8",
            )
            return 0

        runner = SimpleNamespace(
            WARMUP_COUNT=2,
            REPEAT_COUNT=7,
            _source_provenance=lambda repository_root: {"commit_sha": "a" * 40},
            _input_provenance=lambda input_path, repository_root: {"size_bytes": 1},
            _windows_environment=lambda: {"logical_processor_count": 3},
            run_benchmark=run_benchmark,
            _atomic_write_text=write_text,
            _artifact_records=lambda output_root: [
                {"path": "summary.md", "size_bytes": 1, "sha256": "a" * 64}
            ],
            _canonical_json=lambda value: json.dumps(value, ensure_ascii=False),
        )

        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "pgsa"
            paths = self._paths(repository)
            paths.build_root.mkdir(parents=True)
            benchmark = paths.build_root / "bin" / "csc3_demo_benchmark.exe"
            benchmark.parent.mkdir()
            benchmark.write_bytes(b"fake")
            output_root = paths.build_root / "example-results" / "candidate"
            with (
                mock.patch.object(example.os, "name", "nt"),
                mock.patch.object(
                    example,
                    "_cache_entries",
                    return_value={"CMAKE_GENERATOR": "Visual Studio 17 2022"},
                ),
                mock.patch.object(
                    example,
                    "_compiler_facts",
                    return_value=("MSVC", "19.44", "x64"),
                ),
                mock.patch.object(example, "_load_runner", return_value=runner),
                mock.patch.object(
                    example,
                    "_git_tools",
                    return_value={"git": "git version 2.51", "git_lfs": "git-lfs/3.7"},
                ),
                mock.patch.object(example, "_build_release", return_value="MSBuild 17.14"),
                mock.patch.object(example, "_toolchain_facts", return_value=manifest["toolchain"]),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = example.run_example(paths, output_root)

            markdown = (output_root / "summary.md").read_text(encoding="utf-8")
            sample_lines = (output_root / "benchmark_samples.csv").read_text(
                encoding="utf-8"
            ).splitlines()
            recorded_manifest = json.loads(
                (output_root / "run_manifest.json").read_text(encoding="utf-8")
            )

        options = captured["options"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(options.maximum_threads, 3)
        self.assertEqual(options.warmup, 2)
        self.assertEqual(options.repeat, 7)
        self.assertEqual(9 * options.maximum_threads, 27)
        self.assertEqual(len(sample_lines), 28)
        self.assertEqual(options.issue, 72)
        self.assertEqual(options.source_tools["git_lfs"], "git-lfs/3.7")
        self.assertTrue(options.progress)
        self.assertIsNone(options.result_stream)
        self.assertEqual(
            recorded_manifest["schema_version"],
            "csc3-demo-windows-process-manifest-v2",
        )
        self.assertIn("| 3 |", markdown)

    def test_32_bit_python_is_rejected_before_any_build(self) -> None:
        with (
            mock.patch.object(example.os, "name", "nt"),
            mock.patch.object(example.struct, "calcsize", return_value=4),
        ):
            with self.assertRaisesRegex(RuntimeError, "64 位 Python"):
                example.run_example()

    def test_non_x64_msvc_build_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._paths(Path(temporary) / "pgsa")
            paths.build_root.mkdir(parents=True)
            with (
                mock.patch.object(example.os, "name", "nt"),
                mock.patch.object(
                    example,
                    "_cache_entries",
                    return_value={"CMAKE_GENERATOR": "Visual Studio 17 2022"},
                ),
                mock.patch.object(
                    example,
                    "_compiler_facts",
                    return_value=("MSVC", "19.44", "ARM64"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "MSVC x64"):
                    example.run_example(paths, paths.build_root / "example-results" / "x")

    def test_missing_lfs_entity_gives_copyable_recovery_command(self) -> None:
        runner = SimpleNamespace(
            _source_provenance=lambda repository_root: {"commit_sha": "a" * 40},
            _input_provenance=mock.Mock(side_effect=RuntimeError("LFS 实体不存在")),
        )
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._paths(Path(temporary) / "pgsa")
            paths.build_root.mkdir(parents=True)
            with (
                mock.patch.object(example.os, "name", "nt"),
                mock.patch.object(
                    example,
                    "_cache_entries",
                    return_value={"CMAKE_GENERATOR": "Visual Studio 17 2022"},
                ),
                mock.patch.object(
                    example,
                    "_compiler_facts",
                    return_value=("MSVC", "19.44", "x64"),
                ),
                mock.patch.object(example, "_load_runner", return_value=runner),
                mock.patch.object(
                    example,
                    "_git_tools",
                    return_value={"git": "git version 2.51", "git_lfs": "git-lfs/3.7"},
                ),
                mock.patch.object(example, "_build_release") as build_release,
            ):
                with self.assertRaisesRegex(RuntimeError, "git lfs pull"):
                    example.run_example(paths, paths.build_root / "example-results" / "x")
            build_release.assert_not_called()

    def test_missing_release_executable_fails_before_sampling(self) -> None:
        runner = SimpleNamespace(
            _source_provenance=lambda repository_root: {"commit_sha": "a" * 40},
            _input_provenance=lambda input_path, repository_root: {"size_bytes": 1},
        )
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._paths(Path(temporary) / "pgsa")
            paths.build_root.mkdir(parents=True)
            with (
                mock.patch.object(example.os, "name", "nt"),
                mock.patch.object(
                    example,
                    "_cache_entries",
                    return_value={"CMAKE_GENERATOR": "Visual Studio 17 2022"},
                ),
                mock.patch.object(
                    example,
                    "_compiler_facts",
                    return_value=("MSVC", "19.44", "x64"),
                ),
                mock.patch.object(example, "_load_runner", return_value=runner),
                mock.patch.object(
                    example,
                    "_git_tools",
                    return_value={"git": "git version 2.51", "git_lfs": "git-lfs/3.7"},
                ),
                mock.patch.object(example, "_build_release", return_value="MSBuild 17.14"),
            ):
                with self.assertRaisesRegex(RuntimeError, "没有找到性能程序"):
                    example.run_example(paths, paths.build_root / "example-results" / "x")


if __name__ == "__main__":
    unittest.main()
