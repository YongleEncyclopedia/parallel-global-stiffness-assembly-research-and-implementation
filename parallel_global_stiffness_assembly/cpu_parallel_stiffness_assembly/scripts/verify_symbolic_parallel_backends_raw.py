#!/usr/bin/env python3
"""Validate raw isolated symbolic/numeric backend sweep data.

The monthly-report chart expects one serial symbolic+numeric baseline and a
complete parallel-symbolic sweep for each numeric backend. This script checks
that contract before the raw CSV is handed to the Mac-side plotting workflow.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_BACKENDS = (
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_lock_guard",
    "cpu_graph_coloring",
    "cpu_row_owner",
)


def parse_threads_range(text: str) -> list[int]:
    if ":" in text:
        start_text, end_text = text.split(":", 1)
        start = int(start_text)
        end = int(end_text)
        if start <= 0 or end < start:
            raise argparse.ArgumentTypeError("threads range must be positive and increasing")
        return list(range(start, end + 1))
    values = [int(part.strip()) for part in text.split(",") if part.strip()]
    if not values or any(v <= 0 for v in values):
        raise argparse.ArgumentTypeError("threads list must contain positive integers")
    return values


def parse_float(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    if value == "":
        raise ValueError(f"missing {field}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} is not finite: {value}")
    return result


def row_label(row: dict[str, str]) -> str:
    return (
        f"mode={row.get('mode', '')}, "
        f"backend={row.get('numeric_backend', '')}, "
        f"threads={row.get('threads', '')}"
    )


def fail(messages: Iterable[str]) -> int:
    print("CSV validation failed:", file=sys.stderr)
    for message in messages:
        print(f"- {message}", file=sys.stderr)
    return 1


def validate(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        return fail([f"CSV does not exist: {csv_path}"])

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return fail([f"CSV has no rows: {csv_path}"])

    expected_threads = parse_threads_range(args.threads_range)
    expected_backends = tuple(
        item.strip() for item in args.required_backends.split(",") if item.strip()
    )

    errors: list[str] = []
    forbidden_rows = [
        row
        for row in rows
        if "direct_no_symbolic" in row.get("mode", "")
        or row.get("numeric_backend") == "cpu_coo_sort_reduce"
    ]
    if forbidden_rows:
        errors.append(
            "forbidden direct/no-symbolic or COO sort-reduce rows found: "
            + "; ".join(row_label(row) for row in forbidden_rows[:5])
        )

    baseline_rows = [
        row
        for row in rows
        if row.get("mode") == "symbolic_reuse_serial"
        and row.get("numeric_backend") == "cpu_serial"
        and row.get("threads") == "1"
    ]
    if not baseline_rows:
        errors.append(
            "missing baseline row: mode=symbolic_reuse_serial, "
            "numeric_backend=cpu_serial, threads=1"
        )

    required_rows: list[dict[str, str]] = []
    if baseline_rows:
        required_rows.append(baseline_rows[0])

    row_index = {
        (row.get("mode"), row.get("numeric_backend"), row.get("threads")): row
        for row in rows
    }
    for backend in expected_backends:
        for threads in expected_threads:
            key = ("parallel_symbolic_reuse", backend, str(threads))
            row = row_index.get(key)
            if row is None:
                errors.append(
                    "missing parallel row: "
                    f"mode=parallel_symbolic_reuse, backend={backend}, threads={threads}"
                )
            else:
                required_rows.append(row)

    max_rel_l2 = 0.0
    min_rel_l2 = math.inf
    for row in required_rows:
        label = row_label(row)
        if row.get("matrix_correctness_status") != "PASS":
            errors.append(f"{label}: matrix_correctness_status is not PASS")
            continue
        try:
            rel_l2 = parse_float(row, "rel_l2")
            isolated_peak_rss_mb = parse_float(row, "isolated_peak_rss_mb")
            symbolic_total_ms = parse_float(row, "symbolic_total_ms")
            numeric_ms = parse_float(row, "numeric_ms")
            amortized_total_ms = parse_float(row, "amortized_total_ms")
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue

        max_rel_l2 = max(max_rel_l2, rel_l2)
        min_rel_l2 = min(min_rel_l2, rel_l2)
        if rel_l2 > args.max_rel_l2:
            errors.append(f"{label}: rel_l2={rel_l2:.3e} exceeds {args.max_rel_l2:.3e}")
        if isolated_peak_rss_mb <= 0:
            errors.append(f"{label}: isolated_peak_rss_mb must be positive")
        if symbolic_total_ms <= 0 or numeric_ms <= 0 or amortized_total_ms <= 0:
            errors.append(f"{label}: timing columns must be positive")
        expected_total = symbolic_total_ms + numeric_ms
        tolerance = max(1e-6, args.total_tolerance * max(1.0, amortized_total_ms))
        if abs(amortized_total_ms - expected_total) > tolerance:
            errors.append(
                f"{label}: amortized_total_ms={amortized_total_ms:.6f} does not match "
                f"symbolic_total_ms + numeric_ms = {expected_total:.6f}"
            )

    if errors:
        return fail(errors)

    baseline_total = parse_float(baseline_rows[0], "amortized_total_ms")
    rel_l2_range = "n/a" if min_rel_l2 is math.inf else f"{min_rel_l2:.3e}..{max_rel_l2:.3e}"
    print("CSV validation passed")
    print(f"- csv: {csv_path}")
    print(f"- baseline amortized_total_ms: {baseline_total:.6f}")
    print(f"- parallel rows checked: {len(expected_backends) * len(expected_threads)}")
    print(f"- backends: {', '.join(expected_backends)}")
    print(f"- threads: {expected_threads[0]}..{expected_threads[-1]}")
    print(f"- rel_l2 range: {rel_l2_range}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="isolated_symbolic_memory.csv path")
    parser.add_argument("--threads-range", default="1:20", help="Thread range, e.g. 1:20")
    parser.add_argument(
        "--required-backends",
        default=",".join(DEFAULT_BACKENDS),
        help="Comma-separated numeric_backend names expected for parallel_symbolic_reuse",
    )
    parser.add_argument("--max-rel-l2", type=float, default=1e-10)
    parser.add_argument("--total-tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    return validate(args)


if __name__ == "__main__":
    raise SystemExit(main())
