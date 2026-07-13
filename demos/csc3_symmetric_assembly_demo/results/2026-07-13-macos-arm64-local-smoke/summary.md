# CSC3 Demo Benchmark Summary

> **NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE**

## Run classification

- Status: `LOCAL_SMOKE`
- Evidence level: `local-smoke`
- Case: `cube_tet4_1x1x1`

## Environment

- System: `Darwin`
- Architecture: `arm64`
- CPU vendor: `Apple`
- CPU model: `Apple M5`
- Physical cores: `10`
- Compiler: `AppleClang 21.0.0.21000101`
- CMake: `4.4.0`

## Input

- Case selector: `generated-tet4`
- Grid: `{'nx': 1, 'ny': 1, 'nz': 1}`
- Input size bytes: `not recorded`
- Input SHA-256: `not recorded`

## Commands

- `configure`: `cmake --preset delivery -B '<host-path>/delivery'`
- `build`: `cmake --build '<host-path>/delivery' --config Release`
- `ctest`: `ctest --test-dir '<host-path>/delivery' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'`
- `benchmark`: `'<host-path>/csc3_demo_benchmark' --case generated-tet4 --threads-list 1,2 --warmup 1 --repeat 2 --amortization-count 2 --evidence-level local-smoke --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --nx 1 --ny 1 --nz 1`

## Correctness

- Status: `PASS`
- Relative Frobenius error: 0
- Maximum absolute error: 0

## Performance evidence

| Threads | Symbolic median (ms) | Symbolic CV | Numeric median (ms) | Numeric CV | Amortized median (ms) | Amortized CV | Symbolic speedup | Numeric speedup |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0065 | 0.160308 | 0.0004585 | 0.00109051 | 0.0043335 | 0.129803 | 1.57369 | 0.363141 |
| 2 | 0.0521875 | 0.0451162 | 0.01725 | 0.0990725 | 0.0441978 | 0.0676562 | 0.196005 | 0.00965217 |

## Performance gate

- Status: `NOT_APPLICABLE_GENERATED_CASE`
- Applicable: `False`
- Performance requirements met: `False`

## Memory and artifacts

- estimated persistent bytes: 6996
- Memory meaning: owned vector payload estimate, not RSS.
- [benchmark_samples.csv](benchmark_samples.csv)
- [benchmark_summary.json](benchmark_summary.json)
- [ctest.xml](ctest.xml)
- [run_manifest.json](run_manifest.json)

## Limits and blockers

- formal controlled-host evidence was not produced

> **NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE**

## Evidence hashes

- `ctest.xml`: `417f102f38307f566e6d865c2d8f22c5159e1f36b40d5afd842dcac1125fa814` (3339 bytes)
- `benchmark_samples.csv`: `81f53aaabdac86bcfbd8d5f8a349113b8a9adf99d97bdf057ad5d54efbd74f66` (2401 bytes)
- `benchmark_summary.json`: `5551cf9e0f09cb86c1ada694599ebd5ae436925aae6bd814b56ccd1e3de976e9` (10032 bytes)
