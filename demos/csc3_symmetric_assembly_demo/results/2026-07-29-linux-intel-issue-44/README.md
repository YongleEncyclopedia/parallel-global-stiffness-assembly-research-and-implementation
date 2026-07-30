# 2026-07-29 Linux Intel WindHub 加速比复现证据

本目录是 Issue #44 在物理 Linux Intel 主机 `iWORK` 上生成的原始证据与派生
分析。结论使用 `3d-WindTurbineHub.inp`，不得外推到其他网格、单元类型、NUMA
拓扑或 OpenMP runtime。

## 证据分层

- `fresh-process-unbound/`：与 Windows Issue #54 相同的独立进程口径。线程数为
  $p=1,2,\ldots,20$，预热 $W=2$，正式重复 $R=7$；每个样本启动一个新进程，
  样本串行执行，正式轮次交替升序和降序；不显式设置线程绑定。
- `analysis/`：从 Linux 140 个 measured 样本与 Windows 112 个 measured 样本
  独立复算得到的统计和阶段比较。`analysis_summary.json` 同时记录 Windows 阶段
  raw CSV 的路径、大小和 SHA-256。
- `formal-bound-control/evidence/`：在干净 detached Issue 分支提交上，由仓库
  formal runner 生成的绑核控制实验。线程数为
  $p\in\{1,2,4,8,16,20\}$，并设置 `OMP_PROC_BIND=close`、
  `OMP_PLACES=cores`。该 runner 证据为 `PASS`，但提交尚未合入 `origin/main`，
  因此它不是规范 runbook 的 `PACKAGE_CANDIDATE`，也不代表四方正式验收完成。
- `formal-attempts/`：四次失败尝试的原始 manifest、JUnit 和必要的配置证据。
  这些失败推动了 Python 解释器绑定和测试夹具修复，不能被表述为通过。
- `scripts/`：本次 Linux 独立进程适配器和 Linux/Windows 交叉分析器。

## 数据身份

- Windows-mirror 源码 SHA：
  `94cd0d00f1d6725a6af67c8364b4bd07643f1e43`。
- 绑核控制源码 SHA：
  `33918620e8689e745db2d81b5f52f659b3207075`。
- WindHub SHA-256：
  `4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`。
- WindHub 大小：`76,111,745` bytes。
- 算例规模：228,384 个节点、1,113,684 个 Tet4、685,152 个自由度、
  14,093,676 个 CSC3 非零元。

顶层 `SHA256SUMS` 覆盖本目录最终归档的全部普通文件；各实验 manifest 继续承担
其自身 artifact 的相对路径、大小和 SHA-256 绑定。
