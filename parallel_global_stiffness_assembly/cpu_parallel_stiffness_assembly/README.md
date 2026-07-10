# CPU 并行整体刚度矩阵组装主线目录

## 用途

保存 CMake 项目、源码、脚本、测试、报告和结果证据。

本项目是直接在源码树中构建、验证和运行的研究平台；当前不提供受支持的 SDK 或软件包安装契约。

## 存放内容

- 直接文件：`.gitignore`、`CMakeLists.txt`、`CMakePresets.json`、`README.md`、`build_and_test.bat`、`build_and_test.ps1`、`build_now.bat`、`build_simple.bat`、`compile_and_test.bat`、`configure_and_build.bat` 等 14 个直接文件
- 子目录：`apps/`、`cmake/`、`docs/`、`examples/`、`include/`、`legacy_gpu/`、`reports/`、`results/`、`scripts/`、`src/`、`tests/`

## 不应存放

新的 GPU 主线开发或无关项目文件。

## 维护提示

这是当前唯一有效主线；新增人读文档默认中文。

根部独立文件的维护理由：

- `CMakeLists.txt`：CMake 项目入口，必须放在本目录根部，供 `cmake -S .` 直接发现。
- `CMakePresets.json`：CMake presets 的固定入口文件，JSON 不支持注释，因此维护说明写在这里而不是写进文件头。
- `build_*.bat`、`compile_and_test.bat`、`configure_and_build.bat`、`quick_build.bat`、`build_and_test.ps1`：历史 Windows/CUDA 一键构建脚本，保留在根部是为了能从模块根目录直接运行；它们不是当前 macOS/Linux CPU 主线的首选入口。
- `minimal_verify*.cu`、`quick_verify.cu`：早期 CUDA warp aggregation 独立验证程序，放在根部是为了独立 `nvcc` 编译；当前 CPU 主线只把它们当历史参考。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly](../README.md)
- 子目录：[`apps/`](apps/README.md)
- 子目录：[`cmake/`](cmake/README.md)
- 子目录：[`docs/`](docs/README.md)
- 子目录：[`examples/`](examples/README.md)
- 子目录：[`include/`](include/README.md)
- 子目录：[`legacy_gpu/`](legacy_gpu/README.md)
- 子目录：[`reports/`](reports/README.md)
- 子目录：[`results/`](results/README.md)


## 原有说明

以下保留本文件原有的详细说明；本节之前的内容是统一补充的中文目录维护说明。

# CPU 并行整体刚度矩阵组装平台

本目录是当前仓库唯一有效的 CPU 主线项目，用于在共享内存多核 CPU 平台上研究和验证整体刚度矩阵并行组装算法。

当前目标已经不是“从零开始做 CPU 原型”，而是把现有代码推进成一套**可复现实验平台**：

- 统一算法入口
- 统一网格、CSR 与 scatter plan
- 统一 benchmark 口径
- 统一 correctness / memory / assembly-time 三项基础评价指标
- 统一图表与结果归档
- 可在真实工程网格上重复实验

后续所有整体刚度矩阵组装算法都必须先进入三项基础评价体系：正确性、内存占用、组装耗时。正式口径见：

- [整体刚度矩阵组装三项基础评价指标](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/basic_evaluation_metrics.md>)

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

- [CPU 并行算法说明](<docs/cpu/cpu_algorithms.md>)

## 当前支持的输入与 stiffness model

- 规则网格：
  - `Tet4`
  - `Hex8`
- Abaqus `.inp`：
  - `*NODE`
  - `*ELEMENT, TYPE=C3D4`
  - `*ELEMENT, TYPE=C3D8`
- 局部刚度矩阵模型：
  - Canonical CLI：`--stiffness-model linear_elastic_solid`
  - 含义：3D small-strain linear elastic solid stiffness model。
  - Tet4/C3D4：调用 constant-strain Tet4 物理局部刚度矩阵实现。
  - Hex8/C3D8：调用 2x2x2 Gauss full integration Hex8/C3D8 线弹性实现。
  - Legacy alias：`--kernel physics_solid` 仍映射到 `linear_elastic_solid`；`--kernel physics_tet4` 只作为 Tet4/C3D4-only 历史入口。
  - Legacy synthetic：`simplified` 已降级为 `legacy_synthetic` smoke/provenance 模型，必须显式加 `--allow-legacy-synthetic` 才能运行，不再作为当前 benchmark 结论依据。

## 求解级 validation 导出

`validation_export` 固化求解级正确性闭环的输入资产：C++ 只负责组装并导出 $K$、$f$、边界条件、probes 和 metadata，MATLAB 读取自研 $K$ 求解位移，Abaqus、COMSOL 或其他可信有限元链路的位移 CSV 作为独立参考。完整契约见[跨平台求解器 validation 协议](../../docs/platform/cross-platform-validation-protocol.md)。

默认无量纲悬臂块参数：

