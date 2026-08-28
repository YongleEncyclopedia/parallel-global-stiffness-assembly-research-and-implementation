#!/usr/bin/env python3
"""WindHub Windows 双入口、输出与失败契约测试。"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "examples" / "run_windhub.py"
FULL_ENTRY = DEMO_ROOT / "examples" / "run_windhub.ps1"
DEMO_ENTRY = DEMO_ROOT / "examples" / "run_windhub_demo.ps1"
LAUNCHER = DEMO_ROOT / "examples" / "run_windhub_launcher.ps1"


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


def demo_configuration(thread_count: int = 16) -> dict[str, object]:
    return {
        "thread_count": thread_count,
        "warmup_count": 0,
        "repeat_count": 1,
        "amortization_count": 1,
        "performance_evidence_level": "local-smoke",
        "sample_process_model": "one_fresh_child_process",
        "benchmark_process_count": 1,
        "benchmark_processes_are_concurrent": False,
        "time_definition": {
            "serial_total_ms": "serial_direct_ms",
            "serial_direct_ms": (
                "direct contribution generation, sort, and reduction without a "
                "prebuilt CSC3 structure or scatter"
            ),
            "serial_symbolic_ms": "two-stage phase diagnostic only",
            "serial_numeric_ms": "two-stage phase diagnostic only",
            "parallel_total_ms": "parallel_symbolic_ms + parallel_numeric_ms",
        },
    }


def demo_sample(thread_count: int = 16) -> dict[str, object]:
    return {
        "sample_kind": "measured",
        "round": 1,
        "order_position": 1,
        "thread_count": thread_count,
        "exit_code": 0,
        "symbolic_team_size_observed": thread_count,
        "numeric_team_size_observed": thread_count,
        "input_prepare_ms": 12.5,
        "serial_direct_ms": 200.0,
        "serial_symbolic_ms": 30.0,
        "serial_numeric_ms": 40.0,
        "serial_total_ms": 200.0,
        "parallel_symbolic_ms": 30.0,
        "parallel_numeric_ms": 20.0,
        "parallel_total_ms": 50.0,
        "peak_working_set_bytes": 5 * 1024**3,
        "peak_working_set_source": "GetProcessMemoryInfo.PeakWorkingSetSize",
        "estimated_persistent_bytes": 512 * 1024**2,
        "wall_time_seconds": 1.0,
        "matrix_correctness_status": "PASS",
        "structure_matches": True,
        "scatter_correctness_status": "PASS",
        "symbolic_plan_matches_serial": True,
        "numeric_setup_plan_matches_serial": True,
        "relative_frobenius_error": 1.0e-12,
        "max_absolute_error": 1.0e-10,
        "raw_json_path": "raw/benchmark_summary.json",
    }


def demo_manifest(thread_count: int = 16) -> dict[str, object]:
    return {
        "schema_version": example.DEMO_SCHEMA_VERSION,
        "status": "PASS",
        "mode": example.DEMO_MODE,
        "formal_evidence": False,
        "configuration": demo_configuration(thread_count),
        "case_sizes": {
            "node_count": 228384,
            "element_count": 1113684,
            "dof_count": 685152,
            "nnz": 14093676,
        },
        "correctness": {
            "status": "PASS",
            "structure_matches": True,
            "scatter_status": "PASS",
            "symbolic_plan_matches_serial": True,
            "numeric_setup_plan_matches_serial": True,
            "relative_frobenius_error": 1.0e-12,
            "relative_frobenius_error_threshold": 1.0e-8,
            "max_absolute_error": 1.0e-10,
        },
        "sample": demo_sample(thread_count),
        "overall_speedup": 4.0,
        "memory_definition": {
            "peak_working_set": "GetProcessMemoryInfo.PeakWorkingSetSize",
            "peak_working_set_is_os_measured": True,
            "estimated_persistent_bytes": (
                "owned vector payload capacity estimate; not RSS or peak memory"
            ),
        },
        "source": {"commit_sha": "a" * 40},
        "input": {"repository_relative_path": "examples/3d-WindTurbineHub.inp"},
        "environment": {
            "platform": "windows",
            "caption": "Windows 11",
            "version": "10.0",
            "architecture": "64-bit",
            "cpu_model": "Example CPU",
            "physical_core_count": 8,
            "logical_processor_count": thread_count,
        },
        "toolchain": {"compiler": "MSVC 19.44"},
    }


class PathAndEntryTests(unittest.TestCase):
    def test_discovers_repository_and_package_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository_script = (
                root
                / "repo"
                / "demos"
                / "csc3_symmetric_assembly_demo"
                / "examples"
                / "run_windhub.py"
            )
            repository_paths = example.discover_paths(repository_script)
            package = root / "package"
            package_script = package / "examples" / "run_windhub.py"
            package_script.parent.mkdir(parents=True)
            (package / "PACKAGE_MANIFEST.json").write_text("{}", encoding="utf-8")
            package_paths = example.discover_paths(package_script)

        self.assertEqual(repository_paths.repository_root, (root / "repo").resolve())
        self.assertEqual(
            repository_paths.input_path,
            (root / "repo" / "examples" / "3d-WindTurbineHub.inp").resolve(),
        )
        self.assertEqual(package_paths.repository_root, package.resolve())
        self.assertEqual(
            package_paths.input_path,
            package.resolve() / "examples" / "3d-WindTurbineHub.inp",
        )

    def test_result_directories_are_separate(self) -> None:
        build = Path("C:/src/demo/build")
        now = datetime(2026, 8, 28, 12, 34, 56, 123456)
        self.assertEqual(
            example._output_root(build, now, mode=example.FULL_MODE),
            build / "example-results" / "20260828-123456-123456",
        )
        self.assertEqual(
            example._output_root(build, now, mode=example.DEMO_MODE),
            build / "demo-results" / "20260828-123456-123456",
        )

    def test_only_two_parameter_free_powershell_entries_remain(self) -> None:
        self.assertIn("-Mode full", FULL_ENTRY.read_text(encoding="utf-8-sig"))
        self.assertIn("-Mode demo", DEMO_ENTRY.read_text(encoding="utf-8-sig"))
        launcher = LAUNCHER.read_text(encoding="utf-8-sig")
        self.assertIn('ValidateSet("full", "demo")', launcher)
        for name in (
            "run_windhub.sh",
            "run_windhub_demo.sh",
            "run_windhub_launcher.sh",
        ):
            self.assertFalse((DEMO_ROOT / "examples" / name).exists())

    def test_release_build_is_silent_on_success(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout="MSBuild 17.14\n")
        stream = io.StringIO()
        with (
            mock.patch.object(example.subprocess, "run", return_value=completed) as run,
            redirect_stdout(stream),
        ):
            output = example._build_release(Path("C:/demo/build"), Path("C:/demo"))
        self.assertEqual(stream.getvalue(), "")
        self.assertIn("MSBuild", output)
        self.assertIn("--config", run.call_args.args[0])
        self.assertIn("Release", run.call_args.args[0])

    def test_release_build_failure_keeps_actionable_detail(self) -> None:
        completed = SimpleNamespace(returncode=1, stdout="fatal compiler error\n")
        with mock.patch.object(example.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "fatal compiler error"):
                example._build_release(Path("C:/demo/build"), Path("C:/demo"))


class DemoContractTests(unittest.TestCase):
    def test_markdown_is_compact_and_uses_direct_speedup(self) -> None:
        text = example.render_demo_markdown(demo_manifest())
        self.assertIn("直接串行", text)
        self.assertIn("CSC3 并行", text)
        self.assertIn("加速比 4.00×", text)
        for excluded in (
            "会议演示",
            "证据边界",
            "formal_evidence=false",
            "耗时降低",
            "两阶段串行",
        ):
            self.assertNotIn(excluded, text)

    def test_console_matches_locked_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            demo_root = Path(temporary) / "csc3-windhub-demo"
            output = demo_root / "build" / "demo-results" / "20260828-120000-000000"
            stream = io.StringIO()
            with redirect_stdout(stream):
                example.print_demo_summary(demo_manifest(), output, demo_root)
        lines = stream.getvalue().splitlines()
        self.assertEqual(lines[1], "WindHub 组装完成")
        self.assertEqual(lines[2], "节点 228384 | 单元 1113684 | 自由度 685152")
        self.assertEqual(lines[4], "路径          线程  符号(ms)  数值(ms)  总时间(ms)")
        self.assertTrue(lines[5].startswith("直接串行         1          —          —"))
        self.assertTrue(lines[6].startswith("CSC3 并行       16"))
        self.assertEqual(lines[8], "加速比 4.00× | 正确性 PASS | 峰值内存 5.000 GiB")
        self.assertEqual(
            lines[9],
            "结果：build/demo-results/20260828-120000-000000",
        )

    def test_serial_total_must_equal_direct_time(self) -> None:
        manifest = demo_manifest()
        manifest["sample"]["serial_total_ms"] = 70.0
        with self.assertRaisesRegex(RuntimeError, "直接串行组装时间"):
            example.render_demo_markdown(manifest)

    def test_parallel_total_must_equal_two_parallel_phases(self) -> None:
        manifest = demo_manifest()
        manifest["sample"]["parallel_total_ms"] = 51.0
        manifest["overall_speedup"] = 200.0 / 51.0
        with self.assertRaisesRegex(RuntimeError, "符号、数值阶段之和"):
            example.render_demo_markdown(manifest)

    def test_correctness_failure_is_rejected(self) -> None:
        manifest = demo_manifest()
        manifest["correctness"]["status"] = "FAIL"
        with self.assertRaisesRegex(RuntimeError, "未通过"):
            example.render_demo_markdown(manifest)

    def test_demo_runner_executes_one_full_thread_sample(self) -> None:
        class FakeRunner:
            RELATIVE_FROBENIUS_TOLERANCE = 1.0e-8

            def __init__(self) -> None:
                self.specification = None

            @staticmethod
            def _canonical_json(value):
                return json.dumps(value, ensure_ascii=False, indent=2) + "\n"

            @staticmethod
            def _atomic_write_text(path, text):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            @staticmethod
            def _artifact_records(_):
                return []

            def _run_one_sample(self, _executable, _input, result_root, specification):
                self.specification = specification
                raw_json = result_root / "raw" / "benchmark_summary.json"
                raw_json.parent.mkdir(parents=True)
                raw_json.write_text(
                    json.dumps({"case_sizes": demo_manifest()["case_sizes"]}),
                    encoding="utf-8",
                )
                sample = demo_sample()
                sample["raw_json_path"] = raw_json.relative_to(result_root).as_posix()
                return sample

        with tempfile.TemporaryDirectory() as temporary:
            demo_root = Path(temporary) / "demo"
            result_root = demo_root / "build" / "demo-results" / "one"
            runner = FakeRunner()
            with redirect_stdout(io.StringIO()):
                result = example._run_demo(
                    runner=runner,
                    demo_root=demo_root,
                    benchmark_executable=demo_root / "build" / "bin" / "bench.exe",
                    input_path=demo_root / "examples" / "3d-WindTurbineHub.inp",
                    result_root=result_root,
                    maximum_threads=16,
                    source={"commit_sha": "a" * 40},
                    source_tools={"package_manifest": "verified"},
                    input_facts={"repository_relative_path": "examples/3d-WindTurbineHub.inp"},
                    environment=demo_manifest()["environment"],
                    toolchain=demo_manifest()["toolchain"],
                )
            manifest = json.loads((result_root / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 0)
        self.assertEqual(
            runner.specification,
            {
                "sample_kind": "measured",
                "round": 1,
                "order_position": 1,
                "thread_count": 16,
            },
        )
        self.assertEqual(manifest["sample"]["serial_total_ms"], 200.0)
        self.assertEqual(manifest["sample"]["serial_direct_ms"], 200.0)
        self.assertEqual(manifest["overall_speedup"], 4.0)
        self.assertEqual(manifest["status"], "PASS")


class FullSummaryTests(unittest.TestCase):
    @staticmethod
    def summary() -> dict[str, object]:
        rows = []
        for thread_count, total, speedup in ((1, 30.0, 1.0), (2, 15.0, 2.0)):
            statistics = {
                "sample_count": 1,
                "median": total,
                "coefficient_of_variation": 0.0,
            }
            rows.append(
                {
                    "thread_count": thread_count,
                    "parallel_symbolic_ms": {"median": total * 2.0 / 3.0},
                    "parallel_numeric_ms": {"median": total / 3.0},
                    "parallel_total_ms": statistics,
                    "overall_speedup": speedup,
                    "peak_working_set_bytes": {"median": 5 * 1024**3},
                }
            )
        return {
            "status": "PASS",
            "configuration": {
                "thread_counts": [1, 2],
                "maximum_threads": 2,
                "warmup_count": 0,
                "repeat_count": 1,
                "sample_process_model": "one_fresh_child_process_per_sample",
                "measured_round_order": "alternating_ascending_descending",
                "samples_are_serialized": True,
            },
            "process_integrity": {
                "expected_sample_count": 2,
                "observed_sample_count": 2,
                "measured_sample_count_per_thread": 1,
                "unique_sample_ids": True,
                "samples_overlap": False,
                "all_exit_codes_zero": True,
                "all_observed_team_sizes_match": True,
            },
            "memory_definition": {
                "peak_working_set": "GetProcessMemoryInfo.PeakWorkingSetSize",
                "peak_working_set_is_os_measured": True,
            },
            "case_sizes": {
                "node_count": 228384,
                "element_count": 1113684,
                "dof_count": 685152,
                "nnz": 14093676,
            },
            "correctness": {
                "status": "PASS",
                "relative_frobenius_error_maximum": 1.0e-12,
            },
            "per_thread": rows,
        }

    @staticmethod
    def manifest() -> dict[str, object]:
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
                "openmp_runtime": "vcomp140.dll",
            },
        }

    def test_full_summary_displays_speedup_as_ratio(self) -> None:
        text = example.render_summary_markdown(self.summary(), self.manifest())
        self.assertIn("1.000×", text)
        self.assertIn("2.000×", text)
        self.assertNotIn("整体加速比（%）", text)
        self.assertIn("每个线程数测量 1 次", text)
        for excluded in ("测试方法", "不同电脑", "正式证据", "CV"):
            self.assertNotIn(excluded, text)


class OrchestrationTests(unittest.TestCase):
    def test_full_scan_runs_each_thread_once(self) -> None:
        self.assertEqual(example.FULL_WARMUP_COUNT, 0)
        self.assertEqual(example.FULL_REPEAT_COUNT, 1)

    def test_demo_progress_has_only_three_fixed_steps_before_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            demo_root = Path(temporary) / "demo"
            build_root = demo_root / "build"
            benchmark = build_root / "bin" / "csc3_demo_benchmark.exe"
            benchmark.parent.mkdir(parents=True)
            benchmark.write_bytes(b"test")
            paths = example.ExamplePaths(
                demo_root=demo_root,
                repository_root=Path(temporary) / "repository",
                build_root=build_root,
                input_path=Path(temporary) / "repository" / "examples" / "input.inp",
            )
            runner = SimpleNamespace(
                _host_environment=lambda: {
                    "logical_processor_count": 16,
                    "physical_core_count": 8,
                }
            )
            stream = io.StringIO()
            with (
                mock.patch.object(example.os, "name", "nt"),
                mock.patch.object(
                    example,
                    "_cache_entries",
                    return_value={"CMAKE_GENERATOR": "Visual Studio 17 2022"},
                ),
                mock.patch.object(example, "_compiler_facts", return_value=("MSVC", "19.44", "x64")),
                mock.patch.object(example, "_compiler_pointer_size", return_value=8),
                mock.patch.object(example, "_load_runner", return_value=runner),
                mock.patch.object(
                    example,
                    "_source_context",
                    return_value=(
                        {"commit_sha": "a" * 40},
                        {"package_manifest": "verified"},
                        {"sha256": "b" * 64},
                    ),
                ),
                mock.patch.object(example, "_build_release", return_value="MSBuild 17.14"),
                mock.patch.object(example, "_toolchain_facts", return_value={"compiler": "MSVC"}),
                mock.patch.object(example, "_run_demo", return_value=0) as run_demo,
                redirect_stdout(stream),
            ):
                result = example.run_example(
                    paths,
                    build_root / "demo-results" / "candidate",
                    mode=example.DEMO_MODE,
                )
        self.assertEqual(result, 0)
        self.assertEqual(
            stream.getvalue().splitlines(),
            [
                "[1/3] 校验环境与输入",
                "[2/3] 构建 Release",
                "[3/3] 运行 WindHub（16 线程）",
            ],
        )
        self.assertEqual(run_demo.call_args.kwargs["maximum_threads"], 16)

    def test_non_windows_fails_before_build(self) -> None:
        with mock.patch.object(example.os, "name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "只支持 Windows x64"):
                example.run_example(mode=example.DEMO_MODE)


if __name__ == "__main__":
    unittest.main()
