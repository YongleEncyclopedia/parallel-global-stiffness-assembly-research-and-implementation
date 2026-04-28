# 12 charts from actual CPU assembly runs

- Run directory: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-run`
- Run command: built `benchmark_assembly`, then executed 4 case/kernel configurations with algorithms `serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner`, threads `1,2,4,8,14`, warmup `0`, repeat `1`, `--check`, max memory `32 GiB`.
- Charts: each configuration has correctness, efficiency, and memory charts. All plotted values are annotated on the figures.

## 01. cube_tet4_8x8x8 + simplified

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-run/csv/01_cube_tet4_8x8x8_simplified.csv`
| Algorithm | best speedup | best speedup threads | assembly ms at best | max rel_l2 | max max_abs | extra memory range GiB | peak RSS range GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.35343 | 4 | 0.21975 | 1.62016e-16 | 2.84217e-14 | 0–0 | 0.009155–0.04831 |
| Private CSR | 2.90543 | 4 | 0.178 | 1.53043e-16 | 2.13163e-14 | 0.00061–0.00854 | 0.009781–0.05687 |
| COO Sort-Reduce | 0.0660561 | 14 | 7.82921 | 1.91871e-16 | 3.55271e-14 | 0.006592–0.006592 | 0.02301–0.05721 |
| Coloring | 0.754897 | 1 | 0.685083 | 1.83937e-16 | 2.84217e-14 | 2.289e-05–2.289e-05 | 0.02332–0.05725 |
| Row Owner | 3.24666 | 14 | 0.159292 | 0 | 0 | 0.004944–0.004944 | 0.02332–0.05727 |

## 02. cube_tet4_8x8x8 + physics_tet4

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-run/csv/02_cube_tet4_8x8x8_physics_tet4.csv`
| Algorithm | best speedup | best speedup threads | assembly ms at best | max rel_l2 | max max_abs | extra memory range GiB | peak RSS range GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.82016 | 14 | 0.378583 | 7.46897e-17 | 1.52588e-05 | 0–0 | 0.009155–0.047 |
| Private CSR | 2.93583 | 4 | 0.363667 | 1.15581e-16 | 3.05176e-05 | 0.00061–0.00854 | 0.009781–0.05556 |
| COO Sort-Reduce | 0.13613 | 14 | 7.843 | 9.08896e-17 | 3.05176e-05 | 0.006592–0.006592 | 0.02299–0.05647 |
| Coloring | 1.07177 | 4 | 0.996167 | 8.81878e-17 | 3.05176e-05 | 2.289e-05–2.289e-05 | 0.02328–0.05652 |
| Row Owner | 2.90324 | 8 | 0.36775 | 0 | 0 | 0.004944–0.004944 | 0.02328–0.05656 |

## 03. 3d-WindTurbineHub + simplified

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-run/csv/03_windhub_simplified.csv`
| Algorithm | best speedup | best speedup threads | assembly ms at best | max rel_l2 | max max_abs | extra memory range GiB | peak RSS range GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.92259 | 14 | 64.3275 | 1.69917e-16 | 8.52651e-14 | 0–0 | 2.521–10.84 |
| Private CSR | 3.05232 | 8 | 61.5935 | 1.30882e-16 | 5.68434e-14 | 0.2049–2.869 | 2.726–11.96 |
| COO Sort-Reduce | 0.048416 | 8 | 3883.08 | 1.78538e-16 | 7.10543e-14 | 2.39–2.39 | 6.805–11.96 |
| Coloring | 1.8356 | 8 | 102.42 | 1.39058e-16 | 4.26326e-14 | 0.008298–0.008298 | 6.918–11.96 |
| Row Owner | 4.13167 | 14 | 45.503 | 0 | 0 | 1.792–1.792 | 6.968–11.96 |

## 04. 3d-WindTurbineHub + physics_tet4

- CSV: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-run/csv/04_windhub_physics_tet4.csv`
| Algorithm | best speedup | best speedup threads | assembly ms at best | max rel_l2 | max max_abs | extra memory range GiB | peak RSS range GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 4.44517 | 14 | 97.1715 | 1.50978e-16 | 0.00683594 | 0–0 | 2.522–11.15 |
| Private CSR | 4.24399 | 8 | 101.778 | 1.1563e-16 | 0.00585938 | 0.2049–2.869 | 2.727–11.86 |
| COO Sort-Reduce | 0.110522 | 8 | 3908.2 | 1.61485e-16 | 0.00585938 | 2.39–2.39 | 7.507–11.86 |
| Coloring | 3.02581 | 14 | 142.753 | 1.22801e-16 | 0.00488281 | 0.008298–0.008298 | 7.544–11.86 |
| Row Owner | 4.29327 | 14 | 100.609 | 0 | 0 | 1.792–1.792 | 7.544–11.86 |
