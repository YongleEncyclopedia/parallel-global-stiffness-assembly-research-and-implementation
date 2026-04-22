# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 8 线程，`119.566 ms`
- 最高加速比：`cpu_private_csr` @ 8 线程，`4.686x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 560.300 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 738.570 | 0.759 | 0.759 | 0 B | PASS |
| cpu_private_csr | 1 | 553.981 | 1.011 | 1.011 | 209.83 MiB | PASS |
| cpu_graph_coloring | 1 | 885.394 | 0.633 | 0.633 | 8.50 MiB | PASS |
| cpu_row_owner | 1 | 602.326 | 0.930 | 0.930 | 1.79 GiB | PASS |
| cpu_atomic | 2 | 399.921 | 1.401 | 0.701 | 0 B | PASS |
| cpu_private_csr | 2 | 308.891 | 1.814 | 0.907 | 419.65 MiB | PASS |
| cpu_graph_coloring | 2 | 508.919 | 1.101 | 0.550 | 8.50 MiB | PASS |
| cpu_row_owner | 2 | 329.308 | 1.701 | 0.851 | 1.79 GiB | PASS |
| cpu_atomic | 4 | 232.185 | 2.413 | 0.603 | 0 B | PASS |
| cpu_private_csr | 4 | 174.898 | 3.204 | 0.801 | 839.30 MiB | PASS |
| cpu_graph_coloring | 4 | 288.917 | 1.939 | 0.485 | 8.50 MiB | PASS |
| cpu_row_owner | 4 | 208.202 | 2.691 | 0.673 | 1.79 GiB | PASS |
| cpu_atomic | 8 | 149.103 | 3.758 | 0.470 | 0 B | PASS |
| cpu_private_csr | 8 | 119.566 | 4.686 | 0.586 | 1.64 GiB | PASS |
| cpu_graph_coloring | 8 | 153.593 | 3.648 | 0.456 | 8.50 MiB | PASS |
| cpu_row_owner | 8 | 120.444 | 4.652 | 0.581 | 1.79 GiB | PASS |
| cpu_atomic | 14 | 123.174 | 4.549 | 0.325 | 0 B | PASS |
| cpu_private_csr | 14 | 134.537 | 4.165 | 0.297 | 2.87 GiB | PASS |
| cpu_graph_coloring | 14 | 154.949 | 3.616 | 0.258 | 8.50 MiB | PASS |
| cpu_row_owner | 14 | 121.996 | 4.593 | 0.328 | 1.79 GiB | PASS |
