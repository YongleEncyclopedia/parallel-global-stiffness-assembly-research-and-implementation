# Isolated Symbolic Memory Evaluation

Each row was measured in a fresh subprocess. `isolated_peak_rss_mb` is the OS-observed peak RSS for that single command.

## Rows

| strategy | mode | backend | threads | assemblies | estimated peak bytes | delta bytes | isolated peak RSS MB |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 1 | 1364927580 | 0 | 2783.062 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 1 | 1 | 2898694948 | 1533767368 | 6053.281 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2572.707 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2698.664 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 1 | 1 | 1584945180 | 220017600 | 2782.512 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 1 | 1584945180 | 220017600 | 2908.461 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 1 | 1 | 2465015580 | 1100088000 | 3621.965 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 1 | 2465015580 | 1100088000 | 3747.605 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 2 | 1 | 2898694948 | 1533767368 | 6052.316 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 2572.578 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 3088.930 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 2 | 1 | 1804962780 | 440035200 | 2992.281 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 1 | 1804962780 | 440035200 | 3508.535 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 2 | 1 | 2465015580 | 1100088000 | 3621.719 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 1 | 2465015580 | 1100088000 | 4138.180 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 3 | 1 | 2898694948 | 1533767368 | 5236.062 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 2572.566 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 3226.797 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 3 | 1 | 2024980380 | 660052800 | 3202.215 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 1 | 2024980380 | 660052800 | 3856.344 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 3 | 1 | 2465015580 | 1100088000 | 3621.711 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 1 | 2465015580 | 1100088000 | 4275.891 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 4 | 1 | 2898694948 | 1533767368 | 4828.215 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 2572.551 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 3085.684 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 4 | 1 | 2244997980 | 880070400 | 3412.000 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 1 | 2244997980 | 880070400 | 4135.285 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 4 | 1 | 2465015580 | 1100088000 | 3621.871 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 1 | 2465015580 | 1100088000 | 4344.836 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 5 | 1 | 2898694948 | 1533767368 | 4563.332 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 2572.621 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 3131.688 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 5 | 1 | 2465015580 | 1100088000 | 3621.750 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 1 | 2465015580 | 1100088000 | 4390.664 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 5 | 1 | 2465015580 | 1100088000 | 3621.703 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 1 | 2465015580 | 1100088000 | 4390.969 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 6 | 1 | 2898694948 | 1533767368 | 4420.551 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 2572.633 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 3154.473 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 6 | 1 | 2685033180 | 1320105600 | 3831.660 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 1 | 2685033180 | 1320105600 | 4623.070 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 6 | 1 | 2465015580 | 1100088000 | 3621.801 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 1 | 2465015580 | 1100088000 | 4413.758 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 7 | 1 | 2898694948 | 1533767368 | 4293.445 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 2572.566 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 3178.609 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 7 | 1 | 2905050780 | 1540123200 | 4041.348 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 1 | 2905050780 | 1540123200 | 4751.965 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 7 | 1 | 2465015580 | 1100088000 | 3621.820 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 1 | 2465015580 | 1100088000 | 4332.535 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 8 | 1 | 2898694948 | 1533767368 | 4202.844 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 2572.480 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 3194.652 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 8 | 1 | 3125068380 | 1760140800 | 4251.449 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 1 | 3125068380 | 1760140800 | 4978.031 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 8 | 1 | 2465015580 | 1100088000 | 3621.816 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 1 | 2465015580 | 1100088000 | 4348.906 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 9 | 1 | 2898694948 | 1533767368 | 4133.922 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 9 | 1 | 1364927580 | 0 | 2572.664 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 1 | 1364927580 | 0 | 3204.676 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 9 | 1 | 3345085980 | 1980158400 | 4461.016 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 1 | 3345085980 | 1980158400 | 5197.703 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 9 | 1 | 2465015580 | 1100088000 | 3621.910 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 1 | 2465015580 | 1100088000 | 4358.777 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 10 | 1 | 2898694948 | 1533767368 | 4087.746 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 10 | 1 | 1364927580 | 0 | 2572.551 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 1 | 1364927580 | 0 | 3317.340 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 10 | 1 | 3565103580 | 2200176000 | 4776.078 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 1 | 3565103580 | 2200176000 | 5415.164 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 10 | 1 | 2465015580 | 1100088000 | 3621.910 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 1 | 2465015580 | 1100088000 | 4366.125 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 11 | 1 | 2898694948 | 1533767368 | 4045.234 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 11 | 1 | 1364927580 | 0 | 2572.492 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 1 | 1364927580 | 0 | 3427.656 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 11 | 1 | 3785121180 | 2420193600 | 4986.008 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 1 | 3785121180 | 2420193600 | 5735.613 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 11 | 1 | 2465015580 | 1100088000 | 3621.809 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 1 | 2465015580 | 1100088000 | 4476.984 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 12 | 1 | 2898694948 | 1533767368 | 4013.012 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 12 | 1 | 1364927580 | 0 | 2572.527 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 1 | 1364927580 | 0 | 3328.027 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 12 | 1 | 4005138780 | 2640211200 | 5195.926 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 1 | 4005138780 | 2640211200 | 5845.977 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 12 | 1 | 2465015580 | 1100088000 | 3621.797 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 1 | 2465015580 | 1100088000 | 4376.543 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 13 | 1 | 2898694948 | 1533767368 | 3978.543 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 13 | 1 | 1364927580 | 0 | 2572.688 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 1 | 1364927580 | 0 | 3332.059 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 13 | 1 | 4225156380 | 2860228800 | 5405.711 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 1 | 4225156380 | 2860228800 | 6060.184 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 13 | 1 | 2465015580 | 1100088000 | 3621.805 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 1 | 2465015580 | 1100088000 | 4381.746 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 14 | 1 | 2898694948 | 1533767368 | 3951.215 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 14 | 1 | 1364927580 | 0 | 2572.578 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 1 | 1364927580 | 0 | 3336.129 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 14 | 1 | 4445173980 | 3080246400 | 5615.430 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 1 | 4445173980 | 3080246400 | 6273.875 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 14 | 1 | 2465015580 | 1100088000 | 3621.918 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 1 | 2465015580 | 1100088000 | 4385.754 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 15 | 1 | 2898694948 | 1533767368 | 3927.078 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 15 | 1 | 1364927580 | 0 | 2572.812 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 1 | 1364927580 | 0 | 3339.594 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 15 | 1 | 4665191580 | 3300264000 | 5825.203 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 1 | 4665191580 | 3300264000 | 6486.973 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 15 | 1 | 2465015580 | 1100088000 | 3621.762 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 1 | 2465015580 | 1100088000 | 4388.836 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 16 | 1 | 2898694948 | 1533767368 | 3900.594 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 16 | 1 | 1364927580 | 0 | 2572.758 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 1 | 1364927580 | 0 | 3343.527 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 16 | 1 | 4885209180 | 3520281600 | 6035.168 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 1 | 4885209180 | 3520281600 | 6700.438 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 16 | 1 | 2465015580 | 1100088000 | 3621.938 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 1 | 2465015580 | 1100088000 | 4392.219 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 17 | 1 | 2898694948 | 1533767368 | 3878.500 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 17 | 1 | 1364927580 | 0 | 2572.805 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 1 | 1364927580 | 0 | 3346.965 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 17 | 1 | 5105226780 | 3740299200 | 6245.105 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 1 | 5105226780 | 3740299200 | 6914.422 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 17 | 1 | 2465015580 | 1100088000 | 3621.797 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 1 | 2465015580 | 1100088000 | 4395.848 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 18 | 1 | 2898694948 | 1533767368 | 3874.254 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 18 | 1 | 1364927580 | 0 | 2572.754 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 1 | 1364927580 | 0 | 3350.312 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 18 | 1 | 5325244380 | 3960316800 | 6454.859 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 1 | 5325244380 | 3960316800 | 7127.547 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 18 | 1 | 2465015580 | 1100088000 | 3621.828 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 1 | 2465015580 | 1100088000 | 4399.215 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 19 | 1 | 2898694948 | 1533767368 | 3857.355 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 19 | 1 | 1364927580 | 0 | 2572.949 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 1 | 1364927580 | 0 | 3353.465 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 19 | 1 | 5545261980 | 4180334400 | 6664.695 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 1 | 5545261980 | 4180334400 | 7340.340 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 19 | 1 | 2465015580 | 1100088000 | 3621.973 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 1 | 2465015580 | 1100088000 | 4402.758 |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 20 | 1 | 2898694948 | 1533767368 | 3835.168 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 20 | 1 | 1364927580 | 0 | 2572.672 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 1 | 1364927580 | 0 | 3356.348 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_private_csr` | 20 | 1 | 5765279580 | 4400352000 | 6874.668 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 1 | 5765279580 | 4400352000 | 7553.121 |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_lock_guard` | 20 | 1 | 2465015580 | 1100088000 | 3621.750 |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 1 | 2465015580 | 1100088000 | 4404.859 |

