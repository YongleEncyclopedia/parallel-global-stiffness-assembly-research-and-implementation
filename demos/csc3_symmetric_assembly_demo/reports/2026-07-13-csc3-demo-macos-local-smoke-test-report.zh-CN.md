NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE

# CSC3 并行整体刚度组装测试报告

## 1. 交付验收结论

**DELIVERY ACCEPTANCE: NOT GRANTED (LOCAL_SMOKE)**

- 证据状态：`LOCAL_SMOKE`。
- Demo 版本：`0.2.0`。
- 完整 commit SHA：`25018ba61f15e6505a33d1478000d2a23d3c1803`。
- 分支：`codex/issue-44-csc3-evidence-report`。
- 运行开始时工作树脏状态：`false`。
- 运行 ID：`run-20260713T052322Z-25018ba61f15`。
- 开始 UTC：`2026-07-13T05:23:22Z`。
- 结束 UTC：`2026-07-13T05:23:23Z`。
- `LOCAL_SMOKE` 仅表示本地冒烟证据，不授予交付验收。

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
| OS | `Darwin` |
| 架构 | `arm64` |
| 主机名 | `HaohuaJiang.local` |
| CPU 供应商 / 型号 | `Apple` / `Apple M5` |
| 物理核 / 逻辑核 | 10 / 10 |
| 总内存 | 17179869184 bytes |
| 编译器 | `AppleClang 21.0.0.21000101` |
| 编译器 ID / 版本 | `AppleClang` / `21.0.0.21000101` |
| CMake | `4.4.0` |
| OpenMP required / found / flags | `true` / `true` / `-Xclang -fopenmp` |
| Python | `3.9.6` |
| 受控主机 ID | `无` |
| OpenMP 绑定 | `OMP_DYNAMIC=false`; `OMP_PROC_BIND=close`; `OMP_PLACES=cores` |

## 5. 输入、规模与执行参数

- 输入：`generated-tet4`，网格 $(1,1,1)$。
- 输入文件字节数与 SHA-256：不适用（程序生成，无输入文件）。
- 规模：节点数 `8`，单元数 `6`，DOF 数 `24`，NNZ `219`。
- 请求线程数：`[1, 2]`；观测线程数：`[1, 2]`。
- 热身次数 $W=1$，重复次数 $R=2$，摊销次数 $m=2$。

| 命令 | 已脱敏记录 |
|---|---|
| `configure` | `cmake --preset delivery -B '<host-path>/delivery'` |
| `build` | `cmake --build '<host-path>/delivery' --config Release` |
| `ctest` | `ctest --test-dir '<host-path>/delivery' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'` |
| `benchmark` | `'<host-path>/csc3_demo_benchmark' --case generated-tet4 --threads-list 1,2 --warmup 1 --repeat 2 --amortization-count 2 --evidence-level local-smoke --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --nx 1 --ny 1 --nz 1` |

## 6. 自动测试结果

CTest 精确执行 $9/9$ 个测试：

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

验证后的 JUnit 证据中不存在 failure、error、skip、disabled 或 not-run 条目。

## 7. 整体刚度矩阵正确性

Benchmark 矩阵：结构匹配 `true`，状态 `PASS`，$e_F=0$，$e_{\max}=0$，最大绝对误差容差 `1480.769231`。

| 验证算例 | 节点 | 单元 | DOF | 线程 | 结构 | $e_F$ | $e_{\max}$ | 状态 |
|---|---:|---:|---:|---:|---|---:|---:|---|
| `Tet4` | 8 | 6 | 24 | 2 | `true` | 0 | 0 | `PASS` |
| `Hex8` | 8 | 1 | 24 | 2 | `true` | 0 | 0 | `PASS` |

$$
e_F=\frac{\lVert K_p-K_s\rVert_F}
{\max(\lVert K_s\rVert_F,10^{-30})}\le10^{-8}.
$$

验证阈值为 $e_F\le 1e-08$。

## 8. 位移与残差正确性

