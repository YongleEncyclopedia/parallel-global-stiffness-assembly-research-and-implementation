from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = DEMO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INVENTORY = load_script("check_ctest_inventory")
JUNIT = load_script("check_ctest_junit")


class InventoryHelperTests(unittest.TestCase):
    def test_labeled_inventory_is_exact(self) -> None:
        document = {
            "tests": [
                {
                    "name": "CiOne",
                    "properties": [{"name": "LABELS", "value": ["ci"]}],
                },
                {
                    "name": "Contention",
                    "properties": [
                        {"name": "LABELS", "value": ["ci", "atomic-contention"]}
                    ],
                },
                {
                    "name": "Manual",
                    "properties": [{"name": "LABELS", "value": ["manual"]}],
                },
            ]
        }

        self.assertEqual(
            INVENTORY.select_labeled_test_names(document, "ci"),
            {"CiOne", "Contention"},
        )
        self.assertEqual(
            INVENTORY.compare_test_names(
                {"CiOne", "Contention"}, {"CiOne", "Expected"}
            ),
            (["Expected"], ["Contention"]),
        )

    def test_expected_inventory_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "expected.txt"
            expected.write_text("One\nOne\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                INVENTORY.read_expected_names(expected)


class JunitHelperTests(unittest.TestCase):
    def write_junit(self, contents: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "ctest.xml"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_clean_junit_has_only_passing_cases(self) -> None:
        path = self.write_junit(
            '<testsuite tests="2"><testcase name="One" status="run"/>'
            '<testcase name="Two" status="run"/></testsuite>'
        )
        self.assertEqual(
            JUNIT.read_junit_summary(path),
            JUNIT.JUnitSummary(2, 0, 0, 0, 0),
        )

    def test_skip_and_not_run_are_counted(self) -> None:
        path = self.write_junit(
            '<testsuite tests="3"><testcase name="Skip"><skipped/></testcase>'
            '<testcase name="NotRun" status="not_run"/>'
            '<testcase name="Disabled" status="disabled"/></testsuite>'
        )
        self.assertEqual(
            JUNIT.read_junit_summary(path),
            JUNIT.JUnitSummary(3, 0, 0, 1, 2),
        )


if __name__ == "__main__":
    unittest.main()
