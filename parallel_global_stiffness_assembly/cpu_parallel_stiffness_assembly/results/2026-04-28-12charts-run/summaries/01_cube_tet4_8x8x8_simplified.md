# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 14 线程，`0.159 ms`
- 最高加速比：`cpu_row_owner` @ 14 线程，`3.247x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 0.517 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 0.638 | 0.811 | 0.811 | 0 B | PASS |
| cpu_private_csr | 1 | 0.389 | 1.328 | 1.328 | 639.63 KiB | PASS |
| cpu_coo_sort_reduce | 1 | 17.755 | 0.029 | 0.029 | 6.75 MiB | PASS |
| cpu_graph_coloring | 1 | 0.685 | 0.755 | 0.755 | 24.00 KiB | PASS |
| cpu_row_owner | 1 | 0.798 | 0.648 | 0.648 | 5.06 MiB | PASS |
| cpu_atomic | 2 | 0.470 | 1.099 | 0.550 | 0 B | PASS |
| cpu_private_csr | 2 | 0.303 | 1.705 | 0.852 | 1.25 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 12.794 | 0.040 | 0.020 | 6.75 MiB | PASS |
| cpu_graph_coloring | 2 | 0.858 | 0.603 | 0.301 | 24.00 KiB | PASS |
| cpu_row_owner | 2 | 0.332 | 1.557 | 0.779 | 5.06 MiB | PASS |
| cpu_atomic | 4 | 0.220 | 2.353 | 0.588 | 0 B | PASS |
| cpu_private_csr | 4 | 0.178 | 2.905 | 0.726 | 2.50 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 10.203 | 0.051 | 0.013 | 6.75 MiB | PASS |
| cpu_graph_coloring | 4 | 0.798 | 0.648 | 0.162 | 24.00 KiB | PASS |
| cpu_row_owner | 4 | 0.195 | 2.648 | 0.662 | 5.06 MiB | PASS |
| cpu_atomic | 8 | 0.269 | 1.920 | 0.240 | 0 B | PASS |
| cpu_private_csr | 8 | 0.225 | 2.303 | 0.288 | 5.00 MiB | PASS |
| cpu_coo_sort_reduce | 8 | 8.589 | 0.060 | 0.008 | 6.75 MiB | PASS |
| cpu_graph_coloring | 8 | 1.661 | 0.311 | 0.039 | 24.00 KiB | PASS |
| cpu_row_owner | 8 | 0.211 | 2.447 | 0.306 | 5.06 MiB | PASS |
| cpu_atomic | 14 | 0.267 | 1.934 | 0.138 | 0 B | PASS |
| cpu_private_csr | 14 | 0.438 | 1.181 | 0.084 | 8.74 MiB | PASS |
| cpu_coo_sort_reduce | 14 | 7.829 | 0.066 | 0.005 | 6.75 MiB | PASS |
| cpu_graph_coloring | 14 | 3.075 | 0.168 | 0.012 | 24.00 KiB | PASS |
| cpu_row_owner | 14 | 0.159 | 3.247 | 0.232 | 5.06 MiB | PASS |
