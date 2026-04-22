# CPU 并行整体刚度矩阵组装项目交接与下一阶段开发任务书

## 1. 文档目的

本文件用于把当前工作区的真实状态、已经完成的集成与验证、明确存在的问题，以及下一阶段应继续推进的开发任务，清晰交接给后续开发者或大模型。

这不是“背景介绍”，而是一份面向继续开发的主线任务书。后续开发必须以本文件和 `docs/requirements/cpu-parallel-stiffness-assembly-design.md` 为准，而不是自行重新理解目录结构。

## 2. 唯一主线目录

后续开发只能在以下目录继续进行：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

这条规则必须被严格遵守。原因如下：

- 该目录已经被改造成 CPU-first 主平台。
- 该目录已经完成本机编译、测试和实算例验证。
- 该目录已经接入统一的 `fem_core` / `fem_assembly` / `benchmark_assembly` 主结构。
- 该目录已经修复 Abaqus `.inp` 解析边界问题，并产出第一轮本机实验结果。

## 3. 已删除或不再作为主线的候选代码

历史上曾存在两套候选代码：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/cpu_parallel_assembly`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/pgsa_cpu_overlay`

它们曾经用于对比不同生成路线，但现在都不应继续作为开发落点。

原则：

- 不要继续在这两个目录上写功能。
- 不要把这两个目录重新引回主流程。
- 若需要参考历史思路，只能把它们当作已经消化过的来源，而不是继续维护的第二套代码树。

## 4. 当前已完成状态

### 4.1 构建与平台

当前主项目已经从历史的 GPU/CUDA 必需构建切换为 CPU-first：

- 默认语言为 `CXX`
- 标准为 `C++17`
- `OpenMP` 为可选但优先启用
- AppleClang + Homebrew `libomp` 已做自动探测兼容
- `CMakePresets.json` 已可直接用于 CPU 配置

本机验证环境：

- Machine: Apple M4 Max
- OS / arch: `macOS;arm64`
- Compiler: `AppleClang 21.0.0.21000099`
- OpenMP runtime: Homebrew `libomp`
- CMake: `4.3.2`

### 4.2 已接入的 CPU 并行算法

当前主项目已经实现并接入以下算法：

- `cpu_serial`
- `cpu_atomic`
- `cpu_private_csr`
- `cpu_coo_sort_reduce`
- `cpu_graph_coloring`
- `cpu_row_owner`

这些算法已经通过统一的 factory 和 benchmark CLI 暴露，不是“散落的原型代码”。

### 4.3 网格与输入

当前主项目已经具备：

- 规则块体网格生成
  - `Tet4`
  - `Hex8`
- Abaqus `.inp` 解析
  - `*NODE`
  - `*ELEMENT, TYPE=C3D4`
  - `*ELEMENT, TYPE=C3D8`
- Abaqus 1-based label 到内部 0-based index 的正确映射
- 对 `*OUTPUT` / `*NODE OUTPUT` / `*ELEMENT OUTPUT` 这类非网格 section 的安全跳过

### 4.4 局部核与预处理

当前已具备：

- CSR sparsity 结构构建
- element-local 到 CSR 位置的 scatter plan 预计算
- `simplified` kernel
- `physics_tet4` kernel

### 4.5 benchmark 当前输出能力

当前 benchmark 已能输出：

- 输入网格规模
- CSR 非零元数
- 平台信息
- mesh / CSR / scatter-plan 预处理时间
- 算法级 `preprocess_ms`
- 算法级 `assembly_ms`
- 算法级 `total_ms`
- `speedup`
- `rel_l2`
- `max_abs`
- `extra_memory_bytes`
- `colors`
- `diagnostics`

并且已经修复一项关键口径问题：

- `speedup` 现在固定相对 `1` 线程串行基线
- 串行基线在输出中只记录一次，不再随着线程列表重复

## 5. 已完成的本机验证

