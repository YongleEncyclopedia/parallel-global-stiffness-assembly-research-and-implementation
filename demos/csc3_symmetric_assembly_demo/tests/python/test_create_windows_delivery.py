"""Issue #54 Windows 交付 ZIP 的创建与自校验测试。"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "create_windows_delivery.py"
RUNNER_SCRIPT = DEMO_ROOT / "scripts" / "run_windows_process_benchmark.py"


def load_packager():
    specification = importlib.util.spec_from_file_location(
        "csc3_windows_delivery_test",
        SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("无法加载 Windows 交付打包器")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


packager = load_packager()


def load_runner():
    specification = importlib.util.spec_from_file_location(
        "csc3_windows_runner_for_delivery_test",
        RUNNER_SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("无法加载 Windows 性能 runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


runner = load_runner()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class WindowsDeliveryTests(unittest.TestCase):
    def prepare_source_repository(self, root: Path) -> tuple[Path, Path, str]:
        repository = root / "repository"
        repository.mkdir(parents=True)

        # 源码 ZIP 本身不携带 .git；测试在临时目录重建最小仓库边界，
        # 避免打包器测试暗中依赖开发者的原始工作树。
        source_zip = packager.create_source_zip(DEMO_ROOT, [])
        with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
            archive.extractall(repository / "demos")
        demo = repository / "demos" / packager.SOURCE_ROOT_NAME
        for arguments in (
            ["git", "init", "--quiet"],
            ["git", "config", "core.autocrlf", "false"],
            ["git", "config", "user.name", "CSC3 Test"],
            ["git", "config", "user.email", "csc3-test@example.invalid"],
            ["git", "add", "."],
            ["git", "commit", "--quiet", "-m", "fixture"],
        ):
            subprocess.run(arguments, cwd=repository, check=True)
        commit_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        return repository, demo, commit_sha

    def prepare_fixture(
        self,
        root: Path,
        repository: Path,
        demo: Path,
        delivery_commit: str,
    ):
        performance = root / "performance"
        report = root / "report"
        build = root / "build-evidence"
        output = root / "output"
        performance.mkdir()
        report.mkdir()
        build.mkdir()
        output.mkdir()
        input_facts = {
            "repository_relative_path": "examples/3d-WindTurbineHub.inp",
            "sha256": "4f" * 32,
            "size_bytes": 76111745,
            "git_lfs_materialized": True,
            "matches_head_lfs_pointer": True,
        }
        maximum_threads = 1
        schedule = runner.build_schedule(maximum_threads, 2, 7)
        origin = datetime(2026, 7, 25, tzinfo=timezone.utc)
        records: list[dict[str, object]] = []
        for index, specification in enumerate(schedule):
            started = origin + timedelta(seconds=index * 2)
            ended = started + timedelta(seconds=1)
            thread_count = int(specification["thread_count"])
            sample_id = runner._sample_id(specification)
            raw_root = f"raw/{sample_id}"
            records.append(
                {
                    "schema_version": runner.SCHEMA_VERSION,
                    "sample_id": sample_id,
                    **specification,
                    "pid": 9000 + index,
                    "started_at_utc": runner._utc_text(started),
                    "ended_at_utc": runner._utc_text(ended),
                    "wall_time_seconds": 1.0,
                    "exit_code": 0,
                    "peak_working_set_bytes": 2_000_000_000,
                    "peak_working_set_source": runner.PEAK_WORKING_SET_SOURCE,
                    "symbolic_team_size_observed": thread_count,
                    "numeric_team_size_observed": thread_count,
                    "input_prepare_ms": 10.0,
                    "serial_symbolic_ms": 600.0,
                    "serial_numeric_ms": 400.0,
                    "serial_total_ms": 1000.0,
                    "parallel_symbolic_ms": 600.0,
                    "parallel_numeric_ms": 400.0,
                    "parallel_total_ms": 1000.0,
                    "estimated_persistent_bytes": 900_000_000,
                    "relative_frobenius_error": 1.0e-14,
                    "max_absolute_error": 1.0e-10,
                    "structure_matches": True,
                    "matrix_correctness_status": "PASS",
                    "scatter_correctness_status": "PASS",
                    "symbolic_plan_matches_serial": True,
                    "numeric_setup_plan_matches_serial": True,
                    "raw_csv_path": f"{raw_root}/benchmark_samples.csv",
                    "raw_json_path": f"{raw_root}/benchmark_summary.json",
                    "stdout_log_path": f"{raw_root}/stdout.txt",
                    "stderr_log_path": f"{raw_root}/stderr.txt",
                }
            )
        summary = runner.summarize_records(records, maximum_threads, 2, 7)
        summary["case_sizes"] = {
            "node_count": 228384,
            "element_count": 1113684,
            "dimension": 685152,
            "nonzero_count": 14093676,
        }
        summary["input"] = input_facts
        manifest = {
            "schema_version": runner.MANIFEST_SCHEMA_VERSION,
            "status": "PASS",
            "summary_status": "PASS",
            "issue": 54,
            "source": {
                "branch": "codex/issue-54-csc3-windows-delivery",
                "commit_sha": "a" * 40,
            },
            "environment": {
                "logical_processor_count": maximum_threads,
            },
            "configuration": {
                "maximum_threads": maximum_threads,
                "thread_counts": [1],
                "warmup_count": 2,
                "repeat_count": 7,
                "sample_process_model": "one_fresh_child_process_per_sample",
                "samples_are_serialized": True,
                "schedule": schedule,
            },
            "input": input_facts,
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
        }
        source_zip = packager.create_source_zip_from_commit(
            repository,
            demo,
            delivery_commit,
            [],
        )
        build_evidence = {
            "schema_version": "csc3-demo-windows-build-evidence-v1",
            "status": "PASS",
            "issue": 54,
            "source_performance_commit": "a" * 40,
            "delivery_source_commit": delivery_commit,
            "source_zip_sha256": hashlib.sha256(source_zip).hexdigest(),
            "builds": [
                {
                    "id": build_id,
                    "name": name,
                    "compiler": compiler,
                    "openmp": openmp,
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
                }
                for build_id, name, compiler, openmp in (
                    ("msvc", "MSVC + Ninja", "MSVC 19.44", "vcomp140.dll"),
                    ("mingw", "MinGW-w64 + Ninja", "GCC 16.1.0", "libgomp"),
                )
            ],
            "commands": [
                {
                    "purpose": "测试命令",
                    "command": "ctest --test-dir build --output-on-failure",
                    "status": "PASS",
                    "log": "ctest.log",
                }
            ],
        }
        (performance / "benchmark_summary.json").write_text(
            json.dumps(summary),
            encoding="utf-8",
        )
        with (performance / "benchmark_samples.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=runner.PROCESS_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(records)
        for record in records:
            for field in (
                "raw_csv_path",
                "raw_json_path",
                "stdout_log_path",
                "stderr_log_path",
            ):
                path = performance / str(record[field])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"fixture={record['sample_id']} field={field}\n",
                    encoding="utf-8",
                )
        manifest["artifacts"] = [
            {
                "path": path.relative_to(performance).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in sorted(performance.rglob("*"))
            if path.is_file() and path.name != "run_manifest.json"
        ]
        (performance / "run_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        (build / "build_evidence.json").write_text(
            json.dumps(build_evidence),
            encoding="utf-8",
        )
        (build / "ctest.log").write_text(
            f"source={repository}\\demos\n",
            encoding="utf-8",
        )
        (report / "报告.md").write_text(
            "# 报告\n\n"
            "[`benchmark_samples.csv`](../../results/date/benchmark_samples.csv)\n"
            "[`benchmark_summary.json`](../../results/date/benchmark_summary.json)\n"
            "[`run_manifest.json`](../../results/date/run_manifest.json)\n",
            encoding="utf-8",
        )
        figures = report / "figures"
        figures.mkdir()
        (figures / "figure_qa.json").write_text(
            '{"status":"PASS"}\n',
            encoding="utf-8",
        )
        internal = root / "内部评估.md"
        internal.write_text(
            "# 仅供内部评估\n\n结论：PASS。\n",
            encoding="utf-8",
        )
        return performance, report, build, output, internal

    def make_options(self, root: Path):
        repository, demo, delivery_commit = self.prepare_source_repository(root)
        performance, report, build, output, internal = self.prepare_fixture(
            root,
            repository,
            demo,
            delivery_commit,
        )
        return argparse.Namespace(
            repository_root=repository,
            demo_root=demo,
            performance_evidence_dir=performance,
            report_dir=report,
            build_evidence_dir=build,
            internal_evaluation=internal,
            output_dir=output,
            delivery_date="2026-07-25",
            delivery_source_commit=delivery_commit,
            sanitize_root=[root],
        )

    def test_package_contains_nested_source_and_verified_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(packager.create_delivery(options), 0)
            packages = list(options.output_dir.glob("*.zip"))
            self.assertEqual(len(packages), 1)
            package = packages[0]
            result = packager.verify_delivery_file(package, check_sidecar=True)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["all_member_checksums_match"])
            self.assertTrue(result["source_zip"]["required_members_present"])

            with zipfile.ZipFile(package) as archive:
                root_name = packager.OUTER_ROOT_NAME
                report_text = archive.read(
                    f"{root_name}/02_测试报告/测试报告.md"
                ).decode("utf-8")
                self.assertIn(
                    "../03_性能原始证据/benchmark_samples.csv",
                    report_text,
                )
                delivery_manifest = json.loads(
                    archive.read(
                        f"{root_name}/06_校验/delivery_manifest.json"
                    )
                )
                self.assertEqual(
                    delivery_manifest["source"]["commit_sha"],
                    options.delivery_source_commit,
                )
                self.assertEqual(
                    delivery_manifest["source"]["performance_commit_sha"],
                    "a" * 40,
                )
                build_log = archive.read(
                    f"{root_name}/04_构建与CleanRoom证据/ctest.log"
                ).decode("utf-8")
                self.assertIn("<REPOSITORY_ROOT>", build_log)
                self.assertNotRegex(build_log, r"[A-Za-z]:[\\/]")

    def test_cache_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            cache = options.build_evidence_dir / "__pycache__"
            cache.mkdir()
            (cache / "bad.txt").write_text("bad", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "禁止目录"):
                packager.create_delivery(options)

    def test_tampered_summary_is_rejected_even_when_manifest_hash_is_updated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            summary_path = options.performance_evidence_dir / "benchmark_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["per_thread"][0]["parallel_total_ms"]["median"] = 123.0
            summary_path.write_text(json.dumps(summary), encoding="utf-8")

            manifest_path = options.performance_evidence_dir / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for artifact in manifest["artifacts"]:
                if artifact["path"] == "benchmark_summary.json":
                    artifact["size_bytes"] = summary_path.stat().st_size
                    artifact["sha256"] = sha256_file(summary_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "与 CSV 重新计算结果不一致"):
                packager.create_delivery(options)

    def test_tampered_artifact_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            samples_path = options.performance_evidence_dir / "benchmark_samples.csv"
            with samples_path.open("a", encoding="utf-8", newline="") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(RuntimeError, "大小不匹配|SHA-256 不匹配"):
                packager.create_delivery(options)

    def test_incomplete_build_counts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            build_path = options.build_evidence_dir / "build_evidence.json"
            build = json.loads(build_path.read_text(encoding="utf-8"))
            build["builds"][0]["ctest_passed"] = 9
            build_path.write_text(json.dumps(build), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "ctest_passed.*预期值 10"):
                packager.create_delivery(options)

    def test_source_zip_is_read_from_declared_commit_not_dirty_worktree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            options = self.make_options(root)
            committed_readme = subprocess.run(
                [
                    "git",
                    "show",
                    (
                        f"{options.delivery_source_commit}:"
                        "demos/csc3_symmetric_assembly_demo/README.md"
                    ),
                ],
                cwd=options.repository_root,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
            (options.demo_root / "README.md").write_text(
                "这段未提交内容不得进入交付包。\n",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                packager.create_delivery(options)
            package = next(options.output_dir.glob("*.zip"))
            with zipfile.ZipFile(package) as outer:
                source_zip = outer.read(
                    f"{packager.OUTER_ROOT_NAME}/01_源代码/"
                    f"{packager.SOURCE_ZIP_NAME}"
                )
            with zipfile.ZipFile(io.BytesIO(source_zip)) as source:
                packaged_readme = source.read(
                    f"{packager.SOURCE_ROOT_NAME}/README.md"
                )
            self.assertEqual(packaged_readme, committed_readme)
            self.assertNotIn("未提交内容".encode("utf-8"), packaged_readme)

    def test_minimal_source_cli_is_reproducible_and_self_verifying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, demo, commit_sha = self.prepare_source_repository(root)
            first = root / "first" / "CSC3对称稀疏组装Demo_源码.zip"
            second = root / "second" / "CSC3对称稀疏组装Demo_源码.zip"

            for output in (first, second):
                with contextlib.redirect_stdout(io.StringIO()):
                    status = packager.main(
                        [
                            "create-source",
                            "--repository-root",
                            str(repository),
                            "--demo-root",
                            str(demo),
                            "--source-commit",
                            commit_sha,
                            "--output",
                            str(output),
                        ]
                    )
                self.assertEqual(status, 0)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    packager.main(
                        ["verify-source", "--package", str(first)]
                    ),
                    0,
                )
            with zipfile.ZipFile(first) as source:
                names = set(source.namelist())
            self.assertTrue(packager.REQUIRED_SOURCE_MEMBERS <= names)
            self.assertFalse(any("/packaging/" in name for name in names))
            self.assertFalse(any("/tests/python/" in name for name in names))
            self.assertFalse(any(name.endswith("/MIGRATION.md") for name in names))


if __name__ == "__main__":
    unittest.main()
