# CSC3 公共接口与命名契约

本文是 CSC3 对称组装 Demo `0.2.0` 的规范性公共契约。唯一受支持的实现路径是“OpenMP 并行符号组装 + OpenMP atomic 数值组装”；不存在串行生产回退。

## 公共接口清单

### 类型与别名

| 公共名称 | 类型 | 契约 |
|---|---|---|
| `GlobalDofIndex` | `std::int32_t` 别名 | 非负、零基的全局自由度索引，属于紧凑范围 $[0,n)$。 |
| `ElementId` | `std::int32_t` 别名 | 唯一、非负的单元身份编号，不是输入次序。 |
| `Offset` | `std::uint64_t` 别名 | 指向扁平化自有数组的非负零基偏移。 |
| `ElementDofMap` | 自有结构 | 完整的“单元到全局自由度”扁平拓扑输入。 |
| `ElementMatrixBatch` | 自有结构 | 按规范单元次序排列的完整稠密单元矩阵批次。 |
| `Csc3Matrix` | 自有结构 | 零基 CSC3 上三角结构与数值。 |
| `AssemblyPlan` | 自有结构 | 规范化拓扑与数值 scatter 目标。 |
| `SymmetricCscAssembler` | 自有类 | 拥有当前矩阵和计划，并提供两阶段接口。 |

### 公共字段

| 所属类型 | 字段 | 含义 |
|---|---|---|
| `ElementDofMap` | `element_ids` | 每个输入单元分段对应一个非负唯一编号。 |
| `ElementDofMap` | `element_dof_offsets` | 指向 `global_dof_indices` 的零基分段偏移；长度为单元数加一。 |
| `ElementDofMap` | `global_dof_indices` | 按每个单元局部次序扁平存放的零基全局自由度。 |
| `ElementMatrixBatch` | `element_value_offsets` | 指向 `values_row_major` 的零基分段偏移；长度为规范单元数加一。 |
| `ElementMatrixBatch` | `values_row_major` | 每个规范单元一个完整行主序方阵，全部值必须有限。 |
| `Csc3Matrix` | `dimension` | 矩阵行列数 $n$。 |
| `Csc3Matrix` | `column_offsets` | 零基 CSC 列偏移；长度为 $n+1$。 |
| `Csc3Matrix` | `row_indices` | 零基行索引，每列内严格递增。 |
| `Csc3Matrix` | `values` | 与 `row_indices` 一一对应的上三角数值。 |
| `AssemblyPlan` | `element_ids` | 按严格升序排列的规范单元编号。 |
| `AssemblyPlan` | `element_dof_offsets` | 指向计划内 `global_dof_indices` 的零基偏移。 |
| `AssemblyPlan` | `global_dof_indices` | 保留各单元内部局部次序的扁平全局自由度。 |
| `AssemblyPlan` | `element_scatter_offsets` | 指向 `scatter_indices` 的零基分段偏移，每个规范单元一个分段。 |
| `AssemblyPlan` | `scatter_indices` | 指向 `Csc3Matrix::values` 的零基目标偏移。 |

### 函数与方法

| 公共调用 | 契约 |
|---|---|
| `build_symbolic_parallel(element_dof_map, thread_count)` | 校验并复制完整拓扑，按编号升序规范化单元，确定性构造 CSC3 结构与 scatter 数据，成功后替换旧状态。 |
| `assemble_numeric_atomic(element_matrices, thread_count)` | 校验完整规范矩阵批次，清零全部整体数值，再用 atomic 组装该批次。 |
| `matrix()` | 返回 assembler 所有矩阵状态的常量引用。 |
| `assembly_plan()` | 返回 assembler 所有规范计划的常量引用。 |
| `symbolic_thread_count_used()` | 返回最近一次成功符号调用的三个 OpenMP 区域中观察到的最大 team size；成功前为零。 |
| `numeric_thread_count_used()` | 返回最近一次成功数值调用观察到的 OpenMP team size；成功前或新符号构造后为零。 |
| `openmp_enabled()` | 所有受支持构建均返回 `true`；缺少 OpenMP 时配置失败，而不是生成串行版本。 |
| `max_openmp_threads()` | 返回调用线程当前 OpenMP 运行时允许的最大 team size。 |

## 命名规则

- 公共类型与类型别名使用 `PascalCase`。
- 函数、方法、参数、局部变量和公共字段使用 `snake_case`。
- 私有数据成员使用末尾带一个下划线的 `snake_case_`。
- `_id` 表示一个稳定身份编号，`_ids` 表示身份编号集合；不得把身份编号描述成 ordinal。
- `_indices` 表示集合内的零基索引或被索引身份。
- `_offsets` 表示扁平数组中的零基边界或前缀和；通常必须包含末端边界。
- `_count` 表示无量纲的项目数或线程数。
- `_ms` 表示毫秒耗时。
- `_bytes` 表示字节存储量。

