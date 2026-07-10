# 整体刚度矩阵组装三项基础评价指标

本文件定义后续所有整体刚度矩阵组装算法必须遵循的基础评价口径。任何新算法、并行策略或内存优化都必须先进入这套口径，再讨论是否值得保留。

## 固定顺序

1. 正确性：先证明候选算法没有改变矩阵和有限元物理结果。
2. 内存占用：再比较候选算法相对基础直接组装的存储压力。
3. 组装耗时：最后比较从网格已准备好到全局刚度矩阵完成的耗时和加速比。

性能结论必须在正确性通过之后才有意义。没有正确性证据的耗时或内存数字只能作为调试信息，不作为算法优劣结论。

## 1. 正确性

正确性分两层。

### 矩阵级正确性

候选算法得到的全局刚度矩阵必须与参考矩阵比较，并记录：

- `rel_l2`：相对 L2 误差。
- `max_abs`：最大绝对误差。
- `matrix_correctness_status`：`PASS` / `FAIL`。
- `matrix_correctness_reference_strategy`：本轮比较使用的参考策略。

`symbolic_numeric_eval` 的三指标 smoke 默认把 `direct_no_symbolic_serial` 作为矩阵正确性参考；如果显式过滤掉该模式，则退回到 `serial_symbolic_serial_numeric` 参考，并必须在结果字段中记录。

### 求解级正确性

矩阵级正确性不足以证明有限元问题可用。正式 validation 还必须进入求解流程：

- C++ `validation_export` 导出 $K$、$f$、边界条件、probes、nodes、elements 和 metadata。
- MATLAB 读取自研 $K$、$f$ 和边界条件并求解位移。
- COMSOL、Abaqus 或其他可信独立链路输出同一 probe 的位移参考。
- `compare_validation_displacements.py` 输出 `validation_level=finite_element_probe`、`reference_solver`、`abs_diff`、`rel_diff` 和 `fe_result_correctness_status`。

本项目的悬臂块求解级主指标固定为自由端挠度幅值相对差异百分比，不再用所有 probe 的最大 `rel_diff` 作为最终正确性口径。对 MATLAB 位移 $u_p$ 和参考位移 $u_r$，自由端指标定义为

$$
d_{\mathrm{tip},\%}=100\,
\frac{\left|\lVert u_p\rVert_2-\lVert u_r\rVert_2\right|}
{\max\!\left(\lVert u_r\rVert_2,10^{-30}\right)}.
$$

$u_p$ 来自 MATLAB 对自研 C++ 导出系统的求解结果，$u_r$ 来自 COMSOL、Abaqus、CalculiX 或其他独立有限元参考。当前 probe 级资产默认使用 `free_tip_center`。`rel_diff` 字段是逐 probe 三维位移向量范数差异的诊断量，用来排查载荷方向、节点映射和中间截面趋势，不作为硬阈值。

求解级比较默认不设硬阈值；报告必须说明自由端挠度幅值相对差异百分比、位移向量绝对差异、对应 reference solver 和解释状态。

## 2. 内存占用

内存字段必须按来源和生命周期分层，不允许只给一个笼统峰值。

| 字段 | 含义 | 来源 |
| --- | --- | --- |
| `symbolic_persistent_bytes` | CSR 结构和值数组加 AssemblyPlan 的持久内存 | exact model |
| `symbolic_temporary_bytes` | 并行符号组装的临时结构 | estimated |
| `numeric_backend_extra_bytes` | 数值后端额外内存，例如 private CSR 或 lock array | exact/estimated by backend |
| `direct_transient_bytes` | 无符号直接组装贡献 buffer | estimated |
| `estimated_peak_bytes` | 生命周期模型估计峰值 | estimated lifecycle model |
| `delta_vs_serial_direct_bytes` | 相对 `direct_no_symbolic_serial` 的估计峰值差 | derived |
| `isolated_peak_rss_mb` | 独立子进程观测到的峰值 RSS | OS observed |

基础内存对比对象是 `memory_reference_strategy=direct_no_symbolic_serial`。多线程 RSS 容易受同进程历史峰值污染；需要严肃比较 RSS 时，使用 `scripts/run_isolated_symbolic_memory_eval.py` 逐策略独立进程测量，并在报告中说明重复次数和平台环境。

