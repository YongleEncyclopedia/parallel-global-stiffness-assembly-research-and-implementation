# CPU 并行整体刚度矩阵组装研究与实现仓库

本仓库当前聚焦于 **CPU 平台上的并行整体刚度矩阵组装**。

它已经不再是早期的 GPU-first 实验快照，也不再处于“从零做 CPU 原型”的阶段；当前目标是把现有代码推进成一套**可复现实验平台**，能够在规则网格和真实工程网格上统一比较多种 CPU 并行算法。

## 用途

本 README 是整个工作区的人工维护入口，用于说明当前研究主线、阅读顺序、目录治理规则和后续清理边界。

## 存放内容

仓库根目录只保留仓库级入口文件、Git/LFS 配置、工具状态目录、项目级文档目录、工程输入样例目录和 CPU 主线代码目录。具体实现和实验结果应进入对应子目录，不应堆放在根目录。

## 不应存放

根目录不应新增一次性脚本、临时结果、未说明来源的大文件、未归类报告或与 CPU 整体刚度矩阵组装无关的材料。

## 维护提示

给人阅读的新文档默认使用中文；代码标识、命令、路径、schema key、论文名和外部工具字段可以保留英文。每个 Git tracked 子目录都应有 `README.md`，目录职责变化时先更新相邻 README 再移动或新增内容。

## 相关入口

- [当前知识边界与事实优先级](docs/context/current-knowledge-boundary.md)
- [文档语言例外清单](docs/context/document-language-allowlist.md)
- [知识边界审计表与清理候选](docs/context/knowledge-boundary-audit.md)
- [CPU 主线项目 README](parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md)

## 从哪里开始

优先阅读：

- [当前知识边界与事实优先级](docs/context/current-knowledge-boundary.md)
- [CPU 平台并行整体刚度矩阵组装算法调研与验证需求文档](<docs/requirements/cpu-parallel-stiffness-assembly-design.md>)
- [CPU 主线项目 README](<parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md>)
- [平台与路径兼容策略](<docs/platform/cross-platform-strategy.md>)
- [Linux Intel 正式实验协议](<docs/platform/linux-intel-experiment-protocol.md>)
- [跨平台求解器 validation 协议](<docs/platform/cross-platform-validation-protocol.md>)
- [工程输入与样例说明](<examples/README.md>)
- [知识边界审计表与清理候选](docs/context/knowledge-boundary-audit.md)

正在执行的开发计划以 GitHub Issues 为唯一状态源；仓库文档只保存长期有效的协议、架构与实验方法。

## 当前主线目录

后续开发只在这里继续：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

## 当前已实现的 CPU 并行算法

- `serial`
- `atomic`
- `lock_guard`
- `private_csr`
- `coo_sort_reduce`
- `coloring`
- `row_owner`

详细实现方式见：

- [CPU 并行算法说明](<parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md>)

## 当前仓库包含什么

- CPU 主线代码
- 需求文档、平台策略和长期实验协议
- Git LFS 管理的真实工程网格 `examples/3d-WindTurbineHub.inp`
- 小型 `.inp` 回归样例
- CPU benchmark、绘图和实验调度脚本
- Tet4/Hex8 及 Abaqus C3D4/C3D8 输入；正式局部刚度矩阵模型为 `linear_elastic_solid`

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
- 以 3D small-strain linear elastic solid stiffness model 作为当前正式 benchmark / validation / report 口径
- 输出更完整的时间、加速比、效率和内存指标
- 自动生成更适合论文/PPT 使用的图表与摘要

## 关于 GPU 历史内容

仓库里仍保留少量 CUDA/GPU 时代的历史资产，仅用于参考，不是当前开发入口。继续开发时请优先遵循 CPU 主线文档和 `cpu_parallel_stiffness_assembly` 目录，而不要把 GPU 遗留脚本重新带回主流程。
