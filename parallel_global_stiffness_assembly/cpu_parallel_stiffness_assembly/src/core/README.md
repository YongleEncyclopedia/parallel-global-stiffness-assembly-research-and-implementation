# 核心数据结构实现目录

## 用途

保存 Mesh、CSR、DoF map、platform 等基础实现。

## 存放内容

- 直接文件：`csr_matrix.cpp`、`dof_map.cpp`、`mesh.cpp`、`platform.cpp`
- 子目录：当前没有直接子目录。

## 不应存放

后端算法策略或报告。

## 维护提示

核心改动影响广，需同步单元测试。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src](../README.md)