## 3. 组装耗时

统一时间范围是：

```text
time_scope = mesh_ready_to_matrix_assembled
```

也就是说，从网格和输入数据已经准备好之后开始，到整体刚度矩阵组装完成为止。文件读取、图表生成、报告生成和外部 packaging 不计入主组装耗时。

直接组装路径的耗时包括：

- 单元刚度矩阵计算。
- 贡献生成。
- bucket / merge。
- sort / reduce。
- 写入或形成全局矩阵。

符号加数值路径的耗时包括：

- `symbolic_csr_ms`
- `symbolic_plan_ms`
- `symbolic_total_ms`
- `numeric_ms`
- `amortized_total_ms`

加速比统一字段是：

```text
speedup_vs_serial_direct = serial_direct_baseline_ms / assembly_or_amortized_ms
speedup_baseline_strategy = direct_no_symbolic_serial
```

`benchmark_assembly` 中已有的 `speedup` 仍可用于后端内部线程扩展分析，但它不是三项基础评价指标的最终加速比字段。跨路径比较必须优先看 `symbolic_numeric_eval` 输出的 `speedup_vs_serial_direct`。

## 必须覆盖的四类路径

三指标 smoke 至少覆盖：

| 路径 | `symbolic_numeric_eval` mode | 说明 |
| --- | --- | --- |
| 串行直接组装 | `direct_no_symbolic_serial` | 基础 correctness、memory、time 基线 |
| 串行符号组装 + 串行数值组装 | `symbolic_reuse_serial` | 符号结构复用基线 |
| 并行直接组装 | `direct_no_symbolic_parallel` | 不复用 CSR/scatter plan 的并行背景路径 |
| 并行符号组装 + 并行数值组装 | `parallel_symbolic_reuse` | 当前主要并行候选路径 |

`serial_symbolic_parallel_numeric` 是重要对照：它固定串行符号构建，只并行化数值后端，用于判断符号阶段是否值得并行化。

## 小网格 smoke

```bash
build/cpu-release/bin/symbolic_numeric_eval \
  --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 \
  --stiffness-model linear_elastic_solid \
  --assemblies-list 1 \
  --threads-list 1,2 \
  --backend-list atomic,lock_guard \
  --mode-list direct_no_symbolic_serial,symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel \
  --csv /tmp/pgsa_basic_metrics_smoke.csv \
  --json /tmp/pgsa_basic_metrics_smoke.json \
  --summary-md /tmp/pgsa_basic_metrics_smoke.md
```

期望输出中至少包含：

- `evaluation_schema_version=pgsa-basic-metrics-v1`
- `metric_contract=correctness_memory_time_v1`
- `matrix_correctness_status`
- `memory_reference_strategy`
- `time_scope`
- `serial_direct_baseline_ms`
- `speedup_vs_serial_direct`
- `delta_vs_serial_direct_bytes`

## 工程算例建议命令

真实 WindHub 路径可能耗时较长，尤其是 `direct_no_symbolic_serial` 和 `direct_no_symbolic_parallel`。正式工程复跑建议先单次、少线程确认 schema：

```bash
build/cpu-release/bin/symbolic_numeric_eval \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --stiffness-model linear_elastic_solid \
  --assemblies-list 1 \
  --threads-list 1,4,8 \
  --backend-list atomic,private_csr,lock_guard \
  --max-memory-gb 32 \
  --csv results/current/basic_metrics/windhub_basic_metrics.csv \
  --json results/current/basic_metrics/windhub_basic_metrics.json \
  --summary-md results/current/basic_metrics/windhub_basic_metrics.md
```

若需要进程级 RSS，追加隔离测量：

```bash
python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval \
  --out-root results/current/basic_metrics/isolated_rss \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --stiffness-model linear_elastic_solid \
  --assemblies-list 1 \
  --threads-list 1,4,8 \
  --backend-list atomic,private_csr,lock_guard \
  --max-memory-gb 32
```

## 与 schema v2 的关系

`package_cross_platform_results_v2.py` 会把现有 symbolic/benchmark CSV 提炼成 `basic_metrics` experiment family。`validate_benchmark_package_v2.py` 会检查 `basic_metrics` 记录是否包含正确性、内存和耗时三类字段。
