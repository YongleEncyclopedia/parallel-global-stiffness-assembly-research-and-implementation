# scripts 目录说明

这个目录放实验、报告和 Windows 文件整理脚本，不包含 CSC3 组装算法。真正的并行符号组装和
atomic 数值组装在 `../src/assembly_helper.cpp`，公共接口在
`../include/csc3_demo/assembly_helper.h`。

这些脚本主要做四件事：运行实验、检查测试结果、生成报告、整理交付文件。它们会
调用已经编译好的 C++ 程序，并保存命令、环境、原始数据和校验值。只想接入组装类时，
不需要通读本目录。

`run_windows_process_benchmark.py` 是保存正式证据的底层脚本，要求维护者明确提供
仓库、程序、输入、输出目录和工具链信息。直接空参运行时，它只会提示改用一键
示例，不会自行猜测信息或误启动高负载实验。普通 Windows 用户请在 `build` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub.ps1
```

一键脚本会检查并填写这些信息，再调用本目录的同一套独立进程采样逻辑。

## 建议阅读顺序

如果想了解 Windows 实验和交付过程，按下面的顺序看即可：

1. `run_windows_process_benchmark.py`：逐线程运行工程网格实验；
2. `generate_windows_delivery_report.py`：复核实验数据并生成报告和图；
3. `create_windows_delivery.py`：把源码、报告和证据整理成 Windows 交付 ZIP；
4. `check_ctest_inventory.py`、`check_ctest_junit.py`：检查 CTest 是否完整通过。

Linux 正式实验使用 `run_benchmark.py` 和 `formal_host.py`。

## 文件分工

| 文件 | 用途 |
|---|---|
| `run_windows_process_benchmark.py` | 维护者使用的 Windows 底层实验脚本；以独立进程扫描全部线程数，记录时间、正确性和峰值内存占用 |
| `generate_windows_delivery_report.py` | 从 Windows 原始证据生成中文 Markdown 报告和性能图 |
| `create_windows_delivery.py` | 从指定 Git 提交和 Windows 证据生成中文交付 ZIP |
| `run_benchmark.py` | 配置、构建并运行通用或 Linux 正式 benchmark，保存可复核证据 |
| `formal_host.py` | 读取 Linux CPU 拓扑，检查正式实验所需的线程和 OpenMP 环境 |
| `generate_test_report.py` | 复核 benchmark、CTest 和 manifest，生成通用 Markdown 报告 |
| `check_ctest_inventory.py` | 将实际注册的 CTest 与预期测试清单逐项比较 |
| `check_ctest_junit.py` | 检查 CTest JUnit XML 中的测试数和通过状态 |
| `plot_demo_logic_cn.py` | 绘制中文算法流程示意图，不读取性能数据 |

## 数据边界

- Python 脚本不计算单元刚度，也不实现 `Symbolic()` 或 `add()`；这些工作由 C++ 完成。
- 性能结论必须来自脚本保存的 CSV、JSON 和 manifest，不能从终端截图手工抄写。
- Windows 线程扫描中，每个预热或正式样本都在新的子进程中运行，避免前一轮实验的
  内存状态影响下一轮。
- 报告生成脚本会重新计算统计量。原始数据不完整或互相矛盾时，脚本直接失败。
