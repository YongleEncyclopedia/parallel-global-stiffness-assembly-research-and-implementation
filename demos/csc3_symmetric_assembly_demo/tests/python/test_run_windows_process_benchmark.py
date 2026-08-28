#!/usr/bin/env python3
"""Windows 独立进程 benchmark runner 的契约测试。"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "run_windows_process_benchmark.py"


def load_runner():
    specification = importlib.util.spec_from_file_location(
        "csc3_windows_process_runner_test",
        SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("无法加载 Windows benchmark runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


runner = load_runner()


class ScheduleTests(unittest.TestCase):
    def test_portable_csv_replaces_windows_memory_fields_without_losing_teams(self) -> None:
        self.assertNotIn("peak_working_set_bytes", runner.PORTABLE_PROCESS_CSV_FIELDS)
        self.assertNotIn("peak_working_set_source", runner.PORTABLE_PROCESS_CSV_FIELDS)
        self.assertIn("peak_resident_memory_bytes", runner.PORTABLE_PROCESS_CSV_FIELDS)
        self.assertIn("symbolic_team_size_observed", runner.PORTABLE_PROCESS_CSV_FIELDS)
        self.assertIn("numeric_team_size_observed", runner.PORTABLE_PROCESS_CSV_FIELDS)

    def test_issue_54_schedule_is_complete_and_alternating(self) -> None:
        schedule = runner.build_schedule(16, 2, 7)
        self.assertEqual(len(schedule), 16 * 9)
        identities = {
            (
                item["sample_kind"],
                item["round"],
                item["thread_count"],
            )
            for item in schedule
        }
        self.assertEqual(len(identities), len(schedule))

        measured = [item for item in schedule if item["sample_kind"] == "measured"]
        first_round = [
            item["thread_count"] for item in measured if item["round"] == 1
        ]
        second_round = [
            item["thread_count"] for item in measured if item["round"] == 2
        ]
        self.assertEqual(first_round, list(range(1, 17)))
        self.assertEqual(second_round, list(range(16, 0, -1)))

    def test_statistics_use_population_standard_deviation(self) -> None:
        result = runner._statistics([1.0, 2.0, 3.0])
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["median"], 2.0)
        self.assertAlmostEqual(
            result["population_standard_deviation"],
            (2.0 / 3.0) ** 0.5,
        )

    def test_progress_reports_completed_sample_and_requested_team(self) -> None:
        stream = io.StringIO()
        options = argparse.Namespace(progress_stream=stream)
        runner._emit_progress(
            options,
            17,
            144,
            {
                "sample_kind": "measured",
                "round": 1,
                "thread_count": 16,
            },
        )
        self.assertEqual(
            stream.getvalue(),
            "[17/144] 正式测量第 1 轮，线程数 16：完成\n",
        )


class ToolchainTests(unittest.TestCase):
    def test_legacy_ninja_metadata_keeps_v1_manifest(self) -> None:
        schema, facts = runner._toolchain_provenance(
            argparse.Namespace(
                compiler="MSVC 19.44",
                cmake="4.3.3",
                ninja="1.13.2",
                openmp_runtime="vcomp140.dll",
            )
        )
        self.assertEqual(schema, runner.MANIFEST_SCHEMA_VERSION)
        self.assertEqual(facts["ninja"], "1.13.2")

    def test_generic_build_tool_metadata_uses_v2_manifest(self) -> None:
        schema, facts = runner._toolchain_provenance(
            argparse.Namespace(
                toolchain={
                    "compiler": "MSVC 19.44",
                    "cmake": "cmake version 4.3.3",
                    "cmake_generator": "Visual Studio 17 2022",
                    "build_tool": "MSBuild 17.14",
                    "openmp_runtime": "vcomp140.dll 14.51",
                    "benchmark_build_type": "Release",
                }
            )
        )
        self.assertEqual(schema, runner.GENERIC_TOOLCHAIN_MANIFEST_SCHEMA_VERSION)
        self.assertEqual(facts["build_tool"], "MSBuild 17.14")
        self.assertNotIn("ninja", facts)

    def test_generic_metadata_rejects_non_release_build(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Release"):
            runner._toolchain_provenance(
                argparse.Namespace(
                    toolchain={
                        "compiler": "MSVC",
                        "cmake": "CMake",
                        "cmake_generator": "Visual Studio 17 2022",
                        "build_tool": "MSBuild",
                        "openmp_runtime": "vcomp140.dll",
                        "benchmark_build_type": "Debug",
                    }
                )
            )


class CommandLineTests(unittest.TestCase):
    def test_empty_command_points_to_the_one_click_example(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("维护者使用的底层脚本", completed.stderr)
        self.assertIn(r"..\examples\run_windhub.ps1", completed.stderr)
        self.assertNotIn("--repository-root", completed.stderr)


class PreflightTests(unittest.TestCase):
    def test_32_bit_python_is_rejected_for_peak_memory_sampling(self) -> None:
        with (
            mock.patch.object(runner.os, "name", "nt"),
            mock.patch.object(runner.ctypes, "sizeof", return_value=4),
        ):
            with self.assertRaisesRegex(RuntimeError, "64 位 Python"):
                runner.run_benchmark(argparse.Namespace())

    def test_actual_logical_processor_mismatch_fails_before_sampling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            executable = root / "benchmark.exe"
            executable.write_bytes(b"fake")
            input_path = repository / "examples" / "windhub.inp"
            input_path.parent.mkdir()
            input_path.write_bytes(b"fake")
            output_root = root / "result"
            options = argparse.Namespace(
                repository_root=repository,
                benchmark_executable=executable,
                input=input_path,
                out_dir=output_root,
                maximum_threads=4,
                warmup=2,
                repeat=7,
            )
            with (
                mock.patch.object(runner.os, "name", "nt"),
                mock.patch.object(
                    runner,
                    "_source_provenance",
                    return_value={"commit_sha": "a" * 40},
                ),
                mock.patch.object(
                    runner,
                    "_input_provenance",
                    return_value={"size_bytes": 1},
                ),
                mock.patch.object(
                    runner,
                    "_windows_environment",
                    return_value={"logical_processor_count": 8},
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "当前为 8"):
                    runner.run_benchmark(options)
            self.assertFalse(output_root.exists())

    def test_keyboard_interrupt_kills_the_current_hidden_child(self) -> None:
        class FakeProcess:
            _handle = 123
            pid = 456

            def __init__(self) -> None:
                self.killed = False
                self.wait_count = 0

            def poll(self):
                return -9 if self.killed else None

            def kill(self) -> None:
                self.killed = True

            def wait(self) -> int:
                self.wait_count += 1
                self.killed = True
                return -9

        process = FakeProcess()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(runner.subprocess, "Popen", return_value=process),
                mock.patch.object(
                    runner,
                    "_query_peak_working_set",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    runner._run_one_sample(
                        root / "benchmark.exe",
                        root / "windhub.inp",
                        root,
                        {
                            "sample_kind": "warmup",
                            "round": 1,
                            "order_position": 1,
                            "thread_count": 1,
                        },
                    )
        self.assertTrue(process.killed)
        self.assertGreaterEqual(process.wait_count, 1)

    def test_keyboard_interrupt_marks_the_manifest_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            repository.mkdir()
            executable = root / "benchmark.exe"
            executable.write_bytes(b"fake")
            input_path = repository / "windhub.inp"
            input_path.write_bytes(b"fake")
            output_root = root / "result"
            options = argparse.Namespace(
                repository_root=repository,
                benchmark_executable=executable,
                input=input_path,
                out_dir=output_root,
                maximum_threads=1,
                warmup=2,
                repeat=7,
                toolchain={
                    "compiler": "MSVC 19.44",
                    "cmake": "cmake version 4.3",
                    "cmake_generator": "Visual Studio 17 2022",
                    "build_tool": "MSBuild 17.14",
                    "openmp_runtime": "vcomp140.dll 14.51",
                    "benchmark_build_type": "Release",
                },
                source_tools={"git": "git version 2.51", "git_lfs": "git-lfs/3.7"},
            )
            with (
                mock.patch.object(runner.os, "name", "nt"),
                mock.patch.object(
                    runner,
                    "_source_provenance",
                    return_value={"commit_sha": "a" * 40},
                ),
                mock.patch.object(
                    runner,
                    "_input_provenance",
                    return_value={"size_bytes": 1},
                ),
                mock.patch.object(
                    runner,
                    "_windows_environment",
                    return_value={"logical_processor_count": 1},
                ),
                mock.patch.object(
                    runner,
                    "_run_one_sample",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    runner.run_benchmark(options)
            manifest = json.loads(
                (output_root / "run_manifest.json").read_text(encoding="utf-8")
            )
        self.assertEqual(manifest["status"], "FAIL")
        self.assertIn("KeyboardInterrupt", manifest["failure"])
        self.assertEqual(manifest["source_tools"]["git_lfs"], "git-lfs/3.7")


class ChildOutputContractTests(unittest.TestCase):
    @staticmethod
    def _write_child(root: Path) -> tuple[Path, Path]:
        raw_csv = root / "benchmark_samples.csv"
        raw_json = root / "benchmark_summary.json"
        row = {
            "schema_version": "csc3-demo-benchmark-v3",
            "thread_count": "4",
            "sample_kind": "measured",
            "input_prepare_ms": "100.0",
            "serial_direct_ms": "12000.0",
            "serial_symbolic_ms": "6000.0",
            "serial_numeric_ms": "3000.0",
            "symbolic_total_ms": "1500.0",
            "numeric_total_ms": "500.0",
            "amortized_total_ms": "2000.0",
            "estimated_persistent_bytes": str(512 * 1024**2),
            "symbolic_plan_matches_serial": "true",
            "numeric_setup_plan_matches_serial": "true",
        }
        with raw_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=tuple(row))
            writer.writeheader()
            writer.writerow(row)
        statistics = lambda value: {
            "sample_count": 1,
            "median_ms": value,
        }
        raw_json.write_text(
            json.dumps(
                {
                    "schema_version": "csc3-demo-benchmark-v3",
                    "configuration": {
                        "case": "windhub",
                        "nx": 0,
                        "ny": 0,
                        "nz": 0,
                        "thread_counts": [4],
                        "warmup_count": 0,
                        "repeat_count": 1,
                        "amortization_count": 1,
                        "performance_evidence_level": "local-smoke",
                    },
                    "correctness": {
                        "status": "PASS",
                        "structure_matches": True,
                        "relative_frobenius_error": 1.0e-16,
                        "max_absolute_error": 1.0e-12,
                    },
                    "scatter_correctness": {"status": "PASS"},
                    "per_thread_measured_statistics": [
                        {
                            "symbolic_thread_count_observed": 4,
                            "numeric_thread_count_observed": 4,
                        }
                    ],
                    "validation_cases": [{"status": "PASS"}],
                    "serial_reference_definition": (
                        "direct contribution generation, sort, and reduction; "
                        "no prebuilt CSC3 or scatter"
                    ),
                    "serial_direct_measured_statistics": {
                        "total_ms": statistics(12000.0)
                    },
                    "serial_two_stage_phase_measured_statistics": {
                        "symbolic_total_ms": statistics(6000.0),
                        "numeric_total_ms": statistics(3000.0),
                    },
                    "case_sizes": {
                        "node_count": 100,
                        "element_count": 200,
                        "dof_count": 300,
                        "nnz": 400,
                    },
                }
            ),
            encoding="utf-8",
        )
        return raw_csv, raw_json

    def test_direct_serial_is_the_only_overall_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_csv, raw_json = self._write_child(Path(temporary))
            record = runner._validate_child_outputs(raw_csv, raw_json, 4)
        self.assertEqual(record["serial_direct_ms"], 12000.0)
        self.assertEqual(record["serial_total_ms"], 12000.0)
        self.assertNotEqual(
            record["serial_total_ms"],
            record["serial_symbolic_ms"] + record["serial_numeric_ms"],
        )

    def test_direct_serial_summary_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_csv, raw_json = self._write_child(Path(temporary))
            summary = json.loads(raw_json.read_text(encoding="utf-8"))
            summary["serial_direct_measured_statistics"]["total_ms"][
                "median_ms"
            ] = 9000.0
            raw_json.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "直接串行统计.*不一致"):
                runner._validate_child_outputs(raw_csv, raw_json, 4)


class SummaryTests(unittest.TestCase):
    def make_records(self, maximum_threads: int = 3) -> list[dict[str, object]]:
        schedule = runner.build_schedule(maximum_threads, 2, 7)
        origin = datetime(2026, 7, 23, tzinfo=timezone.utc)
        records: list[dict[str, object]] = []
        for index, specification in enumerate(schedule):
            start = origin + timedelta(seconds=2 * index)
            end = start + timedelta(seconds=1)
            thread_count = int(specification["thread_count"])
            records.append(
                {
                    "sample_id": runner._sample_id(specification),
                    **specification,
                    "pid": 1000 + index,
                    "started_at_utc": runner._utc_text(start),
                    "ended_at_utc": runner._utc_text(end),
                    "exit_code": 0,
                    "peak_working_set_bytes": 1_000_000 + thread_count,
                    "symbolic_team_size_observed": thread_count,
                    "numeric_team_size_observed": thread_count,
                    "serial_total_ms": 100.0,
                    "parallel_symbolic_ms": 60.0 / thread_count,
                    "parallel_numeric_ms": 40.0 / thread_count,
                    "parallel_total_ms": 100.0 / thread_count,
                    "estimated_persistent_bytes": 500_000,
                    "relative_frobenius_error": 0.0,
                    "max_absolute_error": 0.0,
                    "structure_matches": True,
                    "matrix_correctness_status": "PASS",
                    "scatter_correctness_status": "PASS",
                    "symbolic_plan_matches_serial": True,
                    "numeric_setup_plan_matches_serial": True,
                }
            )
        return records

    def test_summary_keeps_seven_samples_and_uses_total_time(self) -> None:
        summary = runner.summarize_records(self.make_records(), 3, 2, 7)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(
            summary["serial_baseline_total_ms"]["sample_count"],
            7,
        )
        per_thread = summary["per_thread"]
        self.assertEqual([item["thread_count"] for item in per_thread], [1, 2, 3])
        self.assertAlmostEqual(per_thread[2]["overall_speedup"], 3.0)
        self.assertEqual(
            per_thread[1]["peak_working_set_bytes"]["sample_count"],
            7,
        )

    def test_linux_summary_uses_peak_resident_set_without_relabeling_it(self) -> None:
        records = self.make_records()
        for record in records:
            record["peak_resident_memory_bytes"] = record.pop(
                "peak_working_set_bytes"
            )
        summary = runner.summarize_records(records, 3, 2, 7)
        self.assertEqual(summary["schema_version"], runner.PORTABLE_SCHEMA_VERSION)
        self.assertEqual(
            summary["memory_definition"]["peak_resident_set"],
            runner.PEAK_RSS_SOURCE,
        )
        self.assertIn("peak_resident_memory_bytes", summary["per_thread"][0])
        self.assertNotIn("peak_working_set_bytes", summary["per_thread"][0])

    def test_overlap_is_rejected(self) -> None:
        records = self.make_records()
        records[1]["started_at_utc"] = records[0]["started_at_utc"]
        with self.assertRaisesRegex(RuntimeError, "重叠"):
            runner.summarize_records(records, 3, 2, 7)

    def test_team_size_mismatch_is_rejected(self) -> None:
        records = self.make_records()
        records[-1]["numeric_team_size_observed"] = 1
        with self.assertRaisesRegex(RuntimeError, "team size"):
            runner.summarize_records(records, 3, 2, 7)

    def test_schedule_order_mismatch_is_rejected(self) -> None:
        records = self.make_records()
        records[1], records[2] = records[2], records[1]
        with self.assertRaisesRegex(RuntimeError, "执行顺序"):
            runner.summarize_records(records, 3, 2, 7)


@unittest.skipUnless(os.name == "nt", "Windows API test")
class WindowsMemoryTests(unittest.TestCase):
    def test_peak_working_set_comes_from_live_process_handle(self) -> None:
        process = subprocess.Popen(
            [
                sys._base_executable,
                "-c",
                "import time; payload=bytearray(64*1024*1024); time.sleep(0.5)",
            ],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        peak = 0
        while process.poll() is None:
            peak = max(peak, runner._query_peak_working_set(int(process._handle)))
            time.sleep(0.01)
        process.wait()
        self.assertGreater(peak, 48 * 1024 * 1024)


class LinuxMemoryContractTests(unittest.TestCase):
    def test_wait4_ru_maxrss_is_converted_from_kibibytes_to_bytes(self) -> None:
        process = SimpleNamespace(pid=1234, returncode=None)
        usage = SimpleNamespace(ru_maxrss=12345)
        with (
            mock.patch.object(runner.sys, "platform", "linux"),
            mock.patch.object(
                runner.os,
                "wait4",
                return_value=(1234, 0, usage),
                create=True,
            ),
        ):
            exit_code, peak_bytes = runner._wait_linux_process(process)
        self.assertEqual(exit_code, 0)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(peak_bytes, 12345 * 1024)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux wait4 test")
    def test_live_linux_child_reports_peak_resident_set(self) -> None:
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "payload=bytearray(64*1024*1024)",
            ]
        )
        exit_code, peak_bytes = runner._wait_linux_process(process)
        self.assertEqual(exit_code, 0)
        self.assertGreater(peak_bytes, 48 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
