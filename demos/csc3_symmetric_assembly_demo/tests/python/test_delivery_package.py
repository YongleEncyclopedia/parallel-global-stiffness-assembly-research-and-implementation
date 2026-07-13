#!/usr/bin/env python3
"""Contract tests for the deterministic CSC3 demo delivery archive."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
PACKAGER_SCRIPT = DEMO_ROOT / "scripts" / "create_delivery_package.py"


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class GitDemoFixture:
    def __init__(self, root: Path) -> None:
        self.repository = root / "repository"
        self.demo = self.repository / "demos" / "csc3_symmetric_assembly_demo"
        self.evidence = self.demo / "results" / "checked-evidence"
        self.report = self.demo / "reports" / "checked-report.zh-CN.md"

        ctest_xml = b'<testsuite tests="1" failures="0" errors="0" skipped="0"/>\n'
        benchmark_samples = b"sample,value\n0,1\n"
        benchmark_summary = b'{"status":"LOCAL_SMOKE"}\n'
        summary = b"# Summary\n"
        artifacts = [
            {
                "path": path,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for path, content in (
                ("ctest.xml", ctest_xml),
                ("benchmark_samples.csv", benchmark_samples),
                ("benchmark_summary.json", benchmark_summary),
                ("summary.md", summary),
            )
        ]
        run_manifest = (
            json.dumps(
                {
                    "schema_version": "fixture-v1",
                    "source": {"commit_sha": "b" * 40},
                    "artifacts": artifacts,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode()

        ci_tests = (
            "Csc3DemoTests",
            "Csc3DemoConsumer",
            "Csc3DemoCorrectness",
            "Csc3DemoBenchmarkTiming",
            "Csc3DemoBenchmarkEngine",
            "Csc3DemoBenchmarkIo",
            "Csc3DemoInpCase",
            "Csc3DemoWindHubBenchmark",
            "Csc3DemoBenchmarkRunner",
            "Csc3DemoAtomicContention",
        )
        cmake_lists = """cmake_minimum_required(VERSION 3.21)
project(Csc3PackageFixture NONE)
include(CTest)
foreach(test_name IN ITEMS
""" + "".join(f"    {name}\n" for name in ci_tests) + """ )
    add_test(NAME ${test_name} COMMAND "${CMAKE_COMMAND}" -E true)
    set_tests_properties(${test_name} PROPERTIES LABELS ci)
endforeach()
"""
        presets = {
            "version": 2,
            "configurePresets": [
                {
                    "name": "delivery",
                    "generator": "Ninja",
                    "binaryDir": "${sourceDir}/build/delivery",
                    "cacheVariables": {"BUILD_TESTING": "ON"},
                }
            ],
            "buildPresets": [{"name": "delivery", "configurePreset": "delivery"}],
            "testPresets": [{"name": "delivery", "configurePreset": "delivery"}],
        }
        external_consumer_cmake = b"""cmake_minimum_required(VERSION 3.21)
