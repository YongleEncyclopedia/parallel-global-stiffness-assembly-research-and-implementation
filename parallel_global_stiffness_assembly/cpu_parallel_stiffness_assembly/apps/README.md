# 命令行应用入口目录

## 用途

保存各个 C++ CLI 程序的子目录，每个子目录通常只有一个 `main.cpp`。

## 存放内容

- 直接文件：当前没有直接文件，主要通过子目录承载内容。
- 子目录：`benchmark/`、`pattern_export/`、`symbolic_eval/`、`validation_export/`

## 不应存放

共享库实现、公共头文件或实验结果。

## 维护提示

新增 CLI 时建立独立子目录，并在 CPU 主线 README 中说明用途。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly](../README.md)
- 子目录：[`benchmark/`](benchmark/README.md)
- 子目录：[`pattern_export/`](pattern_export/README.md)
- 子目录：[`symbolic_eval/`](symbolic_eval/README.md)
- 子目录：[`validation_export/`](validation_export/README.md)
