# Intel backend thread sweep raw data

本轮是 Intel 平台实跑数据，目标网格为 `3d-WindTurbineHub.inp`，刚度核为 `physics_tet4`，线程范围是完整 `1..20`。

本轮只生成 raw data，没有画图，也没有修改或运行绘图脚本。后续画图可以筛选任意固定线程数；speedup 后续绘图默认以 `cpu_serial` 1 线程总耗时为基线。

正式 benchmark 命令见 `run_commands.sh`。本轮算法集为 `cpu_serial`、`cpu_atomic`、`cpu_private_csr`、`cpu_lock_guard`、`cpu_graph_coloring`、`cpu_row_owner`；未运行或输出 `direct_no_symbolic_*`，未混入 `cpu_coo_sort_reduce`。

`cpu_serial` 是单线程基线：线程 1 为 `PASS`，线程 2..20 作为 `SKIP/NOT_APPLICABLE` 记录保留，用于保证 raw data 中每个算法都有 `1..20` 线程组合的审计行。

## 历史 tar 清理来源

Issue #28 删除了源码树根部的冗余归档 `intel_backend_thread_sweep_raw_2026-06-26.tar.gz`。删除前记录：

- tar SHA256：`cfe3ffc9aa03d71d9a9745db120fc660d26c8b89dc70045106d12b31395b2d79`
- 比较结论：清理前基线 `eca50af` 中，归档文件集合与展开目录完全相同，以下 6 个文件逐字节一致，没有归档独有内容。
- 成员：`README_raw_data.md`
- 成员：`platform_info.txt`
- 成员：`run_commands.sh`
- 成员：`windhub_backend_thread_sweep_intel.csv`
- 成员：`windhub_backend_thread_sweep_intel.json`
- 成员：`windhub_backend_thread_sweep_intel.md`

因此除本节新增的审计说明外，本目录保留了该 tar 的完整展开内容。

机器可读逐成员哈希见 [`../2026-06-26-archive-provenance.tsv`](../2026-06-26-archive-provenance.tsv)；其中 `working_tree_sha256` 记录清理前基线 `eca50af`。
