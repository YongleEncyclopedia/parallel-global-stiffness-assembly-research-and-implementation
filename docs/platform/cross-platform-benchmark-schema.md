# 跨平台 CPU Benchmark Schema

## 用途

本文定义项目级 benchmark package 格式，用于比较不同 CPU 平台上的 CPU/OpenMP 整体刚度矩阵组装结果。

这个 schema 的目的，是让不同平台结果能够合并与追踪；它不能被用来把单平台绝对运行时间直接解释成跨平台算法结论。

## Baseline v1

v1 跨平台基线固定为：

- case：`3d-WindTurbineHub`
- stiffness_model：`linear_elastic_solid`
- 历史 kernel 字段：新 package 使用 `linear_elastic_solid`；历史 `physics_tet4` package 只作为 Tet4/C3D4 物理模型 provenance 继续可读。
- algorithms：`cpu_atomic`、`cpu_private_csr`、`cpu_row_owner`、`cpu_graph_coloring`
- environment groups：`default`、`bound`
- schema version：`pgsa-cross-platform-v1`

`cpu_coo_sort_reduce` 仍然是研究对照路线，不属于 v1 完整基线矩阵。

## 必需 Package 字段

每个可合并 package 必须包含：

- `schema_version`
- `platform_id`
- `run_profile`
- `profile_note`
- `baseline`
- `platform`
- `records`

每条 record 必须包含：

- `schema_version`
- `platform_id`
- `run_profile`
- `env_group`
- `algorithm`
- `threads`
- timing、memory、status、correctness 和 OpenMP environment 相关字段。

C++ benchmark 支持下面这些 metadata 参数：

```bash
--schema-version pgsa-cross-platform-v1
--platform-id apple-m4-max
--run-profile full_host
--profile-note "full host run"
--env-group default
```

## Run Profiles

每个 CPU 平台都必须提供 `full_host`。

`performance_core_only` 和 `efficiency_core_only` 是条件 profile：

- 当 CPU 存在明确 P/E core 分类，且平台能可靠隔离这些资源时使用。
- 对没有 P/E core 分类的同质 CPU，标记为 `not_applicable`。
- 对有 P/E core 但尚未采集的 profile，标记为 `missing`。

不要为同质 CPU 虚构 P/E-only profile。

## 运行前强制规则

在任何新 CPU 平台上跑 benchmark 前，AI/operator 必须：

1. 运行 `scripts/inspect_cpu_platform.py`。
2. 向用户说明检测到的 CPU 型号、core-class 证据和推荐 profile。
3. 运行所有可以可靠隔离的适用 profile。
4. 如果某个 profile 不适用或缺失，在 `profile_note` 或 package metadata 中记录原因。

这是 benchmark 协议的一部分，不是可选旁白。

## 解释边界

报告可以讨论 schema 完整性、缺失 profile、运行环境和解释护栏。

除非硬件型号、core profile、编译器、操作系统、OpenMP runtime、affinity 设置、输入 case、stiffness model、algorithm set 和 thread policy 都被控制或显式拆分，否则报告不得声称某个 runtime 差异是纯算法差异。

特别不要把下面因素压缩成一个结论：

- Apple Silicon 与 Intel/AMD microarchitecture 差异。
- performance-core-only 与 efficiency-core-only 资源差异。
- AppleClang/libomp、GCC/libgomp、MSVC/OpenMP 等编译器/runtime 差异。
- 默认 OpenMP scheduling 与绑定后的 `OMP_PROC_BIND` / `OMP_PLACES` 差异。
- full-host mixed-core 运行与 core-restricted sensitivity 运行差异。

## 当前 Package

当前 normalized package 位于：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/
```

其中包含：

- `apple-m4-max/full_host`
- `intel-u7-265kf/full_host`
- `intel-u7-265kf/performance_core_only`
- `intel-u7-265kf/efficiency_core_only`

当前 M4 Max package 故意把 `performance_core_only` 和 `efficiency_core_only` 标记为 `missing`；在这些 profile 被采集或明确排除前，不应写跨平台性能结论表。

## 工具命令

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

python3 scripts/inspect_cpu_platform.py

python3 scripts/validate_benchmark_package.py   results/cross-platform-v1/packages/apple-m4-max/full_host   results/cross-platform-v1/packages/intel-u7-265kf/full_host

python3 scripts/report_cross_platform_benchmark.py   results/cross-platform-v1/packages/apple-m4-max/full_host   results/cross-platform-v1/packages/intel-u7-265kf/full_host
```

这些命令中的路径和 schema key 保持英文，是为了与脚本和 package 字段一致。
