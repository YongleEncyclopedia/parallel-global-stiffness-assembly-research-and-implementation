# CSC3 Demo 接口说明

公共声明位于 `include/csc3_demo/assembly_helper.h`。实现分为并行符号组装和 atomic 数值组装两步。

## 数据结构

### `DofCodingInfo`

```cpp
struct DofCodingInfo {
    std::unordered_map<ElementId, std::vector<NodeId>> elems;
    std::unordered_map<NodeId, std::vector<Index>> node_dofs;
};
```

`elems` 保存每个单元的节点顺序，`node_dofs` 保存每个节点对应的全局自由度。节点在单元中的顺序和自由度在节点中的顺序共同决定局部矩阵的行列顺序。

要求：

- 单元编号和节点编号不能为负；
- 每个单元至少有一个节点，同一单元内不能重复节点或自由度；
- `elems` 使用的每个节点都必须出现在 `node_dofs` 中；
- 全局自由度从 0 开始，并连续覆盖 $[0,n)$。

输入 `unordered_map` 的遍历顺序不影响结果。`Symbolic(...)` 会按单元编号升序整理数据。

### `Csc3Matrix`

```cpp
struct Csc3Matrix {
    Index n;
    std::vector<Index> col_ptr;
    std::vector<Index> row_idx;
    std::vector<double> values;
};
```

矩阵只保存上三角。第 $j$ 列的条目位于
`[col_ptr[j], col_ptr[j + 1])`，其中 `row_idx` 严格递增并满足 $0\le i\le j<n$。三个索引数组都从 0 开始。

### `HelpInfo`

```cpp
struct HelpInfo {
    std::vector<ElementId> element_ids;
    std::vector<Index> element_dof_offsets;
    std::vector<Index> element_dofs;
    std::vector<Index> entry_offsets;
    std::vector<Index> scatter;
};
```

`HelpInfo` 把每个局部上三角条目映射到 `Csc3Matrix::values`：

- `element_ids` 按单元编号升序排列；
- `element_dof_offsets` 对 `element_dofs` 分段；
- `entry_offsets` 对 `scatter` 分段；
- `scatter[k]` 是 `values` 中的目标位置。

若单元 $e$ 有 $d_e$ 个自由度，它在 `scatter` 中占用
$d_e(d_e+1)/2$ 个位置，顺序是局部上三角行主序。

### `ElementStiffness`

```cpp
struct ElementStiffness {
    ElementId elem_id;
    const double* values_row_major;
    std::size_t value_count;
};
```

这是单元刚度矩阵的只读视图。调用方持有实际内存，且必须保证指针在 `add(...)` 返回前有效。对于局部维数 $d_e$，`value_count` 必须等于 $d_e^2$。

## 调用顺序

### 1. 符号组装

```cpp
AssemblyHelper helper;
Csc3Matrix csc3;
HelpInfo help_info;
helper.Symbolic(csc3, help_info, dof_coding_info);
```

`Symbolic(...)` 的三个参数依次是输出 CSC3、输出辅助信息和输入自由度编码。函数内部并行完成：

1. 整理单元和自由度；
2. 建立“自由度到单元”的邻接；
3. 按列并行收集、排序和去重行号；
4. 生成 `col_ptr` 与 `row_idx`；
5. 按单元并行生成 `scatter`。

同一份合法输入在不同线程数下应得到相同的 `col_ptr`、`row_idx` 和 `scatter`。函数先在临时对象中完成全部工作，成功后再写回两个输出参数。

### 2. 数值组装

```cpp
helper.zero_values(csc3);

#pragma omp parallel for schedule(static)
for (std::int64_t e = 0; e < element_count; ++e) {
    helper.add(csc3, help_info, element_stiffness[e]);
}
```

`zero_values(...)` 在每轮完整组装前调用一次。`add(...)` 每次处理一个单元，只读取 `HelpInfo` 和单元矩阵，通过 `scatter` 找到整体位置，并对共享位置执行 OpenMP atomic 累加。

不要让 `zero_values(...)`、`Symbolic(...)` 和 `add(...)` 相互并发。完成符号组装后，多个线程可以使用同一个 `AssemblyHelper`、`Csc3Matrix` 和 `HelpInfo`，针对不同单元并发调用 `add(...)`。

## 单元矩阵要求

局部矩阵必须是完整的 $d_e\times d_e$ 行主序数组，所有值有限。对非对角项 $a_{ij}$ 与 $a_{ji}$，只有在以下两个条件同时成立时才判为不对称：

$$
|a_{ij}-a_{ji}|>10^{-12},
$$

$$
|a_{ij}-a_{ji}|>
10^{-10}\max(|a_{ij}|,|a_{ji}|).
$$

组装使用上三角值，下三角只用于对称性检查。

## 异常与所有权

- 非法拓扑、未知单元、错误矩阵长度、非有限值和实质不对称矩阵抛出 `std::invalid_argument`；
- 计数或索引超出 `Index`、`std::size_t` 可表示范围时抛出 `std::overflow_error`；
- `DofCodingInfo`、`Csc3Matrix` 和 `HelpInfo` 拥有各自的容器；
- `ElementStiffness` 不拥有矩阵数据；
- `add(...)` 的输入应在进入 OpenMP 循环前准备好。不要让异常越过 OpenMP 并行区边界。

## 线程数

`Symbolic(...)` 使用当前 OpenMP 运行环境的线程数。可在调用前设置 `OMP_NUM_THREADS`，或用 `omp_set_num_threads(...)`。`symbolic_thread_count_used()` 返回最近一次成功调用实际使用的最大线程数。

本 Demo 要求 OpenMP。CMake 找不到运行时会停止配置，不会把并行接口悄悄改成串行实现。
