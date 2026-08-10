# CSC3 对称稀疏组装 Demo

本 Demo 用 C++17 和 OpenMP 实现两步刚度矩阵组装：先并行生成 CSC3 结构和散射表，再由调用方并行遍历单元，通过 atomic 累加单元刚度。串行代码只用于测试和性能基线。

源码仅供研究院内部技术评估。

## 文件位置

| 内容 | 路径 |
|---|---|
| 公共接口 | `include/csc3_demo/assembly_helper.h` |
| 接口实现 | `src/assembly_helper.cpp` |
| 最小示例 | `src/main.cpp` |
| 测试 | `tests/` |
| 性能程序 | `tools/src/benchmark_main.cpp` |
| 接口细则 | `docs/api-and-naming-contract.md` |

构建命令都从本 README 所在目录执行。若从仓库根目录开始，先进入：

```powershell
cd demos/csc3_symmetric_assembly_demo
```

解压单独交付的源码包后，进入解压得到的 `csc3_symmetric_assembly_demo` 目录即可。

## 公共接口

研发部门要求的四个名称直接出现在公共头文件中：

- `DofCodingInfo`：保存“单元到节点”和“节点到全局自由度”的映射；
- `HelpInfo`：保存符号组装得到的自由度顺序和散射位置；
- `AssemblyHelper::Symbolic(...)`：输出 `Csc3Matrix` 和 `HelpInfo`，输入 `DofCodingInfo`；
- `AssemblyHelper::add(...)`：输入 `Csc3Matrix`、`HelpInfo` 和一个 `ElementStiffness`。

`ElementStiffness` 是“单刚”的只读视图，包含单元编号、行主序数据指针和数据长度，不复制单元矩阵。

典型调用如下：

```cpp
#include <csc3_demo/assembly_helper.h>

#include <cstdint>
#include <unordered_map>
#include <vector>

using namespace csc3_demo;

const DofCodingInfo dof_coding_info{
    {{10, {0, 1}}, {20, {1, 2}}},
    {{0, {0}}, {1, {1}}, {2, {2}}},
};
const std::unordered_map<ElementId, std::vector<double>> element_stiffness{
    {10, {3.0, -2.0, -2.0, 3.0}},
    {20, {2.0, -1.0, -1.0, 2.0}},
};

AssemblyHelper helper;
Csc3Matrix csc3;
HelpInfo help_info;

helper.Symbolic(csc3, help_info, dof_coding_info);
helper.zero_values(csc3);

const std::int64_t element_count =
    static_cast<std::int64_t>(help_info.element_ids.size());
#pragma omp parallel for schedule(static)
for (std::int64_t e = 0; e < element_count; ++e) {
    const ElementId elem_id = help_info.element_ids[static_cast<std::size_t>(e)];
    const auto& ke = element_stiffness.at(elem_id);
    helper.add(csc3, help_info,
               ElementStiffness{elem_id, ke.data(), ke.size()});
}
```

调用时注意三点：

1. `Symbolic(...)` 内部使用 OpenMP，线程数由 `OMP_NUM_THREADS` 控制。
2. `zero_values(...)` 在一轮数值组装开始前调用一次，不能和 `add(...)` 并发。
3. `add(...)` 可以在外部并行循环中并发调用，共享矩阵条目由 OpenMP atomic 更新。

`Symbolic(...)` 会按单元编号升序生成 `HelpInfo::element_ids`。数值阶段应按该顺序取单元矩阵。单元矩阵必须是完整、有限、对称的 $d_e\times d_e$ 行主序数组。

## Windows 编译

需要 64 位 CMake 3.21 以上、Ninja 和带 OpenMP 的 C++17 编译器。MSVC 与 MinGW 使用不同构建目录，不能共用 CMake 缓存。

### MSVC + Ninja

打开“x64 Native Tools Command Prompt for VS 2022”或已经载入 VS 2022 x64 环境的 PowerShell，进入 Demo 目录后执行：

```powershell
cmake --preset submission -B build/msvc
cmake --build build/msvc --parallel
ctest --test-dir build/msvc --output-on-failure --no-tests=error
build/msvc/bin/csc3_demo_app.exe
```

### MinGW-w64 + Ninja

在能找到 64 位 `g++.exe`、`libgomp`、CMake 和 Ninja 的 PowerShell 中，进入 Demo 目录后执行：

```powershell
cmake --preset submission -B build/mingw -DCMAKE_CXX_COMPILER=g++.exe
cmake --build build/mingw --parallel
ctest --test-dir build/mingw --output-on-failure --no-tests=error
build/mingw/bin/csc3_demo_app.exe
```

两条路径都应通过 9 个 C++ 测试。找不到 OpenMP 时，CMake 会直接报错，不会生成串行替代版本。

## Linux 和 macOS

进入 Demo 目录后执行：

```bash
cmake --preset submission
cmake --build --preset submission
ctest --preset submission --output-on-failure
./build/submission/bin/csc3_demo_app
```

AppleClang 需要先安装 `libomp`。若 CMake 没有自动找到它，可补充：

```bash
cmake --preset submission -DOpenMP_ROOT="$(brew --prefix libomp)"
```

## 测试内容

CTest 覆盖以下内容：

- 不同线程数下的符号结构和散射表一致；
- atomic 高冲突累加结果正确；
- 串行与并行整体刚度矩阵一致；
- Tet4、Hex8 小算例的位移和残差满足阈值；
- 非法节点、自由度、矩阵尺寸、非有限值和非对称矩阵会被拒绝；
- 外部 CMake 工程能只通过公共头文件和 `csc3_demo::csc3_demo` 完成集成。

矩阵比较使用相对 Frobenius 误差

$$
e_F=\frac{\lVert K_p-K_s\rVert_F}
{\max(\lVert K_s\rVert_F,10^{-30})}.
$$

正确性门槛为 $e_F\le 10^{-8}$。由于浮点加法不满足结合律，不同线程数下不要求数值逐位相同。

## 工程网格性能测试

`csc3_demo_benchmark` 支持生成式 Tet4、Hex8 和 Abaqus `.inp` 网格。正式线程扫描使用脚本 `scripts/run_windows_process_benchmark.py`：

- 线程数依次覆盖 $1,2,\ldots,P_{\max}$；
- 预热次数为 $W=2$，正式重复次数为 $R=7$；
- 每个样本启动一个新进程；
- 样本串行执行，不让不同线程配置互相影响内存和时间；
- Windows 峰值内存取自 `PeakWorkingSetSize`；
- 原始 CSV、JSON 和 manifest 一并保留。

性能结果只对记录的输入、提交、编译器和机器有效。GitHub Actions 只检查编译和小型正确性，不作为正式性能数据。

## 接入现有工程

本项目提供构建树 target，不提供安装包：

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(my_solver PRIVATE csc3_demo::csc3_demo)
```

作为子目录使用时，Demo 自带测试默认关闭，不会改写父工程的 `BUILD_TESTING`。

## 使用限制

- CSC3 只保存对称矩阵上三角，索引从 0 开始；
- 目前只提供 OpenMP 路径；
- Demo 不读取材料参数，也不处理单位换算；
- WindHub 解析器用于组装性能测试，不包含载荷、边界条件和位移求解；
- 正式对外发布前仍需由项目负责人确认许可证和分发范围。
