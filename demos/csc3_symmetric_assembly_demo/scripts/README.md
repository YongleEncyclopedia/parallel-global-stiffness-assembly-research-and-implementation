# scripts 目录说明

这个目录放实验和交付辅助脚本，不包含 CSC3 组装算法。真正的并行符号组装和
atomic 数值组装在 `../src/assembly_helper.cpp`，公共接口在
`../include/csc3_demo/assembly_helper.h`。

这些脚本主要做四件事：运行实验、检查测试结果、生成报告、整理交付文件。它们会
调用已经编译好的 C++ 程序，并保存命令、环境、原始数据和校验值。只想接入组装类时，
不需要通读本目录。

## 建议阅读顺序

如果想了解 Windows 实验和交付过程，按下面的顺序看即可：

1. `run_windows_process_benchmark.py`：逐线程运行工程网格实验；
2. `generate_windows_delivery_report.py`：复核实验数据并生成报告和图；
3. `create_windows_delivery.py`：把源码、报告和证据整理成 Windows 交付 ZIP；
4. `check_ctest_inventory.py`、`check_ctest_junit.py`：检查 CTest 是否完整通过。

Linux 正式实验使用 `run_benchmark.py` 和 `formal_host.py`。其余
`acceptance_*.py`、`prepare_acceptance_materials.py`、
`validate_acceptance_record.py` 与 `finalize_delivery.py` 属于内部验收流程，第一次
阅读 Demo 时可以先跳过。

## 文件分工

| 文件 | 用途 |
|---|---|
| `run_windows_process_benchmark.py` | 在 Windows 上以独立进程扫描全部线程数，记录时间、正确性和峰值工作集 |
| `generate_windows_delivery_report.py` | 从 Windows 原始证据生成中文 Markdown 报告和性能图 |
| `create_windows_delivery.py` | 从指定 Git 提交和 Windows 证据生成中文交付 ZIP |
| `run_benchmark.py` | 配置、构建并运行通用或 Linux 正式 benchmark，保存可复核证据 |
| `formal_host.py` | 读取 Linux CPU 拓扑，检查正式实验所需的线程和 OpenMP 环境 |
| `generate_test_report.py` | 复核 benchmark、CTest 和 manifest，生成通用 Markdown 报告 |
| `check_ctest_inventory.py` | 将实际注册的 CTest 与预期测试清单逐项比较 |
| `check_ctest_junit.py` | 检查 CTest JUnit XML 中的测试数和通过状态 |
| `plot_demo_logic_cn.py` | 绘制中文算法流程示意图，不读取性能数据 |
| `create_internal_handoff.py` | 把本机快速测试整理成内部交接材料，不作为正式性能证据 |
| `create_delivery_package.py` | 生成通用的可重复源码交付包 |
| `verify_delivery_package.py` | 校验交付 ZIP；可在干净目录中重新构建和运行测试 |
| `acceptance_core.py` | 固定候选包和证据快照，推导机器可复核的验收事实 |
| `acceptance_rendering.py` | 根据机器事实和人工决定生成验收记录、清单与交付说明 |
| `acceptance_publication.py` | 将验收目录安全地发布到最终位置，不覆盖已有目录 |
| `prepare_acceptance_materials.py` | 生成待填写的验收决定，并在填写后渲染验收文件 |
| `validate_acceptance_record.py` | 独立检查验收记录、证据引用和 SHA-256 |
| `finalize_delivery.py` | 复验已批准材料并生成最终交付目录 |

## 数据边界

- Python 脚本不计算单元刚度，也不实现 `Symbolic()` 或 `add()`；这些工作由 C++ 完成。
- 性能结论必须来自脚本保存的 CSV、JSON 和 manifest，不能从终端截图手工抄写。
- Windows 线程扫描中，每个预热或正式样本都在新的子进程中运行，避免前一轮实验的
  内存状态影响下一轮。
- 报告生成脚本会重新计算统计量。原始数据不完整或互相矛盾时，脚本直接失败。
