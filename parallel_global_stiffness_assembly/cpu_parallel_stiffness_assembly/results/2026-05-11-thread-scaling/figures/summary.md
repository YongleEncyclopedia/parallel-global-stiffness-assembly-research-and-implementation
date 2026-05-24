# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling/figures/summary.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Thread Scaling Figures Summary

Figures in this directory were redrawn in presentation style from existing CSV benchmark results. PNG files are for Markdown viewing; SVG files keep editable text for inspection and slide reuse.

| Figure | PNG | SVG | Purpose |
| --- | --- | --- | --- |
| `thread_scaling_default_dashboard` | [png](thread_scaling_default_dashboard.png) | [svg](thread_scaling_default_dashboard.svg) | Default-environment timing, speedup, efficiency, memory, and best-point summary. |
| `thread_scaling_bound_dashboard` | [png](thread_scaling_bound_dashboard.png) | [svg](thread_scaling_bound_dashboard.svg) | Bound-environment timing, speedup, efficiency, memory, and best-point summary. |
| `thread_scaling_by_algorithm_cpu_atomic` | [png](thread_scaling_by_algorithm_cpu_atomic.png) | [svg](thread_scaling_by_algorithm_cpu_atomic.svg) | Single-algorithm default/bound thread-scaling detail. |
| `thread_scaling_by_algorithm_cpu_private_csr` | [png](thread_scaling_by_algorithm_cpu_private_csr.png) | [svg](thread_scaling_by_algorithm_cpu_private_csr.svg) | Single-algorithm default/bound thread-scaling detail. |
| `thread_scaling_by_algorithm_cpu_row_owner` | [png](thread_scaling_by_algorithm_cpu_row_owner.png) | [svg](thread_scaling_by_algorithm_cpu_row_owner.svg) | Single-algorithm default/bound thread-scaling detail. |
| `thread_scaling_by_algorithm_cpu_graph_coloring` | [png](thread_scaling_by_algorithm_cpu_graph_coloring.png) | [svg](thread_scaling_by_algorithm_cpu_graph_coloring.svg) | Single-algorithm default/bound thread-scaling detail. |
| `thread_scaling_memory_by_env` | [png](thread_scaling_memory_by_env.png) | [svg](thread_scaling_memory_by_env.svg) | Extra memory across thread counts in default and bound environments. |
| `thread_scaling_physical_vs_oversubscription` | [png](thread_scaling_physical_vs_oversubscription.png) | [svg](thread_scaling_physical_vs_oversubscription.svg) | Direct comparison of the best physical-core and oversubscription assembly times. |
| `thread_scaling_stage_breakdown_best` | [png](thread_scaling_stage_breakdown_best.png) | [svg](thread_scaling_stage_breakdown_best.svg) | Stage composition at each environment and algorithm best thread count. |
| `thread_scaling_contact_sheet` | [png](thread_scaling_contact_sheet.png) | - | Thumbnail overview for visual QA. |
