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
- Relative Frobenius error: 1.51154e-16
- Maximum absolute error: 0.0078125

## Performance evidence

- Serial symbolic $CV$: 0.00389421
- Serial numeric $CV$: 0.00378206
- Scatter plan status: `PASS`; symbolic matches/checks: $54/54$; numeric setup matches/checks: $6/6$.

| Threads | Symbolic median (ms) | Symbolic CV | Numeric median (ms) | Numeric CV | Amortized median (ms) | Amortized CV | Symbolic speedup | Numeric speedup |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3535.77 | 0.00208613 | 411.274 | 0.00510893 | 4100.45 | 0.00212929 | 0.937637 | 0.359484 |
| 2 | 2273.87 | 0.00195009 | 218.034 | 0.00969829 | 2645.31 | 0.00243622 | 1.45799 | 0.678089 |
| 4 | 1633.64 | 0.00137884 | 132.977 | 0.00567311 | 1917.49 | 0.00142176 | 2.02938 | 1.11182 |
| 8 | 1341.33 | 0.00399627 | 89.7101 | 0.00450547 | 1583.79 | 0.00341711 | 2.47163 | 1.64805 |
| 16 | 1220.72 | 0.00279169 | 83.7677 | 0.014166 | 1458.18 | 0.0025434 | 2.71584 | 1.76496 |
| 20 | 1215.32 | 0.00339432 | 87.7512 | 0.0294253 | 1455.53 | 0.00372161 | 2.72789 | 1.68484 |

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

- `ctest.xml`: `3e96b6deb970ede559f58d1093e92cf15def4ae68066fb4f5b4ad9571fa12ac8` (3572 bytes)
- `benchmark_samples.csv`: `e3b58b6cd6da6ca8e97d3df5a463bb08875b1d463e1ea897450bc9e9cfaca8cc` (20716 bytes)
- `benchmark_summary.json`: `c9823d05e83b24990cc87ef7f6dded8f1e691305aa26cc6db72660940bdb0c49` (33515 bytes)
