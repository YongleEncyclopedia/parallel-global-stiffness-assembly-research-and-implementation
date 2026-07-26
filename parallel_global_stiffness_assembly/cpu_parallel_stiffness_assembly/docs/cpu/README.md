# CPU 算法与实现说明目录

## 用途

保存 CPU 后端算法、symbolic/numeric 分离、内存生命周期和 smoke 结果说明。

## 存放内容

- 直接文件：`cpu_algorithms.md`、`graph_coloring_and_private_csr_scaling.md`、`implementation_notes.md`、`memory_lifecycle.md`、`smoke_test_results.md`、`symbolic_numeric_assembly.md`
- 子目录：当前没有直接子目录。

## 不应存放

新 benchmark 原始 CSV/JSON 或会议 deck。

## 维护提示

这里是理解 CPU 实现的主要人读入口；英文术语可保留作代码对照。

## 相关入口

- 性能现象说明：[图着色与线程私有算法的性能现象说明](graph_coloring_and_private_csr_scaling.md)
- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs](../README.md)
