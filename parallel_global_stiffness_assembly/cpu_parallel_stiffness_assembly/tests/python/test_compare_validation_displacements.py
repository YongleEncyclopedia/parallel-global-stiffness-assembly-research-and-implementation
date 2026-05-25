#!/usr/bin/env python3
"""Unit tests for validation displacement comparison reports."""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "compare_validation_displacements.py"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class CompareValidationDisplacementsTests(unittest.TestCase):
    def test_reference_solver_label_controls_columns_and_markdown_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matlab = root / "matlab.csv"
            reference = root / "comsol.csv"
            probes = root / "probes.csv"
            out_csv = root / "compare.csv"
            out_md = root / "compare.md"

            write_csv(matlab, ["node", "ux", "uy", "uz"], [{"node": 7, "ux": 1.0, "uy": 2.0, "uz": 3.0}])
            write_csv(reference, ["node", "ux", "uy", "uz"], [{"node": 7, "ux": 1.5, "uy": 2.0, "uz": 2.0}])
            write_csv(probes, ["name", "node"], [{"name": "tip", "node": 7}])

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--matlab",
                    str(matlab),
                    "--abaqus",
                    str(reference),
                    "--reference-solver",
                    "comsol",
                    "--probes",
                    str(probes),
                    "--out-csv",
                    str(out_csv),
                    "--out-md",
                    str(out_md),
                ],
                check=True,
            )

            with out_csv.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)
            self.assertIn("comsol_ux", fieldnames)
            self.assertNotIn("abaqus_ux", fieldnames)
            self.assertEqual(rows[0]["validation_level"], "finite_element_probe")
            self.assertEqual(rows[0]["reference_solver"], "comsol")
            self.assertEqual(rows[0]["fe_result_correctness_status"], "REPORTED_NO_HARD_THRESHOLD")

            markdown = out_md.read_text(encoding="utf-8")
            self.assertIn("COMSOL source", markdown)
            self.assertNotIn("Abaqus source", markdown)
            self.assertIn("Validation level: finite-element probe displacement", markdown)


if __name__ == "__main__":
    unittest.main()
