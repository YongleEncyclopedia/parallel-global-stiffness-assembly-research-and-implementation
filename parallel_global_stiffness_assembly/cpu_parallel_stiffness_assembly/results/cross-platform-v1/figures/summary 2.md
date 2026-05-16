# Core-Profile Acceleration Comparison Figures

These figures compare `full_host`, `performance_core_only`, and `efficiency_core_only` within each CPU platform using the `bound` environment and each algorithm's best assembly-time point.

| Figure | PNG | SVG | Notes |
| --- | --- | --- | --- |
| Apple M4 Max | [png](core_profile_speedup_comparison_apple_m4_max.png) | [svg](core_profile_speedup_comparison_apple_m4_max.svg) | macOS QoS-biased sensitivity profiles; not hard-pinned core affinity. |
| Intel Core Ultra 7 265KF | [png](core_profile_speedup_comparison_intel_u7_265kf.png) | [svg](core_profile_speedup_comparison_intel_u7_265kf.svg) | Linux `taskset` affinity-restricted P/E-core profiles. |
