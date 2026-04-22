# CPU 并行整体刚度矩阵组装研究与实现仓库

本仓库当前聚焦于 **CPU 平台上的并行整体刚度矩阵组装**。

它已经不再是早期的 GPU-first 实验快照，也不再处于“从零做 CPU 原型”的阶段；当前目标是把现有代码推进成一套**可复现实验平台**，能够在规则网格和真实工程网格上统一比较多种 CPU 并行算法。

## 从哪里开始

优先阅读：

- [CPU 平台并行整体刚度矩阵组装算法调研与验证需求文档](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/docs/requirements/cpu-parallel-stiffness-assembly-design.md>)
- [CPU 主线项目 README](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md>)
- [项目交接与下一阶段任务书](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/docs/plans/2026-04-22-chatgpt-pro-handoff.md>)
- [平台与路径兼容策略](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/docs/platform/cross-platform-strategy.md>)
- [工程输入与样例说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/examples/README.md>)

## 当前主线目录

后续开发只在这里继续：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

## 当前已实现的 CPU 并行算法

- `serial`
- `atomic`
- `private_csr`
- `coo_sort_reduce`
- `coloring`
- `row_owner`

详细实现方式见：

- [CPU 并行算法说明](</Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md>)

## 当前仓库包含什么

- CPU 主线代码
- 需求文档、平台策略和交接文档
- Git LFS 管理的真实工程网格 `examples/3d-WindTurbineHub.inp`
- 小型 `.inp` 回归样例
- CPU benchmark、绘图和实验调度脚本

## Git LFS

真实工程输入通过 Git LFS 管理。克隆后先执行：

```bash
brew install git-lfs
git lfs install
git lfs pull
```

Windows 环境请先安装 Git LFS，再在 Git Bash 中执行 `git lfs install`。

## 当前研究定位

本仓库现在的重点是：

- 统一 benchmark 口径
- 补齐真实工程网格上的实验矩阵
- 输出更完整的时间、加速比、效率和内存指标
- 自动生成更适合论文/PPT 使用的图表与摘要

## 关于 GPU 历史内容

仓库里仍保留少量 CUDA/GPU 时代的历史资产，仅用于参考，不是当前开发入口。继续开发时请优先遵循 CPU 主线文档和 `cpu_parallel_stiffness_assembly` 目录，而不要把 GPU 遗留脚本重新带回主流程。
