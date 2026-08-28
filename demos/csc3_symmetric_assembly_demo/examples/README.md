# WindHub 会议演示与完整复现

这里提供 Windows 和 Linux 两组无参数入口。`run_windhub_demo.*` 用于会议现场的单样本演示，`run_windhub.*` 用于完整性能复现。

入口支持两种源码布局：自包含交付包把物化后的 WindHub 输入放在本目录，并用 `PACKAGE_MANIFEST.json` 与 `SHA256SUMS.txt` 校验；完整 Git 仓库从仓库根目录读取同一输入，并校验当前提交的 Git LFS 指针。

运行前请确认：

- 自包含包已完整解压，或完整仓库已经物化 Git LFS 输入；
- 已安装 CMake 3.21 以上、64 位 Python 3.10 以上版本和对应平台的 C++17/OpenMP 工具链；
- 完整 Git 仓库模式下，已跟踪文件没有尚未提交的修改；自包含包不要求 Git。
- Demo 目录下没有旧的 `build`；不同生成器留下的构建目录不能混用。

完整仓库第一次运行时先执行：

```powershell
git lfs install
git lfs pull --include="examples/3d-WindTurbineHub.inp"
```

自包含包不执行上述 Git 命令。Windows 与 Linux 的配置、构建和 CTest 命令见包根目录 [`README.md`](../README.md)。

## 会议快速演示

在刚才的 `build` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub_demo.ps1
```

Linux 在包根目录执行：

```bash
bash examples/run_windhub_demo.sh
```

该入口自动使用本机全部逻辑处理器，只启动一个新的 benchmark 子进程，配置为 $p=P_{\max}$、$W=0$、$R=1$ 和 `local-smoke`。它仍运行独立直接串行参考、CSC3/scatter 正确性对比和实际 OpenMP 线程组检查，但不并发其他 benchmark，也不循环制造持续高负载。

结果写入 `build/presentation-results/<时间戳>/`。`run_manifest.json` 使用 `csc3-windhub-presentation-v2`，并强制记录 `formal_evidence=false`；终端和 `summary.md` 都会说明“单次会议演示，不是正式性能统计”。其中的单次示意加速比只适合现场讲解，不能代替完整统计。

“直接串行参考”直接读取原始单元自由度拓扑和单元刚度矩阵，不调用 `Symbolic()`，不读取 `HelpInfo`，也不预建 CSC3 或 scatter；它采用贡献生成、排序和归并形成矩阵。`serial_total_ms` 只记录这条直接路径；单次整体加速比用它除以满线程 CSC3 的符号、数值总时间之和，并在终端和 Markdown 中按百分比显示，例如 $2.71\times$ 显示为约 $271\%$。另行记录的串行符号和串行数值时间只用于阶段诊断，不构成直接串行总时间。

## 完整性能复现

需要扫描全部线程数时执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub.ps1
```

Linux 在包根目录执行：

```bash
bash examples/run_windhub.sh
```

完整入口测试本机从 1 到全部逻辑线程，每档先预热 2 次，再正式测量 7 次，总计 $9P_{\max}$ 个样本。每个样本使用一个干净的新进程，样本之间不会并发。这样不仅能把进程内存读数归因到对应样本，也能隔离 CPU、缓存、内存带宽和系统内存压力；每个子进程的候选组装阶段仍由 OpenMP 并行。

结果写入 `build/example-results/<时间戳>/`，其中包括逐样本 CSV、汇总 JSON、运行记录和中文 `summary.md`。新结果使用包含直接串行字段的 raw v3 / process v2 schema；历史数据不改写、不与新口径混算。自包含包和 Linux 结果记录 `formal_evidence=false`。

## CPU 与内存读数

任务管理器中的 CPU 只在候选并行组装阶段明显升高；输入准备、独立串行参考和正确性检查不会持续占满全部核心，所以整个子进程的平均占用通常不高。

Windows 使用 `GetProcessMemoryInfo.PeakWorkingSetSize` 报告进程峰值工作集；Linux 使用 `wait4(...).ru_maxrss` 报告进程峰值常驻集。两个数字都覆盖整个 benchmark 子进程，包括直接串行参考的临时贡献数组，但操作系统定义不同，不能作为完全相同的跨平台指标。`estimated_persistent_bytes` 只表示候选算法所拥有持久向量的容量估计，不包含直接参考临时数组，不是常驻集，也不是算法峰值内存。

如果运行条件不满足，终端会直接说明原因并给出 `failure.json` 的位置。如果还没有
`build` 目录，或者没有找到 Python，Windows 失败记录会保存到临时目录。
需要提前结束时按 `Ctrl+C`；脚本会停止当前子进程并保留失败记录。
