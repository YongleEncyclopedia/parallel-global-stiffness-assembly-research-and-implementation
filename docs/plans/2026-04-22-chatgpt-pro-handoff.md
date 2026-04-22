# CPU 并行整体刚度矩阵组装项目交接与下一阶段任务书

## 1. 文档目的

本文件用于交接当前 CPU 主线项目的真实状态、已完成验证、结果产物和后续任务。

这份文档面向继续开发者与大模型，不是背景介绍。后续开发应优先遵循：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md`
- `docs/requirements/cpu-parallel-stiffness-assembly-design.md`
- 本文档

## 2. 唯一主线目录

后续开发只能在以下目录继续进行：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

不要重新引入独立旁路项目，也不要把历史 `parallel_stiffness_assembly`、`cpu_parallel_assembly`、`pgsa_cpu_overlay` 等目录恢复成第二主线。

## 3. 当前阶段定位

项目已经不是“从零做 CPU 并行组装原型”的阶段，而是进入了**可复现实验平台阶段**。当前主线已经具备：

- 统一的 CPU 算法工厂和 benchmark CLI
- 规则网格与 Abaqus `.inp` 输入
- `simplified` 与 `physics_tet4` 两类局部刚度核
- 真实工程网格 `3d-WindTurbineHub.inp`
- 可重复运行的实验脚本、结果目录、图表脚本和摘要文档

当前重点不再是“再搭一套框架”，而是：

- 持续补强实验覆盖面
- 对比 CPU 并行算法在真实网格上的扩展性
- 把结果、图表和文档组织成可复现研究产物

## 4. 当前已经实现的能力

### 4.1 构建与平台

当前主项目已经 CPU-first：

- 默认语言：`CXX`
- 标准：`C++17`
- OpenMP：可选但默认优先启用
- AppleClang + Homebrew `libomp`：已兼容
- CMake：已可直接用于 CPU-only 配置和测试

### 4.2 已接入的 CPU 并行算法

当前主线已经实现并接入以下算法：

- `cpu_serial`
- `cpu_atomic`
- `cpu_private_csr`
- `cpu_coo_sort_reduce`
- `cpu_graph_coloring`
- `cpu_row_owner`

算法说明、实现机制、源码入口和适用场景见：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md`

### 4.3 网格、输入与预处理

当前主线已经具备：

- 规则块体网格生成
  - `Tet4`
  - `Hex8`
- Abaqus `.inp` 解析
  - `*NODE`
  - `*ELEMENT, TYPE=C3D4`
  - `*ELEMENT, TYPE=C3D8`
- Abaqus label 重映射
  - 1-based
  - 跳号 label
  - 内部 0-based index
- 对 `*OUTPUT` / `*NODE OUTPUT` / `*ELEMENT OUTPUT` 等无关 section 的安全跳过
- 统一 CSR 结构
- CSR symbolic / numeric 分离
- element-local 到 CSR value index 的 scatter plan 预计算

### 4.4 benchmark 与结果输出

当前 benchmark 已支持：

- `--threads-all`
- `--threads-range a:b[:step]`
- `--threads-list`
- `--case-name`
- `--json`
- `--summary-md`
- 固定相对 `1` 线程串行基线的 speedup
- 重复运行统计
  - `mean`
  - `min`
  - `max`
  - `std`
- 并行效率 `efficiency`
- 预处理占比 `preprocess_share`
- 额外内存 `extra_memory_bytes`
- 峰值 RSS `peak_rss_mb`
- OpenMP 环境字段
  - `omp_proc_bind`
  - `omp_places`
  - `omp_dynamic`
- 结构化状态
  - `PASS`
  - `SKIP`
  - `FAIL`

同时，算法内部阶段计时已细化：

- `private_csr`
  - `prepare_allocate_ms`
  - `assembly_zero_ms`
  - `assembly_numeric_ms`
  - `assembly_reduce_ms`
- `coo_sort_reduce`
  - `assembly_generate_ms`
  - `assembly_merge_ms`
  - `assembly_sort_ms`
  - `assembly_reduce_ms`
- `graph_coloring`
  - `prepare_coloring_ms`
  - `assembly_numeric_ms`
- `row_owner`
  - `prepare_owner_partition_ms`
  - `assembly_numeric_ms`

### 4.5 绘图与摘要

当前主线已有 CPU 专用绘图脚本：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/plot_cpu_results.py`

可自动输出：

- `assembly_ms`
- `total_ms`
- `speedup`
- `efficiency`
- `stage_breakdown`
- `extra_memory`
- `dashboard`
- `cross_case_best_speedup`
- `cross_kernel_best_speedup`
- 中文 Markdown 摘要

图中已直接标出具体数值，不再要求读者回看 CSV。

## 5. 当前标准运行流程

### 5.1 工程案例路径

真实工程网格统一使用：

```text
examples/3d-WindTurbineHub.inp
```

该文件由 Git LFS 管理。不要再改写成 `data/external/...` 或其它本机私有路径。

### 5.2 标准命令

```bash
git lfs pull

cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

/opt/homebrew/bin/cmake -S . -B build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON

