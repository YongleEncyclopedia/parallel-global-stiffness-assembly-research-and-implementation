#!/usr/bin/env python3
"""Generate and run Abaqus reference solves for validation_export cases."""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_CASES = (
    "cantilever_hex8_small",
    "cantilever_hex8_medium",
    "cantilever_tet4_small",
    "cantilever_tet4_medium",
)

CASE_SPECS = {
    "cantilever_hex8_small": ("hex8", 2, 2, 2),
    "cantilever_hex8_medium": ("hex8", 12, 4, 4),
    "cantilever_tet4_small": ("tet4", 2, 2, 2),
    "cantilever_tet4_medium": ("tet4", 12, 4, 4),
}

JOB_ALIASES = {
    "cantilever_hex8_small": "h8s",
    "cantilever_hex8_medium": "h8m",
    "cantilever_tet4_small": "t4s",
    "cantilever_tet4_medium": "t4m",
}


@dataclass(frozen=True)
class Node:
    label: int
    cpp_node: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Element:
    label: int
    node_labels: tuple[int, ...]


@dataclass(frozen=True)
class Probe:
    name: str
    cpp_node: int
    abaqus_node: int
    target: tuple[float, float, float]
    actual: tuple[float, float, float]


@dataclass(frozen=True)
class AbaqusCase:
    name: str
    element_kind: str
    abaqus_element_type: str
    nodes: tuple[Node, ...]
    elements: tuple[Element, ...]
    fixed_nodes: tuple[int, ...]
    loaded_nodes: tuple[int, ...]
    loads: tuple[tuple[int, int, float], ...]
    probes: tuple[Probe, ...]
    length: float
    width: float
    thickness: float
    young_modulus: float
    poisson_ratio: float


def split_csv(text: str) -> list[str]:
    return [token.strip() for token in text.split(",") if token.strip()]


def structured_node_id(i: int, j: int, k: int, nx: int, ny: int) -> int:
    return (k * (ny + 1) + j) * (nx + 1) + i


def node_label(cpp_node: int) -> int:
    return cpp_node + 1


def make_nodes(nx: int, ny: int, nz: int, length: float, width: float, thickness: float) -> tuple[Node, ...]:
    nodes: list[Node] = []
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                cpp_node = structured_node_id(i, j, k, nx, ny)
                nodes.append(
                    Node(
                        label=node_label(cpp_node),
                        cpp_node=cpp_node,
                        x=length * i / nx,
                        y=width * j / ny,
                        z=thickness * k / nz,
                    )
                )
    return tuple(nodes)


def make_hex8_elements(nx: int, ny: int, nz: int) -> tuple[Element, ...]:
    elements: list[Element] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                labels = (
                    node_label(structured_node_id(i, j, k, nx, ny)),
                    node_label(structured_node_id(i + 1, j, k, nx, ny)),
                    node_label(structured_node_id(i + 1, j + 1, k, nx, ny)),
                    node_label(structured_node_id(i, j + 1, k, nx, ny)),
                    node_label(structured_node_id(i, j, k + 1, nx, ny)),
                    node_label(structured_node_id(i + 1, j, k + 1, nx, ny)),
                    node_label(structured_node_id(i + 1, j + 1, k + 1, nx, ny)),
                    node_label(structured_node_id(i, j + 1, k + 1, nx, ny)),
                )
                elements.append(Element(len(elements) + 1, labels))
    return tuple(elements)


def make_tet4_elements(nx: int, ny: int, nz: int) -> tuple[Element, ...]:
    elements: list[Element] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                n000 = structured_node_id(i, j, k, nx, ny)
                n100 = structured_node_id(i + 1, j, k, nx, ny)
                n010 = structured_node_id(i, j + 1, k, nx, ny)
                n110 = structured_node_id(i + 1, j + 1, k, nx, ny)
                n001 = structured_node_id(i, j, k + 1, nx, ny)
                n101 = structured_node_id(i + 1, j, k + 1, nx, ny)
                n011 = structured_node_id(i, j + 1, k + 1, nx, ny)
                n111 = structured_node_id(i + 1, j + 1, k + 1, nx, ny)
                for tet in (
                    (n000, n100, n110, n111),
                    (n000, n110, n010, n111),
                    (n000, n010, n011, n111),
                    (n000, n011, n001, n111),
                    (n000, n001, n101, n111),
                    (n000, n101, n100, n111),
                ):
                    elements.append(Element(len(elements) + 1, tuple(node_label(n) for n in tet)))
    return tuple(elements)


def nearest_node(nodes: Iterable[Node], target: tuple[float, float, float]) -> Node:
    def dist2(node: Node) -> float:
        return (node.x - target[0]) ** 2 + (node.y - target[1]) ** 2 + (node.z - target[2]) ** 2

    return min(nodes, key=dist2)


