# 后端实现目录

## 用途

保存 CPU 当前后端和 CUDA 历史后端实现。

## 存放内容

- 直接文件：`atomic_assembler.cpp`、`coo_sort_reduce_assembler.cpp`、`cpu_assembler_base.cpp`、`graph_coloring_assembler.cpp`、`lock_guard_assembler.cpp`、`private_csr_assembler.cpp`、`row_owner_assembler.cpp`、`serial_assembler.cpp`
- 子目录：当前没有直接子目录。

## 不应存放

平台无关核心结构或报告输出。

## 维护提示

当前主线是 CPU；CUDA 子目录按 legacy 处理。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends](../README.md)
