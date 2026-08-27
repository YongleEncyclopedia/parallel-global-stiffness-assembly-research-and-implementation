# CSC3 对称稀疏组装 Demo

本 Demo 使用 C++17 和 OpenMP，实现对称矩阵上三角的 CSC3 符号组装和原子（atomic）数值组装，公共接口版本为 `0.2.0`。

本页所说的 Demo 是 WindHub 工程算例。`src/main.cpp` 中的固定小输入只用于说明公共接口怎么调用，不是性能报告的运行结果。

## 自包含交付包

研发部接收的是 `csc3-windhub-demo-<commit前12位>.zip`。包中已经包含物化后的 WindHub 输入、源码提交号、`PACKAGE_MANIFEST.json` 和逐文件 `SHA256SUMS.txt`；解压后不需要 `.git`、Git 或 Git LFS。运行入口会在启动 benchmark 前重新核对全部交付文件和输入 SHA-256。

自包含表示项目源码和工程输入已经齐全，不表示把编译器打进 ZIP。目标机器仍需预装 CMake、C++ 编译器、OpenMP 和 64 位 Python。

不要把历史 `create_windows_delivery.py` 生成的“源码 ZIP”当成这个自包含包：历史包为了控制体积，明确不携带 WindHub Git LFS 实体，只能独立构建和运行 CTest。可直接演示的包根目录必须同时存在 `PACKAGE_MANIFEST.json`、`SHA256SUMS.txt` 和 `examples/3d-WindTurbineHub.inp`。

## Windows：从干净目录编译并演示

前提条件：Windows 10/11 x64、CMake 3.21 以上、64 位 Python 3.10 以上，以及已勾选“使用 C++ 的桌面开发”的 Visual Studio 2022。MSVC 已带有所需 OpenMP 支持，不需要 Ninja。

将 ZIP 解压到较短且不含中文的路径，例如 `C:\csc3-clean\csc3-windhub-demo`。打开普通 PowerShell，进入解压后的包根目录，逐条执行：

```powershell
mkdir build
cd build
cmake -G "Visual Studio 17 2022" -A x64 ..
cmake --build . --config Release
ctest -C Release --output-on-failure
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub_demo.ps1
```

正常结果是 9 项 CTest 全部通过，随后 WindHub 会议演示显示 `PASS`。如果本机有 16 个可用逻辑处理器，入口会请求并核对 16 个符号组装线程和 16 个数值组装线程。结果位于 `build/presentation-results/<时间戳>/summary.md`。

`cmake --build .` 中的 `.` 表示当前 `build` 目录，不能换成 `.exe` 路径。不同生成器的构建目录不能混用；若配置命令失败，应删除这个尚未交付任何结果的 `build` 后重新开始。

## Linux：从干净目录编译并演示

前提条件：x86_64 Linux、CMake 3.21 以上、64 位 Python 3.10 以上，以及支持 OpenMP 的 GCC 或 Clang。Ubuntu/Debian 使用 GCC 时通常安装 `build-essential cmake python3` 即可；使用 Clang 时还需相应的 `libomp` 开发包。

进入解压后的包根目录，逐条执行：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
bash examples/run_windhub_demo.sh
```

Linux 入口同样使用当前进程可用的全部逻辑处理器，核对实际 OpenMP 线程组、矩阵、scatter 和独立串行参考。结果目录与 Windows 相同。

## 会议快速演示

会议现场只需运行对应平台最后一条命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub_demo.ps1
```

```bash
bash examples/run_windhub_demo.sh
```

演示入口自动使用当前进程可用的全部逻辑处理器，只启动一个新的 benchmark 子进程，配置为 $p=P_{\max}$、$W=0$、$R=1$。它仍会执行独立串行参考、CSC3 与 scatter 正确性对比，并核对实际 OpenMP 线程组；不会并发运行其他 benchmark，也不会用循环人为维持高 CPU 占用。终端和 `build/presentation-results/<时间戳>/summary.md` 会醒目标记“单次会议演示，不是正式性能统计”，manifest 使用 `csc3-windhub-presentation-v1` 并记录 `formal_evidence=false`。

