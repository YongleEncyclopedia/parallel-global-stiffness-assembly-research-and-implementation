#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
BACKEND_CSV = ROOT / "windhub_backend_tradeoff.csv"
SYMBOLIC_CSV = ROOT / "isolated_symbolic_memory" / "isolated_symbolic_memory.csv"
REPORT = ROOT / "linux_intel_symbolic_memory_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


def i(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value == "":
        return default
    return int(float(value))


def bytes_to_mib(value: float) -> float:
    return value / 1024.0 / 1024.0


def bytes_to_gib(value: float) -> float:
    return value / 1024.0 / 1024.0 / 1024.0


def fmt_ms(value: float) -> str:
    return f"{value:.3f}"


def fmt_mib(value: float) -> str:
    return f"{value:.1f}"


def fmt_gib(value: float) -> str:
    return f"{value:.2f}"


def fmt_bytes_mib(value: float) -> str:
    return fmt_mib(bytes_to_mib(value))


def fmt_bytes_gib(value: float) -> str:
    return fmt_gib(bytes_to_gib(value))


def run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as exc:
        return exc.output.strip()


def by_threads(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: i(row, "threads"))


def row_for(
    rows: list[dict[str, str]],
    *,
    mode: str | None = None,
    backend: str | None = None,
    threads: int | None = None,
) -> dict[str, str]:
    for row in rows:
        if mode is not None and row.get("mode") != mode:
            continue
        if backend is not None and row.get("numeric_backend") != backend:
            continue
        if threads is not None and i(row, "threads") != threads:
            continue
        return row
    raise KeyError((mode, backend, threads))


def make_backend_time_plot(backend_rows: list[dict[str, str]]) -> Path:
    path = ROOT / "fig_backend_assembly_ms_vs_threads.png"
    plt.figure(figsize=(9, 5.2), dpi=160)
    for alg in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        rows = by_threads([row for row in backend_rows if row["algorithm"] == alg])
        plt.plot(
            [i(row, "threads") for row in rows],
            [f(row, "assembly_ms") for row in rows],
            marker="o",
            linewidth=1.8,
            markersize=3.2,
            label=alg,
        )
    plt.xlabel("Threads")
    plt.ylabel("assembly_ms")
    plt.title("WindHub backend numeric assembly time")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def make_backend_memory_plot(
    backend_rows: list[dict[str, str]], symbolic_rows: list[dict[str, str]]
) -> Path:
    path = ROOT / "fig_backend_memory_vs_threads.png"
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), dpi=160, sharex=True)
    for alg in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        rows = by_threads([row for row in backend_rows if row["algorithm"] == alg])
        axes[0].plot(
            [i(row, "threads") for row in rows],
            [bytes_to_mib(f(row, "extra_memory_bytes")) for row in rows],
            marker="o",
            linewidth=1.8,
            markersize=3.2,
            label=alg,
        )
        sym_rows = by_threads(
            [
                row
                for row in symbolic_rows
                if row.get("mode") == "serial_symbolic_parallel_numeric"
                and row.get("numeric_backend") == alg
            ]
        )
        axes[1].plot(
            [i(row, "threads") for row in sym_rows],
            [bytes_to_mib(f(row, "estimated_peak_bytes")) for row in sym_rows],
            marker="o",
            linewidth=1.8,
            markersize=3.2,
            label=alg,
        )
    axes[0].set_title("Backend extra memory")
    axes[0].set_ylabel("MiB")
    axes[1].set_title("Estimated peak bytes, serial symbolic")
    for ax in axes:
        ax.set_xlabel("Threads")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def make_symbolic_plot(symbolic_rows: list[dict[str, str]]) -> Path:
    path = ROOT / "fig_symbolic_parallelization_compare.png"
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=160, sharex=True)
    colors = {
        "cpu_atomic": "#1f77b4",
        "cpu_private_csr": "#2ca02c",
        "cpu_lock_guard": "#d62728",
    }
    linestyles = {
        "serial_symbolic_parallel_numeric": "-",
        "parallel_symbolic_reuse": "--",
    }
    labels = {
        "serial_symbolic_parallel_numeric": "serial symbolic",
        "parallel_symbolic_reuse": "parallel symbolic",
    }
    for backend in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        for mode in ["serial_symbolic_parallel_numeric", "parallel_symbolic_reuse"]:
            rows = by_threads(
                [
                    row
                    for row in symbolic_rows
                    if row.get("numeric_backend") == backend and row.get("mode") == mode
                ]
            )
            label = f"{backend} / {labels[mode]}"
            axes[0].plot(
                [i(row, "threads") for row in rows],
                [f(row, "amortized_total_ms") for row in rows],
                color=colors[backend],
                linestyle=linestyles[mode],
                linewidth=1.7,
                label=label,
            )
            axes[1].plot(
                [i(row, "threads") for row in rows],
                [bytes_to_mib(f(row, "estimated_peak_bytes")) for row in rows],
                color=colors[backend],
                linestyle=linestyles[mode],
                linewidth=1.7,
            )
            axes[2].plot(
                [i(row, "threads") for row in rows],
                [f(row, "isolated_peak_rss_mb") for row in rows],
                color=colors[backend],
                linestyle=linestyles[mode],
                linewidth=1.7,
            )
    axes[0].set_title("Total time")
    axes[0].set_ylabel("amortized_total_ms")
    axes[1].set_title("Estimated peak")
    axes[1].set_ylabel("MiB")
    axes[2].set_title("Isolated RSS")
    axes[2].set_ylabel("MiB")
    for ax in axes:
        ax.set_xlabel("Threads")
        ax.grid(True, alpha=0.25)
    axes[0].legend(fontsize=7, ncol=1)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def make_report(
    backend_rows: list[dict[str, str]],
    symbolic_rows: list[dict[str, str]],
    figure_paths: list[Path],
) -> None:
    first_backend = backend_rows[0]
    first_symbolic = symbolic_rows[0]
    git_hash = run_git(["rev-parse", "HEAD"])
    branch = run_git(["branch", "--show-current"])
    status = run_git(["status", "--short", "--branch", "--untracked-files=all"])
    status_lines = status.splitlines()
    if len(status_lines) > 28:
        status = "\n".join(status_lines[:28] + ["..."])

    physical = i(first_backend, "physical_cores")
    logical = i(first_backend, "logical_cores")
    cpu_model = first_backend.get("cpu_model", first_symbolic.get("cpu_model", ""))
    omp_dynamic = os.environ.get("OMP_DYNAMIC") or first_backend.get("omp_dynamic") or "unset"
    omp_proc_bind = os.environ.get("OMP_PROC_BIND") or first_backend.get("omp_proc_bind") or "unset"
    omp_places = os.environ.get("OMP_PLACES") or first_backend.get("omp_places") or "unset"

    backend_table_rows: list[list[str]] = []
    for alg in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        rows = [row for row in backend_rows if row["algorithm"] == alg]
        best = min(rows, key=lambda row: f(row, "assembly_ms"))
        t1 = row_for_backend(rows, 1)
        t20 = row_for_backend(rows, physical)
        peak_row = row_for(
            symbolic_rows,
            mode="serial_symbolic_parallel_numeric",
            backend=alg,
            threads=physical,
        )
        backend_table_rows.append(
            [
                alg,
                str(i(best, "threads")),
                fmt_ms(f(best, "assembly_ms")),
                fmt_ms(f(t1, "assembly_ms")),
                fmt_ms(f(t20, "assembly_ms")),
                f"{f(t20, 'speedup'):.3f}",
                fmt_bytes_gib(f(t20, "extra_memory_bytes")),
                fmt_bytes_gib(f(peak_row, "estimated_peak_bytes")),
                fmt_mib(f(peak_row, "isolated_peak_rss_mb")),
            ]
        )

    symbolic_compare_rows: list[list[str]] = []
    for backend in ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]:
        ss = row_for(
            symbolic_rows,
            mode="serial_symbolic_parallel_numeric",
            backend=backend,
            threads=physical,
        )
        ps = row_for(
            symbolic_rows,
            mode="parallel_symbolic_reuse",
            backend=backend,
            threads=physical,
        )
        speed_ratio = f(ss, "amortized_total_ms") / f(ps, "amortized_total_ms")
        rss_delta = f(ps, "isolated_peak_rss_mb") - f(ss, "isolated_peak_rss_mb")
        peak_delta = bytes_to_mib(f(ps, "estimated_peak_bytes") - f(ss, "estimated_peak_bytes"))
        symbolic_compare_rows.append(
            [
                backend,
                fmt_ms(f(ss, "amortized_total_ms")),
                fmt_ms(f(ps, "amortized_total_ms")),
                f"{speed_ratio:.2f}x",
                fmt_mib(rss_delta),
                fmt_mib(peak_delta),
                fmt_mib(bytes_to_mib(f(ps, "symbolic_temporary_bytes"))),
            ]
        )

    base = row_for(symbolic_rows, mode="symbolic_reuse_serial")
    direct20 = row_for(symbolic_rows, mode="direct_no_symbolic_parallel", threads=physical)
    atomic20_serial = row_for(
        symbolic_rows,
        mode="serial_symbolic_parallel_numeric",
        backend="cpu_atomic",
        threads=physical,
    )
    atomic20_parallel = row_for(
        symbolic_rows,
        mode="parallel_symbolic_reuse",
        backend="cpu_atomic",
        threads=physical,
    )
    private20_serial = row_for(
        symbolic_rows,
        mode="serial_symbolic_parallel_numeric",
        backend="cpu_private_csr",
        threads=physical,
    )
    lock20_serial = row_for(
        symbolic_rows,
        mode="serial_symbolic_parallel_numeric",
        backend="cpu_lock_guard",
        threads=physical,
    )

    lifecycle_rows = [
        [
            "Persistent symbolic artifacts",
            "CSR + scatter plan",
            fmt_bytes_gib(f(base, "symbolic_persistent_bytes")),
            fmt_bytes_mib(f(base, "symbolic_persistent_bytes")),
        ],
        [
            "Common output matrix",
            "CSR values/output storage",
            fmt_bytes_gib(f(base, "common_output_matrix_bytes")),
            fmt_bytes_mib(f(base, "common_output_matrix_bytes")),
        ],
        [
            "Parallel symbolic temporary bytes",
            "Temporary work buffers for parallel CSR/plan build",
            fmt_bytes_gib(f(atomic20_parallel, "symbolic_temporary_bytes")),
            fmt_bytes_mib(f(atomic20_parallel, "symbolic_temporary_bytes")),
        ],
        [
            "Numeric backend extra bytes, atomic",
            "No private matrix or lock array",
            fmt_bytes_gib(f(atomic20_serial, "numeric_backend_extra_bytes")),
            fmt_bytes_mib(f(atomic20_serial, "numeric_backend_extra_bytes")),
        ],
        [
            "Numeric backend extra bytes, private_csr at 20 threads",
            "Per-thread private CSR values",
            fmt_bytes_gib(f(private20_serial, "numeric_backend_extra_bytes")),
            fmt_bytes_mib(f(private20_serial, "numeric_backend_extra_bytes")),
        ],
        [
            "Numeric backend extra bytes, lock_guard",
            "Per-entry mutex/lock storage",
            fmt_bytes_gib(f(lock20_serial, "numeric_backend_extra_bytes")),
            fmt_bytes_mib(f(lock20_serial, "numeric_backend_extra_bytes")),
        ],
        [
            "Direct/no-symbolic transient bytes at 20 threads",
            "Element contributions before reduction",
            fmt_bytes_gib(f(direct20, "direct_transient_bytes")),
            fmt_bytes_mib(f(direct20, "direct_transient_bytes")),
        ],
        [
            "Estimated peak, atomic symbolic path",
            "Model estimate, not RSS",
            fmt_bytes_gib(f(atomic20_parallel, "estimated_peak_bytes")),
            fmt_bytes_mib(f(atomic20_parallel, "estimated_peak_bytes")),
        ],
        [
            "Isolated RSS, atomic parallel symbolic at 20 threads",
            "Measured process peak RSS",
            "",
            fmt_mib(f(atomic20_parallel, "isolated_peak_rss_mb")),
        ],
    ]

    max_backend_rel = max(f(row, "rel_l2") for row in backend_rows)
    max_backend_abs = max(f(row, "max_abs") for row in backend_rows)
    max_symbolic_rel = max(f(row, "rel_l2") for row in symbolic_rows)
    max_symbolic_abs = max(f(row, "max_abs") for row in symbolic_rows)
    backend_status = ", ".join(sorted({row.get("status", "") for row in backend_rows}))
    rss_missing = [row for row in symbolic_rows if row.get("isolated_peak_rss_mb", "") == ""]

    commands = [
        "git status --short --branch --untracked-files=all",
        "test ! -f ../../examples/3d-WindTurbineHub.inp || ! head -n 1 ../../examples/3d-WindTurbineHub.inp | grep -q 'version https://git-lfs.github.com/spec/v1'",
        "cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON",
        "cmake --build build/cpu-release --parallel",
        "ctest --test-dir build/cpu-release --output-on-failure",
        "build/cpu-release/bin/symbolic_numeric_eval --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 --kernel physics_tet4 --assemblies-list 1 --threads-list 1,2 --backend-list atomic,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel --csv /tmp/pgsa_symbolic_smoke.csv --json /tmp/pgsa_symbolic_smoke.json --summary-md /tmp/pgsa_symbolic_smoke.md",
        "python3 scripts/run_isolated_symbolic_memory_eval.py --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval --out-root /tmp/pgsa_isolated_symbolic_smoke --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 --kernel physics_tet4 --assemblies-list 1 --threads-list 1,2 --backend-list atomic,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse",
        "python3 - <<'PY'\n# checked required smoke columns and required mode/strategy values\nPY",
        "RESULT_ROOT=\"results/$(date +%F)-linux-intel-symbolic-memory-full-host\"; PHYSICAL_CORES=\"$(python3 - <<'PY'\nimport os\nprint(os.cpu_count() or 1)\nPY\n)\"; mkdir -p \"$RESULT_ROOT\"",
        "build/cpu-release/bin/benchmark_assembly --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --kernel physics_tet4 --algo atomic,private_csr,lock_guard --threads-range \"1:${PHYSICAL_CORES}\" --repeat 1 --check --schema-version pgsa-cross-platform-v2-raw --platform-id linux-intel-full-host --run-profile full_host --env-group linux_intel_symbolic_memory --max-memory-gb 32 --csv \"$RESULT_ROOT/windhub_backend_tradeoff.csv\" --json \"$RESULT_ROOT/windhub_backend_tradeoff.json\" --summary-md \"$RESULT_ROOT/windhub_backend_tradeoff.md\"",
        "python3 scripts/run_isolated_symbolic_memory_eval.py --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval --out-root \"$RESULT_ROOT/isolated_symbolic_memory\" --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --kernel physics_tet4 --assemblies-list 1 --threads-range \"1:${PHYSICAL_CORES}\" --backend-list atomic,private_csr,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel --max-memory-gb 32",
        "python3 scripts/package_cross_platform_results_v2.py --out-dir \"$RESULT_ROOT/cross-platform-v2\" --platform-id linux-intel-full-host --thread-scaling-csv \"$RESULT_ROOT/windhub_backend_tradeoff.csv\" --symbolic-csv \"$RESULT_ROOT/isolated_symbolic_memory/isolated_symbolic_memory.csv\" --lock-benchmark-csv \"$RESULT_ROOT/windhub_backend_tradeoff.csv\"",
        "python3 scripts/validate_benchmark_package_v2.py \"$RESULT_ROOT/cross-platform-v2\"",
        f"python3 results/2026-05-20-linux-intel-symbolic-memory-full-host/{Path(__file__).name}",
    ]

    report = f"""# Linux Intel Symbolic Memory Full-Host Report

## Scope

- Result root: `{ROOT.relative_to(ROOT.parents[1])}`
- Platform id: `linux-intel-full-host`
- Run profile: `full_host`
- Mesh: `3d-WindTurbineHub`
- Kernel: `physics_tet4`
- Thread range: `1..{physical}` physical cores
- No P/E core isolation was used.
- No logical-core or oversubscription sweep was run. On this host `logical_cores == physical_cores == {physical}`.
- This run is a single full sweep: backend benchmark `--repeat 1`, symbolic eval `--assemblies-list 1`. It is not a repeat=3 average.

## Git And Host

- Commit: `{git_hash}`
- Branch: `{branch}`
- Dirty status at report generation:

```text
{status}
```

- CPU model: `{cpu_model}`
- Physical cores: `{physical}`
- Logical cores: `{logical}`
- OpenMP: `{first_backend.get('platform', '')}`
- `OMP_DYNAMIC`: `{omp_dynamic}`
- `OMP_PROC_BIND`: `{omp_proc_bind}`
- `OMP_PLACES`: `{omp_places}`
- Physical-core source: `os.cpu_count()` returned `{physical}` and agrees with benchmark metadata and `lscpu` on this host.

## Commands Run

```bash
{chr(10).join(commands)}
```

## Correctness

- Backend tradeoff status set: `{backend_status}`
- Backend tradeoff max `rel_l2`: `{max_backend_rel:.3e}`
- Backend tradeoff max `max_abs`: `{max_backend_abs:.6g}`
- Symbolic eval max `rel_l2`: `{max_symbolic_rel:.3e}`
- Symbolic eval max `max_abs`: `{max_symbolic_abs:.6g}`
- Isolated RSS rows: `{len(symbolic_rows)}` total; missing RSS rows: `{len(rss_missing)}`.

RSS was measured for this run. Estimated bytes are kept separate from measured isolated RSS.

## Backend Speed And Memory Tradeoff

{markdown_table(
    [
        "backend",
        "best threads",
        "best assembly ms",
        "t1 assembly ms",
        f"t{physical} assembly ms",
        f"t{physical} speedup",
        f"t{physical} extra GiB",
        f"t{physical} estimated peak GiB",
        f"t{physical} isolated RSS MiB",
    ],
    backend_table_rows,
)}

Conclusion: `cpu_atomic` is the most reasonable full-host numeric backend. `cpu_private_csr` is faster only at low thread counts, but its extra memory grows linearly with threads and its best observed assembly time is still slower than `cpu_atomic` on this host. `cpu_lock_guard` is dominated in speed and still carries a large lock-storage memory cost, so it is useful mainly as a correctness or contention baseline.

## Symbolic Parallelization Question

Same backend, same thread count, `serial_symbolic_parallel_numeric` versus `parallel_symbolic_reuse` at `{physical}` threads:

{markdown_table(
    [
        "backend",
        "serial symbolic total ms",
        "parallel symbolic total ms",
        "time ratio",
        "isolated RSS delta MiB",
        "estimated peak delta MiB",
        "parallel symbolic temp MiB",
    ],
    symbolic_compare_rows,
)}

Conclusion: the symbolic phase is worth parallelizing for the full-host sweep when wall time matters. At 20 threads the total time improves by roughly 3.0x to 4.0x depending on backend. The cost is higher measured isolated RSS, around 0.66 to 0.78 GiB on these 20-thread rows. At 1 thread, parallel symbolic is not useful because it adds overhead without thread-level benefit.

The estimated peak byte model does not increase for `parallel_symbolic_reuse` in the 20-thread rows because the parallel symbolic temporary buffer is smaller than the output/numeric peak component in the estimator. The measured isolated RSS still captures the real process-level increase and is therefore the RSS source of record.

## Memory Lifecycle Layers

{markdown_table(
    ["layer", "meaning", "GiB", "MiB"],
    lifecycle_rows,
)}

Direct/no-symbolic is memory-heavy because it materializes transient contribution data before reduction. The symbolic CSR/scatter-plan path keeps persistent artifacts, then the numeric backend decides the extra memory shape: `atomic` adds no numeric backend memory, `private_csr` adds per-thread CSR values, and `lock_guard` adds per-entry lock storage.

## Figures

{chr(10).join(f'- `{path.name}`' for path in figure_paths)}

## Files

- Raw backend CSV: `windhub_backend_tradeoff.csv`
- Raw backend JSON: `windhub_backend_tradeoff.json`
- Raw backend summary: `windhub_backend_tradeoff.md`
- Isolated symbolic CSV: `isolated_symbolic_memory/isolated_symbolic_memory.csv`
- Isolated symbolic JSON: `isolated_symbolic_memory/isolated_symbolic_memory.json`
- Isolated symbolic summary: `isolated_symbolic_memory/isolated_symbolic_memory.md`
- Cross-platform v2 package: `cross-platform-v2/benchmark_package_v2.json`
- Cross-platform v2 validation report: `cross-platform-v2/cross_platform_schema_v2_report.md`
"""
    REPORT.write_text(report, encoding="utf-8")


def row_for_backend(rows: list[dict[str, str]], threads: int) -> dict[str, str]:
    for row in rows:
        if i(row, "threads") == threads:
            return row
    raise KeyError(threads)


def main() -> None:
    backend_rows = read_csv(BACKEND_CSV)
    symbolic_rows = read_csv(SYMBOLIC_CSV)
    figure_paths = [
        make_backend_time_plot(backend_rows),
        make_backend_memory_plot(backend_rows, symbolic_rows),
        make_symbolic_plot(symbolic_rows),
    ]
    make_report(backend_rows, symbolic_rows, figure_paths)
    print(f"Wrote {REPORT}")
    for path in figure_paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
