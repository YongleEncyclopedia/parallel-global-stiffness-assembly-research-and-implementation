# Isolated Symbolic Memory Evaluation

Each row was measured in a fresh subprocess. On POSIX, `isolated_peak_rss_mb` is `ru_maxrss`; on Windows, it is the OS-observed peak working set fallback and `isolated_memory_metric` records that distinction.
The legacy report label `isolated peak RSS` is retained for schema continuity, but Windows rows must be read with the metric field.
`numeric_ms = backend_prepare_ms + assembly_numeric_ms`; `legacy_numeric_ms_without_prepare` is retained only to explain older plots.
When `--repeat-count` is greater than 1, `isolated_symbolic_memory.csv` keeps all raw repeats and `isolated_symbolic_memory_summary.csv` stores median rows.

## Rows

| strategy | mode | backend | threads | repeat | status | assemblies | total ms | numeric ms | isolated peak MB | metric |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 1 | PASS | 1 | 4213.612917 | 707.879749 | 3099.883 | `process_ru_maxrss` |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 2 | PASS | 1 | 4224.053433 | 696.362006 | 3099.957 | `process_ru_maxrss` |
| `serial_symbolic_serial_numeric` | `symbolic_reuse_serial` | `cpu_serial` | 1 | 3 | PASS | 1 | 4160.565826 | 687.12216 | 3100.113 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | PASS | 1 | 4830.908954 | 1244.81523 | 3120.996 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 2 | PASS | 1 | 4768.557744 | 1224.895589 | 3120.910 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 3 | PASS | 1 | 4776.290607 | 1211.554008 | 3120.988 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 1 | PASS | 1 | 4391.709592 | 815.628176 | 3225.684 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 2 | PASS | 1 | 4348.530157 | 802.055573 | 3225.707 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 3 | PASS | 1 | 4360.819448 | 798.717758 | 3225.715 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 1 | PASS | 1 | 6449.471851 | 2890.865887 | 4065.223 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 2 | PASS | 1 | 6426.13158 | 2885.54329 | 4065.090 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 3 | PASS | 1 | 6389.680303 | 2866.00154 | 4065.219 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 1 | 1 | PASS | 1 | 5079.253462 | 1534.824583 | 3015.949 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 1 | 2 | PASS | 1 | 5075.33913 | 1537.616474 | 3016.113 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 1 | 3 | PASS | 1 | 5079.567054 | 1540.375749 | 3015.969 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 1 | 1 | PASS | 1 | 8584.374392 | 5012.839358 | 4851.328 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 1 | 2 | PASS | 1 | 8509.63821 | 4967.8893 | 4851.121 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 1 | 3 | PASS | 1 | 8514.861543 | 4982.33535 | 4851.312 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | PASS | 1 | 2769.502786 | 657.696211 | 3340.234 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 2 | PASS | 1 | 2760.919743 | 648.652381 | 3340.242 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 3 | PASS | 1 | 2777.282367 | 650.008773 | 3340.258 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 1 | PASS | 1 | 2679.879942 | 569.620831 | 3718.816 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 2 | PASS | 1 | 2696.061259 | 576.160056 | 3718.832 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 3 | PASS | 1 | 2701.53403 | 575.901945 | 3718.648 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 1 | PASS | 1 | 4268.953897 | 2163.003421 | 4348.199 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 2 | PASS | 1 | 4289.446467 | 2167.121473 | 4348.191 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 3 | PASS | 1 | 4252.13284 | 2155.835991 | 4348.059 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 2 | 1 | PASS | 1 | 3037.116467 | 913.212722 | 3273.250 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 2 | 2 | PASS | 1 | 3009.88007 | 920.281977 | 3273.336 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 2 | 3 | PASS | 1 | 3040.395805 | 926.035378 | 3273.230 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 2 | 1 | PASS | 1 | 6933.884863 | 4832.193255 | 5736.941 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 2 | 2 | PASS | 1 | 6960.315522 | 4859.358863 | 5736.949 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 2 | 3 | PASS | 1 | 6942.247366 | 4841.449746 | 5736.684 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | PASS | 1 | 2126.81305 | 463.522306 | 3478.078 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 2 | PASS | 1 | 2074.74547 | 471.956507 | 3478.184 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 3 | PASS | 1 | 2058.513895 | 460.909209 | 3478.184 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 1 | PASS | 1 | 2152.439538 | 551.963025 | 4066.316 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 2 | PASS | 1 | 2127.505698 | 546.35359 | 4066.246 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 3 | PASS | 1 | 2153.385208 | 549.829486 | 4066.324 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 1 | PASS | 1 | 3282.603159 | 1696.7173 | 4485.895 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 2 | PASS | 1 | 3296.008343 | 1693.000475 | 4486.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 3 | PASS | 1 | 3297.800973 | 1692.683579 | 4485.840 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 3 | 1 | PASS | 1 | 2335.268282 | 744.513987 | 3411.230 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 3 | 2 | PASS | 1 | 2384.521149 | 746.456661 | 3411.211 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 3 | 3 | PASS | 1 | 2344.039788 | 744.584284 | 3411.270 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 3 | 1 | PASS | 1 | 5990.939177 | 4403.96813 | 5568.359 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 3 | 2 | PASS | 1 | 6037.093945 | 4449.093144 | 5568.242 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 3 | 3 | PASS | 1 | 6006.294025 | 4427.570205 | 5568.281 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | PASS | 1 | 1690.114965 | 359.237153 | 3442.238 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 2 | PASS | 1 | 1670.061003 | 358.692257 | 3442.422 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 3 | PASS | 1 | 1684.423523 | 358.551769 | 3442.383 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 1 | PASS | 1 | 1883.469312 | 570.899221 | 4345.293 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 2 | PASS | 1 | 1900.880523 | 573.418202 | 4345.238 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 3 | PASS | 1 | 1907.003973 | 573.355674 | 4345.273 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 1 | PASS | 1 | 2767.311065 | 1456.353282 | 4555.145 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 2 | PASS | 1 | 2784.533449 | 1465.061116 | 4555.070 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 3 | PASS | 1 | 2782.310831 | 1464.27313 | 4555.102 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 4 | 1 | PASS | 1 | 1953.403255 | 630.524421 | 3480.301 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 4 | 2 | PASS | 1 | 1959.787585 | 629.929552 | 3480.387 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 4 | 3 | PASS | 1 | 1933.404355 | 627.593949 | 3480.289 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 4 | 1 | PASS | 1 | 5879.12215 | 4560.195796 | 5484.652 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 4 | 2 | PASS | 1 | 5832.602965 | 4519.550576 | 5484.660 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 4 | 3 | PASS | 1 | 5842.641674 | 4536.140493 | 5484.805 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | PASS | 1 | 1464.153658 | 298.064359 | 3488.027 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 2 | PASS | 1 | 1487.627223 | 295.648036 | 3487.891 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 3 | PASS | 1 | 1474.633082 | 297.736195 | 3487.965 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 1 | PASS | 1 | 1782.580101 | 617.8485 | 4600.738 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 2 | PASS | 1 | 1781.766999 | 613.152057 | 4600.738 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 3 | PASS | 1 | 1792.116442 | 617.64035 | 4600.887 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 1 | PASS | 1 | 2494.675156 | 1325.882851 | 4600.848 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 2 | PASS | 1 | 2502.088972 | 1327.759827 | 4600.680 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 3 | PASS | 1 | 2487.327707 | 1325.921899 | 4600.703 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 5 | 1 | PASS | 1 | 1725.979442 | 552.981412 | 3525.930 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 5 | 2 | PASS | 1 | 1732.400903 | 553.831361 | 3525.941 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 5 | 3 | PASS | 1 | 1723.300593 | 555.138111 | 3525.938 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 5 | 1 | PASS | 1 | 5481.93646 | 4309.181935 | 5423.184 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 5 | 2 | PASS | 1 | 5463.281565 | 4289.99425 | 5423.043 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 5 | 3 | PASS | 1 | 5509.082704 | 4339.348329 | 5423.082 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | PASS | 1 | 1314.275158 | 252.159108 | 3511.051 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 2 | PASS | 1 | 1310.759421 | 252.600249 | 3511.203 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 3 | PASS | 1 | 1301.171235 | 253.877175 | 3510.988 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 1 | PASS | 1 | 1719.263755 | 671.230517 | 4833.816 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 2 | PASS | 1 | 1728.76005 | 671.083308 | 4833.824 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 3 | PASS | 1 | 1747.615142 | 673.688114 | 4833.660 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 1 | PASS | 1 | 2279.788809 | 1219.261128 | 4623.953 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 2 | PASS | 1 | 2266.7252 | 1222.663121 | 4623.973 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 3 | PASS | 1 | 2265.520874 | 1221.644328 | 4623.984 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 6 | 1 | PASS | 1 | 1551.811359 | 505.777429 | 3549.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 6 | 2 | PASS | 1 | 1570.115363 | 506.311329 | 3549.043 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 6 | 3 | PASS | 1 | 1558.436441 | 504.241397 | 3549.090 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 6 | 1 | PASS | 1 | 5202.246206 | 4137.681124 | 5410.254 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 6 | 2 | PASS | 1 | 5198.08487 | 4139.837896 | 5410.258 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 6 | 3 | PASS | 1 | 5202.946851 | 4155.541623 | 5410.301 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | PASS | 1 | 1233.488176 | 222.740445 | 3535.203 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 2 | PASS | 1 | 1213.957496 | 222.948603 | 3535.098 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 3 | PASS | 1 | 1199.073266 | 222.103549 | 3535.133 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 1 | PASS | 1 | 1705.724227 | 730.974539 | 5067.625 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 2 | PASS | 1 | 1714.691766 | 736.54478 | 5067.570 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 3 | PASS | 1 | 1712.405009 | 734.567464 | 5067.613 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 1 | PASS | 1 | 2145.477747 | 1149.253173 | 4648.047 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 2 | PASS | 1 | 2145.12783 | 1147.505554 | 4648.035 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 3 | PASS | 1 | 2132.258399 | 1150.316915 | 4647.887 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 7 | 1 | PASS | 1 | 1458.682966 | 464.701226 | 3573.160 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 7 | 2 | PASS | 1 | 1443.89727 | 465.374934 | 3573.105 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 7 | 3 | PASS | 1 | 1446.732714 | 465.036892 | 3573.160 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 7 | 1 | PASS | 1 | 5211.165051 | 4219.211139 | 5434.066 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 7 | 2 | PASS | 1 | 5218.26108 | 4224.966778 | 5434.098 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 7 | 3 | PASS | 1 | 5199.367217 | 4203.73394 | 5434.199 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | PASS | 1 | 1127.737111 | 200.464039 | 3551.293 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 2 | PASS | 1 | 1126.42461 | 200.465998 | 3551.492 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 3 | PASS | 1 | 1126.798214 | 199.765876 | 3551.473 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 1 | PASS | 1 | 1735.167178 | 809.592812 | 5293.656 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 2 | PASS | 1 | 1737.215087 | 799.915791 | 5293.578 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 3 | PASS | 1 | 1739.348896 | 802.042579 | 5293.465 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 1 | PASS | 1 | 2031.664979 | 1094.003276 | 4664.016 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 2 | PASS | 1 | 2016.667688 | 1094.794541 | 4664.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 3 | PASS | 1 | 2019.720896 | 1096.953985 | 4663.996 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 8 | 1 | PASS | 1 | 1384.748818 | 444.664067 | 3660.465 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 8 | 2 | PASS | 1 | 1375.676422 | 440.645664 | 3660.430 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 8 | 3 | PASS | 1 | 1380.816032 | 440.343392 | 3660.301 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 8 | 1 | PASS | 1 | 5101.810606 | 4164.694825 | 5450.285 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 8 | 2 | PASS | 1 | 5076.343055 | 4152.673269 | 5450.387 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 8 | 3 | PASS | 1 | 5086.903518 | 4162.005593 | 5450.324 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 1 | PASS | 1 | 1197.852081 | 223.865848 | 3561.152 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 2 | PASS | 1 | 1206.987476 | 224.139694 | 3561.160 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 3 | PASS | 1 | 1198.557171 | 223.660279 | 3561.016 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 1 | PASS | 1 | 1867.865188 | 891.767636 | 5513.047 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 2 | PASS | 1 | 1869.986968 | 893.539788 | 5513.195 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 3 | PASS | 1 | 1872.033345 | 896.875294 | 5513.074 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 1 | PASS | 1 | 2028.451509 | 1056.913354 | 4673.660 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 2 | PASS | 1 | 2045.646949 | 1067.990687 | 4673.816 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 3 | PASS | 1 | 2032.68896 | 1053.055469 | 4673.652 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 9 | 1 | PASS | 1 | 1430.728685 | 448.370487 | 3598.906 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 9 | 2 | PASS | 1 | 1423.499616 | 441.81974 | 3598.891 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 9 | 3 | PASS | 1 | 1419.897991 | 441.716611 | 3599.051 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 9 | 1 | PASS | 1 | 4948.050469 | 3941.889927 | 5460.098 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 9 | 2 | PASS | 1 | 4910.441975 | 3928.895972 | 5459.895 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 9 | 3 | PASS | 1 | 4897.925816 | 3926.18199 | 5460.039 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 1 | PASS | 1 | 1153.329934 | 217.246294 | 3677.781 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 2 | PASS | 1 | 1146.458547 | 213.054759 | 3677.660 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 3 | PASS | 1 | 1149.602701 | 212.367749 | 3677.770 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 1 | PASS | 1 | 1915.252292 | 984.15344 | 5730.746 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 2 | PASS | 1 | 1913.573554 | 977.113398 | 5730.555 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 3 | PASS | 1 | 1911.274932 | 981.992654 | 5730.543 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 1 | PASS | 1 | 1962.550512 | 1033.370493 | 4681.344 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 2 | PASS | 1 | 1961.336984 | 1027.873002 | 4681.320 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 3 | PASS | 1 | 1964.157906 | 1031.902094 | 4681.484 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 10 | 1 | PASS | 1 | 1370.075936 | 440.468718 | 3632.410 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 10 | 2 | PASS | 1 | 1356.87115 | 430.791713 | 3632.324 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 10 | 3 | PASS | 1 | 1374.674788 | 439.261996 | 3632.238 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 10 | 1 | PASS | 1 | 4908.776466 | 3978.13203 | 5467.680 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 10 | 2 | PASS | 1 | 4924.307117 | 3977.461169 | 5467.652 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 10 | 3 | PASS | 1 | 4910.86049 | 3976.037431 | 5467.684 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 1 | PASS | 1 | 1098.983656 | 201.288996 | 3683.129 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 2 | PASS | 1 | 1096.755934 | 202.873057 | 3683.129 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 3 | PASS | 1 | 1100.09874 | 201.291579 | 3683.090 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 1 | PASS | 1 | 1952.640639 | 1058.445442 | 5946.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 2 | PASS | 1 | 1949.012217 | 1055.754245 | 5946.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 3 | PASS | 1 | 1984.738372 | 1071.864438 | 5946.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 1 | PASS | 1 | 1900.066653 | 1013.102454 | 4686.762 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 2 | PASS | 1 | 1913.187064 | 1016.798694 | 4686.836 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 3 | PASS | 1 | 1909.662824 | 1016.738657 | 4686.816 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 11 | 1 | PASS | 1 | 1313.16496 | 425.103518 | 3637.738 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 11 | 2 | PASS | 1 | 1344.672556 | 428.916123 | 3637.859 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 11 | 3 | PASS | 1 | 1431.750235 | 522.165278 | 3637.934 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 11 | 1 | PASS | 1 | 4853.665473 | 3963.490746 | 5473.023 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 11 | 2 | PASS | 1 | 4855.402124 | 3968.251137 | 5473.125 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 11 | 3 | PASS | 1 | 4901.245396 | 4007.489994 | 5473.137 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 1 | PASS | 1 | 1077.385778 | 192.708292 | 3617.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 2 | PASS | 1 | 1067.154816 | 192.563096 | 3617.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 3 | PASS | 1 | 1059.036826 | 195.447603 | 3617.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 1 | PASS | 1 | 2016.177961 | 1133.263247 | 6160.902 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 2 | PASS | 1 | 2007.843955 | 1149.645561 | 6161.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 3 | PASS | 1 | 1995.160874 | 1136.198782 | 6160.738 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 1 | PASS | 1 | 1885.036963 | 1011.571218 | 4692.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 2 | PASS | 1 | 1878.464478 | 1016.728984 | 4691.941 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 3 | PASS | 1 | 1885.015261 | 1016.057188 | 4692.121 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 12 | 1 | PASS | 1 | 1287.643858 | 429.659369 | 3642.836 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 12 | 2 | PASS | 1 | 1284.378377 | 424.014297 | 3642.773 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 12 | 3 | PASS | 1 | 1286.577368 | 421.869713 | 3642.883 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 12 | 1 | PASS | 1 | 4985.230645 | 4125.290598 | 5478.051 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 12 | 2 | PASS | 1 | 4957.819373 | 4091.555203 | 5478.191 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 12 | 3 | PASS | 1 | 4992.887515 | 4118.383219 | 5478.020 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 1 | PASS | 1 | 1025.022167 | 182.255494 | 3692.762 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 2 | PASS | 1 | 1017.394901 | 183.320483 | 3692.926 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 3 | PASS | 1 | 1025.228231 | 183.22843 | 3692.789 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 1 | PASS | 1 | 2071.794306 | 1224.954611 | 6375.391 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 2 | PASS | 1 | 2055.786452 | 1221.74065 | 6375.410 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 3 | PASS | 1 | 2069.405045 | 1223.000591 | 6375.398 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 1 | PASS | 1 | 1858.651876 | 1000.82654 | 4696.641 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 2 | PASS | 1 | 1832.354489 | 999.971013 | 4696.801 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 3 | PASS | 1 | 1854.16018 | 1010.576743 | 4696.777 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 13 | 1 | PASS | 1 | 1259.16391 | 420.941013 | 3647.484 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 13 | 2 | PASS | 1 | 1258.626017 | 413.044931 | 3647.367 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 13 | 3 | PASS | 1 | 1258.951419 | 421.80288 | 3647.543 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 13 | 1 | PASS | 1 | 4963.003444 | 4127.775824 | 5482.844 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 13 | 2 | PASS | 1 | 4984.853167 | 4151.723417 | 5482.734 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 13 | 3 | PASS | 1 | 4976.075188 | 4139.65798 | 5482.707 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 1 | PASS | 1 | 991.160629 | 174.592001 | 3625.844 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 2 | PASS | 1 | 1017.360538 | 173.346512 | 3625.852 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 3 | PASS | 1 | 996.716742 | 174.055541 | 3625.602 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 1 | PASS | 1 | 2116.089169 | 1302.035448 | 6588.863 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 2 | PASS | 1 | 2190.043413 | 1302.919689 | 6588.836 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 3 | PASS | 1 | 2115.158792 | 1301.373725 | 6589.027 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 1 | PASS | 1 | 1805.180774 | 992.43245 | 4700.707 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 2 | PASS | 1 | 1802.974008 | 991.818244 | 4700.570 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 3 | PASS | 1 | 1800.251915 | 988.583287 | 4700.691 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 14 | 1 | PASS | 1 | 1265.818384 | 413.920874 | 3651.500 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 14 | 2 | PASS | 1 | 1225.444357 | 412.799869 | 3651.488 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 14 | 3 | PASS | 1 | 1227.022117 | 411.058935 | 3651.641 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 14 | 1 | PASS | 1 | 5017.965387 | 4203.977584 | 5487.016 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 14 | 2 | PASS | 1 | 5017.036116 | 4176.749253 | 5486.746 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 14 | 3 | PASS | 1 | 4998.802761 | 4170.472641 | 5486.734 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 1 | PASS | 1 | 988.547472 | 164.080185 | 3629.055 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 2 | PASS | 1 | 987.135535 | 166.27509 | 3629.137 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 15 | 3 | PASS | 1 | 984.736262 | 163.448701 | 3628.816 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 1 | PASS | 1 | 2182.485171 | 1386.716815 | 6801.828 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 2 | PASS | 1 | 2183.541635 | 1383.668574 | 6801.934 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 15 | 3 | PASS | 1 | 2203.647072 | 1381.165243 | 6801.922 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 1 | PASS | 1 | 1785.253222 | 987.302105 | 4703.734 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 2 | PASS | 1 | 1811.064798 | 989.652469 | 4703.805 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 15 | 3 | PASS | 1 | 1796.448718 | 985.111277 | 4703.781 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 15 | 1 | PASS | 1 | 1232.400288 | 413.835334 | 3654.445 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 15 | 2 | PASS | 1 | 1198.950901 | 404.383084 | 3654.434 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 15 | 3 | PASS | 1 | 1201.850074 | 407.001124 | 3654.613 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 15 | 1 | PASS | 1 | 4963.451569 | 4165.336149 | 5489.992 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 15 | 2 | PASS | 1 | 5008.647089 | 4183.842628 | 5489.902 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 15 | 3 | PASS | 1 | 5026.368904 | 4204.327426 | 5489.781 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 1 | PASS | 1 | 947.172318 | 159.817311 | 3632.684 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 2 | PASS | 1 | 947.632443 | 159.316106 | 3632.496 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 16 | 3 | PASS | 1 | 989.644798 | 160.397982 | 3632.414 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 1 | PASS | 1 | 2259.438915 | 1474.658652 | 7015.590 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 2 | PASS | 1 | 2239.28845 | 1457.14457 | 7015.406 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 16 | 3 | PASS | 1 | 2267.747759 | 1464.730994 | 7015.340 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 1 | PASS | 1 | 1783.332848 | 984.941681 | 4707.328 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 2 | PASS | 1 | 1781.230774 | 989.628703 | 4707.266 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 16 | 3 | PASS | 1 | 1790.989237 | 984.204275 | 4707.328 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 16 | 1 | PASS | 1 | 1192.04948 | 405.817177 | 3658.059 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 16 | 2 | PASS | 1 | 1218.152932 | 407.813326 | 3658.105 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 16 | 3 | PASS | 1 | 1265.193158 | 403.142126 | 3658.262 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 16 | 1 | PASS | 1 | 4840.852969 | 4042.672471 | 5493.547 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 16 | 2 | PASS | 1 | 4849.016831 | 4050.783124 | 5493.445 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 16 | 3 | PASS | 1 | 4848.817382 | 4044.620698 | 5493.523 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 1 | PASS | 1 | 931.498492 | 152.530215 | 3636.320 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 2 | PASS | 1 | 954.917691 | 151.979219 | 3636.484 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 17 | 3 | PASS | 1 | 929.917925 | 151.67661 | 3636.324 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 1 | PASS | 1 | 2331.192663 | 1535.803582 | 7228.977 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 2 | PASS | 1 | 2315.937548 | 1541.337486 | 7229.176 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 17 | 3 | PASS | 1 | 2322.821003 | 1548.012264 | 7229.281 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 1 | PASS | 1 | 1765.089984 | 974.190997 | 4711.305 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 2 | PASS | 1 | 1789.386605 | 977.712866 | 4711.156 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 17 | 3 | PASS | 1 | 1783.4071 | 978.643899 | 4711.148 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 17 | 1 | PASS | 1 | 1205.250747 | 397.395305 | 3662.309 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 17 | 2 | PASS | 1 | 1185.457935 | 397.557658 | 3662.266 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 17 | 3 | PASS | 1 | 1168.991369 | 397.226451 | 3662.098 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 17 | 1 | PASS | 1 | 4845.634733 | 4010.17003 | 5497.391 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 17 | 2 | PASS | 1 | 4793.60826 | 4019.850067 | 5497.543 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 17 | 3 | PASS | 1 | 4800.392079 | 3994.885517 | 5497.512 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 1 | PASS | 1 | 948.329045 | 149.12926 | 3640.188 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 2 | PASS | 1 | 951.704569 | 150.929956 | 3640.395 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 18 | 3 | PASS | 1 | 963.639371 | 159.224066 | 3640.238 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 1 | PASS | 1 | 2427.379681 | 1629.194696 | 7442.598 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 2 | PASS | 1 | 2393.490225 | 1624.728595 | 7442.574 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 18 | 3 | PASS | 1 | 2395.984962 | 1624.390137 | 7442.574 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 1 | PASS | 1 | 1755.457307 | 981.862846 | 4715.223 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 2 | PASS | 1 | 1777.706375 | 981.973964 | 4715.137 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 18 | 3 | PASS | 1 | 1752.537453 | 977.222926 | 4715.086 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 18 | 1 | PASS | 1 | 1171.338121 | 401.12063 | 3665.840 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 18 | 2 | PASS | 1 | 1194.410598 | 402.904763 | 3665.742 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 18 | 3 | PASS | 1 | 1170.772565 | 402.960436 | 3665.715 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 18 | 1 | PASS | 1 | 4834.673465 | 4030.070607 | 5501.148 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 18 | 2 | PASS | 1 | 4877.746597 | 4039.248022 | 5501.121 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 18 | 3 | PASS | 1 | 4825.323002 | 4029.748393 | 5501.289 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 1 | PASS | 1 | 982.23323 | 175.922909 | 3642.871 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 2 | PASS | 1 | 966.136331 | 146.886824 | 3643.004 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 19 | 3 | PASS | 1 | 962.874015 | 144.242982 | 3643.137 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 1 | PASS | 1 | 2480.578621 | 1708.264504 | 7655.258 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 2 | PASS | 1 | 2477.755167 | 1706.267236 | 7655.207 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 19 | 3 | PASS | 1 | 2486.746296 | 1715.071611 | 7655.527 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 1 | PASS | 1 | 1766.090898 | 967.941823 | 4717.879 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 2 | PASS | 1 | 1781.851525 | 981.213851 | 4718.031 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 19 | 3 | PASS | 1 | 1811.647632 | 972.044826 | 4717.934 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 19 | 1 | PASS | 1 | 1180.221135 | 400.986503 | 3668.488 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 19 | 2 | PASS | 1 | 1174.525572 | 400.571987 | 3668.672 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 19 | 3 | PASS | 1 | 1186.926437 | 413.208951 | 3668.562 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 19 | 1 | PASS | 1 | 4671.101899 | 3870.724209 | 5503.883 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 19 | 2 | PASS | 1 | 4635.090664 | 3856.897067 | 5504.055 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 19 | 3 | PASS | 1 | 4626.381063 | 3821.015736 | 5503.988 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 1 | PASS | 1 | 940.139324 | 145.765381 | 3645.992 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 2 | PASS | 1 | 973.032615 | 142.676819 | 3645.844 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_atomic` | 20 | 3 | PASS | 1 | 976.079501 | 147.710102 | 3645.797 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 1 | PASS | 1 | 2579.316615 | 1797.021631 | 7868.176 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 2 | PASS | 1 | 2591.328428 | 1794.061622 | 7867.949 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_private_csr` | 20 | 3 | PASS | 1 | 2572.170764 | 1789.345891 | 7868.012 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 1 | PASS | 1 | 1809.408466 | 970.5611 | 4720.582 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 2 | PASS | 1 | 1834.578611 | 1036.579151 | 4720.758 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_lock_guard` | 20 | 3 | PASS | 1 | 1815.056195 | 1002.114201 | 4720.746 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 20 | 1 | PASS | 1 | 1184.039092 | 399.60961 | 3671.449 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 20 | 2 | PASS | 1 | 1211.280732 | 401.599747 | 3671.629 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_graph_coloring` | 20 | 3 | PASS | 1 | 1184.415968 | 399.08791 | 3671.445 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 20 | 1 | PASS | 1 | 4625.625539 | 3805.974912 | 5506.812 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 20 | 2 | PASS | 1 | 4617.869965 | 3797.33146 | 5506.770 | `process_ru_maxrss` |
| `parallel_symbolic_parallel_numeric` | `parallel_symbolic_reuse` | `cpu_row_owner` | 20 | 3 | PASS | 1 | 4607.788374 | 3808.277356 | 5506.707 | `process_ru_maxrss` |

