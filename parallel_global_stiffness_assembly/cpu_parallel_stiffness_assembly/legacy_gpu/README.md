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
