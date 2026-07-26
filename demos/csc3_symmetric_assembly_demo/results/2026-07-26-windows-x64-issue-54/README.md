# Issue #54 Windows x64 正式交付证据

## 结论

**PASS。** 本目录保存 Issue #54 的 Windows 原始性能数据、构建与
clean-room 日志、内部评估、最终中文交付 ZIP 及校验文件。中文测试报告位于
[`reports/2026-07-26-windows-x64-issue-54/测试报告.md`](../../reports/2026-07-26-windows-x64-issue-54/测试报告.md)。

基线提交为 `ae7da2aaad2b72e012bfb842bfa34ba894b00c74`；性能实验源码提交为
`14d89fad3b643b0ce81047aecbddd3e1cfb504e2`；最终源码 ZIP 对应提交为
`419221b0ce58e37fca41fe48bbcbca9f71709ecf`。后两者之间只包含交付测试、
报告链接和版本追溯修正，没有改变算法、公开接口或基准程序。

## 关键结果

- 平台：Windows 11 Pro for Workstations x64，AMD Ryzen 7 9800X3D，
  8 个物理核、16 个逻辑处理器，31.116 GiB 物理内存。
- MSVC 19.44.35227 + Ninja 1.13.2：配置、编译、CTest 10/10、
  外部 consumer 1/1、两项 OpenMP 负向门禁和最终 clean-room 均 `PASS`。
- MinGW-w64 GCC 16.1.0 + Ninja 1.13.2：配置、编译、CTest 10/10、
  外部 consumer 1/1、两项 OpenMP 负向门禁和最终 clean-room 均 `PASS`。
- WindHub 扫描覆盖 $p=1,\ldots,16$，每档预热 $W=2$、正式测量 $R=7$；
  共 144 个新启动且互不重叠的子进程样本，全部退出码为零，实际 OpenMP
  team size 与请求值一致。
- 最大相对 Frobenius 误差为 $1.510488\times10^{-16}$，满足
  $10^{-8}$ 阈值。
- $p=16$ 时总体加速比为 2.1490，并行总时间中位数为
  $1428.320\ \mathrm{ms}$；$p=1$ 时总体加速比为 0.8039。
- Windows 实测峰值工作集在 $p=16$ 时的中位数为
  5,150,707,712 bytes，约 4.797 GiB；来源为存活子进程句柄上的
  `GetProcessMemoryInfo().PeakWorkingSetSize`。
- 最终 Python 测试为 380 项通过、3 项按设计跳过、退出码 0。

## 输入与交付校验

- WindHub 输入：
  `examples/3d-WindTurbineHub.inp`，76,111,745 bytes，
  SHA-256
  `4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`。
- 性能基准程序 SHA-256：
  `bfbc7b2b5b4e39347d8da250383f8787530afe038cbc3c71545a76be3bc4c1b1`。
- 最终源码 ZIP SHA-256：
  `b5a1a1cff747718b292d9388efb51f9cb3de5912d0fb6daa6f55c5fbd1758aa0`。
- 最终外层 ZIP SHA-256：
  `4ac0a2a4072c02a6c5ede35bea816b17f9d4e44a33651f56d668a7fefd735214`。

最终包为
[`CSC3对称稀疏组装Demo_Windows_x64_研究院交付_2026-07-26.zip`](delivery/CSC3对称稀疏组装Demo_Windows_x64_研究院交付_2026-07-26.zip)，
相邻 `.sha256` 文件校验外层 ZIP。独立校验结果见
[`release_verification.json`](delivery/release_verification.json)。

## 证据索引

- [`performance/benchmark_samples.csv`](performance/benchmark_samples.csv)：
  144 个逐样本记录。
- [`performance/benchmark_summary.json`](performance/benchmark_summary.json)：
  正确性、时间、加速比和峰值内存统计。
- [`performance/run_manifest.json`](performance/run_manifest.json)：
  进程时段、线程 team size、输入与 578 个工件哈希追溯。
- [`performance/raw/`](performance/raw/)：逐进程 stdout、stderr、CSV 和
  JSON 原始输出。
- [`builds/build_evidence.json`](builds/build_evidence.json)：双工具链、
  consumer、OpenMP 门禁、完整测试和 clean-room 汇总。
- [`builds/clean-room/final-source-419221b-msvc/`](builds/clean-room/final-source-419221b-msvc/)：
  最终源码 ZIP 的 MSVC clean-room 日志。
- [`builds/clean-room/final-source-419221b-mingw/`](builds/clean-room/final-source-419221b-mingw/)：
  最终源码 ZIP 的 MinGW clean-room 日志。
- [`internal-evaluation/内部评估.md`](internal-evaluation/内部评估.md)：
  仅供内部评估的结论、适用边界和风险。
- [`SHA256SUMS.txt`](SHA256SUMS.txt)：本目录全部非自引用文件的
  SHA-256。

早期失败日志被保留，用于说明隔离 Python 选择和首次 clean-room 测试夹具
问题；每个失败均在后续全新目录中修复并重新得到 `PASS`，没有删除或改写原始
诊断证据。当前剩余 blocker：无。
