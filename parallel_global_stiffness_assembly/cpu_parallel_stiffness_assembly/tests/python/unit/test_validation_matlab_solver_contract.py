from __future__ import annotations

import re
import unittest
from pathlib import Path


CPU_ROOT = Path(__file__).resolve().parents[3]
SOLVER = CPU_ROOT / "scripts" / "solve_validation_export_matlab.m"


class MatlabValidationSolverContractTests(unittest.TestCase):
    def solver_source(self) -> str:
        self.assertTrue(SOLVER.is_file(), f"missing MATLAB solver: {SOLVER}")
        return SOLVER.read_text(encoding="utf-8")

    def test_public_entrypoint_and_required_files_are_stable(self) -> None:
        source = self.solver_source()

        self.assertRegex(
            source,
            r"(?m)^function\s+solve_validation_export_matlab\(result_dir,\s*prefix\)\s*$",
        )
        for suffix in ("_K.mtx", "_force.csv", "_bc.csv", "_probes.csv"):
            with self.subTest(suffix=suffix):
                self.assertIn(suffix, source)

    def test_matrix_market_reader_is_internal_strict_and_symmetric(self) -> None:
        source = self.solver_source()

        self.assertNotRegex(source.lower(), r"\bmmread\b")
        self.assertIn("%%MatrixMarket matrix coordinate real symmetric", source)
        self.assertRegex(source, r"function\s+\[K,\s*stored_nnz\]\s*=\s*read_matrix_market_symmetric")
        self.assertRegex(source, r"rows\s*<\s*cols")
        self.assertRegex(source, r"rows\s*<\s*1")
        self.assertRegex(source, r"rows\s*>\s*n_rows")
        self.assertRegex(source, r"cols\s*>\s*n_cols")
        self.assertIn("~isreal(dimensions)", source)
        self.assertIn("~isreal(values)", source)
        self.assertIn("all(isfinite(values))", source)
        self.assertRegex(
            source,
            r"sparse\(\s*\[rows;\s*cols\(off_diagonal\)\]",
        )
        self.assertRegex(
            source,
            r"\[cols;\s*rows\(off_diagonal\)\]",
        )

    def test_system_and_csv_indices_are_validated_and_converted(self) -> None:
        source = self.solver_source()

        self.assertRegex(source, r"n_rows\s*~=\s*n_cols")
        self.assertRegex(source, r"mod\(n_dofs,\s*3\)\s*~=\s*0")
        self.assertRegex(source, r"dofs\s*<\s*0\s*\|\s*dofs\s*>\s*2")
        self.assertRegex(source, r"nodes\s*<\s*0\s*\|\s*nodes\s*>=\s*n_nodes")
        self.assertRegex(
            source,
            r"matlab_dofs\s*=\s*3\s*\*\s*nodes\s*\+\s*dofs\s*\+\s*1",
        )
        self.assertRegex(
            source,
            r"numel\(unique\(constrained_dofs\)\)\s*~=\s*numel\(constrained_dofs\)",
        )

    def test_nonzero_dirichlet_reduction_is_explicit(self) -> None:
        source = self.solver_source()

        self.assertRegex(
            source,
            re.compile(
                r"rhs_free\s*=\s*force_vector\(free_dofs\)\s*-\s*"
                r"K\(free_dofs,\s*constrained_dofs\)\s*\*\s*constrained_values\s*;"
            ),
        )
        self.assertRegex(
            source,
            re.compile(
                r"displacement\(free_dofs\)\s*=\s*"
                r"K\(free_dofs,\s*free_dofs\)\s*\\\s*rhs_free\s*;"
            ),
        )
        self.assertIn("displacement(constrained_dofs) = constrained_values;", source)

    def test_outputs_and_residual_metadata_are_stable(self) -> None:
        source = self.solver_source()

        for suffix in (
            "_matlab_displacements.csv",
            "_matlab_probe_summary.csv",
            "_matlab_solve_metadata.json",
        ):
            with self.subTest(suffix=suffix):
                self.assertIn(suffix, source)
        self.assertIn("{'node', 'ux', 'uy', 'uz', 'umag'}", source)
        self.assertIn("{'name', 'node', 'ux', 'uy', 'uz', 'umag'}", source)
        self.assertIn("absolute_free_l2", source)
        self.assertIn("relative_free_l2", source)
        self.assertIn("metadata.status", source)
        self.assertIn("metadata.matrix.rows", source)
        self.assertIn("metadata.matrix.cols", source)

    def test_input_validation_helpers_cover_columns_integrality_and_finiteness(self) -> None:
        source = self.solver_source()

        self.assertRegex(source, r"function\s+require_columns\(")
        self.assertRegex(source, r"function\s+validate_integer_vector\(")
        self.assertRegex(source, r"function\s+validate_finite_vector\(")
        self.assertGreaterEqual(source.count("~isreal(values)"), 3)
        for columns in (
            "{'node', 'dof', 'force'}",
            "{'node', 'dof', 'value'}",
            "{'name', 'node'}",
        ):
            with self.subTest(columns=columns):
                self.assertIn(columns, source)


if __name__ == "__main__":
    unittest.main()
