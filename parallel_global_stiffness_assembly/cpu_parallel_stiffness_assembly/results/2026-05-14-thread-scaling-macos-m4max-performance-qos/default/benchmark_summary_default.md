# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_private_csr` @ 8 线程，`127.380 ms`
- 最高加速比：`cpu_private_csr` @ 8 线程，`4.453x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 779.499 | 0.728 | 0.728 | 0 B | PASS |
| cpu_private_csr | 1 | 579.165 | 0.979 | 0.979 | 209.83 MiB | PASS |
| cpu_row_owner | 1 | 625.446 | 0.907 | 0.907 | 1.79 GiB | PASS |
| cpu_graph_coloring | 1 | 932.873 | 0.608 | 0.608 | 8.50 MiB | PASS |
| cpu_atomic | 2 | 429.397 | 1.321 | 0.661 | 0 B | PASS |
| cpu_private_csr | 2 | 321.659 | 1.764 | 0.882 | 419.65 MiB | PASS |
| cpu_row_owner | 2 | 330.074 | 1.719 | 0.859 | 1.79 GiB | PASS |
| cpu_graph_coloring | 2 | 489.707 | 1.158 | 0.579 | 8.50 MiB | PASS |
| cpu_atomic | 3 | 293.256 | 1.934 | 0.645 | 0 B | PASS |
| cpu_private_csr | 3 | 224.445 | 2.527 | 0.842 | 629.48 MiB | PASS |
| cpu_row_owner | 3 | 248.726 | 2.281 | 0.760 | 1.79 GiB | PASS |
| cpu_graph_coloring | 3 | 360.875 | 1.572 | 0.524 | 8.50 MiB | PASS |
| cpu_atomic | 4 | 239.934 | 2.364 | 0.591 | 0 B | PASS |
| cpu_private_csr | 4 | 181.303 | 3.129 | 0.782 | 839.30 MiB | PASS |
| cpu_row_owner | 4 | 196.222 | 2.891 | 0.723 | 1.79 GiB | PASS |
| cpu_graph_coloring | 4 | 279.083 | 2.033 | 0.508 | 8.50 MiB | PASS |
| cpu_atomic | 5 | 216.234 | 2.623 | 0.525 | 0 B | PASS |
| cpu_private_csr | 5 | 162.429 | 3.492 | 0.698 | 1.02 GiB | PASS |
| cpu_row_owner | 5 | 194.844 | 2.911 | 0.582 | 1.79 GiB | PASS |
| cpu_graph_coloring | 5 | 249.727 | 2.272 | 0.454 | 8.50 MiB | PASS |
| cpu_atomic | 6 | 180.550 | 3.142 | 0.524 | 0 B | PASS |
| cpu_private_csr | 6 | 141.400 | 4.012 | 0.669 | 1.23 GiB | PASS |
| cpu_row_owner | 6 | 146.439 | 3.874 | 0.646 | 1.79 GiB | PASS |
| cpu_graph_coloring | 6 | 209.115 | 2.713 | 0.452 | 8.50 MiB | PASS |
| cpu_atomic | 7 | 157.613 | 3.599 | 0.514 | 0 B | PASS |
| cpu_private_csr | 7 | 132.665 | 4.276 | 0.611 | 1.43 GiB | PASS |
| cpu_row_owner | 7 | 158.298 | 3.584 | 0.512 | 1.79 GiB | PASS |
| cpu_graph_coloring | 7 | 193.473 | 2.932 | 0.419 | 8.50 MiB | PASS |
| cpu_atomic | 8 | 153.673 | 3.691 | 0.461 | 0 B | PASS |
| cpu_private_csr | 8 | 127.380 | 4.453 | 0.557 | 1.64 GiB | PASS |
| cpu_row_owner | 8 | 132.056 | 4.296 | 0.537 | 1.79 GiB | PASS |
| cpu_graph_coloring | 8 | 182.677 | 3.105 | 0.388 | 8.50 MiB | PASS |
| cpu_atomic | 9 | 136.109 | 4.168 | 0.463 | 0 B | PASS |
| cpu_private_csr | 9 | 128.167 | 4.426 | 0.492 | 1.84 GiB | PASS |
| cpu_row_owner | 9 | 147.803 | 3.838 | 0.426 | 1.79 GiB | PASS |
| cpu_graph_coloring | 9 | 207.745 | 2.731 | 0.303 | 8.50 MiB | PASS |
| cpu_atomic | 10 | 140.947 | 4.025 | 0.402 | 0 B | PASS |
| cpu_private_csr | 10 | 128.595 | 4.411 | 0.441 | 2.05 GiB | PASS |
| cpu_row_owner | 10 | 130.409 | 4.350 | 0.435 | 1.79 GiB | PASS |
| cpu_graph_coloring | 10 | 209.641 | 2.706 | 0.271 | 8.50 MiB | PASS |
