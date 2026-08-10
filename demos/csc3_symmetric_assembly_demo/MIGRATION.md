# 迁移到 CSC3 Demo `0.2.0`

`0.2.0` 删除了 `0.1.x` 的兼容名称，调用方需要同时更新类型、字段和数据组织方式。

## 名称对应关系

| `0.1.x` 名称 | `0.2.0` 名称 | 修改内容 |
|---|---|---|
| `Index` | `GlobalDofIndex` 或 `Offset` | 自由度使用 `GlobalDofIndex`，数组边界和目标位置使用 `Offset`。 |
| `NodeId` | 无 | 调用 Demo 前把节点拓扑转换为全局自由度。 |
| `DofCodingInfo` | `ElementDofMap` | 提供扁平的单元—自由度映射。 |
| `DofCodingInfo::elems` | `element_ids`、`element_dof_offsets`、`global_dof_indices` | 每个单元对应一个自由度分段。 |
| `DofCodingInfo::node_dofs` | `global_dof_indices` | 节点到自由度的转换由调用方完成。 |
| `Csc3Matrix::n` | `dimension` | 矩阵行列数。 |
| `Csc3Matrix::col_ptr` | `column_offsets` | 零基列偏移。 |
| `Csc3Matrix::row_idx` | `row_indices` | 零基行索引。 |
| `HelpInfo` | `AssemblyPlan` | 保存规范化拓扑和 scatter 目标。 |
| `HelpInfo::element_dofs` | `global_dof_indices` | 改用全局自由度名称。 |
| `HelpInfo::entry_offsets` | `element_scatter_offsets` | 每个单元的 scatter 分段偏移。 |
| `HelpInfo::scatter` | `scatter_indices` | 指向 `Csc3Matrix::values` 的目标位置。 |
| `AssemblyHelper` | `SymmetricCscAssembler` | 两阶段组装对象。 |
| `AssemblyHelper::symbolic` | `build_symbolic_parallel` | 增加显式的正 `thread_count`。 |
| `AssemblyHelper::zero_values` | 无 | 数值组装会自行清零。 |
| `AssemblyHelper::add` | `assemble_numeric_atomic` | 改为一次提交完整矩阵批次。 |
| `AssemblyHelper::add_parallel` | `assemble_numeric_atomic` | 数值分段按 `assembly_plan().element_ids` 排列。 |
| `AssemblyHelper::help_info` | `assembly_plan` | 返回值仍由 assembler 持有。 |
| `ke_row_major` | `ElementMatrixBatch::values_row_major` | 按行主序连接各单元的稠密矩阵。 |
| `size` | 无 | 局部维数 $d_e$ 取自符号计划，每段包含 $d_e^2$ 项。 |
| `threads` | `thread_count` | 实际线程数用 `*_thread_count_used()` 查询。 |
| `expand_upper_csc_to_dense` | 无 | 如有需要，在调用方测试代码中实现。 |
| `generate_demo_report` | 无 | 报告生成不属于组装接口。 |
| Eigen `add` 重载 | 无 | 先把矩阵写入 `values_row_major`，公共接口不依赖 Eigen。 |

## 数据转换

旧接口从节点连接关系开始，新接口接收已经编号的全局自由度。构造 `ElementDofMap` 时：

1. 将每个单元的节点转换为有序全局自由度；
2. 把单元编号写入 `element_ids`；
3. 把自由度追加到 `global_dof_indices`，并更新 `element_dof_offsets`；
4. 调用 `build_symbolic_parallel()`。

符号阶段会按单元编号排序。随后按 `assembly_plan().element_ids` 的次序组织 `ElementMatrixBatch`：

1. `element_value_offsets` 的第一项设为零；
2. 依次追加每个 $d_e\times d_e$ 行主序矩阵；
3. 每追加一个矩阵，就记录新的末端偏移；
4. 对整个批次调用一次 `assemble_numeric_atomic()`。

旧版逐单元 `add()` 循环不能直接替换为多次 `assemble_numeric_atomic()`，因为每次数值调用都会清零整体矩阵。

## 调用点示例

迁移前：

```cpp
csc3_demo::AssemblyHelper helper;
helper.symbolic(info);
helper.add_parallel(element_matrices, threads);
const auto& matrix = helper.matrix();
```

迁移后：

```cpp
csc3_demo::SymmetricCscAssembler assembler;
assembler.build_symbolic_parallel(element_dof_map, thread_count);
assembler.assemble_numeric_atomic(element_matrix_batch, thread_count);
const csc3_demo::Csc3Matrix& matrix = assembler.matrix();
```

构建选项见 [README](README.md)。`0.2.0` 强制使用 OpenMP，不提供串行回退。
