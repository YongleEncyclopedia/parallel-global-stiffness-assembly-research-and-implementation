# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-12-thread-scaling-linux-intel-hybrid-core-supplement.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Intel P/E-Core Isolation Supplement

## Scope

This supplement keeps `results/2026-05-11-thread-scaling-linux-intel` as the mixed Linux Intel baseline and adds two affinity-restricted sensitivity runs:

- P-core-only: `taskset -c 0-7`, output root `results/2026-05-12-thread-scaling-linux-intel-pcore`
- E-core-only: `taskset -c 8-19`, output root `results/2026-05-12-thread-scaling-linux-intel-ecore`

The run only covers the four main CPU algorithms: `atomic`, `private_csr`, `row_owner`, and `coloring`. It does not reopen the symbolic/numeric path and does not include `coo_sort_reduce`.

## Host And Affinity Evidence

- CPU model: `Intel(R) Core(TM) Ultra 7 265KF`
- Online CPUs: `0-19`
- Threads per core: `1`
- SMT control: `notsupported`
- `cpu_capacity` grouping:
  - P-core tier: CPU `0-7`, capacity `1008` or `1024`
  - E-core tier: CPU `8-19`, capacity `736`

The generated benchmark CSV files still report host-level `physical_cores=20` and `logical_cores=20`. For the P/E-core-only runs, the effective hardware restriction is the outer `taskset` command above, not the CSV physical/logical core fields.

## Commands

```bash
cmake --build build/cpu-release -j
ctest --test-dir build/cpu-release --output-on-failure

taskset -c 0-7 python3 scripts/run_thread_scaling_eval.py \
  --skip-build \
  --threads-range 1:8 \
  --warmup 1 \
  --repeat 3 \
  --out-root results/2026-05-12-thread-scaling-linux-intel-pcore

taskset -c 8-19 python3 scripts/run_thread_scaling_eval.py \
  --skip-build \
  --threads-range 1:12 \
  --warmup 1 \
  --repeat 3 \
  --out-root results/2026-05-12-thread-scaling-linux-intel-ecore

python3 scripts/plot_thread_scaling_results.py \
  --results-root results/2026-05-12-thread-scaling-linux-intel-pcore

python3 scripts/plot_thread_scaling_results.py \
  --results-root results/2026-05-12-thread-scaling-linux-intel-ecore
```

## Validation

- Release build completed successfully.
- `ctest`: `4/4` tests passed.
- Mixed baseline: `320` combined rows, `2` env groups, `4` algorithms, thread range `1..40`, `non_pass=0`.
- P-core-only: `64` combined rows, `2` env groups, `4` algorithms, thread range `1..8`, `non_pass=0`.
- E-core-only: `96` combined rows, `2` env groups, `4` algorithms, thread range `1..12`, `non_pass=0`.
- Each new output root contains:
  - `thread_scaling_combined.csv`
  - `default/thread_scaling_default.csv`
  - `bound/thread_scaling_bound.csv`
  - `thread_scaling_report.md`
  - `figures/summary.md`
  - `figures/thread_scaling_contact_sheet.png`
  - `10` PNG figures and `9` SVG figures

## Bound Best-Time Comparison

The table below uses `bound` as the primary interpretation group. Runtime changes within `5%` are treated as roughly flat.

| Algorithm | Mixed bound best | P-core-only bound best | P vs mixed | E-core-only bound best | E vs mixed | E vs P |
| --- | ---: | ---: | --- | ---: | --- | --- |
| `cpu_atomic` | `28T`, `158.345 ms` | `8T`, `204.800 ms` | slower by `29.3%` | `12T`, `202.992 ms` | slower by `28.2%` | within `5%` |
| `cpu_private_csr` | `7T`, `272.294 ms` | `7T`, `274.061 ms` | within `5%` | `7T`, `372.414 ms` | slower by `36.8%` | slower by `35.9%` |
| `cpu_row_owner` | `20T`, `159.806 ms` | `8T`, `189.616 ms` | slower by `18.7%` | `12T`, `188.142 ms` | slower by `17.7%` | within `5%` |
| `cpu_graph_coloring` | `38T`, `211.668 ms` | `8T`, `249.501 ms` | slower by `17.9%` | `12T`, `231.924 ms` | slower by `9.6%` | E-core-only faster by `7.0%` |

## Interpretation Boundary

These results show hybrid-core sensitivity under different available CPU resource sets. They should not be written as intrinsic algorithm superiority caused only by P-core or E-core type. The mixed baseline has access to all cores and, for some algorithms, oversubscribed software threads; the P/E-only runs intentionally cap the available hardware resources.

<!-- core-profile-comparison-figure:start -->
## Core-Profile Acceleration Figure

This figure visualizes the same `taskset` affinity-restricted P/E-core data summarized above.

### Intel Core Ultra 7 265KF

![Intel Core Ultra 7 265KF core-profile acceleration comparison](cross-platform-v1/figures/core_profile_speedup_comparison_intel_u7_265kf.png)

[Intel Core Ultra 7 265KF SVG](cross-platform-v1/figures/core_profile_speedup_comparison_intel_u7_265kf.svg)
<!-- core-profile-comparison-figure:end -->
