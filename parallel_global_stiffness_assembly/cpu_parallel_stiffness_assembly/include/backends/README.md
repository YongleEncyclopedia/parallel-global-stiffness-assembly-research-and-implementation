# 后端公共头文件目录

## 用途

保存不同计算后端的接口分组，目前 CPU 是当前主线，CUDA 是历史参考。

## 存放内容

- 直接文件：当前没有直接文件，主要通过子目录承载内容。
- 子目录：`cpu/`、`cuda/`

## 不应存放

核心网格/CSR 数据结构实现。

## 维护提示

新增后端前先确认是否属于当前 CPU-first 范围。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/include](../README.md)
- 子目录：[`cpu/`](cpu/README.md)
- 子目录：[`cuda/`](cuda/README.md)
