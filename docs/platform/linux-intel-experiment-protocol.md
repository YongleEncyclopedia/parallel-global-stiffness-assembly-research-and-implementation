# Linux Intel 正式实验协议

## 目的与边界

本协议定义 Linux Intel 物理机上的正式 CPU/OpenMP benchmark 口径。它用于回答线程扩展、数值后端取舍、符号阶段并行化和内存生命周期问题，并保证结果能够追溯到提交、输入、主机和原始记录。

GitHub Actions 只负责小规模、确定性的编译、CTest、Python 测试和 smoke。托管 runner 的 CPU 型号、邻居负载、频率与调度状态不可控，因此 Actions 的用时不能进入正式性能结论。正式 benchmark 必须在受控物理机上执行，原始证据写入 CPU 子项目的 `results/`；CI artifact 只保存 CI 自身的诊断产物。

## 运行前基线

工作目录为：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/
```

正式运行前必须完成以下检查：

1. 记录完整 Git SHA、分支和 dirty status。若存在与本次实验无关的修改，不在该工作树继续运行。
2. 确认 WindHub 等大输入已经由 Git LFS 实体化；LFS pointer 不是合法实验输入。
3. 使用要求 OpenMP 的 Release 配置完成 configure、build 和全部 CTest；任何失败、`SKIP` 或 `Not Run` 都会阻断正式实验。
4. 先在生成式 Tet4/Hex8 小网格上运行 smoke，并确认所有请求算法均为 `PASS`。
5. 固定输入、`linear_elastic_solid`、算法集合、线程集合、重复次数、warmup、OpenMP 环境和内存上限；运行中不得悄悄改变口径。

## 物理核与 `full_host` 线程契约

令可用于本次实验的物理核数为 $N_{\mathrm{physical}}$。`full_host` 的主线程扫描固定为

$$
T_{\mathrm{full\_host}}=\{1,2,\ldots,N_{\mathrm{physical}}\}.
$$

这里的“可用”同时受主机拓扑与当前进程 CPU 集合约束。运行前至少保存以下证据：

```bash
python3 scripts/inspect_cpu_platform.py \
  --json <result-root>/platform.json \
  --markdown <result-root>/platform.md
