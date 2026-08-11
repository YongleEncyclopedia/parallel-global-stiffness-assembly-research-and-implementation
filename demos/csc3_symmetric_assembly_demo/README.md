# CSC3 对称稀疏组装 Demo

本 Demo 使用 C++17 和 OpenMP 完成对称矩阵上三角的 CSC3 符号组装与 atomic 数值组装，公共接口版本为 `0.2.0`。

## 目录说明

后文命令都在 Demo 根目录运行，也就是能够直接看到 `CMakeLists.txt` 的目录。

在完整仓库中先执行：

```powershell
cd demos/csc3_symmetric_assembly_demo
```

如果使用单独的源码 ZIP，解压后进入 `csc3_symmetric_assembly_demo` 目录。

| 内容 | 路径 |
|---|---|
| 公共接口 | `include/csc3_demo/assembly_helper.h` |
| 并行实现 | `src/assembly_helper.cpp` |
| 最小示例 | `src/main.cpp` |
| 性能测试程序 | `tools/src/benchmark_main.cpp` |
| 串行参考实现 | `tools/src/validation.cpp` |
| C++ 测试 | `tests/` |
| Windows 实验脚本 | `scripts/run_windows_process_benchmark.py` |
| 接口细则 | `docs/api-and-naming-contract.md` |

Windows 下建议把 MSVC 和 MinGW 的构建目录分别设为 `build/msvc` 与 `build/mingw`，不要共用 CMake 缓存。测试数据写入单独的结果目录，不写入源码目录。

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

`Symbolic(...)` 的三个参数依次是输出矩阵、输出辅助表和输入自由度编码。函数内部并行生成 CSC3 结构与散射位置。每轮数值组装先调用一次 `zero_values(...)`，再由调用方并行遍历单元；`add(...)` 使用 OpenMP atomic 累加共享矩阵条目。

`DofCodingInfo`、`HelpInfo`、`AssemblyHelper::Symbolic(...)` 和 `AssemblyHelper::add(...)` 的声明都在 `include/csc3_demo/assembly_helper.h`。完整示例见 `src/main.cpp`。串行实现只用于正确性比较和性能基线。

数值组装中的浮点加法顺序会随线程调度变化，因此结果按相对 Frobenius 误差 $e_F$ 和最大绝对误差比较。

输入、索引、所有权、异常和线程安全规则见[公共接口与命名契约](docs/api-and-naming-contract.md)。

## Windows 编译

需要准备：

- 64 位 Windows；
- CMake 3.21 以上；
- Ninja；
- Visual Studio 2022 的“使用 C++ 的桌面开发”工作负载，或 64 位 MinGW-w64；
- 与编译器匹配的 OpenMP 运行时；
- Python 3.10 以上（仅运行工程网格测试时需要）。

### MSVC + Ninja

在 “x64 Native Tools Command Prompt for VS 2022” 中执行：

```powershell
cmake --preset submission -B build/msvc
cmake --build build/msvc --parallel
ctest --test-dir build/msvc --output-on-failure --no-tests=error
build/msvc/bin/csc3_demo_app.exe
```

MSVC 构建会把 `/utf-8` 传递给使用 `csc3_demo` 的目标，使包含中文注释的公共头文件可在 Windows 默认代码页环境中编译。

### MinGW-w64 + Ninja

确认当前终端中的 `g++`、`cmake` 和 `ninja` 都来自同一套 64 位环境，然后执行：

```powershell
cmake --preset submission -B build/mingw -DCMAKE_CXX_COMPILER=g++.exe
cmake --build build/mingw --parallel
ctest --test-dir build/mingw --output-on-failure --no-tests=error
build/mingw/bin/csc3_demo_app.exe
```

两个工具链均可用下面的方式单独验证公共接口：

```powershell
cmake -S tests/external_consumer -B build/consumer-msvc -G Ninja `
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/consumer-msvc --parallel
ctest --test-dir build/consumer-msvc --output-on-failure --no-tests=error
```

MinGW 验证时把构建目录改为 `build/consumer-mingw`，并增加 `-DCMAKE_CXX_COMPILER=g++.exe`。

`CSC3_DEMO_REQUIRE_OPENMP=OFF`、找不到 `OpenMP::OpenMP_CXX` 或编译器与运行时不匹配，都会使配置失败。

## Windows 工程网格测试

正式测试扫描 $p=1,\ldots,P_{\max}$。每个线程数预热 $W=2$ 次、测量 $R=7$ 次；每个样本单独启动一个子进程，样本之间不并发。

实验脚本需要从完整 Git 仓库运行，以便记录源码提交和输入文件校验值。先取得本机版本信息，再执行线程扫描：

```powershell
$compilerVersion = (cl 2>&1 | Select-String "Version" | Select-Object -First 1).Line
$cmakeVersion = cmake --version | Select-Object -First 1
$ninjaVersion = ninja --version
$openmpVersion = (Get-Item "$env:WINDIR\System32\vcomp140.dll").VersionInfo.FileVersion
$windHubInput = Resolve-Path "..\..\examples\3d-WindTurbineHub.inp"

python scripts/run_windows_process_benchmark.py `
  --repository-root ../.. `
  --benchmark-executable build/msvc/bin/csc3_demo_benchmark.exe `
  --input $windHubInput `
  --out-dir ../../results/csc3-windows-thread-scan `
  --maximum-threads $env:NUMBER_OF_PROCESSORS --warmup 2 --repeat 7 `
  --compiler "$compilerVersion" `
  --cmake "$cmakeVersion" --ninja "$ninjaVersion" `
  --openmp-runtime "vcomp140.dll $openmpVersion"
```

脚本会检查 WindHub 的 Git LFS 文件、请求和实际线程数、样本时间区间、返回码以及矩阵误差。若样本缺失、重叠、执行失败或满足 $e_F>10^{-8}$，本轮测试判为 `FAIL`。

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
