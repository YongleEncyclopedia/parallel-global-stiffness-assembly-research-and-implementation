#!/usr/bin/env python3
"""Validate the seven-file validation_export contract on Tet4 and Hex8."""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Iterable


EXPECTED_COLUMNS = {
    "force": ("node", "dof", "force"),
    "bc": ("node", "dof", "value"),
    "probes": ("name", "node", "target_x", "target_y", "target_z", "x", "y", "z"),
    "nodes": ("node", "x", "y", "z"),
    "elements": (
        "element",
        "element_type",
        "node_count",
        "n0",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "n7",
    ),
}


def read_csv(path: Path, expected_columns: Iterable[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == tuple(expected_columns), (
            f"{path}: expected columns {tuple(expected_columns)}, got {reader.fieldnames}"
        )
        rows = list(reader)
    assert rows, f"{path}: CSV must not be empty"
    return rows


def parse_int(value: str, context: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise AssertionError(f"{context}: expected integer, got {value!r}") from exc
    return parsed


def parse_finite(value: str, context: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AssertionError(f"{context}: expected number, got {value!r}") from exc
    assert math.isfinite(parsed), f"{context}: expected finite number, got {value!r}"
    return parsed


def validate_matrix_market(path: Path, metadata: dict[str, object], n_dofs: int) -> None:
    with path.open(encoding="utf-8") as handle:
        header = handle.readline().strip()
        assert header == "%%MatrixMarket matrix coordinate real symmetric"
        data_lines = [line.strip() for line in handle if line.strip() and not line.startswith("%")]
    assert data_lines, f"{path}: missing dimension line"
    dimensions = data_lines[0].split()
    assert len(dimensions) == 3, f"{path}: malformed dimension line"
    n_rows, n_cols, stored_nnz = (
        parse_int(value, f"{path}: dimension") for value in dimensions
    )
    assert n_rows == n_cols == n_dofs, f"{path}: matrix dimensions do not match mesh DOFs"
    assert stored_nnz >= 0
    assert len(data_lines[1:]) == stored_nnz, f"{path}: stored entry count mismatch"

    seen: set[tuple[int, int]] = set()
    for line_number, line in enumerate(data_lines[1:], start=3):
        fields = line.split()
        assert len(fields) == 3, f"{path}:{line_number}: malformed matrix entry"
        row = parse_int(fields[0], f"{path}:{line_number}: row")
        col = parse_int(fields[1], f"{path}:{line_number}: column")
        parse_finite(fields[2], f"{path}:{line_number}: value")
        assert 1 <= col <= row <= n_dofs, (
            f"{path}:{line_number}: expected one-based lower-triangle coordinate"
        )
        assert (row, col) not in seen, f"{path}:{line_number}: duplicate matrix coordinate"
        seen.add((row, col))

    matrix = metadata["matrix"]
    assert isinstance(matrix, dict)
    assert matrix["format"] == "MatrixMarket coordinate real symmetric"
    assert matrix["rows"] == n_rows
    assert matrix["cols"] == n_cols
    assert matrix["lower_triangle_nnz"] == stored_nnz


def validate_nodes(path: Path, expected_count: int) -> list[dict[str, str]]:
    rows = read_csv(path, EXPECTED_COLUMNS["nodes"])
    assert len(rows) == expected_count
    for expected_node, row in enumerate(rows):
        assert parse_int(row["node"], f"{path}: node") == expected_node
        for coordinate in ("x", "y", "z"):
            parse_finite(row[coordinate], f"{path}: {coordinate}")
    return rows


def validate_elements(
    path: Path,
    expected_count: int,
    expected_type: str,
    node_count: int,
) -> None:
    rows = read_csv(path, EXPECTED_COLUMNS["elements"])
    assert len(rows) == expected_count
    nodes_per_element = 4 if expected_type == "tet4" else 8
    for expected_element, row in enumerate(rows):
        assert parse_int(row["element"], f"{path}: element") == expected_element
        assert row["element_type"] == expected_type
        assert parse_int(row["node_count"], f"{path}: node_count") == nodes_per_element
        for local_node in range(8):
            value = row[f"n{local_node}"]
            if local_node < nodes_per_element:
                node = parse_int(value, f"{path}: n{local_node}")
                assert 0 <= node < node_count
            else:
                assert value == "", f"{path}: unused n{local_node} must be empty"


def validate_force(path: Path, metadata: dict[str, object], node_count: int) -> None:
    rows = read_csv(path, EXPECTED_COLUMNS["force"])
    load = metadata["load"]
    assert isinstance(load, dict)
    assert len(rows) == load["loaded_nodes"]
    pairs: set[tuple[int, int]] = set()
    total = 0.0
    for row in rows:
        node = parse_int(row["node"], f"{path}: node")
        dof = parse_int(row["dof"], f"{path}: dof")
        force = parse_finite(row["force"], f"{path}: force")
        assert 0 <= node < node_count
        assert dof == load["load_dof"]
        assert (node, dof) not in pairs, f"{path}: duplicate node/DOF load"
        pairs.add((node, dof))
        total += force
    assert math.isclose(total, float(load["total_load"]), rel_tol=1.0e-12, abs_tol=1.0e-12)


def validate_boundary(path: Path, metadata: dict[str, object], node_count: int) -> None:
    rows = read_csv(path, EXPECTED_COLUMNS["bc"])
    boundary = metadata["boundary"]
    assert isinstance(boundary, dict)
    assert len(rows) == boundary["fixed_dofs"]
    pairs: set[tuple[int, int]] = set()
    for row in rows:
        node = parse_int(row["node"], f"{path}: node")
        dof = parse_int(row["dof"], f"{path}: dof")
        parse_finite(row["value"], f"{path}: value")
        assert 0 <= node < node_count
        assert 0 <= dof < 3
        assert (node, dof) not in pairs, f"{path}: duplicate constrained node/DOF"
        pairs.add((node, dof))


def validate_probes(path: Path, metadata: dict[str, object], node_count: int) -> None:
    rows = read_csv(path, EXPECTED_COLUMNS["probes"])
    names: set[str] = set()
    nodes: set[int] = set()
    normalized: list[dict[str, object]] = []
    for row in rows:
        name = row["name"].strip()
        node = parse_int(row["node"], f"{path}: node")
        assert name and name not in names
        assert 0 <= node < node_count and node not in nodes
        names.add(name)
        nodes.add(node)
        normalized.append({"name": name, "node": node})
        for coordinate in ("target_x", "target_y", "target_z", "x", "y", "z"):
            parse_finite(row[coordinate], f"{path}: {coordinate}")
    assert normalized == metadata["probes"]


def validate_case_export(out_dir: Path, case: str) -> None:
    files = {
        "K": out_dir / f"{case}_K.mtx",
        "force": out_dir / f"{case}_force.csv",
        "bc": out_dir / f"{case}_bc.csv",
        "probes": out_dir / f"{case}_probes.csv",
        "nodes": out_dir / f"{case}_nodes.csv",
        "elements": out_dir / f"{case}_elements.csv",
        "metadata": out_dir / f"{case}_metadata.json",
    }
    for path in files.values():
        assert path.is_file(), f"missing {path.name}"

    metadata = json.loads(files["metadata"].read_text(encoding="utf-8"))
    assert metadata["case_name"] == case
    assert metadata["stiffness_model"] == "linear_elastic_solid"
    assert metadata["kernel"] == "linear_elastic_solid"
    assert metadata["element_type"] in {"tet4", "hex8"}
    assert metadata["index_base"] == 0
    assert math.isfinite(float(metadata["material"]["E"]))
    assert math.isfinite(float(metadata["material"]["nu"]))

    mesh = metadata["mesh"]
    node_count = int(mesh["nodes"])
    element_count = int(mesh["elements"])
    n_dofs = int(mesh["dofs"])
    assert node_count > 0 and element_count > 0 and n_dofs == 3 * node_count
    validate_nodes(files["nodes"], node_count)
    validate_elements(files["elements"], element_count, metadata["element_type"], node_count)
    validate_matrix_market(files["K"], metadata, n_dofs)
    validate_force(files["force"], metadata, node_count)
    validate_boundary(files["bc"], metadata, node_count)
    validate_probes(files["probes"], metadata, node_count)

    for key in ("K", "force", "bc", "probes", "nodes", "elements"):
        assert metadata["files"][key] == files[key].name


def run_case(exe: Path, out_root: Path, case: str) -> None:
    out_dir = out_root / case
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(exe),
            "--case",
            case,
            "--E",
            "1",
            "--nu",
            "0.3",
            "--total-load",
            "-1",
            "--load-dof",
            "2",
            "--stiffness-model",
            "linear_elastic_solid",
            "--out-dir",
            str(out_dir),
            "--prefix",
            case,
        ],
        check=True,
    )
    validate_case_export(out_dir, case)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_validation_export.py VALIDATION_EXPORT_EXE OUT_DIR", file=sys.stderr)
        return 2

    exe = Path(sys.argv[1])
    out_root = Path(sys.argv[2])
    out_root.mkdir(parents=True, exist_ok=True)
    run_case(exe, out_root, "cantilever_tet4_small")
    run_case(exe, out_root, "cantilever_hex8_small")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