新增公共名称必须表达具体语义，禁止单独使用 `n`、`size`、`info`、`help` 等模糊名称。应使用 `dimension`、`thread_count`、`element_dof_map`、`assembly_plan` 等能直接体现含义与单位的名称。

## 零基范围与单位

- 合法 `GlobalDofIndex` 属于 $[0,n)$，其中 $n$ 为矩阵维数；输入中全部不同自由度必须恰好覆盖该紧凑范围。
- 合法 `ElementId` 属于 $[0,2^{31}-1]$，并在一次拓扑中唯一。
- `Offset` 属于 $[0,2^{64}-1]$；用作内存索引前还必须能被宿主容器尺寸类型表示。
- 自由度索引、单元编号、偏移、维数和线程数均无量纲。
- `values` 保留调用方提供的物理单位，例如刚度单位；Demo 不进行单位转换，也不附加单位元数据。
- 后续公共时间和存储字段必须分别使用 `_ms` 与 `_bytes`，不得隐藏单位。

## 拓扑与规范次序

对 $m$ 个输入单元：

1. `element_ids` 长度为 $m$，非空且无重复。
2. `element_dof_offsets` 长度为 $m+1$，首项为零、单调不减，末项等于 `global_dof_indices.size()`。
3. 每个单元至少拥有一个自由度，单元内部不得重复自由度；不同单元共享自由度是合法的。
4. 单元编号和全局自由度均非负；不同的全局自由度必须恰好为 $0,1,\ldots,n-1$。

输入单元可以无序。组装计划按 `ElementId` 升序规范化，同时保持每个单元内部的局部自由度次序。数值批次没有单元编号字段，因此其分段必须严格遵循 `assembly_plan().element_ids`。这样可从类型上排除部分、缺失、重复或未知单元更新。

## CSC3 不变量

成功完成符号构造后，必须同时满足：

- `dimension` 为 $n>0$；
- `column_offsets.size()` 为 $n+1$，`column_offsets[0]` 为零，全部偏移单调不减；
- `column_offsets[n]` 同时等于 `row_indices.size()` 与 `values.size()`；
- 对列 $c$，半开区间
  $[\mathtt{column\_offsets}[c],\mathtt{column\_offsets}[c+1])$
  内行号严格递增且满足 $0\le r\le c<n$；
- 存储结构是全部单元拓扑诱导的全局自由度上三角对的并集，每个已编号自由度都包含对角项；
- 符号阶段的 `values` 全部初始化为零。

对局部维数为 $d_e$ 的规范单元，`element_scatter_offsets` 预留 $d_e(d_e+1)/2$ 个目标。`scatter_indices` 按局部上三角行主序枚举 $(i,j)$，其中 $0\le i\le j<d_e$；每个目标都必须是 `Csc3Matrix::values` 的合法零基位置。

## 稠密局部矩阵契约

每个规范单元 $e$ 的数值分段包含恰好 $d_e^2$ 个有限 `double`，表示完整的 $d_e\times d_e$ 行主序矩阵。对非对角项 $a_{ij}$ 与 $a_{ji}$，仅当绝对和相对门槛同时被超过时拒绝该批次：

$$
|a_{ij}-a_{ji}|>10^{-12}
\quad\text{且}\quad
|a_{ij}-a_{ji}|>
10^{-10}\max(|a_{ij}|,|a_{ji}|).
$$

对 $i\le j$，组装上三角局部值 $a_{ij}$；下三角只用于对称性检查，不对两者求平均。

每次成功数值调用都是一次完整覆盖：先清零完整 CSC3 数值数组，再组装当前批次。OpenMP atomic 保证共享目标无数据竞争，但浮点累加次序不提供逐位确定性。

## 所有权、生命期、异常与线程安全

全部公共数据结构拥有自己的 `std::vector` 存储。符号构造复制并规范化 `ElementDofMap`；数值组装只在调用期间借用 `ElementMatrixBatch`，不保留任何输入指针或引用。

`matrix()` 与 `assembly_plan()` 返回 assembler 所有成员对象的常量引用。成员对象引用绑定到该 assembler，但后续变更调用可以替换其内容，并使从内部向量取得的全部指针、迭代器和元素引用失效。任何访问器返回值都不能比 assembler 活得更久。

公共异常契约：

- `std::invalid_argument`：非正 `thread_count`、非法拓扑或偏移、非法局部维数、非有限值、实质不对称矩阵；
- `std::logic_error`：数值组装早于符号构造，或内部计划不变量被破坏；
- `std::overflow_error`：计数、偏移、维数或分配请求无法由公共或宿主索引类型表示；
- 标准分配异常可以继续向上传播。

同一个 `SymmetricCscAssembler` 实例不支持并发调用，包括修改期间的并发读取。不同实例可以并发运行。正 `thread_count` 只是 OpenMP 请求；运行时可能提供更小 team。若真实数量影响正确性或证据有效性，必须在成功调用后查询记录的 team size；Issue #54 正式样本要求真实值等于请求值。
