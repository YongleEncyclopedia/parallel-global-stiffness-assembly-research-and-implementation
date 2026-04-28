# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 8 线程，`0.284 ms`
- 最高加速比：`cpu_private_csr` @ 8 线程，`3.761x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 1.069 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 1.269 | 0.842 | 0.842 | 0 B | PASS |
| cpu_private_csr | 1 | 1.087 | 0.984 | 0.984 | 639.63 KiB | PASS |
| cpu_coo_sort_reduce | 1 | 8.707 | 0.123 | 0.123 | 6.75 MiB | PASS |
| cpu_graph_coloring | 1 | 1.120 | 0.955 | 0.955 | 24.00 KiB | PASS |
| cpu_row_owner | 1 | 1.174 | 0.911 | 0.911 | 5.06 MiB | PASS |
| cpu_atomic | 2 | 0.664 | 1.610 | 0.805 | 0 B | PASS |
| cpu_private_csr | 2 | 0.587 | 1.821 | 0.910 | 1.25 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 8.059 | 0.133 | 0.066 | 6.75 MiB | PASS |
| cpu_graph_coloring | 2 | 1.024 | 1.045 | 0.522 | 24.00 KiB | PASS |
| cpu_row_owner | 2 | 0.676 | 1.581 | 0.790 | 5.06 MiB | PASS |
| cpu_atomic | 4 | 0.388 | 2.757 | 0.689 | 0 B | PASS |
| cpu_private_csr | 4 | 0.367 | 2.915 | 0.729 | 2.50 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 7.875 | 0.136 | 0.034 | 6.75 MiB | PASS |
| cpu_graph_coloring | 4 | 0.990 | 1.080 | 0.270 | 24.00 KiB | PASS |
| cpu_row_owner | 4 | 0.532 | 2.010 | 0.503 | 5.06 MiB | PASS |
| cpu_atomic | 8 | 0.463 | 2.312 | 0.289 | 0 B | PASS |
| cpu_private_csr | 8 | 0.284 | 3.761 | 0.470 | 5.00 MiB | PASS |
| cpu_coo_sort_reduce | 8 | 7.840 | 0.136 | 0.017 | 6.75 MiB | PASS |
| cpu_graph_coloring | 8 | 1.654 | 0.647 | 0.081 | 24.00 KiB | PASS |
| cpu_row_owner | 8 | 0.533 | 2.007 | 0.251 | 5.06 MiB | PASS |
| cpu_atomic | 14 | 0.323 | 3.311 | 0.236 | 0 B | PASS |
| cpu_private_csr | 14 | 0.376 | 2.841 | 0.203 | 8.74 MiB | PASS |
| cpu_coo_sort_reduce | 14 | 7.823 | 0.137 | 0.010 | 6.75 MiB | PASS |
| cpu_graph_coloring | 14 | 2.772 | 0.386 | 0.028 | 24.00 KiB | PASS |
| cpu_row_owner | 14 | 0.399 | 2.681 | 0.191 | 5.06 MiB | PASS |
