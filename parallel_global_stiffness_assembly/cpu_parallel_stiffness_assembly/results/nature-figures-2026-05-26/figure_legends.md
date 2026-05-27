# PGSA Nature-Style Figure Legends

本文件为本轮 Nature 风格重绘图包的详细图例说明。每张图均按数据来源、参数设置、测试背景、结果结论和原因解释组织，便于审稿、汇报和后续复现实验时直接核对。

## fig01_benchmark_three_axis_summary

**图件定位**：Correctness, memory, and assembly-time evidence must be read together, not as speedup alone.

**数据来源**：本图读取 `results/2026-04-28-12charts-repeat3-threads1to14/csv/` 下四个基准 CSV，覆盖规则立方体网格与 WindHub 网格、legacy synthetic 与 Tet4 弹性局部刚度模型。绘图只使用 `status=PASS` 的记录，并从 `speedup`、`extra_memory_bytes`、`rel_l2`、`max_abs` 等字段提取每个算法和场景的确定性摘要。

**参数设置**：仅纳入 `status=PASS` 的 1-14 线程记录；每个场景和算法的速度取 `speedup` 最大值，内存取 `extra_memory_bytes` 最小值并换算为 GiB，误差取 `rel_l2` 与 `max_abs` 最大值后做 `log10(max(value, 1e-18))` 变换。画布为 7.2 x 5.6 inch，四宫格热图共享算法顺序。

**测试背景**：这组测试的目的不是单独追求最高加速比，而是把矩阵正确性、额外内存和装配耗时放在同一证据链中审阅。每个场景都以 `cpu_serial` 作为正确性和性能基线，比较 `cpu_atomic`、`cpu_private_csr`、`cpu_graph_coloring`、`cpu_row_owner` 与 `cpu_coo_sort_reduce` 在 1 到 14 线程区间的行为。

**结果结论**：热图显示所有通过记录的相对矩阵误差基本处在浮点舍入量级，最大绝对误差也保持在可解释的小范围内。同时，加速收益和内存代价并不同步：在 WindHub Tet4 弹性场景中，`cpu_row_owner` 和 `cpu_atomic` 能给出较高加速，但 row-owner 类策略需要显著额外存储，而 atomic 类策略的内存增量更低。

**原因解释**：这种形态来自有限元全局刚度矩阵装配的共享写入冲突：不同单元会向同一全局自由度贡献条目。原子加法减少临时存储但付出同步代价；私有 CSR 或 row-owner 策略通过拆分写入路径降低冲突，因而更容易加速，但需要保留 per-thread 或 owner 分区数据。误差非零主要来自并行归约顺序变化，不是稀疏结构或物理模型的系统性失配。

## fig02_cpu_benchmark_dashboard

**图件定位**：WindHub-scale timing shows different algorithms trade assembly time against memory and preprocessing.

**数据来源**：本图来自 `results/2026-04-22/csv/` 下的 CPU 基准 CSV，尤其是 WindHub simplified、WindHub physics Tet4 以及单独的 `windhub_physics_tet4_coo_sort_reduce.csv`。脚本读取 `assembly_mean_ms` 或 `assembly_ms`、`speedup`、`extra_memory_bytes`、`threads` 等字段，并按 WindHub 场景汇总时间曲线、最快记录的内存成本和最高加速比。

**参数设置**：只筛选 WindHub 场景；时间字段优先使用 `assembly_mean_ms`，缺失时回退到 `assembly_ms`，主曲线使用对数 y 轴显示不同线程下装配耗时。下方面板按每个算法的最快 PASS 行提取额外内存 GiB 和最高加速比，算法颜色与全图包保持一致。

**测试背景**：该图对应项目早期 CPU 主线基准：在真实 WindHub 网格上比较串行装配、原子写入、私有 CSR、图着色、row-owner 和 COO sort-reduce 后端。测试关注真实大规模网格下的装配阶段，而不是小网格上的函数级微基准。

**结果结论**：WindHub physics Tet4 中，私有 CSR、row-owner 和 atomic 后端形成主要可用候选；COO sort-reduce 在该规模下耗时明显偏高且额外内存更大。图中同时保留速度和内存面板，说明最快策略并不自动等于最适合作为默认后端。

**原因解释**：私有 CSR 与 row-owner 通过减少热点写入冲突提升数值装配效率，但需要额外的矩阵副本、owner 映射或合并工作。Atomic 后端几乎不增加算法性额外内存，但热点自由度上的原子操作会限制扩展性。COO sort-reduce 需要先生成大量三元组再排序归并，因此在 WindHub 这类 2750 万非零条目的矩阵上会被内存流量和排序成本主导。

