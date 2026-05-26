# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/data_summary_12_charts_v2.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Repeat=3 redesigned chart data summary

- Run directory: `..`
- Rerun settings: warmup=1, repeat=3, threads=1,2,4,8,14, check enabled, max memory=32 GiB.
- Redesign changes: correctness and memory use heatmaps; efficiency uses grouped bars plus a mean assembly-time table. Scientific notation is avoided in chart labels by scaling rel_l2 to ×10^-16 and max_abs to ×10^-3. All plotted values use two decimals.

## 01. cube_tet4_8x8x8 + simplified

- CSV: `../csv/01_cube_tet4_8x8x8_simplified.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 1.65 | 4 | 0.20 | 0.02 | 1.78 | 0.00 | 0.00–0.00 | 0.01–0.10 |
| Private CSR | 1.69 | 6 | 0.19 | 0.01 | 1.55 | 0.00 | 0.00–0.01 | 0.01–0.10 |
| COO Sort-Reduce | 0.04 | 12 | 8.67 | 0.31 | 1.92 | 0.00 | 0.01–0.01 | 0.02–0.10 |
| Coloring | 0.77 | 1 | 0.42 | 0.01 | 1.84 | 0.00 | 0.00–0.00 | 0.02–0.10 |
| Row Owner | 1.92 | 8 | 0.17 | 0.01 | 0.00 | 0.00 | 0.00–0.00 | 0.02–0.10 |

## 02. cube_tet4_8x8x8 + physics_tet4

- CSV: `../csv/02_cube_tet4_8x8x8_physics_tet4.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 5.26 | 10 | 0.25 | 0.01 | 0.84 | 0.03 | 0.00–0.00 | 0.01–0.09 |
| Private CSR | 4.62 | 9 | 0.28 | 0.00 | 1.16 | 0.03 | 0.00–0.01 | 0.01–0.10 |
| COO Sort-Reduce | 0.16 | 11 | 8.11 | 0.07 | 0.91 | 0.03 | 0.01–0.01 | 0.02–0.10 |
| Coloring | 1.18 | 5 | 1.10 | 0.01 | 0.88 | 0.03 | 0.00–0.00 | 0.02–0.10 |
| Row Owner | 4.12 | 10 | 0.32 | 0.00 | 0.00 | 0.00 | 0.00–0.00 | 0.02–0.10 |

## 03. 3d-WindTurbineHub + simplified

- CSV: `../csv/03_windhub_simplified.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.36 | 10 | 83.49 | 2.10 | 1.69 | 0.00 | 0.00–0.00 | 2.52–8.02 |
| Private CSR | 2.88 | 9 | 68.48 | 0.48 | 1.31 | 0.00 | 0.20–2.87 | 2.52–8.02 |
| COO Sort-Reduce | 0.05 | 12 | 4198.96 | 1.31 | 1.79 | 0.00 | 2.39–2.39 | 6.95–8.02 |
| Coloring | 1.79 | 10 | 110.10 | 3.18 | 1.39 | 0.00 | 0.01–0.01 | 6.95–8.02 |
| Row Owner | 3.47 | 9 | 56.72 | 0.42 | 0.00 | 0.00 | 1.79–1.79 | 6.95–8.02 |

## 04. 3d-WindTurbineHub + physics_tet4

- CSV: `../csv/04_windhub_physics_tet4.csv`
| Algorithm | best speedup | threads | assembly_mean_ms | assembly_std_ms | max rel_l2 ×10^-16 | max_abs ×10^-3 | extra memory GiB range | peak RSS GiB range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 4.48 | 12 | 127.35 | 1.93 | 1.49 | 7.81 | 0.00–0.00 | 2.52–8.22 |
| Private CSR | 5.06 | 10 | 112.74 | 0.75 | 1.16 | 5.86 | 0.20–2.87 | 2.73–8.22 |
| COO Sort-Reduce | 0.14 | 13 | 4222.32 | 21.40 | 1.61 | 5.86 | 2.39–2.39 | 7.08–8.22 |
| Coloring | 3.51 | 14 | 162.58 | 2.44 | 1.23 | 4.88 | 0.01–0.01 | 7.08–8.22 |
| Row Owner | 5.35 | 12 | 106.50 | 1.53 | 0.00 | 0.00 | 1.79–1.79 | 7.08–8.22 |
