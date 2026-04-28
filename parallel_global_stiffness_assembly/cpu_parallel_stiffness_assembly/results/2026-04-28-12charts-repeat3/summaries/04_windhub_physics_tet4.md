# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_atomic` @ 14 线程，`103.891 ms`
- 最高加速比：`cpu_atomic` @ 14 线程，`4.160x`
- 最低额外内存：`cpu_serial`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_serial | 1 | 432.231 | 1.000 | 1.000 | 0 B | PASS |
| cpu_atomic | 1 | 566.627 | 0.763 | 0.763 | 0 B | PASS |
| cpu_private_csr | 1 | 518.906 | 0.833 | 0.833 | 209.83 MiB | PASS |
| cpu_coo_sort_reduce | 1 | 4204.286 | 0.103 | 0.103 | 2.39 GiB | PASS |
| cpu_graph_coloring | 1 | 803.677 | 0.538 | 0.538 | 8.50 MiB | PASS |
| cpu_row_owner | 1 | 478.935 | 0.902 | 0.902 | 1.79 GiB | PASS |
| cpu_atomic | 2 | 304.349 | 1.420 | 0.710 | 0 B | PASS |
| cpu_private_csr | 2 | 247.512 | 1.746 | 0.873 | 419.65 MiB | PASS |
| cpu_coo_sort_reduce | 2 | 4200.414 | 0.103 | 0.051 | 2.39 GiB | PASS |
| cpu_graph_coloring | 2 | 471.483 | 0.917 | 0.458 | 8.50 MiB | PASS |
| cpu_row_owner | 2 | 353.968 | 1.221 | 0.611 | 1.79 GiB | PASS |
| cpu_atomic | 4 | 214.002 | 2.020 | 0.505 | 0 B | PASS |
| cpu_private_csr | 4 | 172.004 | 2.513 | 0.628 | 839.30 MiB | PASS |
| cpu_coo_sort_reduce | 4 | 4217.253 | 0.102 | 0.026 | 2.39 GiB | PASS |
| cpu_graph_coloring | 4 | 265.494 | 1.628 | 0.407 | 8.50 MiB | PASS |
| cpu_row_owner | 4 | 179.270 | 2.411 | 0.603 | 1.79 GiB | PASS |
| cpu_atomic | 8 | 133.958 | 3.227 | 0.403 | 0 B | PASS |
| cpu_private_csr | 8 | 105.272 | 4.106 | 0.513 | 1.64 GiB | PASS |
| cpu_coo_sort_reduce | 8 | 4081.426 | 0.106 | 0.013 | 2.39 GiB | PASS |
| cpu_graph_coloring | 8 | 146.408 | 2.952 | 0.369 | 8.50 MiB | PASS |
| cpu_row_owner | 8 | 115.408 | 3.745 | 0.468 | 1.79 GiB | PASS |
| cpu_atomic | 14 | 103.891 | 4.160 | 0.297 | 0 B | PASS |
| cpu_private_csr | 14 | 108.442 | 3.986 | 0.285 | 2.87 GiB | PASS |
| cpu_coo_sort_reduce | 14 | 4100.005 | 0.105 | 0.008 | 2.39 GiB | PASS |
| cpu_graph_coloring | 14 | 148.357 | 2.913 | 0.208 | 8.50 MiB | PASS |
| cpu_row_owner | 14 | 110.956 | 3.896 | 0.278 | 1.79 GiB | PASS |
