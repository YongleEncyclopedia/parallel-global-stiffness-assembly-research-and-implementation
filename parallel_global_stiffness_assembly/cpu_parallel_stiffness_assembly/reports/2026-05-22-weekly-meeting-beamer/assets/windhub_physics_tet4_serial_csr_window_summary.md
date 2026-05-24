# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_serial_csr_window_summary.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# CSR Window Summary

- Matrix shape: `685152 x 685152`
- Total nnz: `27502200`
- Row window: `[0, 4)`

| row | row_offsets[row] | row_offsets[row+1] | row nnz |
| --- | ---: | ---: | ---: |
| 0 | 0 | 27 | 27 |
| 1 | 27 | 54 | 27 |
| 2 | 54 | 81 | 27 |
| 3 | 81 | 102 | 21 |
