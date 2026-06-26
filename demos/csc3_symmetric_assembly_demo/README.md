# CSC3 Symmetric Assembly Demo

这个目录是一个独立 C++17 demo，用于展示 mentor 草图里的两阶段整体刚度矩阵组装：

1. `symbolic(DofCodingInfo)` 根据单元拓扑和节点全局自由度编号生成上三角 CSC3 结构。
2. `add(...)` / `add_parallel(...)` 将显式给定的单元刚度矩阵累加到 CSC3 `values`。

demo 不依赖当前 PGSA 主线，也不依赖实习单位求解器源码。它只保留可迁移的 helper 接口和数据流。

## Matrix Format

CSC3 被定义为 0-based 三数组：

- `col_ptr`: 每一列在 `row_idx` / `values` 中的起止位置，长度为 `n + 1`
- `row_idx`: 非零元行号
- `values`: 非零元数值

本 demo 只存对称矩阵上三角，因此所有存储项满足 `row <= col`。

## 输入契约

- `elems[element_id] = {node0, node1, ...}` 表示单元节点拓扑和局部节点顺序。
- `node_dofs[node_id] = {global_dof0, ...}` 表示节点自由度到全局自由度编号的映射。
- global DOF 必须在 `node_dofs` 中全局唯一，并且连续紧凑编号为 `0..n-1`。
- 每个单元拼接后的 local-to-global DOF 列表不得包含重复 DOF。
- `add_parallel(...)` 是完整装配接口：传入的 `element_matrices` 必须覆盖 `symbolic(...)` 阶段的所有 element，缺少 element 或传入未知 element 都会抛错，不做静默子集装配。

## Build and Test

单配置生成器，例如 Ninja、Unix Makefiles：

```bash
cmake -S . -B build -DCSC3_DEMO_ENABLE_OPENMP=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
./build/csc3_demo_app --report report/generated_demo_report.md
```

多配置生成器，例如 Visual Studio、Xcode：

```bash
cmake -S . -B build -DCSC3_DEMO_ENABLE_OPENMP=ON
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release
./build/Release/csc3_demo_app --report report/generated_demo_report.md
```

Windows 多配置构建后的可执行文件通常是 `build/Release/csc3_demo_app.exe`。macOS / Linux 单配置构建后的可执行文件通常是 `./build/csc3_demo_app`。

如果机器没有 CMake，也可以用 C++ 编译器做最小 smoke：

```bash
c++ -std=c++17 -Wall -Wextra -Wpedantic -Iinclude \
  src/assembly_helper.cpp tests/assembly_helper_tests.cpp \
  -o /tmp/csc3_demo_tests
/tmp/csc3_demo_tests
```

OpenMP 是可选能力。没有 OpenMP 时 `add_parallel(...)` 会退化为串行累加，接口和结果保持一致。

## Files

- `include/csc3_demo/assembly_helper.h`: public API
- `src/assembly_helper.cpp`: symbolic assembly、numeric assembly、report generation
- `src/main.cpp`: report CLI
- `tests/assembly_helper_tests.cpp`: correctness and validation tests
- `report/demo_report.md`: 随包提交的中文测试报告
