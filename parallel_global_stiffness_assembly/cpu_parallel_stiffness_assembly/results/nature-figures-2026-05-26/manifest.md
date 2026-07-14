# PGSA Nature-Style Figure Redraw Package

This package redraws project visualizations from existing repository results using the Python backend only.

## Figure Contract

- Core conclusion: PGSA algorithm evidence must be reviewed through correctness, memory, assembly-time, platform, symbolic/numeric, sparse-pattern, and solver-validation views.
- Figure archetype: quantitative grid, with one asymmetric mixed-modality sparse-pattern figure.
- Backend: Python / matplotlib only.
- Export contract: SVG keeps editable text; PDF is a vector submission copy; PNG is the visual preview. TIFF can be regenerated at 600 dpi but is not retained in Git.
- Source data: committed CSV/JSON result artifacts only; no benchmark was rerun by this plotting script.
- Statistics: benchmark panels report deterministic summaries from PASS rows; no inferential statistics are introduced.
- Image integrity: sparse-pattern panels plot row/column pairs from exported CSV windows without local contrast manipulation.
- Detailed figure legends: [figure_legends.md](figure_legends.md).
- Monthly report guide: [monthly_report_figure_guide.md](monthly_report_figure_guide.md).

## Figures

| Figure | Archetype | Conclusion | Exports | Source families |
| --- | --- | --- | --- | --- |
| `fig01_benchmark_three_axis_summary` | quantitative grid | Correctness, memory, and assembly-time evidence must be read together, not as speedup alone. | [svg](fig01_benchmark_three_axis_summary.svg), [pdf](fig01_benchmark_three_axis_summary.pdf), [png](fig01_benchmark_three_axis_summary.png) | benchmark_12_charts |
| `fig02_cpu_benchmark_dashboard` | quantitative grid | WindHub-scale timing shows different algorithms trade assembly time against memory and preprocessing. | [svg](fig02_cpu_benchmark_dashboard.svg), [pdf](fig02_cpu_benchmark_dashboard.pdf), [png](fig02_cpu_benchmark_dashboard.png) | cpu_benchmark |
| `fig03_thread_scaling_platforms` | quantitative grid | Thread scaling changes by platform profile, with oversubscription and memory pressure visible in the same view. | [svg](fig03_thread_scaling_platforms.svg), [pdf](fig03_thread_scaling_platforms.pdf), [png](fig03_thread_scaling_platforms.png) | thread_scaling |
| `fig04_core_profile_comparison` | quantitative grid | Full-host, performance-core, and efficiency-core profiles expose platform-specific acceleration limits. | [svg](fig04_core_profile_comparison.svg), [pdf](fig04_core_profile_comparison.pdf), [png](fig04_core_profile_comparison.png) | cross_platform, thread_scaling |
| `fig05_symbolic_memory_lifecycle` | quantitative grid | Symbolic reuse shifts cost from repeated direct assembly into persistent CSR and scatter-plan storage. | [svg](fig05_symbolic_memory_lifecycle.svg), [pdf](fig05_symbolic_memory_lifecycle.pdf), [png](fig05_symbolic_memory_lifecycle.png) | symbolic_memory |
| `fig06_backend_tradeoff` | quantitative grid | Atomic, private-CSR, and lock-guard backends separate synchronization cost from memory growth. | [svg](fig06_backend_tradeoff.svg), [pdf](fig06_backend_tradeoff.pdf), [png](fig06_backend_tradeoff.png) | symbolic_memory |
| `fig07_sparse_pattern_windows` | asymmetric mixed-modality figure | The WindHub stiffness matrix is highly sparse, structured, and reproducibly exported from serial and parallel paths. | [svg](fig07_sparse_pattern_windows.svg), [pdf](fig07_sparse_pattern_windows.pdf), [png](fig07_sparse_pattern_windows.png) | sparse_pattern |
| `fig08_solver_validation` | quantitative grid | Independent COMSOL and CalculiX probe comparisons close the solve-level validation loop. | [svg](fig08_solver_validation.svg), [pdf](fig08_solver_validation.pdf), [png](fig08_solver_validation.png) | validation |
| `fig09_basic_metrics_schema_coverage` | quantitative grid | The cross-platform v2 packages make correctness, memory, and assembly-time fields first-class review artifacts. | [svg](fig09_basic_metrics_schema_coverage.svg), [pdf](fig09_basic_metrics_schema_coverage.pdf), [png](fig09_basic_metrics_schema_coverage.png) | basic_metrics_schema |

## Source Data

