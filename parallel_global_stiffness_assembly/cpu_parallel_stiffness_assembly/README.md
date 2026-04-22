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
- [实现说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/implementation_notes.md>)
- [Mac Studio 验证记录](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/macstudio-validation-2026-04-22.md>)

## 关于 GPU 历史内容

仓库中仍保留少量 CUDA/GPU 时代的源码和脚本，仅作为历史参考，不属于当前 CPU 主线。

当前继续开发时请只看：

- 本 README
- `docs/requirements/cpu-parallel-stiffness-assembly-design.md`
- `docs/plans/2026-04-22-chatgpt-pro-handoff.md`
- `docs/cpu/`
- `scripts/run_cpu_experiments.py`
- `scripts/plot_cpu_results.py`
