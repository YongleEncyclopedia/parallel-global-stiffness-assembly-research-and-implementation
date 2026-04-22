# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_coo_sort_reduce` @ 4 线程，`4330.916 ms`
- 最高加速比：`cpu_coo_sort_reduce` @ 4 线程，`0.124x`
- 最低额外内存：`cpu_coo_sort_reduce`，`2.39 GiB`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_coo_sort_reduce | 1 | 4935.610 | 0.109 | 0.109 | 2.39 GiB | PASS |
| cpu_coo_sort_reduce | 2 | 4679.651 | 0.115 | 0.057 | 2.39 GiB | PASS |
| cpu_coo_sort_reduce | 4 | 4330.916 | 0.124 | 0.031 | 2.39 GiB | PASS |
