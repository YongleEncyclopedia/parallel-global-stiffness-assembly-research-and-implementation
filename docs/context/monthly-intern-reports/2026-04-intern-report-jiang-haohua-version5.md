# 2026年04月实习生汇报：整体刚度矩阵并行组装算法

> AI-readable extraction of an existing monthly intern-report PPTX. The raw PPTX is not copied into this repository.

## Metadata

- Period: `2026-04`
- Source path: `/Users/haohua_jiang/Documents/Intern_Peking University_supu/2026年04月实习生汇报/2026年04月实习生汇报-江浩华_version5.pptx`
- Source role: CPU 多线程主线转向后的汇报版本，包含真实工程网格、算法框架、正确性/效率/内存结果与阶段判断。
- Extracted on: `2026-05-22`
- Slides: `13`
- Slides with speaker notes: `13`
- Embedded media references: `11`

## AI Reading Guide

- Start with the narrative spine below to understand the deck's argument.
- Use the slide table for fast retrieval.
- Use the slide-level sections for exact visible text, speaker notes, and media metadata.
- OCR is best-effort English-only from embedded images; Chinese text in images may not be captured.
- Treat benchmark numbers here as report context; current repository CSV/JSON/result reports remain the source of truth.

## Narrative Spine

- 承接前期 GPU 探索，但明确本月重点转为 CPU 多线程可复现实验和算法对比。
- 先交代实验对象和代码结构，再解释组装原理，避免把图表结果脱离有限元组装流程展示。
- 用真实工程网格 physics_tet4 结果组织证据：正确性、效率和内存占用是三个并列验收维度。
- 从结果回到阶段判断：当前不是只追最高加速比，而是要选出能在真实网格上继续优化的 CPU 算法主线。
- 后续工作落在 row_owner、private_csr、atomic 等实现的性能分析、内存解释和跨平台复现实验。

## Reuse Boundary

- 适合复用为当前仓库 CPU-first 叙事、真实网格实验上下文、图表解释和 mentor/weekly Beamer 的历史来源。
- 图表数值若与仓库 results 目录冲突，以仓库中最新 CSV/JSON/报告为准；本文件负责记录汇报叙事，不替代 benchmark source of truth。

## Project Crosswalk

- 本 deck 的 CPU-first 叙事与当前仓库 README、需求文档和 `cpu_parallel_stiffness_assembly` 主线一致。
- 真实工程网格 `3d-WindTurbineHub.inp`、`physics_tet4`、正确性/效率/内存三维度，对应当前 `results/2026-04-22`、`results/2026-04-28-*` 和后续 2026-05 result reports。
- Slide 12 的阶段判断可作为 2026-04 汇报时刻的决策快照；若与 2026-05 benchmark 或 cross-platform reports 冲突，以后者为准。
- 本 deck 可为 mentor next-steps、weekly meeting Beamer 和 project-long-term-beamer 提供讲述顺序，但不应覆盖最新 source index 中的 result evidence。

## Slide Index

| Slide | Inferred title / claim | Visible content lines | Notes lines | Media |
| ---: | --- | ---: | ---: | ---: |
| 1 | 2026年04月汇报：整体刚度矩阵并行组装算法 | 1 | 2 | 2 |
| 2 | CPU整体刚度矩阵并行组装算法测试 | 1 | 2 | 0 |
| 3 | 项目背景： | 4 | 2 | 1 |
| 4 | 项目背景： | 4 | 2 | 1 |
| 5 | 任务需求： | 10 | 2 | 1 |
| 6 | 实现 serial / atomic / private_csr / coo_sort_reduce / coloring / row_owner | 7 | 2 | 0 |
| 7 | 1.4：组装原理概述 | 2 | 2 | 1 |
| 8 | 1.5：代码结构概述 | 2 | 2 | 1 |
| 9 | 2.1：真实工程网格结果/physics_tet4 | 3 | 2 | 1 |
| 10 | 2.1：真实工程网格结果/physics_tet4 | 3 | 2 | 1 |
| 11 | 2.1：真实工程网格结果/physics_tet4 | 3 | 2 | 1 |
| 12 | 2.3：算法对比与阶段性判断 | 32 | 2 | 0 |
| 13 | 感谢您的指正 | 1 | 2 | 1 |

