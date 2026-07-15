# CSC3 Demo：两阶段正式验收工作流设计

## 1. 决策状态与适用范围

本文件记录 CSC3 对称 CSC3 刚度矩阵组装 Demo 的长期验收设计决策。设计于
2026-07-14 经仓库所有者确认，实施与验收状态仍以 GitHub Issue #44 为唯一活跃
状态源。

本设计解决候选包、机器事实、四方审批与最终侧车文件之间的时序闭环。它不改变
算法、正确性门槛、WindHub 性能门槛、源码包格式或 `INTERNAL EVALUATION ONLY`
分发边界。

## 2. 问题定义

旧流程要求四方在批准前查看“完成版”验收记录、清单和交付说明，但这些文件又必须
包含四方身份、批准时间和审批引用。因此，完成版文件只能在批准后形成，无法同时
作为批准前已经审阅的字节对象。旧批准项只绑定候选 ZIP 与源码身份，也没有明确
覆盖批准后生成的侧车内容。

该问题不是文件哈希自引用，而是审批对象与生成顺序不一致。正式流程不得声称四方
已经审批尚未生成的最终侧车字节。

## 3. 目标与非目标

### 3.1 目标

- 自动提取并冻结候选包、源码、主机、输入、测试、正确性、性能和 verifier 事实；
- 让四方审批显式绑定同一候选、机器事实和组织决定；
- 审批后由确定性 renderer 生成验收记录、清单和交付说明；
- finalizer 只接收已验证的 renderer 输出，并生成自包含的最终证据闭包；
- 新 shell 中恢复并验证同一正式工具链和运行环境；
- 拒绝受限 cpuset、超额订阅或无法证明全物理机口径的正式性能结果；
- 任何失败均保留证据并停在 `FAIL` 或 `BLOCKED`，不得通过手工修补提升状态。

### 3.2 非目标

- 不将 GitHub runner 或 macOS 本地计时升级为正式性能结论；
- 不改变性能门槛
  $S_{\mathrm{numeric}}(p)\ge 1.5$、
  $S_{\mathrm{symbolic}}(p)>1$ 与 $CV\le 0.05$；
- 不引入电子签名基础设施、证书链或外部审批服务；
- 不把可选 PDF 变成规范报告；
- 不授予公开发布、再分发或转授权许可；
- 本轮不要求第二阶段“最终字节回执”。若接收组织要求批准最终文件字节，应另行
  增加绑定最终三个侧车 SHA-256 的 receipt acknowledgement。

## 4. 状态模型

正式流程使用以下单向状态：

1. `PENDING`：尚未执行或资料未完成；
2. `BLOCKED`：环境、身份、源码、输入、工具链或授权前置条件不足；
3. `FAIL`：流程完整执行，但至少一个正确性、性能或验证门槛失败；
4. `PACKAGE_CANDIDATE`：自动证据、报告、确定性打包和 clean-room 门槛通过；
5. `APPROVAL_INPUT_READY`：机器事实已冻结，等待组织信息和四方批准；
6. `APPROVED_INPUT`：四方批准完整且全部绑定同一机器事实与组织决定；
7. `RENDERED`：最终侧车由已批准输入确定性生成并复验；
8. `PASS`：finalizer 完成自包含封包，且 `FINAL_SHA256SUMS` 全部通过。

状态只能按上述方向推进。`FAIL` 或 `BLOCKED` 不能在原 `RUN_ROOT` 内修补成
`PACKAGE_CANDIDATE`；修复原因后必须使用新的唯一目录从头执行。

## 5. 两阶段文件边界

### 5.1 阶段一：冻结机器事实并收集审批

`draft` 命令读取已经为 `PACKAGE_CANDIDATE` 的 `RUN_ROOT`，重新验证候选包、
`SHA256SUMS`、证据、报告、clean-room 结果与源码身份，然后以拒绝覆盖和原子发布
方式生成：

