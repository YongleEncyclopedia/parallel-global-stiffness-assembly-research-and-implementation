# 线程私有 CSR 实验导师复现包交付记录

关联 Issue：[#58](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/58)

## 交付结果

已在 2026-07-28 整理出一份课题组内部使用的导师复现包：

```text
线程私有CSR实验_导师复现材料_2026-07-08_2026-07-10.zip
```

- 文件大小：23,029,628 bytes；
- SHA-256：`7aa5dc8cde426b8956eb20f873f1f442d97ff5195483cf0263faaae61ce5bed3`；
- 包内普通文件：228 个，其中 226 个实质文件进入内部 SHA-256 清单，
  另外 2 个文件是清单本身；
- 当前本地输出路径：
  `/Users/macbook_prom5/Desktop/线程私有CSR实验_导师复现材料_2026-07-08_2026-07-10.zip`。

压缩包没有提交进仓库。这样既避免重复纳入 76,111,745 bytes 的工程网格，
也避免在尚未确认网格公开发行授权时把内部复现材料当作公共发布件。

## 日期与来源

沟通中曾把这轮实验称为“2026 年 7 月 20 日实验”。仓库实际证据链是：

- 2026-07-08：Linux Intel 五后端、\(p=1,\ldots,20\) 线程的原始实验；
- 2026-07-10：根据上述 summary CSV 生成正式图表与说明；
- 2026-07-28：整理注释版源码、复现说明和导师交付 ZIP。

仓库中没有能够支持“2026-07-20”这一日期的原始日志，因此交付包保留真实
日期，没有为了贴合口头记忆而重命名证据。

实验运行记录中的 Git 提交为：

```text
9c8568c47c749e903a213c8392359819d3e63c2b
```

运行机器当时另有一行未提交的 `<cmath>` include。它随后和原始结果一起
进入归档提交：

```text
03aa53eb066180a622c2ad72735bb20fa69520d1
```

因此，导师包中的完整、可构建 CPU 源码从 `03aa53e...` 提取。本次只给关键
实验链路增加中文工程注释，没有改动算法语句、常量、循环、条件、CLI、
schema 或输出字段。

## 包内结构

| 目录 | 内容 |
| --- | --- |
| `00_请先阅读` | 证据日期、阅读顺序、实验设计、主要结果和复现命令 |
| `01_实验源码_中文注释版` | 历史有效源码快照与中文注释，能够独立配置、构建和运行 13 个测试 |
| `02_实验运行代码_中文注释版` | 隔离进程 runner 的单独副本，文件头详细解释实验设计 |
| `03_绘图代码` | 正式绘图脚本与 `matplotlib==3.10.8` 固定依赖 |
| `04_原始证据_2026-07-08` | 303 条逐次记录、101 条中位数汇总、JSON、命令和平台信息 |
| `05_图表与图表数据_2026-07-10` | 正式 PNG/SVG/PDF、逐图输入行和线程覆盖审计 |
| `06_实际工程网格` | materialize 后的 WindHub Abaqus `.inp` 网格 |
| `07_验证记录与校验值` | 验证脚本、完整检查记录、文件清单和包内 SHA-256 |

## 关键结果

线程私有 CSR 在 \(p=7\) 时达到本轮最低总耗时
\(t_{\mathrm{total}}=1.711228\ \mathrm{s}\)，整体加速比为 \(2.456\)。
当线程数增加到 \(p=20\) 时：

- \(t_{\mathrm{total}}\) 回升到 \(2.578190\ \mathrm{s}\)；
- 后端准备时间增加到 \(1.338267\ \mathrm{s}\)；
- 实测进程峰值内存增加到 \(7.683605\ \mathrm{GiB}\)；
- 整体加速比下降到 \(1.630\)。

代码显示每个线程保存一份完整 CSR values，额外容量近似为

$$
M_{\mathrm{private}}
=T N_{\mathrm{nz}}\mathrm{sizeof}(\mathrm{Real}).
$$

因此，分配、两次清零、逐非零元归并和数据搬运会随线程数增加。原实验没有
采集内存带宽或末级缓存 miss，故这里只把缓存容量和内存流量压力列为有
代码依据的机制解释，不写成硬件计数器已经证明的结论。

## 验证

### 注释等价性

- 3 个关键 C++ 翻译单元在 `clang++ -E -P` 后，原始版与注释版 SHA-256
  分别一致；
- Python runner 去掉注释和换行后均为 4304 个有效 token，序列完全一致。

### 构建与测试

```bash
cmake -S <导师包>/01_实验源码_中文注释版 \
  -B build/issue-58-mentor-handoff/annotated-build \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON \
  -DBUILD_TESTS=ON \
  -DBUILD_BENCHMARKS=ON

cmake --build build/issue-58-mentor-handoff/annotated-build --parallel

ctest \
  --test-dir build/issue-58-mentor-handoff/annotated-build \
  --output-on-failure
```

结果：配置 `PASS`，37 个构建步骤 `PASS`，13/13 测试 `PASS`。

### runner 冒烟

在内置 \(2\times2\times2\) 小网格上检查串行基线与线程私有 CSR 的
\(p=1,2\)。汇总得到 3 行记录，`run_status` 和
`matrix_correctness_status` 均为 `PASS`。

### 证据与网格

```bash
python3 07_验证记录与校验值/validate_evidence.py
shasum -a 256 -c 07_验证记录与校验值/SHA256SUMS
```

结果：

- 303 条原始记录和 101 条汇总记录通过数量、线程覆盖和正确性检查；
- 逐条复核
  \(t_{\mathrm{numeric}}=t_{\mathrm{prepare}}+t_{\mathrm{assembly}}\)
  与
  \(t_{\mathrm{total}}=t_{\mathrm{symbolic}}+t_{\mathrm{numeric}}\)；
- 线程私有绘图行逐字段匹配 summary CSV；
- WindHub 网格 SHA-256 为
  `4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3`，
  且不是 Git LFS pointer。

### 制图复现

正式 PNG 元数据记录 Matplotlib 3.10.8。固定到同一版本后重绘：

- 6 份线程趋势 CSV 的解析结果全部相同；
- 线程私有 CSR PNG 同为 \(3072\times1728\) pixels；
- 解码后的 RGB 像素逐像素相同，三个通道平均绝对差均为 0。

### ZIP 干净环境复验

ZIP 以 UTF-8 文件名标志重新生成，290 个目录或文件条目中的全部非 ASCII
路径均带 UTF-8 标志。压缩包解压到新的临时目录后重新执行：

- ZIP CRC：`PASS`；
- 包内 226 个实质文件 SHA-256：`PASS`；
- 证据验证脚本：`PASS`；
- 从零 CMake 配置与完整构建：`PASS`；
- CTest：13/13 `PASS`；
- 固定 Matplotlib 版本重绘：数值行一致，线程私有图像素一致。

## 校验最终 ZIP

在 ZIP 所在目录执行：

```bash
shasum -a 256 \
  线程私有CSR实验_导师复现材料_2026-07-08_2026-07-10.zip
```

结果应为 `SHA256SUMS` 中记录的值。

## 边界与回滚

- 当前 macOS 验证只证明代码可构建、测试和贯通，不替代原 Linux Intel
  性能实验；
- 包中没有新增硬件计数器证据；
- 网格和整个 ZIP 仅用于课题组内部研究及导师复核；
- 若撤回本次仓库记录，只需回退本目录；外部 ZIP 独立删除即可，不影响
  原始 `results/`、正式 `reports/2026-07-10-*` 或算法源码。
