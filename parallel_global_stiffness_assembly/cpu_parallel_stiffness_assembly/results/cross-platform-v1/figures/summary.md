# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/figures/summary.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Core-Profile Acceleration Comparison Figures

These figures compare `full_host`, `performance_core_only`, and `efficiency_core_only` within each CPU platform using the `bound` environment and each algorithm's best assembly-time point.

| Figure | PNG | SVG | Notes |
| --- | --- | --- | --- |
| Apple M4 Max | [png](core_profile_speedup_comparison_apple_m4_max.png) | [svg](core_profile_speedup_comparison_apple_m4_max.svg) | macOS QoS-biased sensitivity profiles; not hard-pinned core affinity. |
| Intel Core Ultra 7 265KF | [png](core_profile_speedup_comparison_intel_u7_265kf.png) | [svg](core_profile_speedup_comparison_intel_u7_265kf.svg) | Linux `taskset` affinity-restricted P/E-core profiles. |
