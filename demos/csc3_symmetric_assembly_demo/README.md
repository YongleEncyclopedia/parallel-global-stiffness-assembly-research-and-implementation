# CSC3 对称稀疏组装 Demo

> **仅供内部评估。** 分发策略仍由 [Issue #37](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/37) 跟踪。

这是一个独立的 C++17 源码 Demo，用 OpenMP 完成对称矩阵上三角的 CSC3 符号组装和原子数值组装。公共接口版本为 `0.2.0`；没有串行回退，关闭 `CSC3_DEMO_REQUIRE_OPENMP` 会在 CMake 配置阶段直接失败。

## 接收方快速入口

以下路径均相对于仓库根目录；本节给出的命令也在仓库根目录执行。

| 内容 | 路径 |
|---|---|
| Demo 源码目录 | `demos/csc3_symmetric_assembly_demo/` |
| 公共接口与完整契约注释 | `demos/csc3_symmetric_assembly_demo/include/csc3_demo/assembly_helper.h` |
| 完整并行实现 | `demos/csc3_symmetric_assembly_demo/src/assembly_helper.cpp` |
| WindHub benchmark | `demos/csc3_symmetric_assembly_demo/tools/src/benchmark.cpp` |
| 独立串行参考实现 | `demos/csc3_symmetric_assembly_demo/tools/src/validation.cpp` |
| C++ 测试 | `demos/csc3_symmetric_assembly_demo/tests/` |
| Windows 独立进程实验 runner | `demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py` |
| Windows 中文报告生成器 | `demos/csc3_symmetric_assembly_demo/scripts/generate_windows_delivery_report.py` |
| Windows 交付 ZIP 生成与校验 | `demos/csc3_symmetric_assembly_demo/scripts/create_windows_delivery.py` |

建议使用仓库根目录下的 `build/issue-54-msvc` 与 `build/issue-54-mingw` 作为构建目录。生成证据进入 `demos/csc3_symmetric_assembly_demo/results/`，报告进入 `demos/csc3_symmetric_assembly_demo/reports/`，最终 ZIP 进入显式指定的交付目录；这些输出不写入公共头文件或实现目录。

最小调用顺序如下：

```cpp
#include <csc3_demo/assembly_helper.h>

csc3_demo::ElementDofMap topology = /* 单元编号、偏移和全局自由度 */;
csc3_demo::ElementMatrixBatch element_matrices = /* 规范单元顺序的稠密矩阵 */;

csc3_demo::SymmetricCscAssembler assembler;
assembler.build_symbolic_parallel(topology, thread_count);
assembler.assemble_numeric_atomic(element_matrices, thread_count);

const csc3_demo::Csc3Matrix& K = assembler.matrix();
```

## 支持的算法路径

- `build_symbolic_parallel(...)` 校验并规范化拓扑，确定性地生成 CSC3 结构和 scatter 计划；同一合法输入在不同 OpenMP 线程数下得到逐项一致的结构与计划。
- `assemble_numeric_atomic(...)` 接收全部单元的完整稠密矩阵批次，用 OpenMP atomic 无数据竞争地累加到 CSC3 `values`。
- 测试和 benchmark 中的串行实现只作为独立正确性参考与性能基线，不是生产回退。即使 `thread_count == 1`，仍执行受支持的 OpenMP 路径。

浮点加法不满足结合律，不同线程到达顺序可能造成舍入级差异。因此数值验收使用相对 Frobenius 误差 $e_F$ 与最大绝对误差，而不承诺跨线程数逐位一致。

## 矩阵与输入契约

### CSC3 上三角

`Csc3Matrix` 只保存满足 $0 \le r \le c < n$ 的上三角条目，全部数组均采用零基索引：

- `column_offsets` 长度为 $n+1$；第 $c$ 列位于半开区间 `[column_offsets[c], column_offsets[c + 1])`。
- 每列的 `row_indices` 严格递增。
- `values` 与 `row_indices` 一一对应，物理单位由调用方决定；Demo 不转换单位。

最后一个列偏移同时等于 `row_indices.size()` 与 `values.size()`。成功完成符号组装后，全部 `values` 初始化为零。

### 符号输入

`ElementDofMap` 表示完整的“单元到整体自由度”拓扑：

- `element_ids` 非空，每个编号唯一且非负。
- `element_dof_offsets` 长度为单元数加一，首项为零、单调不减，末项等于 `global_dof_indices.size()`。
- 每个单元分段非空，单元内部不得重复全局自由度；不同单元可以共享自由度。
- 全局自由度非负，全部不同编号必须恰好形成紧凑范围 $[0,n)$。

输入单元次序可以任意。符号阶段按 `ElementId` 升序规范化单元次序，同时保持每个单元内部的局部自由度次序。返回的 `AssemblyPlan` 采用同一规范次序；每个 scatter 分段按局部上三角行主序枚举。

### 数值输入与覆盖语义

`ElementMatrixBatch` 必须按 `assembly_plan().element_ids` 的规范次序，为每个单元提供一个完整稠密矩阵。若单元 $e$ 的局部维数为 $d_e$，其分段必须包含恰好 $d_e^2$ 个有限 `double`，并按行主序存放。

每个局部矩阵必须在公共头文件记录的绝对/相对组合容差内对称。上三角值进入组装，下三角只用于对称性校验；不支持部分批次或按单元增量更新。

每次成功的 `assemble_numeric_atomic(...)` 都先清零完整 CSC3 `values`，再组装当前批次。因此重复调用是覆盖，而不是累加到上一次结果。

### 所有权、异常与线程安全

- 输入结构拥有各自的 `std::vector`。assembler 复制并规范化拓扑，只在调用期间借用数值批次，不保留输入引用。
- `matrix()` 与 `assembly_plan()` 返回 assembler 所有成员的常量引用。后续变更调用可能替换其向量内容，使旧指针、迭代器和向量元素引用失效；任何返回引用都不能比 assembler 活得更久。
- 非法拓扑、批次布局、非有限值、实质不对称矩阵或非正线程数抛出 `std::invalid_argument`。
- 未完成符号阶段就执行数值阶段，或内部计划损坏，抛出 `std::logic_error`；尺寸与偏移不可表示时抛出 `std::overflow_error`；标准分配异常可继续向上传播。
- 同一个 `SymmetricCscAssembler` 实例不支持并发调用，也不支持一边修改一边读取。不同实例可以并发使用。
- `thread_count` 是对 OpenMP 运行时的请求。通过 `symbolic_thread_count_used()` 与 `numeric_thread_count_used()` 读取真实观察到的 team size；正式性能样本要求它与请求值完全相等。

规范性细节见[接口与命名契约](docs/api-and-naming-contract.md)。旧调用方必须按 [`0.2.0` 迁移指南](MIGRATION.md) 一次性迁移；本版本不提供兼容别名。

## Windows 构建与验证

### 前置条件

- 64 位 Windows；
- CMake `3.21` 或更高版本；
- Ninja；
- Visual Studio 2022 的“使用 C++ 的桌面开发”工作负载，或 MinGW-w64 `g++`；
- 对应编译器可用的 OpenMP C++ 运行时；
- C++ 构建只需 C++17 工具链；完整 Python 验收还需 Python `3.10` 或更高版本与 `requirements-test.txt`。

所有平台都要求 CMake `3.21` 或更高版本；证据与 JUnit 工作流同样要求 CMake `3.21` 或更高版本。开启 `CSC3_DEMO_BUILD_CPP_TESTS` 后，C++ 测试的权威名称与次序记录在 `tests/ctest/expected-cpp-tests.txt`。

Ninja 是 CMake 的构建系统生成器（generator），不是编译器。MSVC 流程由 Ninja 调用 `cl.exe`，MinGW 流程由 Ninja 调用 `g++.exe`。两种流程必须使用不同构建目录，避免编译器缓存互相污染。

先安装 Python 验收依赖：

```powershell
python -m pip install -r demos/csc3_symmetric_assembly_demo/requirements-test.txt
```

### MSVC + Ninja

在 Visual Studio 2022 x64 本机工具命令提示符中确认 `cl`、`cmake` 与 `ninja` 均可找到，然后执行：

```powershell
cmake -S demos/csc3_symmetric_assembly_demo -B build/issue-54-msvc -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DBUILD_TESTING=ON `
  -DCSC3_DEMO_REQUIRE_OPENMP=ON `
  -DCSC3_DEMO_WARNINGS_AS_ERRORS=ON `
  -DCSC3_DEMO_BUILD_CPP_TESTS=ON `
  -DCSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON
cmake --build build/issue-54-msvc --parallel
ctest --test-dir build/issue-54-msvc --output-on-failure --no-tests=error
```

独立 consumer 不依赖主构建树：

```powershell
cmake -S demos/csc3_symmetric_assembly_demo/tests/external_consumer `
  -B build/issue-54-msvc-consumer -G Ninja `
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/issue-54-msvc-consumer --parallel
ctest --test-dir build/issue-54-msvc-consumer --output-on-failure --no-tests=error
```

MSVC 构建会把 `/utf-8` 作为 `csc3_demo` 的公共使用要求传播给 consumer，确保中文公共头文件在默认中文 Windows 代码页下仍可编译。

### MinGW-w64 + Ninja

先确保当前终端中的 `g++`、`cmake` 与 `ninja` 来自同一套 64 位 MinGW 环境，再执行：

```powershell
cmake -S demos/csc3_symmetric_assembly_demo -B build/issue-54-mingw -G Ninja `
  -DCMAKE_CXX_COMPILER=g++ `
  -DCMAKE_BUILD_TYPE=Release `
  -DBUILD_TESTING=ON `
  -DCSC3_DEMO_REQUIRE_OPENMP=ON `
  -DCSC3_DEMO_WARNINGS_AS_ERRORS=ON `
  -DCSC3_DEMO_BUILD_CPP_TESTS=ON `
  -DCSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON
cmake --build build/issue-54-mingw --parallel
ctest --test-dir build/issue-54-mingw --output-on-failure --no-tests=error
```

独立 consumer：

```powershell
cmake -S demos/csc3_symmetric_assembly_demo/tests/external_consumer `
  -B build/issue-54-mingw-consumer -G Ninja `
  -DCMAKE_CXX_COMPILER=g++ `
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/issue-54-mingw-consumer --parallel
ctest --test-dir build/issue-54-mingw-consumer --output-on-failure --no-tests=error
```

### OpenMP 强制失败口径

该 Demo 没有静默串行路径。以下任一情况都必须视为配置失败：

- `CSC3_DEMO_REQUIRE_OPENMP=OFF`；
- CMake 无法找到 `OpenMP::OpenMP_CXX`；
- 编译器与 OpenMP 运行时来自不兼容的工具链。

## Windows 全线程独立进程实验

Issue #54 的正式实验必须扫描 Windows 逻辑处理器总数 $P_{\max}$，并固定执行 $W=2$、$R=7$。每个 warmup/measured 样本启动一个新 `csc3_demo_benchmark.exe` 子进程；样本之间不得并发，正式轮次按升序、降序交替。

本交付主机的 $P_{\max}=16$，示例命令如下：

```powershell
python demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py `
  --repository-root . `
  --benchmark-executable build/issue-54-msvc/bin/csc3_demo_benchmark.exe `
  --input examples/3d-WindTurbineHub.inp `
  --out-dir demos/csc3_symmetric_assembly_demo/results/2026-07-25-windows-x64-issue-54 `
  --maximum-threads 16 --warmup 2 --repeat 7 `
  --compiler "MSVC 19.44.35227" `
  --cmake "4.3.3" `
  --ninja "1.13.2" `
  --openmp-runtime "vcomp140.dll 14.51.36247.0"
```

runner 在开始前要求已跟踪工作树干净，并校验 WindHub Git LFS 实体大小与 SHA-256。每个子进程记录 PID、请求/实际线程数、样本类型、轮次、开始/结束时间、退出码、串行与并行分阶段时间、正确性状态和原始输出路径。峰值内存直接从存活进程句柄的 `GetProcessMemoryInfo().PeakWorkingSetSize` 取得；`estimated_persistent_bytes` 另列为向量容量估计，不能当作峰值内存。

任一样本重叠、缺失、重复、失败、team size 不符或 $e_F>10^{-8}$，整次实验立即判为 `FAIL`。

## 作为子目录接入

本任务提供构建树 target，不提供可安装 CMake package。调用方加入源码目录并链接公共别名：

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(my_solver PRIVATE csc3_demo::csc3_demo)
```

作为子项目时，内部 C++ 测试与 Python 验收默认关闭，不会修改父项目的 `BUILD_TESTING`。顶层 `BUILD_TESTING=ON` 会默认启用 C++ 测试；Python 验收仍需显式设置 `CSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON`。

一个包含规范单元重排的完整最小示例：

```cpp
#include <csc3_demo/assembly_helper.h>

int main() {
    const csc3_demo::ElementDofMap topology{
        {20, 10},
        {0, 2, 4},
        {1, 2, 0, 1},
    };
    const csc3_demo::ElementMatrixBatch element_matrices{
        {0, 4, 8},
        {
            2.0, -1.0, -1.0, 2.0,
            3.0, -2.0, -2.0, 3.0,
        },
    };

    csc3_demo::SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(topology, 4);
    assembler.assemble_numeric_atomic(element_matrices, 4);
    return assembler.matrix().dimension == 3 ? 0 : 1;
}
```

## 证据与交付状态

CTest 覆盖确定性符号结构、atomic 高争用数值累加、输入/异常契约、独立串行正确性比较和公共头文件 consumer。CI 时长只用于运行状态反馈，不能作为正式性能结论。

Windows 正式交付证据由 Issue #54 的独立进程 runner、中文报告生成器和交付 ZIP 生成器共同产生。最终外层中文 ZIP 包含：

- 独立源码 ZIP；
- 中文 README 与严格八章测试报告；
- 原始性能 CSV、汇总 JSON、运行 manifest 和逐样本原始输出；
- MSVC、MinGW、CTest、consumer 与 clean-room 日志；
- 输入与交付文件 SHA-256；
- “仅供内部评估”说明。

源码 ZIP 明确排除 WindHub Git LFS 大文件、构建目录、可执行文件、缓存、宿主绝对路径及无关资产。最终包可用以下命令独立核验：

```powershell
python demos/csc3_symmetric_assembly_demo/scripts/create_windows_delivery.py verify `
  --package <中文交付ZIP>
```

在 Issue #37 解决分发策略前，整个源码与交付包均保持 **仅供内部评估**。

### 与既有受控验收流程的关系

Issue #54 的 Windows 交付不替代已有 Linux Intel 受控验收。旧流程的长期协议仍保存在：

- `packaging/README.md`；
- `packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md`；
- `packaging/ACCEPTANCE_CHECKLIST.zh-CN.md`；
- `packaging/ACCEPTANCE_RECORD.schema.json`；
- `packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md`。

该流程的强制交接顺序是 `draft`、人工决策、`render`、`validate`、`finalize`。`prepare_acceptance_materials.py draft` 冻结 `acceptance-machine-facts.json` 并创建 `acceptance-decision.json`；人工只编辑决策文件。之后的 `render` 生成确定性渲染产物（deterministic renderer outputs），再由校验与最终化步骤绑定 `MANIFEST.sha256`。自动化候选不能冒充人工验收结论。

对外状态字段仍写作 `INTERNAL EVALUATION ONLY`，直到 Issue #37 明确许可证与分发边界。
