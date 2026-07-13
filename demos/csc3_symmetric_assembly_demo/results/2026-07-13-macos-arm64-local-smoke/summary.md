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

- `configure`: `cmake --preset delivery -B '<host-path>/build'`
- `build`: `cmake --build '<host-path>/build' --config Release`
- `ctest`: `ctest --test-dir '<host-path>/build' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'`
- `benchmark`: `'<host-path>/csc3_demo_benchmark' --case generated-tet4 --threads-list 1,2 --warmup 1 --repeat 2 --amortization-count 2 --evidence-level local-smoke --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --nx 1 --ny 1 --nz 1`

## Correctness

- Status: `PASS`
- Relative Frobenius error: 0
- Maximum absolute error: 0

## Performance evidence

| Threads | Symbolic median (ms) | Symbolic CV | Numeric median (ms) | Numeric CV | Amortized median (ms) | Amortized CV | Symbolic speedup | Numeric speedup |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0174585 | 0.114586 | 0.001479 | 0.0135227 | 0.0117293 | 0.0816975 | 1.66108 | 0.323867 |
| 2 | 0.106604 | 0.0361525 | 0.026291 | 0.0174204 | 0.0819895 | 0.0293513 | 0.272035 | 0.0182192 |

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

- `ctest.xml`: `cb1d554b08e8a27ae0af16a498a0cf3a6d65275a6606342f3f84d25608e0a4c1` (3322 bytes)
- `benchmark_samples.csv`: `800e8e111547941d4be89f72c2b7e712e04e03ce5826d95f598a91a747fd7a02` (2361 bytes)
- `benchmark_summary.json`: `201e4cce36ac872d7ef37ab8d0bf75f6fdb5dcec458a63cdab5a56f014f3a33a` (10114 bytes)
