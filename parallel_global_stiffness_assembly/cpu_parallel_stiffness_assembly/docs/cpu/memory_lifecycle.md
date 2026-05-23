# CPU 组装内存生命周期说明

## 结论

内存数字必须按生命周期解释，不能把 persistent symbolic artifacts、direct/no-symbolic transient buffers、numeric backend extra memory 和 OS-level `peak_rss_mb` 混成一个指标。

2026-05-16 WindHub 评估固定，历史字段为 `kernel=physics_tet4`；当前等价推荐口径是 `stiffness_model=linear_elastic_solid`：

- nodes: `228384`
- elements: `1113684`
- dofs: `685152`
- nnz: `27502200`
- platform: Apple M4 Max, macOS arm64, OpenMP 202011
- result root: `results/2026-05-16-mentor-action-items/`

## 字段口径

| 项目 | 生命周期 | 精度 | 字段/公式 | 说明 |
| --- | --- | --- | --- | --- |
| CSR structure + values | persistent | exact | `CsrMatrix::bytes()` | `row_offsets + col_indices + values`，WindHub 为 `317.35 MiB`。 |
| AssemblyPlan dofs/scatter | persistent | exact | `AssemblyPlan::bytes()` | WindHub 为 `666.99 MiB`。 |
| parallel symbolic row/node adjacency | transient | estimated | `symbolic_temporary_bytes` | `build_sparsity_parallel()` 估计 row-owned 临时结构，当前为 `149752608` bytes。 |
| direct/no-symbolic contributions | transient | estimated | `direct_transient_bytes = entries * sizeof(DirectContribution)` | 不复用 CSR/scatter plan，每次生成 `(row,col,value)`。 |
| `cpu_private_csr` extra memory | transient per prepare/assemble lifecycle | exact formula | `threads * nnz * sizeof(double)` | 线程越多，私有 `values` 越大。 |
| `cpu_lock_guard` extra memory | persistent while assembler prepared | exact formula | `nnz * sizeof(std::mutex)` | 与线程数无关；当前 `1760140800` bytes。 |
| `peak_rss_mb` | process-level | OS observed | `getrusage(RUSAGE_SELF).ru_maxrss` | 只作进程峰值参考，不等价于任一算法字段。 |

## 2026-05-16 读数

| 项目 | 代表读数 |
| --- | ---: |
| CSR memory | `317.35 MiB` |
| AssemblyPlan memory | `666.99 MiB` |
| parallel symbolic temporary bytes | `149752608` |
| `cpu_lock_guard` extra memory | `1760140800` |
| `cpu_private_csr` 8 线程 extra memory | `1760140800` |

## 解释规则

- `CSR + AssemblyPlan` 是 symbolic reuse 的持久成本；只要拓扑、DOF ordering 和 sparsity 不变，就可以复用。
- `direct/no-symbolic` 的 contribution buffer 是 transient；它不留下可复用 CSR/scatter plan，但每次组装都要承担生成、bucket/merge、sort/reduce 成本。
- `parallel symbolic` 的临时内存必须单独列出，因为它是为了并行构建 CSR pattern 额外引入的 row/node adjacency 工作区。
- `cpu_lock_guard` 的 mutex 内存不是 transient contribution buffer；它是 prepared assembler 生命周期内的同步结构。
- `peak_rss_mb` 可以作为 sanity check，但报告中必须和上述估算字段分列。
