# 符号组装与数值组装说明

## 结论

当前 C++ 主线已经实现了 mentor 所说的“先符号组装，再数值/物理组装”的核心技术路线，只是此前没有在文档、CLI 输出和报告中显式使用这套术语。

在当前项目中：

- 符号组装：根据网格拓扑和 DOF 映射建立 CSR 稀疏结构，并预计算每个单元写入全局矩阵的 scatter 位置。
- 并行符号组装：按 row-owned 路径并行生成 CSR pattern，并按 element-owned 预分配 slice 并行生成 scatter plan；输出必须与串行符号组装逐项一致。
- 数值组装/物理组装：计算单元刚度矩阵 `Ke`，复用符号阶段结果填充全局刚度矩阵；`physics_tet4` 保持 Tet4 兼容主线，`physics_solid` 覆盖 Tet4 + Hex8/C3D8 求解级 validation。
- 无符号直接组装：不复用 CSR pattern 或 scatter plan，每次从单元 DOF 直接生成 `(row, col, value)` 贡献，再排序归并为全局矩阵。

## Mentor 示例与当前 C++ 的对应关系

| Mentor MATLAB 示例 | 当前 C++ 主线 | 关系 |
| --- | --- | --- |
| `build_mesh_topology` | `Mesh` 中的节点/单元连接关系 | C++ 已有 3D Tet4/Hex8 网格与 `.inp` 解析，不重写为 MATLAB 拓扑结构体 |
| `build_section` | `element_dofs()` 的节点 DOF 规则 | 当前主线每节点 3 DOF，未显式抽象 `section` |
| `get_cell_closure` | 单元连接节点集合 | 当前主线只需要节点 DOF，暂不显式枚举边/单元 closure |
| `build_cell_dofs` | `element_dofs()` 与 `AssemblyPlan::dofs` | 等价于生成并缓存每个单元的全局 DOF |
| `build_symbolic_pattern` | `CsrMatrix::build_sparsity()` | 等价于用单元 DOF 外积建立全局稀疏结构 |
| `allocate_global_matrix` | `CsrMatrix` 结构复用并清零 `values` | 等价于预分配结构、数值阶段只填值 |
| `assemble_numeric` | `cpu_serial` / `cpu_atomic` / `cpu_private_csr` 等 `assemble()` | 等价于计算 `Ke` 并写入全局矩阵 |
| `cellDofsCache` | `AssemblyPlan::dofs` | 直接对应 |
| 无直接对应项 | `AssemblyPlan::scatter` | C++ 比示例多缓存了 `Ke(i,j)` 到 CSR value 位置的映射，数值阶段不再查找 |

## 异同

共同点：

- 都是两阶段组装。
- 符号阶段只处理拓扑、DOF 和稀疏模式，不计算 `Ke`。
- 数值阶段复用符号阶段缓存，不重复做拓扑/DOF 结构分析。
- 多次组装时，符号阶段结果可以复用，从而摊销预处理成本。

差异：

- MATLAB 示例是 2D Tri3/CST 教学原型；当前 C++ 主线是 3D Tet4/Hex8 工程 benchmark。
- MATLAB 使用 1-based sparse；C++ 使用 0-based CSR。
- MATLAB 显式展示 PETSc-style `section/closure`；C++ 当前采用每节点固定 3 DOF 的直接映射。
- C++ 的 `AssemblyPlan::scatter` 更接近高性能实现，提前保存全局 CSR 写入位置。

## 是否参考 mentor 示例

参考，但不直接移植。

首阶段采用方式：

- 吸收 mentor 示例中的术语：符号组装、数值组装、`cellDofsCache`、预分配。
- 吸收 mentor 示例中的讲解结构：先解释拓扑/DOF/稀疏模式，再解释 `Ke` 计算和写入。
- 保留当前 C++ 的 CSR/scatter plan 设计，不引入 MATLAB 式 `section/closure` 重构。

不直接移植的原因：

- 示例是 2D、MATLAB、Tri3/CST，与当前 3D `physics_tet4` 主线不一致。
- 当前项目已经有可复用的 C++ CSR 和 scatter plan，实现层面更适合性能评估。
- 首阶段目标是回答效率问题，不是重构 DOF 抽象。

后续如果研究高阶单元、边 DOF、单元 DOF 或更接近 PETSc DMPlex 的通用拓扑抽象，再考虑引入显式 `Section` / `Closure` 层。

## 新增评估模式

新增独立程序 `symbolic_numeric_eval`，固定用于回答“符号组装是否带来效率收益”。

主线模式：

- `symbolic_reuse_serial`：构建一次 CSR/scatter plan，多次复用数值组装。
- `parallel_symbolic_reuse`：并行构建 CSR/scatter plan，再用指定 CPU backend 做数值组装；默认主线 backend 是 `cpu_atomic`，附录可用 `cpu_private_csr` 和 `cpu_lock_guard`。
- `direct_no_symbolic_serial`：不复用 CSR/scatter plan，每次生成 `(row,col,value)` 贡献并排序归并。
- `direct_no_symbolic_parallel`：不复用 CSR pattern 或 scatter plan；OpenMP 并行生成 `(row,col,value)`，按 row range bucket/merge，再对每个 bucket 排序规约。

控制实验：

- `symbolic_rebuild_serial`：每次都重建 CSR/scatter plan，再数值组装。它不是推荐使用场景，也不是 mentor 需求中的主比较对象；它用于隔离变量，说明符号组装收益到底来自“预计算 CSR/scatter”还是“预计算结果可被多次数值组装复用”。

关键输出字段：