## fig03_thread_scaling_platforms

**图件定位**：Thread scaling changes by platform profile, with oversubscription and memory pressure visible in the same view.

**数据来源**：本图汇总六个 `thread_scaling_combined.csv` 文件，覆盖 Apple M4 Max full host、performance QoS、efficiency QoS，以及 Intel Core Ultra 7 265KF full host、P-core、E-core 配置。每个平台配置按算法选择 `assembly_ms` 最小的 PASS 记录，并展示对应的 `speedup` 与 `extra_memory_bytes`。

**参数设置**：读取六个线程扩展 CSV；若存在 `env_group` 字段，仅使用 `bound` 记录。每个平台配置、算法组合选择 `assembly_ms` 最小的 PASS 行，分别绘制最佳加速比和对应额外内存 GiB。Apple 与 Intel 的 full host、性能核和效率核配置在列方向并列。

**测试背景**：线程扩展测试用于回答同一 PGSA 后端在不同异构 CPU 资源绑定下是否仍保持相同排序。因此图中不只看线程数增加后的速度，也把性能核、效率核和全主机配置分开，避免把操作系统调度和核心类型差异混成一个平均值。

**结果结论**：结果显示扩展性具有明显平台和核心配置依赖：Apple 与 Intel 的 full-host、性能核心和效率核心配置并不产生同一组最优速度。私有 CSR 往往能取得更高速度，但图中同步显示其额外内存会随线程和缓冲区规模增加。

**原因解释**：这种差异来自三类因素叠加：核心微架构吞吐、共享内存带宽、以及同步或合并阶段的串行残留。性能核心通常提高单线程和缓存层级表现，效率核心在内存密集的稀疏装配中更容易受带宽和频率限制；全主机运行虽然线程更多，但也可能引入跨核心类型调度和共享资源竞争。

## fig04_core_profile_comparison

**图件定位**：Full-host, performance-core, and efficiency-core profiles expose platform-specific acceleration limits.

**数据来源**：本图使用与线程扩展相同的 cross-platform CSV 数据，但重新组织为相对 full-host 的装配时间比。脚本在 Apple M4 Max 和 Intel U7 265KF 两个平台内分别找出每个算法、每个核心配置的最快 PASS 记录，再用该配置的 `assembly_ms` 除以同平台 full-host 最快时间。

**参数设置**：复用线程扩展数据，先在每个平台、核心配置、算法内取最快 PASS 行，再用受限核心配置的 `assembly_ms` 除以同平台 full-host 最快时间得到相对耗时比。条形末端标注比值与线程数，1.0 虚线表示 full-host 基准。

**测试背景**：该图的背景问题是：full-host 是否总是最有解释力的比较对象，以及只用性能核或效率核是否能暴露算法瓶颈。比值小于或接近 1 表示受限核心配置接近全主机表现；显著大于 1 表示该算法依赖更多核心或更高带宽。

**结果结论**：图中可以看到性能核心配置在若干算法上接近 full-host，而效率核心配置通常明显慢于 full-host。这说明 PGSA 的线程扩展不能只按逻辑线程数解释，必须把核心类型和绑定策略作为实验条件写入结果包。

**原因解释**：有限元装配包含局部刚度计算、稀疏索引访问和全局写入三部分。性能核心更适合局部计算和同步密集段，效率核心在频率和缓存资源上受限时会放大原子写入或 merge 阶段成本。full-host 可能受益于更多并发，但如果算法合并阶段或内存带宽先达到瓶颈，单纯增加核心并不会线性改善装配时间。

## fig05_symbolic_memory_lifecycle

**图件定位**：Symbolic reuse shifts cost from repeated direct assembly into persistent CSR and scatter-plan storage.

**数据来源**：本图读取 `results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`。该文件包含 WindHub physics Tet4 在 Linux Intel full-host 上的 symbolic CSR 构建时间、scatter-plan 时间、数值装配时间、估算峰值字节数和隔离进程 RSS。

**参数设置**：使用隔离进程内存 CSV；时间曲线绘制 `amortized_total_ms`，内存曲线绘制 `isolated_peak_rss_mb / 1024`。对 atomic、private CSR 和 lock-guard 后端比较 serial-symbolic/parallel-numeric 与 parallel-symbolic-reuse 两类模式；峰值内存面板优先取物理核心数对应记录。

