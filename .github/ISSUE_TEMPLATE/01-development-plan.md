---
name: "开发计划"
about: "规划代码、文档、构建或自动化变更"
title: "[开发] "
labels: ""
assignees: ""
---

> 以下各节均为必填。提交前删除引导注释；不适用的项目请写“无”并说明原因，不得留空。活跃计划只维护在本 Issue 中。

## 目标（Goal，必填）

<!-- 用可验证的一句话说明完成后具备的行为或能力。 -->

## 非目标（Non-goals，必填）

<!-- 明确本 Issue 不处理的事项，避免隐式扩展范围。 -->

## 基线 SHA（Base SHA，必填）

<!-- 填写完整 base SHA，并说明其分支或 tag 来源。 -->

## 平台与环境（Platform / environment，必填）

<!-- 记录操作系统、CPU/架构、编译器、CMake、Python、OpenMP runtime、Git LFS 状态及相关依赖版本。 -->

## 输入（Inputs，必填）

<!-- 列出代码版本、网格/数据、配置、参数、随机种子及外部依赖；不适用时说明原因。 -->

## 预期产物（Expected artifacts，必填）

<!-- 列出预期代码/文档文件，以及 results/、reports/ 或 Actions artifact 的具体输出路径。 -->

## 变更范围（Change scope，必填）

### 允许变更的路径

<!-- 逐项列出路径。 -->

### 明确排除的路径或行为

<!-- 列出不可修改的文件、远程资源与非目标行为。 -->

## 实施步骤（必填）

<!-- 用有序列表给出可独立验证的最小步骤。 -->

## 验证命令（Validation commands，必填）

<!-- 使用代码块列出可复制执行的完整命令，并说明每条命令的预期成功条件。 -->

## 验收标准（Acceptance criteria，必填）

<!-- 每项必须可客观判定；使用未勾选的任务列表。 -->

## 依赖（Dependencies，必填）

<!-- 列出前置 Issue/PR、数据、工具、权限或外部团队；没有时写“无”。 -->

## 阻塞项（Blockers，必填）

<!-- 写明当前 blocker、负责人和解除条件；没有时写“无”。 -->

## 关闭条件（Close conditions，必填）

<!-- 列出允许最终 PR 使用 Closes #N 的全部条件，包括验收、证据、文档和 finish comment。 -->

## 机器协作记录要求

- 分支必须为 `codex/issue-<number>-<slug>`，同一时间只允许一个活跃分支。
- start comment 记录 base SHA、平台/工具链、分支、计划变更/输出路径、验证命令和 blocker。
- finish comment 记录 base/end SHA、平台/工具链、分支、实际变更/输出路径、验证命令及 `PASS`/`FAIL`、blocker。
- 中间 PR 使用 `Refs #N`；只有满足本 Issue 全部验收与关闭条件的最终 PR 使用 `Closes #N`。