project(Csc3ExternalConsumerFixture NONE)
enable_testing()
add_test(NAME Csc3DemoExternalConsumer COMMAND \"${CMAKE_COMMAND}\" -E true)
"""

        files: dict[str, bytes] = {
            ".clang-format": b"BasedOnStyle: LLVM\n",
            "CMakeLists.txt": cmake_lists.encode(),
            "CMakePresets.json": (json.dumps(presets, indent=2) + "\n").encode(),
            "README.md": b"# Demo\r\n",
            "MIGRATION.md": b"# Migration\n",
            "docs/api-and-naming-contract.md": b"# API\n",
            "include/csc3_demo/assembly_helper.h": b"#pragma once\n",
            "src/assembly_helper.cpp": b"// source\n",
            "src/main.cpp": b"int main() { return 0; }\n",
            "tools/include/csc3_demo_tools/evidence.h": b"#pragma once\n",
            "tools/src/benchmark.cpp": b"// benchmark\n",
            "tests/assembly_helper_tests.cpp": b"// tests\n",
            "tests/consumer/csc3_demo_consumer.cpp": b"int main() { return 0; }\n",
            "tests/ctest/expected-ci-tests.txt": (
                "\n".join(ci_tests) + "\n"
            ).encode(),
            "tests/external_consumer/CMakeLists.txt": external_consumer_cmake,
            "tests/external_consumer/main.cpp": b"int main() { return 0; }\n",
            "tests/python/test_smoke.py": b"# test\n",
            "scripts/check_ctest_inventory.py": DEMO_ROOT.joinpath(
                "scripts/check_ctest_inventory.py"
            ).read_bytes(),
            "scripts/check_ctest_junit.py": DEMO_ROOT.joinpath(
                "scripts/check_ctest_junit.py"
            ).read_bytes(),
            "scripts/run_benchmark.py": b"# runner\n",
            "scripts/generate_test_report.py": b"# reporter\n",
            "scripts/create_delivery_package.py": b"# packager\n",
            "scripts/verify_delivery_package.py": b"# verifier\n",
            "packaging/README.md": b"# Delivery\n",
            "packaging/THIRD_PARTY_NOTICES.md": b"# Third-party notices\n",
            "packaging/INTERNAL_EVALUATION_ONLY.md": b"INTERNAL EVALUATION ONLY\n",
            "reports/checked-report.zh-CN.md": "# 测试报告\n".encode(),
            "results/checked-evidence/benchmark_samples.csv": benchmark_samples,
            "results/checked-evidence/benchmark_summary.json": benchmark_summary,
            "results/checked-evidence/run_manifest.json": run_manifest,
            "results/checked-evidence/ctest.xml": ctest_xml,
            "results/checked-evidence/README.md": b"# Evidence\n",
            "results/checked-evidence/summary.md": summary,
            # These tracked files must never enter the whitelist archive.
            ".DS_Store": b"garbage",
            "figures/huge.tiff": b"tiff",
            "build/generated.o": b"object",
            "scripts/unrelated_helper.py": b"# not part of delivery\n",
        }
        for relative, content in files.items():
            path = self.demo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        run(["git", "init"], self.repository)
        run(["git", "config", "user.name", "CSC3 Test"], self.repository)
        run(["git", "config", "user.email", "csc3@example.invalid"], self.repository)
        run(["git", "config", "core.autocrlf", "false"], self.repository)
        run(["git", "add", "."], self.repository)
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_DATE": "2026-07-13T00:00:00+00:00",
                "GIT_COMMITTER_DATE": "2026-07-13T00:00:00+00:00",
            }
        )
        subprocess.run(
            ["git", "commit", "-m", "fixture"],
            cwd=self.repository,
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def commit_changes(self, message: str) -> None:
        run(["git", "add", "."], self.repository)
        run(["git", "commit", "-m", message], self.repository)


class TemporaryDirectory(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-package-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()


class DeliveryPackageModuleTests(unittest.TestCase):
    def test_packager_module_exists(self) -> None:
        self.assertTrue(PACKAGER_SCRIPT.is_file())

    def test_delivery_policy_documents_are_explicit(self) -> None:
        packaging = DEMO_ROOT / "packaging"
        declaration = packaging / "INTERNAL_EVALUATION_ONLY.md"
        notices = packaging / "THIRD_PARTY_NOTICES.md"
        instructions = packaging / "README.md"
        self.assertTrue(declaration.is_file())
        self.assertTrue(notices.is_file())
        self.assertTrue(instructions.is_file())
        self.assertIn("INTERNAL EVALUATION ONLY", declaration.read_text(encoding="utf-8"))
        self.assertIn("No public license", declaration.read_text(encoding="utf-8"))
        self.assertIn("OpenMP", notices.read_text(encoding="utf-8"))
        instruction_text = instructions.read_text(encoding="utf-8")
        self.assertIn("create_delivery_package.py", instruction_text)
        self.assertIn("verify_delivery_package.py", instruction_text)
        self.assertIn("absolute paths", instruction_text)
        demo_readme = DEMO_ROOT.joinpath("README.md").read_text(encoding="utf-8")
        self.assertIn("packaging/README.md", demo_readme)
        self.assertIn("MANIFEST.sha256", demo_readme)


class DeterministicArchiveTests(TemporaryDirectory):
    def test_archive_is_deterministic_and_contains_only_the_delivery_whitelist(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package")
        fixture = GitDemoFixture(self.root)

        first = packager.create_delivery_package(
            fixture.demo, fixture.evidence, fixture.report, self.root / "out-one"
        )
        second = packager.create_delivery_package(
            fixture.demo, fixture.evidence, fixture.report, self.root / "out-two"
        )

        self.assertEqual(first.name, second.name)
        self.assertRegex(
            first.name,
            r"^csc3-symmetric-assembly-demo-v0\.2\.0\+[0-9a-f]{12}\.zip$",
        )
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(
            hashlib.sha256(first.read_bytes()).hexdigest(),
            hashlib.sha256(second.read_bytes()).hexdigest(),
        )

        package_root = first.stem
        with zipfile.ZipFile(first) as archive:
            members = archive.namelist()
            self.assertEqual(members, sorted(members))
            self.assertIn(f"{package_root}/BUILD_INFO.json", members)
            self.assertIn(f"{package_root}/MANIFEST.sha256", members)
            self.assertIn(f"{package_root}/src/assembly_helper.cpp", members)
            self.assertIn(f"{package_root}/.clang-format", members)
            self.assertIn(
                f"{package_root}/tests/external_consumer/CMakeLists.txt", members
            )
            self.assertIn(
                f"{package_root}/tests/ctest/expected-ci-tests.txt", members
            )
            self.assertIn(
                f"{package_root}/scripts/check_ctest_inventory.py", members
            )
            self.assertIn(
                f"{package_root}/results/checked-evidence/benchmark_samples.csv",
                members,
            )
            self.assertIn(
                f"{package_root}/reports/checked-report.zh-CN.md", members
            )
            self.assertFalse(any(".DS_Store" in name for name in members))
            self.assertFalse(any("figures/" in name for name in members))
            self.assertFalse(any("build/" in name for name in members))
            self.assertFalse(any(name.endswith(".tiff") for name in members))
            self.assertFalse(any("unrelated_helper.py" in name for name in members))

            for info in archive.infolist():
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o644)
                self.assertFalse(stat.S_ISLNK(info.external_attr >> 16))

            # Text comes from committed Git blobs and is normalized to LF.
            self.assertEqual(
                archive.read(f"{package_root}/README.md"), b"# Demo\n"
            )
            build_info = json.loads(
                archive.read(f"{package_root}/BUILD_INFO.json")
            )
            self.assertEqual(build_info["schema_version"], "csc3-demo-build-info-v1")
            self.assertEqual(build_info["version"], "0.2.0")
            self.assertFalse(build_info["source_tree_dirty"])
            self.assertEqual(build_info["distribution"], "INTERNAL EVALUATION ONLY")
            self.assertEqual(build_info["package_filename"], first.name)
            self.assertEqual(build_info["evidence_source_commit"], "b" * 40)
            self.assertFalse(build_info["evidence_source_matches_package_source"])

            manifest = archive.read(f"{package_root}/MANIFEST.sha256").decode()
            self.assertNotIn("MANIFEST.sha256", manifest)
            self.assertIn("BUILD_INFO.json", manifest)

    def test_dirty_tracked_file_is_rejected(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_dirty")
        fixture = GitDemoFixture(self.root)
        fixture.demo.joinpath("README.md").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "dirty"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, self.root / "out"
            )

    def test_untracked_file_is_rejected(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_untracked")
        fixture = GitDemoFixture(self.root)
        fixture.demo.joinpath("untracked.txt").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "untracked"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, self.root / "out"
            )

    def test_evidence_outside_demo_is_rejected(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_escape")
        fixture = GitDemoFixture(self.root)
        outside = self.root / "outside"
        outside.mkdir()

        with self.assertRaisesRegex(ValueError, "inside the demo"):
            packager.create_delivery_package(
                fixture.demo, outside, fixture.report, self.root / "out"
            )

    def test_stale_fixed_temporary_symlink_is_never_followed(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_symlink")
        fixture = GitDemoFixture(self.root)
        output = self.root / "out"
        output.mkdir()
        victim = self.root / "victim.txt"
        original = b"must remain unchanged\n"
        victim.write_bytes(original)
        commit_sha = run(["git", "rev-parse", "HEAD"], fixture.repository).stdout.strip()
        archive_name = (
            f"{packager.PACKAGE_BASENAME}-v{packager.DEMO_VERSION}"
            f"+{commit_sha[:12]}.zip"
        )
        stale_temporary = output / f".{archive_name}.tmp"
        stale_temporary.symlink_to(victim)

        archive = packager.create_delivery_package(
            fixture.demo, fixture.evidence, fixture.report, output
        )

        self.assertEqual(victim.read_bytes(), original)
        self.assertTrue(stale_temporary.is_symlink())
        self.assertFalse(archive.is_symlink())
        self.assertTrue(archive.is_file())

    def test_required_evidence_artifact_binding_cannot_be_omitted(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_missing_binding")
        fixture = GitDemoFixture(self.root)
        manifest_path = fixture.evidence / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"] = [
            record
            for record in manifest["artifacts"]
            if record["path"] != "benchmark_summary.json"
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        fixture.commit_changes("remove required evidence binding")

        with self.assertRaisesRegex(RuntimeError, "missing required artifact bindings"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, self.root / "out"
            )

    def test_crlf_evidence_with_stale_raw_hash_is_rejected_after_normalization(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_delivery_package_crlf")
        fixture = GitDemoFixture(self.root)
        samples_path = fixture.evidence / "benchmark_samples.csv"
        raw_crlf = b"sample,value\r\n0,1\r\n"
        samples_path.write_bytes(raw_crlf)
        manifest_path = fixture.evidence / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record = next(
            item for item in manifest["artifacts"] if item["path"] == "benchmark_samples.csv"
        )
        record["size_bytes"] = len(raw_crlf)
        record["sha256"] = hashlib.sha256(raw_crlf).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        fixture.commit_changes("record raw CRLF evidence hash")

        with self.assertRaisesRegex(RuntimeError, "benchmark_samples.csv.*normalized"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, self.root / "out"
            )


if __name__ == "__main__":
    unittest.main()
