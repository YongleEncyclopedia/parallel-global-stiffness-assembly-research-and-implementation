# CSC3 Demo 本地验证图表与交付包设计

## 1. 目的与边界

本设计用于把仓库现有的 macOS ARM64 `LOCAL_SMOKE` 证据整理为研究院同事可阅读的
内部技术评估材料，同时补充 CSC3 Demo 核心源码的中文工程化注释。它不生成、替代或
暗示 Linux Intel WindHub 正式性能结论。

固定证据范围如下：

- 算例：生成式 $1\times1\times1$ Tet4 网格；
- 环境：Apple M5、macOS ARM64、OpenMP；
- 请求及实测线程数：$p\in\{1,2\}$；
- 预热次数：$W=1$；
- 正式样本数：$R=2$；
- 摊销次数：$m=2$；
- 证据状态：`LOCAL_SMOKE`；
- 用途：验证并行执行路径、计时字段、报告与打包链路；
- 非用途：评价大规模并行效率、判断 Linux Intel 性能门槛或宣称交付验收 `PASS`。

## 2. 性能图设计

新增一张横向三联图，视觉语言参照用户提供的白底、灰色基线、绿色候选柱、直接数值
标签和底部口径说明，但不复制参考图中的数据或不适用于本 Demo 的内存面板。

三个面板分别为：

1. 符号组装总耗时，单位为 $\mathrm{ms}$，越低越好；
2. 数值组装耗时，定义为清零加原子累加内核，单位为 $\mathrm{ms}$，越低越好；
3. 相对串行基线的阶段加速比，越高越好，并显示 $S=1$ 参考线。

图标题必须包含“本地验证”，副标题必须显示算例、主机、线程范围、$W$、$R$ 和
`NON-FORMAL`。图下方必须明确说明：小算例中线程调度和原子同步开销占主导，当前数据
不能外推到 WindHub 或生产规模。

绘图脚本只从受哈希约束的 `run_manifest.json`、`benchmark_summary.json` 与
`benchmark_samples.csv` 读取数据，重新计算串行中位数、候选中位数和加速比，并拒绝
证据状态、主机描述、线程集合或计时口径不匹配的输入。输出同时包含 PNG 与 SVG；同一
输入重复生成的 SVG 内容必须一致，PNG 必须可打开且尺寸非零。

## 3. 报告设计

新增一份面向交接的中文测试报告，保留现有 canonical local-smoke 报告的算法、环境、
正确性、性能表格和限制说明，并增加：

- 只保留可审计的原始计时表，不在交付报告中展示小算例性能图；
- 计时表前的适用边界说明；
- 串行与并行计时定义；
- 明确指出 $p=2$ 在当前极小算例上变慢；
- 源证据提交与待交付源码提交可能不同的说明；
- Linux Intel/WindHub、许可证和下游求解器集成均不在本报告的完成范围内。

报告使用 Markdown。所有数字必须能够回溯到归档 CSV、JSON 和 manifest，不手工改写
性能结果。生成式 6 单元 Tet4 的计时仅作为并行路径证据，不绘制或打包成性能对比图。

## 4. 中文工程化注释设计

注释覆盖“调用者必须知道的契约”和“维护者必须理解的并行/数值原因”，不做逐行翻译，
也不为显而易见的赋值制造噪声。主要范围为：

- `include/csc3_demo/assembly_helper.h`：公开类型、字段不变量、所有权、异常、状态机和
  线程语义；
- `src/assembly_helper.cpp`：输入规范化、DOF—单元邻接、按列并行模式构造、scatter
  映射、原子累加及强异常安全提交点；
- `tools/include/csc3_demo_tools/{benchmark,evidence}.h`：证据模型、时间字段、统计量、
  正确性误差和性能门槛；
- `tools/src/generated_cases.cpp`：Tet4/Hex8 的材料矩阵、$B$ 矩阵、Jacobian、积分和
  自由度映射；
- `tools/src/validation.cpp`：独立串行参考、稳定范数、自由自由度系统、矩阵/位移误差。

测试夹具、命令行转发和机械 JSON/CSV 序列化不增加大段说明。

## 5. 交付结构

最终生成一个外层 ZIP，内容固定为：

```text
csc3-demo-internal-handoff-v0.2.0+<short-sha>-local-smoke/
├── source/
│   └── csc3-symmetric-assembly-demo-v0.2.0+<short-sha>.zip
├── reports/
│   └── 2026-07-17-csc3-demo-macos-local-smoke-test-report.zh-CN.md
├── verification/
│   ├── manifest-only-verification.json
│   └── clean-room-verification.log
├── DELIVERY_SCOPE.zh-CN.md
└── SHA256SUMS
```

源码 ZIP 继续使用现有确定性 packager 生成，并保持 `INTERNAL EVALUATION ONLY`。
外层 `SHA256SUMS` 覆盖除自身以外的全部文件；交付前在新的临时目录解压并重新执行
校验。外层包不得声称 Linux 正式性能通过或四方正式验收完成。

## 6. 验证策略

- TDD 验证计时数据重算、边界文案、输出路径及报告不含图片链接；
- C++ 注释修改后重新执行 warnings-as-errors 构建与全部 CTest；
- Python 全套测试验证报告、证据和打包契约没有回归；
- 同一提交连续生成两份源码 ZIP，要求字节完全一致；
- 对源码 ZIP 运行 manifest-only 与完整 clean-room 验证；
- 检查最终报告和外层 ZIP 均不含本地小算例性能图；
- 对外层 ZIP 解压后执行 `sha256sum -c SHA256SUMS`。
