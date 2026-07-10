# Pull Request

> 所有章节均为必填。不适用的项目请写“无”并说明原因，不得留空。

## 关联 Issue

只勾选并填写一项：

- [ ] `Refs #N` — 中间 PR；本 PR 不满足全部关闭条件。
- [ ] `Closes #N` — 最终 PR；本 PR 已满足 Issue 的每条 acceptance criterion 与 close condition。

## 范围（Scope）

<!-- 说明本 PR 做了什么、没有做什么，并逐项列出实际变更路径。 -->

## 测试（Tests）

<!-- 列出可复制执行的完整命令、运行环境、退出码及逐项 PASS/FAIL。不能只写“测试通过”。 -->

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| <!-- 完整命令 --> | <!-- PASS/FAIL 与退出码 --> | <!-- 覆盖范围或失败原因 --> |

## 产物与证据（Artifacts）

<!-- 列出 results/、reports/ 路径或 Actions artifact 名称/链接，并说明输入、环境与 schema。没有新产物时说明原因。 -->

## 风险与回滚（Risk / rollback）

<!-- 说明行为、兼容性、性能、数据或运维风险，并给出无需重写历史的回滚步骤。 -->

## 检查清单

- [ ] 分支符合 `codex/issue-<number>-<slug>`，且同一 Issue 只有一个活跃分支。
- [ ] 变更只覆盖关联 Issue 的声明范围，没有覆盖无关 dirty worktree 内容。
- [ ] 已在 Issue 留下 start/finish comments，记录 base/end SHA、平台/工具链、分支、变更/输出路径、验证命令、`PASS`/`FAIL` 和 blocker。
- [ ] 活跃计划保留在 Issue，长期协议/决策进入仓库文档，原始证据进入 `results/`、`reports/` 或 Actions artifact。
- [ ] 已检查 Git LFS、大文件、构建产物和敏感信息。
- [ ] 未直接推送 `main`。
- [ ] 未重写 Git 历史，未 force-push。
- [ ] 若使用 `Closes #N`，Issue 的全部验收标准与关闭条件均已有可追溯证据。
