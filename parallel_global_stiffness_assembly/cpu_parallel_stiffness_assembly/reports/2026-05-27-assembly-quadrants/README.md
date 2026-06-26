# 2026-05-27 月度汇报四象限组装策略图

本目录保存月度汇报用的四象限图和支撑图。主图锚定同一份 WindHub / Apple M4 Max 结果，辅助图解释时间构成、线程扩展、内存生命周期和重复组装摊销。

## 主要输出

- `assets/fig00_monthly_report_summary_slide.*`：一页汇报主图。
- `assets/fig01_four_quadrant_strategy_map.*`：纯四象限图。
- `assets/fig02_cost_breakdown.*`：四类路径的端到端耗时构成。
- `assets/fig03_thread_scaling.*`：并行有符号与并行无符号随线程数变化。
- `assets/fig04_memory_lifecycle.*`：persistent / temporary / transient 内存拆分。
- `assets/fig05_symbolic_reuse_amortization.*`：重复组装时 symbolic reuse 摊销收益。

## 数据源

- `results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.csv`
- `results/2026-05-11-symbolic-numeric/symbolic_numeric_eval.csv`
