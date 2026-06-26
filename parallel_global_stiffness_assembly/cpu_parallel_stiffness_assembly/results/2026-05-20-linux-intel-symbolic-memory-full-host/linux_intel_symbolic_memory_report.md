# 中文阅读说明

本文件已纳入中文维护规范。下面保留的英文标识主要是命令、路径、schema key、算法名、图表文件名、历史输出或自动生成字段；这些内容需要与脚本和结果文件保持一致，不应为了翻译而改名。人工阅读时请以本说明和相邻 `README.md` 的中文目录说明为准。

- 文件角色：`parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/linux_intel_symbolic_memory_report.md`
- 维护边界：只描述来源、结构和结果字段，不把历史结果改写成新的 benchmark 结论。

## 原始内容

# Linux Intel Symbolic Memory Full-Host Report

## Scope

- Result root: `results/2026-05-20-linux-intel-symbolic-memory-full-host`
- Platform id: `linux-intel-full-host`
- Run profile: `full_host`
- Mesh: `3d-WindTurbineHub`
- Kernel: `physics_tet4`
- Thread range: `1..20` physical cores
- No P/E core isolation was used.
- No logical-core or oversubscription sweep was run. On this host `logical_cores == physical_cores == 20`.
- This run is a single full sweep: backend benchmark `--repeat 1`, symbolic eval `--assemblies-list 1`. It is not a repeat=3 average.

## Git And Host

- Commit: `3300defe286ab5a1cad467d1d0cd653173954891`
- Branch: `main`
- Dirty status at report generation:

```text
## main...origin/main
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/cross-platform-v2/benchmark_package_v2.json
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/cross-platform-v2/cross_platform_schema_v2_report.md
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/fig_backend_assembly_ms_vs_threads.png
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/fig_backend_memory_vs_threads.png
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/fig_symbolic_parallelization_compare.png
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/generate_linux_intel_symbolic_memory_report.py
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.json
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.md
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/linux_intel_symbolic_memory_report.md
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.csv
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.json
?? results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.md
```

- CPU model: `Intel(R) Core(TM) Ultra 7 265KF`
- Physical cores: `20`
- Logical cores: `20`
- OpenMP: `Linux;x86_64;GCC 13.3;OpenMP 201511`
- `OMP_DYNAMIC`: `unset`
- `OMP_PROC_BIND`: `unset`
- `OMP_PLACES`: `unset`
- Physical-core source: `os.cpu_count()` returned `20` and agrees with benchmark metadata and `lscpu` on this host.

## Commands Run

```bash
git status --short --branch --untracked-files=all
test ! -f ../../examples/3d-WindTurbineHub.inp || ! head -n 1 ../../examples/3d-WindTurbineHub.inp | grep -q 'version https://git-lfs.github.com/spec/v1'
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
build/cpu-release/bin/symbolic_numeric_eval --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 --kernel physics_tet4 --assemblies-list 1 --threads-list 1,2 --backend-list atomic,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel --csv /tmp/pgsa_symbolic_smoke.csv --json /tmp/pgsa_symbolic_smoke.json --summary-md /tmp/pgsa_symbolic_smoke.md
python3 scripts/run_isolated_symbolic_memory_eval.py --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval --out-root /tmp/pgsa_isolated_symbolic_smoke --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 --kernel physics_tet4 --assemblies-list 1 --threads-list 1,2 --backend-list atomic,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse
python3 - <<'PY'
# checked required smoke columns and required mode/strategy values
PY
RESULT_ROOT="results/$(date +%F)-linux-intel-symbolic-memory-full-host"; PHYSICAL_CORES="$(python3 - <<'PY'
import os
print(os.cpu_count() or 1)
PY
)"; mkdir -p "$RESULT_ROOT"
build/cpu-release/bin/benchmark_assembly --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --kernel physics_tet4 --algo atomic,private_csr,lock_guard --threads-range "1:${PHYSICAL_CORES}" --repeat 1 --check --schema-version pgsa-cross-platform-v2-raw --platform-id linux-intel-full-host --run-profile full_host --env-group linux_intel_symbolic_memory --max-memory-gb 32 --csv "$RESULT_ROOT/windhub_backend_tradeoff.csv" --json "$RESULT_ROOT/windhub_backend_tradeoff.json" --summary-md "$RESULT_ROOT/windhub_backend_tradeoff.md"
python3 scripts/run_isolated_symbolic_memory_eval.py --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval --out-root "$RESULT_ROOT/isolated_symbolic_memory" --mesh inp --inp ../../examples/3d-WindTurbineHub.inp --case-name 3d-WindTurbineHub --kernel physics_tet4 --assemblies-list 1 --threads-range "1:${PHYSICAL_CORES}" --backend-list atomic,private_csr,lock_guard --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel --max-memory-gb 32
python3 scripts/package_cross_platform_results_v2.py --out-dir "$RESULT_ROOT/cross-platform-v2" --platform-id linux-intel-full-host --thread-scaling-csv "$RESULT_ROOT/windhub_backend_tradeoff.csv" --symbolic-csv "$RESULT_ROOT/isolated_symbolic_memory/isolated_symbolic_memory.csv" --lock-benchmark-csv "$RESULT_ROOT/windhub_backend_tradeoff.csv"
python3 scripts/validate_benchmark_package_v2.py "$RESULT_ROOT/cross-platform-v2"
python3 results/2026-05-20-linux-intel-symbolic-memory-full-host/generate_linux_intel_symbolic_memory_report.py
```

