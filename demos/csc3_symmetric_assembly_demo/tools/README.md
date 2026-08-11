# tools 目录说明

这个目录放测试和实验辅助代码，不是研发侧调用的组装接口。它负责准备算例、读取 Abaqus
网格、建立串行参考结果、运行不同线程数的测试，并把结果写成 CSV 和 JSON。

如果只想把组装类接入求解器，应先阅读：

- `../include/csc3_demo/assembly_helper.h`：公共接口；
- `../src/assembly_helper.cpp`：并行符号组装和 atomic 数值组装；
- `../src/main.cpp`：最小调用示例。

## 文件分工

| 文件 | 用途 |
|---|---|
| `include/csc3_demo_tools/evidence.h` | 测试算例、串行参考和误差比较使用的数据结构 |
| `include/csc3_demo_tools/benchmark.h` | benchmark 的配置、原始样本和汇总结果 |
| `src/benchmark_main.cpp` | 命令行程序入口 |
| `src/benchmark.cpp` | 串行基线、各线程测试和结果汇总 |
| `src/benchmark_io.cpp` | 参数解析以及 CSV、JSON 文件输出 |
| `src/generated_cases.cpp` | 生成 Tet4、Hex8 小型算例和单元刚度矩阵 |
| `src/inp_case.cpp` | 读取 Abaqus `.inp` 中的节点和实体单元 |
| `src/validation.cpp` | 独立串行组装、矩阵比较和位移验证 |

## 数据怎么流动

一次测试大致经过下面几步：

1. `benchmark_main.cpp` 把命令行参数交给 `run_benchmark_cli()`；
2. `benchmark_io.cpp` 解析参数，得到 `BenchmarkConfiguration`；
3. `benchmark.cpp` 生成小型算例，或通过 `inp_case.cpp` 读取工程网格；
4. `generated_cases.cpp` 准备自由度、单元刚度、载荷和约束；
5. `benchmark.cpp` 分别运行独立串行基线和并行候选路径；
6. `validation.cpp` 比较 CSC3 结构、矩阵数值、位移和残差；
7. `benchmark_io.cpp` 复核原始样本和汇总值，再写出 CSV 与 JSON。

串行参考与并行候选没有共用 `HelpInfo` 或 scatter 位置。这样做是为了避免两条路径同时带有
同一个错误，最后却得到看似一致的结果。

## 建议阅读顺序

第一次阅读可以按下面的顺序：

1. `src/benchmark_main.cpp`：先看程序从哪里开始；
2. `include/csc3_demo_tools/benchmark.h`：了解输入配置和输出结果；
3. `src/benchmark.cpp`：看一次测试如何执行；
4. `src/validation.cpp`：看串并行结果如何比较；
5. `src/generated_cases.cpp`：需要了解 Tet4、Hex8 单元矩阵时再看；
6. `src/inp_case.cpp`：需要了解工程网格输入时再看；
7. `src/benchmark_io.cpp`：这里主要处理文件格式和参数检查，最后看即可。

## 几个容易混淆的名称

- **串行参考**：独立实现，只用于正确性比较和性能基线；
- **并行候选**：研发接口对应的并行符号组装和 atomic 数值组装；
- **scatter**：把单元局部矩阵条目映射到整体 CSC3 数值数组的位置；
- **warmup**：预热样本，保留原始记录但不参与统计；
- **measured**：正式测量样本，用来计算均值、中位数和加速比。

性能数据只有在输入文件、提交版本、编译器、线程设置和机器环境都记录完整时才具有可比性。
