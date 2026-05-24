# Python 测试目录

## 用途

保存绘图、schema 和 core profile comparison 等 Python 自动化测试。

## 存放内容

- 直接文件：`test_benchmark_figure_redesign.py`、`test_core_profile_comparison.py`、`test_cross_platform_schema.py`、`test_cross_platform_schema_v2.py`
- 子目录：当前没有直接子目录。

## 不应存放

C++ 单元测试或结果主数据。

## 维护提示

脚本输出应写到临时目录，避免污染 tracked results。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/tests](../README.md)
