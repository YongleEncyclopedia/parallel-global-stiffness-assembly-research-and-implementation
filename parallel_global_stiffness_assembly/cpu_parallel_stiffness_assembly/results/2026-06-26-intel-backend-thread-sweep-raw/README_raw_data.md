# Intel backend thread sweep raw data

本轮是 Intel 平台实跑数据，目标网格为 `3d-WindTurbineHub.inp`，刚度核为 `physics_tet4`，线程范围是完整 `1..20`。

本轮只生成 raw data，没有画图，也没有修改或运行绘图脚本。后续画图可以筛选任意固定线程数；speedup 后续绘图默认以 `cpu_serial` 1 线程总耗时为基线。

正式 benchmark 命令见 `run_commands.sh`。本轮算法集为 `cpu_serial`、`cpu_atomic`、`cpu_private_csr`、`cpu_lock_guard`、`cpu_graph_coloring`、`cpu_row_owner`；未运行或输出 `direct_no_symbolic_*`，未混入 `cpu_coo_sort_reduce`。

`cpu_serial` 是单线程基线：线程 1 为 `PASS`，线程 2..20 作为 `SKIP/NOT_APPLICABLE` 记录保留，用于保证 raw data 中每个算法都有 `1..20` 线程组合的审计行。
