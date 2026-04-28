# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 14 线程，`43.611 ms`
- 最高加速比：`cpu_row_owner` @ 14 线程，`3.718x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 162.127 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 356.451 | 0.455 | 0.455 | 0 B | PASS |
| cpu_private_csr | 1 | 155.971 | 1.039 | 1.039 | 209.83 MiB | PASS |
| cpu_coo_sort_reduce | 1 | 4262.421 | 0.038 | 0.038 | 2.39 GiB | PASS |
| cpu_graph_coloring | 1 | 484.301 | 0.335 | 0.335 | 8.50 MiB | PASS |
| cpu_row_owner | 1 | 200.537 | 0.808 | 0.808 | 1.79 GiB | PASS |
| cpu_atomic | 2 | 165.139 | 0.982 | 0.491 | 0 B | PASS |
| cpu_private_csr | 2 | 103.568 | 1.565 | 0.783 | 419.65 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 3879.940 | 0.042 | 0.021 | 2.39 GiB | PASS |
| cpu_graph_coloring | 2 | 304.738 | 0.532 | 0.266 | 8.50 MiB | PASS |
| cpu_row_owner | 2 | 131.542 | 1.233 | 0.616 | 1.79 GiB | PASS |
| cpu_atomic | 4 | 125.276 | 1.294 | 0.324 | 0 B | PASS |
| cpu_private_csr | 4 | 81.178 | 1.997 | 0.499 | 839.30 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 3841.488 | 0.042 | 0.011 | 2.39 GiB | PASS |
| cpu_graph_coloring | 4 | 170.785 | 0.949 | 0.237 | 8.50 MiB | PASS |
| cpu_row_owner | 4 | 88.611 | 1.830 | 0.457 | 1.79 GiB | PASS |
| cpu_atomic | 8 | 76.678 | 2.114 | 0.264 | 0 B | PASS |
| cpu_private_csr | 8 | 61.576 | 2.633 | 0.329 | 1.64 GiB | PASS |
| cpu_coo_sort_reduce | 8 | 3802.303 | 0.043 | 0.005 | 2.39 GiB | PASS |
| cpu_graph_coloring | 8 | 101.671 | 1.595 | 0.199 | 8.50 MiB | PASS |
| cpu_row_owner | 8 | 55.293 | 2.932 | 0.367 | 1.79 GiB | PASS |
| cpu_atomic | 14 | 61.758 | 2.625 | 0.188 | 0 B | PASS |
| cpu_private_csr | 14 | 64.046 | 2.531 | 0.181 | 2.87 GiB | PASS |
| cpu_coo_sort_reduce | 14 | 3823.879 | 0.042 | 0.003 | 2.39 GiB | PASS |
| cpu_graph_coloring | 14 | 92.381 | 1.755 | 0.125 | 8.50 MiB | PASS |
| cpu_row_owner | 14 | 43.611 | 3.718 | 0.266 | 1.79 GiB | PASS |
