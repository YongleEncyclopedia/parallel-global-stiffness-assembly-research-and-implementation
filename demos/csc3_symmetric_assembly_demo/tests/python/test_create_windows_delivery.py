"""Issue #54 Windows 交付 ZIP 的创建与自校验测试。"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = DEMO_ROOT.parents[1]
SCRIPT = DEMO_ROOT / "scripts" / "create_windows_delivery.py"


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


class WindowsDeliveryTests(unittest.TestCase):
    def prepare_fixture(self, root: Path):
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
        manifest = {
            "status": "PASS",
            "source": {
                "branch": "codex/issue-54-csc3-windows-delivery",
                "commit_sha": "a" * 40,
            },
            "input": input_facts,
        }
        summary = {
            "status": "PASS",
            "configuration": {
                "maximum_threads": 16,
                "warmup_count": 2,
                "repeat_count": 7,
            },
        }
        build_evidence = {
            "status": "PASS",
            "builds": [{"id": "msvc"}, {"id": "mingw"}],
        }
        (performance / "run_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        (performance / "benchmark_summary.json").write_text(
            json.dumps(summary),
            encoding="utf-8",
        )
        (performance / "benchmark_samples.csv").write_text(
            "sample_id,status\nsample-1,PASS\n",
            encoding="utf-8",
        )
        raw = performance / "raw" / "sample-1"
        raw.mkdir(parents=True)
        (raw / "stdout.log").write_text(
            f"evidence={performance}\\raw\\sample-1\n",
            encoding="utf-8",
        )
        (build / "build_evidence.json").write_text(
            json.dumps(build_evidence),
            encoding="utf-8",
        )
        (build / "ctest.log").write_text(
            f"source={REPOSITORY_ROOT}\\demos\n",
            encoding="utf-8",
        )
        (report / "报告.md").write_text(
            "# 报告\n\n"
            "[benchmark_samples.csv](../../results/date/benchmark_samples.csv)\n"
            "[benchmark_summary.json](../../results/date/benchmark_summary.json)\n"
            "[run_manifest.json](../../results/date/run_manifest.json)\n",
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
        performance, report, build, output, internal = self.prepare_fixture(root)
        return argparse.Namespace(
            repository_root=REPOSITORY_ROOT,
            demo_root=DEMO_ROOT,
            performance_evidence_dir=performance,
            report_dir=report,
            build_evidence_dir=build,
            internal_evaluation=internal,
            output_dir=output,
            delivery_date="2026-07-25",
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


if __name__ == "__main__":
    unittest.main()
