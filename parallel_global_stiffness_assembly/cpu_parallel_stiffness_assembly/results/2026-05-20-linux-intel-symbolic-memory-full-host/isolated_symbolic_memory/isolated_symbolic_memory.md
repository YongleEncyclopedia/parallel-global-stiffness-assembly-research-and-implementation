# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Isolated Symbolic Memory Evaluation

Each row was measured in a fresh subprocess. `isolated_peak_rss_mb` is the OS-observed peak RSS for that single command.

## Rows

| strategy | mode | backend | threads | assemblies | estimated peak bytes | delta bytes | isolated peak RSS MB |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 1 | 1364927580 | 0 | 2782.949 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 1 | 1 | 2898694948 | 1533767368 | 6053.227 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2572.809 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2698.664 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 1 | 1 | 1584945180 | 220017600 | 2887.777 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 1 | 1584945180 | 220017600 | 2908.453 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 1 | 1 | 2465015580 | 1100088000 | 3621.883 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 1 | 2465015580 | 1100088000 | 3747.664 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 2 | 1 | 2898694948 | 1533767368 | 6052.629 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 2572.824 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 3088.793 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 2 | 1 | 1804962780 | 440035200 | 3097.523 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 1 | 1804962780 | 440035200 | 3508.629 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 2 | 1 | 2465015580 | 1100088000 | 3621.711 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 1 | 2465015580 | 1100088000 | 4138.145 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 3 | 1 | 2898694948 | 1533767368 | 5236.156 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 2572.566 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 3226.887 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 3 | 1 | 2024980380 | 660052800 | 3307.312 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 1 | 2024980380 | 660052800 | 3856.516 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 3 | 1 | 2465015580 | 1100088000 | 3621.746 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 1 | 2465015580 | 1100088000 | 4275.883 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 4 | 1 | 2898694948 | 1533767368 | 4828.309 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 2572.887 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 3295.699 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 4 | 1 | 2244997980 | 880070400 | 3517.211 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 1 | 2244997980 | 880070400 | 4135.062 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 4 | 1 | 2465015580 | 1100088000 | 3621.781 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 1 | 2465015580 | 1100088000 | 4345.250 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 5 | 1 | 2898694948 | 1533767368 | 4562.820 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 2572.770 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 3341.617 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 5 | 1 | 2465015580 | 1100088000 | 3727.129 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 1 | 2465015580 | 1100088000 | 4390.742 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 5 | 1 | 2465015580 | 1100088000 | 3621.711 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 1 | 2465015580 | 1100088000 | 4390.637 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 6 | 1 | 2898694948 | 1533767368 | 4420.652 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 2572.668 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 3364.688 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 6 | 1 | 2685033180 | 1320105600 | 3937.113 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 1 | 2685033180 | 1320105600 | 4623.457 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 6 | 1 | 2465015580 | 1100088000 | 3621.812 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 1 | 2465015580 | 1100088000 | 4413.555 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 7 | 1 | 2898694948 | 1533767368 | 4293.254 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 2572.590 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 3283.234 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 7 | 1 | 2905050780 | 1540123200 | 4146.770 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 1 | 2905050780 | 1540123200 | 4752.074 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 7 | 1 | 2465015580 | 1100088000 | 3621.797 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 1 | 2465015580 | 1100088000 | 4332.598 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 8 | 1 | 2898694948 | 1533767368 | 4203.109 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 2572.773 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 3299.434 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 8 | 1 | 3125068380 | 1760140800 | 4356.574 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 1 | 3125068380 | 1760140800 | 4978.512 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 8 | 1 | 2465015580 | 1100088000 | 3621.750 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 1 | 2465015580 | 1100088000 | 4348.832 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 9 | 1 | 2898694948 | 1533767368 | 4134.211 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 9 | 1 | 1364927580 | 0 | 2572.527 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 1 | 1364927580 | 0 | 3309.281 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 9 | 1 | 3345085980 | 1980158400 | 4566.469 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 1 | 3345085980 | 1980158400 | 5198.305 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 9 | 1 | 2465015580 | 1100088000 | 3621.883 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 1 | 2465015580 | 1100088000 | 4358.672 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 10 | 1 | 2898694948 | 1533767368 | 4087.383 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 10 | 1 | 1364927580 | 0 | 2572.535 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 1 | 1364927580 | 0 | 3316.812 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 10 | 1 | 3565103580 | 2200176000 | 4776.086 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 1 | 3565103580 | 2200176000 | 5415.133 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 10 | 1 | 2465015580 | 1100088000 | 3726.996 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 1 | 2465015580 | 1100088000 | 4365.926 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 11 | 1 | 2898694948 | 1533767368 | 4045.098 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 11 | 1 | 1364927580 | 0 | 2572.574 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 1 | 1364927580 | 0 | 3427.855 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 11 | 1 | 3785121180 | 2420193600 | 4985.953 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 1 | 3785121180 | 2420193600 | 5735.512 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 11 | 1 | 2465015580 | 1100088000 | 3727.055 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 1 | 2465015580 | 1100088000 | 4476.824 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 12 | 1 | 2898694948 | 1533767368 | 4012.711 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 12 | 1 | 1364927580 | 0 | 2572.664 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 1 | 1364927580 | 0 | 3327.590 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 12 | 1 | 4005138780 | 2640211200 | 5195.699 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 1 | 4005138780 | 2640211200 | 5845.973 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 12 | 1 | 2465015580 | 1100088000 | 3727.074 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 1 | 2465015580 | 1100088000 | 4377.504 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 13 | 1 | 2898694948 | 1533767368 | 3978.238 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 13 | 1 | 1364927580 | 0 | 2572.770 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 1 | 1364927580 | 0 | 3332.684 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 13 | 1 | 4225156380 | 2860228800 | 5405.645 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 1 | 4225156380 | 2860228800 | 6060.059 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 13 | 1 | 2465015580 | 1100088000 | 3727.031 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 1 | 2465015580 | 1100088000 | 4381.312 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 14 | 1 | 2898694948 | 1533767368 | 3950.793 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 14 | 1 | 1364927580 | 0 | 2572.578 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 1 | 1364927580 | 0 | 3336.113 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 14 | 1 | 4445173980 | 3080246400 | 5615.484 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 1 | 4445173980 | 3080246400 | 6273.711 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 14 | 1 | 2465015580 | 1100088000 | 3727.074 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 1 | 2465015580 | 1100088000 | 4385.805 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 15 | 1 | 2898694948 | 1533767368 | 3926.668 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 15 | 1 | 1364927580 | 0 | 2572.832 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 1 | 1364927580 | 0 | 3339.461 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 15 | 1 | 4665191580 | 3300264000 | 5825.230 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 1 | 4665191580 | 3300264000 | 6486.797 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 15 | 1 | 2465015580 | 1100088000 | 3726.980 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 1 | 2465015580 | 1100088000 | 4388.477 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 16 | 1 | 2898694948 | 1533767368 | 3900.695 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 16 | 1 | 1364927580 | 0 | 2572.703 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 1 | 1364927580 | 0 | 3343.379 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 16 | 1 | 4885209180 | 3520281600 | 6035.051 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 1 | 4885209180 | 3520281600 | 6700.980 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 16 | 1 | 2465015580 | 1100088000 | 3727.211 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 1 | 2465015580 | 1100088000 | 4392.363 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 17 | 1 | 2898694948 | 1533767368 | 3879.082 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 17 | 1 | 1364927580 | 0 | 2572.695 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 1 | 1364927580 | 0 | 3346.875 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 17 | 1 | 5105226780 | 3740299200 | 6244.984 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 1 | 5105226780 | 3740299200 | 6914.191 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 17 | 1 | 2465015580 | 1100088000 | 3727.176 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 1 | 2465015580 | 1100088000 | 4396.176 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 18 | 1 | 2898694948 | 1533767368 | 3874.562 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 18 | 1 | 1364927580 | 0 | 2572.527 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 1 | 1364927580 | 0 | 3350.340 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 18 | 1 | 5325244380 | 3960316800 | 6454.898 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 1 | 5325244380 | 3960316800 | 7127.445 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 18 | 1 | 2465015580 | 1100088000 | 3727.105 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 1 | 2465015580 | 1100088000 | 4399.520 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 19 | 1 | 2898694948 | 1533767368 | 3857.184 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 19 | 1 | 1364927580 | 0 | 2572.750 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 1 | 1364927580 | 0 | 3353.684 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 19 | 1 | 5545261980 | 4180334400 | 6664.621 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 1 | 5545261980 | 4180334400 | 7340.020 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 19 | 1 | 2465015580 | 1100088000 | 3727.176 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 1 | 2465015580 | 1100088000 | 4402.824 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 20 | 1 | 2898694948 | 1533767368 | 3835.078 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 20 | 1 | 1364927580 | 0 | 2572.664 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 1 | 1364927580 | 0 | 3356.016 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 20 | 1 | 5765279580 | 4400352000 | 6874.418 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 1 | 5765279580 | 4400352000 | 7552.656 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 20 | 1 | 2465015580 | 1100088000 | 3727.070 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 1 | 2465015580 | 1100088000 | 4405.305 |