- `acceptance-machine-facts.json`：只包含从不可变候选证据重算的客观事实；
- `acceptance-decision.json`：包含待填写的人类/组织字段和四方批准槽位。

`acceptance-machine-facts.json` 不含人工字段，其 SHA-256 是四方共同审批对象的一部分。
`acceptance-decision.json` 的组织决定至少包括交付 ID、Issue URL、发送组织、接收
组织/部门、指定接收人、偏差及其处置。四个批准角色分别为：

- 操作员；
- 技术复核人；
- 交付批准人；
- 接收方确认人。

每条批准必须显式复制并绑定：

- `delivery_id`；
- 完整 `source_commit`；
- `archive_filename` 与 `archive_sha256`；
- `candidate_status=PACKAGE_CANDIDATE`；
- `clean_room_status=PASS`；
- `machine_facts_sha256`；
- 发送组织、接收组织/部门和指定接收人；
- 完整偏差处置集合；
- 真实身份引用、UTC 时间和组织内审批记录号。

renderer 将逐字段比较四条批准与顶层组织决定，不使用无法复核的自由文本摘要代替
结构化绑定。批准时间必须严格晚于候选完成时间和机器事实冻结时间。

### 5.2 阶段二：确定性渲染与最终封包

`render` 命令重新从 `RUN_ROOT` 计算机器事实，要求其字节和 SHA-256 与冻结文件
一致，再验证完成的 `acceptance-decision.json`。验证通过后，在同一文件系统的私有
暂存目录内按固定顺序生成：

1. `acceptance-record.json`；
2. `completed-acceptance-checklist.zh-CN.md`；
3. `completed-delivery-note.zh-CN.md`。

三个文件均为已批准输入的确定性派生物。流程只能声称四方批准了候选包、机器事实
和组织决定；不得声称四方在批准前查看或审批了尚未生成的侧车字节。

渲染顺序避免哈希循环：验收记录不包含自身或后续侧车的哈希；清单可绑定验收记录；
交付说明可绑定验收记录与清单。renderer 必须拒绝覆盖已有输出，任何失败不得留下
部分发布结果。

随后 finalizer 独立重跑同一跨字段验证、完整 clean-room 和侧车重渲染比较。只有
字节完全一致时，才原子创建 `final-delivery/` 并写出 `FINALIZATION.json` 与
`FINAL_SHA256SUMS`。

## 6. 机器事实的最小内容

机器事实必须至少覆盖：

- 完整源码 SHA、干净状态、Demo 版本与分支/主线身份；
- WindHub 仓库相对路径、实体文件大小、SHA-256、HEAD LFS OID 与 LFS size；
- 受控主机 ID、OS、内核、CPU 厂商/型号、内存、NUMA、SMT、governor 与 turbo；
- 在线 CPU、进程 affinity、cpuset 与物理核心拓扑；
- 编译器、CMake、Ninja、Python、Git、Git LFS 与 OpenMP 版本/路径；
- `OMP_DYNAMIC=false`、`OMP_PROC_BIND=close`、`OMP_PLACES=cores`；
- 请求和实测线程集合、$W=2$、$R=7$、$m=1$；
- 精确十项 CTest 名称与无失败、跳过、禁用或未运行状态；
- Tet4、Hex8 与总体矩阵/位移/残差门槛及实测值；
- numeric 与 symbolic 采用的线程数、speedup、$CV$ 和样本数；
- 候选 ZIP、报告、manifest、CSV/JSON、JUnit、主机记录、确定性打包记录与两类
  verifier 的路径、大小、SHA-256 和状态；
- 候选完成时间与机器事实冻结时间。

所有统计量必须从原始样本重算；机器事实不能信任手工复制的 summary 数值。

## 7. 工具链、环境与 cpuset 契约

运行手册每个可独立粘贴的新 shell 都必须重新设置：

