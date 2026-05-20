# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_atomic` @ 14 线程，`104.437 ms`
- 最高加速比：`cpu_atomic` @ 14 线程，`4.446x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 570.406 | 0.814 | 0.814 | 0 B | PASS |
| cpu_private_csr | 1 | 472.870 | 0.982 | 0.982 | 209.83 MiB | PASS |
| cpu_lock_guard | 1 | 2647.031 | 0.175 | 0.175 | 1.64 GiB | PASS |
| cpu_atomic | 2 | 342.782 | 1.354 | 0.677 | 0 B | PASS |
| cpu_private_csr | 2 | 270.611 | 1.716 | 0.858 | 419.65 MiB | PASS |
| cpu_lock_guard | 2 | 1373.592 | 0.338 | 0.169 | 1.64 GiB | PASS |
| cpu_atomic | 3 | 273.507 | 1.698 | 0.566 | 0 B | PASS |
| cpu_private_csr | 3 | 225.386 | 2.060 | 0.687 | 629.48 MiB | PASS |
| cpu_lock_guard | 3 | 970.974 | 0.478 | 0.159 | 1.64 GiB | PASS |
| cpu_atomic | 4 | 203.833 | 2.278 | 0.569 | 0 B | PASS |
| cpu_private_csr | 4 | 159.590 | 2.909 | 0.727 | 839.30 MiB | PASS |
| cpu_lock_guard | 4 | 760.515 | 0.611 | 0.153 | 1.64 GiB | PASS |
| cpu_atomic | 5 | 183.240 | 2.534 | 0.507 | 0 B | PASS |
| cpu_private_csr | 5 | 136.850 | 3.393 | 0.679 | 1.02 GiB | PASS |
| cpu_lock_guard | 5 | 624.548 | 0.743 | 0.149 | 1.64 GiB | PASS |
| cpu_atomic | 6 | 154.068 | 3.014 | 0.502 | 0 B | PASS |
| cpu_private_csr | 6 | 122.200 | 3.799 | 0.633 | 1.23 GiB | PASS |
| cpu_lock_guard | 6 | 538.400 | 0.862 | 0.144 | 1.64 GiB | PASS |
| cpu_atomic | 7 | 137.016 | 3.389 | 0.484 | 0 B | PASS |
| cpu_private_csr | 7 | 113.344 | 4.096 | 0.585 | 1.43 GiB | PASS |
| cpu_lock_guard | 7 | 481.061 | 0.965 | 0.138 | 1.64 GiB | PASS |
| cpu_atomic | 8 | 129.963 | 3.573 | 0.447 | 0 B | PASS |
| cpu_private_csr | 8 | 105.041 | 4.420 | 0.553 | 1.64 GiB | PASS |
| cpu_lock_guard | 8 | 438.698 | 1.058 | 0.132 | 1.64 GiB | PASS |
| cpu_atomic | 9 | 115.792 | 4.010 | 0.446 | 0 B | PASS |
| cpu_private_csr | 9 | 114.848 | 4.043 | 0.449 | 1.84 GiB | PASS |
| cpu_lock_guard | 9 | 406.806 | 1.141 | 0.127 | 1.64 GiB | PASS |
| cpu_atomic | 10 | 107.391 | 4.323 | 0.432 | 0 B | PASS |
| cpu_private_csr | 10 | 124.261 | 3.736 | 0.374 | 2.05 GiB | PASS |
| cpu_lock_guard | 10 | 365.510 | 1.270 | 0.127 | 1.64 GiB | PASS |
| cpu_atomic | 11 | 110.197 | 4.213 | 0.383 | 0 B | PASS |
| cpu_private_csr | 11 | 137.582 | 3.375 | 0.307 | 2.25 GiB | PASS |
| cpu_lock_guard | 11 | 401.179 | 1.157 | 0.105 | 1.64 GiB | PASS |
| cpu_atomic | 12 | 111.680 | 4.157 | 0.346 | 0 B | PASS |
| cpu_private_csr | 12 | 123.839 | 3.749 | 0.312 | 2.46 GiB | PASS |
| cpu_lock_guard | 12 | 371.893 | 1.248 | 0.104 | 1.64 GiB | PASS |
| cpu_atomic | 13 | 118.091 | 3.932 | 0.302 | 0 B | PASS |
| cpu_private_csr | 13 | 141.210 | 3.288 | 0.253 | 2.66 GiB | PASS |
| cpu_lock_guard | 13 | 376.638 | 1.233 | 0.095 | 1.64 GiB | PASS |
| cpu_atomic | 14 | 104.437 | 4.446 | 0.318 | 0 B | PASS |
| cpu_private_csr | 14 | 153.808 | 3.019 | 0.216 | 2.87 GiB | PASS |
| cpu_lock_guard | 14 | 374.778 | 1.239 | 0.088 | 1.64 GiB | PASS |