## Slide-Level Extraction

### Slide 1: 2026年04月汇报：整体刚度矩阵并行组装算法

- Slide XML: `ppt/slides/slide1.xml`
- Notes XML: `ppt/notesSlides/notesSlide1.xml`
- Media count: `2`

#### Visible Text

```text
2026年04月汇报：整体刚度矩阵并行组装算法
报告人：江浩华
合作导师：苏璞
```

#### Speaker Notes

```text
大家好，我是江浩华，目前在苏璞师兄指导下实习。本次汇报的主题是整体刚度矩阵的并行组装算法。简单说，这件事就是在有限元计算里，把大量单元贡献快速、正确地累加到全局刚度矩阵里。
本月我主要把前期 GPU 方向的探索，进一步整理成面向 CPU 多线程的可复现实验和对比结果。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image4.jpeg` | 图片 2 | 1600x501 JPEG | en . Se h th ~ 6 @ § Vs ae ROP aes io / BSS SK SA ee i See / @= eA ay er Sa ad CL (ee, ‘ty, ~ iy, ee ot teat . 5 / i <a / A) = oA 9 ae, Ee Pacis © Ueda be |
| `ppt/media/image2.png` | 图片 4 / 微信图片_20210609194104 | 1721x260 PNG | ey je Z 4.¥ BKARUEHA / <7 om / (GN): LAG K FL PIT / rs 98 PEKING UNIVERSITY CHONGQING RESEARCH INSTITUTE OF BIG DATA |

### Slide 2: CPU整体刚度矩阵并行组装算法测试

- Slide XML: `ppt/slides/slide2.xml`
- Notes XML: `ppt/notesSlides/notesSlide2.xml`

#### Visible Text

```text
CPU整体刚度矩阵并行组装算法测试
2026/4/28
Regular Report
2
```

#### Speaker Notes

```text
这一页是本次汇报的主线：CPU 整体刚度矩阵并行组装算法测试。
后面我会先交代为什么要转到 CPU 这条线，再讲实验对象和算法框架，最后看正确性、效率、内存占用三个维度的结果。
```

### Slide 3: 项目背景：

- Slide XML: `ppt/slides/slide3.xml`
- Notes XML: `ppt/notesSlides/notesSlide3.xml`
- Media count: `1`

#### Visible Text

```text
2026/4/28
Regular Report
3
项目背景：
前期工作：完成多类并行组装算法的调研测试，主要在GPU平台实现。
本月工作：项目目标转向 CPU 算法调研和测试。
1.1：工作概览
```

#### Speaker Notes

```text
先看背景。前一阶段我做的是 GPU 上的算法测试，比如这里 Hex8 单元在 RTX 5080 上能达到接近 98 倍的加速。
这个结果说明 GPU 方向是有潜力的，但也带来一个问题：如果后续要在更多普通工作站和工程流程里复现，CPU 多线程版本也必须有清楚的基线和对比。所以本月的重点就从 GPU-first 调整到 CPU 算法调研和测试。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image5.png` | 图片 1 / 图表, 条形图 / AI 生成的内容可能不正确。 | 2774x1574 PNG | GPU SsAMMERECRTEE (Hex8 57) / (RTX 5080, CUDA 13.1, 2026-01-30 SE3ql)) / 100 - 7.8X ae 9x IM: 97.8. Gpy Baseline (1X) / Mmm GPU Atomic / Mm GPU Block / Mmm «GPU WorkQueue / 80 -... |

### Slide 4: 项目背景：

- Slide XML: `ppt/slides/slide4.xml`
- Notes XML: `ppt/notesSlides/notesSlide4.xml`
- Media count: `1`

#### Visible Text

