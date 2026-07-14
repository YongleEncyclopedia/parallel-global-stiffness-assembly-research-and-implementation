# QA Report

## Backend Exclusivity

- Selected backend: Python.
- Plotting, export, preview raster generation, and QA checks were all run with the
  Python script in this package.
- No R graphics device or non-Python renderer was used.

## Output Files

| File | Size bytes |
| --- | ---: |
| `fig01_cpu_parallel_assembly_benchmark.svg` | 105322 |
| `fig01_cpu_parallel_assembly_benchmark.pdf` | 48248 |
| `fig01_cpu_parallel_assembly_benchmark.png` | 675197 |
| `fig01_cpu_parallel_assembly_benchmark.tiff` | 49349006 |

## Raster Dimensions

- `fig01_cpu_parallel_assembly_benchmark.png`: 4140 x 2980 px
- `fig01_cpu_parallel_assembly_benchmark.tiff`: 4140 x 2980 px

## Source Data Hashes

- `source_data/01_cube_tet4_8x8x8_simplified.csv`: `7be4be692de1b37b0542b31fe1158e239c309bf04a5df6e09fe85c403a4fef03`
- `source_data/02_cube_tet4_8x8x8_physics_tet4.csv`: `4056a319cd20888c202d0b67b258650e91f726cbed14425974077881b926a9e3`
- `source_data/03_windhub_simplified.csv`: `c55c4506c3c3a659723ef2e66637e8fc29728a5347050a3c2fc54ed7aec08974`
- `source_data/04_windhub_physics_tet4.csv`: `092b9e9b21490e7897f833276e193cc720302c3005cef438412d7d54e9ffc8b6`

## Checks Passed

- Required CSV columns present.
- Expected CPU algorithms present in every source CSV.
- All source rows have `status=PASS`.
- No duplicate parallel algorithm/thread rows.
- SVG keeps editable text nodes.
- At generation time PDF, SVG, PNG, and TIFF files were non-empty; the reproducible TIFF copies are no longer retained in Git.
- The retained PNG is a high-resolution raster export.
