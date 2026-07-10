# 仓库范围与整理说明

## 目的

本仓库当前是为 CPU 并行整体刚度矩阵组装项目继续开发而整理的工作区。

它不是旧工作目录的完整镜像，而是面向当前 CPU 主线继续推进的可维护版本。

当前知识边界和清理状态见：

- [当前知识边界与事实优先级](current-knowledge-boundary.md)
- [知识边界审计表与清理候选](knowledge-boundary-audit.md)

## 有意保留的内容

- 更新后的 CPU 需求文档
- 平台迁移与跨平台约束说明
- 当前主线 `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`
- 工程输入 `examples/3d-WindTurbineHub.inp` 及小型回归样例

## 有意排除的内容

- 演示文稿与一次性汇报材料
- 文献大包、压缩备份、编辑器缓存
- 构建产物
- 不适合公开仓库直接保存的原始大体积中间文件

## 允许保留的汇报来源抽取

原始 PPTX 仍属于一次性汇报材料，不直接放入仓库；但当月度汇报已经成为当前 CPU 主线叙事、需求定义或后续 Beamer 的事实来源时，可以保留 AI-readable 的轻量抽取版本。

当前这类抽取统一放在：

- `docs/context/monthly-intern-reports/`

这些文件只保存逐页文本、speaker notes、媒体清单、OCR 片段、叙事脉络和复用边界，不替代原始 PPTX，也不替代 `results/` 中的 benchmark source of truth。

## 为什么保留 `parallel_global_stiffness_assembly`

项目历史里仍有值得延续的结构与代码，尤其包括：

- benchmark 主程序和参数入口
- mesh / CSR / assembler 抽象
- 当前 CPU 串行基线与多类 CPU 并行算法
- 继续补实验和补图表所需的源代码骨架

保留该目录是为了保持研究连续性，但它已经被裁剪成当前 CPU 主线可直接继续开发的版本。

## GPU 历史资产

CUDA / GPU 历史资产已从默认源码树迁入 `legacy_gpu/`，仅作参考，不是当前主线入口。详见：

- [GPU 历史资产说明](<legacy-gpu-assets.md>)

## 当前事实上的 source of truth

后续继续开发时，请按以下优先级理解项目：

1. `docs/context/current-knowledge-boundary.md`
2. `docs/requirements/cpu-parallel-stiffness-assembly-design.md`
3. `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md`
4. `docs/platform/` 中的当前平台、benchmark 和 validation 协议
5. `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/`
6. `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/`

如果历史代码与当前需求文档冲突，以需求文档和 CPU 主线 README 为准。

正在执行的任务状态不写入上述排序；它以 GitHub Issues 为唯一来源，并通过 Pull Request 与仓库内长期文档建立链接。