```text
2026/4/28
Regular Report
3
项目背景：
前期工作：完成多类并行组装算法的调研测试，主要在GPU平台实现。
本月工作：项目主线转向 CPU 并行算法调研和测试。
1.1：工作概览
```

#### Speaker Notes

```text
这一页还是背景，但这里强调的是物理内核。相比简单 kernel，physics_tet4 更接近真实有限元计算，因为它会包含 B 矩阵、D 矩阵以及单元体积这些计算。
也就是说，我们不只关心一个理想化的累加速度，而是想知道在更真实的计算负载下，不同 CPU 并行策略到底还能不能稳定提升。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image6.png` | 图片 8 | 4341x2077 PNG | ~ s . . . . ° / BAK GB . / BERRI / Efficiency Grouped Bars: 3d—WindTurbineHub / physics_tet4 / ft / Configuration / Case: 3d—WindTurbineHub \| Mesh: 3d—WindTurbineHub \| Element: ... |

### Slide 5: 任务需求：

- Slide XML: `ppt/slides/slide5.xml`
- Notes XML: `ppt/notesSlides/notesSlide5.xml`
- Media count: `1`

#### Visible Text

```text
2026/4/28
Regular Report
4
任务需求：
在统一框架下比较正确性、效率和内存占用。
在规则网格与真实工程网格上输出统一 benchmark 结果。
真实工程网格规模：
算例：3d-WindTurbineHub.inp
节点数：228,384
单元数：1,113,684
总自由度：685,152
CSR NNZ：27,502,200
1.2：实验设计
```

#### Speaker Notes

```text
这页讲实验设计。我的目标不是单独跑一个算法，而是在同一个框架下同时比较正确性、效率和内存占用。测试对象里既有规则网格，也有真实工程网格。
重点这个 WindTurbineHub 网格有 22.8 万个节点、111 万个单元、68.5 万个自由度，CSR 非零元达到 2750 万级别，所以它已经不是玩具案例，能比较真实地反映工程规模下的问题。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image7.jpg` | 图片 1 | 2698x1280 JPEG | [E] Viewport: 1 ODB: Y:/CAL/010-Hu_La/008-Indu...del/3d-Win.... [5] (=) ES) \| [2] Viewport: 2. ODB: Y:/CAL/010-Hu_La/008-Indu...del/3d-Win... [5] \|) ES \|\| [2] Viewport: 3 ODB: Y... |

### Slide 6: 实现 serial / atomic / private_csr / coo_sort_reduce / coloring / row_owner

- Slide XML: `ppt/slides/slide6.xml`
- Notes XML: `ppt/notesSlides/notesSlide6.xml`

#### Visible Text

```text
2026/4/28
Regular Report
5
实现 serial / atomic / private_csr / coo_sort_reduce / coloring / row_owner
原子累加：多线程直接写共享 CSR，用 atomic 处理冲突。
线程私有 CSR ：每个线程先写自己的 CSR 副本，最后统一归并。
COO 排序归并：先生成贡献项列表，再排序和归并。
图着色法：先把有写冲突的单元分到不同颜色；同一颜色内可并行写入。
行独占：按矩阵行划分 owner，每个线程只写自己拥有的行。
1.3：算法简述
```

#### Speaker Notes

```text
这里把这次测试的几类 CPU 算法先简单说明一下。serial 是串行基线，后面所有结果都拿它做参考；atomic 是大家一起写同一个 CSR，用原子操作避免冲突；private_csr 是每个线程先写自己的副本，最后归并。
coo_sort_reduce 是先收集贡献项再排序归并；coloring 是用图着色把冲突拆开；row_owner 是每个线程只负责自己拥有的矩阵行。后面结果主要就是比较这些路线的取舍。
```

### Slide 7: 1.4：组装原理概述

- Slide XML: `ppt/slides/slide7.xml`
- Notes XML: `ppt/notesSlides/notesSlide7.xml`
- Media count: `1`

#### Visible Text

