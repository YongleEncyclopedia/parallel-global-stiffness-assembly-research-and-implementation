# Thread Scaling Figures Summary

本目录图表与 `plot_cpu_results.py` 的 benchmark 风格保持一致，PNG 用于 Markdown 浏览，SVG 用于放大或后续编辑。

| 图表 | PNG | SVG | 用途 |
| --- | --- | --- | --- |
| `thread_scaling_default_dashboard` | [png](thread_scaling_default_dashboard.png) | [svg](thread_scaling_default_dashboard.svg) | default 环境下四算法的时间、加速比、效率、内存和物理/超物理最佳对比。 |
| `thread_scaling_bound_dashboard` | [png](thread_scaling_bound_dashboard.png) | [svg](thread_scaling_bound_dashboard.svg) | bound 环境下四算法的时间、加速比、效率、内存和物理/超物理最佳对比。 |
| `thread_scaling_by_algorithm_cpu_atomic` | [png](thread_scaling_by_algorithm_cpu_atomic.png) | [svg](thread_scaling_by_algorithm_cpu_atomic.svg) | 单算法 default/bound 详细线程扩展曲线。 |
| `thread_scaling_by_algorithm_cpu_private_csr` | [png](thread_scaling_by_algorithm_cpu_private_csr.png) | [svg](thread_scaling_by_algorithm_cpu_private_csr.svg) | 单算法 default/bound 详细线程扩展曲线。 |
| `thread_scaling_by_algorithm_cpu_row_owner` | [png](thread_scaling_by_algorithm_cpu_row_owner.png) | [svg](thread_scaling_by_algorithm_cpu_row_owner.svg) | 单算法 default/bound 详细线程扩展曲线。 |
| `thread_scaling_by_algorithm_cpu_graph_coloring` | [png](thread_scaling_by_algorithm_cpu_graph_coloring.png) | [svg](thread_scaling_by_algorithm_cpu_graph_coloring.svg) | 单算法 default/bound 详细线程扩展曲线。 |
| `thread_scaling_memory_by_env` | [png](thread_scaling_memory_by_env.png) | [svg](thread_scaling_memory_by_env.svg) | 两组环境下额外内存随线程数变化，突出 private_csr 的内存压力。 |
| `thread_scaling_physical_vs_oversubscription` | [png](thread_scaling_physical_vs_oversubscription.png) | [svg](thread_scaling_physical_vs_oversubscription.svg) | 物理核内最佳与超物理最佳直接对比，支撑继续加速/持平/变慢判断。 |
| `thread_scaling_stage_breakdown_best` | [png](thread_scaling_stage_breakdown_best.png) | [svg](thread_scaling_stage_breakdown_best.svg) | 各环境/算法最佳线程点的阶段拆分，用于解释瓶颈。 |
| `thread_scaling_contact_sheet` | [png](thread_scaling_contact_sheet.png) | - | 核心图缩略总览。 |
