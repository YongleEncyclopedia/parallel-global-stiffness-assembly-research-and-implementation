# 2026-05 Monthly Report Figure Guide

本说明面向 2026 年 5 月月度汇报，目标是把 2026 年 4 月汇报后的 PGSA 进展组织成可讲述、可复查的视觉证据链。

## Figure Contract

- Core conclusion: since the 2026-04 report, the project has moved from CPU benchmark availability to a reviewable evidence package covering algorithm tradeoffs, cross-platform behavior, memory lifecycle, sparse structure, solver validation, and schema-level handoff.
- Figure archetype: quantitative grid, plus one asymmetric mixed-modality sparse-pattern figure.
- Backend: Python / matplotlib only.
- Output size: compact double-column style figures, mostly 7.2 inch wide, with 7 pt base text and bold lowercase panel labels.
- Export formats: editable SVG, vector PDF, high-resolution PNG preview, and 600 dpi TIFF.
- Source policy: figures read committed CSV/JSON artifacts only; this package does not rerun benchmarks or overwrite legacy chart folders.
- Statistics policy: deterministic benchmark summaries from PASS rows; no inferential statistics or uncertainty intervals are introduced.

## Reading Order

1. Use `fig01` as the overview: correctness, memory, and time are the three axes of the monthly story.
2. Use `fig02` to connect the overview back to the 4 月 CPU WindHub baseline.
3. Use `fig03` and `fig04` to explain 5 月新增的 cross-platform and core-profile evidence.
4. Use `fig05` and `fig06` to show the symbolic/numeric and backend tradeoff work matured from raw speed to memory lifecycle analysis.
5. Use `fig07` to make the sparse-matrix structure visually concrete.
6. Use `fig08` as the strongest validation closure: independent finite-element solvers reproduce probe displacement behavior.
7. Use `fig09` to end with handoff readiness: results are now packaged into machine-readable basic metrics.

## Selection Rationale

| Figure | Monthly-report role | Why selected |
| --- | --- | --- |
| `fig01_benchmark_three_axis_summary` | Correctness, memory, and assembly-time evidence must be read together, not as speedup alone. | 作为月报第一页的总览图，先把 4 月末已有的 correctness/memory/time 基线重新组织成三轴证据，防止汇报只围绕加速比展开。 |
| `fig02_cpu_benchmark_dashboard` | WindHub-scale timing shows different algorithms trade assembly time against memory and preprocessing. | 承接 4 月 CPU 主线基准，展示真实 WindHub 网格上各后端的速度和内存取舍，是解释算法路线选择的核心图。 |
| `fig03_thread_scaling_platforms` | Thread scaling changes by platform profile, with oversubscription and memory pressure visible in the same view. | 5 月新增的重要进展是跨平台和异构核心实验；该图直接回答同一算法在 Apple/Intel 和不同核心绑定下是否稳定。 |
| `fig04_core_profile_comparison` | Full-host, performance-core, and efficiency-core profiles expose platform-specific acceleration limits. | 把线程扩展结果压缩成相对 full-host 的比值，适合在月报中解释为什么后续结果包必须记录 core profile。 |
| `fig05_symbolic_memory_lifecycle` | Symbolic reuse shifts cost from repeated direct assembly into persistent CSR and scatter-plan storage. | symbolic/numeric 解耦是 5 月从“跑得快”转向“可复用、可解释内存生命周期”的关键进展，需单独成图。 |
| `fig06_backend_tradeoff` | Atomic, private-CSR, and lock-guard backends separate synchronization cost from memory growth. | 该图把 atomic、private CSR 和 lock-guard 的同步代价拆开，便于说明为什么某些后端适合保留，某些只适合作为反例。 |
| `fig07_sparse_pattern_windows` | The WindHub stiffness matrix is highly sparse, structured, and reproducibly exported from serial and parallel paths. | 稀疏模式图是把工程网格规模、稀疏矩阵结构和并行冲突来源可视化的桥梁，适合给非实现同事建立直觉，也能解释后续内存布局与重排序分析为什么必要。 |
| `fig08_solver_validation` | Independent COMSOL and CalculiX probe comparisons close the solve-level validation loop. | COMSOL/CalculiX 独立求解器对比是 5 月最强的正确性闭环证据，应独立展示而不是藏在 benchmark 附录里。 |
| `fig09_basic_metrics_schema_coverage` | The cross-platform v2 packages make correctness, memory, and assembly-time fields first-class review artifacts. | 月报不仅要展示实验结果，也要证明结果已经进入可移交的数据契约；schema 覆盖图承担这个工程成熟度证据。 |

## What This Batch Deliberately Leaves Out

- It does not copy older presentation snapshots; all visual claims are redrawn from source CSV/JSON where possible.
- It does not rank Apple and Intel as competing products; platform panels are guardrail and completeness evidence.
- It does not claim production solver performance; solver validation is probe-level correctness evidence for exported finite-element cases.
- It does not turn schema coverage into a finished state; `fig09` intentionally exposes where memory/time fields still need broader normalization.

## Companion Files

- `manifest.md`: output inventory, source-data table, and package-level QA notes.
- `figure_legends.md`: per-figure data source, parameter settings, test background, conclusions, and interpretation.
