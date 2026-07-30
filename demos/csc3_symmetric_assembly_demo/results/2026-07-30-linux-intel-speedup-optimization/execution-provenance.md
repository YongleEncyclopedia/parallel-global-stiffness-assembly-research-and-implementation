# 执行来源

## 平台

- 主机：`iWORK`
- CPU：Intel Core Ultra 7 265KF
- 物理核 / 逻辑处理器：20 / 20
- 编译器：GCC 13.3.0
- CMake：3.28.3
- Ninja：1.11.1
- OpenMP runtime：GNU libgomp
- 构建类型：Release

完整平台字段见 `fresh-process-unbound/run_manifest.json`。

## 源码与二进制

- 分支：`codex/issue-44-linux-speedup`
- 源码提交：`7da2897ab1b01a4aa028dc91a2885d0232fad01d`
- 实验开始时已跟踪工作树：干净
- benchmark 二进制 SHA-256：
  `2917e9663a3875f77a465dbb0c2314fd730f2e6cf8d7ba9c8f4f7bcd834e0733`

正式实验前的最后一次源码操作是 `clang-format`。为排除“实验二进制没有来自
记录提交”的疑问，实验结束后从上述干净提交重新构建
`csc3_demo_benchmark`。实验实际使用的二进制与重新构建的二进制 SHA-256
完全相同。

## 时间和内存定义

- 串行基准：
  7 个正式 $p=1$ 子进程中的
  $t_{\mathrm{serial}}=t_{\mathrm{serial,symbolic}}+
  t_{\mathrm{serial,numeric}}$ 中位数。
- 候选总时间：
  $t_{\mathrm{candidate}}=t_{\mathrm{symbolic}}+t_{\mathrm{numeric}}$。
- 总加速比：
  $S_p=\operatorname{median}(t_{\mathrm{serial}})/
  \operatorname{median}(t_{\mathrm{candidate},p})$。
- 峰值内存：Linux `wait4().ru_maxrss`，每个子进程独立采集。

## 验证结果

- Release CTest：10/10 `PASS`。
- 检查版 CTest：9/9 `PASS`。
- Python：465 项 `PASS`，3 项按平台条件 `SKIP`。
- 正式 benchmark：180/180 子进程退出码为 0。
- 每个 $p=1,\ldots,20$：2 个预热样本和 7 个正式样本。
- 矩阵正确性、结构、scatter 和线程组大小：全部 `PASS`。
- 最大相对 Frobenius 误差：$1.5377070308250195\times10^{-16}$，
  阈值为 $10^{-8}$。

所有实际命令见 `run_commands.sh`。
