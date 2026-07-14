# 报告与图件目录

## 当前入口

- [`2026-07-10-linux-symbolic-parallel-backend-metrics/`](2026-07-10-linux-symbolic-parallel-backend-metrics/README.md)：当前 Linux Intel 五类数值后端主图与线程趋势图。数据来自三次独立进程测试的中位数；总耗时为“符号组装 + 数值组装”，数值组装包含后端准备。
- [`2026-06-16-simple-deflection-validation-figures/`](2026-06-16-simple-deflection-validation-figures/README.md)：修正后的四面体/六面体悬臂梁最大挠度相对差异图。

## 解释与历史材料

- `2026-05-27-assembly-quadrants/`、`2026-05-27-assembly-schematics/`：算法概念和路径示意，不作为当前性能真值。
- `2026-06-12-assembly-quadrants-revision/`：四象限图的后续排版版本。
- `2026-05-14-*`、`2026-05-22-*`、`2026-05-23-*`、`2026-05-24-*`：对应日期的汇报快照。
- `project-long-term-beamer/`：长期学习与汇报手册。

## 维护边界

- 原始实验数据只进入 `../results/`；报告必须回链到原始 CSV、命令和平台信息。
- 本目录保留 `SVG`、`PDF` 和 `PNG`。可由脚本重建的 `TIFF` 不纳入 Git 工作树。
- 含占位估计、混合计时口径、同进程历史峰值内存或遗漏后端准备耗时的旧图已在 Issue #49 第一阶段清理中移除。
- 带日期的报告只代表当时状态，不得覆盖当前代码和最新结构化结果。

## 相关入口

- [CPU 主线](../README.md)
- [实验结果](../results/README.md)
- [当前知识边界](../../../docs/context/current-knowledge-boundary.md)
