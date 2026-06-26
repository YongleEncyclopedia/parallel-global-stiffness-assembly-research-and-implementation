# 2026 年 5 月以来高影响力期刊风格可视化图表标题与说明清单

本文档清点当前项目文件夹中 2026 年 5 月以来按高影响力期刊风格绘制、并带有绘图契约或来源清单的可视化图表。清点单位是“唯一图件身份”，不是导出格式；同一张图的 `SVG`、`PDF`、`PNG`、`TIFF` 只计为一张图。

## 范围说明

- 纳入：`results/nature-figures-2026-05-26/`、`reports/2026-05-27-assembly-quadrants/`、`reports/2026-05-27-assembly-schematics/`、`results/2026-05-27-windows-amd-abaqus-figures/`、`reports/2026-05-28-solver-validation-case-figures/`。
- 去重：`results/2026-05-26-nature-figures/` 是同名九张重绘图的早期导出副本，缺少后续 `TIFF` 与详细图例文件；本清单采用 `results/nature-figures-2026-05-26/` 作为这九张图的权威版本。
- 排除：`results/2026-05-27-macos-matlab-cantilever-topology-sparsity/` 为 MATLAB 生成的拓扑和稀疏模式图，不属于本绘图技能产线；5 月 14 日和 5 月 22 日周会/汇报资产为历史报告图或幻灯片资产，当前未发现对应的本绘图技能契约，因此不纳入本清单。
- 语言：标题和说明统一为中文；文件名、路径、算法名、字段名和单元类型保留原始标识符，便于回到源文件核验。

## 汇总

| 图件包 | 图数 | 主要依据 |
| --- | ---: | --- |
| 月报重绘证据包 | 9 | `results/nature-figures-2026-05-26/manifest.md` 与 `figure_legends.md` |
| 四象限组装策略图 | 6 | `reports/2026-05-27-assembly-quadrants/figure_contract.md` 与 `source_manifest.json` |
| 组装路径示意图 | 3 | `reports/2026-05-27-assembly-schematics/README.md` 与 `source_manifest.json` |
| Windows AMD 与 Abaqus 图件包 | 4 | `results/2026-05-27-windows-amd-abaqus-figures/figure_contract.md` 与各图说明 |
| 求解验证案例图 | 2 | `reports/2026-05-28-solver-validation-case-figures/figure_contract.md` 与 `source_manifest.json` |
| 合计 | 24 | 按唯一图件身份计数 |

## 月报重绘证据包

### 1. 三轴证据总览：正确性、内存与装配时间必须一起审阅

- 对应图件：`results/nature-figures-2026-05-26/fig01_benchmark_three_axis_summary.*`
- 说明文字：本图把矩阵正确性、额外内存和装配耗时放在同一证据链中展示，避免只用加速比评价并行装配策略。数据来自 4 月 28 日十二图基准的四个 CSV，覆盖规则立方体网格与 WindHub 网格、简化核与 Tet4 弹性局部刚度模型，并只使用 `status=PASS` 的记录。图中可见，通过记录的相对矩阵误差基本处于浮点舍入量级，而加速收益与内存代价并不同步：在 WindHub Tet4 弹性场景中，`cpu_row_owner` 和 `cpu_atomic` 能给出较高加速，但 row-owner 类策略需要显著额外存储，atomic 类策略的内存增量更低。该图的核心作用是把“快、准、省内存”拆成三个可复核指标。

### 2. WindHub 规模 CPU 基准总览：不同后端在时间、内存和预处理之间取舍

- 对应图件：`results/nature-figures-2026-05-26/fig02_cpu_benchmark_dashboard.*`
- 说明文字：本图面向真实 WindHub 网格，比较串行装配、原子写入、私有 CSR、图着色、row-owner 和 COO sort-reduce 等后端的装配耗时、最高加速比和额外内存。数据来自 4 月 22 日 CPU 基准 CSV，优先读取 `assembly_mean_ms`，缺失时回退到 `assembly_ms`。图中显示，WindHub physics Tet4 下私有 CSR、row-owner 和 atomic 是主要可用候选；COO sort-reduce 在该规模下耗时明显偏高且额外内存更大。该图说明最快策略并不必然适合作为默认后端，因为有限元装配的热点写入冲突可以用额外内存换取速度，也可以用原子操作降低内存但牺牲部分扩展性。

### 3. 跨平台线程扩展：平台配置和核心类型会改变最优后端排序

