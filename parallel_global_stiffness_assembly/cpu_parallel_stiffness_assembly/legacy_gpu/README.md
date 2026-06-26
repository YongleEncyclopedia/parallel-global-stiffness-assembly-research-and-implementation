# GPU 历史归档目录

## 用途

保存 GPU-first 阶段的归档说明或后续迁移标记。

## 存放内容

- 直接文件：`README.md`
- 子目录：当前没有直接子目录。

## 不应存放

当前 CPU 主线新代码或正式结果。

## 维护提示

这里是历史连续性材料，不是当前开发入口。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly](../README.md)


## 原有说明

以下保留本文件原有的详细说明；本节之前的内容是统一补充的中文目录维护说明。

# legacy_gpu：GPU 历史内容归档

本目录用于保存早期 CUDA / GPU 探索代码、验证脚本和绘图脚本，便于追溯历史实现。

它不是当前开发入口，也不参与默认 CPU benchmark、默认 CMake 配置和实验脚本。

当前主线入口保持为：

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

当前主线关注：

- CPU 多线程全局刚度矩阵装配
- OpenMP 线程数、亲和、同步与内存占用
- `serial / atomic / private_csr / coo_sort_reduce / coloring / row_owner` 的统一 benchmark
- 规则网格与真实工程网格的 CPU strong-scaling 对照

如果后续重新启动 GPU 研究，应从当前 CPU 主线重新开新分支，并明确写入新的设计文档；不要把本目录恢复成默认入口。
