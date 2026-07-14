# Linux Intel 五类数值后端隔离实测

## 实验口径

- 平台：Intel Core Ultra 7 265KF，Linux，GCC 13.3，OpenMP 201511。
- 算例：`3d-WindTurbineHub.inp`，四面体单元，`linear_elastic_solid`。
- 基线：串行符号组装 + 串行数值组装，1 线程。
- 并行后端：原子累加、线程私有、互斥锁、图着色、按行分配，1..20 线程。
- 每个算法/线程在独立子进程中重复 3 次；`isolated_symbolic_memory_summary.csv` 保存中位数。
- 正确性以串行基线整体刚度矩阵为参考。

## 字段口径

```text
numeric_ms = backend_prepare_ms + assembly_numeric_ms
amortized_total_ms = symbolic_total_ms + numeric_ms
```

`isolated_peak_rss_mb` 是独立子进程实测峰值 RSS；`numeric_backend_extra_bytes` 等字段是结构内存解释，不替代实测峰值。

## 文件

- `isolated_symbolic_memory/isolated_symbolic_memory.csv`：全部逐次记录。
- `isolated_symbolic_memory/isolated_symbolic_memory_summary.csv`：三次中位数汇总，当前绘图唯一输入。
- `isolated_symbolic_memory/isolated_symbolic_memory.json`：原始记录与命令元数据。
- `isolated_symbolic_memory/run_commands.sh`：每个独立子进程的实际命令。
- `platform_info_full.txt` 与子目录 `platform_info.txt`：平台与运行环境。

本目录只保存原始证据，不保存图。对应图件位于 `reports/2026-07-10-linux-symbolic-parallel-backend-metrics/`。