Windows 任务管理器或 Linux 系统监视器中的 CPU 只会在候选并行组装阶段明显升高。输入准备、独立串行参考和正确性检查仍以串行为主，因此观察整个子进程生命周期时，平均 CPU 占用不会持续接近 100%。

## 完整性能复现

需要扫描所有线程数时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub.ps1
```

```bash
bash examples/run_windhub.sh
```

完整入口依次测试 1 线程到本机全部逻辑线程，每档预热 2 次、正式测量 7 次，总样本数为 $9P_{\max}$。每个样本都使用干净的新进程，任意时刻只运行一个 benchmark。串行调度既让峰值内存能够归因到单个样本，也隔离 CPU、缓存、内存带宽和系统内存压力；单个子进程内部的候选组装阶段仍使用 OpenMP 并行。

完整实验需要较长时间。CSV、JSON、运行记录和中文 `summary.md` 保存在 `build/example-results/<时间戳>/`。只有完整 Git 仓库中的 Windows 流程继续使用原正式证据 schema；自包含包和 Linux 的结果会明确记录 `formal_evidence=false`，用于复现和演示而不是替代正式趋势证据。

## 如何读内存数字

两个入口都区分以下数字：

- Windows 的“进程峰值工作集”由 `GetProcessMemoryInfo.PeakWorkingSetSize` 实测。
- Linux 的“进程峰值常驻集”由内核 `wait4(...).ru_maxrss` 实测并换算为字节。
- `estimated_persistent_bytes` 只估算算法所拥有持久向量的容量，不包含临时分配、运行库或其他进程内存；它不是算法峰值内存。

两种操作系统的数字都覆盖整个 benchmark 子进程，但系统定义不同，不能把 Linux 常驻集与 Windows 工作集当作完全相同的跨平台指标。不同电脑的时间和内存也不会逐项相同；必须一致的是输入 SHA-256、实际线程组、矩阵正确性和误差门限。

## 可选：运行自动测试

WindHub 是面向使用者的工程算例，自动测试则面向代码改动：它用已知答案、错误输入和并发场景检查公共接口及组装结果，防止修改后悄悄算错。它不生成性能报告，也不会重复运行上面的全线程实验。

Windows 和 Linux 的主流程已经在运行 WindHub 前执行 CTest。正常结果为 9 项测试全部通过；测试内容和维护者提交前检查见 [`tests/README.md`](tests/README.md)。

## 维护者：创建自包含 ZIP

从完整仓库根目录执行以下命令。创建脚本只读取指定 commit 中的 Demo 源码，并要求工作树中的 WindHub 实体与该 commit 的 Git LFS 指针完全一致；不会把 `build/`、`results/` 或 `reports/` 打进源码包。

```powershell
git lfs pull --include="examples/3d-WindTurbineHub.inp"
python demos/csc3_symmetric_assembly_demo/scripts/create_portable_delivery.py create --repository-root . --output-dir demos/csc3_symmetric_assembly_demo/build/portable-delivery --commit HEAD
python demos/csc3_symmetric_assembly_demo/scripts/create_portable_delivery.py verify --package demos/csc3_symmetric_assembly_demo/build/portable-delivery/csc3-windhub-demo-<commit前12位>.zip
```

包中的 WindHub 实体为 `76,111,745` 字节；期望 SHA-256 为 `4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`。该包仅供研究院内部技术评估，未经项目负责人许可不得对外发布。

## 可选：MinGW-w64 构建兼容性

如果使用 MinGW，请先在默认位置 `C:\msys64` 安装 MSYS2，并安装 `mingw-w64-x86_64-gcc`、`mingw-w64-x86_64-cmake` 和 `mingw-w64-x86_64-ninja`。打开普通 PowerShell，在 Demo 包根目录执行：

```powershell
$env:Path = "C:\msys64\mingw64\bin;$env:Path"
mkdir build-mingw
cd build-mingw
cmake -G Ninja "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe" ..
cmake --build .
ctest --output-on-failure
```

`build-mingw` 只用于 MinGW，不要与 MSVC 的 `build` 共用。这里检查构建兼容性和 9 项自动测试；会议 WindHub 演示使用前面的 MSVC x64 主流程。

## 目录与接口

主要源码和接口如下。

| 内容 | 路径 |
|---|---|
| 公共接口 | `include/csc3_demo/assembly_helper.h` |
| 算法说明 | `ALGORITHM.md` |
| 并行实现 | `src/assembly_helper.cpp` |
| 接口调用参考（固定小输入） | `src/main.cpp` |
| WindHub 会议演示入口 | `examples/run_windhub_demo.ps1` |
| Linux WindHub 会议演示入口 | `examples/run_windhub_demo.sh` |
| WindHub 完整复现入口 | `examples/run_windhub.ps1` |
| Linux WindHub 完整复现入口 | `examples/run_windhub.sh` |
| 性能测试程序 | `tools/src/benchmark_main.cpp` |
| 串行参考实现 | `tools/src/validation.cpp` |
| C++ 测试 | `tests/` |
| 独立进程实验脚本 | `scripts/run_windows_process_benchmark.py` |
| 自包含交付打包器 | `scripts/create_portable_delivery.py` |
| 接口说明 | `include/README.md` |

## 调用方式

```cpp
#include <csc3_demo/assembly_helper.h>

