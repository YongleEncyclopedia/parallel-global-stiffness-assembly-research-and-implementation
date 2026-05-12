# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 8 线程，`189.616 ms`
- 最高加速比：`cpu_row_owner` @ 8 线程，`3.874x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1276.572 | 0.575 | 0.575 | 0 B | PASS |
| cpu_private_csr | 1 | 787.563 | 0.933 | 0.933 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 870.251 | 0.844 | 0.844 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 1353.714 | 0.543 | 0.543 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 684.312 | 1.073 | 0.537 | 0 B | PASS |
| cpu_private_csr | 2 | 473.528 | 1.551 | 0.776 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 495.676 | 1.482 | 0.741 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 773.488 | 0.950 | 0.475 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 474.896 | 1.547 | 0.516 | 0 B | PASS |
| cpu_private_csr | 3 | 363.663 | 2.020 | 0.673 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 375.706 | 1.955 | 0.652 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 561.741 | 1.308 | 0.436 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 368.101 | 1.995 | 0.499 | 0 B | PASS |
| cpu_private_csr | 4 | 315.314 | 2.329 | 0.582 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 301.008 | 2.440 | 0.610 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 437.172 | 1.680 | 0.420 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 302.153 | 2.431 | 0.486 | 0 B | PASS |
| cpu_private_csr | 5 | 291.680 | 2.518 | 0.504 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 259.744 | 2.828 | 0.566 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 365.785 | 2.008 | 0.402 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 257.812 | 2.849 | 0.475 | 0 B | PASS |
| cpu_private_csr | 6 | 278.594 | 2.637 | 0.439 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 219.803 | 3.342 | 0.557 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 308.704 | 2.379 | 0.397 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 227.585 | 3.227 | 0.461 | 0 B | PASS |
| cpu_private_csr | 7 | 274.061 | 2.680 | 0.383 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 207.993 | 3.531 | 0.504 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 274.842 | 2.673 | 0.382 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 204.800 | 3.587 | 0.448 | 0 B | PASS |
| cpu_private_csr | 8 | 277.085 | 2.651 | 0.331 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 189.616 | 3.874 | 0.484 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 249.501 | 2.944 | 0.368 | 8.50 MiB | PASS |
