# Apple M4 Max QoS-Biased P/E-Core Supplement

## Scope

This supplement keeps the existing Apple M4 Max `full_host` run as the mixed Mac baseline and adds two macOS scheduler-policy sensitivity runs:

- Performance profile: `results/2026-05-14-thread-scaling-macos-m4max-performance-qos`, normal foreground/default scheduling, `threads=1..10`.
- Efficiency profile: `results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos`, `taskpolicy -c background`, `threads=1..4`.

Both new profiles are recorded as `QoS-biased sensitivity run; not hard-pinned core affinity`. They are not equivalent to Linux `taskset` CPU affinity.

## Host And QoS Evidence

- CPU model: `Apple M4 Max`
- physical_cores: `14`
- logical_cores: `14`
- performance_core_count: `10`
- efficiency_core_count: `4`
- affinity_control metadata: `manual`
- Core-class evidence: `sysctl hw.perflevel0/1.physicalcpu`.
- QoS policy evidence: Apple documents QoS as the public mechanism that influences P/E core placement on Apple Silicon; macOS `taskpolicy` exposes QoS/background policy but not per-core hard pinning.

## Commands

```bash
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release -j
ctest --test-dir build/cpu-release --output-on-failure

/Library/Developer/CommandLineTools/usr/bin/python3 scripts/run_thread_scaling_eval.py --skip-build --threads-range 1:10 --warmup 1 --repeat 3 --max-memory-gb 32.0 --out-root results/2026-05-14-thread-scaling-macos-m4max-performance-qos --platform-id apple-m4-max --run-profile performance_core_only --profile-note Performance QoS: QoS-biased sensitivity run; not hard-pinned core affinity. normal foreground/default scheduling; thread range limited to detected P-core count.
python3 scripts/plot_thread_scaling_results.py --results-root results/2026-05-14-thread-scaling-macos-m4max-performance-qos

taskpolicy -c background /Library/Developer/CommandLineTools/usr/bin/python3 scripts/run_thread_scaling_eval.py --skip-build --threads-range 1:4 --warmup 1 --repeat 3 --max-memory-gb 32.0 --out-root results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos --platform-id apple-m4-max --run-profile efficiency_core_only --profile-note Efficiency QoS: QoS-biased sensitivity run; not hard-pinned core affinity. taskpolicy -c background; thread range limited to detected E-core count.
python3 scripts/plot_thread_scaling_results.py --results-root results/2026-05-14-thread-scaling-macos-m4max-efficiency-qos
```

## Validation

- Release configure/build completed successfully.
- `ctest`: `6/6` tests passed.
- Performance QoS: `80` combined rows, `non_pass=0`.
- Efficiency QoS: `32` combined rows, `non_pass=0`.
- Each new output root contains combined CSV, default/bound CSV+JSON+summary files, figure index, contact sheet, and default/bound dashboard PNG/SVG files.

## Bound Best-Time Comparison

The table below uses `bound` as the primary interpretation group. Runtime changes within `5%` are treated as roughly flat.

| Algorithm | Full-host bound best | Performance QoS best | P QoS vs full | Efficiency QoS best | E QoS vs full | E vs P |
| --- | ---: | ---: | --- | ---: | --- | --- |
| `cpu_atomic` | `23T`, `116.568 ms` | `9T`, `137.305 ms` | slower by `17.8%` | `4T`, `2213.704 ms` | slower by `1799.1%` | slower by `1512.3%` |
| `cpu_private_csr` | `10T`, `113.933 ms` | `9T`, `116.150 ms` | within `5%` | `4T`, `1839.601 ms` | slower by `1514.6%` | slower by `1483.8%` |
| `cpu_row_owner` | `12T`, `114.460 ms` | `10T`, `126.131 ms` | slower by `10.2%` | `4T`, `2186.021 ms` | slower by `1809.9%` | slower by `1633.1%` |
| `cpu_graph_coloring` | `18T`, `139.994 ms` | `8T`, `181.230 ms` | slower by `29.5%` | `4T`, `2091.895 ms` | slower by `1394.3%` | slower by `1054.3%` |

## Interpretation Boundary

These results are macOS QoS-policy sensitivity results under restricted thread ranges. They should not be interpreted as intrinsic P-core-only or E-core-only hardware throughput, and they should not be compared with the Intel `taskset` results as if the isolation mechanism were identical.

Generated on `2026-05-14`.

<!-- core-profile-comparison-figure:start -->
## Core-Profile Acceleration Figure

This figure visualizes macOS QoS-biased sensitivity data. It is not evidence of hard-pinned core affinity.

### Apple M4 Max

![Apple M4 Max core-profile acceleration comparison](cross-platform-v1/figures/core_profile_speedup_comparison_apple_m4_max.png)

[Apple M4 Max SVG](cross-platform-v1/figures/core_profile_speedup_comparison_apple_m4_max.svg)
<!-- core-profile-comparison-figure:end -->
