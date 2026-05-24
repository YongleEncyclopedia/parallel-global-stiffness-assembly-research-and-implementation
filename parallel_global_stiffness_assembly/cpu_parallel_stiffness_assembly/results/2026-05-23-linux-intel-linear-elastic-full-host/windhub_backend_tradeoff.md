# CPU 并行整体刚度矩阵组装实验摘要

- 最快单次平均组装：`cpu_atomic` @ 20 线程，`139.186 ms`
- 最高加速比：`cpu_atomic` @ 20 线程，`5.051x`
- 最低额外内存：`cpu_atomic`，`0 B`

| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| cpu_atomic | 1 | 1188.554 | 0.592 | 0.592 | 0 B | PASS |
| cpu_private_csr | 1 | 702.826 | 1.000 | 1.000 | 209.83 MiB | PASS |
| cpu_lock_guard | 1 | 2405.369 | 0.292 | 0.292 | 1.02 GiB | PASS |
| cpu_atomic | 2 | 660.306 | 1.065 | 0.532 | 0 B | PASS |
| cpu_private_csr | 2 | 434.898 | 1.617 | 0.808 | 419.65 MiB | PASS |
| cpu_lock_guard | 2 | 1738.483 | 0.404 | 0.202 | 1.02 GiB | PASS |
| cpu_atomic | 3 | 466.241 | 1.508 | 0.503 | 0 B | PASS |
| cpu_private_csr | 3 | 350.258 | 2.007 | 0.669 | 629.48 MiB | PASS |
| cpu_lock_guard | 3 | 1293.479 | 0.544 | 0.181 | 1.02 GiB | PASS |
| cpu_atomic | 4 | 370.194 | 1.899 | 0.475 | 0 B | PASS |
| cpu_private_csr | 4 | 308.113 | 2.282 | 0.570 | 839.30 MiB | PASS |
| cpu_lock_guard | 4 | 1042.895 | 0.674 | 0.169 | 1.02 GiB | PASS |
| cpu_atomic | 5 | 309.917 | 2.269 | 0.454 | 0 B | PASS |
| cpu_private_csr | 5 | 285.879 | 2.459 | 0.492 | 1.02 GiB | PASS |
| cpu_lock_guard | 5 | 903.840 | 0.778 | 0.156 | 1.02 GiB | PASS |
| cpu_atomic | 6 | 261.512 | 2.689 | 0.448 | 0 B | PASS |
| cpu_private_csr | 6 | 272.455 | 2.581 | 0.430 | 1.23 GiB | PASS |
| cpu_lock_guard | 6 | 799.481 | 0.879 | 0.147 | 1.02 GiB | PASS |
| cpu_atomic | 7 | 232.181 | 3.028 | 0.433 | 0 B | PASS |
| cpu_private_csr | 7 | 269.305 | 2.611 | 0.373 | 1.43 GiB | PASS |
| cpu_lock_guard | 7 | 715.610 | 0.982 | 0.140 | 1.02 GiB | PASS |
| cpu_atomic | 8 | 208.765 | 3.368 | 0.421 | 0 B | PASS |
| cpu_private_csr | 8 | 271.928 | 2.586 | 0.323 | 1.64 GiB | PASS |
| cpu_lock_guard | 8 | 667.260 | 1.054 | 0.132 | 1.02 GiB | PASS |
| cpu_atomic | 9 | 211.627 | 3.322 | 0.369 | 0 B | PASS |
| cpu_private_csr | 9 | 289.760 | 2.426 | 0.270 | 1.84 GiB | PASS |
| cpu_lock_guard | 9 | 632.443 | 1.112 | 0.124 | 1.02 GiB | PASS |
| cpu_atomic | 10 | 194.725 | 3.611 | 0.361 | 0 B | PASS |
| cpu_private_csr | 10 | 298.626 | 2.354 | 0.235 | 2.05 GiB | PASS |
| cpu_lock_guard | 10 | 606.042 | 1.160 | 0.116 | 1.02 GiB | PASS |
| cpu_atomic | 11 | 186.845 | 3.763 | 0.342 | 0 B | PASS |
| cpu_private_csr | 11 | 312.245 | 2.252 | 0.205 | 2.25 GiB | PASS |
| cpu_lock_guard | 11 | 598.718 | 1.174 | 0.107 | 1.02 GiB | PASS |
| cpu_atomic | 12 | 180.177 | 3.902 | 0.325 | 0 B | PASS |
| cpu_private_csr | 12 | 331.871 | 2.119 | 0.177 | 2.46 GiB | PASS |
| cpu_lock_guard | 12 | 581.606 | 1.209 | 0.101 | 1.02 GiB | PASS |
| cpu_atomic | 13 | 170.374 | 4.127 | 0.317 | 0 B | PASS |
| cpu_private_csr | 13 | 340.371 | 2.066 | 0.159 | 2.66 GiB | PASS |
| cpu_lock_guard | 13 | 579.178 | 1.214 | 0.093 | 1.02 GiB | PASS |
| cpu_atomic | 14 | 161.725 | 4.347 | 0.311 | 0 B | PASS |
| cpu_private_csr | 14 | 355.106 | 1.980 | 0.141 | 2.87 GiB | PASS |
| cpu_lock_guard | 14 | 564.272 | 1.246 | 0.089 | 1.02 GiB | PASS |
| cpu_atomic | 15 | 154.661 | 4.546 | 0.303 | 0 B | PASS |
| cpu_private_csr | 15 | 366.609 | 1.918 | 0.128 | 3.07 GiB | PASS |
| cpu_lock_guard | 15 | 552.472 | 1.273 | 0.085 | 1.02 GiB | PASS |
| cpu_atomic | 16 | 153.731 | 4.573 | 0.286 | 0 B | PASS |
| cpu_private_csr | 16 | 380.174 | 1.849 | 0.116 | 3.28 GiB | PASS |
| cpu_lock_guard | 16 | 541.303 | 1.299 | 0.081 | 1.02 GiB | PASS |
| cpu_atomic | 17 | 143.841 | 4.888 | 0.288 | 0 B | PASS |
| cpu_private_csr | 17 | 389.232 | 1.806 | 0.106 | 3.48 GiB | PASS |
| cpu_lock_guard | 17 | 551.898 | 1.274 | 0.075 | 1.02 GiB | PASS |
| cpu_atomic | 18 | 145.541 | 4.831 | 0.268 | 0 B | PASS |
| cpu_private_csr | 18 | 406.733 | 1.729 | 0.096 | 3.69 GiB | PASS |
| cpu_lock_guard | 18 | 539.339 | 1.304 | 0.072 | 1.02 GiB | PASS |
| cpu_atomic | 19 | 146.681 | 4.793 | 0.252 | 0 B | PASS |
| cpu_private_csr | 19 | 420.237 | 1.673 | 0.088 | 3.89 GiB | PASS |
| cpu_lock_guard | 19 | 533.105 | 1.319 | 0.069 | 1.02 GiB | PASS |
| cpu_atomic | 20 | 139.186 | 5.051 | 0.253 | 0 B | PASS |
| cpu_private_csr | 20 | 433.340 | 1.622 | 0.081 | 4.10 GiB | PASS |
| cpu_lock_guard | 20 | 536.531 | 1.310 | 0.066 | 1.02 GiB | PASS |
