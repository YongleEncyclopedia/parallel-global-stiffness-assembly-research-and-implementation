# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 8 线程，`188.690 ms`
- 最高加速比：`cpu_row_owner` @ 8 线程，`3.930x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1283.515 | 0.578 | 0.578 | 0 B | PASS |
| cpu_private_csr | 1 | 772.077 | 0.961 | 0.961 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 856.173 | 0.866 | 0.866 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 1366.567 | 0.543 | 0.543 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 678.915 | 1.092 | 0.546 | 0 B | PASS |
| cpu_private_csr | 2 | 466.409 | 1.590 | 0.795 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 502.766 | 1.475 | 0.738 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 777.410 | 0.954 | 0.477 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 480.752 | 1.543 | 0.514 | 0 B | PASS |
| cpu_private_csr | 3 | 367.787 | 2.016 | 0.672 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 369.315 | 2.008 | 0.669 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 567.081 | 1.308 | 0.436 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 370.433 | 2.002 | 0.500 | 0 B | PASS |
| cpu_private_csr | 4 | 319.574 | 2.321 | 0.580 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 300.017 | 2.472 | 0.618 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 450.037 | 1.648 | 0.412 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 304.970 | 2.432 | 0.486 | 0 B | PASS |
| cpu_private_csr | 5 | 294.593 | 2.517 | 0.503 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 262.181 | 2.829 | 0.566 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 368.798 | 2.011 | 0.402 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 259.456 | 2.858 | 0.476 | 0 B | PASS |
| cpu_private_csr | 6 | 281.251 | 2.637 | 0.439 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 220.358 | 3.365 | 0.561 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 316.139 | 2.346 | 0.391 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 227.572 | 3.259 | 0.466 | 0 B | PASS |
| cpu_private_csr | 7 | 274.938 | 2.697 | 0.385 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 209.281 | 3.544 | 0.506 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 278.010 | 2.668 | 0.381 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 205.705 | 3.605 | 0.451 | 0 B | PASS |
| cpu_private_csr | 8 | 278.189 | 2.666 | 0.333 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 188.690 | 3.930 | 0.491 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 250.981 | 2.955 | 0.369 | 8.50 MiB | PASS |
