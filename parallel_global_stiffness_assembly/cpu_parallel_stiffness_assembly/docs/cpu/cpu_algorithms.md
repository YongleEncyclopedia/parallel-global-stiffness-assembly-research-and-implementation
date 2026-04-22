# CPU 并行组装算法说明

本文档说明当前主线项目已经实现的 CPU 并行整体刚度矩阵组装算法、对应源码位置、核心实现机制、额外内存代价以及当前已知优缺点。

## 项目当前实现的算法

当前通过统一工厂注册的 CPU 算法共有 6 类，注册入口见：

- [assembler_factory.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/assembly/assembler_factory.cpp)

| CLI 名称 | 内部标识 | 主要思想 | 是否需要原子操作 |
| --- | --- | --- | --- |
| `serial` | `cpu_serial` | 串行 CSR 组装基线 | 否 |
| `atomic` | `cpu_atomic` | OpenMP 原子直接累加 | 是 |
| `private_csr` | `cpu_private_csr` | 线程私有 CSR + 归并 | 否 |
| `coo_sort_reduce` | `cpu_coo_sort_reduce` | 线程私有 COO + 排序归并 | 否 |
| `coloring` | `cpu_graph_coloring` | 图着色后按颜色并行 | 否 |
| `row_owner` | `cpu_row_owner` | owner-computes / 行拥有者 | 否 |

## 统一前提

所有算法共享同一套前提，不存在“每个算法各自偷偷换数据结构”的情况：

- 统一网格输入：规则 `Tet4/Hex8` 或 Abaqus `.inp`
- 统一自由度映射：每节点 `3` 个自由度
- 统一 CSR 稀疏结构
- 统一 scatter plan：单元局部矩阵条目预先映射到 CSR `value` 位置
- 统一 kernel：`simplified` 或 `physics_tet4`

这意味着算法对比的重点是：

- 并发冲突如何处理
- 为避免冲突付出了哪些预处理和内存代价
- 最终在哪个规模和线程范围更占优

## 1. 串行基线 `cpu_serial`

源码：

- [serial_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/serial_assembler.cpp)

实现方式：

- 遍历每个单元
- 计算局部刚度矩阵 `ke`
- 根据 scatter plan 把 `ke` 的每个条目直接加到目标 CSR 位置

特点：

- 作为唯一正确性基线和加速比基线
- 没有同步成本，也没有额外缓冲
- 在当前项目中，所有并行算法都要和它比误差

适用性：

- 正确性参考
- 1 线程性能基准
- 不适合大规模多核性能研究本身

## 2. 原子直接累加 `cpu_atomic`

源码：

- [atomic_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/atomic_assembler.cpp)

实现方式：

- OpenMP 并行遍历单元
- 每个线程独立计算局部刚度矩阵
- 对每个局部条目，直接对目标 CSR `values[p]` 做 `#pragma omp atomic update`

关键点：

- 冲突在写回阶段解决，不复制全局矩阵
- 依赖 OpenMP atomic 的共享内存同步语义
- 当前实现中的查址开销已由 scatter plan 预先摊平

优点：

- 结构简单
- 几乎没有算法预处理
- 内存额外开销小

缺点：

- 热点位置会产生原子争用
- 线程数高时可能受缓存一致性和同步成本限制

## 3. 线程私有 CSR `cpu_private_csr`

源码：

- [private_csr_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/private_csr_assembler.cpp)

实现方式：

- 为每个线程分配一整份 `CSR values` 私有数组
- 元素并行时只写本线程私有数组，不发生共享写冲突
- 装配结束后，对所有 `nnz` 位置做一次确定性的逐项 reduction

当前实现中的阶段拆分：

- `prepare_allocate_ms`：线程私有数组分配
- `assembly_zero_ms`：每轮装配前清零
- `assembly_numeric_ms`：单元局部矩阵散射到各线程私有 CSR
- `assembly_reduce_ms`：所有线程私有数组归并回最终 CSR

优点：

- 数值装配阶段没有原子冲突
- 结果确定性强
- 在真实工程网格上当前已经证明是值得保留的候选路线

缺点：

- 额外内存约为 `threads × nnz × sizeof(double)`
- 线程数上去后 reduction 成本和内存压力都会上升

## 4. 线程私有 COO + 排序归并 `cpu_coo_sort_reduce`

