# CPU Parallel Global Stiffness Assembly Backend

This generated implementation turns the historical stiffness assembly codebase into the CPU-first benchmark platform `cpu_parallel_stiffness_assembly`.
It keeps the original library names (`fem_core`, `fem_assembly`) and executable name (`benchmark_assembly`) so the code can be merged into the existing repository with minimal workflow changes.

## Implemented CPU algorithms

| Algorithm flag | Class | Conflict strategy |
|---|---|---|
| `serial` | `SerialAssembler` | single-thread reference |
| `atomic` | `AtomicAssembler` | OpenMP `atomic` AddTo |
| `private_csr` | `PrivateCsrAssembler` | one full CSR value array per thread, then reduction |
| `coo_sort_reduce` | `CooSortReduceAssembler` | thread-local COO contributions, sort by CSR address, reduce |
| `coloring` | `GraphColoringAssembler` | greedy first-fit element coloring, no atomics within a color |
| `row_owner` | `RowOwnerAssembler` | owner-computes by CSR row block |

## Mesh and kernel support

- Structured cube mesh generation: `Tet4` and `Hex8`.
- Abaqus/CalculiX `.inp` parser: `*Node`, `*Element, type=C3D4`, and `*Element, type=C3D8`.
- Local stiffness kernels:
  - `simplified`: deterministic synthetic local matrix for isolating assembly cost.
  - `physics_tet4`: geometry-dependent linear-elastic `Tet4` matrix for C3D4 engineering meshes.

## Build

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON
cmake --build build/cpu-release -j
ctest --test-dir build/cpu-release --output-on-failure
```

On macOS with AppleClang, install OpenMP first if you want true parallel execution:

```bash
brew install libomp
```

If OpenMP is not found, the code still builds and runs, but parallel backends fall back to one thread.

## Smoke test

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 6 --ny 6 --nz 6 \
  --algo serial,atomic,coloring,private_csr,coo_sort_reduce,row_owner \
  --threads-list 1,2,4,8 \
  --kernel simplified --check \
  --csv results_cpu_cube.csv
```

## Engineering input test

Place the large engineering input outside the public repository or under a local-only data folder, for example:

```text
data/external/3d-WindTurbineHub.inp
```

Then start with the synthetic kernel:

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp --inp data/external/3d-WindTurbineHub.inp \
  --algo serial,atomic,coloring \
  --threads-list 1,2,4,8,16 \
  --kernel simplified --check \
  --csv results_windhub_simplified.csv
```

After topology, CSR scatter, and correctness are verified, switch to the geometry-aware Tet4 kernel:

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp --inp data/external/3d-WindTurbineHub.inp \
  --algo serial,atomic,coloring \
  --threads-list 1,2,4,8,16 \
  --kernel physics_tet4 --check \
  --csv results_windhub_physics_tet4.csv
```

`private_csr`, `coo_sort_reduce`, and `row_owner` intentionally include a transient-memory guard. Increase or decrease it with `--max-memory-gb`.

## Merge notes

This package is intended as a CPU-focused replacement/overlay for:

```text
parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/
```

It deliberately removes the requirement that CUDA be available at configure time. Historical CUDA files can be kept in the repository, but this CPU CMake entry does not compile them by default.
