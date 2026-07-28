# 迁移到 CSC3 Demo `0.2.0`

`0.2.0` 有意用“强类型、扁平化、仅并行”契约替换原型接口，不提供兼容别名。调用方必须一次性迁移名称和数据流；旧接口代码在迁移完成前编译失败是预期行为。

## 新旧名称映射

| 已移除的 `0.1.x` 名称 | `0.2.0` 替代 | 必需迁移动作 |
|---|---|---|
| `Index` | `GlobalDofIndex` 或 `Offset` | 零基自由度坐标使用 `GlobalDofIndex`；扁平数组边界与目标位置使用 `Offset`。 |
| `NodeId` | 无公共替代 | 调用 Demo 前，由调用方把节点拓扑解析为全局自由度。 |
| `DofCodingInfo` | `ElementDofMap` | 提供完整、扁平的“单元到全局自由度”映射。 |
| `DofCodingInfo::elems` | `element_ids`、`element_dof_offsets`、`global_dof_indices` | 把每个单元解析后的全局自由度写入一个分段；输入单元次序可以任意。 |
| `DofCodingInfo::node_dofs` | 合并到 `global_dof_indices` | 节点到自由度的解析由调用方负责；公共接口不再拥有节点层。 |
| `Csc3Matrix::n` | `Csc3Matrix::dimension` | 重命名矩阵行列数。 |
| `Csc3Matrix::col_ptr` | `Csc3Matrix::column_offsets` | 使用零基 `Offset`；末端项仍表示存储条目总数。 |
| `Csc3Matrix::row_idx` | `Csc3Matrix::row_indices` | 使用零基 `GlobalDofIndex`。 |
| `HelpInfo` | `AssemblyPlan` | 从明确的计划类型读取规范拓扑与 scatter 数据。 |
| `HelpInfo::element_dofs` | `AssemblyPlan::global_dof_indices` | 改用表达具体语义的全局自由度名称。 |
| `HelpInfo::entry_offsets` | `AssemblyPlan::element_scatter_offsets` | 使用每单元 scatter 分段偏移。 |
| `HelpInfo::scatter` | `AssemblyPlan::scatter_indices` | 使用指向 `Csc3Matrix::values` 的零基 `Offset` 目标。 |
| `AssemblyHelper` | `SymmetricCscAssembler` | 改为拥有状态的两阶段 assembler。 |
| `AssemblyHelper::symbolic` | `build_symbolic_parallel` | 传入 `ElementDofMap` 与显式正 `thread_count`。 |
| `AssemblyHelper::zero_values` | 无单独调用 | 每次成功 `assemble_numeric_atomic` 都会在组装前清零全部值。 |
| `AssemblyHelper::add` | `assemble_numeric_atomic` | 已移除按单元更新；构造一个完整 `ElementMatrixBatch`。 |
| `AssemblyHelper::add_parallel` | `assemble_numeric_atomic` | 把单元编号映射改为按 `assembly_plan().element_ids` 排列的扁平批次。 |
| `AssemblyHelper::help_info` | `assembly_plan` | 返回的常量引用仍由 assembler 拥有。 |
| `ke_row_major` | `ElementMatrixBatch::values_row_major` | 按规范单元次序连接完整、有限、对称的行主序局部矩阵。 |
| `size` | 无公共参数 | 局部维数 $d_e$ 来自符号计划；每个数值分段必须恰好包含 $d_e^2$ 项。 |
| `threads` | `thread_count` | 传入正 OpenMP 线程请求；用对应的 `*_thread_count_used()` 查询实际 team size。 |
| `expand_upper_csc_to_dense` | 无公共替代 | 如有需要，在调用方验证或测试代码中保留稠密展开。 |
| `generate_demo_report` | 无公共替代 | 报告生成已与组装公共接口分离。 |
| Eigen `add` 重载 | 无公共替代 | 调用方把矩阵扁平写入 `values_row_major`；公共边界不暴露 Eigen 类型。 |

## 数据流迁移

旧接口接收节点连接关系与“节点到自由度”映射。新接口从解析完成后的全局自由度开始。对每个输入单元：

1. 把节点解析为该单元有序的全局自由度列表。
2. 把单元编号追加到 `ElementDofMap::element_ids`。
3. 把有序自由度追加到 `global_dof_indices`，再把新的末端长度追加到 `element_dof_offsets`。
4. 用正 `thread_count` 调用 `build_symbolic_parallel(...)`。

assembler 按单元编号升序规范化次序，同时保持每个单元内部自由度次序。随后，数值数据必须遵循 `assembly_plan().element_ids`，不能继续使用原输入次序：

1. 创建首项为零的 `element_value_offsets`。
2. 对每个规范单元，把完整的 $d_e\times d_e$ 行主序对称矩阵追加到 `values_row_major`。
3. 每追加一个矩阵，就把新的末端数值总数追加到 `element_value_offsets`。
4. 对完整批次调用一次 `assemble_numeric_atomic(...)`。

旧的部分 `add(...)` 循环不等价于新契约。每次数值调用都会清除旧值并执行一次完整组装。

## 最小调用点改写

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

新构建强制要求 OpenMP。不存在兼容选项或串行回退；设置 `CSC3_DEMO_REQUIRE_OPENMP=OFF` 会有意触发 CMake 配置错误。
