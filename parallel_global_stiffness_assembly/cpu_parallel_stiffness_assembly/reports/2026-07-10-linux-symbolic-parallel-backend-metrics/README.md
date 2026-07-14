# Linux Intel 数值组装后端图件

## 用途

这是当前五类并行数值组装后端的主图与线程趋势图入口。

## 数据来源

唯一原始数据为：

```text
results/2026-07-08-linux-intel-symbolic-parallel-backends-raw/
  isolated_symbolic_memory/isolated_symbolic_memory_summary.csv
```

- 算例：风机轮毂工程网格、四面体单元、线弹性实体刚度模型。
- 基线：串行符号组装 + 串行数值组装，1 线程。
- 并行后端：原子累加、线程私有、互斥锁、图着色、按行分配。
- 每个算法/线程运行 3 次独立子进程，图中使用中位数。
- 峰值内存为隔离子进程实测 peak RSS。
- `numeric_ms = backend_prepare_ms + assembly_numeric_ms`。
- `amortized_total_ms = symbolic_total_ms + numeric_ms`。

## 内容

- `assets/`：16 线程主图以及五类算法的 1..20 线程趋势图，保留 `SVG`、`PDF`、`PNG`。
- `source_data/`：各图实际使用的行和覆盖审计。
- `*_summary.md`：字段语义、基线、取值与正确性说明。

## 复现

```bash
python3 scripts/plot_linux_symbolic_parallel_backend_metrics_cn.py
python3 scripts/plot_linux_backend_thread_trends_cn.py
```

绘图脚本只读取既有 CSV，不重新运行 benchmark。可重建的 `TIFF` 不在仓库中保留。
