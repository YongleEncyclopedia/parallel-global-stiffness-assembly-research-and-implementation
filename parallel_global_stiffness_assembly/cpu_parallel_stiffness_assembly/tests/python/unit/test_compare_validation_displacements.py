from __future__ import annotations

import csv
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


CPU_ROOT = Path(__file__).resolve().parents[3]
COMPARATOR_PATH = CPU_ROOT / "scripts" / "compare_validation_displacements.py"


def load_comparator() -> ModuleType:
    if not COMPARATOR_PATH.is_file():
        raise AssertionError(f"missing comparator: {COMPARATOR_PATH}")
    spec = importlib.util.spec_from_file_location(
        "compare_validation_displacements", COMPARATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load comparator: {COMPARATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class CompareValidationDisplacementsTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[Path, Path, Path]:
        matlab = root / "matlab.csv"
        reference = root / "reference.csv"
        probes = root / "probes.csv"
        write_csv(
            matlab,
            ["node", "ux", "uy", "uz", "umag"],
            [
                {"node": 0, "ux": 0, "uy": 0, "uz": 0, "umag": 0},
                {"node": 1, "ux": 1, "uy": 0, "uz": 0, "umag": 1},
                {"node": 2, "ux": 3, "uy": 4, "uz": 0, "umag": 5},
            ],
        )
        write_csv(
            reference,
            ["cpp_node", "node_label", "ux", "uy", "uz"],
            [
                {"cpp_node": 0, "node_label": 1, "ux": 0, "uy": 0, "uz": 0},
                {"cpp_node": 1, "node_label": 2, "ux": 1, "uy": 0, "uz": 0},
                {"cpp_node": 2, "node_label": 3, "ux": 0, "uy": 0, "uz": 4},
            ],
        )
        write_csv(
            probes,
            ["name", "node", "x", "y", "z"],
            [
                {"name": "root_center", "node": 0, "x": 0, "y": 0, "z": 0},
                {"name": "free_tip_center", "node": 2, "x": 1, "y": 0, "z": 0},
            ],
        )
        return matlab, reference, probes

    def test_compare_computes_vector_norms_tip_percent_and_status(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab, reference, probes = self.make_inputs(root)
            out_csv = root / "compare.csv"
            out_md = root / "compare.md"

            result = comparator.main(
                [
                    "--matlab",
                    str(matlab),
                    "--reference",
                    str(reference),
                    "--reference-solver",
                    "abaqus",
                    "--reference-index-base",
                    "1",
                    "--probes",
                    str(probes),
                    "--out-csv",
                    str(out_csv),
                    "--out-md",
                    str(out_md),
                ]
            )

            self.assertEqual(result, 0)
            rows = read_csv(out_csv)
            self.assertEqual([row["probe"] for row in rows], ["root_center", "free_tip_center"])
            tip = rows[1]
            self.assertAlmostEqual(float(tip["abs_diff"]), math.sqrt(41.0))
            self.assertAlmostEqual(float(tip["rel_diff"]), math.sqrt(41.0) / 4.0)
            self.assertAlmostEqual(float(tip["free_tip_deflection_rel_pct"]), 25.0)
            self.assertEqual(tip["reference_solver"], "abaqus")
            self.assertEqual(
                tip["fe_result_correctness_status"],
                "REPORTED_NO_HARD_THRESHOLD",
            )
            self.assertEqual(tip["status"], "reported_no_hard_threshold")
            self.assertEqual(float(tip["abaqus_uz"]), 4.0)
            report = out_md.read_text(encoding="utf-8")
            self.assertIn("REPORTED_NO_HARD_THRESHOLD", report)
            self.assertIn("25", report)

    def test_zero_reference_uses_epsilon_denominator(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab, reference, probes = self.make_inputs(root)
            write_csv(
                reference,
                ["node_zero_based", "ux", "uy", "uz"],
                [{"node_zero_based": 0, "ux": 0, "uy": 0, "uz": 0}],
            )
            write_csv(
                matlab,
                ["node", "ux", "uy", "uz"],
                [{"node": 0, "ux": 1, "uy": 0, "uz": 0}],
            )
            write_csv(
                probes,
                ["name", "node"],
                [{"name": "free_tip_center", "node": 0}],
            )

            rows = comparator.compare_files(
                matlab,
                reference,
                probes,
                reference_solver="reference",
                reference_index_base=0,
            )

            self.assertEqual(rows[0]["abs_diff"], 1.0)
            self.assertTrue(math.isclose(rows[0]["rel_diff"], 1.0e30, rel_tol=1.0e-15))
            self.assertTrue(
                math.isclose(
                    rows[0]["free_tip_deflection_rel_pct"],
                    1.0e32,
                    rel_tol=1.0e-15,
                )
            )

    def test_large_finite_vectors_do_not_overflow_and_nonfinite_metrics_fail(self) -> None:
        comparator = load_comparator()
        self.assertTrue(math.isfinite(comparator._norm((1.0e308, 0.0, 0.0))))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab = root / "matlab.csv"
            reference = root / "reference.csv"
            probes = root / "probes.csv"
            write_csv(
                matlab,
                ["node", "ux", "uy", "uz"],
                [{"node": 0, "ux": 1.0e308, "uy": 0, "uz": 0}],
            )
            write_csv(
                reference,
                ["node", "ux", "uy", "uz"],
                [{"node": 0, "ux": -1.0e308, "uy": 0, "uz": 0}],
            )
            write_csv(
                probes,
                ["name", "node"],
                [{"name": "free_tip_center", "node": 0}],
            )

            with self.assertRaisesRegex(ValueError, "non-finite derived metric"):
                comparator.compare_files(
                    matlab,
                    reference,
                    probes,
                    reference_solver="reference",
                    reference_index_base=0,
                )

    def test_all_mapping_columns_must_normalize_to_same_node(self) -> None:
        comparator = load_comparator()
        row = {
            "cpp_node": "4",
            "node_zero_based": "4",
            "node": "5",
            "node_label": "5",
        }
        self.assertEqual(comparator.resolve_node(row, index_base=1), 4)

        row["node_label"] = "6"
        with self.assertRaisesRegex(ValueError, "inconsistent node mapping"):
            comparator.resolve_node(row, index_base=1)

    def test_node_and_node_label_follow_reference_index_base(self) -> None:
        comparator = load_comparator()
        self.assertEqual(comparator.resolve_node({"node": "7"}, index_base=0), 7)
        self.assertEqual(comparator.resolve_node({"node": "7"}, index_base=1), 6)
        self.assertEqual(
            comparator.resolve_node({"node_label": "7"}, index_base=1), 6
        )

    def test_duplicate_displacement_node_is_rejected(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicates.csv"
            write_csv(
                path,
                ["node", "ux", "uy", "uz"],
                [
                    {"node": 0, "ux": 0, "uy": 0, "uz": 0},
                    {"node": 0, "ux": 1, "uy": 0, "uz": 0},
                ],
            )
            with self.assertRaisesRegex(ValueError, "duplicate node"):
                comparator.read_displacements(path, index_base=0)

    def test_missing_probe_node_is_rejected(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab, reference, probes = self.make_inputs(root)
            write_csv(
                probes,
                ["name", "node"],
                [{"name": "missing", "node": 99}],
            )
            with self.assertRaisesRegex(ValueError, "missing node 99"):
                comparator.compare_files(
                    matlab,
                    reference,
                    probes,
                    reference_solver="reference",
                    reference_index_base=1,
                )

    def test_missing_columns_nonfinite_values_and_mapping_are_rejected(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = (
                (
                    ["node", "ux", "uy"],
                    [{"node": 0, "ux": 0, "uy": 0}],
                    "missing required columns",
                ),
                (
                    ["node", "ux", "uy", "uz"],
                    [{"node": 0, "ux": "nan", "uy": 0, "uz": 0}],
                    "non-finite",
                ),
                (
                    ["ux", "uy", "uz"],
                    [{"ux": 0, "uy": 0, "uz": 0}],
                    "node mapping",
                ),
            )
            for index, (fields, rows, message) in enumerate(cases):
                path = root / f"invalid-{index}.csv"
                write_csv(path, fields, rows)
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        comparator.read_displacements(path, index_base=0)

    def test_duplicate_probe_name_or_node_is_rejected(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probes.csv"
            for rows in (
                [{"name": "a", "node": 0}, {"name": "a", "node": 1}],
                [{"name": "a", "node": 0}, {"name": "b", "node": 0}],
            ):
                write_csv(path, ["name", "node"], rows)
                with self.subTest(rows=rows):
                    with self.assertRaisesRegex(ValueError, "duplicate probe"):
                        comparator.read_probes(path)

    def test_deprecated_abaqus_alias_selects_abaqus_solver_columns(self) -> None:
        comparator = load_comparator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab, reference, probes = self.make_inputs(root)
            out_csv = root / "compare.csv"
            out_md = root / "compare.md"

            result = comparator.main(
                [
                    "--matlab",
                    str(matlab),
                    "--abaqus",
                    str(reference),
                    "--reference-index-base",
                    "1",
                    "--probes",
                    str(probes),
                    "--out-csv",
                    str(out_csv),
                    "--out-md",
                    str(out_md),
                ]
            )

            self.assertEqual(result, 0)
            first = read_csv(out_csv)[0]
            self.assertEqual(first["reference_solver"], "abaqus")
            self.assertIn("abaqus_ux", first)


if __name__ == "__main__":
    unittest.main()
