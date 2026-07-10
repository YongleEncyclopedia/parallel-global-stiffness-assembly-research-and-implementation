# 仓库协作规则

本文件适用于整个仓库。人工贡献者、Codex 及其他自动化代理都应遵守这些规则；更深层目录若有补充规则，只能在不冲突的前提下收紧本文件。

## 内容与语言

- 面向维护者的新文档默认使用中文；代码标识、命令、路径、schema key、论文名和外部工具字段可以保留英文。
- 中文 prose 涉及物理量、数学公式或抽象符号时，必须使用标准 LaTeX。例如整体刚度方程写作 $K u = f$，弹性模量和泊松比分别写作 $E$ 与 $\nu$，组装时间写作 $t_{\mathrm{assembly}}$。
- 不凭记忆复制性能结论。结论必须能够追溯到命令、输入、环境和原始证据。

## 计划、决策与证据的归属

- 仍在执行的计划以 GitHub Issue 为唯一活跃状态源；不要在仓库中维护第二份会漂移的活跃计划。
- 长期有效的协议、设计和决策写入仓库文档，并由相关 Issue 或 PR 链接。
- 原始实验、验证和复现证据只能进入相应的 `results/`、`reports/` 或 GitHub Actions artifact；Issue 和 PR 只保留摘要与稳定链接。
- CPU 主线位于 `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/`。构建、验证和实验约定见 `CONTRIBUTING.md` 及相邻文档。

## Issue 驱动工作流

1. 开始开发、实验或缺陷修复前，先建立对应 Issue，并完整填写适用模板。
2. Codex 可以在没有额外确认时起草 Issue。远程创建之前，必须向用户展示最终的标题、正文、labels、assignee 和 milestone，并等待用户明确确认；除非用户对该次远程创建另有明确授权，否则不得代替确认。
3. 每个 Issue 只允许一个活跃分支，命名为 `codex/issue-<number>-<slug>`，其中 `<number>` 是 Issue 编号，`<slug>` 是简短英文主题。
4. 多台机器不得并发推送同一个分支。需要并行工作时，拆分为独立 Issue 和独立分支，再通过 PR 集成。
5. 开始和结束机器任务时，都要在 Issue 留下机器协作记录；记录规则见下节。
6. 通过 PR 合并，禁止直接向 `main` 推送。

## 机器开始与结束记录

一对 start/finish comments 必须共同覆盖 base/end SHA、平台与工具链、分支、变更与输出路径、验证命令，以及 `PASS`、`FAIL` 或 blocker。具体要求如下：

- start comment：记录 base SHA、操作系统与架构、编译器/CMake/Python/OpenMP 等工具链、分支、计划变更路径、计划输出路径、计划验证命令、初始 blocker。
- finish comment：再次记录 base SHA，并补充 end SHA、实际平台与工具链、分支、实际变更路径、实际输出路径、逐条验证命令及其 `PASS`/`FAIL`、剩余 blocker。
- SHA 使用完整值；命令必须可复制执行；没有输出文件或 blocker 时明确写“无”并说明原因，不能省略字段。

## PR 与 Issue 关闭语义

- 中间 PR 使用 `Refs #N`，只表达关联，不关闭 Issue。
- 只有满足 Issue 全部 acceptance criteria 和 close conditions 的最终 PR 才能使用 `Closes #N`。
- PR 必须说明关联 Issue、范围、测试、证据、风险与回滚，并确认未直接推送 `main`、未重写历史。

## Git 与工作树安全

- 不覆盖、清理或回退与当前 Issue 无关的 dirty worktree 内容；发现重叠改动时停止并请求协调。
- 不重写 Git 历史，不 force-push，不直接推送 `main`。
- 提交只包含当前 Issue 范围内的文件。提交前检查 `git status --short` 和暂存区 diff。
- 不因本地便利而提交构建目录、临时文件、未归档大文件或凭据。

## 完成标准

- 运行 Issue 中列出的验证命令，并记录真实结果；不能以“应当通过”替代执行证据。
- 检查变更范围、文档链接、输出路径和 Git LFS 状态。
- 在 finish comment 中给出 end SHA、验证状态与 blocker；只有 close conditions 全部满足时才允许最终 PR 关闭 Issue。
