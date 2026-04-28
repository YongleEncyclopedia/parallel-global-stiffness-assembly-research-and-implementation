# Repeat=3 redesigned chart data summary

- Run directory: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3`
- Rerun settings: warmup=1, repeat=3, threads=1,2,4,8,14, check enabled, max memory=32 GiB.
- Redesign changes: correctness and memory use heatmaps; efficiency uses grouped bars plus a mean assembly-time table. Scientific notation is avoided in chart labels by scaling rel_l2 to ×10^-16 and max_abs to ×10^-3. All plotted values use two decimals.

## 01. cube_tet4_8x8x8 + simplified

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3/csv/01_cube_tet4_8x8x8_simplified.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.14 | 4 | 0.16 | 0.00 | 1.79 | 0.00 | 0.00–0.00 | 0.01–0.05 |
| Private CSR | 2.36 | 4 | 0.14 | 0.00 | 1.53 | 0.00 | 0.00–0.01 | 0.01–0.06 |
| COO Sort-Reduce | 0.04 | 14 | 7.62 | 0.06 | 1.92 | 0.00 | 0.01–0.01 | 0.02–0.06 |
| Coloring | 0.92 | 1 | 0.36 | 0.00 | 1.84 | 0.00 | 0.00–0.00 | 0.02–0.06 |
| Row Owner | 2.70 | 8 | 0.12 | 0.00 | 0.00 | 0.00 | 0.00–0.00 | 0.02–0.06 |

## 02. cube_tet4_8x8x8 + physics_tet4

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3/csv/02_cube_tet4_8x8x8_physics_tet4.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 3.31 | 14 | 0.32 | 0.03 | 0.75 | 0.03 | 0.00–0.00 | 0.01–0.05 |
| Private CSR | 3.76 | 8 | 0.28 | 0.01 | 1.16 | 0.03 | 0.00–0.01 | 0.01–0.06 |
| COO Sort-Reduce | 0.14 | 14 | 7.82 | 0.03 | 0.91 | 0.03 | 0.01–0.01 | 0.02–0.06 |
| Coloring | 1.08 | 4 | 0.99 | 0.00 | 0.88 | 0.03 | 0.00–0.00 | 0.02–0.06 |
| Row Owner | 2.68 | 14 | 0.40 | 0.01 | 0.00 | 0.00 | 0.00–0.00 | 0.02–0.06 |

## 03. 3d-WindTurbineHub + simplified

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3/csv/03_windhub_simplified.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.63 | 14 | 61.76 | 1.15 | 1.70 | 0.00 | 0.00–0.00 | 2.52–10.95 |
| Private CSR | 2.63 | 8 | 61.58 | 0.43 | 1.31 | 0.00 | 0.20–2.87 | 2.73–10.95 |
| COO Sort-Reduce | 0.04 | 8 | 3802.30 | 3.61 | 1.79 | 0.00 | 2.39–2.39 | 7.51–11.94 |
| Coloring | 1.75 | 14 | 92.38 | 2.88 | 1.39 | 0.00 | 0.01–0.01 | 7.54–11.94 |
| Row Owner | 3.72 | 14 | 43.61 | 0.88 | 0.00 | 0.00 | 1.79–1.79 | 7.54–11.94 |

## 04. 3d-WindTurbineHub + physics_tet4

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3/csv/04_windhub_physics_tet4.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 4.16 | 14 | 103.89 | 5.00 | 1.49 | 6.84 | 0.00–0.00 | 2.52–10.34 |
| Private CSR | 4.11 | 8 | 105.27 | 0.24 | 1.16 | 5.86 | 0.20–2.87 | 2.73–10.58 |
| COO Sort-Reduce | 0.11 | 8 | 4081.43 | 10.39 | 1.61 | 5.86 | 2.39–2.39 | 7.51–10.58 |
| Coloring | 2.95 | 8 | 146.41 | 1.26 | 1.23 | 4.88 | 0.01–0.01 | 7.55–10.58 |
| Row Owner | 3.90 | 14 | 110.96 | 0.73 | 0.00 | 0.00 | 1.79–1.79 | 7.55–10.58 |