- 对应图件：`results/nature-figures-2026-05-26/fig03_thread_scaling_platforms.*`
- 说明文字：本图汇总 Apple M4 Max 与 Intel Core Ultra 7 265KF 的全主机、性能核和效率核配置，展示不同算法在各平台配置下的最佳加速比及对应额外内存。数据来自六个 `thread_scaling_combined.csv` 文件，每个平台配置按算法选择装配时间最小的 PASS 记录。图中结果表明，线程扩展性具有明显平台依赖和核心配置依赖；full-host、性能核与效率核配置并不产生同一组最优速度。该图强调 PGSA 的并行结果不能只写线程数，还必须记录核心类型、绑定策略和内存压力。

### 4. 核心配置对比：全主机、性能核和效率核暴露不同的加速上限

- 对应图件：`results/nature-figures-2026-05-26/fig04_core_profile_comparison.*`
- 说明文字：本图把跨平台线程扩展结果重组为相对 full-host 的装配时间比，用来判断受限核心配置是否接近全主机表现。脚本在每个平台、核心配置和算法内取最快 PASS 行，再用该配置的 `assembly_ms` 除以同平台 full-host 最快时间。图中可以看到，性能核配置在若干算法上接近 full-host，而效率核配置通常明显慢于 full-host。该图的解释重点是有限元装配同时包含局部刚度计算、稀疏索引访问和全局写入，同一算法在不同核心类型下会受微架构吞吐、内存带宽和同步残留的共同限制。

### 5. 符号结构复用的内存生命周期：成本从重复直接组装转移到持久 CSR 与 scatter plan

- 对应图件：`results/nature-figures-2026-05-26/fig05_symbolic_memory_lifecycle.*`
- 说明文字：本图读取 Linux Intel full-host 的 isolated symbolic memory 结果，展示 symbolic/numeric 解耦后，前处理时间、数值装配时间、估算峰值内存和隔离进程峰值 RSS 的关系。图中比较 serial symbolic reuse、direct no-symbolic、serial symbolic with parallel numeric 和 parallel symbolic reuse 等路径。结果表明，symbolic reuse 会把成本从反复生成和排序矩阵条目的 direct 路径转移到持久 CSR 与 scatter-plan 存储；direct no-symbolic 的瞬时贡献列表和排序归并成本更高，而 symbolic 路径在重复装配场景中更适合摊销前处理成本。该图不把估算内存和 OS 观测内存混为一个指标。

### 6. 数值后端取舍：atomic、private CSR 与 lock-guard 分离同步成本和内存增长

- 对应图件：`results/nature-figures-2026-05-26/fig06_backend_tradeoff.*`
- 说明文字：本图比较 WindHub physics Tet4 在 Linux Intel full-host 上的 atomic、private CSR 和 lock-guard 后端，分别展示装配时间、加速比和额外内存随线程变化的曲线。数据来自 `windhub_backend_tradeoff.csv`。图中 private CSR 通常能在中等线程数获得较好速度，但额外内存随线程缓冲增长；atomic 内存代价最低，但在热点写入密集时扩展受限；lock-guard 装配时间明显偏高，说明频繁互斥不适合该稀疏装配热点。该图用同一数据源解释同步策略与内存放大的结构性取舍。

### 7. WindHub 稀疏模式窗口：串行与并行路径可复现导出同一类局部稀疏结构

- 对应图件：`results/nature-figures-2026-05-26/fig07_sparse_pattern_windows.*`
- 说明文字：本图读取周会材料中的 WindHub physics Tet4 稀疏窗口 CSV 和 metadata，展示全局刚度矩阵在局部窗口中的非零项分布。metadata 记录该案例具有 228,384 个节点、685,152 个自由度和 27,502,200 个非零项，并记录 serial 与 14 线程 atomic 路径具有相同稀疏结构。图中非零项集中在局部对角带和块状邻域，体现有限元局部支撑导致的稀疏连接。RCM 可视化带宽从 392,948 降至 9,314，说明节点重排会显著改变观察到的局部性；但该重排只用于可视化，不改变 benchmark 的数值矩阵。

### 8. 独立求解器验证：COMSOL 与 CalculiX 探针比较闭合求解级正确性链路

