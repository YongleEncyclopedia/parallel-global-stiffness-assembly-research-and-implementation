#!/usr/bin/env python3
"""比较 MATLAB 自研矩阵求解位移与独立参考求解器的 probe 位移。"""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Optional, Sequence


EPSILON = 1.0e-30
VALID_STATUS = "REPORTED_NO_HARD_THRESHOLD"
LEGACY_STATUS = "reported_no_hard_threshold"
MAPPING_COLUMNS = (
    ("cpp_node", 0),
    ("node_zero_based", 0),
    ("node", None),
    ("node_label", None),
)


def _parse_integer(value: str, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer in {field}: {value!r}") from exc
    return parsed


def resolve_node(row: dict[str, str], index_base: int) -> int:
    """按固定优先级解析节点，并拒绝多个映射列之间的不一致。"""

    if index_base not in (0, 1):
        raise ValueError(f"index_base must be 0 or 1, got {index_base}")
    resolved: list[tuple[str, int]] = []
    for column, fixed_base in MAPPING_COLUMNS:
        raw = row.get(column)
        if raw is None or not raw.strip():
            continue
        value = _parse_integer(raw.strip(), field=column)
        base = fixed_base if fixed_base is not None else index_base
        node = value - base
        if node < 0:
            raise ValueError(f"negative zero-based node from {column}={value}")
        resolved.append((column, node))
    if not resolved:
        raise ValueError(
            "missing node mapping; expected one of cpp_node, node_zero_based, node, node_label"
        )
    nodes = {node for _, node in resolved}
    if len(nodes) != 1:
        details = ", ".join(f"{column}->{node}" for column, node in resolved)
        raise ValueError(f"inconsistent node mapping columns: {details}")
    return resolved[0][1]


def _require_columns(path: Path, fieldnames: Optional[list[str]], required: set[str]) -> None:
    actual = set(fieldnames or [])
    missing = sorted(required - actual)
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")


def read_displacements(path: Path, index_base: int) -> dict[int, tuple[float, float, float]]:
    """读取位移 CSV，返回按 C++ 零基节点编号索引的三维向量。"""

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, {"ux", "uy", "uz"})
        if not set(reader.fieldnames or []).intersection(column for column, _ in MAPPING_COLUMNS):
            raise ValueError(f"{path}: missing node mapping column")
        displacements: dict[int, tuple[float, float, float]] = {}
        for line_number, row in enumerate(reader, start=2):
            node = resolve_node(row, index_base)
            if node in displacements:
                raise ValueError(f"{path}:{line_number}: duplicate node {node}")
            try:
                vector = tuple(float(row[field]) for field in ("ux", "uy", "uz"))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid displacement component"
                ) from exc
            if not all(math.isfinite(value) for value in vector):
                raise ValueError(f"{path}:{line_number}: non-finite displacement value")
            displacements[node] = vector  # type: ignore[assignment]
    if not displacements:
        raise ValueError(f"{path}: displacement table is empty")
    return displacements


def read_probes(path: Path) -> list[tuple[str, int]]:
    """读取零基 probe 映射并保持文件顺序。"""

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames, {"name", "node"})
        probes: list[tuple[str, int]] = []
        names: set[str] = set()
        nodes: set[int] = set()
        for line_number, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError(f"{path}:{line_number}: empty probe name")
            node = _parse_integer((row.get("node") or "").strip(), field="node")
            if node < 0:
                raise ValueError(f"{path}:{line_number}: negative probe node {node}")
            if name in names:
                raise ValueError(f"{path}:{line_number}: duplicate probe name {name!r}")
            if node in nodes:
                raise ValueError(f"{path}:{line_number}: duplicate probe node {node}")
            names.add(name)
            nodes.add(node)
            probes.append((name, node))
    if not probes:
        raise ValueError(f"{path}: probe table is empty")
    return probes


def _norm(vector: tuple[float, float, float]) -> float:
    return math.hypot(*vector)


def _require_finite_metric(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"non-finite derived metric {name}: {value!r}")
    return value


def _solver_column_prefix(reference_solver: str) -> str:
    prefix = re.sub(r"[^a-zA-Z0-9_]+", "_", reference_solver.strip().lower()).strip("_")
    if not prefix:
        raise ValueError("reference solver name must not be empty")
    if prefix[0].isdigit():
        prefix = f"reference_{prefix}"
    return prefix


