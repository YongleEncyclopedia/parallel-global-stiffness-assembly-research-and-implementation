# Git LFS 推出计划

## 目标

在不重写 Git 历史的前提下，把大型工程网格切换到 Git LFS 管理；小型示例输入继续保留普通 Git diff；同时让本地和远程协作设置匹配 CPU 研究工作流。

## 范围

1. 在当前 macOS 工作站安装并初始化 `git-lfs`。
2. 用不重写历史的方式让 `examples/3d-WindTurbineHub.inp` 由 Git LFS 跟踪。
3. 记录协作者工作流：安装 LFS、clone 仓库、运行 `git lfs pull`。
4. 在 GitHub 上开启合并后自动删除分支。
5. 核验后删除已经合并的过时 feature branch。

## 明确不做

- 不使用 `git lfs migrate import --everything` 重写仓库历史。
- 不 force-push `main`。
- 不默认让 GitHub source archive 包含 LFS 对象。
- 不把小型示例 `.inp` 文件迁入 Git LFS。

## 验证目标

- `git lfs version` 在本地成功。
- `.gitattributes` 包含仓库内 LFS tracking rule。
- `git lfs ls-files` 显示 `examples/3d-WindTurbineHub.inp`。
- GitHub 仓库设置 `delete_branch_on_merge` 已开启。
- 远端已合并 feature branch `codex/cpu-rename-sync` 已删除。

## 维护说明

这是 2026-04-22 的执行计划快照，不代表当前 Git LFS 状态的唯一事实来源。后续判断真实状态时，应优先检查 `.gitattributes`、`git lfs ls-files` 和当前 README。
