# Linux 隔离进程数值组装后端图件说明

## 图表目标

在同一 16 线程条件下，用完整总耗时和隔离峰值内存公平比较五类数值组装后端。

## 数据物理含义

- 本图只使用 Linux 端重新实跑后的三次重复中位数汇总 CSV，不重跑 benchmark。
- 基线为 `symbolic_reuse_serial / cpu_serial / 1线程`，即串行符号组装 + 串行数值组装。
- 并行行均为 `parallel_symbolic_reuse`，即并行符号组装 + 对应并行数值后端。
- `numeric_ms = backend_prepare_ms + assembly_numeric_ms`；图中仍统一显示为“数值组装”。
- `amortized_total_ms = symbolic_total_ms + numeric_ms`，图中总耗时只拆成“符号组装 + 数值组装”两部分。
- `isolated_peak_rss_mb` 是每一行单独子进程运行时的峰值 RSS，反映实测进程峰值内存。
- 图中“额外内存”定义为当前峰值 RSS 相对串行基线峰值 RSS 的新增部分；不是 `numeric_backend_extra_bytes` 理论字段。
- 整体加速比以串行 1 线程总耗时 4202.095 ms 为基线。
- 绘图取并行后端 16 线程；每个数据点来自 3 次独立进程测试的中位数。

## 绘图行

| 算法 | 后端 | 线程 | 峰值内存(GiB) | 基础内存(GiB) | 额外内存(GiB) | 符号组装(ms) | 数值组装(ms) | 后端准备(ms) | 实际累加(ms) | 总耗时(ms) | 加速比 | rel_L2 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 串行基线 | cpu_serial | 1 | 3.027 | 3.027 | 0.000 | 3505.733 | 696.362 | 0.000 | 696.362 | 4202.095 | 1.000 | 0.000e+00 |
| 原子累加 | cpu_atomic | 16 | 3.547 | 3.027 | 0.520 | 788.316 | 159.817 | 0.000 | 159.817 | 948.134 | 4.432 | 1.507e-16 |
| 线程私有 | cpu_private_csr | 16 | 6.851 | 3.027 | 3.824 | 784.780 | 1465.977 | 1064.865 | 401.112 | 2250.758 | 1.867 | 1.194e-16 |
| 互斥锁 | cpu_lock_guard | 16 | 4.597 | 3.027 | 1.570 | 798.391 | 985.060 | 415.023 | 570.037 | 1783.451 | 2.356 | 1.502e-16 |
| 图着色 | cpu_graph_coloring | 16 | 3.572 | 3.027 | 0.545 | 810.340 | 405.063 | 200.776 | 204.286 | 1215.402 | 3.457 | 1.226e-16 |
| 按行分配 | cpu_row_owner | 16 | 5.365 | 3.027 | 2.337 | 798.234 | 4042.672 | 3879.144 | 163.528 | 4840.906 | 0.868 | 0.000e+00 |

## 覆盖审计

| 算法 | 记录数 | 覆盖完整 | 期望 |
|---|---:|---|---|
| 串行基线 | 1 | 是 | symbolic_reuse_serial, 1线程, PASS |
| 原子累加 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取16线程 |
| 线程私有 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取16线程 |
| 互斥锁 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取16线程 |
| 图着色 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取16线程 |
| 按行分配 | 20 | 是 | parallel_symbolic_reuse, 1..20线程, PASS；绘图取16线程 |

source_csv: `results/2026-07-08-linux-intel-symbolic-parallel-backends-raw/isolated_symbolic_memory/isolated_symbolic_memory_summary.csv`
