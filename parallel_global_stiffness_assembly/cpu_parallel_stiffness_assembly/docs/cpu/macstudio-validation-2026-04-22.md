# Mac Studio Validation - 2026-04-22

## Environment

- Machine: Apple M4 Max
- OS / arch: `macOS;arm64`
- Compiler: `AppleClang 21.0.0.21000099`
- OpenMP runtime: Homebrew `libomp`
- CMake: `4.3.2`

## Build

```bash
/opt/homebrew/bin/cmake -S parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly \
  -B /tmp/pgsa_main_build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON

/opt/homebrew/bin/cmake --build /tmp/pgsa_main_build --parallel 8
ctest --test-dir /tmp/pgsa_main_build --output-on-failure
```

Both tests passed:

- `VerifyCpuAssemblers`
- `VerifyInpParser`

## Benchmarks

### Cube Tet4 8x8x8, simplified kernel

Command:

```bash
/tmp/pgsa_main_build/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 8 --ny 8 --nz 8 \
  --algo serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel simplified --warmup 1 --repeat 3 --check \
  --csv parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/pgsa_main_cube.csv
```

Selected results:

| Algorithm | Best speedup | Thread count |
| --- | ---: | ---: |
| `cpu_row_owner` | 2.904 | 8 |
| `cpu_private_csr` | 2.708 | 4 |
| `cpu_atomic` | 2.197 | 4 |
| `cpu_graph_coloring` | 0.926 | 1 |
| `cpu_coo_sort_reduce` | 0.046 | 14 |

### 3d-WindTurbineHub.inp, simplified kernel

Command:

```bash
/tmp/pgsa_main_build/bin/benchmark_assembly \
  --mesh inp \
  --inp examples/3d-WindTurbineHub.inp \
  --algo serial,atomic,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel simplified --warmup 0 --repeat 1 --check \
  --csv parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/pgsa_main_windhub_simplified.csv
```

Mesh and preprocessing summary:

- Nodes: `228384`
- Elements: `1113684`
- DOFs: `685152`
- NNZ: `27502200`
- CSR memory: `317.35 MiB`
- Scatter-plan memory: `666.99 MiB`
- Mesh / CSR / scatter-plan preprocess: `558.272 ms / 1691.17 ms / 1432.46 ms`

Selected results:

| Algorithm | 1 thread (ms) | 14 threads (ms) | Speedup at 14 threads |
| --- | ---: | ---: | ---: |
| `cpu_serial` | 224.106 | - | 1.000 |
| `cpu_atomic` | 339.012 | 83.988 | 2.668 |
| `cpu_graph_coloring` | 549.431 | 96.946 | 2.312 |
| `cpu_row_owner` | 259.145 | 53.706 | 4.173 |

## Output Files

- CSV: [pgsa_main_cube.csv](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/pgsa_main_cube.csv)
- CSV: [pgsa_main_windhub_simplified.csv](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/pgsa_main_windhub_simplified.csv)
- Figure: [pgsa_main_cube_speedup.png](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/figures/pgsa_main_cube_speedup.png)
- Figure: [pgsa_main_windhub_simplified_speedup.png](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/figures/pgsa_main_windhub_simplified_speedup.png)

## Notes

- The `.inp` parser needed an Abaqus-header fix so `*NODE OUTPUT` is no longer misread as a new `*NODE` section.
- Benchmark speedup is now always normalized against the measured 1-thread serial baseline, and the serial row is emitted only once.
