# 符号/数值组装效率评估报告

## 固定术语

- 符号组装：拓扑、DOF、CSR 稀疏结构和 scatter 写入位置预计算，不计算 `Ke`。
- 数值组装/物理组装：计算 `physics_tet4` 单元刚度 `Ke`，并填充全局矩阵。
- 无符号直接组装：不复用 CSR pattern 或 scatter plan，每次直接生成 `(row,col,value)` 贡献并排序归并。

## Mentor 示例 vs 当前 C++ 实现

| Mentor MATLAB 示例 | 当前 C++ 主线 | 采用策略 |
| --- | --- | --- |
| `build_symbolic_pattern` 生成稀疏模式 | `CsrMatrix::build_sparsity` 生成 CSR pattern | 保留 C++ 实现，文档显式命名为符号组装 |
| `cellDofsCache` 缓存单元 DOF | `AssemblyPlan::dofs` 缓存单元 DOF | 直接对应 |
| `allocate_global_matrix` 预分配稀疏矩阵 | `CsrMatrix` 结构复用并清零 values | 直接对应 |
| `assemble_numeric` 计算 `Ke` 并块插入 | `cpu_serial` 等 assembler 计算 `Ke` 并按 scatter 写入 | C++ 额外缓存 CSR scatter 位置，数值阶段更工程化 |
| PETSc-style `section/closure` 教学结构 | 当前节点 DOF 直接映射 | 首阶段不重构，作为未来高阶 DOF 扩展参考 |

## 实验设置

- case: `3d-WindTurbineHub`
- mesh: nodes=228384, elements=1113684, dofs=685152
- kernel: `physics_tet4`
- platform: `macOS;arm64;Clang 21.0.0 (clang-2100.1.1.101);OpenMP 202011`
- CPU: `Apple M4 Max`, physical_cores=14, logical_cores=14

## 主结论

本报告的主线是比较 `symbolic_reuse_serial` 与 `direct_no_symbolic_serial`：前者代表固定网格、固定 DOF 布局、固定稀疏结构下“一次符号组装，多次数值/物理组装”；后者代表完全不复用符号结构、每次直接生成并归并全局贡献。`symbolic_rebuild_serial` 不是目标使用场景，只作为控制实验单独解释。

- 组装 1 次：符号复用摊销总耗时 `3092.296 ms`，无符号直接组装 `5203.104 ms`，相对收益 `1.683x`。

## 主线评估：符号复用 vs 无符号直接组装

这一节直接对应 mentor 关心的“单次/多次组装效率评估”和“有符号/无符号组装效率评估”。`assemblies=1` 表示单次组装总成本；`assemblies>1` 表示同一稀疏结构下多次物理组装时，符号组装成本被摊销后的总成本。

| 组装次数 | 符号复用：符号总耗时 ms | 符号复用：数值 ms/次 | 符号复用：摊销总耗时 ms | 无符号直接：生成 ms/次 | 无符号直接：排序归并 ms/次 | 无符号直接：摊销总耗时 ms | 符号复用收益 | rel_l2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2628.604 | 463.692 | 3092.296 | 564.053 | 4639.051 | 5203.104 | 1.683 | 1.615e-16 |

## 并行 symbolic 与同核数 direct/no-symbolic

这一节直接输出 mentor 会后新增口径：`parallel_symbolic_reuse` 使用并行 CSR/scatter plan 构建，并默认用 `cpu_atomic` 做数值组装；`direct_no_symbolic_parallel` 不复用 CSR pattern 或 scatter plan，而是每次直接生成 `(row,col,value)` 贡献、按 row-range bucket 归并后排序/规约。