def build_structured_case(
    name: str,
    *,
    length: float = 1.0,
    width: float = 0.2,
    thickness: float = 0.1,
    young_modulus: float = 1.0,
    poisson_ratio: float = 0.3,
    total_load: float = -1.0,
    load_dof: int = 2,
) -> AbaqusCase:
    if name not in CASE_SPECS:
        raise ValueError(f"unsupported validation case: {name}")
    element_kind, nx, ny, nz = CASE_SPECS[name]
    nodes = make_nodes(nx, ny, nz, length, width, thickness)
    if element_kind == "hex8":
        elements = make_hex8_elements(nx, ny, nz)
        abaqus_element_type = "C3D8"
    else:
        elements = make_tet4_elements(nx, ny, nz)
        abaqus_element_type = "C3D4"

    fixed = tuple(node.label for node in nodes if math.isclose(node.x, 0.0, abs_tol=1.0e-12))
    loaded = tuple(node.label for node in nodes if math.isclose(node.x, length, abs_tol=1.0e-12))
    abaqus_dof = load_dof + 1
    nodal_load = total_load / len(loaded)
    loads = tuple((label, abaqus_dof, nodal_load) for label in loaded)

    yc = 0.5 * width
    zc = 0.5 * thickness
    probe_targets = (
        ("free_tip_center", (length, yc, zc)),
        ("midspan_center", (0.5 * length, yc, zc)),
        ("root_center", (0.0, yc, zc)),
    )
    probes = []
    for probe_name, target in probe_targets:
        node = nearest_node(nodes, target)
        probes.append(
            Probe(
                name=probe_name,
                cpp_node=node.cpp_node,
                abaqus_node=node.label,
                target=target,
                actual=(node.x, node.y, node.z),
            )
        )

    return AbaqusCase(
        name=name,
        element_kind=element_kind,
        abaqus_element_type=abaqus_element_type,
        nodes=nodes,
        elements=elements,
        fixed_nodes=fixed,
        loaded_nodes=loaded,
        loads=loads,
        probes=tuple(probes),
        length=length,
        width=width,
        thickness=thickness,
        young_modulus=young_modulus,
        poisson_ratio=poisson_ratio,
    )


def write_labels(handle, labels: Iterable[int], per_line: int = 16) -> None:
    row: list[str] = []
    for label in labels:
        row.append(str(label))
        if len(row) == per_line:
            handle.write(", ".join(row) + "\n")
            row = []
    if row:
        handle.write(", ".join(row) + "\n")


def write_abaqus_inp(case: AbaqusCase, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("*Heading\n")
        handle.write(f"** Generated from validation_export case {case.name}.\n")
        handle.write("** Node labels are C++ 0-based node indices plus one.\n")
        if case.abaqus_element_type == "C3D8":
            handle.write("** Element formulation: C3D8 full integration, not C3D8R.\n")
        else:
            handle.write("** Element formulation: C3D4 linear tetrahedron.\n")
        handle.write("*Preprint, echo=NO, model=NO, history=NO, contact=NO\n")
        handle.write("*Node\n")
        for node in case.nodes:
            handle.write(f"{node.label}, {node.x:.17g}, {node.y:.17g}, {node.z:.17g}\n")
        handle.write(f"*Element, type={case.abaqus_element_type}, elset=EALL\n")
        for element in case.elements:
            handle.write(f"{element.label}, " + ", ".join(str(label) for label in element.node_labels) + "\n")
        handle.write("*Nset, nset=FIXED\n")
        write_labels(handle, case.fixed_nodes)
        handle.write("*Nset, nset=LOADED\n")
        write_labels(handle, case.loaded_nodes)
        handle.write("*Nset, nset=PROBES\n")
        write_labels(handle, (probe.abaqus_node for probe in case.probes))
        handle.write("*Material, name=MAT_LINEAR_ELASTIC\n")
        handle.write("*Elastic\n")
        handle.write(f"{case.young_modulus:.17g}, {case.poisson_ratio:.17g}\n")
        handle.write("*Solid Section, elset=EALL, material=MAT_LINEAR_ELASTIC\n")
        handle.write(",\n")
        handle.write("*Boundary\n")
        handle.write("FIXED, 1, 3, 0.\n")
        handle.write("*Step, name=StaticStep, nlgeom=NO\n")
        handle.write("*Static\n")
        handle.write("1., 1., 1e-05, 1.\n")
        handle.write("*Cload\n")
        for node_label_value, dof, value in case.loads:
            handle.write(f"{node_label_value}, {dof}, {value:.17g}\n")
        handle.write("*Output, field\n")
        handle.write("*Node Output, nset=PROBES\n")
        handle.write("U\n")
        handle.write("*End Step\n")


def write_probe_mapping(case: AbaqusCase, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "probe",
                "cpp_node",
                "abaqus_node",
                "target_x",
                "target_y",
                "target_z",
                "x",
                "y",
                "z",
            ],
        )
        writer.writeheader()
        for probe in case.probes:
            writer.writerow(
                {
                    "probe": probe.name,
                    "cpp_node": probe.cpp_node,
                    "abaqus_node": probe.abaqus_node,
                    "target_x": f"{probe.target[0]:.17g}",
                    "target_y": f"{probe.target[1]:.17g}",
                    "target_z": f"{probe.target[2]:.17g}",
                    "x": f"{probe.actual[0]:.17g}",
                    "y": f"{probe.actual[1]:.17g}",
                    "z": f"{probe.actual[2]:.17g}",
                }
            )