详细记录见：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/macstudio-validation-2026-04-22.md`

## 5A. 工程案例标准运行流程

后续开发者和大模型在运行真实工程网格时必须优先使用仓库内标准路径：

```text
examples/3d-WindTurbineHub.inp
```

不要再改写成 `data/external/...` 或其它本机私有路径，除非仓库内的 Git LFS 文件明确不可用。

标准步骤：

1. 在仓库根目录执行 `git lfs pull`，确保 `examples/3d-WindTurbineHub.inp` 已 materialize。
2. 进入 `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`。
3. 先跑 `simplified` kernel，确认 `.inp` 解析、CSR、scatter plan 和并行冲突处理正常。
4. 再跑 `physics_tet4` kernel，进入工程案例真实性能测试。

标准命令：

```bash
git lfs pull

cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

/opt/homebrew/bin/cmake -S . -B build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON

/opt/homebrew/bin/cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure

./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel simplified --warmup 0 --repeat 1 --check \
  --csv results/windhub_simplified.csv

./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel physics_tet4 --warmup 0 --repeat 1 --check \
  --csv results/windhub_physics_tet4.csv
```

如果程序读到的是 Git LFS pointer 而不是真实网格，先停止 benchmark，回到仓库根目录重新执行 `git lfs pull`。

### 5.1 通过的测试

已通过：

- `VerifyCpuAssemblers`
- `VerifyInpParser`

### 5.2 已运行的小算例

已在 `cube tet4 8x8x8 + simplified kernel` 上实际运行：

- `serial`
- `atomic`
- `private_csr`
- `coo_sort_reduce`
- `coloring`
- `row_owner`

结论概要：

- `row_owner` 和 `private_csr` 在该小算例上表现较好
- `coo_sort_reduce` 正确但明显偏慢
- `graph_coloring` 在当前实现和当前机器上并不占优

### 5.3 已运行的真实工程网格

已在真实输入：

```text
examples/3d-WindTurbineHub.inp
```

上实际运行：

- `serial`
- `atomic`
- `coloring`
- `row_owner`

当前该文件的已实测规模为：

- 节点数：`228384`
- 单元数：`1113684`
- 总自由度：`685152`
- CSR NNZ：`27502200`
- CSR 内存：`317.35 MiB`
- scatter-plan 内存：`666.99 MiB`

真实工程网格首轮结果表明：

- `row_owner` 当前是最强候选
- `atomic` 次之
- `coloring` 可用但不是领先者
- 真实网格下趋势与小算例并不完全一致，因此必须继续做系统对比

## 6. 当前明确存在的问题

### 6.1 线程扫描不完整

当前只跑了粗粒度线程点：

- `1,2,4,8,14`

这不足以形成完整 strong-scaling 曲线。后续必须支持：

- 自动生成 `1..N` 全线程扫描
- 同时允许用户传入自定义线程列表

### 6.2 指标维度不够丰富

当前图表主要只有：

- `assembly_ms`
- `speedup`

这不够。后续必须同时看：

- `assembly_ms`
- `preprocess_ms`
- `total_ms`
- parallel efficiency
- extra memory
- preprocess share
- correctness error
- 平台元信息

### 6.3 真实工程网格算法覆盖不完整

当前在 `3d-WindTurbineHub.inp` 上还没有完成以下算法的系统对比：

- `private_csr`
- `coo_sort_reduce`

注意：

- 这两类算法已经实现，不是缺代码
- 它们没进入真实网格实验，主要是因为内存和归并代价较大，需要受控实验设计

### 6.4 benchmark 阶段拆分仍不够细

当前虽然已经有 `preprocess_ms / assembly_ms / total_ms`，但对于某些算法，这还不够细：

- `coo_sort_reduce` 至少应拆分为
  - COO 生成
  - 合并
  - 排序
  - reduce
- `private_csr` 至少应拆分为
  - 私有数组分配/清零
  - 元素装配
  - nnz reduction
- `row_owner` 至少应拆分为
  - owner 分配
  - 数值装配

### 6.5 图表与结果归档能力不足

当前脚本还是偏原型，只能输出基础折线图。后续必须补齐：

- 完整实验矩阵生成
- 多图联动输出
- 结果目录自动归档
- 结果摘要 markdown 自动生成
- 适合论文/PPT 复用的图表命名与导出

### 6.6 工作区仍存在“结果不可上传”的事实

当前：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/`
- `*.csv`

