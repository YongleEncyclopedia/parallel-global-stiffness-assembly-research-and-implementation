# include 目录说明

公共头文件。
[`csc3_demo/assembly_helper.h`](csc3_demo/assembly_helper.h)：声明输入数据、CSC3
输出、散射表和 `AssemblyHelper`



## 单轮组装流程

`DofCodingInfo` 提供单元、节点和全局自由度的映射。`Symbolic()` 根据这份拓扑生成
`Csc3Matrix` 的上三角结构，并在 `HelpInfo` 中记录每个局部上三角条目的目标位置。
正式累加前先调用一次 `zero_values()`，随后由调用方建立 OpenMP 循环，每个单元调用
一次 `add()`。

`Symbolic()` 内部已经并行化；`add()` 本身不创建并行区，只在写入共享矩阵条目时使用
OpenMP atomic。因此不能把 `zero_values()` 放进并行累加过程，也不能遗漏或重复处理单元。

## 在其他 CMake 工程中使用

将 Demo 加入工程后，只需要链接带命名空间的 target：

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(your_target PRIVATE csc3_demo::csc3_demo)
```

C++ 文件中包含：

```cpp
#include <csc3_demo/assembly_helper.h>
```

CMake 会把头文件路径、C++17、OpenMP 和 Windows `/utf-8` 选项传给调用目标。