def run_command(command: list[str], cwd: Path | None = None) -> None:
    resolved = command
    executable = shutil.which(command[0])
    if sys.platform == "win32" and executable and Path(executable).suffix.lower() in {".bat", ".cmd"}:
        resolved = ["cmd", "/c", executable, *command[1:]]
    print("+", " ".join(resolved), flush=True)
    subprocess.run(resolved, cwd=str(cwd) if cwd else None, check=True)


def run_case(args: argparse.Namespace, case_name: str) -> dict[str, object]:
    case = build_structured_case(case_name)
    case_dir = args.result_root / case_name
    abaqus_dir = case_dir / "abaqus"
    job_name = JOB_ALIASES[case_name]
    inp_path = abaqus_dir / f"{job_name}.inp"
    mapping_path = abaqus_dir / f"{case_name}_node_mapping.csv"
    write_abaqus_inp(case, inp_path)
    write_probe_mapping(case, mapping_path)

    odb_path = abaqus_dir / f"{job_name}.odb"
    if odb_path.exists() and args.reuse_existing:
        print(f"[reuse] {odb_path}")
    elif odb_path.exists():
        raise RuntimeError(f"Abaqus ODB already exists; pass --reuse-existing to reuse it: {odb_path}")
    else:
        run_command([args.abaqus_bin, f"job={job_name}", f"input={inp_path.name}", "interactive"], cwd=abaqus_dir)
    if not odb_path.exists():
        raise RuntimeError(f"Abaqus job did not produce ODB: {odb_path}")

    abaqus_csv = case_dir / f"{case_name}_abaqus_displacements.csv"
    extract_script = Path(__file__).resolve().parent / "extract_abaqus_displacements.py"
    run_command(
        [
            args.abaqus_bin,
            "python",
            str(extract_script),
            "--odb",
            str(odb_path),
            "--probes",
            str(case_dir / f"{case_name}_probes.csv"),
            "--out",
            str(abaqus_csv),
            "--mapping-out",
            str(mapping_path),
        ]
    )

    compare_csv = case_dir / f"{case_name}_abaqus_compare.csv"
    compare_md = case_dir / f"{case_name}_abaqus_compare.md"
    compare_script = Path(__file__).resolve().parent / "compare_validation_displacements.py"
    run_command(
        [
            sys.executable,
            str(compare_script),
            "--matlab",
            str(case_dir / f"{case_name}_matlab_displacements.csv"),
            "--abaqus",
            str(abaqus_csv),
            "--reference-solver",
            "abaqus",
            "--reference-index-base",
            "1",
            "--probes",
            str(case_dir / f"{case_name}_probes.csv"),
            "--out-csv",
            str(compare_csv),
            "--out-md",
            str(compare_md),
        ]
    )

    return {
        "case": case_name,
        "inp": str(inp_path),
        "odb": str(odb_path),
        "abaqus_displacements": str(abaqus_csv),
        "mapping": str(mapping_path),
        "compare_csv": str(compare_csv),
        "compare_md": str(compare_md),
        "element_type": case.abaqus_element_type,
        "integration": "full" if case.abaqus_element_type == "C3D8" else "linear_tet",
        "nodes": len(case.nodes),
        "elements": len(case.elements),
        "fixed_nodes": len(case.fixed_nodes),
        "loaded_nodes": len(case.loaded_nodes),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", required=True, type=Path)
    parser.add_argument("--cases", default=",".join(DEFAULT_CASES))
    parser.add_argument("--abaqus-bin", default="abaqus")
    parser.add_argument("--reuse-existing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = [run_case(args, case_name) for case_name in split_csv(args.cases)]
    manifest = {
        "schema_version": "abaqus-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "abaqus_bin": args.abaqus_bin,
        "result_root": str(args.result_root),
        "cases": records,
    }
    path = args.result_root / "abaqus_validation_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
