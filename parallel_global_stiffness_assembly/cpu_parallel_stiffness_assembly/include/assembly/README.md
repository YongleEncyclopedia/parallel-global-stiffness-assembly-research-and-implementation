# 组装接口与符号阶段头文件目录

## 用途

保存装配选项、装配计划、局部刚度矩阵、工厂和 symbolic/numeric 评估接口。

## 存放内容

- 直接文件：`assembler_factory.h`、`assembler_interface.h`、`assembly_options.h`、`assembly_plan.h`、`element_kernels.h`、`symbolic_numeric_eval.h`
- 子目录：当前没有直接子目录。

## 不应存放

CPU 后端私有实现或应用入口。

## 维护提示

这里定义跨后端共享契约，修改时要检查所有后端。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/include](../README.md)
