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
| `apple-m4-max` | `full_host` | `Apple M4 Max` | 224 | full_host=available, performance_core_only=missing, efficiency_core_only=missing |
| `intel-u7-265kf` | `full_host` | `Intel(R) Core(TM) Ultra 7 265KF` | 320 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `intel-u7-265kf` | `performance_core_only` | `Intel(R) Core(TM) Ultra 7 265KF` | 64 | full_host=available, performance_core_only=available, efficiency_core_only=available |
| `intel-u7-265kf` | `efficiency_core_only` | `Intel(R) Core(TM) Ultra 7 265KF` | 96 | full_host=available, performance_core_only=available, efficiency_core_only=available |

## Validation

### Warnings

- apple-m4-max is missing performance_core_only
- apple-m4-max is missing efficiency_core_only

## Current Interpretation Boundary

The package set is ready for merge/compatibility checks only. A performance conclusion table should be written only after each target CPU has its required `full_host` result and all applicable conditional core profiles are present or explicitly marked `not_applicable`.
