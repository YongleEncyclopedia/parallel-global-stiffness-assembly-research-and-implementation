# CPU 后端实现说明

## 阶段拆分

当前 benchmark 明确区分以下阶段：

1. 网格生成或 `.inp` 解析
2. CSR 符号结构构建
3. 单元局部矩阵到 CSR 位置的 scatter plan 预计算
4. 算法预处理
5. 数值组装

这样做的原因是：

- 图着色、COO 排序归并、线程私有 CSR、row-owner 的预处理与额外内存开销完全不同
- 如果不拆开统计，只看一条“总时间”曲线，实验结论会失真

## 算法解释

- `cpu_serial`
  - 唯一正确性基线和加速比基线
- `cpu_atomic`
  - 保留自然单元遍历顺序，依赖 OpenMP atomic 解决写冲突
- `cpu_graph_coloring`
  - 延续早期 CPU 图着色思路，重点考察颜色数与负载分布
- `cpu_private_csr`
  - 用内存换同步，把共享写冲突转成最后的 CSR 归并
- `cpu_coo_sort_reduce`
  - 研究“先生成贡献，再排序规约”的路线是否值得
- `cpu_row_owner`
  - owner-computes 原型，不需要 atomic，但可能重复计算某些单元局部矩阵

更完整的算法实现说明见：

- [cpu_algorithms.md](/Users/macstudio/Documents/Intern_Peking%20University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md)

## WindTurbineHub 的实践建议

对于百万级 `C3D4` 工程网格，建议按以下顺序推进：

1. 先跑 `simplified`，确认 `.inp`、CSR 与 scatter plan 没问题
2. 再跑 `physics_tet4`
3. 内存更敏感的算法要结合 `--max-memory-gb` 做受控实验

## 推荐实验顺序

1. 先用 `examples/tiny_c3d4_with_output_sections.inp` 与 `examples/small_c3d4_gap_labels.inp` 跑正确性回归
2. 先 smoke test 规则 `Tet4`
3. 再放大到规则 `Tet4/Hex8`
4. 最后迁移到 `examples/3d-WindTurbineHub.inp`
