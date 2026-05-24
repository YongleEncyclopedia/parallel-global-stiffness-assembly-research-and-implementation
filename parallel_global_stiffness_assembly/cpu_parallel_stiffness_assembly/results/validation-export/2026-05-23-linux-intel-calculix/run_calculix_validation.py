#!/usr/bin/env python3
"""Run CalculiX displacement probes for validation_export cantilever cases."""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Case:
    name: str
    element_type: str
    nx: int
    ny: int
    nz: int


CASES = (
    Case("cantilever_hex8_small", "hex8", 2, 2, 2),
    Case("cantilever_tet4_small", "tet4", 2, 2, 2),
    Case("cantilever_hex8_medium", "hex8", 12, 4, 4),
    Case("cantilever_tet4_medium", "tet4", 12, 4, 4),
)

LENGTH = 1.0
WIDTH = 0.2
THICKNESS = 0.1
YOUNG_MODULUS = 1.0
POISSON_RATIO = 0.3
TOTAL_LOAD = -1.0
LOAD_DOF_ZERO_BASED = 2


def structured_node_id(i: int, j: int, k: int, nx: int, ny: int) -> int:
    return (k * (ny + 1) + j) * (nx + 1) + i


def build_nodes(case: Case) -> list[tuple[float, float, float]]:
    nodes: list[tuple[float, float, float]] = []
    for k in range(case.nz + 1):
        for j in range(case.ny + 1):
            for i in range(case.nx + 1):
                nodes.append((LENGTH * i / case.nx, WIDTH * j / case.ny, THICKNESS * k / case.nz))
    return nodes


def build_elements(case: Case) -> tuple[str, list[list[int]]]:
    elements: list[list[int]] = []
    for k in range(case.nz):
        for j in range(case.ny):
            for i in range(case.nx):
                n000 = structured_node_id(i, j, k, case.nx, case.ny)
                n100 = structured_node_id(i + 1, j, k, case.nx, case.ny)
                n010 = structured_node_id(i, j + 1, k, case.nx, case.ny)
                n110 = structured_node_id(i + 1, j + 1, k, case.nx, case.ny)
                n001 = structured_node_id(i, j, k + 1, case.nx, case.ny)
                n101 = structured_node_id(i + 1, j, k + 1, case.nx, case.ny)
                n011 = structured_node_id(i, j + 1, k + 1, case.nx, case.ny)
                n111 = structured_node_id(i + 1, j + 1, k + 1, case.nx, case.ny)
                if case.element_type == "hex8":
                    elements.append([n000, n100, n110, n010, n001, n101, n111, n011])
                else:
                    elements.extend(
                        [
                            [n000, n100, n110, n111],
                            [n000, n110, n010, n111],
                            [n000, n010, n011, n111],
                            [n000, n011, n001, n111],
                            [n000, n001, n101, n111],
                            [n000, n101, n100, n111],
                        ]
                    )
    ccx_type = "C3D8" if case.element_type == "hex8" else "C3D4"
    return ccx_type, elements


def face_node_ids(nodes: list[tuple[float, float, float]], x_value: float) -> list[int]:
    tol = max(LENGTH, WIDTH, THICKNESS, 1.0) * 1.0e-9
    return [idx for idx, (x, _y, _z) in enumerate(nodes) if abs(x - x_value) <= tol]


def nearest_node(nodes: list[tuple[float, float, float]], target: tuple[float, float, float]) -> int:
    best = 0
    best_dist2 = float("inf")
    tx, ty, tz = target
    for idx, (x, y, z) in enumerate(nodes):
        dist2 = (x - tx) ** 2 + (y - ty) ** 2 + (z - tz) ** 2
        if dist2 < best_dist2:
            best = idx
            best_dist2 = dist2
    return best


def probe_nodes(nodes: list[tuple[float, float, float]]) -> dict[int, str]:
    yc = 0.5 * WIDTH
    zc = 0.5 * THICKNESS
    targets = {
        "free_tip_center": (LENGTH, yc, zc),
        "midspan_center": (0.5 * LENGTH, yc, zc),
        "root_center": (0.0, yc, zc),
    }
    return {nearest_node(nodes, target): name for name, target in targets.items()}