- 对应图件：`results/nature-figures-2026-05-26/fig08_solver_validation.*`
- 说明文字：本图读取 macOS+COMSOL 与 Linux Intel+CalculiX 的 probe compare CSV，按 cantilever Tet4/Hex8、小/中等网格案例汇总 root、midspan 和 free-tip 探针位移差异。该验证不只检查矩阵条目，而是检查自研导出的刚度矩阵、载荷、边界条件进入求解后能否与独立有限元软件形成闭环。图中 CalculiX 对比的最大相对差异约在 `1e-7` 量级，COMSOL 对比约在 `1e-4` 到 `8e-4` 量级。差异主要可由导入网格、积分设置、载荷面积分布和探针插值细节解释；因此该图是求解链路正确性的探针级证据，而不是完整商业软件等价声明。

### 9. 基础指标模式覆盖：跨平台结果包把正确性、内存和耗时变成可审查工件

- 对应图件：`results/nature-figures-2026-05-26/fig09_basic_metrics_schema_coverage.*`
- 说明文字：本图读取三个 cross-platform v2 benchmark package JSON，统计不同 experiment family 的记录数量，并检查 `matrix_correctness_status`、`estimated_peak_bytes`、`isolated_peak_rss_mb`、`serial_direct_baseline_ms` 和 `speedup_vs_serial_direct` 等基础指标字段是否出现。图中显示，完整 full-host 包包含较多 thread-scaling、symbolic-direct、lock-vs-atomic 和 memory-lifecycle 记录，而 smoke package 记录较少；memory 相关字段主要集中在 symbolic_direct。该图既证明已有结果可追溯，也暴露下一步需要继续做 schema 归一化。

## 四象限组装策略图

### 10. 月度汇报总览页：符号复用与并行符号阶段共同决定主线判断

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig00_monthly_report_summary_slide.*`
- 说明文字：本图是一页汇报主图，综合四象限策略图、关键加速比和阶段性判断，用于支撑“符号组装加数值组装优于无符号直接组装，且并行符号组装优于串行符号组装”的主结论。数据锚定同一份 WindHub / Apple M4 Max 结果，不用于宣称跨平台绝对性能排名。图中加速关系来自同一 case 的路径对比：串行有符号相对串行无符号约 1.68 倍，并行有符号相对串行有符号约 4.67 倍，同为 14 线程时并行有符号相对并行无符号约 2.52 倍。该图适合作为月报开场，但其内存口径仍是数据结构生命周期解释，不是 OS RSS。

### 11. 四象限策略图：组装路径按符号结构复用和执行方式分解

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig01_four_quadrant_strategy_map.*`
- 说明文字：本图以横轴表示是否复用 CSR/scatter 符号结构，以纵轴表示串行或并行执行方式，把四条主路径放入同一坐标系：串行无符号直接、串行有符号加数值、并行无符号直接、并行有符号加数值。图中 direct/no-symbolic 路径被解释为 `(row,col,value)` contribution list 生成后排序归并到 CSR，而不是 dense matrix。该图的核心信息是，符号结构复用减少重复排序归并成本，并行符号阶段进一步降低前处理耗时；最佳象限是并行有符号加数值组装。

### 12. 端到端时间构成：不同路径的主要耗时阶段不同

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig02_cost_breakdown.*`
- 说明文字：本图拆解四条路径的端到端耗时构成，区分 direct 路径中的 contribution 生成、bucket/merge、sort/reduce，以及 symbolic 路径中的 CSR 构建、scatter plan 构建和 numeric assembly。它说明 direct/no-symbolic 虽然不显式保留符号结构，却把成本转移到每次生成和排序归并大量贡献项；symbolic 路径一次性建立可复用结构，之后数值阶段可以直接写入固定 CSR values。该图是四象限主图的时间证据支撑。

### 13. 线程扩展支撑：并行有符号与并行无符号随线程数变化

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig03_thread_scaling.*`
- 说明文字：本图展示并行有符号路径与并行无符号直接路径在线程数变化下的耗时趋势，用于验证四象限主图中的同核数 direct 对照不是孤立读数。它强调，direct/no-symbolic 的并行化确实能压低部分生成和归并成本，但仍需承担每次重建贡献列表与排序归并的结构性开销；parallel symbolic reuse 则把拓扑结构和地址映射提前固化，使数值装配阶段更轻。该图用于支撑“并行符号加数值优于同核数 direct 对照”的判断。

