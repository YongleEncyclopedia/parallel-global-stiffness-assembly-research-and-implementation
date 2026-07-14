# 实验结果目录

## 当前可信结果

- [`2026-07-08-linux-intel-symbolic-parallel-backends-raw/`](2026-07-08-linux-intel-symbolic-parallel-backends-raw/)：当前五类并行数值组装后端的 Linux Intel 隔离实测。每个算法/线程运行三次独立子进程，汇总 CSV 取中位数。
- `validation-export/`、`2026-05-23-linux-intel-linear-elastic-full-host/`、`2026-05-26-windows-amd-abaqus-validation-performance/`：求解验证与跨平台证据入口。

当前性能图应读取：

```text
2026-07-08-linux-intel-symbolic-parallel-backends-raw/
  isolated_symbolic_memory/isolated_symbolic_memory_summary.csv
```

该数据的时间口径为：

```text
numeric_ms = backend_prepare_ms + assembly_numeric_ms
amortized_total_ms = symbolic_total_ms + numeric_ms
```

## 历史结果

- `2026-04-*` 与 `2026-05-*`：早期算法、线程扩展、平台和验证过程证据。除非当前文档明确引用，否则不作为最新性能结论。
- `nature-figures-2026-05-26/`、`2026-06-01-gpu-benchmark-nature-figure/`、`2026-06-02-cpu-benchmark-nature-figure/`：历史图件包；工作树只保留轻量可审阅格式，不保留可重建 `TIFF`。
- [`2026-06-26-archive-provenance.tsv`](2026-06-26-archive-provenance.tsv)：Issue #28 删除三个根部 tar 包时生成的历史逐成员 SHA256 对照。表中旧工作树路径已在 Issue #49 清理，不代表当前文件仍存在；其用途仅是保留删除证据。

## 维护边界

- 只保存可追溯的原始数据、命令、平台信息、摘要和必要预览。
- 禁止把估算内存写成实测峰值内存，也禁止把同一进程历史峰值解释为各算法独立内存。
- 禁止只计实际累加而漏掉图着色、私有数组、锁数组或任务划分等后端准备时间。
- 大型 tar 包必须输出到仓库外；可重建的构建目录、缓存和 `TIFF` 不进入 Git。

## 相关入口

- [CPU 主线](../README.md)
- [报告与图件](../reports/README.md)
- [Linux Intel 实验协议](../../../docs/platform/linux-intel-experiment-protocol.md)