| Family | Files |
| --- | --- |
| `basic_metrics_schema` | `results/2026-05-20-linux-intel-symbolic-memory-full-host/cross-platform-v2/benchmark_package_v2.json`<br>`results/2026-05-23-linux-intel-linear-elastic-full-host/cross-platform-v2/benchmark_package_v2.json`<br>`results/2026-05-24-linux-intel-linear-elastic-full-host/cross-platform-v2/benchmark_package_v2.json` |
| `benchmark_12_charts` | `results/2026-04-28-12charts-repeat3-threads1to14/csv/01_cube_tet4_8x8x8_simplified.csv`<br>`results/2026-04-28-12charts-repeat3-threads1to14/csv/02_cube_tet4_8x8x8_physics_tet4.csv`<br>`results/2026-04-28-12charts-repeat3-threads1to14/csv/03_windhub_simplified.csv`<br>`results/2026-04-28-12charts-repeat3-threads1to14/csv/04_windhub_physics_tet4.csv` |
| `cpu_benchmark` | `results/2026-04-22/csv/cube_tet4_simplified.csv`<br>`results/2026-04-22/csv/windhub_simplified.csv`<br>`results/2026-04-22/csv/windhub_physics_tet4.csv`<br>`results/2026-04-22/csv/windhub_physics_tet4_coo_sort_reduce.csv` |
| `cross_platform` | `results/2026-05-11-thread-scaling/thread_scaling_combined.csv`<br>`results/2026-05-14-thread-scaling-macos-m4max-performance-qos/thread_scaling_combined.csv`<br>`results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos/thread_scaling_combined.csv`<br>`results/2026-05-11-thread-scaling-linux-intel/thread_scaling_combined.csv`<br>`results/2026-05-12-thread-scaling-linux-intel-pcore/thread_scaling_combined.csv`<br>`results/2026-05-12-thread-scaling-linux-intel-ecore/thread_scaling_combined.csv` |
| `sparse_pattern` | `reports/2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_exact_window_serial.csv`<br>`reports/2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_exact_window_auto_serial.csv`<br>`reports/2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_visual_metadata.json`<br>`reports/2026-05-22-weekly-meeting-beamer/assets/windhub_physics_tet4_pattern_metadata.json` |
| `symbolic_memory` | `results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`<br>`results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.csv` |
| `thread_scaling` | `results/2026-05-11-thread-scaling/thread_scaling_combined.csv`<br>`results/2026-05-11-thread-scaling-linux-intel/thread_scaling_combined.csv`<br>`results/2026-05-12-thread-scaling-linux-intel-pcore/thread_scaling_combined.csv`<br>`results/2026-05-12-thread-scaling-linux-intel-ecore/thread_scaling_combined.csv`<br>`results/2026-05-14-thread-scaling-macos-m4max-performance-qos/thread_scaling_combined.csv`<br>`results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos/thread_scaling_combined.csv` |
| `validation` | `results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_medium/cantilever_hex8_medium_comsol_compare.csv`<br>`results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_small/cantilever_hex8_small_comsol_compare.csv`<br>`results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_medium/cantilever_tet4_medium_comsol_compare.csv`<br>`results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_small/cantilever_tet4_small_comsol_compare.csv`<br>`results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/cantilever_hex8_medium_calculix_probe_compare.csv`<br>`results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/cantilever_hex8_small_calculix_probe_compare.csv`<br>`results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/cantilever_tet4_medium_calculix_probe_compare.csv`<br>`results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/cantilever_tet4_small_calculix_probe_compare.csv` |

## Coverage Audit

- Existing visual artifacts under `results/` and `reports/`, excluding this redraw package: 314 files.
- Inventory split: `results/` 273 files; `reports/` 41 files.
- Retained output: 9 Nature-style figures in SVG, PDF, and PNG, plus this manifest, detailed legend file, and monthly report guide. TIFF can be regenerated from the plotting source when needed.
- Coverage unit: project visualization families and their source CSV/JSON data, not a destructive one-to-one overwrite of legacy snapshots or compiled slide PDFs.

## QA Notes

- All plotted outputs are regenerated into this directory and checked for non-zero file size.
- Detailed legends are regenerated from the script and checked for required sections per figure.
- Text is generated by matplotlib with `svg.fonttype = none` and `pdf.fonttype = 42`.
- PNG previews use 600 dpi; TIFF delivery copies are generated only when needed and stored outside Git.
- Legacy `presentation_charts` directories are used only as historical context; this package reads source CSV/JSON instead of copying old image snapshots.
