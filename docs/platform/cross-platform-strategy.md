# 跨平台策略

## 当前平台角色

当前主线按 Linux Intel、macOS ARM64 和 Windows AMD 三类平台维护。它们承担互补职责，不组成一条可以直接按绝对时间排名的“同机器”基线。

| 平台 | 当前角色 | 典型工具链 | 性能解释边界 |
| --- | --- | --- | --- |
| Linux Intel 受控物理机 | 正式 full-host 线程扩展、符号/数值后端与隔离 RSS 证据的主平台 | GCC/libgomp，另行记录实际版本 | 只有满足物理核、重复、绑定和主机状态协议的批次才能形成正式结论 |
| macOS ARM64 物理机 | 日常开发、AppleClang/libomp 可移植性、小型正确性以及 MATLAB/本地验证入口 | AppleClang/libomp | Apple Silicon 架构、统一内存与调度机制不能被解释为 Intel/AMD 的对照实验 |
| Windows AMD 物理机 | Windows 可移植性、AMD 同质核心证据、Windows 内存观测与 Abaqus 等受控验证 | 必须逐批记录 MSVC 或 GNU、OpenMP runtime | 编译器/runtime、电源计划和后台负载不同的批次不能合并 |
| GitHub 托管 runner | Linux、macOS、Windows 的编译和确定性质量门禁 | workflow 固定的工具链 | runner 用时和内存波动不进入正式 benchmark |

新增平台结果前必须运行 CPU 平台探测，记录同质/异构核心证据，并按[跨平台 CPU benchmark schema](cross-platform-benchmark-schema.md)声明 `full_host`、`performance_core_only` 和 `efficiency_core_only` 的 `available`、`missing` 或 `not_applicable` 状态。Linux Intel 正式实验还必须遵守[Linux Intel 正式实验协议](linux-intel-experiment-protocol.md)。

## 自动化与物理机边界

普通 PR 的三平台 CI 负责：

- C++17 configure/build；
- OpenMP required 构建契约；
- CTest、Python 单元与仓库契约测试；
- Tet4、Hex8 小网格 `linear_elastic_solid` 正确性；
- 脚本 dry-run、manifest 和 schema 失败传播。

受控物理机负责：

- WindHub 完整输入和 $1\ldots N_{\mathrm{physical}}$ 线程扫描；
- 正式时间、加速比、离散程度和 OS 峰值内存；
- CPU 绑定、核心 profile、NUMA、电源与热状态控制；
- MATLAB、Abaqus、CalculiX、COMSOL 等许可证或外部求解器验证。

CI 成功证明补丁满足自动质量门，不证明性能提升。物理机报告证明特定提交和环境下的观测，不自动证明其他编译器、操作系统或 CPU 上的行为。

## 工具链血缘必须分开

平台名相同不足以建立可比性。每个 package 必须记录编译器、编译器版本、OpenMP runtime、构建类型与关键选项。

现有 Windows AMD 物理机性能证据使用 GNU 15.2/libgomp；当前 Windows CI 使用 MSVC/OpenMP。MSVC CI 绿色只能证明 MSVC 路径能够构建并通过确定性测试，不能给历史 GNU 结果“补签”同一工具链 provenance，也不能把 GNU/libgomp 的性能数值改写成 MSVC 结果。需要 MSVC 性能结论时，必须在同一 Windows AMD 物理机上按正式口径重新采集独立批次。

同理，AppleClang/libomp、GCC/libgomp 与 MSVC/OpenMP 的结果必须分别保留，不得把 runtime 差异压缩成算法差异。

## 调度与核心隔离不等价

当前三类平台使用的控制机制含义不同：

- Linux `taskset`/cpuset 通过逻辑 CPU affinity 限制可运行 CPU；只有结合 `(SOCKET, CORE)` 拓扑证据，才能说明限制到了哪些物理核或 P/E 核。
- macOS QoS 是调度优先级与资源偏好，不是严格的核心 pinning。QoS-biased 结果不能标成与 Linux P/E CPU 列表等价的 core-only profile。
- Windows Processor Affinity 可以限制逻辑处理器集合，电源计划则影响调度和频率策略；二者都不等价于 Apple QoS，也不能在缺少拓扑映射时自动证明 P/E 核隔离。

因此，报告必须保留原始机制、CPU 列表/掩码和证据，不得用笼统的 `bound` 或 `core-restricted` 标签跨平台合并。若平台无法可靠隔离目标资源，应标记 `missing`；同质核心平台则标记 `not_applicable`，不能虚构 P/E-only 数据。

## 共同设计规则

- 构建入口使用 CMake，主线遵守 C++17。
- 平台相关代码集中在显式兼容层，不散落到算法核心。
- 自动脚本使用跨平台 Python；shell/PowerShell 只承担平台专用封装，不能成为唯一可复现说明。
- 路径、可执行文件后缀和多配置输出目录通过公共 helper 解析。
- benchmark 输出必须记录 OS、架构、CPU、物理/逻辑核、编译器、OpenMP runtime、affinity、线程策略、输入和提交 SHA。
- 物理模型主质量口径使用 `linear_elastic_solid`；历史 alias 只作为 provenance 保留。
- 性能结论必须同时控制 case、element type、算法集合、时间范围、重复次数、内存测量源和正确性状态。

## 解释护栏

除非硬件型号、核心 profile、编译器、OpenMP runtime、affinity、输入、物理模型、算法、线程策略、重复次数和统计方法都相同或已显式拆分，否则不得声称运行时间差异是纯算法差异。

特别要分开：

- ARM64 与 x86_64，以及 Intel 与 AMD 微架构；
- full-host、P/E-only、逻辑核扫描和超订阅；
- 默认调度、CPU affinity、QoS 和电源计划；
- `estimated_peak_bytes` 与操作系统观测的 RSS/working set；
- single sweep 与多次重复统计；
- CI smoke 与受控物理机正式实验。

## 相关协议

- [跨平台 CPU benchmark schema](cross-platform-benchmark-schema.md)
- [Linux Intel 正式实验协议](linux-intel-experiment-protocol.md)
- [跨平台求解器 validation 协议](cross-platform-validation-protocol.md)
