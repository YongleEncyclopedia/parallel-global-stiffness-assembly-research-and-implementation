# CPU Parallel Stiffness Assembly

This folder is now the repository's CPU-first benchmark platform for parallel global stiffness matrix assembly.
It keeps the historical target names `fem_core`, `fem_assembly`, and `benchmark_assembly`, while switching the default build away from mandatory CUDA.

Detailed usage notes live in [README_CPU.md](README_CPU.md).

## Implemented CPU algorithms

- `serial`: single-thread correctness and speedup baseline
- `atomic`: OpenMP `atomic` updates into the shared CSR matrix
- `private_csr`: one full CSR value buffer per thread with reduction
- `coo_sort_reduce`: thread-local COO triplets plus sort/reduce
- `coloring`: greedy graph coloring with conflict-free same-color assembly
- `row_owner`: owner-computes by CSR row range

## Build

```bash
git lfs pull
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
/opt/homebrew/bin/cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON
/opt/homebrew/bin/cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
```

If `cmake` is already on your `PATH`, you can drop the `/opt/homebrew/bin/` prefix.

On macOS with AppleClang, install OpenMP first for true multi-threaded runs:

```bash
brew install cmake libomp git-lfs
git lfs install
```

## Benchmark

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 8 --ny 8 --nz 8 \
  --algo serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner \
  --threads-list 1,2,4,8 \
  --kernel simplified --check \
  --csv results/cube_tet4_simplified.csv
```

Generate comparison figures:

```bash
python3 scripts/plot_cpu_results.py results/cube_tet4_simplified.csv --out-dir results/figures
```

Historical CUDA source files can remain in the tree for reference, but they are not part of the default CPU build.