- $L=1$、$W=0.2$、$T=0.1$
- $E=1$、$\nu=0.3$
- $x=0$ 固定三向位移
- $x=L$ 端面施加总量归一化的向下力，默认 `load_dof=2`、`total_load=-1`

小型 smoke：

```bash
./build/cpu-release/bin/validation_export \
  --case cantilever_hex8_small \
  --stiffness-model linear_elastic_solid \
  --out-dir /tmp/validation-hex8-small \
  --prefix hex8_small
```

MATLAB 求解自研矩阵：

```matlab
addpath("scripts")
solve_validation_export_matlab("/tmp/validation-hex8-small", "hex8_small")
```

通用参考求解器/MATLAB probe 对比报告：

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab /tmp/validation-hex8-small/hex8_small_matlab_displacements.csv \
  --reference /path/to/abaqus_displacements.csv \
  --reference-solver abaqus \
  --reference-index-base 1 \
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

该脚本默认导出 `cantilever_hex8_small`、`cantilever_hex8_medium`、`cantilever_tet4_small` 和 `cantilever_tet4_medium`，并写入 `validation_export_manifest.json`。未传 `--run-matlab` 时，manifest 明确记录 `export-only/SKIPPED`。有限元 probe 位移对比不设硬阈值，报告位移向量的绝对差异、相对差异和自由端挠度幅值百分比差异，并通过 `validation_level=finite_element_probe` 区分于矩阵级正确性。

## 三项基础评价 smoke

后续新增算法至少要能通过小网格三指标 smoke，覆盖串行直接组装、串行符号加串行数值、并行直接组装、并行符号加并行数值四类路径：

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

输出必须包含 `evaluation_schema_version=pgsa-basic-metrics-v1`、`matrix_correctness_status`、`estimated_peak_bytes`、`isolated_peak_rss_mb`、`serial_direct_baseline_ms` 和 `speedup_vs_serial_direct` 等字段。三项基础评价的加速比统一相对 `direct_no_symbolic_serial`，而不是相对候选算法自己的单线程版本。

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
  --stiffness-model linear_elastic_solid --warmup 1 --repeat 3 --check \
  --csv results/current/csv/cube_tet4_linear_elastic_solid.csv \
  --json results/current/json/cube_tet4_linear_elastic_solid.json \
  --summary-md results/current/summaries/cube_tet4_linear_elastic_solid.md
```

### 2. 真实工程网格：正式物理模型

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
  --stiffness-model linear_elastic_solid --warmup 1 --repeat 3 --check \
  --max-memory-gb 32 \
  --csv results/current/csv/windhub_linear_elastic_solid.csv
```

### 3. Legacy synthetic smoke

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 2 --ny 2 --nz 2 \
  --case-name legacy_synthetic_smoke \
  --algo serial,atomic \
  --threads-list 1,2 \
  --stiffness-model legacy_synthetic --allow-legacy-synthetic --check \
  --csv /tmp/legacy_synthetic_smoke.csv
```

`legacy_synthetic` 仅用于极小 smoke 或读取早期 provenance，不用于当前 mentor-facing 或 future benchmark 结论。

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

- [plot_cpu_results.py](scripts/plot_cpu_results.py)

支持一个或多个 CSV 输入，输出：

- 执行时间图
- 总时间图
- 加速比图
- 并行效率图
- 阶段拆分图
- 额外内存图
- 综合 dashboard
- 跨 case / stiffness model 对比图
- 中文 Markdown 摘要

图中会直接标出关键数值，不要求观众回看 CSV。

## 当前结果输出字段

当前核心 CSV/JSON 输出包含两层：`benchmark_assembly` 的后端线程扩展字段，以及 `symbolic_numeric_eval` 的三项基础评价字段。后续跨路径结论优先使用三项基础评价字段。

- `schema_version`
- `evaluation_schema_version`
- `metric_contract`
- `platform_id`
- `run_profile`
- `profile_note`
- `env_group`
- `preprocess_ms`
- `assembly_mean/min/max/std_ms`
- `total_mean/min/max/std_ms`
- `speedup`
- `speedup_vs_serial_direct`
- `serial_direct_baseline_ms`
- `efficiency`
- `preprocess_share`
- `rel_l2`
- `max_abs`
- `matrix_correctness_status`
- `extra_memory_bytes`
- `symbolic_persistent_bytes`
- `numeric_backend_extra_bytes`
- `direct_transient_bytes`
- `estimated_peak_bytes`
- `delta_vs_serial_direct_bytes`
- `isolated_peak_rss_mb`
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

- [CPU 并行算法说明](<docs/cpu/cpu_algorithms.md>)
- [符号组装与数值组装说明](<docs/cpu/symbolic_numeric_assembly.md>)
- [实现说明](<docs/cpu/implementation_notes.md>)
- [跨平台 benchmark schema 规范](<../../docs/platform/cross-platform-benchmark-schema.md>)
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

- [legacy_gpu/README.md](legacy_gpu/README.md)
- [archive_gpu_legacy.py](scripts/archive_gpu_legacy.py)

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