```text
1.4：组装原理概述
2026/4/28
Regular Report
7
规则网格/工程网格
```

#### Speaker Notes

```text
这一页解释为什么串行基线很重要。对于每个单元，我们最终都要把局部刚度矩阵的贡献 scatter 到全局 CSR 里。比如 Tet4 单元一次就是 144 个 CSR 累加。
到了真实的 WindTurbineHub 网格，仅 simplified kernel 就有 1.6 亿级别的 scatter 操作。如果换成 physics_tet4，内部计算量还会放大很多。所以先把串行基线做稳，才能知道后面的加速比到底有没有意义。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image8.jpg` | 图片 6 | 1672x941 PNG | o= 2. MN = > / CPU S77BANLES: —TPRERKTSD / STSTHTRSAt / Tet4 S37 Hex8 #7¢ simplified kernel physics_tet4 kernel / = pT - / edofs = 4x3 = 12 edofs = 8x3 = 24 H=e= A 7 ie Ke BBY. ... |

### Slide 8: 1.5：代码结构概述

- Slide XML: `ppt/slides/slide8.xml`
- Notes XML: `ppt/notesSlides/notesSlide8.xml`
- Media count: `1`

#### Visible Text

```text
1.5：代码结构概述
2026/4/28
Regular Report
8
规则网格/工程网格
```

#### Speaker Notes

```text
这页是代码结构。左边是共享的 FEM 基础设施，比如网格输入、CSR 稀疏结构、自由度映射和 scatter plan；中间是统一的 AssemblerFactory 接口，同一个 set_problem、prepare、assemble、compare 流程可以挂不同算法。
右边是正确性测试、benchmark 和结果输出。这样做的好处是，后面比较算法时不是临时脚本互相对比，而是在同一套输入、同一套检查、同一套输出格式下比较。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image9.png` | 图片 7 | 1672x941 PNG | . . . / . / CPU Parallel Global Stiffness Matrix Assembly: Implementation and Test Structure / =_ . = . / SS 1. Shared FEM Infrastructure G 2. AssemblerFactory + \|Assembler inte... |

### Slide 9: 2.1：真实工程网格结果/physics_tet4

- Slide XML: `ppt/slides/slide9.xml`
- Notes XML: `ppt/notesSlides/notesSlide9.xml`
- Media count: `1`

#### Visible Text

```text
2.1：真实工程网格结果/physics_tet4
2026/4/28
Regular Report
9
任务需求：
在统一框架下比较正确性、效率和内存占用。
```

#### Speaker Notes

```text
先看正确性。这张图把各个算法的结果都拿串行 CSR 组装做参考。左边是相对 L2 误差，右边是最大单个矩阵项误差，可以看到误差基本都在 10 的负 16 次方到 10 的负 13 次方这个量级。
也就是说，几种并行写法虽然实现方式不同，但数值结果都只是在浮点舍入误差范围内波动，正确性这一关是过的。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image10.jpg` | 图片 9 | 2560x1440 JPEG | Correctness Comparison / iF WB tEXT EL / Actual WindTurbineHub simplified benchmark; errors are measured against serial CSR assembly / =e Atomic =e PrivateCSR —e= COOSort-Reduce... |

### Slide 10: 2.1：真实工程网格结果/physics_tet4

- Slide XML: `ppt/slides/slide10.xml`
- Notes XML: `ppt/notesSlides/notesSlide10.xml`
- Media count: `1`

#### Visible Text

```text
2.1：真实工程网格结果/physics_tet4
2026/4/28
Regular Report
10
任务需求：
在统一框架下比较正确性、效率和内存占用。
```

#### Speaker Notes

