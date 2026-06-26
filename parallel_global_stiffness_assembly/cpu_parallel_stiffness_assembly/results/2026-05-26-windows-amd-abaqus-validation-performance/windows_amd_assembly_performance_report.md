# Windows AMD Assembly Performance Report

## 范围与结论

- 本报告只比较自研整体刚度矩阵 assembly；Abaqus/Standard 求解时间不进入任何性能结论。
- WindHub 网格：`3d-WindTurbineHub.inp`, 228,384 nodes, 1,113,684 Tet4 elements, 685,152 DOFs, `linear_elastic_solid`。
- 主线线程范围为 `1:8` 物理核心；未把 16 logical processors 的超线程结果混入主结论。
- 最快 `parallel_symbolic_reuse + cpu_atomic` 是 8 线程，amortized total 1133.4 ms；相对 `serial symbolic + serial numeric` 的 4078.26 ms 为 3.598255x。
- 最快 `direct/no-symbolic parallel` 是 8 线程，amortized total 2146.96 ms；同线程主线下仍慢于 best symbolic reuse，差异主要来自 direct sort/reduce 与 bucket merge。
- Windows 内存指标采用 OS 观测 fallback：`isolated_peak_rss_mb` 列名为历史 schema，实际 `isolated_memory_metric=windows_peak_working_set`；同时保留 `isolated_peak_private_bytes_mb`，未用 estimated bytes 冒充 OS peak RSS。

## 环境与运行条件

| 项 | 记录 |
| --- | --- |
| 日期 | 2026-05-26 |
| CPU | AMD Ryzen 7 9800X3D, 8 physical / 16 logical |
| 内存 | 33,410,088,960 bytes physical |
| 电源计划 | Balanced / 平衡 |
| 后台负载快照 | `wallpaper64`, `MsMpEng`, `System`, `dwm`, `HWINFO`, `WmiPrvSE`, `Segotep Digital-clf`, `ZSpaceSync` 位于 CPU 累计值前列。 |
| 编译 | CMake 4.3.3 + Ninja + GNU 15.2.0 |
| OpenMP | `libgomp`, OpenMP spec date 201511 |
| runner | `scripts/run_isolated_symbolic_memory_eval.py`, per-row subprocess isolation |
| memory metric | `GetProcessMemoryInfo.PeakWorkingSetSize`; private bytes from `PeakPagefileUsage`/`PrivateUsage` sampling |

## 主线时间与内存

| mode | threads | symbolic total ms | numeric/direct total ms | amortized total ms | matrix status | peak working set MB | peak private bytes MB |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `serial_symbolic_serial_numeric` | 1 | 3398.32 | 679.9403 | 4078.26 | PASS | 2311.04 | 2351.12 |
| `parallel_symbolic_reuse + cpu_atomic` | 1 | 3583.51 | 1459.78 | 5043.29 | PASS | 2311.27 | 2351.42 |
| `parallel_symbolic_reuse + cpu_atomic` | 2 | 2445.48 | 821.9291 | 3267.4 | PASS | 2311.42 | 2351.64 |
| `parallel_symbolic_reuse + cpu_atomic` | 3 | 1674.54 | 534.0669 | 2208.6 | PASS | 2312.23 | 2352.52 |
| `parallel_symbolic_reuse + cpu_atomic` | 4 | 1358.18 | 421.8101 | 1779.99 | PASS | 2315.07 | 2355.6 |
| `parallel_symbolic_reuse + cpu_atomic` | 5 | 1146.92 | 349.27 | 1496.19 | PASS | 2313.38 | 2353.88 |
| `parallel_symbolic_reuse + cpu_atomic` | 6 | 1032.85 | 309.1647 | 1342.02 | PASS | 2315.7 | 2356.27 |
| `parallel_symbolic_reuse + cpu_atomic` | 7 | 929.8142 | 273.7783 | 1203.59 | PASS | 2317.71 | 2358.36 |
| `parallel_symbolic_reuse + cpu_atomic` | 8 | 885.531 | 247.8695 | 1133.4 | PASS | 2314.71 | 2355.24 |
| `direct_no_symbolic_parallel` | 1 | 0 | 8017.37 | 8017.37 | PASS | 5584.79 | 5633.9 |
| `direct_no_symbolic_parallel` | 2 | 0 | 5289.5 | 5289.5 | PASS | 5584.21 | 6859.91 |
| `direct_no_symbolic_parallel` | 3 | 0 | 4410.88 | 4410.88 | PASS | 4768.07 | 6451.33 |
| `direct_no_symbolic_parallel` | 4 | 0 | 3713.22 | 3713.22 | PASS | 4360.32 | 6247.53 |
| `direct_no_symbolic_parallel` | 5 | 0 | 2957.52 | 2957.52 | PASS | 4095.33 | 6100.45 |
| `direct_no_symbolic_parallel` | 6 | 0 | 2481.29 | 2481.29 | PASS | 3953.14 | 6451.52 |
| `direct_no_symbolic_parallel` | 7 | 0 | 2236.86 | 2236.86 | PASS | 3825.78 | 5634.23 |
| `direct_no_symbolic_parallel` | 8 | 0 | 2146.96 | 2146.96 | PASS | 3735.79 | 5938.3 |

## 分解观察

- `parallel_symbolic_reuse + cpu_atomic` 在 8 线程下：symbolic 885.531 ms，numeric 247.8695 ms，总计 1133.4 ms。
- `direct_no_symbolic_parallel` 在 8 线程下：generate 202.9502 ms，bucket/merge 684.1595 ms，sort/reduce 1259.85 ms，总计 2146.96 ms。
- `direct_no_symbolic_parallel` 的 estimated peak bytes 为 2,898,694,948，比 symbolic path 的 1,364,927,580 高 1,533,767,368 bytes。
- OS working set：symbolic reuse 主线约 2311-2318 MB；direct/no-symbolic 主线约 3735.79-5584.79 MB。private bytes 最高为 6859.91 MB。
- `serial_symbolic_parallel_numeric` 也已采集，表现为串行 symbolic 加并行 numeric；它用于拆分 symbolic 与 numeric 贡献，不作为推荐主线。

## 产物

- CSV: `results\2026-05-26-windows-amd-abaqus-validation-performance\isolated_symbolic_memory\isolated_symbolic_memory.csv`
- JSON: `results\2026-05-26-windows-amd-abaqus-validation-performance\isolated_symbolic_memory\isolated_symbolic_memory.json`
- Markdown summary: `results\2026-05-26-windows-amd-abaqus-validation-performance\isolated_symbolic_memory\isolated_symbolic_memory.md`

## 限制

- 本机处于 Balanced 电源计划且有后台常驻进程；这些数据适合作为 Windows AMD x86_64 平台证据，不应与隔离实验机结果混写。
- 本轮没有跑 9-16 logical processor 超线程区间；主结论仅覆盖 1-8 physical cores。
- `speedup_vs_serial_direct` 字段为 0，因为本轮按指定主线模式未额外运行 `direct_no_symbolic_serial`；报告中的比值使用 `serial_symbolic_serial_numeric` 或同表总时长直接计算。
