#!/usr/bin/env python3
"""Contract tests for the deterministic CSC3 demo delivery archive."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
PACKAGER_SCRIPT = DEMO_ROOT / "scripts" / "create_delivery_package.py"
REPORTER_SCRIPT = DEMO_ROOT / "scripts" / "generate_test_report.py"
TEST_DIRECTORY = Path(__file__).resolve().parent
if str(TEST_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_DIRECTORY))

from report_test_fixture import EvidenceFixture  # noqa: E402


EXPECTED_PACKAGING_PATHS = {
    "packaging/ACCEPTANCE_DECISION.schema.json",
    "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md",
    "packaging/ACCEPTANCE_MACHINE_FACTS.schema.json",
    "packaging/ACCEPTANCE_RECORD.schema.json",
    "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md",
    "packaging/INTERNAL_EVALUATION_ONLY.md",
    "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md",
    "packaging/README.md",
    "packaging/THIRD_PARTY_NOTICES.md",
    "packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md",
}
EXPECTED_ROOT_DELIVERY_PATHS = {
    "requirements-test.txt",
    "scripts/acceptance_core.py",
    "scripts/acceptance_publication.py",
    "scripts/acceptance_rendering.py",
    "scripts/create_internal_handoff.py",
    "scripts/finalize_delivery.py",
    "scripts/formal_host.py",
    "scripts/prepare_acceptance_materials.py",
    "scripts/validate_acceptance_record.py",
}
TASK1_ACCEPTANCE_TEST_PATHS = {
    "tests/python/acceptance_test_fixture.py",
    "tests/python/report_test_fixture.py",
    "tests/python/test_delivery_package.py",
    "tests/python/test_prepare_acceptance_materials.py",
}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
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


def create_external_formal_inputs(
    root: Path,
    source_commit: str,
    *,
    evidence_level: str = "formal",
    report_intent: str = "delivery",
    formal_gate_pass: bool = True,
) -> tuple[Path, Path, bytes]:
    """Create canonical formal evidence/report inputs outside a fixture repository."""
    evidence = EvidenceFixture(
        root,
        evidence_level=evidence_level,
        report_intent=report_intent,
        formal_gate_pass=formal_gate_pass,
    )
    evidence.manifest["source"]["commit_sha"] = source_commit
    for identity_check in evidence.manifest["identity_checks"]:
        identity_check["source"]["commit_sha"] = source_commit
    evidence.write_manifest()

    reporter = load_script(REPORTER_SCRIPT, "csc3_report_for_external_package_fixture")
    bundle = reporter.validate_evidence_bundle(evidence.manifest_path)
    canonical_report = reporter.render_report(bundle).encode("utf-8")
    report = root.parent / f"{root.name}-test-report.zh-CN.md"
    report.write_bytes(canonical_report)
    return evidence.root, report, canonical_report


def assert_packaged_acceptance_documents(
    test_case: unittest.TestCase,
    archive: zipfile.ZipFile,
    package_root: str,
) -> None:
    """Require the complete acceptance set and resolvable packaging links."""
    prefix = f"{package_root}/"
    packaged_paths = {
        name.removeprefix(prefix)
        for name in archive.namelist()
        if name.startswith(f"{prefix}packaging/")
    }
    test_case.assertEqual(packaged_paths, EXPECTED_PACKAGING_PATHS)
    archive_paths = {
        name.removeprefix(prefix)
        for name in archive.namelist()
        if name.startswith(prefix)
    }
    test_case.assertTrue(EXPECTED_ROOT_DELIVERY_PATHS <= archive_paths)

    readme_path = PurePosixPath("packaging/README.md")
    readme = archive.read(f"{prefix}{readme_path}").decode("utf-8")
    relative_links = [
        target
        for target in MARKDOWN_LINK.findall(readme)
        if not target.startswith(("#", "/"))
        and URI_SCHEME.match(target) is None
    ]
    test_case.assertEqual(
        set(relative_links),
        {
            "ACCEPTANCE_CHECKLIST.zh-CN.md",
            "ACCEPTANCE_DECISION.schema.json",
            "ACCEPTANCE_MACHINE_FACTS.schema.json",
            "ACCEPTANCE_RECORD.schema.json",
            "DELIVERY_NOTE_TEMPLATE.zh-CN.md",
            "LINUX_FORMAL_RUNBOOK.zh-CN.md",
            "TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md",
        },
    )
    for target in relative_links:
        resolved = (readme_path.parent / target).as_posix()
        test_case.assertIn(resolved, packaged_paths)


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
            "requirements-test.txt": b"jsonschema>=4.23,<5\n",
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
            "tests/ctest/expected-cpp-tests.txt": (
                "\n".join(
                    name for name in ci_tests if name != "Csc3DemoBenchmarkRunner"
                )
                + "\n"
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
            "scripts/run_benchmark.py": DEMO_ROOT.joinpath(
                "scripts/run_benchmark.py"
            ).read_bytes(),
            "scripts/generate_test_report.py": DEMO_ROOT.joinpath(
                "scripts/generate_test_report.py"
            ).read_bytes(),
            "scripts/create_delivery_package.py": DEMO_ROOT.joinpath(
                "scripts/create_delivery_package.py"
            ).read_bytes(),
            "scripts/create_internal_handoff.py": DEMO_ROOT.joinpath(
                "scripts/create_internal_handoff.py"
            ).read_bytes(),
            "scripts/acceptance_core.py": DEMO_ROOT.joinpath(
                "scripts/acceptance_core.py"
            ).read_bytes(),
            "scripts/acceptance_publication.py": DEMO_ROOT.joinpath(
                "scripts/acceptance_publication.py"
            ).read_bytes(),
            "scripts/acceptance_rendering.py": DEMO_ROOT.joinpath(
                "scripts/acceptance_rendering.py"
            ).read_bytes(),
            "scripts/prepare_acceptance_materials.py": DEMO_ROOT.joinpath(
                "scripts/prepare_acceptance_materials.py"
            ).read_bytes(),
            "scripts/finalize_delivery.py": DEMO_ROOT.joinpath(
                "scripts/finalize_delivery.py"
            ).read_bytes(),
            "scripts/formal_host.py": DEMO_ROOT.joinpath(
                "scripts/formal_host.py"
            ).read_bytes(),
            "scripts/validate_acceptance_record.py": DEMO_ROOT.joinpath(
                "scripts/validate_acceptance_record.py"
            ).read_bytes(),
            "scripts/verify_delivery_package.py": DEMO_ROOT.joinpath(
                "scripts/verify_delivery_package.py"
            ).read_bytes(),
            "packaging/README.md": DEMO_ROOT.joinpath(
                "packaging/README.md"
            ).read_bytes(),
            "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md": DEMO_ROOT.joinpath(
                "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md"
            ).read_bytes(),
            "packaging/ACCEPTANCE_RECORD.schema.json": DEMO_ROOT.joinpath(
                "packaging/ACCEPTANCE_RECORD.schema.json"
            ).read_bytes(),
            "packaging/ACCEPTANCE_MACHINE_FACTS.schema.json": DEMO_ROOT.joinpath(
                "packaging/ACCEPTANCE_MACHINE_FACTS.schema.json"
            ).read_bytes(),
            "packaging/ACCEPTANCE_DECISION.schema.json": DEMO_ROOT.joinpath(
                "packaging/ACCEPTANCE_DECISION.schema.json"
            ).read_bytes(),
            "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md": DEMO_ROOT.joinpath(
                "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md"
            ).read_bytes(),
            "packaging/THIRD_PARTY_NOTICES.md": b"# Third-party notices\n",
            "packaging/INTERNAL_EVALUATION_ONLY.md": b"INTERNAL EVALUATION ONLY\n",
            "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md": DEMO_ROOT.joinpath(
                "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md"
            ).read_bytes(),
            "packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md": DEMO_ROOT.joinpath(
                "packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md"
            ).read_bytes(),
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


def add_task1_acceptance_merged_tree(fixture: GitDemoFixture) -> None:
    """Add Task 1 tests and execute them in the fixture clean room."""
    for relative in sorted(TASK1_ACCEPTANCE_TEST_PATHS):
        destination = fixture.demo.joinpath(*PurePosixPath(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(DEMO_ROOT.joinpath(relative).read_bytes())

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
    lines = [
        "cmake_minimum_required(VERSION 3.21)",
        "project(Csc3Task1MergedFixture NONE)",
        "include(CTest)",
        "find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)",
    ]
    for test_name in ci_tests:
        if test_name == "Csc3DemoBenchmarkRunner":
            lines.extend(
                (
                    "add_test(",
                    f"  NAME {test_name}",
                    "  COMMAND ${Python3_EXECUTABLE} -m unittest discover",
                    "    -s ${CMAKE_CURRENT_SOURCE_DIR}/tests/python",
                    "    -p test_prepare_acceptance_materials.py -v",
                    ")",
                )
            )
        else:
            lines.append(
                f"add_test(NAME {test_name} COMMAND \"${{CMAKE_COMMAND}}\" -E true)"
            )
        lines.append(f"set_tests_properties({test_name} PROPERTIES LABELS ci)")
    (fixture.demo / "CMakeLists.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    fixture.commit_changes("simulate merged Task 1 acceptance tree")


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
        self.assertIn("DELIVERY_NOTE_TEMPLATE.zh-CN.md", instruction_text)
        self.assertNotIn("DELIVERY_NOTE.zh-CN.md", instruction_text)
        self.assertIn("absolute paths", instruction_text)
        self.assertIn("parent path is the publication trust boundary", instruction_text)
        self.assertIn("parent symlinks are followed deliberately", instruction_text)
        demo_readme = DEMO_ROOT.joinpath("README.md").read_text(encoding="utf-8")
        self.assertIn("packaging/README.md", demo_readme)
        self.assertIn("MANIFEST.sha256", demo_readme)

    def test_two_stage_acceptance_handoff_is_normative_and_not_manual(self) -> None:
        packaging_readme = DEMO_ROOT.joinpath("packaging/README.md").read_text(
            encoding="utf-8"
        )
        demo_readme = DEMO_ROOT.joinpath("README.md").read_text(encoding="utf-8")
        for document in (packaging_readme, demo_readme):
            normalized = " ".join(document.split())
            with self.subTest(document=document[:40]):
                handoff_tokens = (
                    "`draft`",
                    "`render`",
                    "`validate`",
                    "`finalize`",
                )
                positions = [normalized.index(token) for token in handoff_tokens]
                self.assertEqual(positions, sorted(positions))
                self.assertIn("prepare_acceptance_materials.py", document)
                self.assertIn("acceptance-machine-facts.json", document)
                self.assertIn("acceptance-decision.json", document)
                self.assertIn("deterministic renderer outputs", document)
                self.assertIn("INTERNAL EVALUATION ONLY", document)

        normalized_packaging = " ".join(packaging_readme.split())
        normalized_demo = " ".join(demo_readme.split())
        self.assertNotIn(
            "all four approval roles must complete the external acceptance "
            "record, checklist, and delivery note",
            normalized_packaging,
        )
        self.assertNotIn("the sender copies and completes", normalized_demo)


class DeterministicArchiveTests(TemporaryDirectory):
    def test_formal_fixture_artifacts_use_canonical_lf_bytes(self) -> None:
        fixture = EvidenceFixture(
            self.root / "canonical-lf",
            evidence_level="formal",
            report_intent="delivery",
        )
        artifacts = {
            record["path"]: record
            for record in fixture.manifest["artifacts"]
        }
        self.assertNotIn(b"\r", fixture.manifest_path.read_bytes())
        for relative in (
            "ctest.xml",
            "benchmark_samples.csv",
            "benchmark_summary.json",
            "summary.md",
        ):
            with self.subTest(relative=relative):
                content = (fixture.root / relative).read_bytes()
                self.assertNotIn(b"\r", content)
                self.assertEqual(artifacts[relative]["size_bytes"], len(content))
                self.assertEqual(
                    artifacts[relative]["sha256"],
                    hashlib.sha256(content).hexdigest(),
                )

    def test_committed_mode_rejects_git_replace_blob_substitution(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_blob_replace_attack",
        )
        fixture = GitDemoFixture(self.root)
        original_blob = run(
            [
                "git",
                "rev-parse",
                "HEAD:demos/csc3_symmetric_assembly_demo/README.md",
            ],
            fixture.repository,
        ).stdout.strip()
        replacement_marker = b"# replacement blob must never be packaged\n"
        replacement_blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=fixture.repository,
            check=True,
            input=replacement_marker,
            stdout=subprocess.PIPE,
        ).stdout.decode("ascii").strip()
        run(
            ["git", "replace", original_blob, replacement_blob],
            fixture.repository,
        )
        fixture.demo.joinpath("README.md").write_bytes(replacement_marker)

        output = self.root / "blob-replace-attack-out"
        with self.assertRaisesRegex(
            packager.DeliveryPackageError,
            r"replace|object interpretation",
        ):
            packager.create_delivery_package(
                fixture.demo,
                fixture.evidence,
                fixture.report,
                output,
            )
        self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_committed_mode_rejects_git_replace_object_substitution(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_replace_attack",
        )
        fixture = GitDemoFixture(self.root)
        original_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        replacement_marker = "# replacement tree must never be packaged\n"
        fixture.demo.joinpath("README.md").write_text(
            replacement_marker,
            encoding="utf-8",
        )
        fixture.commit_changes("replacement tree")
        replacement_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        run(
            ["git", "replace", original_commit, replacement_commit],
            fixture.repository,
        )
        run(["git", "checkout", "--detach", original_commit], fixture.repository)
        self.assertEqual(
            original_commit,
            run(["git", "rev-parse", "HEAD"], fixture.repository).stdout.strip(),
        )
        self.assertEqual(
            replacement_marker,
            fixture.demo.joinpath("README.md").read_text(encoding="utf-8"),
        )

        output = self.root / "replace-attack-out"
        with self.assertRaisesRegex(
            packager.DeliveryPackageError,
            r"replace|object interpretation",
        ):
            packager.create_delivery_package(
                fixture.demo,
                fixture.evidence,
                fixture.report,
                output,
            )
        self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_packager_rejects_non_strict_evidence_manifest_json(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_strict_manifest",
        )
        fixture = GitDemoFixture(self.root)
        original = fixture.evidence.joinpath("run_manifest.json").read_bytes()
        attacks = {
            "duplicate": (
                b'{\n  "source": {"commit_sha": '
                b'"cccccccccccccccccccccccccccccccccccccccc"},'
            ),
            "overflow": b'{\n  "unused_overflow": 1e999,',
        }
        for name, prefix in attacks.items():
            with self.subTest(name=name):
                fixture.evidence.joinpath("run_manifest.json").write_bytes(
                    original.replace(b"{", prefix, 1)
                )
                fixture.commit_changes(f"strict JSON attack: {name}")
                with self.assertRaisesRegex(
                    packager.DeliveryPackageError,
                    r"strict|duplicate|non-finite|invalid JSON",
                ):
                    packager.create_delivery_package(
                        fixture.demo,
                        fixture.evidence,
                        fixture.report,
                        self.root / f"strict-{name}-out",
                    )

    def test_committed_mode_rejects_head_advance_after_commit_capture(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_committed_head_race",
        )
        fixture = GitDemoFixture(self.root)
        commit_a = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        output = self.root / "committed-head-race-out"
        original_git_text = packager._git_text
        capture_seen = False

        def advance_head_after_capture(
            repository_root: Path,
            arguments,
        ) -> str:
            nonlocal capture_seen
            captured_arguments = tuple(arguments)
            value = original_git_text(repository_root, captured_arguments)
            if (
                not capture_seen
                and captured_arguments
                in {
                    ("rev-parse", "HEAD"),
                    ("rev-parse", "--verify", "HEAD^{commit}"),
                }
            ):
                capture_seen = True
                fixture.demo.joinpath("README.md").write_text(
                    "# HEAD advanced after package commit capture\n",
                    encoding="utf-8",
                )
                fixture.commit_changes("advance HEAD after package commit capture")
            return value

        error: RuntimeError | None = None
        packager._git_text = advance_head_after_capture
        try:
            try:
                packager.create_delivery_package(
                    fixture.demo,
                    fixture.evidence,
                    fixture.report,
                    output,
                )
            except RuntimeError as caught:
                error = caught
        finally:
            packager._git_text = original_git_text

        commit_b = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        self.assertTrue(capture_seen)
        self.assertNotEqual(commit_a, commit_b)
        with self.subTest(contract="fail closed after HEAD advance"):
            self.assertIsNotNone(error)
            if error is not None:
                self.assertRegex(str(error), r"HEAD.*changed|changed.*HEAD")
        with self.subTest(contract="never publish ZIP after HEAD advance"):
            self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_external_formal_mode_rechecks_head_immediately_before_publish(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_final_head_race",
        )
        fixture = GitDemoFixture(self.root)
        commit_a = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "external-final-head-race-evidence",
            commit_a,
        )
        output = self.root / "external-final-head-race-out"
        original_fsync = packager.os.fsync
        fsync_seen = False

        def advance_head_after_fsync(file_descriptor: int) -> None:
            nonlocal fsync_seen
            original_fsync(file_descriptor)
            fsync_seen = True
            fixture.demo.joinpath("README.md").write_text(
                "# HEAD advanced after the temporary ZIP was fsynced\n",
                encoding="utf-8",
            )
            fixture.commit_changes("advance HEAD after temporary ZIP fsync")

        error: RuntimeError | None = None
        packager.os.fsync = advance_head_after_fsync
        try:
            try:
                packager.create_external_formal_package(
                    fixture.demo,
                    evidence,
                    report,
                    "external-final-head-race",
                    output,
                )
            except RuntimeError as caught:
                error = caught
        finally:
            packager.os.fsync = original_fsync

        commit_b = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        self.assertTrue(fsync_seen)
        self.assertNotEqual(commit_a, commit_b)
        with self.subTest(contract="fail closed at final HEAD gate"):
            self.assertIsNotNone(error)
            if error is not None:
                self.assertRegex(str(error), r"HEAD.*changed|changed.*HEAD")
        with self.subTest(contract="never publish external formal ZIP"):
            self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_snapshot_git_reads_are_pinned_to_the_captured_commit(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_pinned_git_reads",
        )
        fixture = GitDemoFixture(self.root)
        commit_sha = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        original_run_git = packager._run_git
        git_calls: list[tuple[str, ...]] = []

        def record_git_call(repository_root: Path, arguments, *, check: bool = True):
            captured_arguments = tuple(arguments)
            git_calls.append(captured_arguments)
            return original_run_git(
                repository_root,
                captured_arguments,
                check=check,
            )

        packager._run_git = record_git_call
        try:
            packager.create_delivery_package(
                fixture.demo,
                fixture.evidence,
                fixture.report,
                self.root / "pinned-git-read-out",
            )
        finally:
            packager._run_git = original_run_git

        self.assertIn(
            ("show", "-s", "--format=%ct", commit_sha),
            git_calls,
        )
        self.assertTrue(
            any(
                arguments[:5]
                == ("ls-tree", "-r", "-z", "--full-tree", commit_sha)
                for arguments in git_calls
            )
        )
        expected_diff_calls = {
            ("diff", "--quiet", commit_sha, "--"),
            ("diff", "--cached", "--quiet", commit_sha, "--"),
        }
        actual_diff_calls = {
            arguments for arguments in git_calls if arguments and arguments[0] == "diff"
        }
        self.assertEqual(actual_diff_calls, expected_diff_calls)
        blob_calls = [
            arguments
            for arguments in git_calls
            if arguments and arguments[0] == "cat-file"
        ]
        self.assertTrue(blob_calls)
        for arguments in blob_calls:
            with self.subTest(blob_read=arguments):
                self.assertEqual(arguments[:2], ("cat-file", "blob"))
                self.assertEqual(len(arguments), 3)
                self.assertRegex(arguments[2], r"^[0-9a-f]{40}$")
        mutable_snapshot_reads = [
            arguments
            for arguments in git_calls
            if arguments
            and arguments[0] in {"diff", "ls-tree", "show"}
            and "HEAD" in arguments
        ]
        self.assertEqual(mutable_snapshot_reads, [])

    def test_publish_rejects_repository_dirtied_after_members_are_captured(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_final_dirty_race",
        )
        fixture = GitDemoFixture(self.root)
        output = self.root / "final-dirty-race-out"
        original_fsync = packager.os.fsync
        fsync_seen = False

        def dirty_repository_after_fsync(file_descriptor: int) -> None:
            nonlocal fsync_seen
            original_fsync(file_descriptor)
            fsync_seen = True
            fixture.demo.joinpath("README.md").write_text(
                "dirty after the temporary ZIP was fsynced\n",
                encoding="utf-8",
            )

        error: RuntimeError | None = None
        packager.os.fsync = dirty_repository_after_fsync
        try:
            try:
                packager.create_delivery_package(
                    fixture.demo,
                    fixture.evidence,
                    fixture.report,
                    output,
                )
            except RuntimeError as caught:
                error = caught
        finally:
            packager.os.fsync = original_fsync

        self.assertTrue(fsync_seen)
        with self.subTest(contract="fail closed at final clean gate"):
            self.assertIsNotNone(error)
            if error is not None:
                self.assertRegex(str(error), r"dirty")
        with self.subTest(contract="never publish ZIP from dirty repository"):
            self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_valid_external_formal_bundle_is_packaged_from_exact_source_commit(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_create_external_formal_package")
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, canonical_report = create_external_formal_inputs(
            self.root / "external-formal-evidence",
            source_commit,
        )

        archive_path = packager.create_external_formal_package(
            fixture.demo,
            evidence,
            report,
            "linux-intel-formal",
            self.root / "external-out",
        )

        package_root = archive_path.stem
        evidence_prefix = f"{package_root}/results/linux-intel-formal/"
        report_member = (
            f"{package_root}/reports/"
            "linux-intel-formal-test-report.zh-CN.md"
        )
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.namelist()
            assert_packaged_acceptance_documents(self, archive, package_root)
            packaged_evidence = {
                name.removeprefix(evidence_prefix)
                for name in members
                if name.startswith(evidence_prefix)
            }
            self.assertEqual(
                packaged_evidence,
                {
                    "run_manifest.json",
                    "ctest.xml",
                    "benchmark_samples.csv",
                    "benchmark_summary.json",
                    "summary.md",
                },
            )
            self.assertEqual(archive.read(report_member), canonical_report)
            build_info = json.loads(
                archive.read(f"{package_root}/BUILD_INFO.json")
            )
            self.assertEqual(build_info["source_commit"], source_commit)
            self.assertEqual(build_info["evidence_source_commit"], source_commit)
            self.assertIs(
                build_info["evidence_source_matches_package_source"], True
            )
            self.assertEqual(
                build_info["evidence_directory"],
                "results/linux-intel-formal",
            )
            self.assertEqual(
                build_info["report"],
                "reports/linux-intel-formal-test-report.zh-CN.md",
            )
            self.assertNotIn(str(evidence), json.dumps(build_info, sort_keys=True))
            self.assertNotIn(str(report), json.dumps(build_info, sort_keys=True))
            self.assertFalse(any(str(evidence) in name for name in members))
            self.assertFalse(any(str(report) in name for name in members))

    def test_identical_external_inputs_produce_byte_identical_archives(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_deterministic",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "deterministic-formal-evidence",
            source_commit,
        )

        first = packager.create_external_formal_package(
            fixture.demo,
            evidence,
            report,
            "deterministic-formal",
            self.root / "external-out-one",
        )
        second = packager.create_external_formal_package(
            fixture.demo,
            evidence,
            report,
            "deterministic-formal",
            self.root / "external-out-two",
        )

        self.assertEqual(first.name, second.name)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_external_formal_source_commit_mismatch_is_rejected_before_write(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_source_mismatch",
        )
        fixture = GitDemoFixture(self.root)
        evidence, report, _ = create_external_formal_inputs(
            self.root / "mismatched-formal-evidence",
            "a" * 40,
        )
        output = self.root / "mismatched-out"

        with self.assertRaisesRegex(RuntimeError, "source.*commit|commit.*source"):
            packager.create_external_formal_package(
                fixture.demo,
                evidence,
                report,
                "mismatched-formal",
                output,
            )

        self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_one_byte_external_report_drift_is_rejected_before_write(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_report_drift",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "report-drift-formal-evidence",
            source_commit,
        )
        report.write_bytes(report.read_bytes() + b"x")
        output = self.root / "report-drift-out"

        with self.assertRaisesRegex(RuntimeError, "canonical|report"):
            packager.create_external_formal_package(
                fixture.demo,
                evidence,
                report,
                "report-drift-formal",
                output,
            )

        self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_external_evidence_is_validated_from_one_captured_snapshot(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_snapshot",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "snapshot-formal-evidence",
            source_commit,
        )
        original_summary = (evidence / "summary.md").read_bytes()
        reporter = load_script(REPORTER_SCRIPT, "csc3_report_for_snapshot_test")

        class MutatingReporter:
            def validate_evidence_bundle(self, manifest_path: Path):
                (evidence / "summary.md").write_bytes(b"changed after capture\n")
                return reporter.validate_evidence_bundle(manifest_path)

            def render_report(self, bundle):
                return reporter.render_report(bundle)

        packager._load_trusted_report_generator = lambda: MutatingReporter()
        archive_path = packager.create_external_formal_package(
            fixture.demo,
            evidence,
            report,
            "snapshot-formal",
            self.root / "snapshot-out",
        )

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(
                archive.read(
                    f"{archive_path.stem}/results/snapshot-formal/summary.md"
                ),
                original_summary,
            )

    def test_external_mode_rejects_nonpass_or_nonformal_delivery_evidence(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_status_contract",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        cases = (
            ("local-smoke", "local-smoke", True),
            ("formal", "local-smoke", True),
            ("formal", "delivery", False),
        )
        for index, (evidence_level, report_intent, formal_gate_pass) in enumerate(cases):
            with self.subTest(
                evidence_level=evidence_level,
                report_intent=report_intent,
                formal_gate_pass=formal_gate_pass,
            ):
                evidence, report, _ = create_external_formal_inputs(
                    self.root / f"invalid-status-evidence-{index}",
                    source_commit,
                    evidence_level=evidence_level,
                    report_intent=report_intent,
                    formal_gate_pass=formal_gate_pass,
                )
                output = self.root / f"invalid-status-out-{index}"
                with self.assertRaisesRegex(
                    RuntimeError,
                    "formal.*delivery.*PASS|PASS.*formal.*delivery",
                ):
                    packager.create_external_formal_package(
                        fixture.demo,
                        evidence,
                        report,
                        f"invalid-status-{index}",
                        output,
                    )
                self.assertFalse(
                    any(output.glob("*.zip")) if output.exists() else False
                )

    def test_external_evidence_symlink_missing_or_extra_file_is_rejected_before_write(
        self,
    ) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_file_contract",
        )
        cases = ("symlink", "missing", "extra")
        for case in cases:
            with self.subTest(case=case):
                case_root = self.root / case
                fixture = GitDemoFixture(case_root)
                source_commit = run(
                    ["git", "rev-parse", "HEAD"], fixture.repository
                ).stdout.strip()
                evidence, report, _ = create_external_formal_inputs(
                    case_root / "external-formal-evidence",
                    source_commit,
                )
                if case == "symlink":
                    summary = evidence / "summary.md"
                    target = evidence / "summary-target.md"
                    summary.rename(target)
                    summary.symlink_to(target.name)
                elif case == "missing":
                    (evidence / "summary.md").unlink()
                else:
                    (evidence / "unexpected.txt").write_text(
                        "unexpected\n", encoding="utf-8"
                    )
                output = case_root / "out"

                with self.assertRaisesRegex(
                    RuntimeError,
                    "exactly|missing|extra|symbolic|regular",
                ):
                    packager.create_external_formal_package(
                        fixture.demo,
                        evidence,
                        report,
                        f"file-contract-{case}",
                        output,
                    )

                self.assertFalse(
                    any(output.glob("*.zip")) if output.exists() else False
                )

    def test_external_report_symlink_is_rejected_before_write(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_report_symlink",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, canonical = create_external_formal_inputs(
            self.root / "report-symlink-formal-evidence",
            source_commit,
        )
        target = self.root / "canonical-report-target.md"
        target.write_bytes(canonical)
        report.unlink()
        report.symlink_to(target)
        output = self.root / "report-symlink-out"

        with self.assertRaisesRegex(RuntimeError, "symbolic|regular"):
            packager.create_external_formal_package(
                fixture.demo,
                evidence,
                report,
                "report-symlink-formal",
                output,
            )

        self.assertFalse(any(output.glob("*.zip")) if output.exists() else False)

    def test_external_inputs_must_resolve_outside_the_git_repository(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_repository_boundary",
        )
        for case in ("evidence", "report"):
            with self.subTest(case=case):
                case_root = self.root / f"inside-{case}"
                fixture = GitDemoFixture(case_root)
                source_commit = run(
                    ["git", "rev-parse", "HEAD"], fixture.repository
                ).stdout.strip()
                if case == "evidence":
                    evidence, inside_report, _ = create_external_formal_inputs(
                        fixture.repository / "host-formal-evidence",
                        source_commit,
                    )
                    report = case_root / "outside-report.md"
                    report.write_bytes(inside_report.read_bytes())
                    inside_report.unlink()
                else:
                    evidence, outside_report, _ = create_external_formal_inputs(
                        case_root / "outside-formal-evidence",
                        source_commit,
                    )
                    report = fixture.repository / "host-report.md"
                    report.write_bytes(outside_report.read_bytes())
                    outside_report.unlink()
                fixture.commit_changes(f"track inside {case} input")
                output = case_root / "out"

                with self.assertRaisesRegex(
                    RuntimeError,
                    "outside.*Git repository|outside.*repository",
                ):
                    packager.create_external_formal_package(
                        fixture.demo,
                        evidence,
                        report,
                        f"inside-{case}",
                        output,
                    )

                self.assertFalse(
                    any(output.glob("*.zip")) if output.exists() else False
                )

    def test_unsafe_external_bundle_ids_are_rejected_before_write(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_bundle_id",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "bundle-id-formal-evidence",
            source_commit,
        )
        unsafe_ids = (
            "",
            "../escape",
            "Uppercase",
            "-leading-hyphen",
            ".leading-dot",
            "contains/slash",
            "contains space",
            "a" * 129,
        )
        for index, bundle_id in enumerate(unsafe_ids):
            with self.subTest(bundle_id=bundle_id):
                output = self.root / f"unsafe-bundle-out-{index}"
                with self.assertRaisesRegex(RuntimeError, "bundle ID|bundle-id|unsafe"):
                    packager.create_external_formal_package(
                        fixture.demo,
                        evidence,
                        report,
                        bundle_id,
                        output,
                    )
                self.assertFalse(
                    any(output.glob("*.zip")) if output.exists() else False
                )

    def test_cli_accepts_the_complete_external_formal_mode(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_cli_happy",
        )
        fixture = GitDemoFixture(self.root)
        source_commit = run(
            ["git", "rev-parse", "HEAD"], fixture.repository
        ).stdout.strip()
        evidence, report, _ = create_external_formal_inputs(
            self.root / "cli-formal-evidence",
            source_commit,
        )
        output = self.root / "cli-out"
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return_code = packager.main(
                [
                    "--external-evidence-dir",
                    str(evidence),
                    "--external-report",
                    str(report),
                    "--bundle-id",
                    "cli-formal",
                    "--out-dir",
                    str(output),
                    "--demo-root",
                    str(fixture.demo),
                ]
            )

        self.assertEqual(return_code, 0, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertTrue(Path(payload["archive"]).is_file())

    def test_cli_rejects_partial_mixed_modes_and_unsafe_bundle_ids(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_external_formal_package_cli_contract",
        )
        cases = (
            (
                "external-evidence-only",
                ["--external-evidence-dir", "/outside/evidence"],
                "three external options.*together",
            ),
            (
                "external-report-and-id-only",
                [
                    "--external-report",
                    "/outside/report.md",
                    "--bundle-id",
                    "formal",
                ],
                "three external options.*together",
            ),
            (
                "legacy-evidence-only",
                ["--evidence-dir", "results/evidence"],
                "legacy options.*together|--evidence-dir.*--report",
            ),
            (
                "mixed-modes",
                [
                    "--evidence-dir",
                    "results/evidence",
                    "--report",
                    "reports/report.md",
                    "--external-evidence-dir",
                    "/outside/evidence",
                    "--external-report",
                    "/outside/report.md",
                    "--bundle-id",
                    "formal",
                ],
                "mutually exclusive",
            ),
            (
                "unsafe-bundle-id",
                [
                    "--external-evidence-dir",
                    "/outside/evidence",
                    "--external-report",
                    "/outside/report.md",
                    "--bundle-id",
                    "../escape",
                ],
                "bundle ID|bundle-id",
            ),
        )
        for name, arguments, expected_error in cases:
            with self.subTest(name=name):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        packager.main(arguments)
                self.assertEqual(raised.exception.code, 2)
                self.assertRegex(stderr.getvalue(), expected_error)

    def test_cli_digest_is_bound_before_published_path_mutation(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_cli_digest_snapshot",
        )
        fixture = GitDemoFixture(self.root)
        output = self.root / "cli-digest-out"
        published: dict[str, str] = {}
        real_link = packager.os.link

        def link_then_mutate(source: object, destination: object) -> None:
            real_link(source, destination)
            destination_path = Path(destination)
            published["sha256"] = hashlib.sha256(
                destination_path.read_bytes()
            ).hexdigest()
            destination_path.write_bytes(b"replacement after publication\n")

        stdout = io.StringIO()
        with mock.patch.object(
            packager.os,
            "link",
            side_effect=link_then_mutate,
        ), contextlib.redirect_stdout(stdout):
            return_code = packager.main(
                [
                    "--demo-root",
                    str(fixture.demo),
                    "--evidence-dir",
                    str(fixture.evidence),
                    "--report",
                    str(fixture.report),
                    "--out-dir",
                    str(output),
                ]
            )

        self.assertEqual(return_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["sha256"], published["sha256"])
        self.assertNotEqual(
            payload["sha256"],
            hashlib.sha256(Path(payload["archive"]).read_bytes()).hexdigest(),
        )

    def test_publish_digest_is_bound_to_archive_in_private_staging(self) -> None:
        packager = load_script(
            PACKAGER_SCRIPT,
            "csc3_create_delivery_package_private_staging",
        )
        fixture = GitDemoFixture(self.root)
        output = self.root / "private-staging-out"
        repository_checks = 0
        direct_temporary_files: list[Path] = []
        published_source_parents: list[Path] = []
        published_source_parent_modes: list[int] = []
        real_repository_check = packager._assert_repository_matches_commit
        real_link = packager.os.link

        def replace_direct_output_temporary_file(
            repository_root: Path,
            commit_sha: str,
        ) -> None:
            nonlocal repository_checks
            real_repository_check(repository_root, commit_sha)
            repository_checks += 1
            if repository_checks == 2:
                direct_temporary_files.extend(output.glob(".*.tmp"))
                for temporary_path in direct_temporary_files:
                    temporary_path.write_bytes(
                        b"substituted between digest and publication\n"
                    )

        def capture_published_source(source: object, destination: object) -> None:
            source_parent = Path(source).parent
            published_source_parents.append(source_parent)
            published_source_parent_modes.append(
                stat.S_IMODE(source_parent.stat().st_mode)
            )
            real_link(source, destination)

        with mock.patch.object(
            packager,
            "_assert_repository_matches_commit",
            side_effect=replace_direct_output_temporary_file,
        ), mock.patch.object(
            packager.os,
            "link",
            side_effect=capture_published_source,
        ):
            created = packager._create_delivery_package_result(
                fixture.demo,
                fixture.evidence,
                fixture.report,
                output,
            )

        self.assertEqual(repository_checks, 2)
        self.assertEqual(direct_temporary_files, [])
        self.assertEqual(len(published_source_parents), 1)
        self.assertNotEqual(published_source_parents[0], output)
        if os.name == "posix":
            self.assertEqual(published_source_parent_modes, [0o700])
        self.assertEqual(
            created.sha256,
            hashlib.sha256(created.path.read_bytes()).hexdigest(),
        )

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
            assert_packaged_acceptance_documents(self, archive, package_root)
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
                f"{package_root}/tests/ctest/expected-cpp-tests.txt", members
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

    def test_existing_archive_is_rejected_without_replacement(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_delivery_existing_archive")
        fixture = GitDemoFixture(self.root)
        output = self.root / "existing-archive-out"
        output.mkdir()
        commit_sha = run(["git", "rev-parse", "HEAD"], fixture.repository).stdout.strip()
        destination = output / (
            f"{packager.PACKAGE_BASENAME}-v{packager.DEMO_VERSION}"
            f"+{commit_sha[:12]}.zip"
        )
        competing_bytes = b"pre-existing delivery bytes\n"
        destination.write_bytes(competing_bytes)

        with self.assertRaisesRegex(RuntimeError, r"already exists|destination"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, output
            )

        self.assertEqual(destination.read_bytes(), competing_bytes)

    def test_existing_archive_symlink_is_rejected_without_following(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_delivery_archive_symlink")
        fixture = GitDemoFixture(self.root)
        output = self.root / "archive-symlink-out"
        output.mkdir()
        commit_sha = run(["git", "rev-parse", "HEAD"], fixture.repository).stdout.strip()
        destination = output / (
            f"{packager.PACKAGE_BASENAME}-v{packager.DEMO_VERSION}"
            f"+{commit_sha[:12]}.zip"
        )
        victim = self.root / "archive-symlink-victim"
        victim_bytes = b"must not be replaced\n"
        victim.write_bytes(victim_bytes)
        destination.symlink_to(victim)

        with self.assertRaisesRegex(RuntimeError, r"already exists|destination"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, output
            )

        self.assertTrue(destination.is_symlink())
        self.assertEqual(victim.read_bytes(), victim_bytes)

    def test_output_directory_symlink_is_rejected_without_following(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_delivery_output_symlink")
        fixture = GitDemoFixture(self.root)
        redirected = self.root / "redirected-output"
        redirected.mkdir()
        output = self.root / "output-link"
        output.symlink_to(redirected, target_is_directory=True)

        with self.assertRaisesRegex(RuntimeError, r"output directory.*symlink"):
            packager.create_delivery_package(
                fixture.demo, fixture.evidence, fixture.report, output
            )

        self.assertEqual(list(redirected.iterdir()), [])

    def test_symlinked_output_parent_is_the_documented_trust_boundary(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_delivery_parent_symlink")
        fixture = GitDemoFixture(self.root)
        redirected_parent = self.root / "redirected-parent"
        redirected_parent.mkdir()
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(redirected_parent, target_is_directory=True)
        output = parent_link / "out"

        archive = packager.create_delivery_package(
            fixture.demo, fixture.evidence, fixture.report, output
        )

        self.assertEqual(archive.parent, (redirected_parent / "out").resolve())
        self.assertTrue(archive.is_file())

    def test_destination_race_fails_without_clobbering_competing_bytes(self) -> None:
        packager = load_script(PACKAGER_SCRIPT, "csc3_delivery_destination_race")
        fixture = GitDemoFixture(self.root)
        output = self.root / "destination-race-out"
        competing_bytes = b"race winner bytes\n"
        real_link = packager.os.link
        injected_destination: Path | None = None

        def inject_competitor(source: object, destination: object) -> None:
            nonlocal injected_destination
            injected_destination = Path(destination)
            injected_destination.write_bytes(competing_bytes)
            real_link(source, destination)

        with mock.patch.object(packager.os, "link", side_effect=inject_competitor):
            with self.assertRaisesRegex(RuntimeError, r"appeared|already exists|destination"):
                packager.create_delivery_package(
                    fixture.demo, fixture.evidence, fixture.report, output
                )

        self.assertIsNotNone(injected_destination)
        assert injected_destination is not None
        self.assertEqual(injected_destination.read_bytes(), competing_bytes)
        self.assertEqual(list(output.glob(".*.staging-*")), [])

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
