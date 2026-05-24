# 核心数据结构头文件目录

## 用途

保存 Mesh、CSR、DoF map、platform 和基础类型接口。

## 存放内容

- 直接文件：`csr_matrix.h`、`dof_map.h`、`mesh.h`、`platform.h`、`soa.h`、`types.h`
- 子目录：当前没有直接子目录。

## 不应存放

后端算法实现或报告材料。

## 维护提示

核心接口影响范围大，修改后需要跑单元和 correctness 测试。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/include](../README.md)
