# 稀疏模式导出入口

## 用途

保存导出刚度矩阵稀疏模式的 CLI，用于可视化和跨工具检查。

## 存放内容

- 直接文件：`main.cpp`
- 子目录：当前没有直接子目录。

## 不应存放

共享算法实现或结果数据。

## 维护提示

应用目录应保持薄入口，把可复用逻辑放到 `src/` 和 `include/`。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/apps](../README.md)