- `LC_ALL=C` 与 `TZ=UTC`；
- 清除 `PYTHONOPTIMIZE`、`PYTHONPATH` 与 `PYTHONHOME`；
- `/usr/bin/gcc`、`/usr/bin/g++`；
- `OMP_DYNAMIC=false`、`OMP_PROC_BIND=close`、`OMP_PLACES=cores`；
- 与候选阶段相同且满足 Python $\ge 3.11$、`jsonschema>=4.23,<5` 的解释器。

preflight 必须检查规范命令实际调用的全部工具，包括 Git、Git LFS、Bash、Python、
CMake、Ninja、GCC、GNU `realpath`、`stat`、`sha256sum`、`install`、`lscpu`、
`awk`、`sed`、`grep`、`sort`、`cmp`、`tee`、`date`、`hostname` 与 `uname`。

正式运行要求未受限制的物理机口径。进程允许的逻辑 CPU 集合必须等于在线 CPU
集合，并能映射到登记的全部物理核心；不满足时状态为 `BLOCKED`。线程集合
$p\in\{1,2,4,8,16,p_{\mathrm{physical}}\}$ 中任何值超过可证明的物理核心数时也
必须阻塞，不能超额订阅后仍生成正式结论。

## 8. 最终证据闭包

`final-delivery/` 必须能在脱离原 `RUN_ROOT` 后独立验证。除候选 ZIP、三个侧车、
`FINALIZATION.json` 与 `FINAL_SHA256SUMS` 外，还必须复制：

- `acceptance-machine-facts.json` 与 `acceptance-decision.json`；
- 候选 `SHA256SUMS`；
- 候选 `SHA256SUMS` 引用的每一个文件，保持其相对路径；
- 验收记录引用但候选清单未覆盖的全部证据。

finalizer 在发布前必须从复制后的根目录执行候选 `sha256sum -c`，再生成覆盖最终目录
全部文件的 `FINAL_SHA256SUMS`。最终验证依次执行：

1. 候选证据子清单校验；
2. 最终全目录清单校验；
3. 验收记录与侧车跨字段复算；
4. 候选 ZIP manifest-only 与完整 clean-room 验证。

任何路径逃逸、符号链接、缺失文件、别名路径、摘要冲突或未列出文件均导致失败。

## 9. 错误处理与安全属性

- 所有生成器默认拒绝覆盖；正式流程不提供原地修补或 `--force`；
- 输出先写入同父目录私有暂存区，校验后使用不可替换的原子发布；
- 输入文件在计算摘要前后都要重新核验身份，防止检查后替换；
- human-readable 文件不能驱动客观事实，必须由机器事实和已验证决定渲染；
- 任一泛化占位值、非有限数、重复人员、无效时间、未批准偏差或不一致组织字段均
  导致 `BLOCKED`；
- 失败证据应完整保留用于诊断，但不得进入 `final-delivery/`。

## 10. 测试与验收

实现必须遵循测试先行，并至少覆盖：

- `draft` 对合法候选的确定性输出，以及所有缺失/篡改/路径逃逸输入；
- 四条批准对候选、机器事实、组织字段和偏差集合的逐项绑定；
- 批准时间边界、角色唯一性和泛化占位值拒绝；
- `render` 重复运行的字节一致性、拒绝覆盖与失败无部分输出；
- 三个侧车与机器事实/决定的全字段一致性；
- finalizer 的候选子清单自包含复验和最终全目录清单；
- 新 shell 环境恢复、完整工具预检与受限 cpuset 负向测试；
- 现有合法验收 fixture 的显式迁移，禁止静默兼容旧的审批时序语义；
- Demo 全部 Python、CTest、ASan/UBSan、external consumer、格式与 clean-room 回归。

完成条件是三平台 CI 通过，合并后的 `main` SHA 可被 Linux 运行手册接受，且受控
Linux 主机能够从 `PACKAGE_CANDIDATE` 经四方批准、确定性渲染和 finalizer 生成可
独立执行 `sha256sum -c FINAL_SHA256SUMS` 的内部正式交付目录。