| 验证算例 | $e_u$ | 并行 $r_{\mathrm{rel}}$ | 串行 $r_{\mathrm{rel}}$ | $\lVert u_p\rVert_2$ | $\lVert u_s\rVert_2$ | 状态 |
|---|---:|---:|---:|---:|---:|---|
| `Tet4` | 0 | 1.160793663e-15 | 1.160793663e-15 | 3.380943826e-08 | 3.380943826e-08 | `PASS` |
| `Hex8` | 0 | 8.817327136e-16 | 8.817327136e-16 | 4.648916393e-08 | 4.648916393e-08 | `PASS` |

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

- 串行符号阶段中位数：`0.010229` ms。
- 串行数值阶段中位数：`0.0001665` ms。

| 线程 $p$ | 符号中位数 (ms) | 数值中位数 (ms) | 摊销后中位数 (ms) | 符号 $CV$ | 数值 $CV$ | $S_{\mathrm{symbolic}}$ | $S_{\mathrm{numeric}}$ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0065 | 0.0004585 | 0.0043335 | 0.1603076923 | 0.001090512541 | 1.573692308 | 0.3631406761 |
| 2 | 0.0521875 | 0.01725 | 0.04419775 | 0.04511616766 | 0.09907246377 | 0.1960047904 | 0.009652173913 |

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

- 门槛状态：`NOT_APPLICABLE_GENERATED_CASE`；适用：`false`。
- 总体要求满足：`false`；符号要求：`false`；数值要求：`false`。
- 符号选中线程 $p=0$；数值选中线程 $p=0$。
- 阈值：$S_{\mathrm{symbolic}}> 1$，$S_{\mathrm{numeric}}\ge 1.5$，$CV\le 0.05$。
- 本地或生成数据不是正式性能结论；仅已验证的正式 WindHub 证据可支撑交付性能验收。

## 11. 内存证据

- 持久化 vector payload 估算值：`6996` bytes。
- 证据类型：`owned_vector_payload_bytes_not_rss`。
- 该值仅是已拥有 vector 载荷的估算字节数，既不是 RSS，也不是进程内存峰值。

## 12. 限制、风险与授权状态

- blocker：
  - formal controlled-host evidence was not produced
- GitHub runner 时序仅是 CI 冒烟证据，不构成正式性能结论。
- MATLAB、Abaqus 与 COMSOL 不在必须 demo 证据范围内。
- 正式 WindHub 验收必须在受控 Linux Intel 主机上执行。
- 授权状态：`INTERNAL EVALUATION ONLY`。

## 13. 原始证据与复现命令

| 仓库相对 artifact 路径 | 字节数 | SHA-256 |
|---|---:|---|
| `ctest.xml` | 3339 | `417f102f38307f566e6d865c2d8f22c5159e1f36b40d5afd842dcac1125fa814` |
| `benchmark_samples.csv` | 2401 | `81f53aaabdac86bcfbd8d5f8a349113b8a9adf99d97bdf057ad5d54efbd74f66` |
| `benchmark_summary.json` | 10032 | `5551cf9e0f09cb86c1ada694599ebd5ae436925aae6bd814b56ccd1e3de976e9` |
| `summary.md` | 2548 | `7565ee36314064dee0a8eababead5258979df29cd0f8212a9602500591207463` |

| 命令 | 已脱敏记录 |
|---|---|
| `configure` | `cmake --preset delivery -B '<host-path>/delivery'` |
| `build` | `cmake --build '<host-path>/delivery' --config Release` |
| `ctest` | `ctest --test-dir '<host-path>/delivery' -C Release --label-regex ci --output-on-failure --no-tests=error --output-junit '<host-path>/ctest.xml'` |
| `benchmark` | `'<host-path>/csc3_demo_benchmark' --case generated-tet4 --threads-list 1,2 --warmup 1 --repeat 2 --amortization-count 2 --evidence-level local-smoke --samples-csv '<host-path>/benchmark_samples.csv' --summary-json '<host-path>/benchmark_summary.json' --nx 1 --ny 1 --nz 1` |

本报告不在当前运行 manifest 的 artifact 绑定中，以避免自哈希循环；交付打包时由后续 `MANIFEST.sha256` 绑定本报告。

NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE
