# WindHub Windows 正式算例

这里是 CSC3 Demo 的正式运行入口。工程网格保存在仓库根目录的
`examples/3d-WindTurbineHub.inp`，本目录不会再复制一份 76 MB 文件。

运行前请确认：

- 当前源码来自完整 Git 仓库，而不是单独的 Demo 源码 ZIP；
- 已安装 64 位 Python 3.10 以上版本、Git for Windows 和 Git LFS，普通 PowerShell 能找到 `py.exe` 或 `python.exe`；
- 已跟踪文件没有尚未提交的修改。
- Demo 目录下没有旧的 `build`；不同生成器留下的构建目录不能混用。

脚本会测试本机从 1 到全部逻辑线程，每档先预热 2 次，再正式测量 7 次。每个样本使用一个新进程，样本之间不会并发。历史机器的峰值内存约为 4.8 GiB，这只是运行前的量级参考，新结果以当前 Windows 设备实测为准。

第一次运行时，请在普通 PowerShell 中进入完整仓库根目录，把下面这段命令从上到下执行：

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

不要把 `cmake --build .` 后面的点改成程序路径；它表示当前 `build` 目录。最后一行才是正式算例入口。

脚本会确认 WindHub 文件已经由 Git LFS 下载，并确认性能程序使用 Release 编译。

结果写入 `build/example-results/<时间戳>/`，其中包括逐样本 CSV、汇总 JSON、
运行记录和中文 `summary.md`。终端会先打印节点、单元、自由度和矩阵正确性，
再列出各线程的总时间、变异系数、整体加速比和峰值内存。整体加速比以同一算例的独立串行组装时间为基准。不同电脑的时间和内存不需要与旧报告完全相同。

如果运行条件不满足，终端会直接说明原因并给出 `failure.json` 的位置。如果还没有
`build` 目录，或者没有找到 Python，失败记录会保存到 Windows 临时目录。
需要提前结束时按 `Ctrl+C`；脚本会停止当前子进程并保留失败记录。