被 `.gitignore` 忽略。

这意味着：

- 本地跑出来的 CSV/PNG 不会通过 GitHub Desktop 自动上传到仓库

## 6A. 已删除的误导性旧文档

以下文档已不再适合作为当前主线 CPU 项目的参考资料，后续不应再恢复：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/环境配置指南.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/技术报告.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README_CPU.md`

原因：

- 它们仍以 GPU/CUDA 环境和 GPU 组装为主叙事，已偏离当前 CPU-first 主线。
- 其中一部分命令仍把真实工程网格写成仓库外部私有路径，容易让大模型忽略仓库内标准 LFS 资源。
- 已进入 git 跟踪的只有文档摘要，而不是原始结果文件

后续必须明确决定：

- 是继续保持结果文件本地化，只提交摘要文档
- 还是把某一批核心结果改为可跟踪产物

## 7. 下一阶段总任务目标

下一阶段不是“继续修几个 bug”，而是要把当前主项目推进成一套真正可用于研究结论产出的 CPU 并行装配平台。

必须同时做到：

- 算法更多
- 指标更多
- 曲线更完整
- 真实网格覆盖更强
- 图表更可解释
- 代码结构更稳
- 文档更可复现

换句话说，下一阶段是“既要又要还要”的系统强化，不接受只补单点功能。

## 8. 下一阶段必须完成的开发包

### 开发包 A：benchmark 核心能力升级

必须完成：

- 支持自动生成 `1..N` 线程扫描
- 支持查询平台默认最大线程数
- 支持 `--threads-all` 或等价开关
- 支持每种算法多次重复运行并输出：
  - mean
  - min
  - max
  - stddev
- 支持固定随机/实验口径，保证可重复

建议新增输出字段：

- `run_count`
- `assembly_mean_ms`
- `assembly_min_ms`
- `assembly_max_ms`
- `assembly_std_ms`
- `total_mean_ms`
- `efficiency`
- `preprocess_share`
- `peak_rss_mb` 或等价内存指标
- `omp_threads_effective`
- `omp_proc_bind`

### 开发包 B：算法阶段计时细化

必须完成：

- 为所有算法建立统一的阶段计时框架
- benchmark 输出要能区分“公共预处理”和“算法内部预处理”
- `coo_sort_reduce` 要拆出内部子阶段
- `private_csr` 要拆出 reduction 成本
- `row_owner` 要能看见 owner 划分成本

目标是让后续研究不止回答“谁更快”，还要回答“为什么更快/更慢”。

### 开发包 C：真实工程网格实验矩阵补齐

必须完成：

- 在 `3d-WindTurbineHub.inp + simplified` 上补齐：
  - `private_csr`
  - `coo_sort_reduce`
- 用完整线程扫描跑真实工程网格
- 对内存敏感算法增加更清晰的失败信息与资源保护

最低要求：

- 如果算法因内存限制被跳过，输出必须是结构化的“SKIP/RESOURCE_LIMIT”而不是单纯崩溃
- 失败原因必须进入 CSV/summary

### 开发包 D：physics_tet4 工程网格验证

必须完成至少一轮真实工程网格下的 `physics_tet4` 验证。

要求：

- 至少跑 `serial`
- 至少跑 `atomic`
- 至少跑 `row_owner`
- 如资源允许，跑 `coloring`
- 给出正确性和时间结果

如果全量线程扫描成本太高，可以先做：

- `1,2,4,8,14`

但必须把这件事写成阶段成果，而不是长期停留在 simplified-only。

### 开发包 E：图表系统升级

必须新增并稳定输出以下图：

1. `assembly time vs threads`
2. `total time vs threads`
3. `speedup vs threads`
4. `parallel efficiency vs threads`
5. `preprocess breakdown`
6. `extra memory by algorithm`
7. `real mesh vs cube` 对比图
8. `simplified vs physics_tet4` 对比图

推荐图表形式：

- 折线图：线程扩展趋势
- 堆叠柱状图：时间分解
- 分组柱状图：内存额外开销
- 双图并排：规则网格与真实网格

要求：

- 文件名稳定
- 轴标签明确
- 单位统一
- 图例能直接用于论文/PPT

### 开发包 F：结果归档与报告化

必须完成：

- 统一结果目录结构
- 支持以日期和 case name 自动归档
- 自动生成 markdown summary
- 自动生成一页式实验摘要

建议新结构：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/
  YYYY-MM-DD/
    csv/
    figures/
    summaries/
```