| mode | backend | threads | assemblies | symbolic total ms | temporary bytes | numeric ms | direct generate ms | direct bucket/merge ms | direct sort/reduce ms | amortized total ms | rel_l2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `direct_no_symbolic_parallel` | `none` | 1 | 1 | 0.000 | 0 | 0.000 | 589.991 | 896.381 | 5085.481 | 6571.854 | 1.615e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 1 | 1 | 2829.454 | 149752608 | 544.796 | 0.000 | 0.000 | 0.000 | 3374.250 | 0.000e+00 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 1 | 1 | 2749.340 | 149752608 | 447.699 | 0.000 | 0.000 | 0.000 | 3197.039 | 0.000e+00 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 1 | 1 | 2783.399 | 149752608 | 2140.447 | 0.000 | 0.000 | 0.000 | 4923.846 | 0.000e+00 |
| `direct_no_symbolic_parallel` | `none` | 2 | 1 | 0.000 | 0 | 0.000 | 306.574 | 831.921 | 2391.742 | 3530.237 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 2 | 1 | 1969.740 | 149752608 | 303.325 | 0.000 | 0.000 | 0.000 | 2273.065 | 9.042e-18 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 2 | 1 | 1979.616 | 149752608 | 250.883 | 0.000 | 0.000 | 0.000 | 2230.500 | 8.298e-18 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 2 | 1 | 1959.624 | 149752608 | 1297.785 | 0.000 | 0.000 | 0.000 | 3257.408 | 9.194e-18 |
| `direct_no_symbolic_parallel` | `none` | 3 | 1 | 0.000 | 0 | 0.000 | 236.890 | 862.565 | 1928.327 | 3027.782 | 1.615e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 3 | 1 | 1917.717 | 149752608 | 251.637 | 0.000 | 0.000 | 0.000 | 2169.353 | 1.422e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 3 | 1 | 1918.358 | 149752608 | 199.076 | 0.000 | 0.000 | 0.000 | 2117.434 | 1.297e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 3 | 1 | 1946.664 | 149752608 | 956.551 | 0.000 | 0.000 | 0.000 | 2903.215 | 1.362e-17 |
| `direct_no_symbolic_parallel` | `none` | 4 | 1 | 0.000 | 0 | 0.000 | 196.194 | 893.911 | 1429.373 | 2519.478 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 4 | 1 | 989.055 | 149752608 | 185.161 | 0.000 | 0.000 | 0.000 | 1174.216 | 1.758e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 4 | 1 | 981.589 | 149752608 | 146.589 | 0.000 | 0.000 | 0.000 | 1128.177 | 1.621e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 4 | 1 | 945.360 | 149752608 | 763.189 | 0.000 | 0.000 | 0.000 | 1708.549 | 1.740e-17 |
| `direct_no_symbolic_parallel` | `none` | 5 | 1 | 0.000 | 0 | 0.000 | 155.434 | 746.659 | 1074.077 | 1976.170 | 1.616e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 5 | 1 | 830.464 | 149752608 | 161.893 | 0.000 | 0.000 | 0.000 | 992.357 | 9.154e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 5 | 1 | 790.807 | 149752608 | 129.688 | 0.000 | 0.000 | 0.000 | 920.495 | 6.934e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 5 | 1 | 792.051 | 149752608 | 621.546 | 0.000 | 0.000 | 0.000 | 1413.597 | 9.154e-17 |
| `direct_no_symbolic_parallel` | `none` | 6 | 1 | 0.000 | 0 | 0.000 | 133.321 | 875.699 | 1073.402 | 2082.422 | 1.616e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 6 | 1 | 739.729 | 149752608 | 141.753 | 0.000 | 0.000 | 0.000 | 881.483 | 1.454e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 6 | 1 | 708.976 | 149752608 | 120.775 | 0.000 | 0.000 | 0.000 | 829.752 | 1.414e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 6 | 1 | 711.814 | 149752608 | 534.942 | 0.000 | 0.000 | 0.000 | 1246.756 | 1.443e-17 |
| `direct_no_symbolic_parallel` | `none` | 7 | 1 | 0.000 | 0 | 0.000 | 124.680 | 768.318 | 862.585 | 1755.582 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 7 | 1 | 637.012 | 149752608 | 134.374 | 0.000 | 0.000 | 0.000 | 771.386 | 1.090e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 7 | 1 | 650.303 | 149752608 | 124.044 | 0.000 | 0.000 | 0.000 | 774.347 | 8.269e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 7 | 1 | 672.268 | 149752608 | 479.225 | 0.000 | 0.000 | 0.000 | 1151.492 | 1.090e-16 |
| `direct_no_symbolic_parallel` | `none` | 8 | 1 | 0.000 | 0 | 0.000 | 107.516 | 774.296 | 761.182 | 1642.995 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 8 | 1 | 566.444 | 149752608 | 118.434 | 0.000 | 0.000 | 0.000 | 684.878 | 9.818e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 8 | 1 | 584.173 | 149752608 | 99.818 | 0.000 | 0.000 | 0.000 | 683.991 | 7.392e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 8 | 1 | 562.628 | 149752608 | 424.198 | 0.000 | 0.000 | 0.000 | 986.826 | 9.815e-17 |
| `direct_no_symbolic_parallel` | `none` | 9 | 1 | 0.000 | 0 | 0.000 | 108.116 | 664.424 | 709.393 | 1481.933 | 1.617e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 9 | 1 | 578.017 | 149752608 | 110.917 | 0.000 | 0.000 | 0.000 | 688.934 | 1.165e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 9 | 1 | 573.021 | 149752608 | 107.512 | 0.000 | 0.000 | 0.000 | 680.533 | 8.849e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 9 | 1 | 663.920 | 149752608 | 387.889 | 0.000 | 0.000 | 0.000 | 1051.809 | 1.164e-16 |
| `direct_no_symbolic_parallel` | `none` | 10 | 1 | 0.000 | 0 | 0.000 | 100.725 | 688.148 | 567.030 | 1355.902 | 1.618e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 10 | 1 | 657.762 | 149752608 | 101.828 | 0.000 | 0.000 | 0.000 | 759.589 | 1.283e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 10 | 1 | 606.436 | 149752608 | 101.800 | 0.000 | 0.000 | 0.000 | 708.236 | 9.694e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 10 | 1 | 609.613 | 149752608 | 354.959 | 0.000 | 0.000 | 0.000 | 964.571 | 1.283e-16 |
| `direct_no_symbolic_parallel` | `none` | 11 | 1 | 0.000 | 0 | 0.000 | 89.584 | 708.835 | 538.347 | 1336.765 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 11 | 1 | 561.030 | 149752608 | 104.878 | 0.000 | 0.000 | 0.000 | 665.908 | 1.371e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 11 | 1 | 558.907 | 149752608 | 118.416 | 0.000 | 0.000 | 0.000 | 677.323 | 1.038e-16 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 11 | 1 | 565.030 | 149752608 | 341.429 | 0.000 | 0.000 | 0.000 | 906.459 | 1.371e-16 |
| `direct_no_symbolic_parallel` | `none` | 12 | 1 | 0.000 | 0 | 0.000 | 86.655 | 706.957 | 555.291 | 1348.903 | 1.613e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 12 | 1 | 541.489 | 149752608 | 109.244 | 0.000 | 0.000 | 0.000 | 650.734 | 2.012e-17 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 12 | 1 | 538.178 | 149752608 | 112.955 | 0.000 | 0.000 | 0.000 | 651.133 | 1.955e-17 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 12 | 1 | 516.941 | 149752608 | 342.867 | 0.000 | 0.000 | 0.000 | 859.808 | 2.119e-17 |
| `direct_no_symbolic_parallel` | `none` | 13 | 1 | 0.000 | 0 | 0.000 | 86.305 | 719.325 | 466.999 | 1272.629 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 13 | 1 | 549.481 | 149752608 | 101.159 | 0.000 | 0.000 | 0.000 | 650.640 | 1.473e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 13 | 1 | 491.022 | 149752608 | 126.949 | 0.000 | 0.000 | 0.000 | 617.970 | 1.128e-16 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 13 | 1 | 493.474 | 149752608 | 336.386 | 0.000 | 0.000 | 0.000 | 829.860 | 1.474e-16 |
| `direct_no_symbolic_parallel` | `none` | 14 | 1 | 0.000 | 0 | 0.000 | 89.403 | 987.407 | 592.607 | 1669.417 | 1.614e-16 |
| `parallel_symbolic_reuse` | `cpu_atomic` | 14 | 1 | 554.432 | 149752608 | 107.991 | 0.000 | 0.000 | 0.000 | 662.423 | 1.511e-16 |
| `parallel_symbolic_reuse` | `cpu_private_csr` | 14 | 1 | 509.983 | 149752608 | 247.543 | 0.000 | 0.000 | 0.000 | 757.526 | 1.156e-16 |
| `parallel_symbolic_reuse` | `cpu_lock_guard` | 14 | 1 | 529.552 | 149752608 | 340.501 | 0.000 | 0.000 | 0.000 | 870.053 | 1.504e-16 |

