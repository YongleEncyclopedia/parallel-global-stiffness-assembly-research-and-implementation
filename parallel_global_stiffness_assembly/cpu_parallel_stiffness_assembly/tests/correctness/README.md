# 正确性验证测试目录

## 用途

保存验证 benchmark schema、`.inp` 解析、物理 kernel、symbolic/numeric CLI 和 validation export 的测试。

## 存放内容

- 直接文件：`verify_benchmark_schema.py`、`verify_inp_parser.cpp`、`verify_isolated_symbolic_memory_runner.py`、`verify_pattern_export.py`、`verify_physics_solid_kernel.cpp`、`verify_results.cpp`、`verify_symbolic_numeric_eval.cpp`、`verify_symbolic_parallel_cli.py`、`verify_thread_region.cpp`、`verify_validation_export.py`
- 子目录：当前没有直接子目录。

## 不应存放

性能 benchmark 主结果。

## 维护提示

这些测试保护行为契约，改 CLI 或 schema 时必须同步。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/tests](../README.md)