源码：

- [coo_sort_reduce_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/coo_sort_reduce_assembler.cpp)

实现方式：

- 每个线程先生成自己的 `(csr_index, value)` 贡献列表
- 所有线程结束后，把私有列表合并成一个大 COO 数组
- 按 `csr_index` 排序
- 对相同 `csr_index` 的条目做 reduce，得到最终 CSR 值

当前实现中的阶段拆分：

- `assembly_generate_ms`：线程私有 COO 贡献生成
- `assembly_merge_ms`：线程私有列表拼接
- `assembly_sort_ms`：全局排序
- `assembly_reduce_ms`：按 CSR 位置串行规约

优点：

- 元素并行阶段不发生共享写冲突
- 形式上最接近“先生成贡献，再统一规约”的研究型路线

缺点：

- 中间态非常大
- 排序成本高
- 当前最终 reduce 仍是串行阶段，因此在真实工程网格上明显偏慢

当前定位：

- 研究对照组
- 不是当前最优主线候选

## 5. 图着色 `cpu_graph_coloring`

源码：

- [graph_coloring_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/graph_coloring_assembler.cpp)

实现方式：

- 先构建“共享节点即相邻”的单元冲突关系
- 使用 greedy first-fit 给单元着色
- 同一颜色组内部的单元互不共享节点，因此可并行装配而无需原子操作
- 颜色组之间顺序执行

当前实现中的阶段拆分：

- `prepare_coloring_ms`：贪心着色和颜色桶构建
- `assembly_numeric_ms`：逐颜色组并行数值装配

优点：

- 避免了原子写
- 逻辑清晰，适合作为 CPU 图着色基线

缺点：

- 颜色预处理本身有成本
- 颜色数和颜色分布会影响负载均衡
- 在当前机器和当前实现上，不一定优于 `atomic` 或 `row_owner`

## 6. 行拥有者 / owner-computes `cpu_row_owner`

源码：

- [row_owner_assembler.cpp](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cpu/row_owner_assembler.cpp)

实现方式：

- 按全局行范围把 CSR 行映射给不同线程 owner
- 预处理阶段把每个单元的局部条目拆成 `(element, local_i, local_j, csr_index)` 任务
- 每个线程只写属于自己 owner 范围的条目，因此不需要 atomic
- 如果一个单元跨多个 owner，会被多个 owner 重复计算局部刚度矩阵

当前实现中的阶段拆分：

- `prepare_owner_partition_ms`：owner 任务划分与排序
- `assembly_numeric_ms`：按 owner 执行数值装配

优点：

- 没有原子冲突
- 在真实工程网格上当前是最强候选之一
- 更接近后续子域/owner-computes 工程路线

缺点：

- 单元可能被多个 owner 重复计算
- 预处理任务列表会带来额外内存

## 当前研究结论

截至当前主线实现与本机验证：

- `row_owner`：真实工程网格上表现最有竞争力，是当前优先保留的主线候选
- `private_csr`：真实工程网格上可跑且扩展性不错，但受内存限制更明显
- `atomic`：实现简单、额外内存低，是可靠的共享内存基线
- `coloring`：仍然重要，但不再默认假设它一定是 CPU 最优
- `coo_sort_reduce`：当前更像研究对照组，而不是最终优选实现

## 参考资料

建议把以下资料与本项目源码一起阅读：

- OpenMP 5.1 `atomic update` 规范：
  [openmp.org/spec-html/5.1/openmpsu105.html](https://www.openmp.org/spec-html/5.1/openmpsu105.html)
- OpenMP 5.1 线程数控制：
  [openmp.org/spec-html/5.1/openmpse59.html](https://www.openmp.org/spec-html/5.1/openmpse59.html)
- OpenMP 5.1 线程绑定：
  [openmp.org/spec-html/5.1/openmpse61.html](https://www.openmp.org/spec-html/5.1/openmpse61.html)
- CMake `FindOpenMP`：
  [cmake.org/cmake/help/latest/module/FindOpenMP.html](https://cmake.org/cmake/help/latest/module/FindOpenMP.html)
- Krysl, 2024, multicore FEM assembly：
  [sciencedirect.com/science/article/pii/S0045782524003323](https://www.sciencedirect.com/science/article/pii/S0045782524003323)
