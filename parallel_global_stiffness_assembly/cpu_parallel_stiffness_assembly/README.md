# CPU 并行整体刚度矩阵组装平台

本目录是当前仓库唯一有效的 CPU 主线项目，用于在共享内存多核 CPU 平台上研究和验证整体刚度矩阵并行组装算法。

当前目标已经不是“从零开始做 CPU 原型”，而是把现有代码推进成一套**可复现实验平台**：

- 统一算法入口
- 统一网格、CSR 与 scatter plan
- 统一 benchmark 口径
- 统一图表与结果归档
- 可在真实工程网格上重复实验

## 当前已实现的 CPU 算法

| CLI 名称 | 内部标识 | 说明 |
| --- | --- | --- |
| `serial` | `cpu_serial` | 串行基线，正确性与加速比基线 |
| `atomic` | `cpu_atomic` | OpenMP atomic 直接累加到共享 CSR |
| `lock_guard` | `cpu_lock_guard` | 每个 CSR entry 一个 `std::mutex`，用 `std::lock_guard` 保护写回 |
| `private_csr` | `cpu_private_csr` | 线程私有 CSR values + 确定性归并 |
| `coo_sort_reduce` | `cpu_coo_sort_reduce` | 线程私有 COO 贡献 + 全局排序规约 |
| `coloring` | `cpu_graph_coloring` | 贪心图着色，同色单元无冲突并行 |
| `row_owner` | `cpu_row_owner` | owner-computes / 行拥有者原型 |

详细实现说明见：

- [CPU 并行算法说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md>)

## 当前支持的输入与 kernel

- 规则网格：
  - `Tet4`
  - `Hex8`
- Abaqus `.inp`：
  - `*NODE`
  - `*ELEMENT, TYPE=C3D4`
  - `*ELEMENT, TYPE=C3D8`
- 局部刚度 kernel：
  - `simplified`
  - `physics_tet4`
  - `physics_solid`：Tet4 复用物理 Tet4 核；Hex8 使用 Abaqus `C3D8` 对齐的 2x2x2 Gauss 全积分线弹性核。

## 求解级 validation 导出

`validation_export` 固化下周正确性闭环的输入资产：C++ 只负责组装并导出 `K/F/BC/probes/metadata`，MATLAB 读取自研 `K` 求解位移，Abaqus 位移 CSV 作为独立商业软件参考。

默认无量纲悬臂块参数：

- `L=1, W=0.2, T=0.1`
- `E=1, nu=0.3`
- `x=0` 固定三向位移
- `x=L` 端面施加总量归一化的向下力，默认 `load_dof=2, total_load=-1`

小型 smoke：

```bash
./build/cpu-release/bin/validation_export \
  --case cantilever_hex8_small \
  --kernel physics_solid \
  --out-dir /tmp/validation-hex8-small \
  --prefix hex8_small
```

MATLAB 求解自研矩阵：

```matlab
addpath("scripts")
solve_validation_export_matlab("/tmp/validation-hex8-small", "hex8_small")
```

Abaqus/MATLAB probe 对比报告：

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab /tmp/validation-hex8-small/hex8_small_matlab_displacements.csv \
  --abaqus /path/to/abaqus_displacements.csv \
  --probes /tmp/validation-hex8-small/hex8_small_probes.csv \
  --out-csv /tmp/validation-hex8-small/hex8_small_compare.csv \
  --out-md /tmp/validation-hex8-small/hex8_small_compare.md
```

Intel/Linux 主线复跑建议使用：

```bash
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-release/bin/validation_export \
  --out-root results/validation-export/intel-linux \
  --run-matlab \
  --matlab-bin matlab
```

该脚本默认导出 `cantilever_hex8_small`、`cantilever_tet4_small`、`cantilever_hex8_medium` 和 `cantilever_tet4_medium`，并写入 `validation_export_manifest.json`。Abaqus 对比不设硬阈值，报告相对差异、绝对差异、最大差异位置和解释状态。

## 构建

```bash
git lfs pull
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
/opt/homebrew/bin/cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON
/opt/homebrew/bin/cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
```

如果本机 `cmake` 已经在 `PATH` 上，可以去掉 `/opt/homebrew/bin/` 前缀。

macOS + AppleClang 环境建议先安装：

```bash
brew install cmake libomp git-lfs
git lfs install
```

## 标准实验流程

### 1. 小型规则网格

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 8 --ny 8 --nz 8 \
  --case-name cube_tet4_8x8x8 \
  --algo serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner \
  --threads-all \
  --kernel simplified --warmup 1 --repeat 3 --check \
  --csv results/2026-04-22/csv/cube_tet4_simplified.csv \
  --json results/2026-04-22/json/cube_tet4_simplified.json \
  --summary-md results/2026-04-22/summaries/cube_tet4_simplified.md
```

