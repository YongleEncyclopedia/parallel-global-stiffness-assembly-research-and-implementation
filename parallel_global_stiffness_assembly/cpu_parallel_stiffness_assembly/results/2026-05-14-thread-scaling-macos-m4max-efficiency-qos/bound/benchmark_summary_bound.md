# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 4 线程，`1839.601 ms`
- 最高加速比：`cpu_private_csr` @ 4 线程，`3.065x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 7474.000 | 0.754 | 0.754 | 0 B | PASS |
| cpu_private_csr | 1 | 5352.357 | 1.054 | 1.054 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 6044.054 | 0.933 | 0.933 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 5960.546 | 0.946 | 0.946 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 3390.213 | 1.663 | 0.832 | 0 B | PASS |
| cpu_private_csr | 2 | 2815.884 | 2.002 | 1.001 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 3206.576 | 1.758 | 0.879 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 3257.034 | 1.731 | 0.866 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 2590.991 | 2.176 | 0.725 | 0 B | PASS |
| cpu_private_csr | 3 | 2082.148 | 2.708 | 0.903 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 2455.948 | 2.296 | 0.765 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 2374.802 | 2.374 | 0.791 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 2213.704 | 2.547 | 0.637 | 0 B | PASS |
| cpu_private_csr | 4 | 1839.601 | 3.065 | 0.766 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 2186.021 | 2.579 | 0.645 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 2091.895 | 2.696 | 0.674 | 8.50 MiB | PASS |
