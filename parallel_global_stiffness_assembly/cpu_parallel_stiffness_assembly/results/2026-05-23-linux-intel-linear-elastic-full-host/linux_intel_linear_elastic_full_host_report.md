# Linux Intel Linear Elastic Full-Host Evidence Report

## Scope

- Case: `3d-WindTurbineHub` from `../../examples/3d-WindTurbineHub.inp`.
- Stiffness model: `linear_elastic_solid` only. No `legacy_synthetic` rows are used.
- Run profile: full host, threads `1..20`, repeat `1`, no P/E-core isolation, no logical-core oversubscription.
- Note: the long run crossed local midnight; raw CSVs and the authoritative package are intentionally kept under the explicit `2026-05-23` result root.

## Environment

- Git branch: `main`
- Git commit: `a5662381dedd9e3a622c0033939381e5fe506e9f`
- Dirty status at report generation: `## main...origin/main` plus generated untracked result files from this run.
- CPU: `Intel(R) Core(TM) Ultra 7 265KF`
- Physical/logical cores: `20/20`
- Platform/OpenMP: `Linux;x86_64;GCC 13.3;OpenMP 201511`; runtime linked by binaries: GNU `libgomp.so.1`.
- `OMP_DYNAMIC`, `OMP_PROC_BIND`, and `OMP_PLACES`: unset in the shell and empty in CSV metadata.

## Commands

```bash
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
build/cpu-release/bin/benchmark_assembly --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --stiffness-model linear_elastic_solid --algo atomic,private_csr,lock_guard --threads-range 1:20 --repeat 1 --check --schema-version pgsa-cross-platform-v2-raw --platform-id linux-intel-full-host --run-profile full_host --env-group linux_intel_linear_elastic --max-memory-gb 32 --csv results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv --json results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.json --summary-md results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.md
python3 scripts/run_isolated_symbolic_memory_eval.py --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval --out-root results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --stiffness-model linear_elastic_solid --assemblies-list 1 --threads-range 1:20 --backend-list atomic,private_csr,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel --max-memory-gb 32
python3 scripts/package_cross_platform_results_v2.py --out-dir results/2026-05-23-linux-intel-linear-elastic-full-host/cross-platform-v2 --platform-id linux-intel-full-host --thread-scaling-csv results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv --symbolic-csv results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv --lock-benchmark-csv results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv
python3 scripts/validate_benchmark_package_v2.py results/2026-05-23-linux-intel-linear-elastic-full-host/cross-platform-v2
```

## Data Integrity

- Backend CSV rows: `60`; symbolic/RSS CSV rows: `141`.
- Thread range in backend CSV: `1..20`.
- Kernel/model values present in result CSVs: `linear_elastic_solid`.
- Backend correctness max: `rel_l2=1.519e-16`, `max_abs=0.0078125`.
- Symbolic/direct correctness max: `rel_l2=1.618e-16`, `max_abs=0.00976562`.
- v2 package validation: `[OK] validated v2 package`.

## Backend Tradeoff At 20 Threads

| backend | assembly ms | total ms | speedup | extra memory MiB | peak RSS MiB | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `cpu_atomic` | 139.186 | 139.186 | 5.051 | 0.0 | 6346.4 | PASS |
| `cpu_private_csr` | 433.340 | 1765.466 | 1.622 | 4196.5 | 6556.3 | PASS |
| `cpu_lock_guard` | 536.531 | 952.144 | 1.310 | 1049.1 | 6556.3 | PASS |

Conclusion: `cpu_atomic` is the best speed/memory tradeoff on this Intel full-host run. It is fastest at 20 threads and has zero backend extra-memory bytes in the CSV, while `private_csr` pays about 4.10 GiB backend extra memory and `lock_guard` remains slower.

## Symbolic Memory Lifecycle At 20 Threads

| mode/backend | total ms | persistent MiB | symbolic temp MiB | backend extra MiB | direct transient MiB | estimated peak GiB | isolated RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| serial symbolic / serial numeric | 4094.963 | 984.3 | 0.0 | 0.0 | 0.0 | 1.27 | 2783.1 |
| direct no-symbolic / parallel | 2494.713 | 0.0 | 0.0 | 0.0 | 2447.1 | 2.70 | 3835.2 |
| serial symbolic / cpu_atomic | 3705.791 | 984.3 | 0.0 | 0.0 | 0.0 | 1.27 | 2572.7 |
| parallel symbolic / cpu_atomic | 876.890 | 984.3 | 142.8 | 0.0 | 0.0 | 1.27 | 3356.3 |
| serial symbolic / cpu_private_csr | 3888.455 | 984.3 | 0.0 | 4196.5 | 0.0 | 5.37 | 6874.7 |
| parallel symbolic / cpu_private_csr | 1193.142 | 984.3 | 142.8 | 4196.5 | 0.0 | 5.37 | 7553.1 |
| serial symbolic / cpu_lock_guard | 4006.923 | 984.3 | 0.0 | 1049.1 | 0.0 | 2.30 | 3621.8 |
| parallel symbolic / cpu_lock_guard | 1265.118 | 984.3 | 142.8 | 1049.1 | 0.0 | 2.30 | 4404.9 |

Parallel symbolic is worthwhile for elapsed time on this host: for `cpu_atomic` at 20 threads it reduces total time from 3705.791 ms to 876.890 ms, with isolated RSS rising from 2572.7 MiB to 3356.3 MiB. Direct/no-symbolic parallel is slower than parallel symbolic and uses a separate 2447.1 MiB direct transient contribution buffer.