## Commands

- `symbolic_reuse_serial-a1-r1`: peak `3099.883` MB via `process_ru_maxrss`
- `symbolic_reuse_serial-a1-r2`: peak `3099.957` MB via `process_ru_maxrss`
- `symbolic_reuse_serial-a1-r3`: peak `3100.113` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-atomic-r1`: peak `3120.996` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-atomic-r2`: peak `3120.910` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-atomic-r3`: peak `3120.988` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-private_csr-r1`: peak `3225.684` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-private_csr-r2`: peak `3225.707` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-private_csr-r3`: peak `3225.715` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-lock_guard-r1`: peak `4065.223` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-lock_guard-r2`: peak `4065.090` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-lock_guard-r3`: peak `4065.219` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-coloring-r1`: peak `3015.949` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-coloring-r2`: peak `3016.113` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-coloring-r3`: peak `3015.969` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-row_owner-r1`: peak `4851.328` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-row_owner-r2`: peak `4851.121` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t1-row_owner-r3`: peak `4851.312` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-atomic-r1`: peak `3340.234` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-atomic-r2`: peak `3340.242` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-atomic-r3`: peak `3340.258` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-private_csr-r1`: peak `3718.816` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-private_csr-r2`: peak `3718.832` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-private_csr-r3`: peak `3718.648` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-lock_guard-r1`: peak `4348.199` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-lock_guard-r2`: peak `4348.191` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-lock_guard-r3`: peak `4348.059` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-coloring-r1`: peak `3273.250` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-coloring-r2`: peak `3273.336` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-coloring-r3`: peak `3273.230` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-row_owner-r1`: peak `5736.941` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-row_owner-r2`: peak `5736.949` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t2-row_owner-r3`: peak `5736.684` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-atomic-r1`: peak `3478.078` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-atomic-r2`: peak `3478.184` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-atomic-r3`: peak `3478.184` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-private_csr-r1`: peak `4066.316` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-private_csr-r2`: peak `4066.246` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-private_csr-r3`: peak `4066.324` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-lock_guard-r1`: peak `4485.895` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-lock_guard-r2`: peak `4486.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-lock_guard-r3`: peak `4485.840` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-coloring-r1`: peak `3411.230` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-coloring-r2`: peak `3411.211` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-coloring-r3`: peak `3411.270` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-row_owner-r1`: peak `5568.359` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-row_owner-r2`: peak `5568.242` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t3-row_owner-r3`: peak `5568.281` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-atomic-r1`: peak `3442.238` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-atomic-r2`: peak `3442.422` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-atomic-r3`: peak `3442.383` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-private_csr-r1`: peak `4345.293` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-private_csr-r2`: peak `4345.238` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-private_csr-r3`: peak `4345.273` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-lock_guard-r1`: peak `4555.145` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-lock_guard-r2`: peak `4555.070` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-lock_guard-r3`: peak `4555.102` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-coloring-r1`: peak `3480.301` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-coloring-r2`: peak `3480.387` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-coloring-r3`: peak `3480.289` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-row_owner-r1`: peak `5484.652` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-row_owner-r2`: peak `5484.660` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t4-row_owner-r3`: peak `5484.805` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-atomic-r1`: peak `3488.027` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-atomic-r2`: peak `3487.891` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-atomic-r3`: peak `3487.965` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-private_csr-r1`: peak `4600.738` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-private_csr-r2`: peak `4600.738` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-private_csr-r3`: peak `4600.887` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-lock_guard-r1`: peak `4600.848` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-lock_guard-r2`: peak `4600.680` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-lock_guard-r3`: peak `4600.703` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-coloring-r1`: peak `3525.930` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-coloring-r2`: peak `3525.941` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-coloring-r3`: peak `3525.938` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-row_owner-r1`: peak `5423.184` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-row_owner-r2`: peak `5423.043` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t5-row_owner-r3`: peak `5423.082` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-atomic-r1`: peak `3511.051` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-atomic-r2`: peak `3511.203` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-atomic-r3`: peak `3510.988` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-private_csr-r1`: peak `4833.816` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-private_csr-r2`: peak `4833.824` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-private_csr-r3`: peak `4833.660` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-lock_guard-r1`: peak `4623.953` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-lock_guard-r2`: peak `4623.973` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-lock_guard-r3`: peak `4623.984` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-coloring-r1`: peak `3549.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-coloring-r2`: peak `3549.043` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-coloring-r3`: peak `3549.090` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-row_owner-r1`: peak `5410.254` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-row_owner-r2`: peak `5410.258` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t6-row_owner-r3`: peak `5410.301` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-atomic-r1`: peak `3535.203` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-atomic-r2`: peak `3535.098` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-atomic-r3`: peak `3535.133` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-private_csr-r1`: peak `5067.625` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-private_csr-r2`: peak `5067.570` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-private_csr-r3`: peak `5067.613` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-lock_guard-r1`: peak `4648.047` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-lock_guard-r2`: peak `4648.035` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-lock_guard-r3`: peak `4647.887` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-coloring-r1`: peak `3573.160` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-coloring-r2`: peak `3573.105` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-coloring-r3`: peak `3573.160` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-row_owner-r1`: peak `5434.066` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-row_owner-r2`: peak `5434.098` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t7-row_owner-r3`: peak `5434.199` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-atomic-r1`: peak `3551.293` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-atomic-r2`: peak `3551.492` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-atomic-r3`: peak `3551.473` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-private_csr-r1`: peak `5293.656` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-private_csr-r2`: peak `5293.578` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-private_csr-r3`: peak `5293.465` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-lock_guard-r1`: peak `4664.016` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-lock_guard-r2`: peak `4664.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-lock_guard-r3`: peak `4663.996` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-coloring-r1`: peak `3660.465` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-coloring-r2`: peak `3660.430` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-coloring-r3`: peak `3660.301` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-row_owner-r1`: peak `5450.285` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-row_owner-r2`: peak `5450.387` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t8-row_owner-r3`: peak `5450.324` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-atomic-r1`: peak `3561.152` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-atomic-r2`: peak `3561.160` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-atomic-r3`: peak `3561.016` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-private_csr-r1`: peak `5513.047` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-private_csr-r2`: peak `5513.195` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-private_csr-r3`: peak `5513.074` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-lock_guard-r1`: peak `4673.660` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-lock_guard-r2`: peak `4673.816` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-lock_guard-r3`: peak `4673.652` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-coloring-r1`: peak `3598.906` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-coloring-r2`: peak `3598.891` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-coloring-r3`: peak `3599.051` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-row_owner-r1`: peak `5460.098` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-row_owner-r2`: peak `5459.895` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t9-row_owner-r3`: peak `5460.039` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-atomic-r1`: peak `3677.781` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-atomic-r2`: peak `3677.660` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-atomic-r3`: peak `3677.770` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-private_csr-r1`: peak `5730.746` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-private_csr-r2`: peak `5730.555` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-private_csr-r3`: peak `5730.543` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-lock_guard-r1`: peak `4681.344` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-lock_guard-r2`: peak `4681.320` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-lock_guard-r3`: peak `4681.484` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-coloring-r1`: peak `3632.410` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-coloring-r2`: peak `3632.324` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-coloring-r3`: peak `3632.238` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-row_owner-r1`: peak `5467.680` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-row_owner-r2`: peak `5467.652` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t10-row_owner-r3`: peak `5467.684` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-atomic-r1`: peak `3683.129` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-atomic-r2`: peak `3683.129` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-atomic-r3`: peak `3683.090` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-private_csr-r1`: peak `5946.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-private_csr-r2`: peak `5946.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-private_csr-r3`: peak `5946.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-lock_guard-r1`: peak `4686.762` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-lock_guard-r2`: peak `4686.836` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-lock_guard-r3`: peak `4686.816` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-coloring-r1`: peak `3637.738` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-coloring-r2`: peak `3637.859` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-coloring-r3`: peak `3637.934` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-row_owner-r1`: peak `5473.023` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-row_owner-r2`: peak `5473.125` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t11-row_owner-r3`: peak `5473.137` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-atomic-r1`: peak `3617.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-atomic-r2`: peak `3617.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-atomic-r3`: peak `3617.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-private_csr-r1`: peak `6160.902` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-private_csr-r2`: peak `6161.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-private_csr-r3`: peak `6160.738` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-lock_guard-r1`: peak `4692.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-lock_guard-r2`: peak `4691.941` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-lock_guard-r3`: peak `4692.121` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-coloring-r1`: peak `3642.836` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-coloring-r2`: peak `3642.773` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-coloring-r3`: peak `3642.883` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-row_owner-r1`: peak `5478.051` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-row_owner-r2`: peak `5478.191` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t12-row_owner-r3`: peak `5478.020` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-atomic-r1`: peak `3692.762` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-atomic-r2`: peak `3692.926` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-atomic-r3`: peak `3692.789` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-private_csr-r1`: peak `6375.391` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-private_csr-r2`: peak `6375.410` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-private_csr-r3`: peak `6375.398` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-lock_guard-r1`: peak `4696.641` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-lock_guard-r2`: peak `4696.801` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-lock_guard-r3`: peak `4696.777` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-coloring-r1`: peak `3647.484` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-coloring-r2`: peak `3647.367` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-coloring-r3`: peak `3647.543` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-row_owner-r1`: peak `5482.844` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-row_owner-r2`: peak `5482.734` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t13-row_owner-r3`: peak `5482.707` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-atomic-r1`: peak `3625.844` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-atomic-r2`: peak `3625.852` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-atomic-r3`: peak `3625.602` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-private_csr-r1`: peak `6588.863` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-private_csr-r2`: peak `6588.836` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-private_csr-r3`: peak `6589.027` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-lock_guard-r1`: peak `4700.707` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-lock_guard-r2`: peak `4700.570` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-lock_guard-r3`: peak `4700.691` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-coloring-r1`: peak `3651.500` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-coloring-r2`: peak `3651.488` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-coloring-r3`: peak `3651.641` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-row_owner-r1`: peak `5487.016` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-row_owner-r2`: peak `5486.746` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t14-row_owner-r3`: peak `5486.734` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-atomic-r1`: peak `3629.055` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-atomic-r2`: peak `3629.137` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-atomic-r3`: peak `3628.816` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-private_csr-r1`: peak `6801.828` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-private_csr-r2`: peak `6801.934` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-private_csr-r3`: peak `6801.922` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-lock_guard-r1`: peak `4703.734` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-lock_guard-r2`: peak `4703.805` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-lock_guard-r3`: peak `4703.781` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-coloring-r1`: peak `3654.445` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-coloring-r2`: peak `3654.434` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-coloring-r3`: peak `3654.613` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-row_owner-r1`: peak `5489.992` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-row_owner-r2`: peak `5489.902` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t15-row_owner-r3`: peak `5489.781` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-atomic-r1`: peak `3632.684` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-atomic-r2`: peak `3632.496` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-atomic-r3`: peak `3632.414` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-private_csr-r1`: peak `7015.590` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-private_csr-r2`: peak `7015.406` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-private_csr-r3`: peak `7015.340` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-lock_guard-r1`: peak `4707.328` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-lock_guard-r2`: peak `4707.266` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-lock_guard-r3`: peak `4707.328` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-coloring-r1`: peak `3658.059` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-coloring-r2`: peak `3658.105` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-coloring-r3`: peak `3658.262` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-row_owner-r1`: peak `5493.547` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-row_owner-r2`: peak `5493.445` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t16-row_owner-r3`: peak `5493.523` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-atomic-r1`: peak `3636.320` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-atomic-r2`: peak `3636.484` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-atomic-r3`: peak `3636.324` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-private_csr-r1`: peak `7228.977` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-private_csr-r2`: peak `7229.176` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-private_csr-r3`: peak `7229.281` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-lock_guard-r1`: peak `4711.305` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-lock_guard-r2`: peak `4711.156` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-lock_guard-r3`: peak `4711.148` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-coloring-r1`: peak `3662.309` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-coloring-r2`: peak `3662.266` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-coloring-r3`: peak `3662.098` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-row_owner-r1`: peak `5497.391` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-row_owner-r2`: peak `5497.543` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t17-row_owner-r3`: peak `5497.512` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-atomic-r1`: peak `3640.188` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-atomic-r2`: peak `3640.395` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-atomic-r3`: peak `3640.238` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-private_csr-r1`: peak `7442.598` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-private_csr-r2`: peak `7442.574` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-private_csr-r3`: peak `7442.574` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-lock_guard-r1`: peak `4715.223` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-lock_guard-r2`: peak `4715.137` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-lock_guard-r3`: peak `4715.086` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-coloring-r1`: peak `3665.840` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-coloring-r2`: peak `3665.742` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-coloring-r3`: peak `3665.715` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-row_owner-r1`: peak `5501.148` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-row_owner-r2`: peak `5501.121` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t18-row_owner-r3`: peak `5501.289` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-atomic-r1`: peak `3642.871` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-atomic-r2`: peak `3643.004` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-atomic-r3`: peak `3643.137` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-private_csr-r1`: peak `7655.258` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-private_csr-r2`: peak `7655.207` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-private_csr-r3`: peak `7655.527` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-lock_guard-r1`: peak `4717.879` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-lock_guard-r2`: peak `4718.031` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-lock_guard-r3`: peak `4717.934` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-coloring-r1`: peak `3668.488` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-coloring-r2`: peak `3668.672` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-coloring-r3`: peak `3668.562` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-row_owner-r1`: peak `5503.883` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-row_owner-r2`: peak `5504.055` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t19-row_owner-r3`: peak `5503.988` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-atomic-r1`: peak `3645.992` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-atomic-r2`: peak `3645.844` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-atomic-r3`: peak `3645.797` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-private_csr-r1`: peak `7868.176` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-private_csr-r2`: peak `7867.949` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-private_csr-r3`: peak `7868.012` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-lock_guard-r1`: peak `4720.582` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-lock_guard-r2`: peak `4720.758` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-lock_guard-r3`: peak `4720.746` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-coloring-r1`: peak `3671.449` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-coloring-r2`: peak `3671.629` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-coloring-r3`: peak `3671.445` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-row_owner-r1`: peak `5506.812` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-row_owner-r2`: peak `5506.770` MB via `process_ru_maxrss`
- `parallel_symbolic_reuse-a1-t20-row_owner-r3`: peak `5506.707` MB via `process_ru_maxrss`
