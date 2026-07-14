# CPU Parallel Assembly Benchmark Figure

This package visualizes CPU parallel assembly benchmark results with the Python /
matplotlib backend only.

## Figure Contract

- Core conclusion: CPU parallel assembly accelerates the WindHub physics Tet4
  benchmark, but the fastest backend must be interpreted together with numerical
  agreement and extra-memory cost.
- Figure archetype: quantitative grid with a dominant speedup panel and three
  supporting quantitative panels.
- Backend: Python / matplotlib only.
- Final size: double-column style, 7.2 x 4.9 inch before tight export.
- Retained output: editable SVG, vector PDF, and 600 dpi PNG preview; 600 dpi TIFF is reproducible on demand outside Git.
- Source data: four repeat-3 CPU benchmark CSV files copied into `source_data/`.
- Statistics: plotted assembly values are deterministic CSV summaries; the source
  rows report `run_count=3`, means, minima, maxima, and standard deviations, but
  this figure introduces no inferential statistics.
- Image integrity: vector line and scatter plots generated directly from CSV values;
  no raster adjustment or image enhancement is applied.
- Reviewer risk: the figure is a platform-specific CPU benchmark snapshot
  (macOS;arm64;Clang 21.0.0 (clang-2100.0.123.102);OpenMP 202011); it should not be read as cross-platform performance
  without the separate platform-profile figures.

## Panel Map

- a: Hero panel, WindHub physics Tet4 speedup versus thread count.
- b: Absolute assembly time for the same benchmark, with CPU serial shown as a
  dashed baseline.
- c: Relative L2 numerical error for parallel backends; all plotted rows are PASS.
- d: Per-backend peak speedup against extra memory at that backend's peak record.

## Main Benchmark Summary

- Mesh: 3d-WindTurbineHub
- Elements: 1,113,684
- DOFs: 685,152
- Nonzeros: 27,502,200
- Serial assembly time: 570.020 ms
- Peak CPU parallel speedup: 5.35x
  (Row owner, 12 threads,
  106.498 ms).

## Scenario Audit

| Scenario | Rows | Best backend | Threads | Best speedup | Time ms | Max extra memory GiB | Max rel L2 | Max abs |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cube simplified | 71 | Row owner | 8 | 1.92x | 0.168 | 0.01 | 1.92e-16 | 3.55e-14 |
| Cube physics | 71 | Atomic | 10 | 5.26x | 0.247 | 0.01 | 1.16e-16 | 3.05e-05 |
| WindHub simplified | 71 | Row owner | 9 | 3.47x | 56.719 | 2.87 | 1.79e-16 | 8.53e-14 |
| WindHub physics | 71 | Row owner | 12 | 5.35x | 106.498 | 2.87 | 1.61e-16 | 7.81e-03 |

## Source Data

| Source | Copied file | SHA-256 |
| --- | --- | --- |
| `01_cube_tet4_8x8x8_simplified.csv` | `source_data/01_cube_tet4_8x8x8_simplified.csv` | `7be4be692de1b37b0542b31fe1158e239c309bf04a5df6e09fe85c403a4fef03` |
| `02_cube_tet4_8x8x8_physics_tet4.csv` | `source_data/02_cube_tet4_8x8x8_physics_tet4.csv` | `4056a319cd20888c202d0b67b258650e91f726cbed14425974077881b926a9e3` |
| `03_windhub_simplified.csv` | `source_data/03_windhub_simplified.csv` | `c55c4506c3c3a659723ef2e66637e8fc29728a5347050a3c2fc54ed7aec08974` |
| `04_windhub_physics_tet4.csv` | `source_data/04_windhub_physics_tet4.csv` | `092b9e9b21490e7897f833276e193cc720302c3005cef438412d7d54e9ffc8b6` |

## Exports

| Figure | Files |
| --- | --- |
| `fig01_cpu_parallel_assembly_benchmark` | [svg](fig01_cpu_parallel_assembly_benchmark.svg), [pdf](fig01_cpu_parallel_assembly_benchmark.pdf), [png](fig01_cpu_parallel_assembly_benchmark.png) |

## QA Notes

- SVG text is preserved with `svg.fonttype = none`.
- PDF text is exported with TrueType font embedding through `pdf.fonttype = 42`.
- PNG is retained at 600 dpi; TIFF is generated only when an external delivery requires it.
- The script validates required columns, expected algorithms, duplicate thread rows,
  PASS-only source status, non-zero output sizes, image dimensions, and SVG text nodes.