## Commands

- `symbolic_reuse_serial-a1`: peak RSS `2782.949` MB
- `direct-parallel-a1-t1`: peak RSS `6053.227` MB
- `serial_symbolic_parallel_numeric-a1-t1-atomic`: peak RSS `2572.809` MB
- `parallel_symbolic_reuse-a1-t1-atomic`: peak RSS `2698.664` MB
- `serial_symbolic_parallel_numeric-a1-t1-private_csr`: peak RSS `2887.777` MB
- `parallel_symbolic_reuse-a1-t1-private_csr`: peak RSS `2908.453` MB
- `serial_symbolic_parallel_numeric-a1-t1-lock_guard`: peak RSS `3621.883` MB
- `parallel_symbolic_reuse-a1-t1-lock_guard`: peak RSS `3747.664` MB
- `direct-parallel-a1-t2`: peak RSS `6052.629` MB
- `serial_symbolic_parallel_numeric-a1-t2-atomic`: peak RSS `2572.824` MB
- `parallel_symbolic_reuse-a1-t2-atomic`: peak RSS `3088.793` MB
- `serial_symbolic_parallel_numeric-a1-t2-private_csr`: peak RSS `3097.523` MB
- `parallel_symbolic_reuse-a1-t2-private_csr`: peak RSS `3508.629` MB
- `serial_symbolic_parallel_numeric-a1-t2-lock_guard`: peak RSS `3621.711` MB
- `parallel_symbolic_reuse-a1-t2-lock_guard`: peak RSS `4138.145` MB
- `direct-parallel-a1-t3`: peak RSS `5236.156` MB
- `serial_symbolic_parallel_numeric-a1-t3-atomic`: peak RSS `2572.566` MB
- `parallel_symbolic_reuse-a1-t3-atomic`: peak RSS `3226.887` MB
- `serial_symbolic_parallel_numeric-a1-t3-private_csr`: peak RSS `3307.312` MB
- `parallel_symbolic_reuse-a1-t3-private_csr`: peak RSS `3856.516` MB
- `serial_symbolic_parallel_numeric-a1-t3-lock_guard`: peak RSS `3621.746` MB
- `parallel_symbolic_reuse-a1-t3-lock_guard`: peak RSS `4275.883` MB
- `direct-parallel-a1-t4`: peak RSS `4828.309` MB
- `serial_symbolic_parallel_numeric-a1-t4-atomic`: peak RSS `2572.887` MB
- `parallel_symbolic_reuse-a1-t4-atomic`: peak RSS `3295.699` MB
- `serial_symbolic_parallel_numeric-a1-t4-private_csr`: peak RSS `3517.211` MB
- `parallel_symbolic_reuse-a1-t4-private_csr`: peak RSS `4135.062` MB
- `serial_symbolic_parallel_numeric-a1-t4-lock_guard`: peak RSS `3621.781` MB
- `parallel_symbolic_reuse-a1-t4-lock_guard`: peak RSS `4345.250` MB
- `direct-parallel-a1-t5`: peak RSS `4562.820` MB
- `serial_symbolic_parallel_numeric-a1-t5-atomic`: peak RSS `2572.770` MB
- `parallel_symbolic_reuse-a1-t5-atomic`: peak RSS `3341.617` MB
- `serial_symbolic_parallel_numeric-a1-t5-private_csr`: peak RSS `3727.129` MB
- `parallel_symbolic_reuse-a1-t5-private_csr`: peak RSS `4390.742` MB
- `serial_symbolic_parallel_numeric-a1-t5-lock_guard`: peak RSS `3621.711` MB
- `parallel_symbolic_reuse-a1-t5-lock_guard`: peak RSS `4390.637` MB
- `direct-parallel-a1-t6`: peak RSS `4420.652` MB
- `serial_symbolic_parallel_numeric-a1-t6-atomic`: peak RSS `2572.668` MB
- `parallel_symbolic_reuse-a1-t6-atomic`: peak RSS `3364.688` MB
- `serial_symbolic_parallel_numeric-a1-t6-private_csr`: peak RSS `3937.113` MB
- `parallel_symbolic_reuse-a1-t6-private_csr`: peak RSS `4623.457` MB
- `serial_symbolic_parallel_numeric-a1-t6-lock_guard`: peak RSS `3621.812` MB
- `parallel_symbolic_reuse-a1-t6-lock_guard`: peak RSS `4413.555` MB
- `direct-parallel-a1-t7`: peak RSS `4293.254` MB
- `serial_symbolic_parallel_numeric-a1-t7-atomic`: peak RSS `2572.590` MB
- `parallel_symbolic_reuse-a1-t7-atomic`: peak RSS `3283.234` MB
- `serial_symbolic_parallel_numeric-a1-t7-private_csr`: peak RSS `4146.770` MB
- `parallel_symbolic_reuse-a1-t7-private_csr`: peak RSS `4752.074` MB
- `serial_symbolic_parallel_numeric-a1-t7-lock_guard`: peak RSS `3621.797` MB
- `parallel_symbolic_reuse-a1-t7-lock_guard`: peak RSS `4332.598` MB
- `direct-parallel-a1-t8`: peak RSS `4203.109` MB
- `serial_symbolic_parallel_numeric-a1-t8-atomic`: peak RSS `2572.773` MB
- `parallel_symbolic_reuse-a1-t8-atomic`: peak RSS `3299.434` MB
- `serial_symbolic_parallel_numeric-a1-t8-private_csr`: peak RSS `4356.574` MB
- `parallel_symbolic_reuse-a1-t8-private_csr`: peak RSS `4978.512` MB
- `serial_symbolic_parallel_numeric-a1-t8-lock_guard`: peak RSS `3621.750` MB
- `parallel_symbolic_reuse-a1-t8-lock_guard`: peak RSS `4348.832` MB
- `direct-parallel-a1-t9`: peak RSS `4134.211` MB
- `serial_symbolic_parallel_numeric-a1-t9-atomic`: peak RSS `2572.527` MB
- `parallel_symbolic_reuse-a1-t9-atomic`: peak RSS `3309.281` MB
- `serial_symbolic_parallel_numeric-a1-t9-private_csr`: peak RSS `4566.469` MB
- `parallel_symbolic_reuse-a1-t9-private_csr`: peak RSS `5198.305` MB
- `serial_symbolic_parallel_numeric-a1-t9-lock_guard`: peak RSS `3621.883` MB
- `parallel_symbolic_reuse-a1-t9-lock_guard`: peak RSS `4358.672` MB
- `direct-parallel-a1-t10`: peak RSS `4087.383` MB
- `serial_symbolic_parallel_numeric-a1-t10-atomic`: peak RSS `2572.535` MB
- `parallel_symbolic_reuse-a1-t10-atomic`: peak RSS `3316.812` MB
- `serial_symbolic_parallel_numeric-a1-t10-private_csr`: peak RSS `4776.086` MB
- `parallel_symbolic_reuse-a1-t10-private_csr`: peak RSS `5415.133` MB
- `serial_symbolic_parallel_numeric-a1-t10-lock_guard`: peak RSS `3726.996` MB
- `parallel_symbolic_reuse-a1-t10-lock_guard`: peak RSS `4365.926` MB
- `direct-parallel-a1-t11`: peak RSS `4045.098` MB
- `serial_symbolic_parallel_numeric-a1-t11-atomic`: peak RSS `2572.574` MB
- `parallel_symbolic_reuse-a1-t11-atomic`: peak RSS `3427.855` MB
- `serial_symbolic_parallel_numeric-a1-t11-private_csr`: peak RSS `4985.953` MB
- `parallel_symbolic_reuse-a1-t11-private_csr`: peak RSS `5735.512` MB
- `serial_symbolic_parallel_numeric-a1-t11-lock_guard`: peak RSS `3727.055` MB
- `parallel_symbolic_reuse-a1-t11-lock_guard`: peak RSS `4476.824` MB
- `direct-parallel-a1-t12`: peak RSS `4012.711` MB
- `serial_symbolic_parallel_numeric-a1-t12-atomic`: peak RSS `2572.664` MB
- `parallel_symbolic_reuse-a1-t12-atomic`: peak RSS `3327.590` MB
- `serial_symbolic_parallel_numeric-a1-t12-private_csr`: peak RSS `5195.699` MB
- `parallel_symbolic_reuse-a1-t12-private_csr`: peak RSS `5845.973` MB
- `serial_symbolic_parallel_numeric-a1-t12-lock_guard`: peak RSS `3727.074` MB
- `parallel_symbolic_reuse-a1-t12-lock_guard`: peak RSS `4377.504` MB
- `direct-parallel-a1-t13`: peak RSS `3978.238` MB
- `serial_symbolic_parallel_numeric-a1-t13-atomic`: peak RSS `2572.770` MB
- `parallel_symbolic_reuse-a1-t13-atomic`: peak RSS `3332.684` MB
- `serial_symbolic_parallel_numeric-a1-t13-private_csr`: peak RSS `5405.645` MB
- `parallel_symbolic_reuse-a1-t13-private_csr`: peak RSS `6060.059` MB
- `serial_symbolic_parallel_numeric-a1-t13-lock_guard`: peak RSS `3727.031` MB
- `parallel_symbolic_reuse-a1-t13-lock_guard`: peak RSS `4381.312` MB
- `direct-parallel-a1-t14`: peak RSS `3950.793` MB
- `serial_symbolic_parallel_numeric-a1-t14-atomic`: peak RSS `2572.578` MB
- `parallel_symbolic_reuse-a1-t14-atomic`: peak RSS `3336.113` MB
- `serial_symbolic_parallel_numeric-a1-t14-private_csr`: peak RSS `5615.484` MB
- `parallel_symbolic_reuse-a1-t14-private_csr`: peak RSS `6273.711` MB
- `serial_symbolic_parallel_numeric-a1-t14-lock_guard`: peak RSS `3727.074` MB
- `parallel_symbolic_reuse-a1-t14-lock_guard`: peak RSS `4385.805` MB
- `direct-parallel-a1-t15`: peak RSS `3926.668` MB
- `serial_symbolic_parallel_numeric-a1-t15-atomic`: peak RSS `2572.832` MB
- `parallel_symbolic_reuse-a1-t15-atomic`: peak RSS `3339.461` MB
- `serial_symbolic_parallel_numeric-a1-t15-private_csr`: peak RSS `5825.230` MB
- `parallel_symbolic_reuse-a1-t15-private_csr`: peak RSS `6486.797` MB
- `serial_symbolic_parallel_numeric-a1-t15-lock_guard`: peak RSS `3726.980` MB
- `parallel_symbolic_reuse-a1-t15-lock_guard`: peak RSS `4388.477` MB
- `direct-parallel-a1-t16`: peak RSS `3900.695` MB
- `serial_symbolic_parallel_numeric-a1-t16-atomic`: peak RSS `2572.703` MB
- `parallel_symbolic_reuse-a1-t16-atomic`: peak RSS `3343.379` MB
- `serial_symbolic_parallel_numeric-a1-t16-private_csr`: peak RSS `6035.051` MB
- `parallel_symbolic_reuse-a1-t16-private_csr`: peak RSS `6700.980` MB
- `serial_symbolic_parallel_numeric-a1-t16-lock_guard`: peak RSS `3727.211` MB
- `parallel_symbolic_reuse-a1-t16-lock_guard`: peak RSS `4392.363` MB
- `direct-parallel-a1-t17`: peak RSS `3879.082` MB
- `serial_symbolic_parallel_numeric-a1-t17-atomic`: peak RSS `2572.695` MB
- `parallel_symbolic_reuse-a1-t17-atomic`: peak RSS `3346.875` MB
- `serial_symbolic_parallel_numeric-a1-t17-private_csr`: peak RSS `6244.984` MB
- `parallel_symbolic_reuse-a1-t17-private_csr`: peak RSS `6914.191` MB
- `serial_symbolic_parallel_numeric-a1-t17-lock_guard`: peak RSS `3727.176` MB
- `parallel_symbolic_reuse-a1-t17-lock_guard`: peak RSS `4396.176` MB
- `direct-parallel-a1-t18`: peak RSS `3874.562` MB
- `serial_symbolic_parallel_numeric-a1-t18-atomic`: peak RSS `2572.527` MB
- `parallel_symbolic_reuse-a1-t18-atomic`: peak RSS `3350.340` MB
- `serial_symbolic_parallel_numeric-a1-t18-private_csr`: peak RSS `6454.898` MB
- `parallel_symbolic_reuse-a1-t18-private_csr`: peak RSS `7127.445` MB
- `serial_symbolic_parallel_numeric-a1-t18-lock_guard`: peak RSS `3727.105` MB
- `parallel_symbolic_reuse-a1-t18-lock_guard`: peak RSS `4399.520` MB
- `direct-parallel-a1-t19`: peak RSS `3857.184` MB
- `serial_symbolic_parallel_numeric-a1-t19-atomic`: peak RSS `2572.750` MB
- `parallel_symbolic_reuse-a1-t19-atomic`: peak RSS `3353.684` MB
- `serial_symbolic_parallel_numeric-a1-t19-private_csr`: peak RSS `6664.621` MB
- `parallel_symbolic_reuse-a1-t19-private_csr`: peak RSS `7340.020` MB
- `serial_symbolic_parallel_numeric-a1-t19-lock_guard`: peak RSS `3727.176` MB
- `parallel_symbolic_reuse-a1-t19-lock_guard`: peak RSS `4402.824` MB
- `direct-parallel-a1-t20`: peak RSS `3835.078` MB
- `serial_symbolic_parallel_numeric-a1-t20-atomic`: peak RSS `2572.664` MB
- `parallel_symbolic_reuse-a1-t20-atomic`: peak RSS `3356.016` MB
- `serial_symbolic_parallel_numeric-a1-t20-private_csr`: peak RSS `6874.418` MB
- `parallel_symbolic_reuse-a1-t20-private_csr`: peak RSS `7552.656` MB
- `serial_symbolic_parallel_numeric-a1-t20-lock_guard`: peak RSS `3727.070` MB
- `parallel_symbolic_reuse-a1-t20-lock_guard`: peak RSS `4405.305` MB
