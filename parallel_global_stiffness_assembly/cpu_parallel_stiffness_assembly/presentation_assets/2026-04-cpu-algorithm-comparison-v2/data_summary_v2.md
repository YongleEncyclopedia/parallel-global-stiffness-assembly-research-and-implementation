Data source: /Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/csv/windhub_simplified.csv

| Algorithm | Best speedup | Threads | Worst rel_L2 | Extra memory at best (GB) | Peak RSS at best (GB) |
|---|---:|---:|---:|---:|---:|
| Atomic | 2.529 | 10 | 1.652e-16 | 0.000 | 12.02 |
| Private CSR | 2.861 | 8 | 1.309e-16 | 1.639 | 12.02 |
| COO Sort-Reduce | 0.049 | 12 | 1.785e-16 | 2.390 | 12.86 |
| Graph Coloring | 1.984 | 14 | 1.391e-16 | 0.008 | 13.43 |
| Row Owner | 3.695 | 14 | 0.000e+00 | 1.792 | 13.43 |
