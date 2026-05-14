# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 4 线程，`1914.702 ms`
- 最高加速比：`cpu_private_csr` @ 4 线程，`2.918x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 7617.142 | 0.733 | 0.733 | 0 B | PASS |
| cpu_private_csr | 1 | 5562.026 | 1.005 | 1.005 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 6406.605 | 0.872 | 0.872 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 5745.469 | 0.972 | 0.972 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 3327.067 | 1.679 | 0.840 | 0 B | PASS |
| cpu_private_csr | 2 | 2693.684 | 2.074 | 1.037 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 3076.272 | 1.816 | 0.908 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 3223.240 | 1.733 | 0.867 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 2509.887 | 2.226 | 0.742 | 0 B | PASS |
| cpu_private_csr | 3 | 2098.413 | 2.663 | 0.888 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 2433.449 | 2.296 | 0.765 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 2376.342 | 2.351 | 0.784 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 2306.723 | 2.422 | 0.606 | 0 B | PASS |
| cpu_private_csr | 4 | 1914.702 | 2.918 | 0.730 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 2187.520 | 2.554 | 0.639 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 2049.711 | 2.726 | 0.681 | 8.50 MiB | PASS |