### 2. 真实工程网格：先 `simplified`

必须优先使用仓库内 Git LFS 管理的标准路径：

```text
../../examples/3d-WindTurbineHub.inp
```

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner \
  --threads-all \
  --kernel simplified --warmup 1 --repeat 3 --check \
  --max-memory-gb 32 \
  --csv results/2026-04-22/csv/windhub_simplified.csv
```

### 3. 真实工程网格：再 `physics_tet4`

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,private_csr,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel physics_tet4 --warmup 0 --repeat 2 --check \
  --max-memory-gb 32 \
  --csv results/2026-04-22/csv/windhub_physics_tet4.csv
```

如果 `.inp` 文件仍然是 Git LFS pointer，程序会直接报错提示先执行 `git lfs pull`。

## 一键实验脚本

如果希望按当前推荐矩阵直接跑完整实验并自动画图：

```bash
python3 scripts/run_cpu_experiments.py
```

该脚本会自动生成：

- `results/YYYY-MM-DD/csv/`
- `results/YYYY-MM-DD/json/`
- `results/YYYY-MM-DD/summaries/`
- `results/YYYY-MM-DD/figures/`

## 绘图

当前 CPU 绘图脚本：

- [plot_cpu_results.py](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/plot_cpu_results.py)

支持一个或多个 CSV 输入，输出：

- 执行时间图
- 总时间图
- 加速比图
- 并行效率图
- 阶段拆分图
- 额外内存图
- 综合 dashboard
- 跨 case / kernel 对比图
- 中文 Markdown 摘要

图中会直接标出关键数值，不要求观众回看 CSV。

## 当前结果输出字段

当前 benchmark CSV/JSON 已包含：

- `schema_version`
- `platform_id`
- `run_profile`
- `profile_note`
- `env_group`
- `preprocess_ms`
- `assembly_mean/min/max/std_ms`
- `total_mean/min/max/std_ms`
- `speedup`
- `efficiency`
- `preprocess_share`
- `rel_l2`
- `max_abs`
- `extra_memory_bytes`
- `peak_rss_mb`
- `colors`
- 算法阶段字段：
  - `prepare_allocate_ms`
  - `prepare_coloring_ms`
  - `prepare_owner_partition_ms`
  - `assembly_zero_ms`
  - `assembly_generate_ms`
  - `assembly_numeric_ms`
  - `assembly_merge_ms`
  - `assembly_sort_ms`
  - `assembly_reduce_ms`

## 相关文档

- [CPU 并行算法说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md>)
- [符号组装与数值组装说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md>)
- [实现说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/implementation_notes.md>)
- [跨平台 benchmark schema 规范](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/docs/platform/cross-platform-benchmark-schema.md>)
- [当前知识边界与事实优先级](../../docs/context/current-knowledge-boundary.md)

## 跨平台 benchmark 包

运行新 CPU 平台测试前，先执行：

```bash
python3 scripts/inspect_cpu_platform.py
```

必须先说明当前 CPU 是否存在性能核/能效核差异；如果能可靠隔离，就采集 `full_host`、`performance_core_only`、`efficiency_core_only` 三类 profile。不能隔离或不适用时，必须在结果包中标记 `missing` 或 `not_applicable`。

当前统一包与规范性报告位于：

- `results/cross-platform-v1/`

## 关于 GPU 历史内容

仓库中仍保留少量 CUDA/GPU 时代的源码和脚本，仅作为历史参考，不属于当前 CPU 主线。

如果要把这些历史内容从默认入口里系统归档，请使用：

- [legacy_gpu/README.md](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/legacy_gpu/README.md)
- [archive_gpu_legacy.py](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/archive_gpu_legacy.py)

可先 dry-run：

```bash
python3 scripts/archive_gpu_legacy.py --project . --dry-run
```

当前继续开发时请只看：

- 本 README
- `docs/requirements/cpu-parallel-stiffness-assembly-design.md`
- `docs/plans/2026-04-22-chatgpt-pro-handoff.md`
- `docs/cpu/`
- `scripts/run_cpu_experiments.py`
- `scripts/run_symbolic_numeric_eval.py`
- `scripts/plot_cpu_results.py`