lscpu
lscpu --extended=CPU,CORE,SOCKET,NODE,ONLINE
grep -E 'Cpus_allowed(_list)?' /proc/self/status
taskset -pc $$
```

应按当前允许的逻辑 CPU 集合，对 `(SOCKET, CORE)` 拓扑对去重，得到 $N_{\mathrm{physical}}$；同时记录可见逻辑处理器数 $N_{\mathrm{logical}}$。若主机处在容器、cgroup、cpuset 或作业调度器内，必须使用该分配实际允许的 CPU 集合，不能用整机标称核心数代替。

`os.cpu_count()` 通常返回当前可见的逻辑处理器数量。它可以作为交叉检查，但不得单独写成物理核证据，也不得在 $N_{\mathrm{logical}}\neq N_{\mathrm{physical}}$ 时把两者混用。若平台工具与拓扑证据不一致，应把物理核数标为 blocker，停止正式线程扫描，不能选择一个更方便的数值继续。

对于异构 Intel CPU，`full_host` 表示当前分配内全部可用物理核。`performance_core_only` 与 `efficiency_core_only` 只能作为单独 profile 采集，并保存 CPU 列表和隔离命令。主结论不扫描 SMT sibling 或超订阅线程；如需研究 $N_{\mathrm{physical}}<T\leq N_{\mathrm{logical}}$，必须使用独立 profile 和独立报告。

## 调度、绑定与主机状态

正式批次必须固定并记录：

- `OMP_NUM_THREADS` 或每条命令的线程参数；
- `OMP_DYNAMIC`、`OMP_PROC_BIND`、`OMP_PLACES` 和其他实际生效的 OpenMP runtime 变量；
- `taskset`/cpuset 的允许 CPU 列表；
- CPU governor、turbo 状态、NUMA 拓扑、内存容量与 swap 状态；
- 运行前后的温度或降频证据（平台能够提供时）；
- 后台负载、同时登录用户和其他已知干扰。

改变绑定、CPU 集合、governor 或 NUMA 策略会形成新的环境组，不得与原环境组聚合。`taskset` 只约束逻辑 CPU 亲和性；它不能自动证明频率、缓存状态或 P/E 核类别已经受控。

## 重复次数与统计可比性

令每个配置的测量重复次数为 $R$，warmup 次数为 $W$。可比较批次必须具有相同的 $R$、$W$、运行顺序策略、时间字段定义和汇总统计量。

- $R=1$ 的 single sweep 是一次观察，不是多次重复均值；报告必须明确写出这一点。
- 不得把 $R=1$ 的单次值和 $R=3$ 的均值放在同一速度曲线中，或据此解释平台/算法差异。
- 一旦正式口径从 $R=1$ 改为 $R>1$，所有进入同一比较的算法、线程数和平台都必须按新口径重跑。
- 原始文件应保留每次重复；汇总值必须说明采用 mean、median、minimum 或其他统计量，并保留离散程度。
- 后端线程扫描与符号/数值模式扫描若要互相引用，必须使用相同的重复口径。逐配置隔离内存测试应让每一行在新进程中运行。

运行顺序应避免把固定的“算法后跑”与主机升温混成算法效应。若脚本不能随机化或轮转顺序，必须在 manifest 中记录固定顺序，并在报告中作为限制说明。

## 内存生命周期分层

内存结论必须保留下面各层，不得只展示一个“memory”数值：

| 层 | schema 字段 | 含义 |
| --- | --- | --- |
| 符号持久层 $M_{\mathrm{sym,persist}}$ | `symbolic_persistent_bytes` | CSR 结构与 scatter/assembly plan，在后续数值装配中继续存活 |
| 公共输出层 $M_{\mathrm{output}}$ | `common_output_matrix_bytes` | 所有候选路径都需要的输出矩阵存储 |
| 并行符号临时层 $M_{\mathrm{sym,temp}}$ | `symbolic_temporary_bytes` | 并行构建 CSR/plan 时的临时工作区 |
| 数值后端额外层 $M_{\mathrm{backend}}$ | `numeric_backend_extra_bytes` | 线程私有矩阵、锁、着色或 owner 数据等后端特有成本 |
| 无符号直接路径临时层 $M_{\mathrm{direct}}$ | `direct_transient_bytes` | contribution、bucket、sort/reduce 等短生命周期缓冲区 |
| 模型估计峰值 $M_{\mathrm{estimated}}$ | `estimated_peak_bytes` | 当前实现按生命周期字段构造的模型值 |
| 隔离进程 OS 峰值 $M_{\mathrm{OS,isolated}}$ | `isolated_peak_rss_mb` | Linux 上由独立子进程观测并归一化的峰值 RSS |

当前估计字段可写为

$$
M_{\mathrm{estimated}}=
M_{\mathrm{sym,persist}}+M_{\mathrm{output}}+
M_{\mathrm{sym,temp}}+M_{\mathrm{backend}}+M_{\mathrm{direct}}.
$$

它描述实现中的显式数据结构，不包含分配器碎片、共享库、线程栈、runtime 和其他进程开销。$M_{\mathrm{OS,isolated}}$ 是操作系统观察值，包含上述进程级影响；二者回答的问题不同，不能相减后当作“未解释内存”，也不能用 $M_{\mathrm{estimated}}$ 填补缺失 RSS。

若 `isolated_peak_rss_mb` 缺失、非有限或不大于零，报告必须标记内存实测 blocker。只有同一主机、同一测量源、同一隔离方式和同一基线下的 OS 峰值差异才可以直接比较。图表若使用估计值，标题和坐标轴必须明确写“estimated”；若使用 OS 观测值，必须同时记录 `isolated_memory_metric` 与 `isolated_memory_measurement_source`。

## 正确性与比较条件

性能记录只有在矩阵正确性状态为 `PASS` 时才可进入结论。至少保留 `rel_l2`、`max_abs`、参考策略、case、element type、`stiffness_model` 与算法名。

数值后端比较必须控制相同输入、线程数和符号路径。符号阶段并行化比较必须控制相同数值后端、线程数和装配次数。跨平台比较还必须拆分编译器、OpenMP runtime、affinity、CPU profile 和内存测量源；详见[跨平台策略](cross-platform-strategy.md)与[跨平台 benchmark schema](cross-platform-benchmark-schema.md)。

## 结果目录与 manifest

每次正式批次使用新的结果根目录；已有目录默认不可覆盖。最少保留：

- `run_manifest.json`：机器可读的批次契约和每个任务状态；
- 原始 CSV/JSON：包含全部配置与逐次重复记录；
- configure/build/CTest、smoke 和正式命令日志；
- `platform.json`、`platform.md` 或等价的完整平台探测输出；
- 人类可读报告和由原始文件生成的图表；
- 输入、关键输出与 package 的 SHA-256 清单。

manifest 至少记录：

- 完整 Git SHA、分支、dirty status、开始/结束时间与时区；
- OS/kernel、CPU 型号、$N_{\mathrm{physical}}$、$N_{\mathrm{logical}}$ 及其证据来源；
- 编译器、CMake、Python、OpenMP runtime、构建 preset 和关键编译选项；
- CPU 集合、NUMA/affinity、OpenMP 环境、governor 与已知后台负载；
- 输入路径、大小、SHA-256 与 Git LFS 实体化状态；
- 完整可复制命令、工作目录、$R$、$W$、运行顺序和内存上限；
- 每个任务的 `PASS`、`FAIL`、`SKIPPED` 或 blocker、退出码和产物路径；
- 内存字段的单位、测量源与隔离方式。

报告中的每个结论都应能够回到 manifest 和原始行。Issue 或 PR 只保留摘要并链接结果目录，不粘贴原始数据，也不把没有相应证据的口头结论写成仓库事实。

## CI 与物理机的验收边界

| 检查 | GitHub Actions | Linux Intel 受控物理机 |
| --- | --- | --- |
| C++ 编译、CTest、Python 测试 | 必须 | 正式运行前必须复验 |
| Tet4/Hex8 小网格 smoke | 必须 | 正式运行前必须复验 |
| WindHub 完整线程扫描 | 不作为门禁 | 必须 |
| 时间、加速比与离散程度 | 不形成正式结论 | 必须 |
| 隔离进程峰值 RSS | 仅测试采集代码 | 必须 |
| 商业求解器或许可证工具 | 不要求 | 按独立 validation 协议人工执行 |

任何 CI 绿色状态都不能替代正式物理机证据；反过来，历史物理机结果也不能豁免当前 PR 的编译和确定性测试。
