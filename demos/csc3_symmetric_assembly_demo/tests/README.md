# tests 目录说明

这里放 Demo 的自动测试。它们主要回答四个问题：公共接口能不能直接使用，串并行组装结果是否一致，OpenMP 并发累加是否安全，以及性能测试生成的数据是否可信。

这些测试没有引入额外的 C++ 测试框架。每个 `.cpp` 文件都会编译成一个小程序；断言失败时抛出异常并返回非零退出码，CTest 据此判断通过或失败。

## 建议阅读顺序

如果想先弄清研发拿到接口后怎么调用，建议按下面的顺序阅读：

1. `external_consumer/main.cpp`：从独立 CMake 工程调用公共接口；
2. `consumer/csc3_demo_consumer.cpp`：用两个单元检查完整的 `Symbolic → zero_values → add` 流程；
3. `assembly_helper_tests.cpp`：核心类的结构、数值、异常和重复调用测试；
4. `correctness_validation_tests.cpp`：与独立串行参考实现比较矩阵、位移和残差；
5. `atomic_contention_tests.cpp`：多个线程同时写相同 CSC3 条目的高冲突测试；
6. `benchmark_timing_tests.cpp`、`benchmark_engine_tests.cpp`、`benchmark_io_tests.cpp`：计时、样本统计和 CSV/JSON 输出；
7. `inp_case_tests.cpp`、`windhub_benchmark_tests.cpp`：Abaqus 网格读取和工程网格实验规则；
8. `python/`：实验脚本、测试报告和交付文件的契约测试。

## 文件分工

| 文件 | 主要检查内容 |
|---|---|
| `assembly_helper_tests.cpp` | 研发接口、CSC3 结构、符号结果确定性、输入校验和异常安全 |
| `atomic_contention_tests.cpp` | OpenMP atomic 在大量写冲突下是否漏加或重复累加 |
| `correctness_validation_tests.cpp` | 并行结果与独立串行参考的矩阵误差、位移误差和残差 |
| `benchmark_timing_tests.cpp` | 符号阶段、清零阶段和数值累加阶段的计时口径 |
| `benchmark_engine_tests.cpp` | 预热、重复测量、统计量、线程选择和小型 Tet4/Hex8 算例 |
| `benchmark_io_tests.cpp` | CSV/JSON 字段、数据复算、命令行参数和输出文件保护 |
| `inp_case_tests.cpp` | Abaqus `.inp` 中 C3D4/C3D8 节点与单元的读取和报错位置 |
| `windhub_benchmark_tests.cpp` | WindHub 参数、正式实验门槛和失败证据保留 |
| `consumer/` | Demo 工程内部的最小公共接口调用 |
| `external_consumer/` | 独立 CMake 工程的接入检查 |
| `python/` | runner、报告、manifest 和交付包的脚本级测试 |

`ctest/expected-cpp-tests.txt` 和 `ctest/expected-ci-tests.txt` 是机器读取的测试清单。前者列出 9 个 C++ 测试，后者再加 1 个 Python 契约测试。清单只写测试名称，不能加入说明文字。

## 运行方法

以下命令在 Demo 根目录运行，也就是 `tests/` 的上一级目录：

```powershell
cmake --preset submission
cmake --build --preset submission --parallel
ctest --preset submission --output-on-failure
```

`submission` 只运行 9 个核心 C++ 测试。启用交付验收测试后，CTest 还会运行 `tests/python/`。

这里的生成式小算例用于检查代码路径和结果，不用于得出正式性能结论。工程网格性能仍要使用规定的输入、线程扫描和独立进程测量流程。
