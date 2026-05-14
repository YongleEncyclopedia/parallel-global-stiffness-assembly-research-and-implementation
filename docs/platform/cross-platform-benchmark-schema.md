# Cross-Platform CPU Benchmark Schema

## Purpose

This document defines the project-level benchmark package format for comparing CPU/OpenMP global stiffness assembly results across different CPU platforms.

The schema exists to make results mergeable. It must not be used to turn single-platform absolute runtime into cross-platform algorithm conclusions.

## Baseline v1

The v1 cross-platform baseline is fixed to:

- case: `3d-WindTurbineHub`
- kernel: `physics_tet4`
- algorithms: `cpu_atomic`, `cpu_private_csr`, `cpu_row_owner`, `cpu_graph_coloring`
- environment groups: `default`, `bound`
- schema version: `pgsa-cross-platform-v1`

`cpu_coo_sort_reduce` remains a research contrast path. It is not part of the v1 full baseline matrix.

## Required Package Fields

Each mergeable package must include:

- `schema_version`
- `platform_id`
- `run_profile`
- `profile_note`
- `baseline`
- `platform`
- `records`

Each record must carry:

- `schema_version`
- `platform_id`
- `run_profile`
- `env_group`
- `algorithm`
- `threads`
- timing, memory, status, correctness, and OpenMP environment fields

The C++ benchmark supports these metadata flags:

```bash
--schema-version pgsa-cross-platform-v1
--platform-id apple-m4-max
--run-profile full_host
--profile-note "full host run"
--env-group default
```

## Run Profiles

`full_host` is required for every CPU platform.

`performance_core_only` and `efficiency_core_only` are conditional profiles:

- Use them when the CPU has distinct P/E core classes and the platform can isolate those resources reliably.
- Mark them `not_applicable` on homogeneous CPUs, such as CPUs whose vendor specification does not define P/E core classes.
- Mark them `missing` when the CPU has P/E core classes but that profile has not been collected yet.

Do not invent P/E-only profiles for homogeneous CPUs.

## Mandatory Pre-Run Rule

Before running benchmarks on any new CPU platform, the AI/operator must:

1. Run `scripts/inspect_cpu_platform.py`.
2. State the detected CPU model, core-class evidence, and recommended profiles to the user.
3. Run all applicable profiles that can be isolated reliably.
4. If a profile is not applicable or missing, record the reason in `profile_note` or package metadata.

This rule is part of the benchmark protocol, not optional narration.

## Interpretation Boundary

Reports may discuss schema completeness, missing profiles, runtime environment, and guardrails.

Reports must not claim that a runtime difference is a pure algorithm difference unless hardware model, core profile, compiler, OS, OpenMP runtime, affinity settings, input case, kernel, algorithm set, and thread policy are all controlled or explicitly separated.

In particular, do not collapse these into one conclusion:

- Apple Silicon vs Intel/AMD microarchitecture
- performance-core-only vs efficiency-core-only resources
- compiler/runtime differences such as AppleClang/libomp vs GCC/libgomp vs MSVC/OpenMP
- default OpenMP scheduling vs bound `OMP_PROC_BIND` / `OMP_PLACES`
- full-host mixed-core runs vs core-restricted sensitivity runs

## Current Packages

The current normalized package set is under:

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/
```

It contains:

- `apple-m4-max/full_host`
- `intel-u7-265kf/full_host`
- `intel-u7-265kf/performance_core_only`
- `intel-u7-265kf/efficiency_core_only`

The current M4 Max package intentionally marks `performance_core_only` and `efficiency_core_only` as `missing`; no cross-platform performance conclusion table should be written until those profiles are collected or explicitly ruled out.

## Tooling

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

python3 scripts/inspect_cpu_platform.py

python3 scripts/validate_benchmark_package.py \
  results/cross-platform-v1/packages/apple-m4-max/full_host \
  results/cross-platform-v1/packages/intel-u7-265kf/full_host

python3 scripts/report_cross_platform_benchmark.py \
  results/cross-platform-v1/packages/apple-m4-max/full_host \
  results/cross-platform-v1/packages/intel-u7-265kf/full_host \
  --out results/cross-platform-v1/cross_platform_schema_report.md
```
