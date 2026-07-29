# CSC3 Demo Benchmark Summary

## Run classification

- Status: `PASS`
- Evidence level: `formal`
- Case: `3d-WindTurbineHub.inp`

## Environment

- System: `Linux`
- Architecture: `x86_64`
- CPU vendor: `GenuineIntel`
- CPU model: `Intel(R) Core(TM) Ultra 7 265KF`
- Physical cores: `20`
- Compiler: `GNU 13.3.0`
- CMake: `3.28.3`

## Input

- Case selector: `windhub`
- Grid: `not applicable`
- Input size bytes: `76111745`
- Input SHA-256: `4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`

## Commands

- `configure`: `cmake --preset delivery -B '<host-path>/build' '-DPython3_EXECUTABLE:FILEPATH=<host-path>/python'`
- `build`: `cmake --build '<host-path>/build' --config Release`
- `ctest`: `ctest --test-dir '<host-path>/build' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'`
- `benchmark`: `'<host-path>/csc3_demo_benchmark' --case windhub --threads-list 1,2,4,8,16,20 --warmup 2 --repeat 7 --amortization-count 1 --evidence-level formal --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --input '<host-path>/3d-WindTurbineHub.inp'`

## Correctness

- Status: `PASS`
- Relative Frobenius error: 1.52311e-16
- Maximum absolute error: 0.0078125

## Performance evidence

- Serial symbolic $CV$: 0.00531871
- Serial numeric $CV$: 0.00227558
- Scatter plan status: `PASS`; symbolic matches/checks: $54/54$; numeric setup matches/checks: $6/6$.

| Threads | Symbolic median (ms) | Symbolic CV | Numeric median (ms) | Numeric CV | Amortized median (ms) | Amortized CV | Symbolic speedup | Numeric speedup |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3543.09 | 0.00458059 | 411.525 | 0.00759322 | 4105.03 | 0.00451809 | 0.940058 | 0.358344 |
| 2 | 2266.52 | 0.00182308 | 218.438 | 0.0100431 | 2639.33 | 0.00197881 | 1.46953 | 0.6751 |
| 4 | 1620.73 | 0.00149538 | 132.484 | 0.00379762 | 1903.93 | 0.0015265 | 2.05507 | 1.11309 |
| 8 | 1333.15 | 0.00220357 | 89.798 | 0.0615447 | 1577.01 | 0.00412682 | 2.49837 | 1.64221 |
| 16 | 1214.31 | 0.00110745 | 84.7709 | 0.0154471 | 1451.54 | 0.00109539 | 2.74289 | 1.7396 |
| 20 | 1206.55 | 0.00805518 | 88.493 | 0.0289548 | 1448.64 | 0.00771856 | 2.76053 | 1.66643 |

## Performance gate

- Status: `PASS`
- Applicable: `True`
- Performance requirements met: `True`
- Serial symbolic/numeric $CV$ requirements met: `True` / `True`
- Scatter/formal requirements met: `True` / `True`

## Memory and artifacts

- estimated persistent bytes: 945274680
- Memory meaning: owned vector payload estimate, not RSS.
- [benchmark_samples.csv](benchmark_samples.csv)
- [benchmark_summary.json](benchmark_summary.json)
- [ctest.xml](ctest.xml)
- [run_manifest.json](run_manifest.json)

## Limits and blockers

- None recorded.

## Evidence hashes

- `ctest.xml`: `1640a6ad42d6429384f631e431b06150f878008889665d4b2716f37f4a7211b3` (3574 bytes)
- `benchmark_samples.csv`: `ccbe2fc64e13c8873bf0f792baed9c7f8c9b4e995fc1e9aa3831068f2abd8e6c` (20397 bytes)
- `benchmark_summary.json`: `984743749a5ac57a2a99b5d9d9b81c02e08327c11ff24b9afb123e6d8a7b074b` (33599 bytes)
