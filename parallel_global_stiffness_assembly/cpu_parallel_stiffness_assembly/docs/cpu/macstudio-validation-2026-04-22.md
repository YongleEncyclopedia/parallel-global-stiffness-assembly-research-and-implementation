# Mac Studio Validation - 2026-04-22

## 1. 环境

- Machine: Apple M4 Max
- OS / arch: `macOS;arm64`
- Compiler: `AppleClang 21.0.0.21000099`
- OpenMP runtime: Homebrew `libomp`
- CMake: `4.3.2`

## 2. 构建与测试

执行命令：

```bash
/opt/homebrew/bin/cmake -S parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly \
  -B /tmp/pgsa_main_build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON

/opt/homebrew/bin/cmake --build /tmp/pgsa_main_build --parallel 8
ctest --test-dir /tmp/pgsa_main_build --output-on-failure
```

结果：

- `VerifyCpuAssemblers` 通过
- `VerifyInpParser` 通过

## 3. 全量实验运行方式

推荐直接使用主线实验脚本：

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
python3 scripts/run_cpu_experiments.py
```

该脚本会自动完成：

- `cube_tet4_8x8x8 + simplified`
- `3d-WindTurbineHub + simplified`
- `3d-WindTurbineHub + physics_tet4`
- `3d-WindTurbineHub + physics_tet4 + coo_sort_reduce`
- 结果 CSV / JSON / Markdown 摘要输出
- PNG / SVG 图表输出

## 4. 已完成实验

### 4.1 cube_tet4_8x8x8, simplified kernel

代表性结论：

| Algorithm | Best threads | Best assembly (ms) | Best speedup |
| --- | ---: | ---: | ---: |
| `cpu_row_owner` | 9 | `0.117` | `3.908x` |
| `cpu_atomic` | 5 | `0.144` | `3.163x` |
| `cpu_private_csr` | 5 | `0.139` | `3.280x` |
| `cpu_graph_coloring` | 1 | `0.413` | `1.106x` |
| `cpu_coo_sort_reduce` | 9 | `8.055` | `0.057x` |

### 4.2 3d-WindTurbineHub, simplified kernel

网格规模：

- Nodes: `228384`
- Elements: `1113684`
- DOFs: `685152`
- NNZ: `27502200`

代表性结论：

| Algorithm | Best threads | Best assembly (ms) | Best speedup | Extra memory |
| --- | ---: | ---: | ---: | ---: |
| `cpu_atomic` | 10 | `80.560` | `2.529x` | `0.000 GiB` |
| `cpu_private_csr` | 8 | `71.211` | `2.861x` | `1.639 GiB` |
| `cpu_coo_sort_reduce` | 12 | `4169.038` | `0.049x` | `2.390 GiB` |
| `cpu_graph_coloring` | 14 | `102.658` | `1.984x` | `0.008 GiB` |
| `cpu_row_owner` | 14 | `55.141` | `3.695x` | `1.792 GiB` |

### 4.3 3d-WindTurbineHub, physics_tet4 kernel

代表性结论：

| Algorithm | Best threads | Best assembly (ms) | Best speedup | Extra memory |
| --- | ---: | ---: | ---: | ---: |
| `cpu_atomic` | 14 | `123.174` | `4.549x` | `0.000 GiB` |
| `cpu_private_csr` | 8 | `119.566` | `4.686x` | `1.639 GiB` |
| `cpu_graph_coloring` | 8 | `153.593` | `3.648x` | `0.008 GiB` |
| `cpu_row_owner` | 8 | `120.444` | `4.652x` | `1.792 GiB` |

### 4.4 3d-WindTurbineHub, physics_tet4, coo_sort_reduce

对照结果：

| Threads | Assembly (ms) | Speedup | Extra memory |
| ---: | ---: | ---: | ---: |
| 1 | `4935.610` | `0.109x` | `2.390 GiB` |
| 2 | `4679.651` | `0.115x` | `2.390 GiB` |
| 4 | `4330.916` | `0.124x` | `2.390 GiB` |

说明：

- `coo_sort_reduce` 在真实工程网格上可正确运行
- 但当前实现明显受中间态和排序归并成本限制
- 现阶段更适合作为研究对照组，而不是主推路线

## 5. 当前结论

这台机器上的真实工程网格结果表明：

- `cpu_private_csr` 与 `cpu_row_owner` 是当前最快的两类路线
- `cpu_atomic` 有较强工程实用性，且额外内存代价最低
- `cpu_graph_coloring` 可稳定运行，但当前实现并非领先
- `cpu_coo_sort_reduce` 正确但明显偏慢，后续除非重写归并路径，否则不建议作为主力方案

## 6. 结果文件

实验结果保存在：

- [cube_tet4_simplified.csv](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/csv/cube_tet4_simplified.csv)
- [windhub_simplified.csv](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/csv/windhub_simplified.csv)
- [windhub_physics_tet4.csv](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/csv/windhub_physics_tet4.csv)
- [windhub_physics_tet4_coo_sort_reduce.csv](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/csv/windhub_physics_tet4_coo_sort_reduce.csv)
- [summary.md](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/figures/summary.md)
- [WindHub simplified dashboard](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/figures/3d-WindTurbineHub_simplified_dashboard.png)
- [WindHub physics_tet4 dashboard](../../../cpu_parallel_stiffness_assembly/results/2026-04-22/figures/3d-WindTurbineHub_physics_tet4_dashboard.png)

## 7. 备注

- `.inp` parser 已修复 `*NODE OUTPUT` 误判问题
- benchmark speedup 已统一为相对 `1` 线程串行基线
- 当前结果目录已包含 CSV / JSON / Markdown / PNG / SVG 五类产物