**测试背景**：symbolic/numeric 解耦测试用于区分两类成本：一次性建立稀疏结构和映射计划的 symbolic 阶段，以及每次载荷或材料更新时重复执行的 numeric 阶段。图中比较 serial symbolic reuse、direct no-symbolic、serial symbolic with parallel numeric 与 parallel symbolic reuse 等路径。

**结果结论**：结果表明 symbolic reuse 会把成本从反复生成和排序矩阵条目的 direct 路径转移到持久 CSR 与 scatter-plan 存储。direct no-symbolic 的瞬时内存峰值和排序归并成本更高，而 symbolic 路径在多次装配场景下更适合摊销前处理成本。

**原因解释**：原因是 WindHub 的稀疏拓扑在同一网格和单元类型下保持稳定：非零模式不需要每次重新发现。提前保存 CSR 结构和散射计划会增加常驻内存，但能避免每轮数值装配都生成大量临时 triplet 或 bucket 数据。因此 symbolic reuse 的优势会随重复装配次数增加而放大，而单次装配时需要同时报告前处理成本和持久内存。

## fig06_backend_tradeoff

**图件定位**：Atomic, private-CSR, and lock-guard backends separate synchronization cost from memory growth.

**数据来源**：本图读取 `results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.csv`，使用同一 WindHub physics Tet4、Linux Intel full-host 实验中的 atomic、private CSR 和 lock-guard 后端记录。面板分别绘制 `assembly_ms`、`speedup` 和 `extra_memory_bytes` 随线程变化的曲线。

**参数设置**：使用同一 WindHub 后端取舍 CSV 中的 PASS 行；三联图分别绘制 `assembly_ms`、`speedup` 和 `extra_memory_bytes / 1024^3` 随线程变化。仅保留 atomic、private CSR 和 lock-guard，避免把串行基线混入同步策略对比。

**测试背景**：该测试专门拆分数值装配后端的同步策略：atomic 使用硬件原子写入，private CSR 使用线程私有缓冲再合并，lock-guard 使用互斥锁保护共享条目。它帮助判断同步开销、内存放大和可扩展性之间的取舍。

**结果结论**：图中 private CSR 通常能在中等线程数获得较好速度，但额外内存随线程缓冲增长；atomic 内存代价最低，但在热点写入密集时扩展受限；lock-guard 的装配时间明显偏高，说明粗粒度或频繁互斥不适合该稀疏装配热点。

**原因解释**：全局刚度装配的冲突来自多个单元同时更新相邻自由度的矩阵项。Atomic 把冲突压缩到硬件同步指令，成本比互斥锁低但仍会在高冲突条目上排队；private CSR 通过本地累积减少写入冲突，代价是额外存储和后处理合并；lock-guard 每次写入都可能进入软件锁路径，因此锁管理成本吞没并行收益。

## fig07_sparse_pattern_windows

**图件定位**：The WindHub stiffness matrix is highly sparse, structured, and reproducibly exported from serial and parallel paths.

**数据来源**：本图读取周会材料资产中的 `windhub_physics_tet4_visual_exact_window_serial.csv`、`windhub_physics_tet4_visual_exact_window_auto_serial.csv` 以及配套 metadata JSON。metadata 记录 WindHub physics Tet4 的 228,384 个节点、685,152 个自由度、27,502,200 个非零项，并记录 serial 与 14 线程 atomic 路径具有相同稀疏结构。

**参数设置**：读取两个稀疏窗口 CSV 的 `row`、`col` 坐标；若窗口点数超过 85,000，则等步长抽样以保证 PDF/SVG 可打开。坐标减去窗口最小行列号后绘制，点大小为 0.04，y 轴反向以匹配矩阵图习惯；RCM 带宽数字来自 metadata。

**测试背景**：稀疏模式图用于解释为什么 PGSA 需要专门处理内存布局和并行写入冲突。面板 a 展示矩阵原点附近的精确窗口，面板 b 展示自动选择的高密度对角窗口；图题还报告可视化用 RCM 重排前后的带宽变化。

**结果结论**：图中非零项高度集中在局部对角带和块状邻域中，说明矩阵既稀疏又有明显有限元连接结构。metadata 中 RCM 可视化带宽从 392,948 降至 9,314，进一步说明节点排序会显著影响观察到的带宽和局部性。

