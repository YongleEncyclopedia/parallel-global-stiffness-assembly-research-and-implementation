# 执行与二进制 provenance

## 主机与工具链

- 主机：`iWORK`，Ubuntu 24.04.4 LTS，Linux `7.0.0-28-generic`，`x86_64`。
- CPU：Intel Core Ultra 7 265KF，20 个在线逻辑 CPU、20 个物理核心、无 SMT、
  单 NUMA node；CPU 0--7 的 `cpu_capacity` 为 1008 或 1024，CPU 8--19 为
  736，属于异构核心拓扑。
- GCC/G++ 13.3.0，CMake 3.28.3，Ninja 1.11.1，Python 3.11.15，
  GNU `libgomp.so.1`，`_OPENMP=201511`。
- 调速器为 `powersave`，boost 开启。运行中 CPU package 温度抽样为
  $60\text{--}61\,^{\circ}\mathrm{C}$，未观察到热节流信号。
- 这是交互式工作站而非隔离实验机；扫描期间存在桌面应用背景负载。正式结论
  因而同时报告 7 次总体变异系数，并保留这一限制。

## Windows-mirror fresh-process 扫描

源代码来自独立、已跟踪文件干净的 detached worktree：

```text
source SHA = 94cd0d00f1d6725a6af67c8364b4bd07643f1e43
input      = examples/3d-WindTurbineHub.inp
W          = 2
R          = 7
p          = 1,2,...,20
process    = one fresh serialized child per sample
order      = alternating ascending/descending measured rounds
binding    = no OMP_PROC_BIND / OMP_PLACES / GOMP_CPU_AFFINITY / KMP_AFFINITY
```

执行命令的参数化形式为：

```bash
/tmp/csc3-issue44-linux-20260729-venv/bin/python \
  results/2026-07-29-linux-intel-issue-44/scripts/run_linux_process_benchmark.py \
  --repository-root /tmp/csc3-issue44-linux-20260729-formal-source \
  --benchmark-executable /tmp/csc3-issue44-linux-20260729-formal-r2/build/bin/csc3_demo_benchmark \
  --input /tmp/csc3-issue44-linux-20260729-formal-source/examples/3d-WindTurbineHub.inp \
  --out-dir /tmp/csc3-issue44-linux-20260729-fresh-process-unbound \
  --maximum-threads 20 --warmup 2 --repeat 7 \
  --compiler 'GCC 13.3.0' --cmake '3.28.3' --ninja '1.11.1' \
  --openmp-runtime 'GNU libgomp; OpenMP 4.5 (_OPENMP=201511)'
```

运行前及运行中的哈希：

```text
d986f391809b7ebac95b0af8faf21be3bba509ffbdc911055b9b935f503ac9df  csc3_demo_benchmark
b07b415835c1cfaa2bf150384bb60fef4d6a28be9559603e5d60d564840ee575  run_linux_process_benchmark.py
43d9078fa64d74169c8919d105b9dcb129f23f2c821988c827f4eb903bcaabe6  run_windows_process_benchmark.py
```

`readelf -p .comment` 记录编译器为
`GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`；`ldd` 记录可执行文件链接到
`/lib/x86_64-linux-gnu/libgomp.so.1`。

运行前父环境的 `OMP_*`、`GOMP_*`、`KMP_*` 查询为空。运行中从 Linux
`/proc` 读取父 adapter 与一个 $p=14$ 子进程的真实环境：父进程仍为空，子进程
仅包含：

```text
OMP_DYNAMIC=false
OMP_NUM_THREADS=14
OMP_THREAD_LIMIT=14
```

适配器没有实现单样本 timeout；这是长跑操作鲁棒性限制。本次 180 个样本均在
有限时间内正常退出，因此该限制没有造成缺样本或孤儿进程。可执行文件哈希、
动态链接和实时环境是在运行中额外采集的补充证据，原始 adapter manifest 没有
把这三项写入自身 schema。

## 绑核 formal-runner 控制

该控制从干净 detached SHA
`33918620e8689e745db2d81b5f52f659b3207075` 执行，设置：

```text
OMP_DYNAMIC=false
OMP_PROC_BIND=close
OMP_PLACES=cores
threads=1,2,4,8,16,20
warmup=2
repeat=7
amortization-count=1
controlled-host-id=iwork-linux-intel-265kf
```

`formal-bound-control/evidence/run_manifest.json` 保存了完整 configure、build、CTest
和 benchmark 命令，以及三次源码、输入和 host identity 复核。它的自动门禁为
`PASS`。但是规范 runbook 要求 `EXPECTED_SOURCE_SHA` 已合入 `origin/main`；当前
Issue 分支不满足这一前提，所以本控制实验没有生成候选源码包或人工验收记录。
