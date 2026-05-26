# Isolated Symbolic Memory Evaluation

Each row was measured in a fresh subprocess. On POSIX, `isolated_peak_rss_mb` is `ru_maxrss`; on Windows, it is the OS-observed peak working set fallback and `isolated_memory_metric` records that distinction.
The legacy report label `isolated peak RSS` is retained for schema continuity, but Windows rows must be read with the metric field.

## Rows

| strategy | mode | backend | threads | assemblies | estimated peak bytes | delta bytes | isolated peak MB | metric |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 1 | 1364927580 | 0 | 2311.043 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 1 | 1 | 2898694948 | 1533767368 | 5584.793 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2311.090 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | 1364927580 | 0 | 2311.266 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 2 | 1 | 2898694948 | 1533767368 | 5584.211 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 2311.164 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | 1364927580 | 0 | 2311.422 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 3 | 1 | 2898694948 | 1533767368 | 4768.074 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 2311.148 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | 1364927580 | 0 | 2312.234 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 4 | 1 | 2898694948 | 1533767368 | 4360.324 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 2311.215 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | 1364927580 | 0 | 2315.070 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 5 | 1 | 2898694948 | 1533767368 | 4095.332 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 2311.152 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | 1364927580 | 0 | 2313.375 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 6 | 1 | 2898694948 | 1533767368 | 3953.141 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 2311.250 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | 1364927580 | 0 | 2315.703 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 7 | 1 | 2898694948 | 1533767368 | 3825.777 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 2311.211 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | 1364927580 | 0 | 2317.707 | `windows_peak_working_set` |
| `direct_no_symbolic_background` | `direct_no_symbolic_parallel` | `none` | 8 | 1 | 2898694948 | 1533767368 | 3735.793 | `windows_peak_working_set` |
| `serial_symbolic_parallel_numeric` | `serial_symbolic_parallel_numeric` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 2311.230 | `windows_peak_working_set` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | 1364927580 | 0 | 2314.715 | `windows_peak_working_set` |

## Commands

- `symbolic_reuse_serial-a1`: peak `2311.043` MB via `windows_peak_working_set`
- `direct-parallel-a1-t1`: peak `5584.793` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t1-atomic`: peak `2311.090` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t1-atomic`: peak `2311.266` MB via `windows_peak_working_set`
- `direct-parallel-a1-t2`: peak `5584.211` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t2-atomic`: peak `2311.164` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t2-atomic`: peak `2311.422` MB via `windows_peak_working_set`
- `direct-parallel-a1-t3`: peak `4768.074` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t3-atomic`: peak `2311.148` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t3-atomic`: peak `2312.234` MB via `windows_peak_working_set`
- `direct-parallel-a1-t4`: peak `4360.324` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t4-atomic`: peak `2311.215` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t4-atomic`: peak `2315.070` MB via `windows_peak_working_set`
- `direct-parallel-a1-t5`: peak `4095.332` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t5-atomic`: peak `2311.152` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t5-atomic`: peak `2313.375` MB via `windows_peak_working_set`
- `direct-parallel-a1-t6`: peak `3953.141` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t6-atomic`: peak `2311.250` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t6-atomic`: peak `2315.703` MB via `windows_peak_working_set`
- `direct-parallel-a1-t7`: peak `3825.777` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t7-atomic`: peak `2311.211` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t7-atomic`: peak `2317.707` MB via `windows_peak_working_set`
- `direct-parallel-a1-t8`: peak `3735.793` MB via `windows_peak_working_set`
- `serial_symbolic_parallel_numeric-a1-t8-atomic`: peak `2311.230` MB via `windows_peak_working_set`
- `parallel_symbolic_reuse-a1-t8-atomic`: peak `2314.715` MB via `windows_peak_working_set`
