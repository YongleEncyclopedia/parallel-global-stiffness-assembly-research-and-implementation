# WindHub Windows 全线程示例

这里放普通用户可以直接运行的示例入口。工程网格仍保存在仓库根目录的
`examples/3d-WindTurbineHub.inp`，本目录不会再复制一份 76 MB 文件。

先按上一级 README 的五行命令完成 MSVC 编译。编译结束后，当前目录应为
`build`，执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\examples\run_windhub.ps1
```

脚本会自动把性能程序构建为 Release，然后测试本机从 1 到全部逻辑线程数。
每档先预热 2 次，再正式测量 7 次；每个样本使用一个新进程，样本之间不会并发。

运行前还需要：

- 当前源码来自完整 Git 仓库，而不是单独的 Demo 源码 ZIP；
- 64 位 Python 3.10 或更高版本；
- Git for Windows 和 Git LFS 已安装；
- `examples/3d-WindTurbineHub.inp` 已下载为真实文件；
- 已跟踪文件没有尚未提交的修改。

首次获取 WindHub 文件时，在仓库根目录执行：

```powershell
git lfs install
git lfs pull --include="examples/3d-WindTurbineHub.inp"
```

脚本一共运行 9 轮，每轮把 1 到最大线程数各测一次。历史机器的峰值内存约为
4.8 GiB，这只是启动前的量级参考；新结果以当前 Windows 设备实测为准。

结果写入 `build/example-results/<时间戳>/`，其中包括逐样本 CSV、汇总 JSON、
运行记录和 `summary.md`。终端也会打印各线程的总时间、变异系数、整体加速比
和峰值内存。不同电脑的时间和内存不需要与旧报告完全相同。

如果运行条件不满足，终端会直接说明原因并给出 `failure.json` 的位置。如果还没有
`build` 目录，或者没有找到 Python，失败记录会保存到 Windows 临时目录。
需要提前结束时按 `Ctrl+C`；脚本会停止当前子进程并保留失败记录。
