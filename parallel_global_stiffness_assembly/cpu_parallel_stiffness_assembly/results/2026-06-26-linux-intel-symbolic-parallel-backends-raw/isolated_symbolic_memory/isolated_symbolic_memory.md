# Isolated Symbolic Memory Evaluation

Each row was measured in a fresh subprocess. On POSIX, `isolated_peak_rss_mb` is `ru_maxrss`; on Windows, it is the OS-observed peak working set fallback and `isolated_memory_metric` records that distinction.
The legacy report label `isolated peak RSS` is retained for schema continuity, but Windows rows must be read with the metric field.

## Rows

| strategy | mode | backend | threads | assemblies | estimated peak bytes | delta bytes | isolated peak MB | metric |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 1 | 1364927580 | 0 | 2890.457 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | 1514680188 | 149752608 | 3120.992 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 1 | 1514680188 | 149752608 | 3225.945 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 1 | 1514680188 | 149752608 | 3960.254 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 1 | 1 | 1514680188 | 149752608 | 3016.008 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 1 | 1 | 1514680188 | 149752608 | 4956.168 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | 1514680188 | 149752608 | 3340.359 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 1 | 1514680188 | 149752608 | 3692.773 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 1 | 1514680188 | 149752608 | 4322.266 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 2 | 1 | 1514680188 | 149752608 | 3340.367 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 2 | 1 | 1514680188 | 149752608 | 5777.938 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | 1514680188 | 149752608 | 3478.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 1 | 1514680188 | 149752608 | 4040.605 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 1 | 1514680188 | 149752608 | 4460.293 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 3 | 1 | 1514680188 | 149752608 | 3478.180 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 3 | 1 | 1514680188 | 149752608 | 5609.445 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | 1514680188 | 149752608 | 3442.281 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 1 | 1514680188 | 149752608 | 4319.574 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 1 | 1514680188 | 149752608 | 4529.402 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 4 | 1 | 1514680188 | 149752608 | 3547.164 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 4 | 1 | 1514680188 | 149752608 | 5421.164 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | 1514680188 | 149752608 | 3487.891 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 1 | 1514680188 | 149752608 | 4575.137 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 1 | 1514680188 | 149752608 | 4575.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 5 | 1 | 1514680188 | 149752608 | 3593.031 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 5 | 1 | 1514680188 | 149752608 | 5359.371 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | 1514680188 | 149752608 | 3511.160 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 1 | 1514680188 | 149752608 | 4807.949 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 1 | 1514680188 | 149752608 | 4598.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 6 | 1 | 1514680188 | 149752608 | 3511.035 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 6 | 1 | 1514680188 | 149752608 | 5346.445 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | 1514680188 | 149752608 | 3535.211 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 1 | 1514680188 | 149752608 | 5042.016 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 1 | 1514680188 | 149752608 | 4622.324 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 7 | 1 | 1514680188 | 149752608 | 3535.367 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 7 | 1 | 1514680188 | 149752608 | 5370.379 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | 1514680188 | 149752608 | 3551.348 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 1 | 1514680188 | 149752608 | 5338.805 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 1 | 1514680188 | 149752608 | 4709.402 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 8 | 1 | 1514680188 | 149752608 | 3551.195 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 8 | 1 | 1514680188 | 149752608 | 5386.547 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 1 | 1514680188 | 149752608 | 3561.043 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 1 | 1514680188 | 149752608 | 5487.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 1 | 1514680188 | 149752608 | 4647.977 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 9 | 1 | 1514680188 | 149752608 | 3560.910 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 9 | 1 | 1514680188 | 149752608 | 5396.367 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 1 | 1514680188 | 149752608 | 3673.648 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 1 | 1514680188 | 149752608 | 5730.578 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 1 | 1514680188 | 149752608 | 4726.887 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 10 | 1 | 1514680188 | 149752608 | 3673.648 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 10 | 1 | 1514680188 | 149752608 | 5513.023 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 1 | 1514680188 | 149752608 | 3679.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 1 | 1514680188 | 149752608 | 5946.020 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 1 | 1514680188 | 149752608 | 4732.305 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 11 | 1 | 1514680188 | 149752608 | 3679.035 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 11 | 1 | 1514680188 | 149752608 | 5518.379 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 1 | 1514680188 | 149752608 | 3684.125 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 1 | 1514680188 | 149752608 | 6160.742 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 1 | 1514680188 | 149752608 | 4666.312 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 12 | 1 | 1514680188 | 149752608 | 3684.172 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 12 | 1 | 1514680188 | 149752608 | 5452.285 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 1 | 1514680188 | 149752608 | 3583.977 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 1 | 1514680188 | 149752608 | 6375.422 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 1 | 1514680188 | 149752608 | 4741.992 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 13 | 1 | 1514680188 | 149752608 | 3584.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 13 | 1 | 1514680188 | 149752608 | 5528.062 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 1 | 1514680188 | 149752608 | 3587.848 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 1 | 1514680188 | 149752608 | 6589.133 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 1 | 1514680188 | 149752608 | 4674.852 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 14 | 1 | 1514680188 | 149752608 | 3587.867 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 14 | 1 | 1514680188 | 149752608 | 5461.074 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 1 | 1514680188 | 149752608 | 3590.793 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 1 | 1514680188 | 149752608 | 6801.949 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 1 | 1514680188 | 149752608 | 4678.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 15 | 1 | 1514680188 | 149752608 | 3591.164 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 15 | 1 | 1514680188 | 149752608 | 5464.008 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 1 | 1514680188 | 149752608 | 3594.660 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 1 | 1514680188 | 149752608 | 7015.371 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 1 | 1514680188 | 149752608 | 4681.480 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 16 | 1 | 1514680188 | 149752608 | 3594.461 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 16 | 1 | 1514680188 | 149752608 | 5467.887 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 1 | 1514680188 | 149752608 | 3598.340 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 1 | 1514680188 | 149752608 | 7229.121 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 1 | 1514680188 | 149752608 | 4685.547 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 17 | 1 | 1514680188 | 149752608 | 3598.359 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 17 | 1 | 1514680188 | 149752608 | 5471.750 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 1 | 1514680188 | 149752608 | 3602.398 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 1 | 1514680188 | 149752608 | 7442.785 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 1 | 1514680188 | 149752608 | 4689.090 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 18 | 1 | 1514680188 | 149752608 | 3602.074 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 18 | 1 | 1514680188 | 149752608 | 5475.520 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 1 | 1514680188 | 149752608 | 3604.906 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 1 | 1514680188 | 149752608 | 7655.297 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 1 | 1514680188 | 149752608 | 4692.066 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 19 | 1 | 1514680188 | 149752608 | 3605.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 19 | 1 | 1514680188 | 149752608 | 5478.234 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 1 | 1514680188 | 149752608 | 3607.883 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 1 | 1514680188 | 149752608 | 7867.887 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 1 | 1514680188 | 149752608 | 4694.871 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 20 | 1 | 1514680188 | 149752608 | 3607.922 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 20 | 1 | 1514680188 | 149752608 | 5480.906 | `process_ru_maxrss` |

