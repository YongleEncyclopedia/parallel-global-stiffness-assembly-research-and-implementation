#!/usr/bin/env python3
"""Compare MATLAB displacement results with optional Abaqus probe/reference CSV."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable


def normalize(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def pick_column(fieldnames: Iterable[str], candidates: set[str]) -> str:
    by_norm = {normalize(name): name for name in fieldnames}
    for candidate in candidates:
        if candidate in by_norm:
            return by_norm[candidate]
    raise ValueError(f"missing any of columns {sorted(candidates)} in {list(fieldnames)}")


def read_displacements(path: Path) -> dict[int, tuple[float, float, float]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"empty CSV: {path}")
        node_col = pick_column(reader.fieldnames, {"node", "nodelabel", "label"})
        ux_col = pick_column(reader.fieldnames, {"ux", "u1"})
        uy_col = pick_column(reader.fieldnames, {"uy", "u2"})
        uz_col = pick_column(reader.fieldnames, {"uz", "u3"})
        out: dict[int, tuple[float, float, float]] = {}
        for row in reader:
            node = int(float(row[node_col]))
            out[node] = (float(row[ux_col]), float(row[uy_col]), float(row[uz_col]))
        return out


def read_probes(path: Path | None) -> dict[int, str]:
    if path is None:
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"empty probes CSV: {path}")
        name_col = pick_column(reader.fieldnames, {"name"})
        node_col = pick_column(reader.fieldnames, {"node", "nodelabel", "label"})
        return {int(float(row[node_col])): row[name_col] for row in reader}


def shifted_nodes(
    matlab: dict[int, tuple[float, float, float]],
    abaqus: dict[int, tuple[float, float, float]],
    mode: str,
) -> dict[int, tuple[float, float, float]]:
    if mode == "0":
        return abaqus
    if mode == "1":
        return {node - 1: value for node, value in abaqus.items()}
    if set(matlab).intersection(abaqus):
        return abaqus
    shifted = {node - 1: value for node, value in abaqus.items()}
    if set(matlab).intersection(shifted):
        return shifted
    return abaqus


def norm3(v: tuple[float, float, float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def compare_rows(
    matlab: dict[int, tuple[float, float, float]],
    abaqus: dict[int, tuple[float, float, float]] | None,
    probes: dict[int, str],
) -> list[dict[str, str]]:
    nodes = sorted(probes) if probes else sorted(matlab)
    rows: list[dict[str, str]] = []
    for node in nodes:
        if node not in matlab:
            rows.append({"node": str(node), "probe": probes.get(node, ""), "status": "missing_matlab"})
            continue
        m = matlab[node]
        row = {
            "node": str(node),
            "probe": probes.get(node, ""),
            "matlab_ux": f"{m[0]:.17g}",
            "matlab_uy": f"{m[1]:.17g}",
            "matlab_uz": f"{m[2]:.17g}",
        }
        if abaqus is None:
            row.update(
                {
                    "abaqus_ux": "",
                    "abaqus_uy": "",
                    "abaqus_uz": "",
                    "abs_diff": "",
                    "rel_diff": "",
                    "status": "missing_abaqus_reference",
                }
            )
        elif node not in abaqus:
            row.update(
                {
                    "abaqus_ux": "",
                    "abaqus_uy": "",
                    "abaqus_uz": "",
                    "abs_diff": "",
                    "rel_diff": "",
                    "status": "missing_abaqus_node",
                }
            )
        else:
            a = abaqus[node]
            delta = (m[0] - a[0], m[1] - a[1], m[2] - a[2])
            abs_diff = norm3(delta)
            rel_diff = abs_diff / max(norm3(a), 1.0e-30)
            row.update(
                {
                    "abaqus_ux": f"{a[0]:.17g}",
                    "abaqus_uy": f"{a[1]:.17g}",
                    "abaqus_uz": f"{a[2]:.17g}",
                    "abs_diff": f"{abs_diff:.17g}",
                    "rel_diff": f"{rel_diff:.17g}",
                    "status": "reported_no_hard_threshold",
                }
            )
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "node",
        "probe",
        "matlab_ux",
        "matlab_uy",
        "matlab_uz",
        "abaqus_ux",
        "abaqus_uy",
        "abaqus_uz",
        "abs_diff",
        "rel_diff",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(path: Path, rows: list[dict[str, str]], matlab: Path, abaqus: Path | None) -> None:
    comparable = [r for r in rows if r.get("status") == "reported_no_hard_threshold"]
    max_row = None
    if comparable:
        max_row = max(comparable, key=lambda row: float(row["abs_diff"]))

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Validation Displacement Comparison\n\n")
        handle.write(f"- MATLAB source: `{matlab}`\n")
        handle.write(f"- Abaqus source: `{abaqus}`\n" if abaqus else "- Abaqus source: `not provided`\n")
        handle.write("- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.\n")
        if max_row:
            handle.write(
                "- Max difference: "
                f"node `{max_row['node']}`"
                f", probe `{max_row.get('probe', '')}`"
                f", abs `{max_row['abs_diff']}`"
                f", rel `{max_row['rel_diff']}`.\n"
            )
        handle.write("\n| node | probe | abs diff | rel diff | status |\n")
        handle.write("| ---: | --- | ---: | ---: | --- |\n")
        for row in rows:
            handle.write(
                f"| {row.get('node', '')} | {row.get('probe', '')} | "
                f"{row.get('abs_diff', '')} | {row.get('rel_diff', '')} | {row.get('status', '')} |\n"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matlab", required=True, type=Path, help="MATLAB displacement CSV")
    parser.add_argument("--abaqus", type=Path, help="Optional Abaqus displacement CSV")
    parser.add_argument("--probes", type=Path, help="Optional validation_export probes CSV")
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    parser.add_argument(
        "--abaqus-index-base",
        choices=("auto", "0", "1"),
        default="auto",
        help="Abaqus node numbering convention; auto shifts 1-based labels when needed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matlab = read_displacements(args.matlab)
    probes = read_probes(args.probes)
    abaqus = None
    if args.abaqus:
        abaqus_raw = read_displacements(args.abaqus)
        abaqus = shifted_nodes(matlab, abaqus_raw, args.abaqus_index_base)

    rows = compare_rows(matlab, abaqus, probes)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_csv, rows)
    write_markdown(args.out_md, rows, args.matlab, args.abaqus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
