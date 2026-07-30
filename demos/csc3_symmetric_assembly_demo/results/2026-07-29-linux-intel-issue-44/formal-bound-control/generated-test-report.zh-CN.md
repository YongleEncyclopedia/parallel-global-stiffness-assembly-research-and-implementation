# CSC3 并行整体刚度组装测试报告

## 1. 技术证据门槛与交付状态边界

**TECHNICAL EVIDENCE GATES: PASS**

**DELIVERY ACCEPTANCE: NOT GRANTED (PACKAGE_CANDIDATE; PENDING FOUR-PARTY APPROVAL AND FINALIZATION)**

- 证据状态：`PASS`。
- Demo 版本：`0.2.0`。
- 完整 commit SHA：`33918620e8689e745db2d81b5f52f659b3207075`。
- 分支：`DETACHED`。
- 运行开始时工作树脏状态：`false`。
- 运行 ID：`run-20260729T144353Z-33918620e868`。
- 开始 UTC：`2026-07-29T14:43:53Z`。
- 结束 UTC：`2026-07-29T14:47:36Z`。
- `PASS` 仅表示已验证的正式技术证据门槛通过；四方批准与 finalizer 完成前仍为 `PACKAGE_CANDIDATE`。

## 2. 算法与 CSC3 数据格式

- 对称整体刚度矩阵 $K$ 采用上三角 CSC3 存储；第 $j$ 列仅存储满足 $i\le j$ 的行索 $i$，下三角由对称性隐式给出。
- 确定性符号阶段按列所有权并行：输入归一化 → 构建 DOF-单元邻接 → 并行生成每列候选行 → 排序去重 → 前缀和 → 并行填充行索 → 并行构建 scatter plan。
- 数值阶段使用 OpenMP 按单元并行：每次完整组装先将 $K$ 的数值数组清零，再通过原子 scatter 累加单元矩阵。
- 串行实现仅作为独立正确性参考和性能基线，不是并行实现的 fallback。

## 3. 公共 API 与命名契约

- 公共类型：`ElementDofMap`、`ElementMatrixBatch`、`AssemblyPlan` 与 `SymmetricCscAssembler`。
- 公共操作：`build_symbolic_parallel()` 与 `assemble_numeric_atomic()`。
- 节点、DOF 和 CSC3 索引均从 $0$ 开始；名称后缀使用 `_offsets`、`_count`、`_ms` 和 `_bytes`。
- 代码遵循 C++17 命名与语义；`assemble_numeric_atomic()` 表示完整组装，每次调用必须执行 reset。

## 4. 测试环境与工具链

| 字段 | 值 |
|---|---|
| OS | `Linux` |
| 架构 | `x86_64` |
| 主机名 | `iWORK` |
| CPU 供应商 / 型号 | `GenuineIntel` / `Intel(R) Core(TM) Ultra 7 265KF` |
| 物理核 / 逻辑核 | 20 / 20 |
| 总内存 | 67112595456 bytes |
| 编译器 | `GNU 13.3.0` |
| 编译器 ID / 版本 | `GNU` / `13.3.0` |
| CMake | `3.28.3` |
| OpenMP required / found / flags | `true` / `true` / `-fopenmp` |
| Python | `3.11.15` |
| 受控主机 ID | `iwork-linux-intel-265kf` |
| OpenMP 绑定 | `OMP_DYNAMIC=false`; `OMP_PROC_BIND=close`; `OMP_PLACES=cores` |

## 5. 输入、规模与执行参数

- 输入：WindHub，仓库相对路径 `examples/3d-WindTurbineHub.inp`。
- 输入文件字节数：`76111745`；SHA-256：`4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`。
- 规模：节点数 `228384`，单元数 `1113684`，DOF 数 `685152`，NNZ `14093676`。
- 请求线程数：`[1, 2, 4, 8, 16, 20]`；观测线程数：`[1, 2, 4, 8, 16, 20]`。
- 热身次数 $W=2$，重复次数 $R=7$，摊销次数 $m=1$。

| 命令 | 已脱敏记录 |
|---|---|
| `configure` | `cmake --preset delivery -B '<host-path>/build' '-DPython3_EXECUTABLE:FILEPATH=<host-path>/python'` |
| `build` | `cmake --build '<host-path>/build' --config Release` |
| `ctest` | `ctest --test-dir '<host-path>/build' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'` |
| `benchmark` | `'<host-path>/csc3_demo_benchmark' --case windhub --threads-list 1,2,4,8,16,20 --warmup 2 --repeat 7 --amortization-count 1 --evidence-level formal --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --input '<host-path>/3d-WindTurbineHub.inp'` |

## 6. 自动测试结果

CTest 精确执行 $10/10$ 个测试：

