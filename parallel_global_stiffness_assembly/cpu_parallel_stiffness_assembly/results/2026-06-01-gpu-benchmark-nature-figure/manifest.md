# Historical GPU Parallel Assembly Benchmark Figure

This package visualizes the provided historical GPU benchmark CSV with the Python /
matplotlib backend only.

## Figure Contract

- Core conclusion: GPU parallel assembly kernels deliver strong but scale-dependent
  speedups over CPU serial assembly, and the plotted PASS rows keep relative error
  near floating-point roundoff.
- Figure archetype: quantitative grid with a dominant speedup panel and three
  supporting quantitative panels.
- Backend: Python / matplotlib only.
- Final size: double-column style, 7.2 x 4.9 inch before tight export.
- Target output: editable SVG, vector PDF, 600 dpi PNG preview, and 600 dpi TIFF.
- Source data: `source_data/benchmark_results_2026-01-30.csv` copied from the provided CSV.
- Source data SHA-256: `c5fceaf729335627e1dd519de96659717bc2ab21ce930f3fde35c3dbc85b39ea`.
- Statistics: deterministic single benchmark rows; no inferential statistics or
  uncertainty intervals are introduced.
- Image integrity: vector line/bar plots generated directly from CSV values; no
  raster adjustment or image enhancement is applied.
- Reviewer risk: the CSV has no memory-use fields and no repeated measurements, so
  the figure must not claim memory behavior or statistical variability.

## Panel Map

- a: Hero panel, speedup versus problem scale for all algorithms.
- b: Absolute assembly time versus problem scale, showing the baseline and GPU
  kernels on comparable log scales.
- c: Numerical error for GPU kernels, with PASS status summarized from the source
  rows.
- d: Largest-mesh speedup ranking for the GPU kernels.

## Source Data Summary

- Rows: 20
- PASS rows: 20
- Algorithms: CPU serial, Atomic warp aggregation, Block parallel, Work queue
- Peak GPU speedup: 97.82x
  (Atomic warp aggregation, 10,648
  elements).

| Elements | DOFs |
| ---: | ---: |
| 216 | 1,029 |
| 1,000 | 3,993 |
| 10,648 | 36,501 |
| 64,000 | 206,763 |
| 125,000 | 397,953 |

## Largest Mesh Summary

| Algorithm | Speedup | Time ms | Relative error |
| --- | ---: | ---: | ---: |
| Atomic warp aggregation | 34.86x | 7.002 | 8.97e-17 |
| Block parallel | 35.33x | 6.908 | 8.98e-17 |
| Work queue | 23.90x | 10.214 | 8.99e-17 |

## Exports

| Figure | Files |
| --- | --- |
| `fig01_gpu_parallel_assembly_benchmark` | [svg](fig01_gpu_parallel_assembly_benchmark.svg), [pdf](fig01_gpu_parallel_assembly_benchmark.pdf), [png](fig01_gpu_parallel_assembly_benchmark.png), [tiff](fig01_gpu_parallel_assembly_benchmark.tiff) |

## QA Notes

- SVG text is preserved with `svg.fonttype = none`.
- PDF text is exported with TrueType font embedding through `pdf.fonttype = 42`.
- PNG and TIFF are exported at 600 dpi.
- The script validates required columns, algorithm/scale coverage, duplicate rows,
  non-zero output sizes, image dimensions, and SVG text nodes.
