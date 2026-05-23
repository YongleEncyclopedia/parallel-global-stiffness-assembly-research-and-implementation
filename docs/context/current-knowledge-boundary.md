# Current Knowledge Boundary

This file is the first stop for future agents and maintainers who need to understand what is current, what is historical, and which sources win when project materials disagree.

## Current Scope

The current project is a CPU-first research and implementation workspace for parallel assembly of global stiffness matrices on shared-memory multicore CPUs.

Current in-scope work:

- Shared-memory CPU assembly algorithms for global stiffness matrices.
- The canonical implementation under `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`.
- `Tet4` and `Hex8` regular-grid tests, plus Abaqus `.inp` inputs for `C3D4` and `C3D8`.
- `simplified` and `physics_tet4` element kernels.
- Symbolic/numeric assembly separation, CSR/scatter-plan reuse, and direct/no-symbolic comparison.
- Benchmark packaging, platform/profile metadata, figures, reports, and Beamer summaries.
- Cross-platform interpretation for Linux Intel and macOS Apple Silicon, with Intel treated as the primary user-facing platform where comparable data exists.

Out-of-scope for the current mainline:

- New GPU algorithm development.
- MPI or distributed-memory assembly.
- Full commercial-solver feature coverage.
- Solver-stage optimization after global matrix assembly.
- High-order elements, nonlinear material models, contact, and general PETSc-style section/closure abstractions beyond explanatory references.

## Source Priority

When sources disagree, use this order:

1. Current structured result data and reports in `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/`, especially 2026-05-16, 2026-05-20, and cross-platform v1/v2 reports.
2. Current CPU mainline code, CLI behavior, and CPU documentation under `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/`.
3. Current requirements and boundary documents: `docs/requirements/cpu-parallel-stiffness-assembly-design.md`, `docs/context/repository-scope.md`, and this file.
4. Date-stamped handoff, mentor, and weekly reports, only for the state they record at that date.
5. Monthly report extracts, Beamer speaker notes, and historical decks, only for narrative/provenance context.
6. External references, only for general concepts; they do not override local benchmark facts.

## Current Facts

- The CPU mainline has seven registered CPU assembly algorithms: `serial`, `atomic`, `lock_guard`, `private_csr`, `coo_sort_reduce`, `coloring`, and `row_owner`.
- `serial` remains the correctness and speedup baseline.
- `lock_guard` is a per-entry `std::lock_guard<std::mutex>` baseline. It is useful as a synchronization comparison, not as the preferred route.
- `3d-WindTurbineHub.inp` is the core real engineering mesh and should be accessed through the repository Git LFS path.
- `physics_tet4` is the current physical Tet4 kernel for report-facing benchmark interpretation; `simplified` remains useful for smoke tests and controlled algorithm comparisons.
- Memory numbers must be separated by lifecycle: persistent CSR/AssemblyPlan, transient symbolic/direct buffers, backend extra memory, and OS-observed peak RSS.
- Intel `taskset` P/E-core profiles and Apple QoS-biased profiles are not equivalent mechanisms and should not be compared as identical hardware controls.

## Material Classes

| Class | Examples | Use rule |
| --- | --- | --- |
| Current source of truth | CPU mainline README, `docs/cpu/*`, latest structured result reports | Use for current implementation and benchmark claims. |
| Requirements and boundary | `docs/requirements/*`, `docs/context/*` | Use for scope, exclusions, and interpretation priority. |
| Result evidence | `results/2026-05-16-*`, `results/2026-05-20-*`, `results/cross-platform-v1`, cross-platform v2 packages | Use for numerical claims, platform interpretation, and report figures. |
| Early result/provenance | `results/2026-04-22`, `results/2026-04-28-*` | Use as historical and presentation-chart sources; do not treat as latest conclusion. |
| Date-stamped reports | `reports/2026-05-14-*`, `reports/2026-05-22-*` | Use as snapshots of what was said at that meeting date. |
| Long-term handbook | `reports/project-long-term-beamer` | Use as a learning/manual layer that must cite its sources. |
| Monthly report extracts | `docs/context/monthly-intern-reports/*` | Use for narrative origin and deck provenance, not current benchmark truth. |
| Legacy GPU assets | `docs/context/legacy-gpu-assets.md`, `legacy_gpu/`, CUDA backend dirs | Use only for historical continuity unless explicitly re-scoped. |
| Cleanup candidates | Files ending in ` 2.*`, stale duplicate reports/figures/scripts/tests | Do not use for current claims unless manually promoted. |

## Legacy And Cleanup Rules

- Do not delete historical material just because it is old; first decide whether it has provenance value.
- Prefer `Archive` for legacy explanatory assets and `Delete candidate` for duplicate copies, generated accidental files, or unreferenced `* 2.*` artifacts.
- Do not make raw PPTX decks part of the repository source of truth. Keep lightweight, AI-readable extracts when they support current narrative or provenance.
- Do not use Beamer text or speaker notes as benchmark truth when CSV/JSON/result reports disagree.
- Before deleting any candidate file, list the exact paths, the likely impact, and the rollback method for user confirmation.

## Active Audit

The current cleanup and synchronization audit is tracked in:

- `docs/context/knowledge-boundary-audit.md`

Use that audit table to decide which references should be kept, updated, archived, or deleted.
