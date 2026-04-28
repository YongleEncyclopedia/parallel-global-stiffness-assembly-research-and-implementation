# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_atomic` @ 14 线程，`97.171 ms`
- 最高加速比：`cpu_atomic` @ 14 线程，`4.445x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 431.943 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 542.519 | 0.796 | 0.796 | 0 B | PASS |
| cpu_private_csr | 1 | 441.568 | 0.978 | 0.978 | 209.83 MiB | PASS |
| cpu_coo_sort_reduce | 1 | 4934.653 | 0.088 | 0.088 | 2.39 GiB | PASS |
| cpu_graph_coloring | 1 | 990.955 | 0.436 | 0.436 | 8.50 MiB | PASS |
| cpu_row_owner | 1 | 506.244 | 0.853 | 0.853 | 1.79 GiB | PASS |
| cpu_atomic | 2 | 303.807 | 1.422 | 0.711 | 0 B | PASS |
| cpu_private_csr | 2 | 247.649 | 1.744 | 0.872 | 419.65 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 4137.488 | 0.104 | 0.052 | 2.39 GiB | PASS |
| cpu_graph_coloring | 2 | 444.597 | 0.972 | 0.486 | 8.50 MiB | PASS |
| cpu_row_owner | 2 | 274.532 | 1.573 | 0.787 | 1.79 GiB | PASS |
| cpu_atomic | 4 | 218.100 | 1.980 | 0.495 | 0 B | PASS |
| cpu_private_csr | 4 | 162.639 | 2.656 | 0.664 | 839.30 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 4166.417 | 0.104 | 0.026 | 2.39 GiB | PASS |
| cpu_graph_coloring | 4 | 281.387 | 1.535 | 0.384 | 8.50 MiB | PASS |
| cpu_row_owner | 4 | 174.639 | 2.473 | 0.618 | 1.79 GiB | PASS |
| cpu_atomic | 8 | 121.839 | 3.545 | 0.443 | 0 B | PASS |
| cpu_private_csr | 8 | 101.778 | 4.244 | 0.530 | 1.64 GiB | PASS |
| cpu_coo_sort_reduce | 8 | 3908.198 | 0.111 | 0.014 | 2.39 GiB | PASS |
| cpu_graph_coloring | 8 | 144.914 | 2.981 | 0.373 | 8.50 MiB | PASS |
| cpu_row_owner | 8 | 109.519 | 3.944 | 0.493 | 1.79 GiB | PASS |
| cpu_atomic | 14 | 97.171 | 4.445 | 0.318 | 0 B | PASS |
| cpu_private_csr | 14 | 750.323 | 0.576 | 0.041 | 2.87 GiB | PASS |
| cpu_coo_sort_reduce | 14 | 4686.780 | 0.092 | 0.007 | 2.39 GiB | PASS |
| cpu_graph_coloring | 14 | 142.753 | 3.026 | 0.216 | 8.50 MiB | PASS |
| cpu_row_owner | 14 | 100.609 | 4.293 | 0.307 | 1.79 GiB | PASS |