## Correctness

- Backend tradeoff status set: `PASS`
- Backend tradeoff max `rel_l2`: `1.517e-16`
- Backend tradeoff max `max_abs`: `0.0078125`
- Symbolic eval max `rel_l2`: `1.618e-16`
- Symbolic eval max `max_abs`: `0.0078125`
- Isolated RSS rows: `141` total; missing RSS rows: `0`.

RSS was measured for this run. Estimated bytes are kept separate from measured isolated RSS.

## Backend Speed And Memory Tradeoff

| backend | best threads | best assembly ms | t1 assembly ms | t20 assembly ms | t20 speedup | t20 extra GiB | t20 estimated peak GiB | t20 isolated RSS MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cpu_atomic | 17 | 156.156 | 1309.329 | 183.178 | 4.148 | 0.00 | 1.27 | 2572.7 |
| cpu_private_csr | 7 | 279.447 | 794.749 | 484.788 | 1.567 | 4.10 | 5.37 | 6874.4 |
| cpu_lock_guard | 18 | 635.537 | 2683.864 | 655.819 | 1.159 | 1.02 | 2.30 | 3727.1 |

Conclusion: `cpu_atomic` is the most reasonable full-host numeric backend. `cpu_private_csr` is faster only at low thread counts, but its extra memory grows linearly with threads and its best observed assembly time is still slower than `cpu_atomic` on this host. `cpu_lock_guard` is dominated in speed and still carries a large lock-storage memory cost, so it is useful mainly as a correctness or contention baseline.

## Symbolic Parallelization Question

Same backend, same thread count, `serial_symbolic_parallel_numeric` versus `parallel_symbolic_reuse` at `20` threads:

| backend | serial symbolic total ms | parallel symbolic total ms | time ratio | isolated RSS delta MiB | estimated peak delta MiB | parallel symbolic temp MiB |
| --- | --- | --- | --- | --- | --- | --- |
| cpu_atomic | 3644.206 | 917.095 | 3.97x | 783.4 | 0.0 | 142.8 |
| cpu_private_csr | 3819.806 | 1203.941 | 3.17x | 678.2 | 0.0 | 142.8 |
| cpu_lock_guard | 3986.033 | 1314.133 | 3.03x | 678.2 | 0.0 | 142.8 |

Conclusion: the symbolic phase is worth parallelizing for the full-host sweep when wall time matters. At 20 threads the total time improves by roughly 3.0x to 4.0x depending on backend. The cost is higher measured isolated RSS, around 0.66 to 0.78 GiB on these 20-thread rows. At 1 thread, parallel symbolic is not useful because it adds overhead without thread-level benefit.

The estimated peak byte model does not increase for `parallel_symbolic_reuse` in the 20-thread rows because the parallel symbolic temporary buffer is smaller than the output/numeric peak component in the estimator. The measured isolated RSS still captures the real process-level increase and is therefore the RSS source of record.

## Memory Lifecycle Layers

| layer | meaning | GiB | MiB |
| --- | --- | --- | --- |
| Persistent symbolic artifacts | CSR + scatter plan | 0.96 | 984.3 |
| Common output matrix | CSR values/output storage | 0.31 | 317.4 |
| Parallel symbolic temporary bytes | Temporary work buffers for parallel CSR/plan build | 0.14 | 142.8 |
| Numeric backend extra bytes, atomic | No private matrix or lock array | 0.00 | 0.0 |
| Numeric backend extra bytes, private_csr at 20 threads | Per-thread private CSR values | 4.10 | 4196.5 |
| Numeric backend extra bytes, lock_guard | Per-entry mutex/lock storage | 1.02 | 1049.1 |
| Direct/no-symbolic transient bytes at 20 threads | Element contributions before reduction | 2.39 | 2447.1 |
| Estimated peak, atomic symbolic path | Model estimate, not RSS | 1.27 | 1301.7 |
| Isolated RSS, atomic parallel symbolic at 20 threads | Measured process peak RSS |  | 3356.0 |

Direct/no-symbolic is memory-heavy because it materializes transient contribution data before reduction. The symbolic CSR/scatter-plan path keeps persistent artifacts, then the numeric backend decides the extra memory shape: `atomic` adds no numeric backend memory, `private_csr` adds per-thread CSR values, and `lock_guard` adds per-entry lock storage.

## Figures

- `fig_backend_assembly_ms_vs_threads.png`
- `fig_backend_memory_vs_threads.png`
- `fig_symbolic_parallelization_compare.png`

## Files

- Raw backend CSV: `windhub_backend_tradeoff.csv`
- Raw backend JSON: `windhub_backend_tradeoff.json`
- Raw backend summary: `windhub_backend_tradeoff.md`
- Isolated symbolic CSV: `isolated_symbolic_memory/isolated_symbolic_memory.csv`
- Isolated symbolic JSON: `isolated_symbolic_memory/isolated_symbolic_memory.json`
- Isolated symbolic summary: `isolated_symbolic_memory/isolated_symbolic_memory.md`
- Cross-platform v2 package: `cross-platform-v2/benchmark_package_v2.json`
- Cross-platform v2 validation report: `cross-platform-v2/cross_platform_schema_v2_report.md`
