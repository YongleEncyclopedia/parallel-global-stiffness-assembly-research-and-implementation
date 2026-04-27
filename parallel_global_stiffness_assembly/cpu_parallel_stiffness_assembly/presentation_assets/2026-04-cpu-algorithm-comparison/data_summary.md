# CPU parallel algorithm comparison data summary
Data source: `/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/csv/windhub_simplified.csv`
Case: 3d-WindTurbineHub, kernel: simplified. Five parallel algorithms are compared against cpu_serial.
| Algorithm | Best speedup | Threads | Assembly ms | Total ms | Worst rel_L2 | Worst max_abs | Extra memory at best (GB) | Peak RSS at best (GB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Atomic | 2.529 | 10 | 80.56 | 80.56 | 1.652e-16 | 7.105e-14 | 0.000 | 12.02 |
| Private CSR | 2.861 | 8 | 71.21 | 155.35 | 1.309e-16 | 7.105e-14 | 1.639 | 12.02 |
| COO Sort-Reduce | 0.049 | 12 | 4169.04 | 4169.04 | 1.785e-16 | 7.105e-14 | 2.390 | 12.86 |
| Graph Coloring | 1.984 | 14 | 102.66 | 311.31 | 1.391e-16 | 4.263e-14 | 0.008 | 13.43 |
| Row Owner | 3.695 | 14 | 55.14 | 467.09 | 0.000e+00 | 0.000e+00 | 1.792 | 13.43 |
