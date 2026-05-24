# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/cross-platform-v2/cross_platform_schema_v2_report.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# PGSA Cross-Platform Benchmark Schema v2

This v2 report groups mentor action-item evidence by experiment family while preserving v1 raw CSV/JSON compatibility.

## Experiment Families

| Family | Records | Status |
| --- | ---: | --- |
| `thread_scaling` | 42 | PASS rows: 42 |
| `symbolic_direct` | 59 | PASS rows: 59 |
| `lock_vs_atomic` | 42 | PASS rows: 42 |
| `correctness_sparse` | 1 | PASS rows: 1 |
| `memory_lifecycle` | 85 | PASS rows: 85 |

## Validation

- No schema v2 errors or warnings.
