# 当前知识边界

本文件是后续维护者和代理理解本仓库的第一入口。它说明哪些内容是当前事实，哪些内容只是历史材料，以及当不同材料互相矛盾时应以谁为准。

## 当前范围

当前项目是一个 **CPU-first** 的研究与实现工作区，目标是在共享内存多核 CPU 上研究整体刚度矩阵的并行组装。

当前范围内的工作包括：

- 面向整体刚度矩阵的共享内存 CPU 组装算法。
- 规范实现位于 `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`。
- `Tet4` 和 `Hex8` 规则网格测试，以及 Abaqus `.inp` 输入中的 `C3D4` 和 `C3D8`。
- 当前规范局部刚度矩阵模型是 `linear_elastic_solid`，也就是三维小变形线弹性实体刚度模型。
- symbolic/numeric 组装阶段分离、CSR/scatter plan 复用，以及 direct/no-symbolic 对照。
- benchmark 打包、平台/profile 元数据、图表、报告和 Beamer 摘要。
- Linux Intel 与 macOS Apple Silicon 的跨平台解释；在有可比数据时，以 Intel 作为主要对外展示平台。

当前主线不包括：

- 新的 GPU 算法开发。
- MPI 或分布式内存组装。
- 商业求解器的完整功能覆盖。
- 整体矩阵组装之后的 solver 阶段优化。
- 高阶单元、非线性材料、接触问题，以及 PETSc section/closure 这类通用抽象；这些内容只可作为解释性参考。

## 资料优先级

当不同资料互相矛盾时，按下面顺序取信：

1. `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/` 中的当前结构化结果和报告，尤其是 2026-05-16、2026-05-20 与 cross-platform v1/v2 报告。
2. `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/` 下的当前 CPU 主线代码、CLI 行为和 CPU 文档。
3. 当前需求与边界文档：`docs/requirements/cpu-parallel-stiffness-assembly-design.md`、`docs/context/repository-scope.md` 和本文件。
4. 带日期的 handoff、导师沟通和周会报告；它们只代表对应日期的状态。
5. 月报摘录、Beamer speaker notes 和历史 deck；它们只作为叙事与 provenance。
6. 外部资料只用于解释一般概念，不能覆盖本地 benchmark 事实。

## 当前事实

- CPU 主线注册了七个 CPU 组装算法：`serial`、`atomic`、`lock_guard`、`private_csr`、`coo_sort_reduce`、`coloring` 和 `row_owner`。
- `serial` 仍然是正确性和加速比基线。
- `lock_guard` 是每个 CSR entry 使用一个 `std::lock_guard<std::mutex>` 的同步基线；它适合做同步开销对照，不是推荐路线。
- `3d-WindTurbineHub.inp` 是核心真实工程网格，应通过仓库 Git LFS 路径访问。
- 当前面向报告的 benchmark/validation 路径是“真实工程网格 + `linear_elastic_solid`”。Tet4/C3D4 使用历史物理 Tet4 实现；Hex8/C3D8 使用 2x2x2 Gauss full integration。
- `physics_tet4` 是历史兼容用的 Tet4/C3D4-only alias。`physics_solid` 是映射到 `linear_elastic_solid` 的历史 alias。
- `simplified` 现在应理解为 `legacy_synthetic`：只用于早期 provenance 或显式开启的小型 smoke，不用于当前 benchmark 结论。
- 内存数字必须按生命周期拆开：持久 CSR/AssemblyPlan、symbolic/direct 临时 buffer、后端额外内存、以及操作系统观测到的 peak RSS。
- Intel `taskset` P/E-core profile 和 Apple QoS-biased profile 不是等价硬件控制机制，不能直接当作同一类 profile 比较。

## 文档语言与目录维护规范

- 给人阅读的新文档默认使用中文；代码标识、命令、路径、schema key、论文名和外部工具字段可以保留英文。
- 每个 Git tracked 子目录都应有 `README.md`，并至少说明用途、存放内容、不应存放内容、维护提示和相关入口。
- 结果目录中的 README 只描述来源、结构和维护边界，不重写或美化数值结论。
- 独立放在模块根部的脚本、构建入口或配置文件，应在文件头或相邻 README 中说明为什么它们不放进更深子目录。
- 机器/工具状态文件如果不适合翻译，应记录在文档语言 allowlist 中，不把它们当作面向人工阅读的项目文档。

## 材料类别

| 类别 | 示例 | 使用规则 |
| --- | --- | --- |
| 当前事实来源 | CPU 主线 README、`docs/cpu/*`、最新结构化结果报告 | 用于当前实现和 benchmark 声明。 |
| 需求与边界 | `docs/requirements/*`、`docs/context/*` | 用于范围、排除项和解释优先级。 |
| 结果证据 | `results/2026-05-16-*`、`results/2026-05-20-*`、`results/cross-platform-v1`、cross-platform v2 packages | 用于数值结论、平台解释和报告图表。 |
| 早期结果/provenance | `results/2026-04-22`、`results/2026-04-28-*` | 只作为历史和汇报图来源，不作为最新结论。 |
| 带日期报告 | `reports/2026-05-14-*`、`reports/2026-05-22-*` | 只代表对应会议日期的陈述。 |
| 长期手册 | `reports/project-long-term-beamer` | 作为学习/手册层使用，必须维护来源索引。 |
| 月报摘录 | `docs/context/monthly-intern-reports/*` | 用于叙事来源和 deck provenance，不覆盖当前 benchmark。 |
| GPU 历史资产 | `docs/context/legacy-gpu-assets.md`、`legacy_gpu/`、CUDA 后端目录 | 除非重新划定范围，否则只用于历史连续性。 |
| 清理候选 | ` 2.*` 结尾文件、陈旧重复报告/图表/脚本/测试 | 未人工提升前，不用于当前声明。 |

## 历史材料与清理规则

- 不要因为材料旧就直接删除；先判断它是否有 provenance 价值。
- 对历史解释性资产优先使用 `Archive`；对重复副本、误生成文件或未引用的 `* 2.*` 文件使用 `Delete candidate`。
- 原始 PPTX deck 不应成为仓库事实来源；如果它们支持叙事或 provenance，应保留轻量、AI 可读的摘录。
- 当 Beamer 文本或 speaker notes 与 CSV/JSON/result reports 矛盾时，不使用 Beamer 文本作为 benchmark 真值。
- 删除任何候选文件前，必须列出精确路径、可能影响和回退方法，并取得确认。

## 活跃审计

当前清理与同步审计记录在：

- `docs/context/knowledge-boundary-audit.md`

后续判断某个引用应保留、更新、归档还是删除时，先读该审计表。
