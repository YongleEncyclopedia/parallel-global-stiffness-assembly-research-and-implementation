# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_row_owner` @ 14 线程，`45.503 ms`
- 最高加速比：`cpu_row_owner` @ 14 线程，`4.132x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 188.003 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 255.935 | 0.735 | 0.735 | 0 B | PASS |
| cpu_private_csr | 1 | 162.081 | 1.160 | 1.160 | 209.83 MiB | PASS |
| cpu_coo_sort_reduce | 1 | 6254.312 | 0.030 | 0.030 | 2.39 GiB | PASS |
| cpu_graph_coloring | 1 | 484.230 | 0.388 | 0.388 | 8.50 MiB | PASS |
| cpu_row_owner | 1 | 262.917 | 0.715 | 0.715 | 1.79 GiB | PASS |
| cpu_atomic | 2 | 194.769 | 0.965 | 0.483 | 0 B | PASS |
| cpu_private_csr | 2 | 125.181 | 1.502 | 0.751 | 419.65 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 5004.563 | 0.038 | 0.019 | 2.39 GiB | PASS |
| cpu_graph_coloring | 2 | 311.257 | 0.604 | 0.302 | 8.50 MiB | PASS |
| cpu_row_owner | 2 | 132.517 | 1.419 | 0.709 | 1.79 GiB | PASS |
| cpu_atomic | 4 | 177.084 | 1.062 | 0.265 | 0 B | PASS |
| cpu_private_csr | 4 | 81.541 | 2.306 | 0.576 | 839.30 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 4273.865 | 0.044 | 0.011 | 2.39 GiB | PASS |
| cpu_graph_coloring | 4 | 171.058 | 1.099 | 0.275 | 8.50 MiB | PASS |
| cpu_row_owner | 4 | 90.668 | 2.074 | 0.518 | 1.79 GiB | PASS |
| cpu_atomic | 8 | 76.600 | 2.454 | 0.307 | 0 B | PASS |
| cpu_private_csr | 8 | 61.593 | 3.052 | 0.382 | 1.64 GiB | PASS |
| cpu_coo_sort_reduce | 8 | 3883.077 | 0.048 | 0.006 | 2.39 GiB | PASS |
| cpu_graph_coloring | 8 | 102.420 | 1.836 | 0.229 | 8.50 MiB | PASS |
| cpu_row_owner | 8 | 55.157 | 3.408 | 0.426 | 1.79 GiB | PASS |
| cpu_atomic | 14 | 64.328 | 2.923 | 0.209 | 0 B | PASS |
| cpu_private_csr | 14 | 446.221 | 0.421 | 0.030 | 2.87 GiB | PASS |
| cpu_coo_sort_reduce | 14 | 4843.277 | 0.039 | 0.003 | 2.39 GiB | PASS |
| cpu_graph_coloring | 14 | 118.111 | 1.592 | 0.114 | 8.50 MiB | PASS |
| cpu_row_owner | 14 | 45.503 | 4.132 | 0.295 | 1.79 GiB | PASS |
