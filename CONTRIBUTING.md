# 贡献指南

本仓库采用 Issue 驱动的开发与实验流程。所有贡献都应可审查、可复现，并保留从计划到证据的清晰链路。

## 工具链与依赖

CPU 主线需要以下工具：

- CMake（最低版本 `3.20`，即 CMake 版本 $\ge 3.20$）；
- 支持 `C++17` 的 C++ 编译器；
- Python，用于自动化、schema 校验和部分测试；
- OpenMP，用于 CPU 并行后端；若 CMake 未找到 OpenMP，并行后端会退化为单线程，不能据此形成并行性能结论；
- Git LFS，用于获取真实工程网格等大文件。

首次克隆后运行：

```bash
git lfs install
git lfs pull
```

macOS + AppleClang 可使用 Homebrew 安装 `cmake`、`libomp` 和 `git-lfs`。Linux 与 Windows 应记录实际编译器、OpenMP runtime 和 Python 版本。

## 本地构建与测试

从仓库根目录执行：

```bash
cmake \
  -S parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly \
  -B parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON
cmake \
  --build parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/build/cpu-release \
  --parallel
ctest \
  --test-dir parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/build/cpu-release \
  --output-on-failure
```

改变实现时应运行受影响的最小测试和完整相关测试集。改变脚本或输出 schema 时，还应运行相应 Python 测试，并在 Issue 与 PR 中记录完整命令。

## 从 Issue 到分支再到 PR

1. 使用开发计划、实验计划或缺陷报告模板创建 Issue。活跃计划只保存在 Issue；长期协议或决策进入仓库文档；原始证据进入 `results/`、`reports/` 或 Actions artifact。
2. Codex 可以先起草 Issue，但远程创建前必须展示最终标题、正文、labels、assignee 和 milestone，并获得用户明确确认。仅当用户对当次操作作出明确授权时，才可直接创建。
3. 从 Issue 记录的 base SHA 建立 `codex/issue-<number>-<slug>`。同一 Issue 同时只能有一个活跃分支。
4. 在 Issue 发布 start comment，记录 base SHA、平台/工具链、分支、计划变更与输出路径、验证命令及 blocker。
5. 实施期间保持提交聚焦。不要覆盖无关 dirty worktree，不要重写历史，不要 force-push，也不要直接推送 `main`。
6. 完成后发布 finish comment，记录 base/end SHA、实际环境、实际路径、逐条命令的 `PASS`/`FAIL` 和剩余 blocker。
7. 创建 PR。中间 PR 使用 `Refs #N`；只有满足 Issue 每条 acceptance criterion 与 close condition 的最终 PR 使用 `Closes #N`。

多机器并行工作必须拆成不同 Issue 和不同分支。禁止多台机器并发推送同一个分支。

## CI 与受控机器的边界

GitHub Actions CI 负责快速、确定性的反馈：配置与编译、单元/正确性测试、小型 smoke、格式或 schema 校验。CI 结果可以证明提交在声明环境中通过这些检查，但不能代替受控性能实验。

以下工作应在记录清楚的受控机器上完成：

- 真实工程网格或大规模输入；
- 组装耗时 $t_{\mathrm{assembly}}$、加速比、效率与峰值内存等性能测量；
- 线程绑定、NUMA、性能核/能效核隔离或特定 OpenMP runtime 的实验；
- 依赖 MATLAB、Abaqus、CalculiX 或其他外部求解器的验证。

受控实验不得用 CI runner 的偶然性能作基线。跨平台比较必须使用相同输入、算法参数和版本化 schema，并分别保留每个平台的环境证据。

## 证据格式

每份验证或实验证据至少包含：

- provenance：Issue、分支、base SHA、end SHA、提交 SHA 和运行时间；
- environment：操作系统、CPU/架构、编译器、CMake、Python、OpenMP runtime、线程与绑定设置；
- inputs：网格或数据集、Git LFS 状态、参数、随机种子（如适用）和输入校验信息；
- commands：可直接复制执行的构建、运行和验证命令；
- artifacts：仓库内 `results/`/`reports/` 路径或 Actions artifact 名称与稳定链接；
- results：逐项 `PASS`/`FAIL`、blocker、退出码和关键日志摘要；
- metrics：指标名称、定义、单位、重复次数、聚合方法和比较基线。例如矩阵方程使用 $K u = f$，时间指标使用 $t_{\mathrm{assembly}}$ 并明确单位。

摘要必须回链到原始证据。不要只提交截图，也不要把无法复现的单个数值写成结论。

## 文档与审查

- 面向维护者的新文档默认使用中文。代码标识、命令、路径和外部字段可保留英文。
- 中文 prose 中的物理量、数学公式和抽象符号使用标准 LaTeX，例如 $E$、$\nu$ 与 $K u = f$。
- PR 说明必须列出关联 Issue、实际范围、测试、artifacts、风险与回滚方法。
- 提交前确认 diff 只包含 Issue 范围，并检查是否意外加入构建产物、凭据或未通过 Git LFS 管理的大文件。
