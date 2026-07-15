from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from delivery_test_context import repository_workflow_text


class RepositoryWorkflowBoundaryTests(unittest.TestCase):
    def test_repository_checkout_reads_the_real_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            repository_root = Path(temporary_name)
            demo_root = repository_root / "demos" / "csc3_symmetric_assembly_demo"
            workflow = repository_root / ".github" / "workflows" / "ci.yml"
            demo_root.mkdir(parents=True)
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: CI\n", encoding="utf-8")

            self.assertEqual(repository_workflow_text(demo_root), "name: CI\n")

    def test_unrelated_parent_workflow_is_not_treated_as_repository_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            parent = Path(temporary_name)
            demo_root = parent / "arbitrary" / "demo"
            workflow = parent / ".github" / "workflows" / "ci.yml"
            demo_root.mkdir(parents=True)
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: unrelated\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "repository demo layout"):
                repository_workflow_text(demo_root)

    def test_standalone_package_has_an_explicit_build_info_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            demo_root = Path(temporary_name) / "csc3-demo-v0.2.0+abc123"
            demo_root.mkdir()
            (demo_root / "BUILD_INFO.json").write_text(
                json.dumps(
                    {
                        "schema_version": "csc3-demo-build-info-v1",
                        "archive_root": demo_root.name,
                    }
                ),
                encoding="utf-8",
            )

            self.assertIsNone(repository_workflow_text(demo_root))

    def test_missing_repository_and_package_context_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            demo_root = Path(temporary_name) / "unbound-demo"
            demo_root.mkdir()

            with self.assertRaisesRegex(AssertionError, "neither a repository checkout"):
                repository_workflow_text(demo_root)

    def test_forged_package_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            demo_root = Path(temporary_name) / "actual-root"
            demo_root.mkdir()
            (demo_root / "BUILD_INFO.json").write_text(
                json.dumps(
                    {
                        "schema_version": "csc3-demo-build-info-v1",
                        "archive_root": "different-root",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "archive_root"):
                repository_workflow_text(demo_root)


if __name__ == "__main__":
    unittest.main()
