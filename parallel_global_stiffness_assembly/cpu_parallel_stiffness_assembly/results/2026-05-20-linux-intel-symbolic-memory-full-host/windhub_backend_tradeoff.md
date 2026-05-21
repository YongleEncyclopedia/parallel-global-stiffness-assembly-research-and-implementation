# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_atomic` @ 17 线程，`156.156 ms`
- 最高加速比：`cpu_atomic` @ 17 线程，`4.866x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1309.329 | 0.580 | 0.580 | 0 B | PASS |
| cpu_private_csr | 1 | 794.749 | 0.956 | 0.956 | 209.83 MiB | PASS |
| cpu_lock_guard | 1 | 2683.864 | 0.283 | 0.283 | 1.02 GiB | PASS |
| cpu_atomic | 2 | 702.432 | 1.082 | 0.541 | 0 B | PASS |
| cpu_private_csr | 2 | 465.132 | 1.634 | 0.817 | 419.65 MiB | PASS |
| cpu_lock_guard | 2 | 1877.923 | 0.405 | 0.202 | 1.02 GiB | PASS |
| cpu_atomic | 3 | 488.894 | 1.554 | 0.518 | 0 B | PASS |
| cpu_private_csr | 3 | 370.287 | 2.052 | 0.684 | 629.48 MiB | PASS |
| cpu_lock_guard | 3 | 1392.318 | 0.546 | 0.182 | 1.02 GiB | PASS |
| cpu_atomic | 4 | 377.627 | 2.012 | 0.503 | 0 B | PASS |
| cpu_private_csr | 4 | 320.551 | 2.371 | 0.593 | 839.30 MiB | PASS |
| cpu_lock_guard | 4 | 1145.451 | 0.663 | 0.166 | 1.02 GiB | PASS |
| cpu_atomic | 5 | 314.627 | 2.415 | 0.483 | 0 B | PASS |
| cpu_private_csr | 5 | 297.253 | 2.556 | 0.511 | 1.02 GiB | PASS |
| cpu_lock_guard | 5 | 993.514 | 0.765 | 0.153 | 1.02 GiB | PASS |
| cpu_atomic | 6 | 268.673 | 2.828 | 0.471 | 0 B | PASS |
| cpu_private_csr | 6 | 282.260 | 2.692 | 0.449 | 1.23 GiB | PASS |
| cpu_lock_guard | 6 | 886.394 | 0.857 | 0.143 | 1.02 GiB | PASS |
| cpu_atomic | 7 | 238.872 | 3.181 | 0.454 | 0 B | PASS |
| cpu_private_csr | 7 | 279.447 | 2.719 | 0.388 | 1.43 GiB | PASS |
| cpu_lock_guard | 7 | 801.779 | 0.948 | 0.135 | 1.02 GiB | PASS |
| cpu_atomic | 8 | 217.504 | 3.494 | 0.437 | 0 B | PASS |
| cpu_private_csr | 8 | 285.874 | 2.658 | 0.332 | 1.64 GiB | PASS |
| cpu_lock_guard | 8 | 761.883 | 0.997 | 0.125 | 1.02 GiB | PASS |
| cpu_atomic | 9 | 228.220 | 3.330 | 0.370 | 0 B | PASS |
| cpu_private_csr | 9 | 307.833 | 2.468 | 0.274 | 1.84 GiB | PASS |
| cpu_lock_guard | 9 | 733.982 | 1.035 | 0.115 | 1.02 GiB | PASS |
| cpu_atomic | 10 | 218.795 | 3.473 | 0.347 | 0 B | PASS |
| cpu_private_csr | 10 | 333.923 | 2.276 | 0.228 | 2.05 GiB | PASS |
| cpu_lock_guard | 10 | 705.856 | 1.077 | 0.108 | 1.02 GiB | PASS |
| cpu_atomic | 11 | 205.380 | 3.700 | 0.336 | 0 B | PASS |
| cpu_private_csr | 11 | 345.664 | 2.198 | 0.200 | 2.25 GiB | PASS |
| cpu_lock_guard | 11 | 682.662 | 1.113 | 0.101 | 1.02 GiB | PASS |
| cpu_atomic | 12 | 194.690 | 3.903 | 0.325 | 0 B | PASS |
| cpu_private_csr | 12 | 351.239 | 2.163 | 0.180 | 2.46 GiB | PASS |
| cpu_lock_guard | 12 | 681.723 | 1.115 | 0.093 | 1.02 GiB | PASS |
| cpu_atomic | 13 | 184.928 | 4.109 | 0.316 | 0 B | PASS |
| cpu_private_csr | 13 | 368.261 | 2.063 | 0.159 | 2.66 GiB | PASS |
| cpu_lock_guard | 13 | 665.987 | 1.141 | 0.088 | 1.02 GiB | PASS |
| cpu_atomic | 14 | 177.273 | 4.287 | 0.306 | 0 B | PASS |
| cpu_private_csr | 14 | 374.235 | 2.030 | 0.145 | 2.87 GiB | PASS |
| cpu_lock_guard | 14 | 654.281 | 1.161 | 0.083 | 1.02 GiB | PASS |
| cpu_atomic | 15 | 174.336 | 4.359 | 0.291 | 0 B | PASS |
| cpu_private_csr | 15 | 394.887 | 1.924 | 0.128 | 3.07 GiB | PASS |
| cpu_lock_guard | 15 | 650.810 | 1.168 | 0.078 | 1.02 GiB | PASS |
| cpu_atomic | 16 | 166.484 | 4.564 | 0.285 | 0 B | PASS |
| cpu_private_csr | 16 | 413.691 | 1.837 | 0.115 | 3.28 GiB | PASS |
| cpu_lock_guard | 16 | 655.352 | 1.159 | 0.072 | 1.02 GiB | PASS |
| cpu_atomic | 17 | 156.156 | 4.866 | 0.286 | 0 B | PASS |
| cpu_private_csr | 17 | 428.000 | 1.775 | 0.104 | 3.48 GiB | PASS |
| cpu_lock_guard | 17 | 654.280 | 1.161 | 0.068 | 1.02 GiB | PASS |
| cpu_atomic | 18 | 159.595 | 4.761 | 0.265 | 0 B | PASS |
| cpu_private_csr | 18 | 446.832 | 1.701 | 0.094 | 3.69 GiB | PASS |
| cpu_lock_guard | 18 | 635.537 | 1.196 | 0.066 | 1.02 GiB | PASS |
| cpu_atomic | 19 | 172.013 | 4.418 | 0.233 | 0 B | PASS |
| cpu_private_csr | 19 | 462.139 | 1.644 | 0.087 | 3.89 GiB | PASS |
| cpu_lock_guard | 19 | 681.821 | 1.114 | 0.059 | 1.02 GiB | PASS |
| cpu_atomic | 20 | 183.178 | 4.148 | 0.207 | 0 B | PASS |
| cpu_private_csr | 20 | 484.788 | 1.567 | 0.078 | 4.10 GiB | PASS |
| cpu_lock_guard | 20 | 655.819 | 1.159 | 0.058 | 1.02 GiB | PASS |
