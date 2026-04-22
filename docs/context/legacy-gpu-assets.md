# GPU 历史资产说明

本仓库当前主线是 CPU 并行整体刚度矩阵组装平台。

仓库中仍然保留了少量 CUDA / GPU 时代的历史源码与脚本，原因是：

- 它们记录了项目前一阶段的探索路径
- 某些数据结构和命名仍与历史阶段存在连续性
- 研究汇报和后续回顾时可能需要查阅

但这些内容**不是当前开发入口**。

## 当前不应作为主线入口的内容

典型例子包括：

- `src/backends/cuda/`
- `include/backends/cuda/`
- 旧的 CUDA 验证程序与 Windows CUDA 批处理脚本
- 旧的 GPU 专用绘图脚本与工作量统计脚本

## 当前真正的 CPU 主线入口

请优先使用：

- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/run_cpu_experiments.py`
- `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/plot_cpu_results.py`

## 对后续开发者的要求

- 不要把 GPU 历史脚本重新写回主 README
- 不要把 CUDA 构建重新设成 CPU 主线的必需入口
- 不要再用 GPU 时代的图表脚本输出 CPU 结果
- 如果确实需要保留历史资产，请明确标注为 `legacy`