| # | testcase | 状态 |
|---:|---|---|
| 1 | `Csc3DemoTests` | `PASS` |
| 2 | `Csc3DemoConsumer` | `PASS` |
| 3 | `Csc3DemoCorrectness` | `PASS` |
| 4 | `Csc3DemoBenchmarkTiming` | `PASS` |
| 5 | `Csc3DemoBenchmarkEngine` | `PASS` |
| 6 | `Csc3DemoBenchmarkIo` | `PASS` |
| 7 | `Csc3DemoInpCase` | `PASS` |
| 8 | `Csc3DemoWindHubBenchmark` | `PASS` |
| 9 | `Csc3DemoBenchmarkRunner` | `PASS` |
| 10 | `Csc3DemoAtomicContention` | `PASS` |

验证后的 JUnit 证据中不存在 failure、error、skip、disabled 或 not-run 条目。

## 7. 整体刚度矩阵正确性

Benchmark 矩阵：结构匹配 `true`，状态 `PASS`，$e_F=1.511540281e-16$，$e_{\max}=0.0078125$，$\max |K_s|=1.085294536e+13$，$e_{\max,\mathrm{tol}}=108529.4536$。原始字段为 `reference_max_absolute_value`。

| 验证算例 | 节点 | 单元 | DOF | 线程 | 结构 | $e_F$ | $e_{\max}$ | $\max |K_s|$ | $e_{\max,\mathrm{tol}}$ | 状态 |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| `Tet4` | 8 | 6 | 24 | 2 | `true` | 7.98771565e-17 | 3.051757812e-05 | 1.480769231e+11 | 1480.769231 | `PASS` |
| `Hex8` | 8 | 1 | 24 | 2 | `true` | 0 | 0 | 4.935897436e+10 | 493.5897436 | `PASS` |

$$
e_F=\frac{\lVert K_p-K_s\rVert_F}
{\max(\lVert K_s\rVert_F,10^{-30})}\le10^{-8}.
$$

$$
e_{\max,\mathrm{tol}}=10^{-10}+10^{-8}\max |K_s|,
\qquad e_{\max}\le e_{\max,\mathrm{tol}}.
$$

验证阈值为 $e_F\le 1e-08$；最大绝对误差容差由独立串行参考尺度重算。

## 8. 位移与残差正确性

| 验证算例 | $e_u$ | 并行 $r_{\mathrm{rel}}$ | 串行 $r_{\mathrm{rel}}$ | $\lVert u_p\rVert_2$ | $\lVert u_s\rVert_2$ | 状态 |
|---|---:|---:|---:|---:|---:|---|
| `Tet4` | 3.371707456e-16 | 1.858941943e-15 | 1.107062295e-15 | 3.380943826e-08 | 3.380943826e-08 | `PASS` |
| `Hex8` | 0 | 9.086060892e-16 | 9.086060892e-16 | 4.648916393e-08 | 4.648916393e-08 | `PASS` |

$$
e_u=\frac{\lVert u_p-u_s\rVert_2}
{\max(\lVert u_s\rVert_2,10^{-30})}\le10^{-8},
$$