## Commands

- `symbolic_reuse_serial-a1`: peak `2890.457` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-atomic`: peak `3120.992` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-private_csr`: peak `3225.945` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-lock_guard`: peak `3960.254` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-coloring`: peak `3016.008` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-row_owner`: peak `4956.168` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-atomic`: peak `3340.359` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-private_csr`: peak `3692.773` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-lock_guard`: peak `4322.266` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-coloring`: peak `3340.367` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-row_owner`: peak `5777.938` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-atomic`: peak `3478.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-private_csr`: peak `4040.605` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-lock_guard`: peak `4460.293` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-coloring`: peak `3478.180` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-row_owner`: peak `5609.445` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-atomic`: peak `3442.281` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-private_csr`: peak `4319.574` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-lock_guard`: peak `4529.402` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-coloring`: peak `3547.164` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-row_owner`: peak `5421.164` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-atomic`: peak `3487.891` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-private_csr`: peak `4575.137` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-lock_guard`: peak `4575.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-coloring`: peak `3593.031` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-row_owner`: peak `5359.371` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-atomic`: peak `3511.160` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-private_csr`: peak `4807.949` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-lock_guard`: peak `4598.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-coloring`: peak `3511.035` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-row_owner`: peak `5346.445` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-atomic`: peak `3535.211` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-private_csr`: peak `5042.016` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-lock_guard`: peak `4622.324` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-coloring`: peak `3535.367` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-row_owner`: peak `5370.379` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-atomic`: peak `3551.348` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-private_csr`: peak `5338.805` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-lock_guard`: peak `4709.402` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-coloring`: peak `3551.195` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-row_owner`: peak `5386.547` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-atomic`: peak `3561.043` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-private_csr`: peak `5487.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-lock_guard`: peak `4647.977` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-coloring`: peak `3560.910` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-row_owner`: peak `5396.367` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-atomic`: peak `3673.648` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-private_csr`: peak `5730.578` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-lock_guard`: peak `4726.887` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-coloring`: peak `3673.648` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-row_owner`: peak `5513.023` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-atomic`: peak `3679.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-private_csr`: peak `5946.020` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-lock_guard`: peak `4732.305` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-coloring`: peak `3679.035` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-row_owner`: peak `5518.379` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-atomic`: peak `3684.125` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-private_csr`: peak `6160.742` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-lock_guard`: peak `4666.312` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-coloring`: peak `3684.172` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-row_owner`: peak `5452.285` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-atomic`: peak `3583.977` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-private_csr`: peak `6375.422` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-lock_guard`: peak `4741.992` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-coloring`: peak `3584.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-row_owner`: peak `5528.062` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-atomic`: peak `3587.848` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-private_csr`: peak `6589.133` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-lock_guard`: peak `4674.852` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-coloring`: peak `3587.867` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-row_owner`: peak `5461.074` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-atomic`: peak `3590.793` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-private_csr`: peak `6801.949` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-lock_guard`: peak `4678.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-coloring`: peak `3591.164` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-row_owner`: peak `5464.008` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-atomic`: peak `3594.660` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-private_csr`: peak `7015.371` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-lock_guard`: peak `4681.480` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-coloring`: peak `3594.461` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-row_owner`: peak `5467.887` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-atomic`: peak `3598.340` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-private_csr`: peak `7229.121` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-lock_guard`: peak `4685.547` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-coloring`: peak `3598.359` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-row_owner`: peak `5471.750` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-atomic`: peak `3602.398` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-private_csr`: peak `7442.785` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-lock_guard`: peak `4689.090` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-coloring`: peak `3602.074` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-row_owner`: peak `5475.520` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-atomic`: peak `3604.906` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-private_csr`: peak `7655.297` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-lock_guard`: peak `4692.066` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-coloring`: peak `3605.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-row_owner`: peak `5478.234` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-atomic`: peak `3607.883` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-private_csr`: peak `7867.887` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-lock_guard`: peak `4694.871` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-coloring`: peak `3607.922` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-row_owner`: peak `5480.906` MB via `process_ru_maxrss`