```text
接着看效率。左图是相对串行基线的加速比，灰色虚线代表理想线性加速。实际结果当然达不到理想线，因为有同步、内存访问和写冲突成本。
这里 row_owner 整体最快，最高接近 3.7 倍；private_csr 也比较稳定，atomic 居中，coloring 稍慢；coo_sort_reduce 基本不适合作为主推路线。右图是并行效率，线程数越高效率下降越明显，这也说明后面优化重点要放在内存访问和负载分配上。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image11.jpg` | 图片 9 | 2560x1440 JPEG | Efficiency Comparison / #22 xt EL / Assembly speedup and parallel efficiency over 1-14 CPU threads / =-=- Ideallinear == Atomic =e Private CSR == COO Sort-Reduce == Graph Colori... |

### Slide 11: 2.1：真实工程网格结果/physics_tet4

- Slide XML: `ppt/slides/slide11.xml`
- Notes XML: `ppt/notesSlides/notesSlide11.xml`
- Media count: `1`

#### Visible Text

```text
2.1：真实工程网格结果/physics_tet4
2026/4/28
Regular Report
11
任务需求：
在统一框架下比较正确性、效率和内存占用。
```

#### Speaker Notes

```text
然后看内存占用。左图是算法自己额外申请的内存，atomic 和 graph coloring 基本很轻；private_csr 会随着线程数增加，因为每个线程都有自己的 CSR 缓冲。
coo_sort_reduce 和 row_owner 需要保留比较大的中间缓冲。右图是实际运行时的峰值 RSS，可以看到工程网格下整体内存压力并不小。所以算法选择不能只看速度，还要看它在真实机器上能不能稳定跑起来。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image12.jpg` | 图片 9 | 2560x1440 JPEG | Memory Footprint Comparison / A444 AXEL / Extra algorithmic memory and observed peak RSS across thread counts / =e Atomic =—e— Private CSR =—e=— COO Sort-Reduce =—e— Graph Color... |

### Slide 12: 2.3：算法对比与阶段性判断

- Slide XML: `ppt/slides/slide12.xml`
- Notes XML: `ppt/notesSlides/notesSlide12.xml`

#### Visible Text

```text
2.3：算法对比与阶段性判断
2026/4/28
Regular Report
10
算法路线
最优线程
平均组装时间
加速比
额外内存
当前判断
row_owner
12
106.498 ms
5.352x
1.792 GiB
首推
Private_csr
112.739 ms
5.056x
2.049 GiB
中高线程稳定
主推路线
atomic
127.355ms
4.476x
0
低内存代价
工程性价比高
coloring
14
162.580ms
3.506x
0.008 GiB
保留为重要基线
coo_sort_reduce
13
4222.318ms
0.135x
2.390 GiB
研究对照组
不作主推
3d-WindTurbineHub.inp 网格、physics_tet4 物理四面体内核
```

#### Speaker Notes

```text
最后把 physics_tet4 的阶段判断汇总在这张表里。现在综合来看，row_owner 是首推路线，12 线程下大约 106.5 毫秒，5.35 倍加速；private_csr 稍慢一点，但中高线程表现很稳。
atomic 虽然不是最快，但额外内存为 0，工程性价比很好；coloring 可以保留为重要基线；coo_sort_reduce 正确性没问题，但速度和内存代价都不适合作为主线。
```

### Slide 13: 感谢您的指正

- Slide XML: `ppt/slides/slide13.xml`
- Notes XML: `ppt/notesSlides/notesSlide13.xml`
- Media count: `1`

#### Visible Text

```text
感谢您的指正
```

#### Speaker Notes

```text
我的汇报就到这里。简单总结一下，本月主要完成了 CPU 并行组装的统一测试框架，并且在真实工程网格上完成了正确性、效率和内存占用三方面的对比。
后续我会继续围绕 row_owner、private_csr 和 atomic 做更细的性能分析和优化。谢谢各位老师，也欢迎批评指正。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image4.jpeg` | 图片 1 | 1600x501 JPEG | en . Se h th ~ 6 @ § Vs ae ROP aes io / BSS SK SA ee i See / @= eA ay er Sa ad CL (ee, ‘ty, ~ iy, ee ot teat . 5 / i <a / A) = oA 9 ae, Ee Pacis © Ueda be |
