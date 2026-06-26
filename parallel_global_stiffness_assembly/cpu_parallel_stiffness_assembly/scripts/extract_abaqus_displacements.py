#!/usr/bin/env python3
"""Extract Abaqus ODB probe displacements to CSV."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from odbAccess import openOdb


def pick(row: dict[str, str], *names: str) -> str:
    normalized = {"".join(ch for ch in key.lower() if ch.isalnum()): key for key in row}
    for name in names:
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        if key in normalized:
            return row[normalized[key]]
    raise KeyError(f"missing any of columns {names}")


def read_probes(path: Path, index_base: int) -> list[dict[str, object]]:
    probes: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cpp_node = int(float(pick(row, "node", "cpp_node")))
            abaqus_node = cpp_node + 1 if index_base == 0 else cpp_node
            probes.append(
                {
                    "probe": pick(row, "name", "probe"),
                    "cpp_node": cpp_node,
                    "node_label": abaqus_node,
                    "x": float(pick(row, "x")),
                    "y": float(pick(row, "y")),
                    "z": float(pick(row, "z")),
                }
            )
    return probes


def extract_displacements(odb_path: Path, step_name: str | None) -> dict[int, tuple[float, float, float]]:
    odb = openOdb(path=str(odb_path), readOnly=True)
    try:
        if step_name:
            step = odb.steps[step_name]
        else:
            step = odb.steps[list(odb.steps.keys())[-1]]
        frame = step.frames[-1]
        field = frame.fieldOutputs["U"]
        out: dict[int, tuple[float, float, float]] = {}
        for value in field.values:
            out[int(value.nodeLabel)] = (float(value.data[0]), float(value.data[1]), float(value.data[2]))
        return out
    finally:
        odb.close()


def write_outputs(
    probes: list[dict[str, object]],
    displacements: dict[int, tuple[float, float, float]],
    out_path: Path,
    mapping_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["probe", "cpp_node", "node_label", "x", "y", "z", "ux", "uy", "uz", "source"],
        )
        writer.writeheader()
        for probe in probes:
            node_label = int(probe["node_label"])
            if node_label not in displacements:
                raise KeyError(f"node label {node_label} was not found in ODB displacement output")
            ux, uy, uz = displacements[node_label]
            writer.writerow(
                {
                    "probe": probe["probe"],
                    "cpp_node": probe["cpp_node"],
                    "node_label": node_label,
                    "x": f"{float(probe['x']):.17g}",
                    "y": f"{float(probe['y']):.17g}",
                    "z": f"{float(probe['z']):.17g}",
                    "ux": f"{ux:.17g}",
                    "uy": f"{uy:.17g}",
                    "uz": f"{uz:.17g}",
                    "source": "abaqus_odb",
                }
            )

    with mapping_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["probe", "cpp_node", "abaqus_node", "x", "y", "z", "mapping_rule"],
        )
        writer.writeheader()
        for probe in probes:
            writer.writerow(
                {
                    "probe": probe["probe"],
                    "cpp_node": probe["cpp_node"],
                    "abaqus_node": probe["node_label"],
                    "x": f"{float(probe['x']):.17g}",
                    "y": f"{float(probe['y']):.17g}",
                    "z": f"{float(probe['z']):.17g}",
                    "mapping_rule": "abaqus_node = cpp_node + 1",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odb", required=True, type=Path)
    parser.add_argument("--probes", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mapping-out", type=Path)
    parser.add_argument("--step", default="")
    parser.add_argument("--index-base", type=int, choices=(0, 1), default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping_path = args.mapping_out or args.out.with_name(args.out.stem + "_node_mapping.csv")
    probes = read_probes(args.probes, args.index_base)
    displacements = extract_displacements(args.odb, args.step or None)
    write_outputs(probes, displacements, args.out, mapping_path)
    print(f"wrote {args.out}")
    print(f"wrote {mapping_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
