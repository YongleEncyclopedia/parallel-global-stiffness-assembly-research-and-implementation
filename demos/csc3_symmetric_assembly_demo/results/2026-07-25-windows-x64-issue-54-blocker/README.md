# Issue #54 Windows 交付阻塞证据

## 结论

Issue #54 的源码实现、中文文档与 Windows 双工具链常规验证已经完成，但正式性能实验在本机被数据完整性故障阻塞。三次从零开始的完整实验均按契约在首个失败样本处终止；没有拼接、重试或挑选失败实验中的样本，也没有生成虚假的八章 `PASS` 报告或最终交付 ZIP。

阻塞不是普通浮点舍入误差。多处异常的 64 位值仅相差
`0x0400000000000000`，即同一个指数位。最终诊断在任何符号或数值组装调用之前，仅对两份只读局部矩阵数组做逐元素扫描时复现了持久差异；同一地址随后重读 1024 次，1024 次均保持不一致。因此，当前主机不能提供 Issue 要求的可信 Windows 峰值内存占用与全线程性能证据。

## 已完成的 Windows 验证

源码提交为 `1d24921a514ce4f3b3ed66756a837bee3949892b`，基线为
`ae7da2aaad2b72e012bfb842bfa34ba894b00c74`。

- MSVC 19.44.35227.0 + Ninja 1.13.2：配置、编译和最小调用程序 `PASS`。
- MSVC CTest：10/10 `PASS`，总耗时 222.68 秒。
- MSVC 独立 consumer：1/1 `PASS`。
- MSVC OpenMP 负向门禁：`CSC3_DEMO_REQUIRE_OPENMP=OFF` 与
  `CMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE` 均按预期在配置期失败，门禁结果 `PASS`。
- MinGW-w64 GCC 16.1.0 + Ninja 1.13.2：配置、编译和最小调用程序 `PASS`。
- MinGW CTest：10/10 `PASS`，总耗时 216.78 秒。
- MinGW 独立 consumer：1/1 `PASS`。
- MinGW OpenMP 负向门禁：两项均按预期在配置期失败，门禁结果 `PASS`。

对应原始日志位于 [`builds/msvc`](builds/msvc) 与
[`builds/mingw`](builds/mingw)。

## 三次完整性能实验

三次实验均要求 $P_{\max}=16$、$W=2$、$R=7$，计划样本数为
$16(2+7)=144$。每个样本使用全新的子进程，样本之间不并发。

1. MSVC 尝试 1 完成 64 个样本后，在
   `measured-r03-o01-p01` 失败。元素 862057 的镜像值位型为
   `0x4230FF63B1A65BEC` 与 `0x4630FF63B1A65BEC`，异或为
   `0x0400000000000000`。
2. MSVC 尝试 2 完成 19 个样本后，在
   `warmup-r02-o04-p13` 失败。损坏值
   `0x4646C99787241DC5` 清除同一位后为
   `0x4246C99787241DC5`；矩阵正确性状态为 `FAIL`。
3. MinGW 尝试 3 的首个 `warmup-r01-o01-p01` 即因局部矩阵对称性异常退出，
   因而完整实验记录 0 个成功样本。

每次失败后都使用全新目录重新开始，前一尝试的样本完全排除。原始清单和失败样本位于
[`performance`](performance)。

## 排查结果

- MSVC 地址消毒器（AddressSanitizer）对 WindHub、$p=13$ 的完整路径运行
  79.15 秒，退出 0、stderr 为 0 字节，$e_F=1.48\times10^{-16}$，未发现堆越界、
  栈越界或释放后访问。
- MinGW 独立二进制连续三个 $p=13$ 子进程均退出 0，$e_F$ 约为
  $1.47\times10^{-16}$。
- 用户态内存模式校验分别覆盖 8 GiB 与 16 GiB；每次写入并读回四种 64 位模式，
  均为 0 mismatch。这说明故障不是一个能被短时常量模式稳定命中的简单坏页，但不能
  推翻后续只读数组上的持久位翻转证据。
- MinGW 调试容器模式运行 604 秒，没有输出越界断言，但未在超时前完成，因此只记为
  `TIMEOUT`，不记为通过。
- 阶段指纹诊断先复制约 1.28 GB 局部矩阵基线。最终版本在任何组装调用之前的第 21 次
  只读扫描发现：

  ```text
  INPUT_MUTATION stage=preflight-scan-21 index=132598192
  expected_bits=0xc634a32231093201
  observed_bits=0xc234a32231093201
  xor=0x0400000000000000
  IMMEDIATE_RECHECK ... repeated_mismatches=1024 attempts=1024
  ```

  这排除了 `build_symbolic_parallel()` 或 `assemble_numeric_atomic()` 写坏该次数据的
  可能；故障位与前两次正式实验完全一致。

诊断源码与原始输出位于 [`diagnostics`](diagnostics)，汇总见
[`blocker-summary.json`](blocker-summary.json)。

## 恢复条件

继续 Issue #54 前必须先得到稳定的 Windows 主机。建议由用户确认并执行以下系统级操作：

1. 重启主机；
2. 将 CPU 的 PBO/Curve Optimizer、内存超频和降压恢复为主板默认值；
3. 运行可启动介质内存测试或 Windows 内存诊断，确认无错误；
4. 回到同一分支，从全新输出目录重新执行全部 144 个样本。

只有一整次 144/144 样本全部通过、团队规模匹配、无重叠且正确性门禁通过后，才能继续
生成八章中文报告、最终 ZIP 和双工具链 clean-room 结果。
