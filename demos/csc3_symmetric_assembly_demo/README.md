# CSC3 对称稀疏组装 Demo

本 Demo 使用 C++17 和 OpenMP，实现对称矩阵上三角的 CSC3 符号组装和原子（atomic）数值组装，公共接口版本为 `0.2.0`。

本页所说的 Demo 是 WindHub 工程算例。`src/main.cpp` 中的固定小输入只用于说明公共接口怎么调用，不是性能报告的运行结果。

## Windows：编译并运行 WindHub

开始前请确认：

- 使用 Windows 10/11 x64（Intel 或 AMD 处理器；Windows ARM64 尚未验证）；
- 已安装 CMake 3.21 以上；
- Visual Studio 2022 已勾选“使用 C++ 的桌面开发”；
- 已安装 64 位 Python 3.10 以上版本、Git for Windows 和 Git LFS，并且普通 PowerShell 能找到 `py.exe` 或 `python.exe`；
- 源码来自完整 Git 仓库，已跟踪文件没有尚未提交的修改。单独的 Demo 源码 ZIP 不能运行正式算例。
- `demos/csc3_symmetric_assembly_demo` 下没有旧的 `build` 目录；不同生成器留下的构建目录不能混用。

MSVC 工具链已经带有本项目所需的 OpenMP 支持，不用另外安装 OpenMP，也不需要 Ninja。

请把完整仓库放在较短且不含中文的路径下，例如 `C:\src\pgsa`。下面运行的是报告中的 WindHub 正式算例：脚本会依次测试 1 线程到本机全部逻辑线程，每档预热 2 次、正式测量 7 次。总样本数是本机逻辑线程数的 9 倍，各样本不会同时运行。

完整实验需要较长时间。历史机器的峰值内存约为 4.8 GiB，这只是运行前的量级参考，新结果以当前电脑实测为准。

打开普通 PowerShell，进入完整仓库根目录，然后把下面这一整段依次执行完：

```powershell
git lfs install
git lfs pull --include="examples/3d-WindTurbineHub.inp"
cd demos/csc3_symmetric_assembly_demo
mkdir build
cd build
cmake ..
cmake --build . --config Release
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub.ps1
```

`cmake --build` 后面的 `.` 表示当前 `build` 目录，必须原样保留，不能换成 `.exe` 路径。最后一行才会启动 WindHub Demo；脚本会复用刚才的构建目录，并确认性能程序是 Release 版本。

运行结束后，终端会列出节点数、单元数、自由度数、矩阵正确性，以及每个线程数下的总时间中位数、变异系数、整体加速比和 Windows 峰值内存。“整体加速比”以同一算例的独立串行组装时间为基准，“矩阵正确性”表示并行结果已经和串行参考结果核对。

CSV、JSON、运行记录和中文 `summary.md` 保存在 `build/example-results/<时间戳>/`。

不同电脑的时间和内存会不同，不要求与旧报告逐项相同；复现时保持的是 WindHub 输入、全部线程、$W=2$、$R=7$ 和 Windows 内存测量口径。Git LFS 下载和常见报错见 [`examples/README.md`](examples/README.md)。

## 可选：运行自动测试

WindHub 是面向使用者的工程算例，自动测试则面向代码改动：它用已知答案、错误输入和并发场景检查公共接口及组装结果，防止修改后悄悄算错。它不生成性能报告，也不会重复运行上面的全线程实验。

当前仍在 `build` 目录时执行：

```powershell
ctest -C Release --output-on-failure
```

正常结果为 9 项测试全部通过。`-C Release` 与主流程编译的配置一致，不能省略。测试内容和维护者提交前检查见 [`tests/README.md`](tests/README.md)。

## MinGW-w64

如果使用 MinGW，请先在默认位置 `C:\msys64` 安装 MSYS2，并安装 `mingw-w64-x86_64-gcc`、`mingw-w64-x86_64-cmake` 和 `mingw-w64-x86_64-ninja`。打开普通 PowerShell，在完整仓库根目录执行：

```powershell
$env:Path = "C:\msys64\mingw64\bin;$env:Path"
cd demos/csc3_symmetric_assembly_demo
mkdir build-mingw
cd build-mingw
cmake -G Ninja "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe" ..
cmake --build .
ctest --output-on-failure
```

`build-mingw` 只用于 MinGW，不要与 MSVC 的 `build` 共用。这里检查的是 MinGW 构建兼容性和 9 项自动测试；正式 WindHub 演示使用前面的 MSVC x64 主流程。

## 目录与接口

主要源码和接口如下。

| 内容 | 路径 |
|---|---|
| 公共接口 | `include/csc3_demo/assembly_helper.h` |
| 算法说明 | `ALGORITHM.md` |
| 并行实现 | `src/assembly_helper.cpp` |
| 接口调用参考（固定小输入） | `src/main.cpp` |
| WindHub 正式算例入口 | `examples/run_windhub.ps1` |
| 性能测试程序 | `tools/src/benchmark_main.cpp` |
| 串行参考实现 | `tools/src/validation.cpp` |
| C++ 测试 | `tests/` |
| Windows 底层实验脚本 | `scripts/run_windows_process_benchmark.py` |
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