def compare_files(
    matlab_path: Path,
    reference_path: Path,
    probes_path: Path,
    *,
    reference_solver: str,
    reference_index_base: int,
) -> list[dict[str, object]]:
    matlab = read_displacements(matlab_path, index_base=0)
    reference = read_displacements(reference_path, index_base=reference_index_base)
    probes = read_probes(probes_path)
    solver_prefix = _solver_column_prefix(reference_solver)
    rows: list[dict[str, object]] = []
    for probe_name, node in probes:
        if node not in matlab:
            raise ValueError(f"MATLAB displacement table is missing node {node} for {probe_name}")
        if node not in reference:
            raise ValueError(f"reference displacement table is missing node {node} for {probe_name}")
        matlab_vector = matlab[node]
        reference_vector = reference[node]
        delta = tuple(
            matlab_value - reference_value
            for matlab_value, reference_value in zip(matlab_vector, reference_vector)
        )
        abs_diff = _require_finite_metric("abs_diff", _norm(delta))  # type: ignore[arg-type]
        matlab_magnitude = _require_finite_metric(
            "matlab_umag", _norm(matlab_vector)
        )
        reference_magnitude = _require_finite_metric(
            "reference_umag", _norm(reference_vector)
        )
        rel_diff = _require_finite_metric(
            "rel_diff", abs_diff / max(reference_magnitude, EPSILON)
        )
        tip_percent: object = ""
        if probe_name == "free_tip_center":
            tip_percent = _require_finite_metric(
                "free_tip_deflection_rel_pct",
                100.0
                * abs(matlab_magnitude - reference_magnitude)
                / max(reference_magnitude, EPSILON),
            )
        row: dict[str, object] = {
            "node": node,
            "probe": probe_name,
            "validation_level": "finite_element_probe",
            "reference_solver": reference_solver,
            "matlab_ux": matlab_vector[0],
            "matlab_uy": matlab_vector[1],
            "matlab_uz": matlab_vector[2],
            "matlab_umag": matlab_magnitude,
            f"{solver_prefix}_ux": reference_vector[0],
            f"{solver_prefix}_uy": reference_vector[1],
            f"{solver_prefix}_uz": reference_vector[2],
            f"{solver_prefix}_umag": reference_magnitude,
            "abs_diff": abs_diff,
            "rel_diff": rel_diff,
            "free_tip_deflection_rel_pct": tip_percent,
            "fe_result_correctness_status": VALID_STATUS,
            "status": LEGACY_STATUS,
        }
        rows.append(row)
    return rows


def _fieldnames(reference_solver: str) -> list[str]:
    prefix = _solver_column_prefix(reference_solver)
    return [
        "node",
        "probe",
        "validation_level",
        "reference_solver",
        "matlab_ux",
        "matlab_uy",
        "matlab_uz",
        "matlab_umag",
        f"{prefix}_ux",
        f"{prefix}_uy",
        f"{prefix}_uz",
        f"{prefix}_umag",
        "abs_diff",
        "rel_diff",
        "free_tip_deflection_rel_pct",
        "fe_result_correctness_status",
        "status",
    ]


def write_csv_report(path: Path, rows: list[dict[str, object]], reference_solver: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_fieldnames(reference_solver))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_report(
    path: Path,
    rows: list[dict[str, object]],
    *,
    matlab_path: Path,
    reference_path: Path,
    probes_path: Path,
    reference_solver: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tip = next((row for row in rows if row["probe"] == "free_tip_center"), None)
    lines = [
        "# Validation displacement comparison",
        "",
        f"- MATLAB source: `{matlab_path}`",
        f"- Reference source: `{reference_path}`",
        f"- Reference solver: `{reference_solver}`",
        f"- Probes: `{probes_path}`",
        f"- Status: `{VALID_STATUS}`",
        "- No hard physical pass/fail threshold is imposed by this comparator.",
        "",
        "The diagnostic vector errors are $d_{\\mathrm{abs}}=\\lVert u_p-u_r\\rVert_2$ and "
        "$d_{\\mathrm{rel}}=d_{\\mathrm{abs}}/\\max(\\lVert u_r\\rVert_2,10^{-30})$.",
        "",
    ]
    if tip is not None:
        lines.extend(
            [
                "The free-tip displacement-magnitude difference is "
                f"`{float(tip['free_tip_deflection_rel_pct']):.12g}%`.",
                "",
            ]
        )
    lines.extend(
        [
            "| Probe | Node | Absolute vector difference | Relative vector difference | Status |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['probe']} | {row['node']} | {float(row['abs_diff']):.12g} | "
            f"{float(row['rel_diff']):.12g} | {VALID_STATUS} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matlab", required=True, type=Path)
    reference = parser.add_mutually_exclusive_group(required=True)
    reference.add_argument("--reference", type=Path)
    reference.add_argument("--abaqus", type=Path, help="deprecated alias for --reference")
    parser.add_argument("--reference-solver", default=None)
    parser.add_argument("--reference-index-base", type=int, choices=(0, 1), default=0)
    parser.add_argument("--probes", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    reference_path = args.reference if args.reference is not None else args.abaqus
    reference_solver = args.reference_solver or ("abaqus" if args.abaqus is not None else "reference")
    rows = compare_files(
        args.matlab,
        reference_path,
        args.probes,
        reference_solver=reference_solver,
        reference_index_base=args.reference_index_base,
    )
    write_csv_report(args.out_csv, rows, reference_solver)
    write_markdown_report(
        args.out_md,
        rows,
        matlab_path=args.matlab,
        reference_path=reference_path,
        probes_path=args.probes,
        reference_solver=reference_solver,
    )
    print(f"wrote {args.out_csv} and {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
