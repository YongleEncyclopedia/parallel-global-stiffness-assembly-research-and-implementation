# QA Report

## Backend Exclusivity

- Selected backend: Python.
- Plotting, export, preview raster generation, and QA checks were all run with the
  Python script in this package.
- No R graphics device or non-Python renderer was used.

## Output Files

| File | Size bytes |
| --- | ---: |
| `fig01_gpu_parallel_assembly_benchmark.svg` | 81840 |
| `fig01_gpu_parallel_assembly_benchmark.pdf` | 44297 |
| `fig01_gpu_parallel_assembly_benchmark.png` | 498721 |
| `fig01_gpu_parallel_assembly_benchmark.tiff` | 47358366 |

## Raster Dimensions

- `fig01_gpu_parallel_assembly_benchmark.png`: 3973 x 2980 px
- `fig01_gpu_parallel_assembly_benchmark.tiff`: 3973 x 2980 px

## Source Data

- Copied source CSV: `source_data/benchmark_results_2026-01-30.csv`
- SHA-256: `c5fceaf729335627e1dd519de96659717bc2ab21ce930f3fde35c3dbc85b39ea`

## Checks Passed

- Required CSV columns present.
- All expected algorithm/scale combinations present once.
- All benchmark statuses are retained in the copied source data.
- SVG keeps editable text nodes.
- At generation time PDF, SVG, PNG, and TIFF files were non-empty; the reproducible TIFF copies are no longer retained in Git.
- The retained PNG is a high-resolution raster export.