**原因解释**：这种结构由有限元网格的局部支撑决定：每个单元只耦合自身节点自由度及其邻近节点，因此全局矩阵不会形成密集连接。WindHub 几何复杂且原始编号不完全按空间局部性排列，所以原始带宽较大；RCM 将相邻连接聚到对角附近，但该重排只用于可视化，不改变实际 benchmark 的数值矩阵。

## fig08_solver_validation

**图件定位**：Independent COMSOL and CalculiX probe comparisons close the solve-level validation loop.

**数据来源**：本图读取 `results/validation-export/2026-05-23-macos-comsol/` 与 `results/validation-export/2026-05-23-linux-intel-calculix/` 下的 probe compare CSV。每个 cantilever Tet4/Hex8、小/中等网格案例都包含 root、midspan 和 free-tip 探针位移，字段包括 MATLAB/PGSA 侧位移、外部求解器位移、`abs_diff` 与 `rel_diff`。

**参数设置**：遍历 COMSOL 与 CalculiX probe compare CSV；每个 case/solver 取 `rel_diff` 和 `abs_diff` 最大值，y 轴使用对数尺度并以 1e-16 作为显示下限。案例按名称排序，COMSOL 与 CalculiX 用并列柱展示。

**测试背景**：该验证不是只检查矩阵条目，而是检查有限元求解结果是否能与独立求解器闭环。COMSOL 6.2 LiveLink 和 CalculiX 分别作为外部参考，探针覆盖固定端、跨中和自由端，以检测边界条件、载荷方向和刚度矩阵缩放是否一致。

**结果结论**：CalculiX 对比的最大相对差异约在 1e-7 量级，COMSOL 对比约在 1e-4 到 8e-4 量级。图中相对误差和绝对误差都保持在小范围，说明 PGSA 的线性弹性装配和求解链路已经通过独立求解器探针级验证。

**原因解释**：CalculiX 与当前导出链在网格、载荷和单元公式上更接近，因此差异更接近舍入和输出精度误差。COMSOL 的差异略大，主要可由 LiveLink 导入网格、默认积分设置、载荷面积分布和探针插值细节解释。由于最大误差集中在位移幅值最大的自由端，绝对差异看起来较大，但相对差异仍保持在验证可解释范围内。

## fig09_basic_metrics_schema_coverage

**图件定位**：The cross-platform v2 packages make correctness, memory, and assembly-time fields first-class review artifacts.

**数据来源**：本图读取三个 cross-platform v2 benchmark package JSON：Linux Intel symbolic-memory full-host、2026-05-23 linear-elastic full-host 与 2026-05-24 linear-elastic full-host。脚本逐个 experiment family 统计 records 数量，并检查 `matrix_correctness_status`、`estimated_peak_bytes`、`isolated_peak_rss_mb`、`serial_direct_baseline_ms`、`speedup_vs_serial_direct` 等基础指标字段是否出现。

**参数设置**：读取三个 cross-platform v2 JSON 包；按 `experiment_family` 统计 records 数量，并在每个 family 的记录键集合中检查 `matrix_correctness_status`、`estimated_peak_bytes`、`isolated_peak_rss_mb`、`serial_direct_baseline_ms`、`speedup_vs_serial_direct` 五个基础指标字段是否出现。

**测试背景**：该图服务于结果包质量审计：PGSA 不应只保留图片或单次 benchmark 摘要，而应把正确性、内存和装配耗时作为可机器读取的评估契约。因此它把 thread_scaling、symbolic_direct、lock_vs_atomic、correctness_sparse 和 memory_lifecycle 等 family 放入同一覆盖矩阵。

**结果结论**：完整 full-host 包包含较多 thread-scaling、symbolic-direct、lock-vs-atomic 和 memory-lifecycle 记录，而 2026-05-24 包更像 smoke package，每个 family 只保留少量记录。字段覆盖矩阵显示 memory 相关字段主要集中在 symbolic_direct，提示仍需继续把三轴指标规范推广到其他 family。

**原因解释**：这种覆盖形态反映了仓库从 benchmark 结果向可移交结果包过渡的阶段性状态。早期 thread-scaling 与 lock-vs-atomic 记录已经有时间、线程和内存原始字段，但未全部映射到统一的基础指标字段名；symbolic-direct 因为本轮重点是 memory lifecycle，最先补齐 estimated peak 与 isolated RSS。因此该图既证明已有结果可追溯，也暴露下一步 schema 归一化的工作边界。
