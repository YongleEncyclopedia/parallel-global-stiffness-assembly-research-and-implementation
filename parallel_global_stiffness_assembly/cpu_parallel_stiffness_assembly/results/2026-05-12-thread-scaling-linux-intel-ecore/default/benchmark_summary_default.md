# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 12 线程，`187.465 ms`
- 最高加速比：`cpu_row_owner` @ 12 线程，`5.750x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1719.056 | 0.627 | 0.627 | 0 B | PASS |
| cpu_private_csr | 1 | 1099.022 | 0.981 | 0.981 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 1187.131 | 0.908 | 0.908 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 1813.867 | 0.594 | 0.594 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 916.926 | 1.176 | 0.588 | 0 B | PASS |
| cpu_private_csr | 2 | 648.227 | 1.663 | 0.831 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 684.797 | 1.574 | 0.787 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 938.525 | 1.149 | 0.574 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 639.908 | 1.685 | 0.562 | 0 B | PASS |
| cpu_private_csr | 3 | 488.433 | 2.207 | 0.736 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 476.407 | 2.263 | 0.754 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 649.154 | 1.661 | 0.554 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 504.350 | 2.137 | 0.534 | 0 B | PASS |
| cpu_private_csr | 4 | 440.183 | 2.449 | 0.612 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 389.292 | 2.769 | 0.692 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 506.976 | 2.126 | 0.532 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 414.749 | 2.599 | 0.520 | 0 B | PASS |
| cpu_private_csr | 5 | 388.958 | 2.771 | 0.554 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 344.597 | 3.128 | 0.626 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 412.219 | 2.615 | 0.523 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 352.091 | 3.062 | 0.510 | 0 B | PASS |
| cpu_private_csr | 6 | 381.878 | 2.823 | 0.470 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 277.508 | 3.885 | 0.647 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 355.564 | 3.032 | 0.505 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 309.013 | 3.488 | 0.498 | 0 B | PASS |
| cpu_private_csr | 7 | 366.127 | 2.944 | 0.421 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 274.920 | 3.921 | 0.560 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 318.244 | 3.387 | 0.484 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 278.128 | 3.876 | 0.484 | 0 B | PASS |
| cpu_private_csr | 8 | 375.675 | 2.869 | 0.359 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 245.560 | 4.390 | 0.549 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 293.266 | 3.676 | 0.459 | 8.50 MiB | PASS |
| cpu_atomic | 9 | 252.389 | 4.271 | 0.475 | 0 B | PASS |
| cpu_private_csr | 9 | 380.674 | 2.832 | 0.315 | 1.84 GiB | PASS |
| cpu_row_owner | 9 | 230.294 | 4.681 | 0.520 | 1.79 GiB | PASS |
| cpu_graph_coloring | 9 | 267.646 | 4.028 | 0.448 | 8.50 MiB | PASS |
| cpu_atomic | 10 | 236.330 | 4.561 | 0.456 | 0 B | PASS |
| cpu_private_csr | 10 | 390.194 | 2.763 | 0.276 | 2.05 GiB | PASS |
| cpu_row_owner | 10 | 225.823 | 4.774 | 0.477 | 1.79 GiB | PASS |
| cpu_graph_coloring | 10 | 252.862 | 4.263 | 0.426 | 8.50 MiB | PASS |
| cpu_atomic | 11 | 215.130 | 5.011 | 0.456 | 0 B | PASS |
| cpu_private_csr | 11 | 406.568 | 2.651 | 0.241 | 2.25 GiB | PASS |
| cpu_row_owner | 11 | 209.323 | 5.150 | 0.468 | 1.79 GiB | PASS |
| cpu_graph_coloring | 11 | 249.490 | 4.321 | 0.393 | 8.50 MiB | PASS |
| cpu_atomic | 12 | 204.114 | 5.281 | 0.440 | 0 B | PASS |
| cpu_private_csr | 12 | 437.507 | 2.464 | 0.205 | 2.46 GiB | PASS |
| cpu_row_owner | 12 | 187.465 | 5.750 | 0.479 | 1.79 GiB | PASS |
| cpu_graph_coloring | 12 | 236.288 | 4.562 | 0.380 | 8.50 MiB | PASS |
