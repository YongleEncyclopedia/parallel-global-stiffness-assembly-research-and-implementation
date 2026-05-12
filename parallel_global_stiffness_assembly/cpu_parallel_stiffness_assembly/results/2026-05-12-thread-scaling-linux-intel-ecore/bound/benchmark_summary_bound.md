# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 12 线程，`188.142 ms`
- 最高加速比：`cpu_row_owner` @ 12 线程，`5.613x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1708.619 | 0.618 | 0.618 | 0 B | PASS |
| cpu_private_csr | 1 | 1098.290 | 0.962 | 0.962 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 1205.224 | 0.876 | 0.876 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 1815.262 | 0.582 | 0.582 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 922.071 | 1.145 | 0.573 | 0 B | PASS |
| cpu_private_csr | 2 | 649.958 | 1.625 | 0.812 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 684.982 | 1.542 | 0.771 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 940.995 | 1.122 | 0.561 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 655.160 | 1.612 | 0.537 | 0 B | PASS |
| cpu_private_csr | 3 | 505.793 | 2.088 | 0.696 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 493.147 | 2.142 | 0.714 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 647.538 | 1.631 | 0.544 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 504.633 | 2.093 | 0.523 | 0 B | PASS |
| cpu_private_csr | 4 | 430.564 | 2.453 | 0.613 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 389.841 | 2.709 | 0.677 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 499.999 | 2.112 | 0.528 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 413.728 | 2.553 | 0.511 | 0 B | PASS |
| cpu_private_csr | 5 | 399.561 | 2.643 | 0.529 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 346.318 | 3.050 | 0.610 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 419.003 | 2.521 | 0.504 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 351.308 | 3.006 | 0.501 | 0 B | PASS |
| cpu_private_csr | 6 | 378.858 | 2.788 | 0.465 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 276.796 | 3.815 | 0.636 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 355.934 | 2.967 | 0.495 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 313.107 | 3.373 | 0.482 | 0 B | PASS |
| cpu_private_csr | 7 | 372.414 | 2.836 | 0.405 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 278.179 | 3.797 | 0.542 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 316.535 | 3.336 | 0.477 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 277.687 | 3.803 | 0.475 | 0 B | PASS |
| cpu_private_csr | 8 | 376.065 | 2.808 | 0.351 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 247.360 | 4.270 | 0.534 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 288.320 | 3.663 | 0.458 | 8.50 MiB | PASS |
| cpu_atomic | 9 | 253.351 | 4.169 | 0.463 | 0 B | PASS |
| cpu_private_csr | 9 | 381.815 | 2.766 | 0.307 | 1.84 GiB | PASS |
| cpu_row_owner | 9 | 229.887 | 4.594 | 0.510 | 1.79 GiB | PASS |
| cpu_graph_coloring | 9 | 270.374 | 3.906 | 0.434 | 8.50 MiB | PASS |
| cpu_atomic | 10 | 230.602 | 4.580 | 0.458 | 0 B | PASS |
| cpu_private_csr | 10 | 391.108 | 2.700 | 0.270 | 2.05 GiB | PASS |
| cpu_row_owner | 10 | 220.784 | 4.783 | 0.478 | 1.79 GiB | PASS |
| cpu_graph_coloring | 10 | 255.886 | 4.127 | 0.413 | 8.50 MiB | PASS |
| cpu_atomic | 11 | 217.879 | 4.847 | 0.441 | 0 B | PASS |
| cpu_private_csr | 11 | 406.710 | 2.597 | 0.236 | 2.25 GiB | PASS |
| cpu_row_owner | 11 | 212.517 | 4.970 | 0.452 | 1.79 GiB | PASS |
| cpu_graph_coloring | 11 | 243.849 | 4.331 | 0.394 | 8.50 MiB | PASS |
| cpu_atomic | 12 | 202.992 | 5.203 | 0.434 | 0 B | PASS |
| cpu_private_csr | 12 | 427.689 | 2.469 | 0.206 | 2.46 GiB | PASS |
| cpu_row_owner | 12 | 188.142 | 5.613 | 0.468 | 1.79 GiB | PASS |
| cpu_graph_coloring | 12 | 231.924 | 4.554 | 0.379 | 8.50 MiB | PASS |
