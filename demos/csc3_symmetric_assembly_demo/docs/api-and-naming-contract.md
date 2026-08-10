# CSC3 公共接口与命名约定

本文说明 CSC3 对称组装 Demo `0.2.0` 的公共类型、输入格式和调用约束。运行路径为 OpenMP 并行符号组装加 OpenMP atomic 数值组装。

## 公共接口

### 类型

| 名称 | 类型 | 含义 |
|---|---|---|
| `GlobalDofIndex` | `std::int32_t` | 非负、零基的全局自由度索引，范围为 $[0,n)$。 |
| `ElementId` | `std::int32_t` | 唯一且非负的单元编号，与输入次序无关。 |
| `Offset` | `std::uint64_t` | 扁平数组中的零基偏移。 |
| `ElementDofMap` | 结构体 | 单元到全局自由度的扁平映射。 |
| `ElementMatrixBatch` | 结构体 | 按计划次序排列的稠密单元矩阵。 |
| `Csc3Matrix` | 结构体 | CSC3 上三角结构及其数值。 |
| `AssemblyPlan` | 结构体 | 规范化拓扑和数值 scatter 目标。 |
| `SymmetricCscAssembler` | 类 | 保存当前矩阵与组装计划，提供符号和数值接口。 |

### 字段

| 所属类型 | 字段 | 含义 |
|---|---|---|
| `ElementDofMap` | `element_ids` | 每个输入分段对应的单元编号。 |
| `ElementDofMap` | `element_dof_offsets` | `global_dof_indices` 的分段偏移，长度为单元数加一。 |
| `ElementDofMap` | `global_dof_indices` | 按单元局部次序存放的全局自由度。 |
| `ElementMatrixBatch` | `element_value_offsets` | `values_row_major` 的分段偏移，长度为单元数加一。 |
| `ElementMatrixBatch` | `values_row_major` | 每个单元的完整行主序矩阵。 |
| `Csc3Matrix` | `dimension` | 矩阵行列数 $n$。 |
| `Csc3Matrix` | `column_offsets` | CSC 列偏移，长度为 $n+1$。 |
| `Csc3Matrix` | `row_indices` | 每列内严格递增的零基行索引。 |
| `Csc3Matrix` | `values` | 与 `row_indices` 对应的上三角数值。 |
| `AssemblyPlan` | `element_ids` | 按升序排列的单元编号。 |
| `AssemblyPlan` | `element_dof_offsets` | `global_dof_indices` 的分段偏移。 |
| `AssemblyPlan` | `global_dof_indices` | 保留单元内部次序的全局自由度。 |
| `AssemblyPlan` | `element_scatter_offsets` | `scatter_indices` 的分段偏移。 |
| `AssemblyPlan` | `scatter_indices` | 指向 `Csc3Matrix::values` 的目标偏移。 |

### 方法

| 调用 | 作用 |
|---|---|
| `build_symbolic_parallel(element_dof_map, thread_count)` | 检查并复制拓扑，按单元编号排序，生成 CSC3 结构和 scatter 计划。成功后替换旧状态。 |
| `assemble_numeric_atomic(element_matrices, thread_count)` | 检查矩阵批次，清零整体数值，再以 atomic 方式组装。 |
| `matrix()` | 返回当前矩阵的常量引用。 |
| `assembly_plan()` | 返回当前组装计划的常量引用。 |
| `symbolic_thread_count_used()` | 返回最近一次符号组装观察到的最大 OpenMP team size；调用前为零。 |
| `numeric_thread_count_used()` | 返回最近一次数值组装观察到的 OpenMP team size；调用前为零。 |
| `openmp_enabled()` | 受支持的构建均返回 `true`。 |
| `max_openmp_threads()` | 返回当前 OpenMP 运行时允许的最大 team size。 |

## 命名

