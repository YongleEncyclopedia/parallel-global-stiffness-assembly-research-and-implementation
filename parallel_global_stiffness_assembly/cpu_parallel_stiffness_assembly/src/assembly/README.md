# 装配流程实现目录

## 用途

保存装配选项解析、assembly plan、局部刚度矩阵、工厂和 symbolic/numeric 评估实现。

## 存放内容

- 直接文件：`assembler_factory.cpp`、`assembly_options.cpp`、`assembly_plan.cpp`、`element_kernels.cpp`、`symbolic_numeric_eval.cpp`
- 子目录：当前没有直接子目录。

## 不应存放

应用 CLI 或测试 fixture。

## 维护提示

这里连接核心数据结构与后端算法，修改后要跑 correctness 测试。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src](../README.md)