## 控制实验：每次重建符号结构

### 为什么做这个控制实验

`symbolic_rebuild_serial` 不代表本项目推荐的使用场景，也不是 mentor 问题中的主评估对象。它用于隔离变量：如果同样采用当前 C++ 的两阶段路线，但故意不复用符号结果、每次都重建 CSR pattern 和 scatter plan，那么总成本会是多少。这个对照可以证明主线收益主要来自“符号结果复用”，而不是仅仅来自“代码路径叫做符号组装”。

### 做了什么

对每个 `assemblies_per_symbolic` 取值，`symbolic_rebuild_serial` 都重复执行完整的 `CsrMatrix::build_sparsity()` 和 `build_assembly_plan()`，随后执行一次串行 `physics_tet4` 数值组装。也就是说，组装 10 次时会重建 10 次符号结构；组装 30 次时会重建 30 次符号结构。

### 怎么做的

实现上它复用同一套符号构建函数和同一套串行数值组装函数，只改变生命周期：`symbolic_reuse_serial` 是一次构建、多次组装；`symbolic_rebuild_serial` 是每轮构建一次、组装一次。两者的数值结果都和符号复用参考矩阵比较，`rel_l2` 用于确认控制实验没有改变数学结果。

### 如何解释

如果 `symbolic_rebuild_serial` 明显慢于 `symbolic_reuse_serial`，说明多次组装场景下必须复用符号结构；如果它仍快于无符号直接组装，说明即便不复用，预先构建 CSR/scatter 也比直接贡献排序归并更高效。但项目主结论仍应以 `symbolic_reuse_serial` 为准。

| 组装次数 | 符号构建次数 | 平均 CSR 构建 ms | 平均 scatter plan ms | 平均符号总耗时 ms | 平均数值 ms/次 | 摊销总耗时 ms | 相对无符号收益 | rel_l2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1706.029 | 1281.565 | 2987.593 | 437.841 | 3425.434 | 1.519 | 0.000e+00 |