- `symbolic_csr_ms`
- `symbolic_plan_ms`
- `symbolic_total_ms`
- `symbolic_temporary_bytes`
- `numeric_ms`
- `direct_generate_ms`
- `direct_bucket_merge_ms`
- `direct_sort_reduce_ms`
- `amortized_total_ms`
- `threads`
- `numeric_backend`

## 2026-05-22 validation 闭环入口

新增独立程序 `validation_export`，固定用于回答“自研组装得到的刚度矩阵是否能在真实小算例上求解出可解释位移”。

职责边界：

- C++：组装并导出 `K.mtx`、`force.csv`、`bc.csv`、`probes.csv`、`metadata.json`。
- MATLAB：读取自研 `K/F/BC`，施加约束并求解位移；输出 `*_matlab_displacements.csv` 和 `*_matlab_probe_summary.csv`。
- Abaqus：作为独立商业软件参考，导出 `abaqus_displacements.csv` 后由 Python 脚本与 MATLAB 位移进入同一差异表。

默认 validation case：

- `cantilever_hex8_small` / `cantilever_hex8_medium`：结构化 Hex8，对齐 Abaqus `C3D8` 全积分。
- `cantilever_tet4_small` / `cantilever_tet4_medium`：Tet4/C3D4 路径，用于确认既有物理核不退化。
- 悬臂块参数固定为 `L=1, W=0.2, T=0.1, E=1, nu=0.3`；`x=0` 固定，`x=L` 施加总量归一化向下力。

本轮不新增 C++ 求解器。求解阶段放在 MATLAB，是为了把“装配正确性”和“求解器实现正确性”解耦；Abaqus 对比不设置硬阈值，只输出绝对差异、相对差异、最大差异位置和解释状态。

示例：

```bash
./build/cpu-release/bin/validation_export \
  --case cantilever_hex8_small \
  --kernel physics_solid \
  --out-dir /tmp/validation-hex8-small \
  --prefix hex8_small

matlab -batch "addpath('scripts'); solve_validation_export_matlab('/tmp/validation-hex8-small','hex8_small')"

python3 scripts/compare_validation_displacements.py \
  --matlab /tmp/validation-hex8-small/hex8_small_matlab_displacements.csv \
  --abaqus /path/to/abaqus_displacements.csv \
  --probes /tmp/validation-hex8-small/hex8_small_probes.csv \
  --out-csv /tmp/validation-hex8-small/hex8_small_compare.csv \
  --out-md /tmp/validation-hex8-small/hex8_small_compare.md
```

下周 Intel/Linux 必跑结果建议由 `scripts/run_validation_export.py` 统一生成 manifest。主线性能矩阵仍固定 `cpu_atomic` 为数值组装后端，对比 `serial symbolic + serial numeric`、`parallel symbolic + cpu_atomic`、`direct/no-symbolic parallel`；`private_csr` 和 `cpu_lock_guard` 只作为已有基线或说明材料。

## 2026-05-16 WindHub 并行评估结果入口

本轮 mentor action-item 评估固定：

- case: `3d-WindTurbineHub`
- kernel: `physics_tet4`
- mesh: `228384` nodes, `1113684` elements, `685152` DOFs
- matrix: `nnz = 27502200`
- platform: Apple M4 Max, macOS arm64, OpenMP 202011
- thread sweep: `1..14` physical cores

主要产物：

- `results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.csv`
- `results/2026-05-16-mentor-action-items/windhub_parallel_symbolic_direct.md`
- `results/2026-05-16-mentor-action-items/cross-platform-v2/benchmark_package_v2.json`
- `results/2026-05-16-mentor-action-items/cross-platform-v2/cross_platform_schema_v2_report.md`

关键读数：

- `parallel_symbolic_reuse + cpu_atomic` 在 14 线程下：`symbolic_total_ms = 554.432`, `numeric_ms = 107.991`, `amortized_total_ms = 662.423`。
- `direct_no_symbolic_parallel` 在 14 线程下：`direct_generate_ms = 89.403`, `direct_bucket_merge_ms = 987.407`, `direct_sort_reduce_ms = 592.607`, `amortized_total_ms = 1669.417`。
- 同为 14 线程、单次组装时，parallel symbolic reuse 仍优于 direct/no-symbolic parallel，主要差距来自 direct 路径的 bucket/merge 和 sort/reduce 成本。
- 并行 symbolic 临时内存估计字段为 `symbolic_temporary_bytes = 149752608`；direct/no-symbolic contribution buffer 字段为 `direct_transient_bytes`，应与 OS peak RSS 分开解释。

## 推荐运行方式

小网格 smoke：

```bash
./build/cpu-release/bin/symbolic_numeric_eval \
  --mesh cube --element tet4 --nx 3 --ny 3 --nz 3 \
  --kernel physics_tet4 \
  --assemblies-list 1,3 \
  --threads-list 1,2,4 \
  --backend-list atomic,lock_guard \
  --csv /tmp/symbolic_numeric_smoke.csv
```

真实工程网格评估：

```bash
python3 scripts/run_symbolic_numeric_eval.py
```

mentor action-item 全物理核评估：

```bash
python3 scripts/run_mentor_action_items_eval.py --skip-build --repeat 1 --assemblies-list 1
```

默认真实评估固定为：

- `3d-WindTurbineHub.inp`
- `physics_tet4`
- `run_symbolic_numeric_eval.py`: `assemblies_per_symbolic = 1,3,10,30`
- `run_mentor_action_items_eval.py`: 默认 `assemblies_per_symbolic = 1`，用于避免在 WindHub full thread sweep 中重复运行极重的 direct/no-symbolic sort/reduce。

Windows Intel 平台使用同一脚本和同一 CSV/JSON/Markdown schema 复跑。跨平台报告必须区分平台差异与算法差异，不能把 Apple Silicon 和 Intel x86_64 的性能差异直接写成算法优劣。