def write_calculix_inp(case: Case, path: Path) -> dict[str, object]:
    nodes = build_nodes(case)
    ccx_type, elements = build_elements(case)
    fixed_nodes = face_node_ids(nodes, 0.0)
    loaded_nodes = face_node_ids(nodes, LENGTH)
    nodal_force = TOTAL_LOAD / len(loaded_nodes)
    probes = probe_nodes(nodes)

    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"** CalculiX validation input for {case.name}\n")
        handle.write("** Generated from the same structured mesh rules as validation_export.\n")
        handle.write("*NODE, NSET=NALL\n")
        for idx, (x, y, z) in enumerate(nodes, start=1):
            handle.write(f"{idx}, {x:.17g}, {y:.17g}, {z:.17g}\n")
        handle.write(f"*ELEMENT, TYPE={ccx_type}, ELSET=EALL\n")
        for elem_id, element in enumerate(elements, start=1):
            labels = ", ".join(str(node + 1) for node in element)
            handle.write(f"{elem_id}, {labels}\n")
        handle.write("*MATERIAL, NAME=MAT1\n")
        handle.write("*ELASTIC\n")
        handle.write(f"{YOUNG_MODULUS:.17g}, {POISSON_RATIO:.17g}\n")
        handle.write("*SOLID SECTION, ELSET=EALL, MATERIAL=MAT1\n")
        handle.write("*BOUNDARY\n")
        for node in fixed_nodes:
            handle.write(f"{node + 1}, 1, 3, 0.0\n")
        handle.write("*STEP\n")
        handle.write("*STATIC\n")
        handle.write("*CLOAD\n")
        for node in loaded_nodes:
            handle.write(f"{node + 1}, {LOAD_DOF_ZERO_BASED + 1}, {nodal_force:.17g}\n")
        handle.write("*NODE PRINT, NSET=NALL\n")
        handle.write("U\n")
        handle.write("*NODE FILE, NSET=NALL\n")
        handle.write("U\n")
        handle.write("*END STEP\n")

    return {
        "nodes": len(nodes),
        "elements": len(elements),
        "fixed_nodes": len(fixed_nodes),
        "fixed_dofs": len(fixed_nodes) * 3,
        "loaded_nodes": len(loaded_nodes),
        "nodal_force": nodal_force,
        "probe_nodes_zero_based": probes,
        "ccx_element_type": ccx_type,
    }


