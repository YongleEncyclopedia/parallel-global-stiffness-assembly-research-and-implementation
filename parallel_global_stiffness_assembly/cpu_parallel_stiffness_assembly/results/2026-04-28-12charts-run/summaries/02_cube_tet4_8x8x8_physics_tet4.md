# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 4 线程，`0.364 ms`
- 最高加速比：`cpu_private_csr` @ 4 线程，`2.936x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 1.068 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 1.268 | 0.842 | 0.842 | 0 B | PASS |
| cpu_private_csr | 1 | 1.083 | 0.986 | 0.986 | 639.63 KiB | PASS |
| cpu_coo_sort_reduce | 1 | 9.336 | 0.114 | 0.114 | 6.75 MiB | PASS |
| cpu_graph_coloring | 1 | 1.201 | 0.889 | 0.889 | 24.00 KiB | PASS |
| cpu_row_owner | 1 | 1.177 | 0.907 | 0.907 | 5.06 MiB | PASS |
| cpu_atomic | 2 | 0.712 | 1.499 | 0.749 | 0 B | PASS |
| cpu_private_csr | 2 | 0.590 | 1.809 | 0.904 | 1.25 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 8.543 | 0.125 | 0.062 | 6.75 MiB | PASS |
| cpu_graph_coloring | 2 | 1.113 | 0.959 | 0.479 | 24.00 KiB | PASS |
| cpu_row_owner | 2 | 0.682 | 1.566 | 0.783 | 5.06 MiB | PASS |
| cpu_atomic | 4 | 0.412 | 2.592 | 0.648 | 0 B | PASS |
| cpu_private_csr | 4 | 0.364 | 2.936 | 0.734 | 2.50 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 8.028 | 0.133 | 0.033 | 6.75 MiB | PASS |
| cpu_graph_coloring | 4 | 0.996 | 1.072 | 0.268 | 24.00 KiB | PASS |
| cpu_row_owner | 4 | 0.534 | 2.000 | 0.500 | 5.06 MiB | PASS |
| cpu_atomic | 8 | 0.530 | 2.013 | 0.252 | 0 B | PASS |
| cpu_private_csr | 8 | 0.439 | 2.430 | 0.304 | 5.00 MiB | PASS |
| cpu_coo_sort_reduce | 8 | 7.992 | 0.134 | 0.017 | 6.75 MiB | PASS |
| cpu_graph_coloring | 8 | 2.002 | 0.533 | 0.067 | 24.00 KiB | PASS |
| cpu_row_owner | 8 | 0.368 | 2.903 | 0.363 | 5.06 MiB | PASS |
| cpu_atomic | 14 | 0.379 | 2.820 | 0.201 | 0 B | PASS |
| cpu_private_csr | 14 | 0.404 | 2.643 | 0.189 | 8.74 MiB | PASS |
| cpu_coo_sort_reduce | 14 | 7.843 | 0.136 | 0.010 | 6.75 MiB | PASS |
| cpu_graph_coloring | 14 | 3.019 | 0.354 | 0.025 | 24.00 KiB | PASS |
| cpu_row_owner | 14 | 0.430 | 2.482 | 0.177 | 5.06 MiB | PASS |
