# 后端公共头文件目录

## 用途

保存不同计算后端的接口分组，目前 CPU 是当前主线，CUDA 是历史参考。

## 存放内容

- 直接文件：`atomic_assembler.h`、`coo_sort_reduce_assembler.h`、`cpu_assembler_base.h`、`graph_coloring_assembler.h`、`lock_guard_assembler.h`、`private_csr_assembler.h`、`row_owner_assembler.h`、`serial_assembler.h`
- 子目录：当前没有直接子目录。

## 不应存放

核心网格/CSR 数据结构实现。

## 维护提示

新增后端前先确认是否属于当前 CPU-first 范围。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/include/backends](../README.md)
