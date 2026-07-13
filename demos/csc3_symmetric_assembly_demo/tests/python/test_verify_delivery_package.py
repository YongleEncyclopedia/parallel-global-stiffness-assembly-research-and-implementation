#!/usr/bin/env python3
"""Contract tests for the portable CSC3 delivery-package verifier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_SCRIPT = DEMO_ROOT / "scripts" / "verify_delivery_package.py"
PACKAGER_SCRIPT = DEMO_ROOT / "scripts" / "create_delivery_package.py"
PACKAGER_TEST_SCRIPT = Path(__file__).with_name("test_delivery_package.py")


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemporaryDirectory(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-verifier-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()


class VerifierModuleTests(unittest.TestCase):
    def test_verifier_module_exists(self) -> None:
        self.assertTrue(VERIFIER_SCRIPT.is_file())


class PortableVerifierTests(TemporaryDirectory):
    def setUp(self) -> None:
        super().setUp()
        self.packager = load_script(PACKAGER_SCRIPT, "csc3_packager_for_verifier")
        self.verifier = load_script(VERIFIER_SCRIPT, "csc3_verify_delivery_package")
        fixtures = load_script(PACKAGER_TEST_SCRIPT, "csc3_packager_test_fixtures")
        self.fixture = fixtures.GitDemoFixture(self.root)
        self.archive = self.packager.create_delivery_package(
            self.fixture.demo,
            self.fixture.evidence,
            self.fixture.report,
            self.root / "out",
        )

    def test_manifest_only_verification_accepts_the_generated_archive(self) -> None:
        result = self.verifier.verify_delivery_package(
            self.archive, run_clean_room=False
        )
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["verified_file_count"], 10)
        self.assertFalse(result["clean_room_executed"])
        self.assertEqual(result["distribution"], "INTERNAL EVALUATION ONLY")

    def test_manifest_verification_rejects_changed_content(self) -> None:
        corrupt_dir = self.root / "corrupt"
        corrupt_dir.mkdir()
        corrupt = corrupt_dir / self.archive.name
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(
            corrupt, "w", compression=zipfile.ZIP_STORED
        ) as target:
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename.endswith("/README.md"):
                    content += b"corrupt\n"
                target.writestr(info, content)

        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            self.verifier.verify_delivery_package(corrupt, run_clean_room=False)

    def test_manifest_verification_rejects_unlisted_content(self) -> None:
        extra_dir = self.root / "extra"
        extra_dir.mkdir()
        archive_path = extra_dir / self.archive.name
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_STORED
        ) as target:
            for info in source.infolist():
                target.writestr(info, source.read(info.filename))
            root = self.archive.stem
            target.writestr(f"{root}/unlisted.txt", "unexpected\n")

        with self.assertRaisesRegex(RuntimeError, "unlisted"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def rewrite_archive(
        self,
        directory_name: str,
        transform,
        *,
        reverse: bool = False,
    ) -> Path:
        directory = self.root / directory_name
        directory.mkdir()
        target_path = directory / self.archive.name
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(
            target_path, "w", compression=zipfile.ZIP_STORED
        ) as target:
            infos = source.infolist()
            if reverse:
                infos.reverse()
            for index, info in enumerate(infos):
                content = source.read(info.filename)
                transform(info, content, index, target)
        return target_path

    def rewrite_archive_contents(
        self,
        directory_name: str,
        mutate,
    ) -> Path:
        """Rewrite payload bytes and rebuild the outer package manifest."""
        directory = self.root / directory_name
        directory.mkdir()
        target_path = directory / self.archive.name
        with zipfile.ZipFile(self.archive) as source:
            infos = {info.filename: info for info in source.infolist()}
            contents = {name: source.read(name) for name in infos}
        root = self.archive.stem + "/"
        relative_contents = {
            name[len(root) :]: content for name, content in contents.items()
        }
        mutate(relative_contents)
        relative_contents["MANIFEST.sha256"] = "".join(
            f"{hashlib.sha256(content).hexdigest()}  {relative}\n"
            for relative, content in sorted(relative_contents.items())
            if relative != "MANIFEST.sha256"
        ).encode("utf-8")
        with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_STORED) as target:
            for relative, content in sorted(relative_contents.items()):
                target.writestr(infos[root + relative], content)
        return target_path

    def test_verifier_rejects_nonlexicographic_member_order(self) -> None:
        def copy(info, content, _index, target) -> None:
            target.writestr(info, content)

        archive_path = self.rewrite_archive("reordered", copy, reverse=True)
        with self.assertRaisesRegex(RuntimeError, "lexicographic"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_nonunix_zip_metadata(self) -> None:
        def change_platform(info, content, index, target) -> None:
            if index == 0:
                info.create_system = 0
            target.writestr(info, content)

        archive_path = self.rewrite_archive("platform", change_platform)
        with self.assertRaisesRegex(RuntimeError, "platform"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_nonregular_member_mode(self) -> None:
        def change_mode(info, content, index, target) -> None:
            if index == 0:
                info.external_attr = (stat.S_IFDIR | 0o644) << 16
            target.writestr(info, content)

        archive_path = self.rewrite_archive("mode", change_mode)
        with self.assertRaisesRegex(RuntimeError, "regular file"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_carriage_return_in_manifest(self) -> None:
        def change_manifest(info, content, _index, target) -> None:
            if info.filename.endswith("/MANIFEST.sha256"):
                content = content.replace(b"\n", b"\r\n")
            target.writestr(info, content)

        archive_path = self.rewrite_archive("manifest-cr", change_manifest)
        with self.assertRaisesRegex(RuntimeError, "carriage return"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_nonlexicographic_manifest_order(self) -> None:
        def reverse_manifest(info, content, _index, target) -> None:
            if info.filename.endswith("/MANIFEST.sha256"):
                lines = content.splitlines(keepends=True)
                content = b"".join(reversed(lines))
            target.writestr(info, content)

        archive_path = self.rewrite_archive("manifest-order", reverse_manifest)
        with self.assertRaisesRegex(RuntimeError, "manifest.*lexicographic"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_requires_all_raw_evidence_files(self) -> None:
        directory = self.root / "missing-evidence"
        directory.mkdir()
        archive_path = directory / self.archive.name
        missing_suffix = "/benchmark_samples.csv"
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_STORED
        ) as target:
            for info in source.infolist():
                if info.filename.endswith(missing_suffix):
                    continue
                content = source.read(info.filename)
                if info.filename.endswith("/MANIFEST.sha256"):
                    content = b"".join(
                        line
                        for line in content.splitlines(keepends=True)
                        if not line.rstrip().endswith(b"benchmark_samples.csv")
                    )
                target.writestr(info, content)

        with self.assertRaisesRegex(RuntimeError, "evidence.*benchmark_samples.csv"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_stale_run_manifest_artifact_hash(self) -> None:
        def change_sample(contents: dict[str, bytes]) -> None:
            path = "results/checked-evidence/benchmark_samples.csv"
            contents[path] = contents[path].replace(b"0,1", b"1,2")

        archive_path = self.rewrite_archive_contents(
            "stale-evidence-binding", change_sample
        )
        with self.assertRaisesRegex(RuntimeError, "benchmark_samples.csv.*SHA-256"):
            self.verifier.verify_delivery_package(archive_path, run_clean_room=False)

    def test_verifier_rejects_path_traversal_before_extraction(self) -> None:
        malicious = self.root / "malicious.zip"
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("../escape.txt", "escape")

        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.verifier.verify_delivery_package(malicious, run_clean_room=False)
        self.assertFalse(self.root.parent.joinpath("escape.txt").exists())

    def test_verifier_rejects_noncanonical_member_path(self) -> None:
        malicious = self.root / "noncanonical.zip"
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("root/./escape.txt", "escape")

        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.verifier.verify_delivery_package(malicious, run_clean_room=False)

    def test_clean_room_runs_delivery_tests_and_external_consumer(self) -> None:
        calls: list[tuple[list[str], Path]] = []

        def recording_runner(command: list[str], cwd: Path) -> None:
            calls.append((command, cwd))

        result = self.verifier.verify_delivery_package(
            self.archive,
            run_clean_room=True,
            command_runner=recording_runner,
        )

        commands = [command for command, _ in calls]
        self.assertTrue(
            any(command[1:3] == ["--preset", "delivery"] for command in commands)
        )
        self.assertTrue(
            any(
                command[1:4] == ["--build", "--preset", "delivery"]
                for command in commands
            )
        )
        self.assertTrue(
            any(
                command[0] == "ctest"
                and "--preset" in command
                and "--no-tests=error" in command
                for command in commands
            )
        )
        self.assertTrue(
            any(
                "tests/external_consumer" in " ".join(command).replace("\\", "/")
                for command in commands
            )
        )
        self.assertTrue(
            any(
                command[0] == "ctest"
                and "external-consumer-build" in " ".join(command)
                for command in commands
            )
        )
        inventory_index = next(
            index
            for index, command in enumerate(commands)
            if any(part.endswith("check_ctest_inventory.py") for part in command)
        )
        demo_ctest_index = next(
            index
            for index, command in enumerate(commands)
            if command[0] == "ctest" and "--preset" in command
        )
        demo_junit_index = next(
            index
            for index, command in enumerate(commands)
            if any(part.endswith("check_ctest_junit.py") for part in command)
            and command[-1] == "10"
        )
        consumer_ctest_index = next(
            index
            for index, command in enumerate(commands)
            if command[0] == "ctest" and "external-consumer-build" in " ".join(command)
        )
        consumer_junit_index = next(
            index
            for index, command in enumerate(commands)
            if any(part.endswith("check_ctest_junit.py") for part in command)
            and command[-1] == "1"
        )
        self.assertEqual(commands[inventory_index][0], sys.executable)
        self.assertEqual(
            commands[inventory_index][
                commands[inventory_index].index("--ctest") + 1
            ],
            "ctest",
        )
        self.assertIn("--output-junit", commands[demo_ctest_index])
        self.assertIn("--output-junit", commands[consumer_ctest_index])
        self.assertLess(inventory_index, demo_ctest_index)
        self.assertLess(demo_ctest_index, demo_junit_index)
        self.assertLess(demo_junit_index, consumer_ctest_index)
        self.assertLess(consumer_ctest_index, consumer_junit_index)
        self.assertTrue(result["clean_room_executed"])

    def test_clean_room_rejects_nine_disabled_ci_tests(self) -> None:
        expected = self.fixture.demo.joinpath(
            "tests/ctest/expected-ci-tests.txt"
        ).read_text(encoding="utf-8").splitlines()
        cmake_path = self.fixture.demo / "CMakeLists.txt"
        cmake_path.write_text(
            cmake_path.read_text(encoding="utf-8")
            + "\nset_tests_properties(\n"
            + "\n".join(f"    {name}" for name in expected[:-1])
            + "\n    PROPERTIES DISABLED TRUE\n)\n",
            encoding="utf-8",
        )
        self.fixture.commit_changes("disable nine tests")
        archive = self.packager.create_delivery_package(
            self.fixture.demo,
            self.fixture.evidence,
            self.fixture.report,
            self.root / "disabled-out",
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.verifier.verify_delivery_package(archive, run_clean_room=True)


if __name__ == "__main__":
    unittest.main()
