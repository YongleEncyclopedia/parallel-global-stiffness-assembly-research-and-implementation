# Cross-Platform CPU Benchmark Schema Report

This report checks schema compatibility, baseline completeness, and interpretation guardrails.
It is not a platform performance ranking.

## Guardrails

- Do not interpret hardware, compiler, operating-system, affinity, or OpenMP runtime differences as pure algorithm differences.
- Do not compare incomplete platform profiles as if they were complete CPU characterizations.
- Treat `full_host`, `performance_core_only`, and `efficiency_core_only` as resource profiles under one CPU platform, not separate CPU models.

## Packages

| Platform | Run profile | CPU model | Records | Profile status |
| --- | --- | --- | ---: | --- |
| `apple-m4-max` | `full_host` | `Apple M4 Max` | 224 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `apple-m4-max` | `performance_core_only` | `Apple M4 Max` | 80 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `apple-m4-max` | `efficiency_core_only` | `Apple M4 Max` | 32 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `intel-u7-265kf` | `full_host` | `Intel(R) Core(TM) Ultra 7 265KF` | 320 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `intel-u7-265kf` | `performance_core_only` | `Intel(R) Core(TM) Ultra 7 265KF` | 64 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `intel-u7-265kf` | `efficiency_core_only` | `Intel(R) Core(TM) Ultra 7 265KF` | 96 | full_host=available, performance_core_only=available, efficiency_core_only=available |

## Validation

- No schema errors or completeness warnings.

## Current Interpretation Boundary

The package set is ready for merge/compatibility checks only. A performance conclusion table should be written only after each target CPU has its required `full_host` result and all applicable conditional core profiles are present or explicitly marked `not_applicable`.

<!-- core-profile-comparison-figures:start -->
## Core-Profile Acceleration Figures

The figures compare `full_host`, `performance_core_only`, and `efficiency_core_only` within each CPU platform using the `bound` environment and each algorithm's best assembly-time point.

### Apple M4 Max

![Apple M4 Max core-profile acceleration comparison](figures/core_profile_speedup_comparison_apple_m4_max.png)

[Apple M4 Max SVG](figures/core_profile_speedup_comparison_apple_m4_max.svg)

### Intel Core Ultra 7 265KF

![Intel Core Ultra 7 265KF core-profile acceleration comparison](figures/core_profile_speedup_comparison_intel_u7_265kf.png)

[Intel Core Ultra 7 265KF SVG](figures/core_profile_speedup_comparison_intel_u7_265kf.svg)
<!-- core-profile-comparison-figures:end -->