### 14. 内存生命周期支撑：persistent、temporary 与 transient 不能混成 OS 峰值内存

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig04_memory_lifecycle.*`
- 说明文字：本图把 symbolic 路径的持久 CSR/AssemblyPlan、并行符号阶段临时结构，以及 direct/no-symbolic 的 transient contribution buffer 分开显示。它的目的不是报告操作系统观测峰值 RSS，而是解释不同组装策略在数据结构生命周期上的内存代价。direct 路径的贡献列表是每轮组装的瞬时成本；symbolic 路径的 CSR 和 scatter plan 是可复用的持久成本；并行符号阶段还可能产生额外临时结构。该图必须与 OS 实测内存图分开解释。

### 15. 符号复用摊销：重复组装次数增加时 symbolic 成本被摊薄

- 对应图件：`reports/2026-05-27-assembly-quadrants/assets/fig05_symbolic_reuse_amortization.*`
- 说明文字：本图展示同一稀疏结构重复组装时，symbolic reuse 的一次性前处理成本如何被多次 numeric assembly 摊销。数据来自 `symbolic_numeric_eval.csv`，覆盖不同 `assemblies_per_symbolic` 设置。图中说明 direct/no-symbolic 每次都要重新生成贡献并排序归并，而 symbolic reuse 可以复用 CSR/scatter plan，仅重复数值填充。该图是回答“为什么一次装配收益有限但多次装配收益更明显”的支撑证据。

## 组装路径示意图

### 16. 符号组装示意图：从网格拓扑建立可复用 CSR 与 scatter 地址

- 对应图件：`reports/2026-05-27-assembly-schematics/assets/symbolic_assembly_schematic.*`
- 说明文字：本图用代码语义示意 symbolic assembly：先根据单元连接关系和自由度映射发现全局稀疏结构，再建立 CSR 行指针、列索引和 `AssemblyPlan::scatter` 地址表。图中强调 `values` 数组是按非零结构分配的固定长度数值存储，而不是动态增长的条目容器。该图不包含 benchmark 统计量，作用是解释为什么同一网格和同一自由度编号下，拓扑和地址构造可以独立于材料参数或载荷更新而复用。

### 17. 数值组装示意图：复用符号阶段结果计算局部刚度并写入 CSR values

- 对应图件：`reports/2026-05-27-assembly-schematics/assets/numeric_assembly_schematic.*`
- 说明文字：本图展示 numeric assembly 如何在已有 CSR 和 scatter plan 上运行：每个单元计算局部刚度矩阵 `Ke`，再通过预计算 scatter 地址把贡献写入全局 `CSR values`。串行后端直接累加，并行后端可使用 atomic、private CSR 或其他同步策略处理共享条目冲突。该图说明 symbolic/numeric 解耦后，数值阶段不需要重新发现非零模式，也不需要重新排序贡献条目。

### 18. 无符号直接组装示意图：贡献列表生成、排序归并与最终 CSR 构造

- 对应图件：`reports/2026-05-27-assembly-schematics/assets/direct_no_symbolic_assembly_schematic.*`
- 说明文字：本图说明 direct/no-symbolic 路径不是 dense matrix 组装，而是先为每个单元生成 `(row,col,value)` 贡献列表，再进行 bucket/merge、sort/reduce，最后形成 CSR 矩阵。该路径避免显式保存可复用的 CSR/scatter plan，但每次装配都必须重新承担贡献生成和排序归并成本。图中信息用于纠正常见误解：direct/no-symbolic 是稀疏 contribution list 路径，不是先构造密集全局矩阵再压缩。

## Windows AMD 与 Abaqus 图件包

### 19. 验证误差汇总：自由端挠度百分比用于区分 Tet4 与 Hex8 的求解级表现

- 对应图件：`results/2026-05-27-windows-amd-abaqus-figures/fig01_validation_error_summary.*`
- 说明文字：本图回答“悬臂块求解级正确性是否在所有单元类型上同样成立”。主相对差异固定为自由端挠度百分比，逐 probe 三维位移向量差异只作为诊断量，避免把固定端近零位移或中间 probe 当成最终挠度结论。数据来自 Windows AMD + Abaqus 验证导出的 `*_abaqus_compare.csv`，由 MATLAB 求解自研 C++ 导出的 `K/F/BC` 后，与 Abaqus/Standard ODB 抽取位移在同一 probe 节点上比较。图中 Tet4/C3D4 的自由端挠度百分比差异接近零；Hex8/C3D8 的自由端挠度百分比差异约为 1.78% 到 2.98%，这是需要继续解释的验证信号，不能写成商业求解器等价。

### 20. 探针位移剖面：沿悬臂长度检查位移趋势和局部偏移

- 对应图件：`results/2026-05-27-windows-amd-abaqus-figures/fig02_probe_displacement_profiles.*`
- 说明文字：本图用 root、midspan、free tip 三个物理位置的 `Uz` 剖面补充自由端挠度百分比。它展示 MATLAB 自研求解与 Abaqus 位移在悬臂长度方向上的趋势是否一致，并用灰色连线标出同一 probe 上的局部差异。四个 case 均保持从固定端到自由端位移增大的物理趋势，说明边界、载荷方向、节点映射和求解流程没有明显错位；Tet4 曲线几乎重合，Hex8 曲线在跨中和自由端出现可见偏移，符合单元刚度或积分细节差异导致柔度预测偏移的表现。

### 21. 组装时间扩展：Windows AMD 上 parallel symbolic reuse 比 direct/no-symbolic 更快

- 对应图件：`results/2026-05-27-windows-amd-abaqus-figures/fig03_assembly_time_scaling.*`
- 说明文字：本图展示 Windows AMD 平台上 WindHub Tet4 assembly 路径的时间扩展，回答哪条自研路径更快以及快在哪里。数据来自 `isolated_symbolic_memory.csv`，每一行由隔离子进程运行 `symbolic_numeric_eval.exe` 得到。WindHub 网格包含 228,384 个节点、1,113,684 个 Tet4 单元和 685,152 个自由度，线程范围为 AMD Ryzen 7 9800X3D 的 1 到 8 物理核心。图中 8 线程 `parallel_symbolic_reuse + cpu_atomic` 达到最低总时长约 1133 ms，相对串行 symbolic baseline 约 3.6 倍；8 线程 direct/no-symbolic 仍约 2147 ms，慢于 symbolic reuse。

### 22. 内存与时间权衡：Windows OS 观测内存和生命周期估算必须分开解释

- 对应图件：`results/2026-05-27-windows-amd-abaqus-figures/fig04_memory_tradeoff.*`
- 说明文字：本图把 Windows OS 观测 peak working set、private bytes、时间-内存运行点和 estimated lifecycle peak 放在一起，避免把模型估算冒充系统观测。数据来自同一 isolated symbolic memory CSV；Windows 下历史列名 `isolated_peak_rss_mb` 实际对应 `windows_peak_working_set`。图中 symbolic reuse 的 peak working set 约 2.26 GiB 且随线程变化很小；direct/no-symbolic 在同一线程范围内约 3.65 到 5.45 GiB，8 线程 estimated lifecycle peak 也明显高于 symbolic reuse。该图说明 direct/no-symbolic 的核心成本之一是大量临时 contribution buffer。

## 求解验证案例图

### 23. 结构化 Hex8/C3D8 悬臂块：自由端挠度百分比揭示 Windows/Abaqus 差异信号

- 对应图件：`reports/2026-05-28-solver-validation-case-figures/assets/fig_hex8_free_tip_deflection_validation.*`
- 说明文字：本图比较结构化 Hex8/C3D8 悬臂块在 macOS+COMSOL、Linux+CalculiX 和 Windows+Abaqus 三类参考下的自由端竖向挠度百分比差异。统一指标为 `100 * abs(abs(Uz_MATLAB_free_tip) - abs(Uz_FE_free_tip)) / abs(Uz_FE_free_tip)`，主 probe 为 `free_tip_center`。图中 macOS+COMSOL 与 Linux+CalculiX 保持在 0.02% 以下，而 Windows+Abaqus 约为 2.98%。该图的结论不是“一票否决”，而是把 Hex8/C3D8 的百分级差异作为需要报告和继续隔离的验证信号，后续应检查单元刚度矩阵约定、节点顺序、全积分实现和载荷等效化。

### 24. Tet4/C3D4 悬臂块：三类参考下自由端挠度差异均处于很小范围

- 对应图件：`reports/2026-05-28-solver-validation-case-figures/assets/fig_tet4_free_tip_deflection_validation.*`
- 说明文字：本图比较 Tet4/C3D4 悬臂块在 macOS+COMSOL、Linux+CalculiX 和 Windows+Abaqus 三类参考下的自由端竖向挠度百分比差异。三类参考均低于 0.02%，其中 Abaqus 和 CalculiX 接近 probe 精度量级，说明 Tet4 线性弹性路径在当前导出、边界、载荷和 MATLAB 自研求解链路下形成了较强的求解级正确性证据。图中同时保留节点数、单元数、自由度数和稀疏模式资产线索，用于把数值挠度结论与网格规模、刚度矩阵结构联系起来。

