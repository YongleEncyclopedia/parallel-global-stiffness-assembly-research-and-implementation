# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 9 线程，`116.150 ms`
- 最高加速比：`cpu_private_csr` @ 9 线程，`4.900x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 775.733 | 0.734 | 0.734 | 0 B | PASS |
| cpu_private_csr | 1 | 603.610 | 0.943 | 0.943 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 656.005 | 0.868 | 0.868 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 938.725 | 0.606 | 0.606 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 408.344 | 1.394 | 0.697 | 0 B | PASS |
| cpu_private_csr | 2 | 297.254 | 1.915 | 0.957 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 336.397 | 1.692 | 0.846 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 496.457 | 1.146 | 0.573 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 293.539 | 1.939 | 0.646 | 0 B | PASS |
| cpu_private_csr | 3 | 231.804 | 2.455 | 0.818 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 240.950 | 2.362 | 0.787 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 364.089 | 1.563 | 0.521 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 242.703 | 2.345 | 0.586 | 0 B | PASS |
| cpu_private_csr | 4 | 182.614 | 3.117 | 0.779 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 202.057 | 2.817 | 0.704 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 281.180 | 2.024 | 0.506 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 194.416 | 2.928 | 0.586 | 0 B | PASS |
| cpu_private_csr | 5 | 168.677 | 3.374 | 0.675 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 184.244 | 3.089 | 0.618 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 243.359 | 2.339 | 0.468 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 185.142 | 3.074 | 0.512 | 0 B | PASS |
| cpu_private_csr | 6 | 138.996 | 4.095 | 0.682 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 147.943 | 3.847 | 0.641 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 211.532 | 2.691 | 0.448 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 157.939 | 3.604 | 0.515 | 0 B | PASS |
| cpu_private_csr | 7 | 134.491 | 4.232 | 0.605 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 156.902 | 3.628 | 0.518 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 194.145 | 2.932 | 0.419 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 149.940 | 3.796 | 0.474 | 0 B | PASS |
| cpu_private_csr | 8 | 129.482 | 4.396 | 0.549 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 133.979 | 4.248 | 0.531 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 181.230 | 3.141 | 0.393 | 8.50 MiB | PASS |
| cpu_atomic | 9 | 137.305 | 4.145 | 0.461 | 0 B | PASS |
| cpu_private_csr | 9 | 116.150 | 4.900 | 0.544 | 1.84 GiB | PASS |
| cpu_row_owner | 9 | 139.779 | 4.072 | 0.452 | 1.79 GiB | PASS |
| cpu_graph_coloring | 9 | 208.293 | 2.733 | 0.304 | 8.50 MiB | PASS |
| cpu_atomic | 10 | 140.356 | 4.055 | 0.406 | 0 B | PASS |
| cpu_private_csr | 10 | 130.408 | 4.364 | 0.436 | 2.05 GiB | PASS |
| cpu_row_owner | 10 | 126.131 | 4.512 | 0.451 | 1.79 GiB | PASS |
| cpu_graph_coloring | 10 | 199.890 | 2.847 | 0.285 | 8.50 MiB | PASS |