- 类型和类型别名使用 `PascalCase`；
- 函数、参数、局部变量和公共字段使用 `snake_case`；
- 私有数据成员使用 `snake_case_`；
- `_id`/`_ids` 表示身份编号，`_indices` 表示零基索引；
- `_offsets` 表示扁平数组边界，通常包含末端边界；
- `_count` 表示数量，`_ms` 表示毫秒，`_bytes` 表示字节。

公共名称应直接说明用途，不单独使用 `n`、`size`、`info` 或 `help` 等含义不清的名称。

## 索引和单位

- `GlobalDofIndex` 位于 $[0,n)$，输入中的不同自由度应覆盖这一连续范围；
- `ElementId` 位于 $[0,2^{31}-1]$，同一拓扑内不得重复；
- `Offset` 位于 $[0,2^{64}-1]$，转成容器索引前还要检查宿主类型能否表示；
- 自由度、单元编号、偏移、维数和线程数均无量纲；
- `values` 沿用调用方的物理单位，Demo 不做单位换算。

## 拓扑次序

设输入包含 $m$ 个单元：

1. `element_ids` 长度为 $m$，非空且不重复；
2. `element_dof_offsets` 长度为 $m+1$，首项为零，单调不减，末项等于 `global_dof_indices.size()`；
3. 每个单元至少有一个自由度，单元内部不得重复；
4. 单元编号和自由度均为非负值。

输入单元可以无序。符号组装按 `ElementId` 升序生成计划，同时保留每个单元内部的自由度次序。数值批次没有单元编号字段，因此必须按照 `assembly_plan().element_ids` 排列。

## CSC3 结构

符号组装成功后满足：

- `dimension` 为 $n>0$；
- `column_offsets.size()` 为 $n+1$，首项为零且单调不减；
- `column_offsets[n]` 等于 `row_indices.size()` 和 `values.size()`；
- 第 $c$ 列位于 $[\mathtt{column\_offsets}[c],\mathtt{column\_offsets}[c+1])$，行号严格递增并满足 $0\le r\le c<n$；
- 所有已编号自由度都包含对角项；
- `values` 初始为零。

局部维数为 $d_e$ 的单元对应 $d_e(d_e+1)/2$ 个 scatter 目标，按局部上三角行主序枚举 $(i,j)$，其中 $0\le i\le j<d_e$。

## 局部矩阵

每个单元分段包含 $d_e^2$ 个有限 `double`，表示一个 $d_e\times d_e$ 行主序矩阵。非对角项 $a_{ij}$ 与 $a_{ji}$ 同时满足下式时，输入被判为不对称：

$$
|a_{ij}-a_{ji}|>10^{-12}
\quad\text{且}\quad
|a_{ij}-a_{ji}|>
10^{-10}\max(|a_{ij}|,|a_{ji}|).
$$

组装使用 $i\le j$ 的上三角值，下三角仅用于对称性检查。每次数值调用都先清零 `values`，因此重复调用表示覆盖，不是增量累加。

## 所有权、异常和并发

公共输入结构保存自己的 `std::vector`。符号组装复制 `ElementDofMap`；数值组装只在调用期间读取 `ElementMatrixBatch`。

`matrix()` 和 `assembly_plan()` 返回 assembler 成员的常量引用。后续符号或数值调用可能替换内部向量，使已有指针、迭代器和元素引用失效；返回引用也不得超过 assembler 的生命周期。

- `std::invalid_argument`：线程数非正、拓扑或偏移错误、局部尺寸错误、出现非有限值或矩阵不对称；
- `std::logic_error`：尚未完成符号组装，或内部计划损坏；
- `std::overflow_error`：计数、偏移或分配大小无法表示；
- 内存分配异常按标准库行为向上传递。

同一个 `SymmetricCscAssembler` 不能被多个调用线程同时使用；不同实例可以并发运行。`thread_count` 是请求值，实际值应在调用后通过 `*_thread_count_used()` 查询，性能测试要求两者相等。
