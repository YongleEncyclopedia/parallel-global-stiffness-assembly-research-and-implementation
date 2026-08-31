"""Issue #54 Windows 中文报告生成器的契约测试。"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
REPORT_SCRIPT = DEMO_ROOT / "scripts" / "generate_windows_delivery_report.py"
RUNNER_SCRIPT = DEMO_ROOT / "scripts" / "run_windows_process_benchmark.py"


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"无法加载 {path.name}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


reporter = load_module("csc3_windows_report_test", REPORT_SCRIPT)
runner = load_module("csc3_windows_runner_for_report_test", RUNNER_SCRIPT)


class WindowsReportTests(unittest.TestCase):
    def make_inputs(self, maximum_threads: int = 3):
        schedule = runner.build_schedule(maximum_threads, 2, 7)
        origin = datetime(2026, 7, 25, tzinfo=timezone.utc)
        records: list[dict[str, object]] = []
        for index, specification in enumerate(schedule):
            start = origin + timedelta(seconds=index * 2)
            end = start + timedelta(seconds=1)
            thread_count = int(specification["thread_count"])
            records.append(
                {
                    "schema_version": runner.SCHEMA_VERSION,
                    "sample_id": runner._sample_id(specification),
                    **specification,
                    "pid": 9000 + index,
                    "started_at_utc": runner._utc_text(start),
                    "ended_at_utc": runner._utc_text(end),
                    "wall_time_seconds": 1.0,
                    "exit_code": 0,
                    "peak_working_set_bytes": 2_000_000_000
                    + 10_000_000 * thread_count,
                    "peak_working_set_source": runner.PEAK_WORKING_SET_SOURCE,
                    "memory_query_count": 10,
                    "symbolic_team_size_observed": thread_count,
                    "numeric_team_size_observed": thread_count,
                    "input_prepare_ms": 10.0,
                    "serial_direct_ms": 1000.0,
                    "serial_symbolic_ms": 600.0,
                    "serial_numeric_ms": 400.0,
                    "serial_total_ms": 1000.0,
                    "parallel_symbolic_ms": 600.0 / thread_count,
                    "parallel_numeric_ms": 400.0 / thread_count,
                    "parallel_total_ms": 1000.0 / thread_count,
                    "estimated_persistent_bytes": 900_000_000,
                    "relative_frobenius_error": 1.0e-14,
                    "max_absolute_error": 1.0e-10,
                    "structure_matches": True,
                    "matrix_correctness_status": "PASS",
                    "scatter_correctness_status": "PASS",
                    "symbolic_plan_matches_serial": True,
                    "numeric_setup_plan_matches_serial": True,
                    "raw_csv_path": f"raw/{index}/benchmark_samples.csv",
                    "raw_json_path": f"raw/{index}/benchmark_summary.json",
                    "stdout_log_path": f"raw/{index}/stdout.log",
                    "stderr_log_path": f"raw/{index}/stderr.log",
                }
            )
        summary = runner.summarize_records(records, maximum_threads, 2, 7)
        summary["case_sizes"] = {
            "node_count": 228384,
            "element_count": 1113684,
            "dimension": 685152,
            "nonzero_count": 14093676,
        }
        summary["input"] = {
            "repository_relative_path": "examples/3d-WindTurbineHub.inp",
            "sha256": "4f" * 32,
            "size_bytes": 76111745,
            "git_lfs_materialized": True,
            "matches_head_lfs_pointer": True,
        }
        rows = [
            {
                field: str(record.get(field, ""))
                for field in runner.PROCESS_CSV_FIELDS
            }
            for record in records
        ]
        for row, record in zip(rows, records):
            for field in (
                "structure_matches",
                "symbolic_plan_matches_serial",
                "numeric_setup_plan_matches_serial",
            ):
                row[field] = "true" if record[field] else "false"

        manifest = {
            "schema_version": runner.MANIFEST_SCHEMA_VERSION,
            "status": "PASS",
            "summary_status": "PASS",
            "issue": 54,
            "source": {
                "commit_sha": "a" * 40,
                "branch": "codex/issue-54-csc3-windows-delivery",
                "tracked_worktree_clean_at_start": True,
            },
            "environment": {
                "caption": "Microsoft Windows 11",
                "version": "10.0",
                "build_number": "26200",
                "architecture": "64-bit",
                "cpu_model": "Test CPU",
                "physical_core_count": maximum_threads,
                "logical_processor_count": maximum_threads,
                "total_physical_memory_bytes": 32 * 1024**3,
                "python_version": "3.13.0",
            },
            "toolchain": {
                "compiler": "MSVC 19.44",
                "cmake": "4.3.3",
                "ninja": "1.13.2",
                "openmp_runtime": "vcomp140.dll",
            },
            "input": summary["input"],
            "configuration": {
                "maximum_threads": maximum_threads,
                "thread_counts": list(range(1, maximum_threads + 1)),
                "warmup_count": 2,
                "repeat_count": 7,
                "sample_process_model": "one_fresh_child_process_per_sample",
                "samples_are_serialized": True,
                "schedule": schedule,
            },
            "samples": [
                {
                    field: record[field]
                    for field in (
                        "sample_id",
                        "sample_kind",
                        "round",
                        "order_position",
                        "thread_count",
                        "pid",
                        "started_at_utc",
                        "ended_at_utc",
                        "exit_code",
                        "peak_working_set_bytes",
                        "symbolic_team_size_observed",
                        "numeric_team_size_observed",
                        "raw_csv_path",
                        "raw_json_path",
                    )
                }
                for record in records
            ],
            "artifacts": [
                {
                    "path": "benchmark_samples.csv",
                    "size_bytes": 1,
                    "sha256": "1" * 64,
                }
            ],
        }
        build_evidence = {
            "schema_version": "csc3-demo-windows-build-evidence-v1",
            "status": "PASS",
            "issue": 54,
            "builds": [
                {
                    "id": "msvc",
                    "name": "MSVC + Ninja",
                    "compiler": "MSVC 19.44",
                    "openmp": "vcomp140.dll",
                    "configure_status": "PASS",
                    "build_status": "PASS",
                    "app_status": "PASS",
                    "ctest_status": "PASS",
                    "ctest_passed": 10,
                    "ctest_failed": 0,
                    "consumer_status": "PASS",
                    "consumer_passed": 1,
                    "consumer_failed": 0,
                    "openmp_off_gate_status": "PASS",
                    "openmp_missing_gate_status": "PASS",
                    "clean_room_status": "PASS",
                    "clean_room_ctest_passed": 10,
                    "clean_room_consumer_passed": 1,
                },
                {
                    "id": "mingw",
                    "name": "MinGW-w64 + Ninja",
                    "compiler": "GCC 16.1.0",
                    "openmp": "libgomp",
                    "configure_status": "PASS",
                    "build_status": "PASS",
                    "app_status": "PASS",
                    "ctest_status": "PASS",
                    "ctest_passed": 10,
                    "ctest_failed": 0,
                    "consumer_status": "PASS",
                    "consumer_passed": 1,
                    "consumer_failed": 0,
                    "openmp_off_gate_status": "PASS",
                    "openmp_missing_gate_status": "PASS",
                    "clean_room_status": "PASS",
                    "clean_room_ctest_passed": 10,
                    "clean_room_consumer_passed": 1,
                },
            ],
            "commands": [
                {
                    "purpose": "MSVC 配置",
                    "command": "cmake -S demos/csc3_symmetric_assembly_demo -B build/msvc -G Ninja",
                    "status": "PASS",
                    "log": "results/build/msvc-configure.log",
                }
            ],
        }
        return manifest, summary, rows, build_evidence

    def test_historical_process_v1_remains_read_only_compatible(self) -> None:
        manifest, summary, rows, build_evidence = self.make_inputs()
        summary["schema_version"] = reporter.PROCESS_SCHEMA_VERSION_V1
        for row in rows:
            row["schema_version"] = reporter.PROCESS_SCHEMA_VERSION_V1
            row.pop("serial_direct_ms")
        maximum_threads = reporter.validate_evidence(
            manifest,
            summary,
            rows,
            build_evidence,
        )
        self.assertEqual(maximum_threads, 3)

    def test_report_has_exact_eight_chapters_and_figure_qa(self) -> None:
        try:
            import matplotlib  # noqa: F401
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib/Pillow 未安装")
        manifest, summary, rows, build_evidence = self.make_inputs()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            evidence = root / "results"
            report_dir = root / "reports"
            evidence.mkdir()
            report_dir.mkdir()
            samples_path = evidence / "benchmark_samples.csv"
            summary_path = evidence / "benchmark_summary.json"
            manifest_path = evidence / "run_manifest.json"
            samples_path.write_text("fixture\n", encoding="utf-8")
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False),
                encoding="utf-8",
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )
            figure_outputs = reporter.generate_performance_figure(
                manifest,
                summary,
                rows,
                report_dir / "figures",
            )
            report_path = report_dir / "测试报告.md"
            text = reporter.render_report(
                manifest,
                summary,
                rows,
                build_evidence,
                report_path,
                samples_path,
                summary_path,
                manifest_path,
                figure_outputs,
            )
            self.assertEqual(
                reporter._extract_headings(text),
                reporter.EXPECTED_TOP_LEVEL_HEADINGS,
            )
            self.assertIn("GetProcessMemoryInfo().PeakWorkingSetSize", text)
            self.assertIn("estimated_persistent_bytes", text)
            self.assertNotRegex(text, r"[A-Za-z]:[\\/]")
            self.assertEqual(figure_outputs["qa"]["status"], "PASS")
            self.assertEqual(
                figure_outputs["qa"]["archetype"],
                "bar comparison with raw-sample scatter",
            )
            self.assertTrue(
                figure_outputs["qa"]["image_integrity"]["raw_samples_plotted"]
            )
            self.assertIn("七次正式测量的散点", text)
            for key in ("png_path", "svg_path", "pdf_path", "qa_path"):
                self.assertTrue(Path(figure_outputs[key]).is_file())

    def test_missing_measured_sample_is_rejected(self) -> None:
        manifest, summary, rows, build_evidence = self.make_inputs()
        with self.assertRaisesRegex(RuntimeError, "样本记录与 CSV 数量不一致"):
            reporter.validate_evidence(
                manifest,
                summary,
                rows[:-1],
                build_evidence,
            )

    def test_summary_statistics_are_recomputed_from_csv(self) -> None:
        manifest, summary, rows, build_evidence = self.make_inputs()
        summary["per_thread"][1]["parallel_total_ms"]["median"] = 1.0
        with self.assertRaisesRegex(RuntimeError, "与 CSV 重新计算结果不一致"):
            reporter.validate_evidence(
                manifest,
                summary,
                rows,
                build_evidence,
            )


if __name__ == "__main__":
    unittest.main()
