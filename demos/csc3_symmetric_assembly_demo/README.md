# CSC3 对称稀疏组装 Demo

> 仅供研究院内部技术评估（`INTERNAL EVALUATION ONLY`）。

本 Demo 使用 C++17 和 OpenMP 完成对称矩阵上三角的 CSC3 符号组装与 atomic 数值组装，公共接口版本为 `0.2.0`。OpenMP 是必需依赖，配置阶段找不到 OpenMP 时会直接报错。

## 目录说明

以下路径均相对于仓库根目录，后文命令也从仓库根目录运行。

| 内容 | 路径 |
|---|---|
| Demo 源码 | `demos/csc3_symmetric_assembly_demo/` |
| 公共接口 | `demos/csc3_symmetric_assembly_demo/include/csc3_demo/assembly_helper.h` |
| 并行实现 | `demos/csc3_symmetric_assembly_demo/src/assembly_helper.cpp` |
| 工程网格 benchmark | `demos/csc3_symmetric_assembly_demo/tools/src/benchmark.cpp` |
| 串行参考实现 | `demos/csc3_symmetric_assembly_demo/tools/src/validation.cpp` |
| C++ 测试 | `demos/csc3_symmetric_assembly_demo/tests/` |
| Windows 实验脚本 | `demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py` |
| Windows 报告脚本 | `demos/csc3_symmetric_assembly_demo/scripts/generate_windows_delivery_report.py` |
| Windows 打包脚本 | `demos/csc3_symmetric_assembly_demo/scripts/create_windows_delivery.py` |

Windows 下建议把 MSVC 和 MinGW 的构建目录分别设为 `build/issue-54-msvc` 与 `build/issue-54-mingw`，不要共用 CMake 缓存。测试数据写入 `results/`，报告写入 `reports/`。

## 调用方式

```cpp
#include <csc3_demo/assembly_helper.h>

csc3_demo::ElementDofMap topology = /* 单元编号、偏移和全局自由度 */;
csc3_demo::ElementMatrixBatch element_matrices = /* 按计划次序排列的局部矩阵 */;

csc3_demo::SymmetricCscAssembler assembler;
assembler.build_symbolic_parallel(topology, thread_count);
assembler.assemble_numeric_atomic(element_matrices, thread_count);

const csc3_demo::Csc3Matrix& stiffness_matrix = assembler.matrix();
```

`build_symbolic_parallel()` 先检查拓扑，再按 `ElementId` 排序并生成 CSC3 结构和 scatter 计划；不同线程数得到相同的结构和计划。`assemble_numeric_atomic()` 清零 `values` 后组装整个局部矩阵批次。串行实现只用于正确性比较和性能基线。

数值组装中的浮点加法顺序会随线程调度变化，因此结果按相对 Frobenius 误差 $e_F$ 和最大绝对误差比较，不要求逐位相同。

输入、索引、所有权、异常和线程安全规则见[公共接口与命名契约](docs/api-and-naming-contract.md)。旧接口迁移见 [`0.2.0` 迁移说明](MIGRATION.md)。

## Windows 编译

需要准备：

- 64 位 Windows；
- CMake `3.21` 或更高版本；
- Ninja；
- Visual Studio 2022 的“使用 C++ 的桌面开发”工作负载，或 64 位 MinGW-w64；
- 与编译器匹配的 OpenMP 运行时；
- Python `3.10` 或更高版本（仅完整验收需要）。

所有平台都要求 CMake `3.21` 或更高版本；证据与 JUnit 工作流同样要求 CMake `3.21` 或更高版本。Python 依赖安装命令为：

```powershell
python -m pip install -r demos/csc3_symmetric_assembly_demo/requirements-test.txt
```

### MSVC + Ninja

在 “x64 Native Tools Command Prompt for VS 2022” 中执行：

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

MSVC 构建会把 `/utf-8` 传递给使用 `csc3_demo` 的目标，使包含中文注释的公共头文件可在 Windows 默认代码页环境中编译。

### MinGW-w64 + Ninja

确认当前终端中的 `g++`、`cmake` 和 `ninja` 都来自同一套 64 位环境，然后执行：

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

两个工具链均可用下面的方式单独验证公共接口：

```powershell
cmake -S demos/csc3_symmetric_assembly_demo/tests/external_consumer `
  -B build/issue-54-consumer -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
cmake --build build/issue-54-consumer --parallel
ctest --test-dir build/issue-54-consumer --output-on-failure --no-tests=error
```

如使用 MinGW，请在 consumer 配置命令中增加 `-DCMAKE_CXX_COMPILER=g++`。MSVC 与 MinGW 的 consumer 也应使用不同的构建目录。

`CSC3_DEMO_REQUIRE_OPENMP=OFF`、找不到 `OpenMP::OpenMP_CXX` 或编译器与运行时不匹配，都会使配置失败；Demo 不会悄悄改走串行路径。

## Windows 工程网格测试

正式测试扫描 $p=1,\ldots,P_{\max}$。每个线程数预热 $W=2$ 次、测量 $R=7$ 次；每个样本单独启动一个子进程，样本之间不并发。下面是本次 16 线程主机使用的命令：

```powershell
python demos/csc3_symmetric_assembly_demo/scripts/run_windows_process_benchmark.py `
  --repository-root . `
  --benchmark-executable build/issue-54-msvc/bin/csc3_demo_benchmark.exe `
  --input examples/3d-WindTurbineHub.inp `
  --out-dir demos/csc3_symmetric_assembly_demo/results/2026-07-25-windows-x64-issue-54 `
  --maximum-threads 16 --warmup 2 --repeat 7 `
  --compiler "MSVC 19.44.35227" `
  --cmake "4.3.3" --ninja "1.13.2" `
  --openmp-runtime "vcomp140.dll 14.51.36247.0"
```

脚本会检查 WindHub 的 Git LFS 文件、请求和实际线程数、样本时间区间、返回码以及矩阵误差。若样本缺失、重叠、执行失败或满足 $e_F>10^{-8}$，本轮测试判为 `FAIL`。峰值工作集取自 `GetProcessMemoryInfo().PeakWorkingSetSize`；`estimated_persistent_bytes` 只是向量容量估计，两者分开记录。

## 作为子目录使用

本项目提供构建树 target，不提供可安装的 CMake package：

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(my_solver PRIVATE csc3_demo::csc3_demo)
```

作为子项目时，内部测试默认关闭，不会改写父项目的 `BUILD_TESTING`。

## 报告和交付文件

CTest 覆盖符号结构、atomic 高争用累加、输入错误、串行矩阵比较和外部 consumer，测试清单见 `tests/ctest/expected-cpp-tests.txt`。CI 只检查功能，不能代替正式性能测试。

Windows 交付包包含源码 ZIP、中文 Markdown 报告、CSV/JSON 原始数据、构建日志和 SHA-256。可用下列命令检查包内文件：

```powershell
python demos/csc3_symmetric_assembly_demo/scripts/create_windows_delivery.py verify `
  --package <中文交付ZIP>
```

受控 Linux 验收见 `packaging/README.md`、`packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md`、`packaging/ACCEPTANCE_CHECKLIST.zh-CN.md`、`packaging/ACCEPTANCE_RECORD.schema.json` 和 `packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md`。流程依次执行 `draft`、`render`、`validate`、`finalize`：`prepare_acceptance_materials.py draft` 生成 `acceptance-machine-facts.json` 与 `acceptance-decision.json`，`render` 生成 deterministic renderer outputs，最后用 `MANIFEST.sha256` 绑定文件。分发策略明确前，交付状态保持 `INTERNAL EVALUATION ONLY`。
