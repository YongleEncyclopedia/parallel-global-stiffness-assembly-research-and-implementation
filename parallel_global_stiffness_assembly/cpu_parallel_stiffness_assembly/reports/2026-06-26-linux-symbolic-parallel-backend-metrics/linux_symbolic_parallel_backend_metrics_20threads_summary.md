# Linux 隔离进程数值组装后端图件说明

## 数据物理含义

- 本图只使用 Linux 端重新实跑后的 isolated raw CSV，不重跑 benchmark。
- 基线为 `symbolic_reuse_serial / cpu_serial / 1线程`，即串行符号组装 + 串行数值组装。
- 并行行均为 `parallel_symbolic_reuse`，即并行符号组装 + 对应并行数值后端。
- `amortized_total_ms = symbolic_total_ms + numeric_ms`，是图中的总耗时。
- `isolated_peak_rss_mb` 是每一行单独子进程运行时的峰值 RSS，反映实测进程峰值内存。
- 图中“额外内存”定义为当前峰值 RSS 相对串行基线峰值 RSS 的新增部分；不是 `numeric_backend_extra_bytes` 理论字段。
- 整体加速比以串行 1 线程总耗时 4201.869 ms 为基线。
- 绘图取并行后端 20 线程。

## 绘图行

| 算法 | 后端 | 线程 | 峰值内存(GiB) | 基础内存(GiB) | 额外内存(GiB) | 符号预处理(ms) | 组装(ms) | 总耗时(ms) | 加速比 | rel_L2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 串行基线 | cpu_serial | 1 | 2.823 | 2.823 | 0.000 | 3503.718 | 698.151 | 4201.869 | 1.000 | 0.000e+00 |
| 原子累加 | cpu_atomic | 20 | 3.523 | 2.823 | 0.701 | 827.487 | 144.549 | 972.035 | 4.323 | 1.487e-16 |
| 线程私有 | cpu_private_csr | 20 | 7.683 | 2.823 | 4.861 | 781.958 | 448.972 | 1230.930 | 3.414 | 1.298e-16 |
| 互斥锁 | cpu_lock_guard | 20 | 4.585 | 2.823 | 1.762 | 814.515 | 569.104 | 1383.619 | 3.037 | 1.473e-16 |
| 图着色 | cpu_graph_coloring | 20 | 3.523 | 2.823 | 0.701 | 787.120 | 194.369 | 981.489 | 4.281 | 1.226e-16 |
| 按行分配 | cpu_row_owner | 20 | 5.352 | 2.823 | 2.530 | 828.502 | 151.759 | 980.261 | 4.286 | 0.000e+00 |

## 覆盖审计

| 算法 | 记录数 | 覆盖完整 | 期望 |
|---|---:|---|---|
| 串行基线 | 1 | 是 | symbolic_reuse_serial, 1线程, PASS |
| 原子累加 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取20线程 |
| 线程私有 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取20线程 |
| 互斥锁 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取20线程 |
| 图着色 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取20线程 |
| 按行分配 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取20线程 |

source_csv: `/Users/haohua_jiang/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-06-26-linux-intel-symbolic-parallel-backends-raw/isolated_symbolic_memory/isolated_symbolic_memory.csv`
