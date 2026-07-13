#!/usr/bin/env python3
"""Contract tests for the portable CSC3 delivery-package verifier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
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
REQUIRED_DELIVERY_PATHS_UNDER_TEST = (
    "requirements-test.txt",
    "scripts/finalize_delivery.py",
    "scripts/validate_acceptance_record.py",
    "packaging/README.md",
    "packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md",
    "packaging/ACCEPTANCE_CHECKLIST.zh-CN.md",
    "packaging/ACCEPTANCE_RECORD.schema.json",
    "packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md",
)


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
        self.fixtures = load_script(
            PACKAGER_TEST_SCRIPT,
            "csc3_packager_test_fixtures",
        )
        self.fixture = self.fixtures.GitDemoFixture(self.root)
        self.archive = self.packager.create_delivery_package(
            self.fixture.demo,
            self.fixture.evidence,
            self.fixture.report,
            self.root / "out",
        )

    def create_formal_archive(self) -> Path:
        existing = getattr(self, "formal_archive", None)
        if existing is not None:
            return existing
        source_commit = self.fixtures.run(
            ["git", "rev-parse", "HEAD"], self.fixture.repository
        ).stdout.strip()
        evidence, report, _ = self.fixtures.create_external_formal_inputs(
            self.root / "external-formal-evidence",
            source_commit,
        )
        self.formal_archive = self.packager.create_external_formal_package(
            self.fixture.demo,
            evidence,
            report,
            "linux-intel-formal",
            self.root / "formal-out",
        )
        return self.formal_archive

    def test_manifest_only_verification_accepts_the_generated_archive(self) -> None:
        result = self.verifier.verify_delivery_package(
            self.archive, run_clean_room=False
        )
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["verified_file_count"], 10)
        self.assertFalse(result["clean_room_executed"])
        self.assertEqual(result["distribution"], "INTERNAL EVALUATION ONLY")
        self.assertEqual(result["evidence_source_commit"], "b" * 40)
        self.assertIs(result["evidence_source_matches_package_source"], False)

    def test_manifest_only_does_not_require_jsonschema_on_the_host(self) -> None:
        self.assertTrue(hasattr(self.verifier.importlib, "metadata"))
        original_version = self.verifier.importlib.metadata.version

        def missing_distribution(_name: str) -> str:
            raise self.verifier.importlib.metadata.PackageNotFoundError

        self.verifier.importlib.metadata.version = missing_distribution
        try:
            result = self.verifier.verify_delivery_package(
                self.archive,
                run_clean_room=False,
            )
        finally:
            self.verifier.importlib.metadata.version = original_version

        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["clean_room_executed"])

    def test_full_clean_room_fails_before_extraction_without_jsonschema(self) -> None:
        self.assertTrue(hasattr(self.verifier.importlib, "metadata"))
        original_version = self.verifier.importlib.metadata.version
        original_temporary_directory = self.verifier.tempfile.TemporaryDirectory
        original_extract_contents = self.verifier._extract_contents

        def missing_distribution(_name: str) -> str:
            raise self.verifier.importlib.metadata.PackageNotFoundError

        def fail_if_temporary_directory_starts(*_args, **_kwargs):
            raise AssertionError("missing jsonschema reached a temporary directory")

        def fail_if_extraction_starts(*_args, **_kwargs):
            raise AssertionError("missing jsonschema reached extraction")

        self.verifier.importlib.metadata.version = missing_distribution
        self.verifier.tempfile.TemporaryDirectory = fail_if_temporary_directory_starts
        self.verifier._extract_contents = fail_if_extraction_starts
        try:
            with self.assertRaisesRegex(
                RuntimeError,
                r"full clean-room.*jsonschema>=4\.23,<5.*requirements-test\.txt",
            ) as caught:
                self.verifier.verify_delivery_package(
                    self.archive,
                    run_clean_room=True,
                )
            self.assertIn(
                str(DEMO_ROOT / "requirements-test.txt"),
                str(caught.exception),
            )
        finally:
            self.verifier.importlib.metadata.version = original_version
            self.verifier.tempfile.TemporaryDirectory = original_temporary_directory
            self.verifier._extract_contents = original_extract_contents

    def test_full_clean_room_rejects_unsupported_jsonschema_version(self) -> None:
        self.assertTrue(hasattr(self.verifier.importlib, "metadata"))
        original_version = self.verifier.importlib.metadata.version
        self.verifier.importlib.metadata.version = lambda _name: "4.22.0"
        try:
            with self.assertRaisesRegex(
                RuntimeError,
                r"jsonschema 4\.22\.0.*jsonschema>=4\.23,<5",
            ):
                self.verifier.verify_delivery_package(
                    self.archive,
                    run_clean_room=True,
                )
        finally:
            self.verifier.importlib.metadata.version = original_version

    def test_manifest_verification_reports_formal_source_binding(self) -> None:
        result = self.verifier.verify_delivery_package(
            self.create_formal_archive(),
            run_clean_room=False,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_commit"], result["evidence_source_commit"])
        self.assertIs(result["evidence_source_matches_package_source"], True)

    def test_manifest_only_requires_delivery_paths_before_temp_or_extraction(
        self,
    ) -> None:
        original_temporary_directory = self.verifier.tempfile.TemporaryDirectory
        original_extract_contents = self.verifier._extract_contents

        def fail_if_temporary_directory_starts(*_args, **_kwargs):
            raise AssertionError("missing acceptance path reached a temporary directory")

        def fail_if_extraction_starts(*_args, **_kwargs):
            raise AssertionError("missing acceptance path reached extraction")

        self.verifier.tempfile.TemporaryDirectory = fail_if_temporary_directory_starts
        self.verifier._extract_contents = fail_if_extraction_starts
        try:
            for index, missing_path in enumerate(
                REQUIRED_DELIVERY_PATHS_UNDER_TEST
            ):
                with self.subTest(missing_path=missing_path):
                    def remove_required_path(
                        contents: dict[str, bytes],
                        path: str = missing_path,
                    ) -> None:
                        contents.pop(path)

                    invalid = self.rewrite_archive_contents(
                        f"missing-acceptance-path-{index}",
                        remove_required_path,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        rf"missing required paths.*{re.escape(missing_path)}",
                    ):
                        self.verifier.verify_delivery_package(
                            invalid,
                            run_clean_room=False,
                        )
        finally:
            self.verifier.tempfile.TemporaryDirectory = original_temporary_directory
            self.verifier._extract_contents = original_extract_contents

    def test_packaging_readme_ignores_external_and_anchor_inline_links(self) -> None:
        def add_nonrelative_links(contents: dict[str, bytes]) -> None:
            contents["packaging/README.md"] += (
                b"\n[external](https://example.invalid/delivery)\n"
                b"[section](#preconditions)\n"
                b"![image](MISSING.png)\n"
                b"\\\\![escaped-backslash-image](MISSING.png)\n"
            )

        archive = self.rewrite_archive_contents(
            "packaging-readme-nonrelative-links",
            add_nonrelative_links,
        )

        result = self.verifier.verify_delivery_package(
            archive,
            run_clean_room=False,
        )

        self.assertEqual(result["status"], "PASS")

    def test_escaped_image_marker_is_validated_as_an_inline_link(self) -> None:
        escaped_markers = (
            b"\\![missing](MISSING.md)",
            b"\\\\\\![missing](MISSING.md)",
        )
        for index, link in enumerate(escaped_markers):
            with self.subTest(link=link):
                def add_escaped_image_marker(contents: dict[str, bytes]) -> None:
                    contents["packaging/README.md"] += b"\n" + link + b"\n"

                archive = self.rewrite_archive_contents(
                    f"packaging-readme-escaped-image-marker-{index}",
                    add_escaped_image_marker,
                )
                with self.assertRaisesRegex(
                    RuntimeError,
                    r"broken relative Markdown link.*MISSING\.md",
                ):
                    self.verifier.verify_delivery_package(
                        archive,
                        run_clean_room=False,
                    )

    def test_manifest_only_rejects_broken_relative_packaging_readme_link(
        self,
    ) -> None:
        def add_broken_relative_link(contents: dict[str, bytes]) -> None:
            contents["packaging/README.md"] += b"\n[missing](MISSING.md)\n"

        archive = self.rewrite_archive_contents(
            "packaging-readme-broken-relative-link",
            add_broken_relative_link,
        )
        original_temporary_directory = self.verifier.tempfile.TemporaryDirectory
        original_extract_contents = self.verifier._extract_contents

        def fail_if_temporary_directory_starts(*_args, **_kwargs):
            raise AssertionError("broken packaging link reached a temporary directory")

        def fail_if_extraction_starts(*_args, **_kwargs):
            raise AssertionError("broken packaging link reached extraction")

        self.verifier.tempfile.TemporaryDirectory = fail_if_temporary_directory_starts
        self.verifier._extract_contents = fail_if_extraction_starts
        try:
            with self.assertRaisesRegex(
                RuntimeError,
                r"broken relative Markdown link.*MISSING\.md",
            ):
                self.verifier.verify_delivery_package(
                    archive,
                    run_clean_room=False,
                )
        finally:
            self.verifier.tempfile.TemporaryDirectory = original_temporary_directory
            self.verifier._extract_contents = original_extract_contents

    def test_manifest_only_rejects_unsupported_inline_link_target_syntax(
        self,
    ) -> None:
        unsupported_links = (
            b'[missing](MISSING.md "title")',
            b'[missing](MISSING.md\n "title")',
            b"[miss\ning](MISSING.md)",
            b"[](MISSING.md)",
            b"[missing](<MISSING.md>)",
            b"[missing](MISSING(section).md)",
        )
        for index, link in enumerate(unsupported_links):
            with self.subTest(link=link):
                def add_unsupported_link(contents: dict[str, bytes]) -> None:
                    contents["packaging/README.md"] += b"\n" + link + b"\n"

                archive = self.rewrite_archive_contents(
                    f"packaging-readme-unsupported-link-{index}",
                    add_unsupported_link,
                )
                with self.assertRaisesRegex(
                    RuntimeError,
                    r"unsupported inline Markdown link syntax",
                ):
                    self.verifier.verify_delivery_package(
                        archive,
                        run_clean_room=False,
                    )

    def test_verifier_accepts_formal_bundle_id_build(self) -> None:
        source_commit = self.fixtures.run(
            ["git", "rev-parse", "HEAD"], self.fixture.repository
        ).stdout.strip()
        evidence, report, _ = self.fixtures.create_external_formal_inputs(
            self.root / "external-formal-build-evidence",
            source_commit,
        )
        archive = self.packager.create_external_formal_package(
            self.fixture.demo,
            evidence,
            report,
            "build",
            self.root / "formal-build-out",
        )

        result = self.verifier.verify_delivery_package(
            archive,
            run_clean_room=False,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_commit"], result["evidence_source_commit"])
        self.assertIs(result["evidence_source_matches_package_source"], True)

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
        source_archive: Path | None = None,
    ) -> Path:
        source_archive = source_archive or self.archive
        directory = self.root / directory_name
        directory.mkdir()
        target_path = directory / source_archive.name
        with zipfile.ZipFile(source_archive) as source, zipfile.ZipFile(
            target_path, "w", compression=zipfile.ZIP_STORED
        ) as target:
            infos = source.infolist()
            if reverse:
                infos.reverse()
            for index, info in enumerate(infos):
                content = source.read(info.filename)
                transform(info, content, index, target)
        return target_path

    def test_zip_preflight_finishes_before_formal_semantic_extraction(self) -> None:
        formal_archive = self.create_formal_archive()

        def change_platform(info, content, index, target) -> None:
            if index == 0:
                info.create_system = 0
            target.writestr(info, content)

        invalid = self.rewrite_archive(
            "formal-preflight-platform",
            change_platform,
            source_archive=formal_archive,
        )
        original_temporary_directory = self.verifier.tempfile.TemporaryDirectory

        def fail_if_semantic_extraction_starts(*_args, **_kwargs):
            raise AssertionError("formal semantic extraction started before ZIP preflight")

        self.verifier.tempfile.TemporaryDirectory = fail_if_semantic_extraction_starts
        try:
            with self.assertRaisesRegex(RuntimeError, "platform"):
                self.verifier.verify_delivery_package(invalid, run_clean_room=False)
        finally:
            self.verifier.tempfile.TemporaryDirectory = original_temporary_directory

    def rewrite_archive_contents(
        self,
        directory_name: str,
        mutate,
        *,
        source_archive: Path | None = None,
    ) -> Path:
        """Rewrite payload bytes and rebuild the outer package manifest."""
        source_archive = source_archive or self.archive
        directory = self.root / directory_name
        directory.mkdir()
        target_path = directory / source_archive.name
        with zipfile.ZipFile(source_archive) as source:
            infos = {info.filename: info for info in source.infolist()}
            contents = {name: source.read(name) for name in infos}
        root = source_archive.stem + "/"
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

    def add_listed_member(
        self,
        directory_name: str,
        relative: str,
        content: bytes = b"listed test member\n",
        *,
        source_archive: Path | None = None,
    ) -> Path:
        """Add one manifest-bound regular member with deterministic ZIP metadata."""
        source_archive = source_archive or self.archive
        directory = self.root / directory_name
        directory.mkdir()
        target_path = directory / source_archive.name
        with zipfile.ZipFile(source_archive) as source:
            root = source_archive.stem + "/"
            infos = {info.filename: info for info in source.infolist()}
            relative_contents = {
                name[len(root) :]: source.read(name)
                for name in infos
                if name != root + "MANIFEST.sha256"
            }
        relative_contents[relative] = content
        relative_contents["MANIFEST.sha256"] = "".join(
            f"{hashlib.sha256(payload).hexdigest()}  {name}\n"
            for name, payload in sorted(relative_contents.items())
            if name != "MANIFEST.sha256"
        ).encode("utf-8")

        with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_STORED) as target:
            for name, payload in sorted(relative_contents.items()):
                member_name = root + name
                info = infos.get(member_name)
                if info is None:
                    info = zipfile.ZipInfo(
                        member_name,
                        date_time=self.verifier.FIXED_ZIP_TIMESTAMP,
                    )
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                target.writestr(info, payload)
        return target_path

    def test_verifier_rejects_forged_formal_source_binding(self) -> None:
        formal_archive = self.create_formal_archive()

        def forge_binding(contents: dict[str, bytes]) -> None:
            build_info = json.loads(contents["BUILD_INFO.json"])
            manifest_path = build_info["evidence_manifest"]
            manifest = json.loads(contents[manifest_path])
            forged_commit = "b" * 40
            manifest["source"]["commit_sha"] = forged_commit
            for identity_check in manifest["identity_checks"]:
                identity_check["source"]["commit_sha"] = forged_commit
            manifest_bytes = (
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            contents[manifest_path] = manifest_bytes
            build_info["evidence_manifest_sha256"] = hashlib.sha256(
                manifest_bytes
            ).hexdigest()
            build_info["evidence_source_commit"] = forged_commit
            build_info["evidence_source_matches_package_source"] = False
            contents["BUILD_INFO.json"] = (
                json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")

        forged = self.rewrite_archive_contents(
            "forged-formal-binding",
            forge_binding,
            source_archive=formal_archive,
        )

        with self.assertRaisesRegex(RuntimeError, "formal.*source|source.*binding"):
            self.verifier.verify_delivery_package(forged, run_clean_room=False)

    def test_verifier_rejects_formal_evidence_downgraded_to_local_smoke(self) -> None:
        formal_archive = self.create_formal_archive()

        def downgrade_report_intent(contents: dict[str, bytes]) -> None:
            build_info = json.loads(contents["BUILD_INFO.json"])
            manifest_path = build_info["evidence_manifest"]
            manifest = json.loads(contents[manifest_path])
            manifest["report_intent"] = "local-smoke"
            manifest_bytes = (
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            contents[manifest_path] = manifest_bytes
            build_info["evidence_manifest_sha256"] = hashlib.sha256(
                manifest_bytes
            ).hexdigest()
            contents["BUILD_INFO.json"] = (
                json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")

        forged = self.rewrite_archive_contents(
            "formal-intent-downgrade",
            downgrade_report_intent,
            source_archive=formal_archive,
        )

        with self.assertRaisesRegex(RuntimeError, "formal.*delivery|report_intent"):
            self.verifier.verify_delivery_package(forged, run_clean_room=False)

    def test_verifier_rejects_noncanonical_formal_report_content(self) -> None:
        formal_archive = self.create_formal_archive()

        def drift_report(contents: dict[str, bytes]) -> None:
            build_info = json.loads(contents["BUILD_INFO.json"])
            report_path = build_info["report"]
            contents[report_path] += b"noncanonical\n"
            build_info["report_sha256"] = hashlib.sha256(
                contents[report_path]
            ).hexdigest()
            contents["BUILD_INFO.json"] = (
                json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")

        drifted = self.rewrite_archive_contents(
            "noncanonical-formal-report",
            drift_report,
            source_archive=formal_archive,
        )

        with self.assertRaisesRegex(RuntimeError, "canonical.*report|report.*canonical"):
            self.verifier.verify_delivery_package(drifted, run_clean_room=False)

    def test_verifier_recomputes_formal_pass_from_reconstructed_evidence(self) -> None:
        formal_archive = self.create_formal_archive()

        def forge_status(contents: dict[str, bytes]) -> None:
            build_info = json.loads(contents["BUILD_INFO.json"])
            manifest_path = build_info["evidence_manifest"]
            manifest = json.loads(contents[manifest_path])
            manifest["status"] = "FAIL"
            manifest_bytes = (
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            contents[manifest_path] = manifest_bytes
            build_info["evidence_manifest_sha256"] = hashlib.sha256(
                manifest_bytes
            ).hexdigest()
            contents["BUILD_INFO.json"] = (
                json.dumps(build_info, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")

        forged = self.rewrite_archive_contents(
            "forged-formal-status",
            forge_status,
            source_archive=formal_archive,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "formal.*semantic|recomputed.*status|formal.*PASS",
        ):
            self.verifier.verify_delivery_package(forged, run_clean_room=False)

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

    def test_verifier_rejects_manifest_bound_prefix_collision_before_extraction(
        self,
    ) -> None:
        formal_archive = self.create_formal_archive()
        collision = self.add_listed_member(
            "formal-prefix-collision",
            "results/linux-intel-formal",
            source_archive=formal_archive,
        )
        original_temporary_directory = self.verifier.tempfile.TemporaryDirectory
        temporary_directory_calls = 0

        def recording_temporary_directory(*args, **kwargs):
            nonlocal temporary_directory_calls
            temporary_directory_calls += 1
            return original_temporary_directory(*args, **kwargs)

        self.verifier.tempfile.TemporaryDirectory = recording_temporary_directory
        try:
            for run_clean_room in (False, True):
                with self.subTest(run_clean_room=run_clean_room):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "archive path prefix collision.*results/linux-intel-formal",
                    ):
                        self.verifier.verify_delivery_package(
                            collision,
                            run_clean_room=run_clean_room,
                        )
            self.assertEqual(temporary_directory_calls, 0)
        finally:
            self.verifier.tempfile.TemporaryDirectory = original_temporary_directory

    def test_manifest_paths_share_the_archive_prefix_collision_model(self) -> None:
        parent = self.add_listed_member(
            "manifest-prefix-parent",
            "docs/prefix-parent",
        )

        def add_manifest_only_descendant(info, content, _index, target) -> None:
            if info.filename.endswith("/MANIFEST.sha256"):
                entries = [
                    tuple(line.decode("utf-8").split("  ", 1))
                    for line in content.splitlines()
                ]
                entries.append(("0" * 64, "docs/prefix-parent/ghost.txt"))
                content = "".join(
                    f"{digest}  {relative}\n"
                    for digest, relative in sorted(
                        entries,
                        key=lambda entry: entry[1],
                    )
                ).encode("utf-8")
            target.writestr(info, content)

        collision = self.rewrite_archive(
            "manifest-prefix-descendant",
            add_manifest_only_descendant,
            source_archive=parent,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "archive path prefix collision.*docs/prefix-parent",
        ):
            self.verifier.verify_delivery_package(collision, run_clean_room=False)

    def test_verifier_rejects_windows_drive_like_members_before_extraction(self) -> None:
        original_extract_contents = self.verifier._extract_contents

        def fail_if_extraction_starts(*_args, **_kwargs):
            raise AssertionError("unsafe Windows drive-like member reached extraction")

        self.verifier._extract_contents = fail_if_extraction_starts
        try:
            for index, relative in enumerate(("D:/escape.txt", "D:foo")):
                with self.subTest(relative=relative):
                    malicious = self.add_listed_member(
                        f"windows-drive-like-{index}",
                        relative,
                    )
                    with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
                        self.verifier.verify_delivery_package(
                            malicious,
                            run_clean_room=True,
                        )
        finally:
            self.verifier._extract_contents = original_extract_contents

    def test_formal_bundle_root_exception_still_rejects_build_elsewhere(self) -> None:
        forbidden = self.add_listed_member(
            "forbidden-build-elsewhere",
            "docs/build/unexpected.txt",
        )

        with self.assertRaisesRegex(RuntimeError, "forbidden delivery path"):
            self.verifier.verify_delivery_package(forbidden, run_clean_room=False)

    def test_formal_bundle_root_exception_rejects_member_equal_to_root(self) -> None:
        source_commit = self.fixtures.run(
            ["git", "rev-parse", "HEAD"], self.fixture.repository
        ).stdout.strip()
        evidence, report, _ = self.fixtures.create_external_formal_inputs(
            self.root / "external-formal-build-root-evidence",
            source_commit,
        )
        formal_archive = self.packager.create_external_formal_package(
            self.fixture.demo,
            evidence,
            report,
            "build",
            self.root / "formal-build-root-out",
        )
        forbidden = self.add_listed_member(
            "forbidden-member-equal-to-build-root",
            "results/build",
            source_archive=formal_archive,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "archive path prefix collision.*results/build",
        ):
            self.verifier.verify_delivery_package(forbidden, run_clean_room=False)

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
