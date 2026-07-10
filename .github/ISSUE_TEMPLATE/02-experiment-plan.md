---
name: "实验计划"
about: "规划可复现的验证、benchmark 或跨平台实验"
title: "[实验] "
labels: ""
assignees: ""
---

> 以下各节均为必填。提交前删除引导注释；不适用的项目请写“无”并说明原因，不得留空。活跃实验计划只维护在本 Issue 中。

## 目标（Goal，必填）

<!-- 说明实验要回答的具体问题和可判定结果。 -->

## 非目标（Non-goals，必填）

<!-- 明确本实验不能支持的结论和不覆盖的平台、算法或输入。 -->

## 基线 SHA（Base SHA，必填）

<!-- 填写完整 base SHA，并说明其分支或 tag 来源。 -->

## 平台与环境（Platform / environment，必填）

<!-- 记录受控机器、操作系统、CPU/架构、编译器、CMake、Python、OpenMP runtime、线程/绑定设置、Git LFS 状态及外部求解器。 -->

## 输入（Inputs，必填）

<!-- 列出网格/数据集、输入校验信息、参数矩阵、重复次数、随机种子和比较基线。 -->

## 预期产物（Expected artifacts，必填）

<!-- 列出 results/、reports/ 或 Actions artifact 的具体路径、文件格式和版本化 schema。 -->

## 变更范围（Change scope，必填）

### 允许变更的路径

<!-- 列出实验脚本、配置、结果和报告路径。 -->

### 明确排除的路径或行为

<!-- 列出不可修改的实现、输入、远程资源和不允许改变的测量口径。 -->

## 实验设计（必填）

<!-- 写明自变量、因变量、控制条件、warm-up、重复与聚合方法、误差处理和停止条件。抽象符号或公式使用 LaTeX。 -->

## 验证命令（Validation commands，必填）

<!-- 使用代码块列出环境检查、构建、正确性校验、实验运行和证据检查命令，并说明预期成功条件。 -->

## 验收标准（Acceptance criteria，必填）

<!-- 使用未勾选的任务列表，覆盖输入有效性、运行完整性、schema、原始证据、摘要和可复现性。 -->

## 依赖（Dependencies，必填）

<!-- 列出前置 Issue/PR、Git LFS 资产、受控机器时段、软件许可或外部求解器；没有时写“无”。 -->

## 阻塞项（Blockers，必填）

<!-- 写明当前 blocker、负责人和解除条件；没有时写“无”。 -->

## 关闭条件（Close conditions，必填）

<!-- 列出允许最终 PR 使用 Closes #N 的条件；必须包含验收通过、原始证据归档、结论回链和 finish comment。 -->

## 机器协作记录要求

- 分支必须为 `codex/issue-<number>-<slug>`；多机器并行实验使用不同 Issue 和分支，不能并发推送同一分支。
- start comment 记录 base SHA、平台/工具链、分支、计划变更/输出路径、验证命令和 blocker。
- finish comment 记录 base/end SHA、平台/工具链、分支、实际变更/输出路径、验证命令及 `PASS`/`FAIL`、blocker。
- 中间 PR 使用 `Refs #N`；只有满足本 Issue 全部验收与关闭条件的最终 PR 使用 `Closes #N`。
