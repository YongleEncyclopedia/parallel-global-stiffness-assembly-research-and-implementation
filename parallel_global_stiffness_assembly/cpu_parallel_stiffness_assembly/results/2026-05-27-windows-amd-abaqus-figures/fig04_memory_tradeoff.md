# Fig. 4 Memory and Time Tradeoff

**绘制理由。** 性能结论不能只看时间；direct/no-symbolic 的核心成本之一是瞬时 contribution buffer。该图把 OS 观测内存、private bytes、时间-内存运行点和 estimated lifecycle peak 放在一起，避免把模型估计冒充系统观测。

**数据来源。** `results/2026-05-26-windows-amd-abaqus-validation-performance/isolated_symbolic_memory/isolated_symbolic_memory.csv` 的 `isolated_peak_working_set_mb`、`isolated_peak_private_bytes_mb` 和 `estimated_peak_bytes`。Windows 下 `isolated_peak_rss_mb` 是历史 schema 列名，本轮实际度量为 `windows_peak_working_set`。

**参数设置。** 每个策略/线程组合在独立子进程中运行；OS 内存来自 Windows `GetProcessMemoryInfo.PeakWorkingSetSize`，private bytes 来自采样到的 `PeakPagefileUsage`/`PrivateUsage`。

**可得结论。** symbolic reuse 的 peak working set 约 2.26 GiB 并随线程变化很小；direct/no-symbolic 在同一线程范围内约 3.65 到 5.45 GiB，且 8 线程 estimated lifecycle peak 也明显高于 symbolic reuse。

**合理解释。** symbolic reuse 的持久 CSR/plan 与输出矩阵占主导，内存较稳定；direct/no-symbolic 需要一次性保存大量贡献并排序归并，导致临时内存和 OS 观测峰值都更高。
