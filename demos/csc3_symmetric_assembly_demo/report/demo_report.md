# CSC3 对称刚度矩阵组装 Demo 测试报告

## 算法介绍

本 demo 将整体刚度矩阵组装拆成两个阶段：符号组装先根据 `DofCodingInfo` 生成上三角 CSC3 稀疏结构和 `HelpInfo::scatter` 写入地址；数值组装对 symbolic 阶段所有元素的单刚完整并行装配，把显式给定的单元刚度矩阵通过 atomic add 累加到 `values` 数组。

CSC3 采用 0-based 三数组：`col_ptr` 记录每列起止位置，`row_idx` 记录行号，`values` 记录数值。本 demo 只存上三角，因此所有结构项满足 `row <= col`。

## 输入格式

- `elems[element_id] = {node0, node1, ...}` 表示单元节点拓扑和局部节点顺序。
- `node_dofs[node_id] = {global_dof0, ...}` 表示节点自由度到全局自由度编号的映射。
- 全局自由度编号要求全局唯一且连续紧凑，即 `0..n-1`。
- `add_parallel()` 要求提供 symbolic 阶段所有元素的单刚；缺失单刚、未知 element id、NaN/Inf 单刚和非对称单刚都会被拒绝。

## 测试案例：二单元一维链

- 单元 10 连接节点 0-1，单刚为 `[[2, -1], [-1, 2]]`。
- 单元 20 连接节点 1-2，单刚为 `[[3, -2], [-2, 3]]`。
- OpenMP atomic enabled: yes

输出 CSC3 数组：

```text
n       = 3
col_ptr = [0, 1, 3, 5]
row_idx = [0, 0, 1, 1, 2]
values  = [2, -1, 5, -2, 3]
```

验证结论：该结果对应完整对称矩阵 `[[2, -1, 0], [-1, 5, -2], [0, -2, 3]]`，与手算整体刚度矩阵一致。

## 测试覆盖

- `Chain1DUpperCsc3`：验证上三角 CSC3 的 `col_ptr / row_idx / values` 与手算结果一致。
- `Triangle2DVariableDofs`：验证每节点可变 DOF 的 Lagrange 单元输入，并将上三角 CSC3 展开为完整 dense 矩阵核对。
- `SharedElementsParallelAtomic`：验证串行 `add()` 与 OpenMP atomic `add_parallel()` 的结构和值一致。
- `ScatterInvariant`：验证每个局部上三角 entry 的 scatter 下标都指向正确 CSC3 结构项。
- `LocalDofOrderUsesLocalUpperEntry` / `UnorderedVariableDofsDenseOracle`：验证局部 DOF 顺序不是全局升序时仍按局部上三角单刚读取数值。
- `HighContentionParallelAtomic`：验证 1000 个共享 DOF 单元在高冲突 atomic 写入下与串行结果一致。
- `RandomDeterministicOracle`：使用固定 seed 小规模随机网格比较 CSC3 展开结果和直接 dense assembly。
- `ValidationFailures`：验证缺失节点、全局重复 DOF、DOF 编号不连续、单元内重复 DOF、单刚尺寸错误、NaN/Inf 单刚、缺失单刚和单刚非对称都会被拒绝。
