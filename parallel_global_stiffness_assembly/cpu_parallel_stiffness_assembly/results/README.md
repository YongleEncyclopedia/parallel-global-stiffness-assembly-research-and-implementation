# 实验结果目录

## 用途

保存按日期或 schema 分组的 CSV、JSON、图表、摘要和跨平台结果包。

## 存放内容

- 直接文件：`2026-05-12-thread-scaling-linux-intel-hybrid-core-supplement.md`、`2026-05-14-thread-scaling-macos-m4max-qos-supplement.md`、`2026-06-26-archive-provenance.tsv`
- 子目录：`2026-04-22/`、`2026-04-28-12charts-repeat3/`、`2026-04-28-12charts-repeat3-threads1to14/`、`2026-04-28-12charts-run/`、`2026-05-11-symbolic-numeric/`、`2026-05-11-thread-scaling/`、`2026-05-11-thread-scaling-linux-intel/`、`2026-05-12-thread-scaling-linux-intel-ecore/`、`2026-05-12-thread-scaling-linux-intel-pcore/`、`2026-05-14-thread-scaling-macos-m4max-efficiency-qos/`、`2026-05-14-thread-scaling-macos-m4max-performance-qos/`、`2026-05-16-mentor-action-items/` 等 14 个子目录

## 不应存放

源码实现、手写计划或未说明来源的临时输出。

## 维护提示

删除任何结果前先确认是否被报告、source index 或审计表引用。

`2026-06-26-archive-provenance.tsv` 是 Issue #28 删除三个根部 tar 前生成的逐成员 SHA256 对照。`archive_sha256` 记录 tar 本体，`working_tree_sha256` 固定指向基线 `eca50af` 的原展开文件；归档独有的 `run.log` 则指向从 tar 精确恢复后的工作树文件。`normalized_lf_sha256` 只把 CRLF 规范化为 LF，用于证明四个 CSV 没有内容差异。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly](../README.md)
- 归档来源对照：[`2026-06-26-archive-provenance.tsv`](2026-06-26-archive-provenance.tsv)
- 子目录：[`2026-04-22/`](2026-04-22/README.md)
- 子目录：[`2026-04-28-12charts-repeat3/`](2026-04-28-12charts-repeat3/README.md)
- 子目录：[`2026-04-28-12charts-repeat3-threads1to14/`](2026-04-28-12charts-repeat3-threads1to14/README.md)
- 子目录：[`2026-04-28-12charts-run/`](2026-04-28-12charts-run/README.md)
- 子目录：[`2026-05-11-symbolic-numeric/`](2026-05-11-symbolic-numeric/README.md)
- 子目录：[`2026-05-11-thread-scaling/`](2026-05-11-thread-scaling/README.md)
- 子目录：[`2026-05-11-thread-scaling-linux-intel/`](2026-05-11-thread-scaling-linux-intel/README.md)
- 子目录：[`2026-05-12-thread-scaling-linux-intel-ecore/`](2026-05-12-thread-scaling-linux-intel-ecore/README.md)
