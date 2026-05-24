# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-14-mentor-next-steps-beamer/asset_manifest.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Beamer Asset Manifest

This manifest records project figures copied into `assets/` for `mentor_next_steps_beamer.tex`.

| Asset | Original source | Used for |
| --- | --- | --- |
| `assets/windhub_simplified_efficiency.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/03_efficiency_grouped_bars_03_windhub_simplified.png` | WindTurbineHub simplified assembly-overhead slide |
| `assets/windhub_physics_efficiency.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_efficiency_grouped_bars_04_windhub_physics_tet4.png` | WindTurbineHub physics_tet4 efficiency slide |
| `assets/windhub_physics_memory.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_memory_heatmap_04_windhub_physics_tet4.png` | physics_tet4 memory evidence |
| `assets/windhub_physics_correctness.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-12charts-repeat3-threads1to14/presentation_charts_12_v2/04_correctness_heatmap_04_windhub_physics_tet4.png` | physics_tet4 correctness evidence |
| `assets/intel_full_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling-linux-intel/figures/thread_scaling_bound_dashboard.png` | Intel full-host bound comparison |
| `assets/apple_full_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling/figures/thread_scaling_bound_dashboard.png` | Apple full-host bound comparison |
| `assets/intel_pcore_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-12-thread-scaling-linux-intel-pcore/figures/thread_scaling_bound_dashboard.png` | Intel P-core-only appendix |
| `assets/intel_ecore_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-12-thread-scaling-linux-intel-ecore/figures/thread_scaling_bound_dashboard.png` | Intel E-core-only appendix |
| `assets/apple_performance_qos_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-14-thread-scaling-macos-m4max-performance-qos/figures/thread_scaling_bound_dashboard.png` | Apple Performance QoS appendix |
| `assets/apple_efficiency_qos_bound_dashboard.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos/figures/thread_scaling_bound_dashboard.png` | Apple Efficiency QoS appendix |
| `assets/core_profile_apple_m4_max.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/figures/core_profile_speedup_comparison_apple_m4_max.png` | Apple P/E QoS profile summary |
| `assets/core_profile_intel_u7_265kf.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/figures/core_profile_speedup_comparison_intel_u7_265kf.png` | Intel P/E taskset profile summary |
| `assets/intel_full_physical_vs_oversubscription.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling-linux-intel/figures/thread_scaling_physical_vs_oversubscription.png` | Physical-core vs oversubscription boundary |
| `assets/apple_full_physical_vs_oversubscription.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling/figures/thread_scaling_physical_vs_oversubscription.png` | Physical-core vs oversubscription boundary |
| `assets/windhub_physics_tet4_spy_python.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_python.png` | WindHub serial/parallel sparse pattern, Python occupancy raster |
| `assets/windhub_physics_tet4_spy_matlab.png` | `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_matlab.png` | WindHub serial/parallel sparse pattern, MATLAB-generated spy-style figure |

## Text/Data Sources Used in Slides

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-symbolic-numeric/symbolic_numeric_eval_report.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-12-thread-scaling-linux-intel-hybrid-core-supplement.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-14-thread-scaling-macos-m4max-qos-supplement.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/cross_platform_schema_report.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/windhub_lock_vs_atomic.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_metadata.json`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/cross-platform-v2/cross_platform_schema_v2_report.md`
