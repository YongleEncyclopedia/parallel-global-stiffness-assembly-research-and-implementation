# C++ 单元测试目录

## 用途

保存 CSR、Mesh 和 assembler 等基础单元测试。

## 存放内容

- 直接文件：`test_assemblers.cpp`、`test_csr.cpp`、`test_mesh.cpp`
- 子目录：当前没有直接子目录。

## 不应存放

长时间 benchmark 或外部平台结果。

## 维护提示

核心接口改动后优先跑这里。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/tests](../README.md)
