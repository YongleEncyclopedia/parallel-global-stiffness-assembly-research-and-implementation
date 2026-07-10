import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from run_abaqus_validation import (
    build_compare_command,
    build_structured_case,
    write_abaqus_inp,
)


class AbaqusValidationWorkflowTests(unittest.TestCase):
    def test_hex8_small_matches_validation_export_topology(self) -> None:
        case = build_structured_case("cantilever_hex8_small")

        self.assertEqual(len(case.nodes), 27)
        self.assertEqual(len(case.elements), 8)
        self.assertEqual(case.abaqus_element_type, "C3D8")
        self.assertEqual(len(case.fixed_nodes), 9)
        self.assertEqual(len(case.loads), 9)
        self.assertTrue(all(dof == 3 for _, dof, _ in case.loads))
        self.assertAlmostEqual(sum(value for _, _, value in case.loads), -1.0)
        self.assertEqual(
            [(probe.name, probe.cpp_node, probe.abaqus_node) for probe in case.probes],
            [("free_tip_center", 14, 15), ("midspan_center", 13, 14), ("root_center", 12, 13)],
        )

    def test_tet4_small_uses_validation_export_cube_split(self) -> None:
        case = build_structured_case("cantilever_tet4_small")

        self.assertEqual(len(case.nodes), 27)
        self.assertEqual(len(case.elements), 48)
        self.assertEqual(case.abaqus_element_type, "C3D4")
        self.assertEqual(case.elements[0].node_labels, (1, 2, 5, 14))

    def test_inp_declares_full_hex8_and_linear_tet4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hex_case = build_structured_case("cantilever_hex8_small")
            tet_case = build_structured_case("cantilever_tet4_small")
            hex_path = Path(tmp) / "hex.inp"
            tet_path = Path(tmp) / "tet.inp"

            write_abaqus_inp(hex_case, hex_path)
            write_abaqus_inp(tet_case, tet_path)

            hex_lines = hex_path.read_text(encoding="utf-8").splitlines()
            tet_lines = tet_path.read_text(encoding="utf-8").splitlines()
            hex_element_lines = [line for line in hex_lines if line.startswith("*Element")]
            self.assertEqual(hex_element_lines, ["*Element, type=C3D8, elset=EALL"])
            self.assertNotEqual(hex_element_lines, ["*Element, type=C3D8R, elset=EALL"])
            self.assertIn("*Element, type=C3D4, elset=EALL", tet_lines)

    def test_compare_command_uses_generic_reference_contract(self) -> None:
        case_dir = Path("/tmp/validation") / "cantilever_hex8_small"

        command = build_compare_command(
            case_dir,
            "cantilever_hex8_small",
            Path("/repo/scripts/compare_validation_displacements.py"),
        )

        self.assertIn("--reference", command)
        self.assertNotIn("--abaqus", command)
        self.assertEqual(command[command.index("--reference-solver") + 1], "abaqus")
        self.assertEqual(command[command.index("--reference-index-base") + 1], "1")
        self.assertEqual(
            command[command.index("--reference") + 1],
            str(case_dir / "cantilever_hex8_small_abaqus_displacements.csv"),
        )


if __name__ == "__main__":
    unittest.main()