/opt/homebrew/bin/cmake --build build/cpu-release --parallel 8
ctest --test-dir build/cpu-release --output-on-failure
```

完整实验矩阵：

```bash
python3 scripts/run_cpu_experiments.py
```

单独重绘图表：

```bash
python3 scripts/plot_cpu_results.py \
  results/2026-04-22/csv/cube_tet4_simplified.csv \
  results/2026-04-22/csv/windhub_simplified.csv \
  results/2026-04-22/csv/windhub_physics_tet4.csv \
  results/2026-04-22/csv/windhub_physics_tet4_coo_sort_reduce.csv \
  --out-dir results/2026-04-22/figures
```

如果程序读到的是 Git LFS pointer 而不是真实 `.inp` 文件，benchmark 会直接报错并提示重新执行 `git lfs pull`。

## 6. 已完成的本机验证

详细记录见：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/macstudio-validation-2026-04-22.md`

### 6.1 构建与测试

本机环境：

- Machine: Apple M4 Max
- OS / arch: `macOS;arm64`
- Compiler: `AppleClang 21.0.0.21000099`
- OpenMP runtime: Homebrew `libomp`
- CMake: `4.3.2`

当前已通过测试：

- `VerifyCpuAssemblers`
- `VerifyInpParser`

### 6.2 已完成实验

已完成的实验矩阵包括：

- `cube_tet4_8x8x8 + simplified`
  - 6 类算法
  - `1..14` 线程
- `3d-WindTurbineHub + simplified`
  - 6 类算法
  - `1..14` 线程
- `3d-WindTurbineHub + physics_tet4`
  - `serial, atomic, private_csr, coloring, row_owner`
  - `1,2,4,8,14` 线程
- `3d-WindTurbineHub + physics_tet4 + coo_sort_reduce`
  - `1,2,4` 线程
  - 作为高成本对照组

### 6.3 当前实测结论

真实工程网格 `3d-WindTurbineHub` 的已实测规模：

- 节点数：`228384`
- 单元数：`1113684`
- 总自由度：`685152`
- CSR NNZ：`27502200`

代表性结果：

| Case | 最快算法 | 最优线程 | 平均组装时间 | 最高加速比 |
| --- | --- | ---: | ---: | ---: |
| `WindHub + simplified` | `cpu_row_owner` | 14 | `55.141 ms` | `3.695x` |
| `WindHub + physics_tet4` | `cpu_private_csr` | 8 | `119.566 ms` | `4.686x` |

算法结论：

- `cpu_private_csr` 与 `cpu_row_owner` 是当前最值得继续深挖的两类 CPU 路线
- `cpu_atomic` 在真实网格上也具备较强竞争力，且实现和内存代价更直接
- `cpu_graph_coloring` 可稳定运行，但当前实现不是领先者
- `cpu_coo_sort_reduce` 正确但显著偏慢，更适合作为研究对照组而不是当前主推方案

## 7. 当前结果产物位置

当前实验结果已经按照日期归档到：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/
```

其中包括：

- `csv/`
- `json/`
- `summaries/`
- `figures/`

重点文件：

- `results/2026-04-22/csv/cube_tet4_simplified.csv`
- `results/2026-04-22/csv/windhub_simplified.csv`
- `results/2026-04-22/csv/windhub_physics_tet4.csv`
- `results/2026-04-22/csv/windhub_physics_tet4_coo_sort_reduce.csv`
- `results/2026-04-22/figures/summary.md`
- `results/2026-04-22/figures/3d-WindTurbineHub_simplified_dashboard.png`
- `results/2026-04-22/figures/3d-WindTurbineHub_physics_tet4_dashboard.png`

## 8. 当前仍需继续推进的任务

当前平台已经可复现，但仍有几项后续任务值得继续做：

1. 把 `physics_tet4` 的真实网格线程扫描从 `1,2,4,8,14` 扩展到完整 `1..N`
2. 为 `coo_sort_reduce` 增加更严格的资源保护与早停策略
3. 在 Windows + Intel 平台复跑同一实验矩阵，形成跨平台对照
4. 继续优化图表版式与论文级导出
5. 若需要对外汇报，可基于 `results/2026-04-22/figures/summary.md` 继续抽取一页式结论图

## 9. 当前不应重新带回主流程的内容

仓库里仍保留少量 GPU / CUDA 历史资产，仅作参考，不是当前开发入口。说明文档见：

- `docs/context/legacy-gpu-assets.md`

要求：

- 不要把 GPU 构建重新设成 CPU 主线的前置条件
- 不要重新使用旧 GPU 绘图脚本输出 CPU 结果
- 不要在 README、handoff、requirements 里把当前项目描述成 GPU-first

## 10. 交接时的最小检查清单

后续开发前，至少先确认：

1. `git lfs pull` 已执行，`examples/3d-WindTurbineHub.inp` 不是 pointer
2. `ctest --test-dir build/cpu-release --output-on-failure` 通过
3. 需要跑全量实验时，优先调用 `scripts/run_cpu_experiments.py`
4. 需要画图时，优先调用 `scripts/plot_cpu_results.py`
5. 需要解释算法时，优先参考 `docs/cpu/cpu_algorithms.md`
