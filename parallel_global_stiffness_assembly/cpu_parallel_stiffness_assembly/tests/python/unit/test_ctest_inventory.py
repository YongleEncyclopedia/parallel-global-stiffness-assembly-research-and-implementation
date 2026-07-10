from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


CPU_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = CPU_ROOT / "scripts" / "check_ctest_inventory.py"


def load_checker() -> ModuleType:
    if not CHECKER_PATH.is_file():
        raise AssertionError(f"missing inventory checker: {CHECKER_PATH}")
    spec = importlib.util.spec_from_file_location("check_ctest_inventory", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load inventory checker: {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CTestInventoryTests(unittest.TestCase):
    def test_exact_inventory_has_no_differences(self) -> None:
        checker = load_checker()

        missing, unexpected = checker.compare_test_names(
            {"VerifyA", "VerifyB"}, {"VerifyB", "VerifyA"}
        )

        self.assertEqual(missing, [])
        self.assertEqual(unexpected, [])

    def test_missing_test_is_reported(self) -> None:
        checker = load_checker()

        missing, unexpected = checker.compare_test_names(
            {"VerifyA"}, {"VerifyA", "VerifyB"}
        )

        self.assertEqual(missing, ["VerifyB"])
        self.assertEqual(unexpected, [])

    def test_unexpected_test_is_reported(self) -> None:
        checker = load_checker()

        missing, unexpected = checker.compare_test_names(
            {"VerifyA", "VerifyExtra"}, {"VerifyA"}
        )

        self.assertEqual(missing, [])
        self.assertEqual(unexpected, ["VerifyExtra"])

    def test_label_selection_reads_ctest_json_properties(self) -> None:
        checker = load_checker()
        document = {
            "tests": [
                {
                    "name": "VerifyCiOnly",
                    "properties": [{"name": "LABELS", "value": ["ci"]}],
                },
                {
                    "name": "VerifyBoth",
                    "properties": [
                        {"name": "LABELS", "value": ["ci", "openmp"]}
                    ],
                },
                {
                    "name": "VerifyRepository",
                    "properties": [
                        {"name": "LABELS", "value": ["repository"]}
                    ],
                },
                {"name": "VerifyUnlabeled", "properties": []},
            ]
        }

        selected = checker.select_labeled_test_names(document, "ci")

        self.assertEqual(selected, {"VerifyCiOnly", "VerifyBoth"})


if __name__ == "__main__":
    unittest.main()
