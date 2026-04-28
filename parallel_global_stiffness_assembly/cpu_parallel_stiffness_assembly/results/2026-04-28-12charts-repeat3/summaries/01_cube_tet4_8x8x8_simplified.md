# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 8 线程，`0.124 ms`
- 最高加速比：`cpu_row_owner` @ 8 线程，`2.697x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 0.334 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 0.514 | 0.650 | 0.650 | 0 B | PASS |
| cpu_private_csr | 1 | 0.342 | 0.975 | 0.975 | 639.63 KiB | PASS |
| cpu_coo_sort_reduce | 1 | 8.026 | 0.042 | 0.042 | 6.75 MiB | PASS |
| cpu_graph_coloring | 1 | 0.364 | 0.916 | 0.916 | 24.00 KiB | PASS |
| cpu_row_owner | 1 | 0.419 | 0.796 | 0.796 | 5.06 MiB | PASS |
| cpu_atomic | 2 | 0.259 | 1.288 | 0.644 | 0 B | PASS |
| cpu_private_csr | 2 | 0.185 | 1.800 | 0.900 | 1.25 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 7.811 | 0.043 | 0.021 | 6.75 MiB | PASS |
| cpu_graph_coloring | 2 | 0.601 | 0.555 | 0.278 | 24.00 KiB | PASS |
| cpu_row_owner | 2 | 0.235 | 1.422 | 0.711 | 5.06 MiB | PASS |
| cpu_atomic | 4 | 0.156 | 2.138 | 0.535 | 0 B | PASS |
| cpu_private_csr | 4 | 0.142 | 2.358 | 0.590 | 2.50 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 7.704 | 0.043 | 0.011 | 6.75 MiB | PASS |
| cpu_graph_coloring | 4 | 0.723 | 0.462 | 0.115 | 24.00 KiB | PASS |
| cpu_row_owner | 4 | 0.176 | 1.900 | 0.475 | 5.06 MiB | PASS |
| cpu_atomic | 8 | 0.218 | 1.533 | 0.192 | 0 B | PASS |
| cpu_private_csr | 8 | 0.212 | 1.573 | 0.197 | 5.00 MiB | PASS |
| cpu_coo_sort_reduce | 8 | 7.696 | 0.043 | 0.005 | 6.75 MiB | PASS |
| cpu_graph_coloring | 8 | 1.583 | 0.211 | 0.026 | 24.00 KiB | PASS |
| cpu_row_owner | 8 | 0.124 | 2.697 | 0.337 | 5.06 MiB | PASS |
| cpu_atomic | 14 | 0.179 | 1.862 | 0.133 | 0 B | PASS |
| cpu_private_csr | 14 | 0.270 | 1.238 | 0.088 | 8.74 MiB | PASS |
| cpu_coo_sort_reduce | 14 | 7.625 | 0.044 | 0.003 | 6.75 MiB | PASS |
| cpu_graph_coloring | 14 | 2.785 | 0.120 | 0.009 | 24.00 KiB | PASS |
| cpu_row_owner | 14 | 0.133 | 2.516 | 0.180 | 5.06 MiB | PASS |
