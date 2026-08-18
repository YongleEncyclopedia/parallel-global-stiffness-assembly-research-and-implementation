# CSC3 对称稀疏组装 Demo

本 Demo 使用 C++17 和 OpenMP，实现对称矩阵上三角的 CSC3 符号组装和原子累加（atomic）数值组装。

## Windows 快速编译

开始前请确认：

- 使用 Windows 10/11 x64（Intel 或 AMD 处理器）；
- 已安装 CMake 3.21 以上；
- Visual Studio 2022 已勾选“使用 C++ 的桌面开发”。

MSVC 工具链已经带有本项目所需的 OpenMP 支持，不用另外安装 OpenMP。首次编译也不需要 Ninja 或 Python。

请把源码放在较短且不含中文的路径下，例如 `C:\src\pgsa`。打开普通 PowerShell，进入完整仓库根目录后执行：

```powershell
cd demos/csc3_symmetric_assembly_demo
mkdir build
cd build
cmake ..
cmake --build .
```

上面的命令结束后，当前目录是 `build`。运行示例程序：

```powershell
.\bin\csc3_demo_app.exe
```

正常输出为：

```text
n=3 values=3,-2,5,-1,2
```

以 Demo 目录为起点，程序位于 `build/bin`，静态库位于 `build/lib`。

上述快速命令只用于确认编译和运行。正确性测试及性能测试请使用 `tests/README.md` 中的 Release 构建方式。

## MinGW-w64

如果使用 MinGW，请先在默认位置 `C:\msys64` 安装 MSYS2，并安装 `mingw-w64-x86_64-gcc`、`mingw-w64-x86_64-cmake` 和 `mingw-w64-x86_64-ninja`。打开普通 PowerShell，在完整仓库根目录执行：

```powershell
$env:Path = "C:\msys64\mingw64\bin;$env:Path"
cd demos/csc3_symmetric_assembly_demo
mkdir build-mingw
cd build-mingw
cmake -G Ninja "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe" ..
cmake --build .
.\bin\csc3_demo_app.exe
```

`build-mingw` 只用于 MinGW，不要与 MSVC 的 `build` 共用。程序输出应与前面的 MSVC 示例一致。

## 目录与接口

主要源码和接口如下。

| 内容 | 路径 |
|---|---|
| 公共接口 | `include/csc3_demo/assembly_helper.h` |
| 算法说明 | `ALGORITHM.md` |
| 并行实现 | `src/assembly_helper.cpp` |
| 最小示例 | `src/main.cpp` |
| 性能测试程序 | `tools/src/benchmark_main.cpp` |
| 串行参考实现 | `tools/src/validation.cpp` |
| C++ 测试 | `tests/` |
| Windows 实验脚本 | `scripts/run_windows_process_benchmark.py` |
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

## 测试

测试内容和运行方法见 [`tests/README.md`](tests/README.md)。这些步骤用于提交前检查，不是第一次编译的必需步骤。

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
