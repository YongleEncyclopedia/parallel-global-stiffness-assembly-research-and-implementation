#!/usr/bin/env python3
"""Windows 独立进程 benchmark runner 的契约测试。"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