def parse_float(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def parse_calculix_dat(path: Path) -> dict[int, tuple[float, float, float]]:
    displacements: dict[int, tuple[float, float, float]] = {}
    in_displacement_block = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            lower = line.lower()
            if "displacements" in lower:
                in_displacement_block = True
                continue
            if not in_displacement_block:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                node = int(float(parts[0]))
                ux = parse_float(parts[1])
                uy = parse_float(parts[2])
                uz = parse_float(parts[3])
            except ValueError:
                if displacements:
                    break
                continue
            displacements[node] = (ux, uy, uz)
    if not displacements:
        raise RuntimeError(f"No displacement rows parsed from {path}")
    return displacements


def read_matlab_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        out: dict[int, tuple[float, float, float]] = {}
        for row in reader:
            node = int(float(row["node"]))
            out[node] = (float(row["ux"]), float(row["uy"]), float(row["uz"]))
        return out


def read_probe_names(path: Path) -> dict[int, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {int(float(row["node"])): row["name"] for row in reader}


def norm3(values: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def write_displacement_csv(path: Path, displacements_one_based: dict[int, tuple[float, float, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["node", "node_zero_based", "ux", "uy", "uz"])
        writer.writeheader()
        for node in sorted(displacements_one_based):
            ux, uy, uz = displacements_one_based[node]
            writer.writerow(
                {
                    "node": node,
                    "node_zero_based": node - 1,
                    "ux": f"{ux:.17g}",
                    "uy": f"{uy:.17g}",
                    "uz": f"{uz:.17g}",
                }
            )


def compare_probes(
    matlab_path: Path,
    calculix_displacements_one_based: dict[int, tuple[float, float, float]],
    probes_path: Path,
) -> list[dict[str, str]]:
    matlab = read_matlab_displacements(matlab_path)
    probes = read_probe_names(probes_path)
    rows: list[dict[str, str]] = []
    for node in sorted(probes):
        matlab_value = matlab[node]
        calculix_value = calculix_displacements_one_based[node + 1]
        delta = tuple(matlab_value[i] - calculix_value[i] for i in range(3))
        abs_diff = norm3(delta)
        rel_diff = abs_diff / max(norm3(calculix_value), 1.0e-30)
        rows.append(
            {
                "node": str(node),
                "calculix_node": str(node + 1),
                "probe": probes[node],
                "matlab_ux": f"{matlab_value[0]:.17g}",
                "matlab_uy": f"{matlab_value[1]:.17g}",
                "matlab_uz": f"{matlab_value[2]:.17g}",
                "calculix_ux": f"{calculix_value[0]:.17g}",
                "calculix_uy": f"{calculix_value[1]:.17g}",
                "calculix_uz": f"{calculix_value[2]:.17g}",
                "abs_diff": f"{abs_diff:.17g}",
                "rel_diff": f"{rel_diff:.17g}",
                "status": "reported_no_hard_threshold",
            }
        )
    return rows


def write_compare_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "node",
        "calculix_node",
        "probe",
        "matlab_ux",
        "matlab_uy",
        "matlab_uz",
        "calculix_ux",
        "calculix_uy",
        "calculix_uz",
        "abs_diff",
        "rel_diff",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_compare_md(path: Path, rows: list[dict[str, str]], matlab_path: Path, calculix_path: Path) -> None:
    max_row = max(rows, key=lambda row: float(row["abs_diff"]))
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# MATLAB vs CalculiX Probe Displacement Comparison\n\n")
        handle.write(f"- MATLAB source: `{matlab_path}`\n")
        handle.write(f"- CalculiX source: `{calculix_path}`\n")
        handle.write("- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.\n")
        handle.write(
            "- Max probe difference: "
            f"node `{max_row['node']}` / CalculiX node `{max_row['calculix_node']}`, "
            f"probe `{max_row['probe']}`, abs `{max_row['abs_diff']}`, rel `{max_row['rel_diff']}`.\n"
        )
        handle.write("\n| node | CalculiX node | probe | abs diff | rel diff | status |\n")
        handle.write("| ---: | ---: | --- | ---: | ---: | --- |\n")
        for row in rows:
            handle.write(
                f"| {row['node']} | {row['calculix_node']} | {row['probe']} | "
                f"{row['abs_diff']} | {row['rel_diff']} | {row['status']} |\n"
            )


def run_case(case: Case, root: Path, ccx_bin: str) -> dict[str, object]:
    case_dir = root / case.name
    calc_dir = case_dir / "calculix"
    calc_dir.mkdir(parents=True, exist_ok=True)
    inp_path = calc_dir / f"{case.name}.inp"
    mesh_info = write_calculix_inp(case, inp_path)

    cmd = [ccx_bin, "-i", case.name]
    completed = subprocess.run(cmd, cwd=calc_dir, text=True, capture_output=True)
    (calc_dir / f"{case.name}_ccx_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (calc_dir / f"{case.name}_ccx_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"CalculiX failed for {case.name} with exit code {completed.returncode}; "
            f"see {calc_dir / (case.name + '_ccx_stderr.txt')}"
        )

    dat_path = calc_dir / f"{case.name}.dat"
    displacements = parse_calculix_dat(dat_path)
    displacement_csv = calc_dir / f"{case.name}_calculix_displacements.csv"
    write_displacement_csv(displacement_csv, displacements)

    matlab_path = case_dir / f"{case.name}_matlab_displacements.csv"
    probes_path = case_dir / f"{case.name}_probes.csv"
    compare_rows = compare_probes(matlab_path, displacements, probes_path)
    compare_csv = case_dir / f"{case.name}_calculix_probe_compare.csv"
    compare_md = case_dir / f"{case.name}_calculix_probe_compare.md"
    write_compare_csv(compare_csv, compare_rows)
    write_compare_md(compare_md, compare_rows, matlab_path, displacement_csv)

    max_row = max(compare_rows, key=lambda row: float(row["abs_diff"]))
    return {
        "case": case.name,
        "element_type": case.element_type,
        "nx": case.nx,
        "ny": case.ny,
        "nz": case.nz,
        "mesh": mesh_info,
        "command": " ".join(cmd),
        "returncode": completed.returncode,
        "files": {
            "inp": str(inp_path),
            "dat": str(dat_path),
            "frd": str(calc_dir / f"{case.name}.frd"),
            "calculix_displacements": str(displacement_csv),
            "probe_compare_csv": str(compare_csv),
            "probe_compare_md": str(compare_md),
            "stdout": str(calc_dir / f"{case.name}_ccx_stdout.txt"),
            "stderr": str(calc_dir / f"{case.name}_ccx_stderr.txt"),
        },
        "max_probe_abs_diff": float(max_row["abs_diff"]),
        "max_probe_rel_diff": float(max_row["rel_diff"]),
        "max_probe": max_row["probe"],
        "status": "reported_no_hard_threshold",
    }


def ccx_version(ccx_bin: str) -> str:
    completed = subprocess.run([ccx_bin, "-v"], text=True, capture_output=True)
    return (completed.stdout + completed.stderr).strip()


def write_summary_report(path: Path, manifest: dict[str, object]) -> None:
    cases = manifest["cases"]
    assert isinstance(cases, list)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Linux Intel CalculiX Validation Report\n\n")
        handle.write("## Environment\n\n")
        handle.write(f"- Platform: `{manifest['platform']}`\n")
        handle.write(f"- CalculiX: `{manifest['calculix_version']}`\n")
        handle.write(f"- Material: `E={YOUNG_MODULUS}, nu={POISSON_RATIO}`\n")
        handle.write(f"- Geometry/load: `L={LENGTH}, W={WIDTH}, T={THICKNESS}`, x=0 fixed, x=L total z-load `{TOTAL_LOAD}`.\n")
        handle.write("- Threshold policy: no hard pass/fail threshold; report probe differences.\n\n")
        handle.write("## Commands\n\n")
        handle.write("```bash\n")
        handle.write(str(manifest["driver_command"]) + "\n")
        for case in cases:
            handle.write(f"(cd {Path(case['files']['inp']).parent} && {case['command']})\n")
        handle.write("```\n\n")
        handle.write("## Probe Summary\n\n")
        handle.write("| case | element | nodes | elements | max probe | max abs diff | max rel diff | status |\n")
        handle.write("| --- | --- | ---: | ---: | --- | ---: | ---: | --- |\n")
        for case in cases:
            mesh = case["mesh"]
            handle.write(
                f"| {case['case']} | {case['element_type']} | {mesh['nodes']} | {mesh['elements']} | "
                f"{case['max_probe']} | {case['max_probe_abs_diff']:.6g} | "
                f"{case['max_probe_rel_diff']:.6g} | {case['status']} |\n"
            )
        handle.write("\n## Outputs\n\n")
        for case in cases:
            handle.write(f"- `{case['case']}`: `{case['files']['calculix_displacements']}`, `{case['files']['probe_compare_md']}`\n")


def self_test() -> None:
    expected = {
        "cantilever_hex8_small": (27, 8, 9, 27, {14: "free_tip_center", 13: "midspan_center", 12: "root_center"}),
        "cantilever_tet4_small": (27, 48, 9, 27, {14: "free_tip_center", 13: "midspan_center", 12: "root_center"}),
        "cantilever_hex8_medium": (325, 192, 25, 75, {168: "free_tip_center", 162: "midspan_center", 156: "root_center"}),
        "cantilever_tet4_medium": (325, 1152, 25, 75, {168: "free_tip_center", 162: "midspan_center", 156: "root_center"}),
    }
    for case in CASES:
        nodes = build_nodes(case)
        _ccx_type, elements = build_elements(case)
        loaded_nodes = face_node_ids(nodes, LENGTH)
        fixed_nodes = face_node_ids(nodes, 0.0)
        probes = probe_nodes(nodes)
        assert (len(nodes), len(elements), len(loaded_nodes), 3 * len(fixed_nodes), probes) == expected[case.name]

    order_probe = Path("/tmp/pgsa_calculix_order_probe.inp")
    write_calculix_inp(CASES[0], order_probe)
    order_text = order_probe.read_text(encoding="utf-8")
    assert order_text.index("*STEP") < order_text.index("*CLOAD")

    sample = Path("/tmp/pgsa_calculix_dat_parser_sample.dat")
    sample.write_text(
        """
 displacements (vx,vy,vz) for set NALL and time  0.1000000E+01

      1  1.000000E+00  2.000000E+00  3.000000E+00
      2 -1.000000D-01  0.000000E+00  4.000000E+00
""",
        encoding="utf-8",
    )
    parsed = parse_calculix_dat(sample)
    assert parsed[1] == (1.0, 2.0, 3.0)
    assert parsed[2] == (-0.1, 0.0, 4.0)
    print("self-test passed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--ccx-bin", default="ccx")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0

    root = args.root.resolve()
    manifest: dict[str, object] = {
        "schema_version": "pgsa-calculix-validation-v1",
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "calculix_version": ccx_version(args.ccx_bin),
        "driver_command": f"python3 {Path(__file__).relative_to(Path.cwd())} --root {args.root} --ccx-bin {args.ccx_bin}",
        "cases": [],
    }
    cases = manifest["cases"]
    assert isinstance(cases, list)
    for case in CASES:
        print(f"[calculix] {case.name}")
        cases.append(run_case(case, root, args.ccx_bin))

    manifest_path = root / "calculix_validation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_summary_report(root / "calculix_validation_report.md", manifest)
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