$$
r_{\mathrm{rel}}=
\frac{\lVert K_{ff}u_f-f'_f\rVert_2}
{\max(\lVert f'_f\rVert_2,10^{-30})}\le10^{-10}.
$$

验证阈值为 $e_u\le 1e-08$ 且 $r_{\mathrm{rel}}\le 1e-10$。

这些结果证明从整体刚度组装到线性求解的一致性，不构成与独立商业求解器的验证。

## 9. 性能结果

- 串行符号阶段中位数：`3315.266679` ms。
- 串行数值阶段中位数：`147.846378` ms。
- 串行符号 $CV$：`0.003894206948`。
- 串行数值 $CV$：`0.003782061946`。

| 线程 $p$ | 符号中位数 (ms) | 数值中位数 (ms) | 摊销后中位数 (ms) | 符号 $CV$ | 数值 $CV$ | $S_{\mathrm{symbolic}}$ | $S_{\mathrm{numeric}}$ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3535.76861 | 411.274289 | 4100.445805 | 0.002086128344 | 0.005108925436 | 0.9376367757 | 0.3594836389 |
| 2 | 2273.865323 | 218.033725 | 2645.306301 | 0.001950090399 | 0.009698287002 | 1.457987263 | 0.6780894928 |
| 4 | 1633.638595 | 132.976914 | 1917.48771 | 0.001378838706 | 0.005673110493 | 2.02937583 | 1.111819891 |
| 8 | 1341.325374 | 89.710119 | 1583.791401 | 0.00399627019 | 0.004505469239 | 2.471634954 | 1.648045724 |
| 16 | 1220.716327 | 83.767708 | 1458.181951 | 0.002791685633 | 0.0141660429 | 2.715837091 | 1.764956706 |
| 20 | 1215.324815 | 87.751163 | 1455.531042 | 0.003394321156 | 0.02942527927 | 2.727885285 | 1.684836678 |

### Scatter plan 正确性

- 根级状态：`PASS`；符号 plan 匹配 $54/54$；数值 setup plan 匹配 $6/6$。

| 线程 $p$ | 符号 plan 匹配 / 检查 | 数值 setup plan | 状态 |
|---:|---:|---|---|
| 1 | $9/9$ | `true` | `PASS` |
| 2 | $9/9$ | `true` | `PASS` |
| 4 | $9/9$ | `true` | `PASS` |
| 8 | $9/9$ | `true` | `PASS` |
| 16 | $9/9$ | `true` | `PASS` |
| 20 | $9/9$ | `true` | `PASS` |

$$
S_{\mathrm{symbolic}}(p)=
\frac{T_{\mathrm{symbolic,serial}}}
{T_{\mathrm{symbolic,parallel}}(p)},
\qquad
S_{\mathrm{numeric}}(p)=
\frac{T_{\mathrm{numeric,serial}}}
{T_{\mathrm{numeric,atomic}}(p)}.
$$

$$
T_{\mathrm{numeric,atomic}}(p)=
T_{\mathrm{numeric,reset}}(p)+T_{\mathrm{numeric,kernel}}(p).
$$

$$
T_{\mathrm{amortized}}(p,m)=
\frac{T_{\mathrm{symbolic,parallel}}(p)}{m}
+T_{\mathrm{numeric,total}}(p).
$$

`numeric_total_ms` 是验证后摊销样本使用的完整候选数值 API 时间；数值加速比、数值 $CV$ 与性能门槛使用 reset 加原子 kernel，即 `numeric_algorithm_ms`。

## 10. 性能门槛

- 门槛状态：`PASS`；适用：`true`。
- 总体要求满足：`true`；符号要求：`true`；数值要求：`true`。
- 串行符号 $CV$ 要求：`true`；串行数值 $CV$ 要求：`true`；scatter 要求：`true`；正式总要求：`true`。
- 符号选中线程 $p=2$；数值选中线程 $p=8$。
- 阈值：$S_{\mathrm{symbolic}}> 1$，$S_{\mathrm{numeric}}\ge 1.5$，$CV\le 0.05$。
- 本地或生成数据不是正式性能结论；仅已验证的正式 WindHub 证据可支撑交付性能验收。

## 11. 内存证据

- 持久化 vector payload 估算值：`945274680` bytes。
- 证据类型：`owned_vector_payload_bytes_not_rss`。
- 该值仅是已拥有 vector 载荷的估算字节数，既不是 RSS，也不是进程内存峰值。

## 12. 限制、风险与授权状态

- blocker：无。
- GitHub runner 时序仅是 CI 冒烟证据，不构成正式性能结论。
- MATLAB、Abaqus 与 COMSOL 不在必须 demo 证据范围内。
- 正式 WindHub 验收必须在受控 Linux Intel 主机上执行。
- 授权状态：`INTERNAL EVALUATION ONLY`。

## 13. 原始证据与复现命令

| 仓库相对 artifact 路径 | 字节数 | SHA-256 |
|---|---:|---|
| `ctest.xml` | 3572 | `3e96b6deb970ede559f58d1093e92cf15def4ae68066fb4f5b4ad9571fa12ac8` |
| `benchmark_samples.csv` | 20716 | `e3b58b6cd6da6ca8e97d3df5a463bb08875b1d463e1ea897450bc9e9cfaca8cc` |
| `benchmark_summary.json` | 33515 | `c9823d05e83b24990cc87ef7f6dded8f1e691305aa26cc6db72660940bdb0c49` |
| `summary.md` | 3133 | `a9c7d00d1911159c691148d9fc7079963b8e6b8cce23f5dfdf0852e6c5fecfd5` |

| 命令 | 已脱敏记录 |
|---|---|
| `configure` | `cmake --preset delivery -B '<host-path>/build' '-DPython3_EXECUTABLE:FILEPATH=<host-path>/python'` |
| `build` | `cmake --build '<host-path>/build' --config Release` |
| `ctest` | `ctest --test-dir '<host-path>/build' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'` |
| `benchmark` | `'<host-path>/csc3_demo_benchmark' --case windhub --threads-list 1,2,4,8,16,20 --warmup 2 --repeat 7 --amortization-count 1 --evidence-level formal --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --input '<host-path>/3d-WindTurbineHub.inp'` |

本报告不在当前运行 manifest 的 artifact 绑定中，以避免自哈希循环；交付打包时由后续 `MANIFEST.sha256` 绑定本报告。
