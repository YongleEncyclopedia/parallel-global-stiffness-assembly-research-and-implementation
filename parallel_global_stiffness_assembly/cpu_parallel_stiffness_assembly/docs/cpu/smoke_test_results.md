# Local Smoke Test Results

These checks were run in the generation environment before packaging the source tree.

## Environment

- OS/CPU compiler line reported by the executable: `Linux;x86_64;GCC 14.2;OpenMP 201511`
- CMake configure: `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`
- Build: `cmake --build build -j1`

## Correctness unit test

```text
cpu_serial rel_l2=0 max_abs=0
cpu_atomic rel_l2=8.25602e-17 max_abs=1.42109e-14
cpu_private_csr rel_l2=1.24831e-16 max_abs=1.42109e-14
cpu_coo_sort_reduce rel_l2=1.39186e-16 max_abs=1.42109e-14
cpu_graph_coloring rel_l2=1.24944e-16 max_abs=1.42109e-14
cpu_row_owner rel_l2=0 max_abs=0
```

## Cube smoke command

```bash
./build/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 3 --ny 3 --nz 3 \
  --algo all --threads-list 1,2 --kernel simplified --check \
  --csv pgsa_cube_smoke.csv
```

All algorithms returned `PASS` against the serial reference.

## Tiny Abaqus/CalculiX input command

```bash
./build/bin/benchmark_assembly \
  --mesh inp --inp examples/tiny_c3d4.inp \
  --algo serial,atomic,coloring --threads-list 1,2 \
  --kernel physics_tet4 --check \
  --csv pgsa_tiny_inp.csv
```

All selected algorithms returned `PASS` against the serial reference.

## Medium cube comparison command

```bash
./build/bin/benchmark_assembly \
  --mesh cube --element tet4 --nx 8 --ny 8 --nz 8 \
  --algo serial,private_csr,coloring,row_owner,atomic \
  --threads-list 1,2,4 --kernel simplified --check --repeat 2 \
  --csv pgsa_cube_8.csv
```

Observed fastest backend in this small environment was `cpu_row_owner` at four threads. This is only a smoke result; use the target Mac Studio and the engineering mesh for real conclusions.