## Commands

- `symbolic_reuse_serial-a1`: peak RSS `2783.062` MB
- `direct-parallel-a1-t1`: peak RSS `6053.281` MB
- `serial_symbolic_parallel_numeric-a1-t1-atomic`: peak RSS `2572.707` MB
- `parallel_symbolic_reuse-a1-t1-atomic`: peak RSS `2698.664` MB
- `serial_symbolic_parallel_numeric-a1-t1-private_csr`: peak RSS `2782.512` MB
- `parallel_symbolic_reuse-a1-t1-private_csr`: peak RSS `2908.461` MB
- `serial_symbolic_parallel_numeric-a1-t1-lock_guard`: peak RSS `3621.965` MB
- `parallel_symbolic_reuse-a1-t1-lock_guard`: peak RSS `3747.605` MB
- `direct-parallel-a1-t2`: peak RSS `6052.316` MB
- `serial_symbolic_parallel_numeric-a1-t2-atomic`: peak RSS `2572.578` MB
- `parallel_symbolic_reuse-a1-t2-atomic`: peak RSS `3088.930` MB
- `serial_symbolic_parallel_numeric-a1-t2-private_csr`: peak RSS `2992.281` MB
- `parallel_symbolic_reuse-a1-t2-private_csr`: peak RSS `3508.535` MB
- `serial_symbolic_parallel_numeric-a1-t2-lock_guard`: peak RSS `3621.719` MB
- `parallel_symbolic_reuse-a1-t2-lock_guard`: peak RSS `4138.180` MB
- `direct-parallel-a1-t3`: peak RSS `5236.062` MB
- `serial_symbolic_parallel_numeric-a1-t3-atomic`: peak RSS `2572.566` MB
- `parallel_symbolic_reuse-a1-t3-atomic`: peak RSS `3226.797` MB
- `serial_symbolic_parallel_numeric-a1-t3-private_csr`: peak RSS `3202.215` MB
- `parallel_symbolic_reuse-a1-t3-private_csr`: peak RSS `3856.344` MB
- `serial_symbolic_parallel_numeric-a1-t3-lock_guard`: peak RSS `3621.711` MB
- `parallel_symbolic_reuse-a1-t3-lock_guard`: peak RSS `4275.891` MB
- `direct-parallel-a1-t4`: peak RSS `4828.215` MB
- `serial_symbolic_parallel_numeric-a1-t4-atomic`: peak RSS `2572.551` MB
- `parallel_symbolic_reuse-a1-t4-atomic`: peak RSS `3085.684` MB
- `serial_symbolic_parallel_numeric-a1-t4-private_csr`: peak RSS `3412.000` MB
- `parallel_symbolic_reuse-a1-t4-private_csr`: peak RSS `4135.285` MB
- `serial_symbolic_parallel_numeric-a1-t4-lock_guard`: peak RSS `3621.871` MB
- `parallel_symbolic_reuse-a1-t4-lock_guard`: peak RSS `4344.836` MB
- `direct-parallel-a1-t5`: peak RSS `4563.332` MB
- `serial_symbolic_parallel_numeric-a1-t5-atomic`: peak RSS `2572.621` MB
- `parallel_symbolic_reuse-a1-t5-atomic`: peak RSS `3131.688` MB
- `serial_symbolic_parallel_numeric-a1-t5-private_csr`: peak RSS `3621.750` MB
- `parallel_symbolic_reuse-a1-t5-private_csr`: peak RSS `4390.664` MB
- `serial_symbolic_parallel_numeric-a1-t5-lock_guard`: peak RSS `3621.703` MB
- `parallel_symbolic_reuse-a1-t5-lock_guard`: peak RSS `4390.969` MB
- `direct-parallel-a1-t6`: peak RSS `4420.551` MB
- `serial_symbolic_parallel_numeric-a1-t6-atomic`: peak RSS `2572.633` MB
- `parallel_symbolic_reuse-a1-t6-atomic`: peak RSS `3154.473` MB
- `serial_symbolic_parallel_numeric-a1-t6-private_csr`: peak RSS `3831.660` MB
- `parallel_symbolic_reuse-a1-t6-private_csr`: peak RSS `4623.070` MB
- `serial_symbolic_parallel_numeric-a1-t6-lock_guard`: peak RSS `3621.801` MB
- `parallel_symbolic_reuse-a1-t6-lock_guard`: peak RSS `4413.758` MB
- `direct-parallel-a1-t7`: peak RSS `4293.445` MB
- `serial_symbolic_parallel_numeric-a1-t7-atomic`: peak RSS `2572.566` MB
- `parallel_symbolic_reuse-a1-t7-atomic`: peak RSS `3178.609` MB
- `serial_symbolic_parallel_numeric-a1-t7-private_csr`: peak RSS `4041.348` MB
- `parallel_symbolic_reuse-a1-t7-private_csr`: peak RSS `4751.965` MB
- `serial_symbolic_parallel_numeric-a1-t7-lock_guard`: peak RSS `3621.820` MB
- `parallel_symbolic_reuse-a1-t7-lock_guard`: peak RSS `4332.535` MB
- `direct-parallel-a1-t8`: peak RSS `4202.844` MB
- `serial_symbolic_parallel_numeric-a1-t8-atomic`: peak RSS `2572.480` MB
- `parallel_symbolic_reuse-a1-t8-atomic`: peak RSS `3194.652` MB
- `serial_symbolic_parallel_numeric-a1-t8-private_csr`: peak RSS `4251.449` MB
- `parallel_symbolic_reuse-a1-t8-private_csr`: peak RSS `4978.031` MB
- `serial_symbolic_parallel_numeric-a1-t8-lock_guard`: peak RSS `3621.816` MB
- `parallel_symbolic_reuse-a1-t8-lock_guard`: peak RSS `4348.906` MB
- `direct-parallel-a1-t9`: peak RSS `4133.922` MB
- `serial_symbolic_parallel_numeric-a1-t9-atomic`: peak RSS `2572.664` MB
- `parallel_symbolic_reuse-a1-t9-atomic`: peak RSS `3204.676` MB
- `serial_symbolic_parallel_numeric-a1-t9-private_csr`: peak RSS `4461.016` MB
- `parallel_symbolic_reuse-a1-t9-private_csr`: peak RSS `5197.703` MB
- `serial_symbolic_parallel_numeric-a1-t9-lock_guard`: peak RSS `3621.910` MB
- `parallel_symbolic_reuse-a1-t9-lock_guard`: peak RSS `4358.777` MB
- `direct-parallel-a1-t10`: peak RSS `4087.746` MB
- `serial_symbolic_parallel_numeric-a1-t10-atomic`: peak RSS `2572.551` MB
- `parallel_symbolic_reuse-a1-t10-atomic`: peak RSS `3317.340` MB
- `serial_symbolic_parallel_numeric-a1-t10-private_csr`: peak RSS `4776.078` MB
- `parallel_symbolic_reuse-a1-t10-private_csr`: peak RSS `5415.164` MB
- `serial_symbolic_parallel_numeric-a1-t10-lock_guard`: peak RSS `3621.910` MB
- `parallel_symbolic_reuse-a1-t10-lock_guard`: peak RSS `4366.125` MB
- `direct-parallel-a1-t11`: peak RSS `4045.234` MB
- `serial_symbolic_parallel_numeric-a1-t11-atomic`: peak RSS `2572.492` MB
- `parallel_symbolic_reuse-a1-t11-atomic`: peak RSS `3427.656` MB
- `serial_symbolic_parallel_numeric-a1-t11-private_csr`: peak RSS `4986.008` MB
- `parallel_symbolic_reuse-a1-t11-private_csr`: peak RSS `5735.613` MB
- `serial_symbolic_parallel_numeric-a1-t11-lock_guard`: peak RSS `3621.809` MB
- `parallel_symbolic_reuse-a1-t11-lock_guard`: peak RSS `4476.984` MB
- `direct-parallel-a1-t12`: peak RSS `4013.012` MB
- `serial_symbolic_parallel_numeric-a1-t12-atomic`: peak RSS `2572.527` MB
- `parallel_symbolic_reuse-a1-t12-atomic`: peak RSS `3328.027` MB
- `serial_symbolic_parallel_numeric-a1-t12-private_csr`: peak RSS `5195.926` MB
- `parallel_symbolic_reuse-a1-t12-private_csr`: peak RSS `5845.977` MB
- `serial_symbolic_parallel_numeric-a1-t12-lock_guard`: peak RSS `3621.797` MB
- `parallel_symbolic_reuse-a1-t12-lock_guard`: peak RSS `4376.543` MB
- `direct-parallel-a1-t13`: peak RSS `3978.543` MB
- `serial_symbolic_parallel_numeric-a1-t13-atomic`: peak RSS `2572.688` MB
- `parallel_symbolic_reuse-a1-t13-atomic`: peak RSS `3332.059` MB
- `serial_symbolic_parallel_numeric-a1-t13-private_csr`: peak RSS `5405.711` MB
- `parallel_symbolic_reuse-a1-t13-private_csr`: peak RSS `6060.184` MB
- `serial_symbolic_parallel_numeric-a1-t13-lock_guard`: peak RSS `3621.805` MB
- `parallel_symbolic_reuse-a1-t13-lock_guard`: peak RSS `4381.746` MB
- `direct-parallel-a1-t14`: peak RSS `3951.215` MB
- `serial_symbolic_parallel_numeric-a1-t14-atomic`: peak RSS `2572.578` MB
- `parallel_symbolic_reuse-a1-t14-atomic`: peak RSS `3336.129` MB
- `serial_symbolic_parallel_numeric-a1-t14-private_csr`: peak RSS `5615.430` MB
- `parallel_symbolic_reuse-a1-t14-private_csr`: peak RSS `6273.875` MB
- `serial_symbolic_parallel_numeric-a1-t14-lock_guard`: peak RSS `3621.918` MB
- `parallel_symbolic_reuse-a1-t14-lock_guard`: peak RSS `4385.754` MB
- `direct-parallel-a1-t15`: peak RSS `3927.078` MB
- `serial_symbolic_parallel_numeric-a1-t15-atomic`: peak RSS `2572.812` MB
- `parallel_symbolic_reuse-a1-t15-atomic`: peak RSS `3339.594` MB
- `serial_symbolic_parallel_numeric-a1-t15-private_csr`: peak RSS `5825.203` MB
- `parallel_symbolic_reuse-a1-t15-private_csr`: peak RSS `6486.973` MB
- `serial_symbolic_parallel_numeric-a1-t15-lock_guard`: peak RSS `3621.762` MB
- `parallel_symbolic_reuse-a1-t15-lock_guard`: peak RSS `4388.836` MB
- `direct-parallel-a1-t16`: peak RSS `3900.594` MB
- `serial_symbolic_parallel_numeric-a1-t16-atomic`: peak RSS `2572.758` MB
- `parallel_symbolic_reuse-a1-t16-atomic`: peak RSS `3343.527` MB
- `serial_symbolic_parallel_numeric-a1-t16-private_csr`: peak RSS `6035.168` MB
- `parallel_symbolic_reuse-a1-t16-private_csr`: peak RSS `6700.438` MB
- `serial_symbolic_parallel_numeric-a1-t16-lock_guard`: peak RSS `3621.938` MB
- `parallel_symbolic_reuse-a1-t16-lock_guard`: peak RSS `4392.219` MB
- `direct-parallel-a1-t17`: peak RSS `3878.500` MB
- `serial_symbolic_parallel_numeric-a1-t17-atomic`: peak RSS `2572.805` MB
- `parallel_symbolic_reuse-a1-t17-atomic`: peak RSS `3346.965` MB
- `serial_symbolic_parallel_numeric-a1-t17-private_csr`: peak RSS `6245.105` MB
- `parallel_symbolic_reuse-a1-t17-private_csr`: peak RSS `6914.422` MB
- `serial_symbolic_parallel_numeric-a1-t17-lock_guard`: peak RSS `3621.797` MB
- `parallel_symbolic_reuse-a1-t17-lock_guard`: peak RSS `4395.848` MB
- `direct-parallel-a1-t18`: peak RSS `3874.254` MB
- `serial_symbolic_parallel_numeric-a1-t18-atomic`: peak RSS `2572.754` MB
- `parallel_symbolic_reuse-a1-t18-atomic`: peak RSS `3350.312` MB
- `serial_symbolic_parallel_numeric-a1-t18-private_csr`: peak RSS `6454.859` MB
- `parallel_symbolic_reuse-a1-t18-private_csr`: peak RSS `7127.547` MB
- `serial_symbolic_parallel_numeric-a1-t18-lock_guard`: peak RSS `3621.828` MB
- `parallel_symbolic_reuse-a1-t18-lock_guard`: peak RSS `4399.215` MB
- `direct-parallel-a1-t19`: peak RSS `3857.355` MB
- `serial_symbolic_parallel_numeric-a1-t19-atomic`: peak RSS `2572.949` MB
- `parallel_symbolic_reuse-a1-t19-atomic`: peak RSS `3353.465` MB
- `serial_symbolic_parallel_numeric-a1-t19-private_csr`: peak RSS `6664.695` MB
- `parallel_symbolic_reuse-a1-t19-private_csr`: peak RSS `7340.340` MB
- `serial_symbolic_parallel_numeric-a1-t19-lock_guard`: peak RSS `3621.973` MB
- `parallel_symbolic_reuse-a1-t19-lock_guard`: peak RSS `4402.758` MB
- `direct-parallel-a1-t20`: peak RSS `3835.168` MB
- `serial_symbolic_parallel_numeric-a1-t20-atomic`: peak RSS `2572.672` MB
- `parallel_symbolic_reuse-a1-t20-atomic`: peak RSS `3356.348` MB
- `serial_symbolic_parallel_numeric-a1-t20-private_csr`: peak RSS `6874.668` MB
- `parallel_symbolic_reuse-a1-t20-private_csr`: peak RSS `7553.121` MB
- `serial_symbolic_parallel_numeric-a1-t20-lock_guard`: peak RSS `3621.750` MB
- `parallel_symbolic_reuse-a1-t20-lock_guard`: peak RSS `4404.859` MB