并且明确：

- 哪些结果应被 git 跟踪
- 哪些结果只保留本地

### 开发包 G：代码结构清理

必须完成：

- benchmark 主程序拆分出独立的配置解析与结果写出模块
- plotting / run scripts 结构整理
- 避免 `main.cpp` 继续膨胀
- 明确“公共计时框架”和“算法自定义统计”的边界

这一步不是为了美观，而是为了支持后续继续加指标而不把 benchmark 主程序做成垃圾堆。

## 9. 下一阶段推荐优先级

推荐按以下顺序推进：

1. benchmark 输出 schema 升级
2. 线程全扫描支持
3. 图表系统升级
4. 真实网格上的 `private_csr / coo_sort_reduce`
5. `physics_tet4` 工程网格验证
6. 结果归档与 markdown 报告自动化
7. 代码结构清理

## 10. 明确的验收标准

下一阶段完成的最低验收标准应为：

- 主线目录仍然唯一，未重新分叉出第二套项目
- `cmake` 配置、编译、测试在本机可重复通过
- benchmark 能自动扫 `1..14` 全线程
- 小算例与真实工程网格都能输出多指标 CSV
- 至少生成 6 类以上可解释图表
- `private_csr` 与 `coo_sort_reduce` 已完成真实工程网格下的受控实验
- 至少一轮 `physics_tet4` 工程网格结果已产出
- 有一份更新后的实验摘要文档，能直接回答：
  - 哪类算法最快
  - 哪类算法最省内存
  - 哪类算法预处理最贵
  - 哪类算法最值得作为后续主线

## 11. 禁止事项

后续开发明确禁止：

- 在 `cpu_parallel_assembly` 或 `pgsa_cpu_overlay` 中继续加功能
- 重新引入“必须 CUDA 才能配置”的构建入口
- 用一次性 shell 脚本替代 CMake 主流程
- 只画 speedup 一张图就声称完成实验分析
- 在真实大网格上不加资源保护直接硬跑内存重算法
- 把 benchmark 主程序继续堆成一个超长文件而不拆结构

## 12. 本地上传提醒

如果使用 GitHub Desktop 上传当前工作区，请注意：

- `results/` 当前被忽略
- `*.csv` 当前被忽略
- 本地图片和原始实验 CSV 默认不会进入仓库

因此仓库中真正会被带走的是：

- 主线源码
- 说明文档
- 验证摘要

如果后续希望让仓库直接保留部分原始结果，需要额外调整 `.gitignore` 策略。

## 13. 交接结论

当前项目已经不是“空骨架”，而是一个已能在 Mac Studio 上实际运行、并已在真实工程网格上完成首轮验证的 CPU 并行装配主平台。

但它还没有达到“研究平台完成体”的程度。

下一阶段的核心目标不是再证明“能跑”，而是把它提升成：

- 实验矩阵完整
- 指标维度完整
- 图表体系完整
- 真实工程网格覆盖完整
- 代码结构可以继续演进

后续开发者应把主要精力投入到 benchmark 能力、实验设计、结果解释和主线算法筛选上，而不是再纠结该在哪个目录开发。
