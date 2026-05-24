# CMake 模块目录

## 用途

保存编译选项、依赖查找和 CUDA 历史配置等 CMake include 文件。

## 存放内容

- 直接文件：`CompilerFlags.cmake`、`CudaConfig.cmake`、`Dependencies.cmake`
- 子目录：当前没有直接子目录。

## 不应存放

业务源码、benchmark 输出或人工报告。

## 维护提示

修改后至少运行 CMake configure，确认配置仍能解析。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly](../README.md)