// 单元到节点、节点到全局自由度的映射。
csc3_demo::DofCodingInfo dof_coding_info = /* ... */;

csc3_demo::AssemblyHelper helper;
csc3_demo::Csc3Matrix csc3;
csc3_demo::HelpInfo help_info;
helper.Symbolic(csc3, help_info, dof_coding_info);
helper.zero_values(csc3);

#pragma omp parallel for schedule(static)
for (std::int64_t e = 0; e < element_count; ++e) {
    const auto elem_id = help_info.element_ids[static_cast<std::size_t>(e)];
    const auto& ke = element_stiffness.at(elem_id);
    helper.add(csc3, help_info,
               csc3_demo::ElementStiffness{elem_id, ke.data(), ke.size()});
}
```

`Symbolic(...)` 的三个参数依次是输出矩阵、输出辅助表和输入自由度编码。函数内部并行生成 CSC3 结构与散射位置。每轮数值组装先调用一次 `zero_values(...)`，再由调用方并行遍历单元；`add(...)` 通过 OpenMP 原子操作累加共享矩阵条目。

`DofCodingInfo`、`HelpInfo`、`AssemblyHelper::Symbolic(...)` 和 `AssemblyHelper::add(...)` 的声明都在 `include/csc3_demo/assembly_helper.h`。完整示例见 `src/main.cpp`。串行实现只用于正确性比较和性能基线。

数值组装中的浮点加法顺序会随线程调度变化，因此结果按相对 Frobenius 误差 $e_F$ 和最大绝对误差比较。

输入、索引、所有权、异常和线程安全规则直接写在
[公共头文件](include/csc3_demo/assembly_helper.h)中；接入说明见
[`include/README.md`](include/README.md)。

## 作为子目录使用

本项目提供构建树 target，不提供可安装的 CMake package：

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(my_solver PRIVATE csc3_demo::csc3_demo)
```

作为子项目时，内部测试默认关闭，不会改写父项目的 `BUILD_TESTING`。

## 使用限制

- CSC3 只保存对称矩阵上三角，全部索引从 0 开始；
- Demo 只提供 OpenMP 并行组装路径；
- 工程网格解析器只读取节点和 Tet4 单元，不处理载荷、边界条件或位移求解；
- 性能结果只对记录的输入、提交、编译器和机器有效。

源码仅供研究院内部技术评估，未经项目负责人许可不得对外发布。
