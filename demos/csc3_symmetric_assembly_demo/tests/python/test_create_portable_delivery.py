#!/usr/bin/env python3
"""WindHub 自包含源码交付包的创建与完整性测试。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "create_portable_delivery.py"


def load_packager():
    specification = importlib.util.spec_from_file_location(
        "csc3_portable_delivery_test",
        SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("无法加载自包含交付打包器")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


packager = load_packager()


class PortableDeliveryTests(unittest.TestCase):
    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
        ).stdout.strip()

    def _repository(self, root: Path) -> tuple[Path, str, bytes]:
        repository = root / "repository"
        demo = repository / "demos" / "csc3_symmetric_assembly_demo"
        required = {
            "README.md": b"portable readme\n",
            "CMakeLists.txt": b"cmake_minimum_required(VERSION 3.21)\n",
            "include/csc3_demo/assembly_helper.h": b"// public\n",
            "src/assembly_helper.cpp": b"// source\n",
            "tools/src/benchmark_main.cpp": b"// benchmark\n",
            "examples/run_windhub.py": b"# runner\n",
            "examples/run_windhub_demo.ps1": b"# windows\n",
            "examples/run_windhub_demo.sh": b"#!/usr/bin/env bash\n",
            "build/leak.txt": b"must not ship\n",
            "results/leak.txt": b"must not ship\n",
        }
        for relative, data in required.items():
            path = demo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        input_bytes = b"materialized WindHub fixture\n"
        import hashlib

        digest = hashlib.sha256(input_bytes).hexdigest()
        pointer = (
            "version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{digest}\n"
            f"size {len(input_bytes)}\n"
        ).encode("ascii")
        input_path = repository / "examples" / "3d-WindTurbineHub.inp"
        input_path.parent.mkdir(parents=True)
        input_path.write_bytes(pointer)

        repository.mkdir(exist_ok=True)
        self._git(repository, "init", "-q")
        self._git(repository, "config", "core.autocrlf", "false")
        self._git(repository, "config", "user.email", "codex@example.invalid")
        self._git(repository, "config", "user.name", "Codex Test")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-q", "-m", "fixture")
        commit = self._git(repository, "rev-parse", "HEAD")
        input_path.write_bytes(input_bytes)
        return repository, commit, input_bytes

    def test_package_contains_committed_source_materialized_input_and_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, commit, input_bytes = self._repository(root)
            package = packager.create_portable_package(
                repository,
                root / "output",
                commit,
            )
            manifest = packager.verify_portable_archive(package)
            with zipfile.ZipFile(package) as archive:
                names = set(archive.namelist())
                packaged_input = archive.read(
                    "csc3-windhub-demo/examples/3d-WindTurbineHub.inp"
                )
            sidecar_exists = package.with_suffix(".zip.sha256").is_file()

        self.assertEqual(manifest["source"]["commit_sha"], commit)
        self.assertEqual(packaged_input, input_bytes)
        self.assertIn("csc3-windhub-demo/PACKAGE_MANIFEST.json", names)
        self.assertIn("csc3-windhub-demo/SHA256SUMS.txt", names)
        self.assertNotIn("csc3-windhub-demo/build/leak.txt", names)
        self.assertNotIn("csc3-windhub-demo/results/leak.txt", names)
        self.assertTrue(sidecar_exists)

    def test_extracted_package_detects_modified_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, commit, _ = self._repository(root)
            package = packager.create_portable_package(
                repository,
                root / "output",
                commit,
            )
            extraction = root / "extraction"
            with zipfile.ZipFile(package) as archive:
                archive.extractall(extraction)
            package_root = extraction / "csc3-windhub-demo"
            verified = packager.verify_extracted_package(package_root)
            self.assertEqual(verified["schema_version"], packager.PACKAGE_SCHEMA_VERSION)
            (package_root / "examples" / "3d-WindTurbineHub.inp").write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "SHA-256 不匹配"):
                packager.verify_extracted_package(package_root)

    def test_same_commit_produces_identical_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, commit, _ = self._repository(root)
            first = packager.create_portable_package(
                repository,
                root / "first",
                commit,
            )
            second = packager.create_portable_package(
                repository,
                root / "second",
                commit,
            )
            first_bytes = first.read_bytes()
            second_bytes = second.read_bytes()

        self.assertEqual(first_bytes, second_bytes)

    def test_archive_with_unlisted_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, commit, _ = self._repository(root)
            package = packager.create_portable_package(
                repository,
                root / "output",
                commit,
            )
            tampered = root / "tampered.zip"
            tampered.write_bytes(package.read_bytes())
            with zipfile.ZipFile(tampered, "a") as archive:
                archive.writestr("csc3-windhub-demo/unlisted.txt", b"unexpected")
            with self.assertRaisesRegex(RuntimeError, "成员集合"):
                packager.verify_portable_archive(tampered)


if __name__ == "__main__":
    unittest.main()
