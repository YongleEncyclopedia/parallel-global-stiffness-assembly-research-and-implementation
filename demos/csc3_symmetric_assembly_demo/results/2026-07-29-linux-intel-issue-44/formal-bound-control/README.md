# 绑核 formal-runner 控制实验

本目录来自干净 detached SHA
`33918620e8689e745db2d81b5f52f659b3207075`。自动 technical evidence gate、
configure、build、10 项 CTest、WindHub benchmark、正确性和 scatter gate 均为
`PASS`。

控制条件为 `OMP_DYNAMIC=false`、`OMP_PROC_BIND=close`、
`OMP_PLACES=cores`，线程集 $p\in\{1,2,4,8,16,20\}$，预热 $W=2$，
正式重复 $R=7$，摊销次数 $m=1$。

## 结果摘要

由 `benchmark_samples.csv` 的 measured 行复算：

| $p$ | 完整候选总时间中位数 / ms | 总时间总体 $CV$ | 独立串行口径加速 | candidate $p=1\to p$ 加速 |
|---:|---:|---:|---:|---:|
| 1 | 4100.446 | 0.213% | 0.844 | 1.000 |
| 8 | 1583.791 | 0.342% | 2.186 | 2.589 |
| 16 | 1458.182 | 0.254% | 2.375 | 2.812 |
| 20 | 1455.531 | 0.372% | 2.379 | 2.817 |

独立串行完整总时间中位数为 3462.528 ms。$p=20$ 时 `symbolic_total_ms`
中位数为 1215.325 ms，`numeric_total_ms` 为 242.289 ms；未分项 residual 合计
中位数为 743.898 ms，占完整候选总时间的 51.197%。

仓库正式性能 gate 使用的数值口径不是完整 `numeric_total_ms`，而是独立串行
`reset + kernel` 对候选 `reset + atomic kernel`。该 gate 在 $p=8$ 首次达到
$1.5\times$，符号 gate 在 $p=2$ 首次超过 $1\times$，所有被引用配置的
$CV\le5\%$。

## 状态边界

`generated-test-report.zh-CN.md` 是报告生成器对 technical evidence 的规范输出，
其中的自动状态语义来自 runner manifest。完整 Linux runbook 另有
“源码 SHA 已合入 `origin/main`”的前置门禁；本次 Issue 分支尚未合入主线，也未
执行候选包生成、四方人工确认或 finalizer。因此本目录只能作为绑核控制实验，
不能对外宣称已经取得最终交付验收或规范 runbook `PACKAGE_CANDIDATE`。
