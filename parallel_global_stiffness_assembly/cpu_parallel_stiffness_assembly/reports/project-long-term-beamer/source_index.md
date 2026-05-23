# Source Index for Project Long-Term Beamer

This file records the sources used by `project_long_term_beamer.tex`.

The deck is a living internal handbook. Local repository facts and benchmark results take priority over external references. External references are used only to anchor general concepts.

## Local Project Documents

| Source | Used for |
| --- | --- |
| `README.md` | Repository-level project positioning and CPU-first scope. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md` | CPU mainline entry, implemented algorithms, build/test commands, benchmark fields. |
| `docs/requirements/cpu-parallel-stiffness-assembly-design.md` | Research goals, scope boundaries, architecture requirements, and benchmark requirements. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md` | Algorithm explanations for serial, atomic, lock_guard, private CSR, COO sort-reduce, graph coloring, and row-owner. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md` | Symbolic/numeric assembly terminology and mentor-example mapping. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/memory_lifecycle.md` | Persistent/transient memory lifecycle definitions for symbolic artifacts, direct buffers, private CSR, and lock_guard. |
| `docs/platform/cross-platform-benchmark-schema.md` | Cross-platform benchmark package fields and platform/profile distinction. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-14-mentor-next-steps-beamer/mentor_next_steps_beamer.tex` | Stable mentor-discussion concepts and existing short-term Beamer narrative. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/weekly_meeting_20260522_beamer.tex` | Weekly-meeting entry for parallel symbolic, correctness reference, and memory lifecycle evidence. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/asset_manifest.md` | Figure provenance for the 2026-05-22 weekly meeting deck. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/mentor_qna_rehearsal.md` | Mentor-facing self Q&A rehearsal for likely weekly-meeting follow-up questions. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/numeric_assembly_algorithm_rehearsal.md` | Plain-language rehearsal notes for how numeric assembly reuses CSR/scatter across the five main CPU backends. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/apps/pattern_export/main.cpp` | Sparse pattern and CSR window export for assembled stiffness matrices. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/plot_stiffness_pattern_matlab.m` | MATLAB sparse-pattern visualization convention. |

## Local Result Reports

| Source | Used for |
| --- | --- |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-symbolic-numeric/symbolic_numeric_eval_report.md` | Symbolic reuse vs direct no-symbolic table, control experiment table, WindHub size, Apple M4 Max platform boundary. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-12-thread-scaling-linux-intel-hybrid-core-supplement.md` | Intel `taskset` P/E-core profile interpretation. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-14-thread-scaling-macos-m4max-qos-supplement.md` | Apple QoS-biased P/E profile interpretation and non-hard-pinned boundary. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/cross_platform_schema_report.md` | Cross-platform schema report and core-profile comparison context. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.md` | Parallel symbolic vs direct/no-symbolic full physical-core sweep. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/windhub_lock_vs_atomic.md` | Atomic vs per-entry `std::lock_guard<std::mutex>` WindHub comparison. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/cross-platform-v2/cross_platform_schema_v2_report.md` | v2 family-grouped mentor action-item package report. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/linux_intel_symbolic_memory_report.md` | Linux Intel full-host symbolic parallelization, isolated RSS, backend memory, and 2.39 GiB direct transient memory summary. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv` | Source data for serial symbolic vs parallel symbolic total time, temporary bytes, and isolated RSS. |

## Direct Figure References

The long-term deck intentionally references these result figures directly rather than copying them into local `assets/`.

| Figure path | Slide purpose |
| --- | --- |
| `../../results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_correctness_heatmap_04_windhub_physics_tet4.png` | WindHub `physics_tet4` correctness evidence. |
| `../../results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_efficiency_grouped_bars_04_windhub_physics_tet4.png` | WindHub `physics_tet4` efficiency evidence. |
| `../../results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_memory_heatmap_04_windhub_physics_tet4.png` | WindHub `physics_tet4` memory evidence. |
| `../../results/2026-05-11-thread-scaling-linux-intel/figures/thread_scaling_bound_dashboard.png` | Intel full-host thread scaling. |
| `../../results/cross-platform-v1/figures/core_profile_speedup_comparison_intel_u7_265kf.png` | Intel `taskset` affinity-restricted core-profile comparison. |
| `../../results/cross-platform-v1/figures/core_profile_speedup_comparison_apple_m4_max.png` | Apple QoS-biased core-profile comparison. |
| `../../results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_python.png` | WindHub serial/parallel sparse pattern evidence generated from exported row,col pattern. |
| `../../results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_matlab.png` | MATLAB-generated sparse pattern cross-check. |
| `../2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_spy_original_raster.png` | Original `.inp` node-order sparse pattern for explaining block-like clustering. |
| `../2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_spy_rcm_raster.png` | RCM `K(p,p)` sparse pattern for explaining mentor-style banded visualization. |
| `../2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_exact_window_serial.png` | Exact uncompressed local sparse window with true row/column coordinates. |
| `../2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_exact_window_auto_serial.png` | Auto-selected exact local sparse window with higher in-window nonzero density. |

## External References

| Reference | URL | Used for |
| --- | --- | --- |
| PETSc DMPlex manual | <https://petsc.org/main/manual/dmplex/> | Explaining `DMPlex`, mesh topology, closure-style data access, and mesh-data layout concepts. |
| PETSc `DMPlexCreateSection` manual page | <https://petsc.org/main/manualpages/DMPlex/DMPlexCreateSection/> | Explaining `PetscSection` as a DOF layout specification. |
| PETSc `DMPLEX` manual page | <https://petsc.org/main/manualpages/DMPlex/DMPLEX/> | Explaining DMPlex as an unstructured mesh object and the role of `PetscSection`. |
| Parallel assembly of finite element matrices on multicore computers | <https://www.sciencedirect.com/science/article/pii/S0045782524003323> | Background for shared-memory FEM sparse matrix assembly and element coloring. |
| A flexible sparse matrix data format and parallel algorithms for assembly using atomic synchronisation primitives | <https://arxiv.org/abs/2012.00585> | Background for sparse matrix assembly and atomic synchronization primitives. |

## Update Rule

When adding a slide:

1. Prefer local project docs/results as the factual source.
2. Add the local source path here.
3. If a figure is referenced directly, add the relative path here.
4. If an external source is used, add the URL and state the exact concept it supports.
5. Do not use external literature to override local benchmark facts.
