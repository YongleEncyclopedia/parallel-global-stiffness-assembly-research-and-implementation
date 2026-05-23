# 2026年01月实习生汇报（兼年终总结）：并行组装整体刚度矩阵算法调研及实现

> AI-readable extraction of an existing monthly intern-report PPTX. The raw PPTX is not copied into this repository.

## Metadata

- Period: `2026-01`
- Source path: `/Users/haohua_jiang/Documents/Intern_Peking University_supu/2026年01月实习生汇报/2026年01月实习生汇报-江浩华.pptx`
- Source role: GPU/CPU 并行组装前期问题定义、算法调研和早期原型材料。
- Extracted on: `2026-05-22`
- Slides: `26`
- Slides with speaker notes: `20`
- Embedded media references: `26`

## AI Reading Guide

- Start with the narrative spine below to understand the deck's argument.
- Use the slide table for fast retrieval.
- Use the slide-level sections for exact visible text, speaker notes, and media metadata.
- OCR is best-effort English-only from embedded images; Chinese text in images may not be captured.
- Treat benchmark numbers here as report context; current repository CSV/JSON/result reports remain the source of truth.

## Narrative Spine

- 从自研有限元软件的整体刚度矩阵组装效率瓶颈切入：串行组装、COO 到 CSR 转换、缺少硬件平台优化。
- 把并行组装拆成可比较的算法族：图着色法、直接累加/Addto/原子操作、区域分解/线程私有或子域策略。
- 用有限元组装流程解释为什么写入冲突和稀疏矩阵存储格式是核心矛盾。
- 沉淀早期实现思路：先用相对小的原型验证正确性、冲突规避和 OpenMP/CPU 并行可行性。
- 报告后段切到 ANSYS APDL 仿真案例，属于同期实习内容，但不是当前 CPU 组装主线的主要技术来源。

## Reuse Boundary

- 适合复用为项目背景、研究动机、算法族 taxonomy 和从 GPU/原型向 CPU 主线迁移的历史依据。
- 不应直接复用其中的早期性能判断作为当前结论；当前仓库的 benchmark 和 2026-04/05 结果优先级更高。

## Project Crosswalk

- `docs/requirements/cpu-parallel-stiffness-assembly-design.md` 的研究背景部分已经引用这份 2026-01 月报；本文件是它的逐页来源补全。
- 图着色法对应当前 `coloring` backend；Addto/直接累加对应当前 `atomic` 类路线；区域分解/私有缓冲思想对应当前 `private_csr`、`row_owner` 等 CPU 主线实现。
- GPU slides 属于历史探索和对比背景；当前仓库范围仍以 CPU 并行组装和可复现实验平台为主。
- ANSYS APDL 案例只说明同期实习工作量，不应进入当前 CPU benchmark 结论链。

## Slide Index

| Slide | Inferred title / claim | Visible content lines | Notes lines | Media |
| ---: | --- | ---: | ---: | ---: |
| 1 | 2026年01月汇报（兼年终总结）： | 2 | 0 | 2 |
| 2 | Task1：并行组装整体刚度矩阵 | 2 | 0 | 0 |
| 3 | 任务需求：自研软件在整体刚度矩阵组装效率上与主流商软存在较大差距 | 7 | 2 | 0 |
| 4 | CPU并行：凭借大容量缓存优势适配 Addto算法（直接累加法），有效缓解随机访存延迟，但在高并发下扩展性受限于内存带宽瓶颈，适合中等规模计算。 | 3 | 3 | 2 |
| 5 | 图着色法 (Graph Coloring)：基于图论将单元分组，同色组内单元互不共享节点，分批次并行执行。 | 5 | 1 | 0 |
| 6 | 图着色 (Graph Coloring)：如果两个单元被染成相同的颜色，则它们一定不共享任何节点，因此可以安全地并行处理。程序采用的是 贪心首次适应算法 (Greedy First-Fit Algorithm) 。 | 7 | 2 | 3 |
| 7 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 8 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 9 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 10 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 11 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 12 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 2 | 1 |
| 13 | 1.3：在多核CPU平台上的并行组装策略 | 1 | 1 | 1 |
| 14 | 1.4：在众核GPU平台上的并行组装策略 | 8 | 0 | 0 |
| 15 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 1 | 2 |
| 16 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 1 | 1 |
| 17 | 1.4：在众核GPU平台上的并行组装策略 | 8 | 1 | 0 |
| 18 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 1 | 1 |
| 19 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 1 | 1 |
| 20 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 1 | 1 |
| 21 | 1.4：在众核GPU平台上的并行组装策略 | 1 | 0 | 1 |
| 22 | Task2：Ansys APDL仿真案例 | 2 | 0 | 0 |
| 23 | 2026/1/30 | 0 | 1 | 2 |
| 24 | 2026/1/30 | 0 | 1 | 1 |
| 25 | 2026/1/30 | 0 | 1 | 1 |
| 26 | 感谢您的指正 | 1 | 0 | 1 |

## Slide-Level Extraction

### Slide 1: 2026年01月汇报（兼年终总结）：

- Slide XML: `ppt/slides/slide1.xml`
- Notes XML: `ppt/notesSlides/notesSlide1.xml`
- Media count: `2`

#### Visible Text

```text
2026年01月汇报（兼年终总结）：
并行组装整体刚度矩阵算法调研及实现
报告人：江浩华
合作导师：苏璞
```

#### Speaker Notes

```text
None extracted.
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image4.jpeg` | 图片 2 | 1600x501 JPEG | en . Se h th ~ 6 @ § Vs ae ROP aes io / BSS SK SA ee i See / @= eA ay er Sa ad CL (ee, ‘ty, ~ iy, ee ot teat . 5 / i <a / A) = oA 9 ae, Ee Pacis © Ueda be |
| `ppt/media/image2.png` | 图片 4 / 微信图片_20210609194104 | 1721x260 PNG | ey je Z 4.¥ BKARUEHA / <7 om / (GN): LAG K FL PIT / rs 98 PEKING UNIVERSITY CHONGQING RESEARCH INSTITUTE OF BIG DATA |

### Slide 2: Task1：并行组装整体刚度矩阵

- Slide XML: `ppt/slides/slide2.xml`

#### Visible Text

```text
Task1：并行组装整体刚度矩阵
算法调研及初步实现
2026/1/30
Regular Report
2
```

#### Speaker Notes

```text
None extracted.
```

### Slide 3: 任务需求：自研软件在整体刚度矩阵组装效率上与主流商软存在较大差距

- Slide XML: `ppt/slides/slide3.xml`
- Notes XML: `ppt/notesSlides/notesSlide2.xml`

#### Visible Text

```text
2026/1/30
Regular Report
3
任务需求：自研软件在整体刚度矩阵组装效率上与主流商软存在较大差距
效率瓶颈：
自研软件采用串行算法组装整体刚度矩阵，而主流商软均可通过并行技术加速
自研软件在组装整体刚度矩阵时需转换稀疏存储格式，通常会经历 “COO (中间态) → 转换→ CSR (最终态)” 的过程，由此带来额外计算开销
自研软件没有针对不同硬件平台做整体刚度矩阵组装算法优化
初步目标：设计高效的并行算法
1.1 背景：自研求解器与商软的组装效率差距
```

#### Speaker Notes

```text
我是25年9月进入现在的实习生管理模式的，最早在9.18号联系上了带教的苏璞师兄。
今天我想先汇报一下从12月开始做的一类任务，即“并行组装整体刚度矩阵”。这个任务的需求是，目前自研有限元软件在整体刚度矩阵组装的效率上与主流商业有限元软件存在较大的差距。这一方面是由于自研软件没有像主流商软那样通过并行技术加速组装过程；另一方面是因为自研软件在组装（Assembly）环节需要经历稀疏存储格式的转换，这一步同样带来内存和时间的开销；当然还有其他可以优化的问题，例如采用工业界普遍的做法，针对不同硬件平台做算法优化。
```

### Slide 4: CPU并行：凭借大容量缓存优势适配 Addto算法（直接累加法），有效缓解随机访存延迟，但在高并发下扩展性受限于内存带宽瓶颈，适合中等规模计算。

- Slide XML: `ppt/slides/slide4.xml`
- Notes XML: `ppt/notesSlides/notesSlide3.xml`
- Media count: `2`

#### Visible Text

```text
2026/1/30
Regular Report
4
CPU并行：凭借大容量缓存优势适配 Addto算法（直接累加法），有效缓解随机访存延迟，但在高并发下扩展性受限于内存带宽瓶颈，适合中等规模计算。
GPU并行：利用高带宽显存适配 Warp聚合原子操作，通过海量线程掩盖访存延迟，适合在超大规模网格上实现高吞吐量加速。
1.2：中央处理器（CPU）及图形处理器（GPU）
```

#### Speaker Notes

```text
现代个人操作系统最主要的硬件平台就是CPU和GPU，他们均可用于并行计算，但GPU 与 CPU 的设计目标存在本质差异。其中CPU 旨在以最快速度执行串行操作序列，也称为线程，并可并行执行数十个此类线程，倾向于将更多晶体管用于数据缓存与流程控制；而 GPU 则专为并行执行数千个线程而设计，通过适度降低单线程性能来实现更高的整体吞吐量，其专为高度并行计算优化，会将更多晶体管资源分配给数据处理单元。
右图展示了不同处理器对于自由度的存储方式，顶部：一个二维域分解为三个元素；底部：节点数据布局；右侧：图形处理器实现中的节点数据布局。通过线程
访问不同单元中的数据（以箭头标示）实现了数据合并访问优化。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image5.png` | 图片 6 / 图形用户界面, 图表 / AI 生成的内容可能不正确。 | 1612x796 PNG | Core Con Core Con / trol iige)\| / L1 Cache L1 Cache / Core Con Core Con / trol iige)\| / L1 Cache L1 Cache / L2 Cache L2 Cache / L3 Cache / L2 Cache / DRAM DRAM / CPU GPU |
| `ppt/media/image6.png` | 图片 8 / 图表 / AI 生成的内容可能不正确。 | 678x299 PNG | - |

### Slide 5: 图着色法 (Graph Coloring)：基于图论将单元分组，同色组内单元互不共享节点，分批次并行执行。

- Slide XML: `ppt/slides/slide5.xml`
- Notes XML: `ppt/notesSlides/notesSlide4.xml`

#### Visible Text

```text
2026/1/30
Regular Report
5
图着色法 (Graph Coloring)：基于图论将单元分组，同色组内单元互不共享节点，分批次并行执行。
在早期硬件性能不足（特别是缺乏高效硬件原子操作支持）的阶段，图着色法是多核CPU（以及早期GPU）上并行组装整体刚度矩阵的主流和通用策略。
直接累加法 (Addto / Atomics)：线程按单元自然顺序计算，利用CPU硬件原子指令解决累加冲突。
区域分解法 (Domain Decomposition)：将网格划分为若干子区域，核心处理内部节点无冲突，仅在边界（Ghost Layer）进行同步/通信。
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
这一页内容展示了多核CPU平台下并行组装整体刚度矩阵的主流算法，在不支持高效硬件原子操作的早期平台，从硬件层规避写入冲突的技术尚不成熟，软件层的着色调度成为并行组装算法最主要的策略。
```

### Slide 6: 图着色 (Graph Coloring)：如果两个单元被染成相同的颜色，则它们一定不共享任何节点，因此可以安全地并行处理。程序采用的是 贪心首次适应算法 (Greedy First-Fit Algorithm) 。

- Slide XML: `ppt/slides/slide6.xml`
- Notes XML: `ppt/notesSlides/notesSlide5.xml`
- Media count: `3`

#### Visible Text

```text
2026/1/30
Regular Report
6
图着色 (Graph Coloring)：如果两个单元被染成相同的颜色，则它们一定不共享任何节点，因此可以安全地并行处理。程序采用的是 贪心首次适应算法 (Greedy First-Fit Algorithm) 。
对有限元网格进行着色
数学定义 ：
将有限元网格抽象为一个无向图 ，其中：
顶点（Vertex） ：代表每个有限元单元（Element）。
边（Edge） ：如果两个单元 和  共享至少一个物理节点，则它们之间存在一条边。
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
图着色的基本原理可以用顶点和边的概念解释。左图展示了基于三色策略的极大独立集划分，相邻顶点颜色互异，形成红、蓝、绿三个无连接边的独立集；在并行刚度矩阵组装中，同色顶点代表无数据依赖的自由度或单元；
右图展示了基于四色定理的区域分区结果，地理邻接区域标记为不同颜色，确保共享边界的相邻子域颜色互异；在并行组装流程中，按颜色批次串行处理，同颜色区域内部的所有单元可同步计算局部刚度并直接累加至全局矩阵
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image8.png` | 图片 6 / 图片包含 游戏机 / AI 生成的内容可能不正确。 | 500x309 PNG | - |
| `ppt/media/image9.png` | 图片 7 / 图表 / AI 生成的内容可能不正确。 | 500x488 PNG | - |
| `ppt/media/image7.png` | - | 1805x439 PNG | > 26 (Graph Coloring): WR NEATH RAGE, Wei—ERSHOIDA, / AbD WURSHHTUe, ESRAWS SOS RISMSIS (Greedy First-Fit / Algorithm) . / WA TMBHiTaE / > AEM: / SA RCMhRA—TAME G = (V,£), Br: /... |

### Slide 7: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide7.xml`
- Notes XML: `ppt/notesSlides/notesSlide6.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
7
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
这是在多核CPU平台使用图着色法简单实现并行组装整体刚度矩阵的程序代码文件夹，为简单起见，程序采用了贪心首次适应算法 (Greedy First-Fit Algorithm)，这类方法并不总能采取最少的颜色分组，但是效率很高。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image10.png` | 图片 11 | 1044x1036 PNG | eK - enceE ag Kun / 50 .ace-tool 2026/1/30 11:51 SESE / 50 claude 2026/1/30 11:51 SESE / bu git 2026/1/30 11:49 SCE / 501 .spec-workflow 2026/1/30 11:49 SUSE / 50 backup 2026/1/... |

### Slide 8: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide8.xml`
- Notes XML: `ppt/notesSlides/notesSlide7.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
8
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
量化地来讲，我设置了30 组基准测试，覆盖 6 种网格规模（900~2700万节点），生成 10 张结果可视化图表，其他量化指标如图所示。接下来我选取一些有代表性的结果进行展示
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image11.png` | 图片 8 / 图形用户界面, 应用程序 / AI 生成的内容可能不正确。 | 4363x1547 PNG | FEM Parallel Assembly - Project Highlights / KASS: 4,248 iF RAL FEAR FHTMIRWER (FR=3.56x) / 4.5 / C++ 4.0 / 3.5 / 7 1 30 3.0 2.9X / BEES Mit A HI 49 2.5 / ry 2.2xX / F200 / 10 4... |

### Slide 9: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide9.xml`
- Notes XML: `ppt/notesSlides/notesSlide8.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
9
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
首先是程序对网格构建单元邻接图
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image12.png` | 图片 7 / 图示, 表格 / AI 生成的内容可能不正确。 | 4951x4449 PNG | Element Adjacency Graph Construction Algorithm / 4 + AM f52 Ex eS > / FBLC VF ta BK / Step 0: Original Mesh Step 1: Build Node~Element Mapping Example: Node 5 / Inge TS #3275 A ... |

### Slide 10: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide10.xml`
- Notes XML: `ppt/notesSlides/notesSlide9.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
10
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
构建完成后，我们就可以采用具体的贪心算法对网格进行着色
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image13.png` | 图片 5 / 图示 / AI 生成的内容可能不正确。 | 4709x4823 PNG | Greedy First-Fit Graph Coloring Algorithm / AS . = Acie Ss / @bFirst-Fith ae St / Algorithm Pseudocode Key Properties / BAAR Ke Tt / def greedy coloring(adjacency) : Greedy Colo... |

### Slide 11: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide11.xml`
- Notes XML: `ppt/notesSlides/notesSlide10.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
11
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
单元分组之后，在硬件层面就可以安全地并行组装，其过程可以抽象成上图所示，每个核心分配到的任务并不总是均衡的，总的求解时间取决于木桶效应
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image14.png` | 图片 6 / 图片包含 图示 / AI 生成的内容可能不正确。 | 4709x3950 PNG | Parallel FEM Assembly with Graph Coloring / T Ala @ Ft BR 2B / aT HFT A BRIT ZB / Complete Workflow / 322 Lititz / Mesh Build Graph Symbolic Parallel / Generation Adjacency Colo... |

### Slide 12: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide12.xml`
- Notes XML: `ppt/notesSlides/notesSlide11.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
12
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
接下来我们看一下具体的并行效果。
首先是计算耗时，可以看到在单元规模增加后，多核耗时要显著地低于少核耗时，但这种效率提升并不是线性增长的，随着核心数量增长到8核左右，这种提升会趋缓，推测是由于单元分组的数量有限，即使启用多核通道，算法也不会将组装任务拆分到这么多的线程。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image15.png` | 图片 5 | 4768x2971 PNG | FEM Assembly Execution Time Comparison / (Scientific Notation Annotations) / Thread Count / mem 1 Thread 2 / mas 2 Threads 5 / 10° mes 4 Threads ni 2 / mmm 8 Threads _ / mmm 16 ... |

### Slide 13: 1.3：在多核CPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide13.xml`
- Notes XML: `ppt/notesSlides/notesSlide12.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
13
1.3：在多核CPU平台上的并行组装策略
```

#### Speaker Notes

```text
其次是加速比和并行效率的结果。从右上角的热力图可以看出，这种加速在多核和大规模单元的case下最为明显，但加速比的提升是有限的，这种有限反应了图着色法内在的效率限制
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image16.png` | 图片 6 / 图形用户界面, 应用程序 / AI 生成的内容可能不正确。 | 5305x3713 PNG | FEM Assembly Performance Benchmark - Comprehensive Dashboard / Execution Time Heatmap (log scale) Speedup Heatmap / Tiny 6.1e-5 1.le-4 1.le-4 1.0e-4 1.3e-4 Tiny 7 1.00x 0.54x 0.... |

### Slide 14: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide14.xml`

#### Visible Text

```text
2026/1/30
Regular Report
14
1.4：在众核GPU平台上的并行组装策略
策略 A：一线程处理一单元 (One Thread Per Element)
机制： 将单元矩阵拆解，每个线程只负责累加一个非零元贡献。
适用： 高阶单元或LMA (Local Matrix Approach，局部矩阵法，每个线程独立计算并存储局部副本，最后统一归约)。
策略 B：一线程处理非零元 (One Thread Per Non-Zero)
策略 C：线程束协作 (Warp-Level Parallelism)
机制： 一个Warp (线程束，GPU调度的最小基本单元，通常包含32个同步执行的线程) 协同处理一个单元。
适用： 高阶单元或复杂材料模型，利用寄存器通信减少显存压力。
```

#### Speaker Notes

```text
None extracted.
```

### Slide 15: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide15.xml`
- Notes XML: `ppt/notesSlides/notesSlide13.xml`
- Media count: `2`

#### Visible Text

```text
2026/1/30
Regular Report
15
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
这页展示了对在GPU上并行组装整体刚度矩阵的文献调研和算法实现的产出物
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image17.png` | 图片 7 | 2320x758 PNG | claude -Spec-workflow build parallel stiffnes BSG Sk ias> 10M-Core Algorithms and Architecting Assembly of benchmark_res Evaluating Finite element GPU_report GreedyColoring / s ... |
| `ppt/media/image18.png` | 图片 9 | 2320x566 PNG | iv) iv) iv) iv) iv) iv) iv) iv) iv) iv) iv) iv) iv) iv) / .ace-tool claude -Spec-workflow trae Vs apps build cmake data docs include openspec results scripts / r) r) © o o v) x ... |

### Slide 16: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide16.xml`
- Notes XML: `ppt/notesSlides/notesSlide14.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
16
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
具体来说，我实现了 GPU 并行刚度矩阵组装框架，代码量约 5,500 行，包含 4 种 GPU 算法。程序在 RTX 5080 平台 上测试，峰值加速比达 97.8 倍，大规模问题稳定在 35 倍加速。
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image19.png` | 图片 8 / 图表 / AI 生成的内容可能不正确。 | 2267x971 PNG | (RRGMU: 5,451 17 GPU MGRERE (RTX 5080) / mm C++/CUDA HLMKAS (3, 344) / me WitKSMARF (458) / mmm Python #ilZk (842) 100 98x / mmm CMake #432 (316) / mmm RARITY (491) / 80 / 2 60 ... |

### Slide 17: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide17.xml`
- Notes XML: `ppt/notesSlides/notesSlide15.xml`

#### Visible Text

```text
2026/1/30
Regular Report
17
1.4：在众核GPU平台上的并行组装策略
策略 A：一线程处理一单元 (One Thread Per Element)
基于原子操作（Atomic Operations）的并行累加
基于工作队列（Work Queue）的动态负载均衡
策略 B：一线程处理非零元 (One Thread Per Non-Zero)
基于线程块（Thread Block）的并行组装
基于前缀和（Prefix Sum/Scan）的并行分配
策略 C：线程束协作 (Warp-Level Parallelism)
```

#### Speaker Notes

```text
在算法实现设计预期目标时，我选取了四种主流的并行算法，希望得出一个初步结论之后再针对一类算法进行更深入的文献调研。这些算法分别属于前面提到的三类策略，但在实际编译测试时，基于前缀和的算法始终报错且无法得到有效解决，这很大程度上拖慢了进度，所以下面我先展示已有的结果，只涉及到三类并行算法
```

### Slide 18: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide18.xml`
- Notes XML: `ppt/notesSlides/notesSlide16.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
18
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
接下来我们看一些具体结果。首先还是耗时的对比结果，这里我们可以看到原子操作和线程块算法的耗时最低且基本相同，并且都比基准效果要低很多
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image20.png` | 图片 5 / 图表, 条形图 / AI 生成的内容可能不正确。 | 2771x1575 PNG | GPU 3-47 Pl BE FBRS48 38 - GAITATIEIIEL (Hex8 477) / (RTX 5080, CUDA 13.1, 2026-01-30 Sei) / 7 ov / mmm CPU Serial oe / _ MME GPU Atomic / ME GPU Block & / Mm GPU WorkQueue ‘ / ... |

### Slide 19: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide19.xml`
- Notes XML: `ppt/notesSlides/notesSlide17.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
19
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
然后是加速比的对比结果，在我们测试案例的中等规模处，加速器出现了一个较为尖锐的拐点
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image21.png` | 图片 7 / 图表, 条形图 / AI 生成的内容可能不正确。 | 2774x1574 PNG | GPU SsAMMERECRTEE (Hex8 57) / (RTX 5080, CUDA 13.1, 2026-01-30 SE3ql)) / 100 - 7.8X ae 9x IM: 97.8. Gpy Baseline (1X) / Mmm GPU Atomic / Mm GPU Block / Mmm «GPU WorkQueue / 80 -... |

### Slide 20: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide20.xml`
- Notes XML: `ppt/notesSlides/notesSlide18.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
20
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
在这张图众，拐点的突变更为清晰，目前暂不清楚这种突兀转变的具体原因，初步结论是当自由度数量达到36k这个量级时，问题规模恰好匹配了GPU的L2 cache 64MB的容量，也就是硬件层面的效率限制，问题规模再大，内存带宽就会趋于饱和
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image22.png` | 图片 5 / 图表, 折线图 / AI 生成的内容可能不正确。 | 3171x1432 PNG | GPU {TRUE SBRECR Se - YP RRMED AR (Hex8 7t) / (RTX 5080, CUDA 13.1, 2026-01-30 SE3ql)) / CAT Rito - PORE BAY Rta ar - MERLE / "== CPU Serial wy 2 4402 ms 100 - os =@= GPU Atomic... |

### Slide 21: 1.4：在众核GPU平台上的并行组装策略

- Slide XML: `ppt/slides/slide21.xml`
- Notes XML: `ppt/notesSlides/notesSlide19.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
21
1.4：在众核GPU平台上的并行组装策略
```

#### Speaker Notes

```text
None extracted.
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image23.png` | 图片 7 / 图表 / AI 生成的内容可能不正确。 | 2773x1186 PNG | GPU F+{TPI SBR CRs - MEREFA TIA) (Hex8 7c) / (RTX 5080, CUDA 13.1, 2026-01-30 SEs) / PUTA) (ms) - MARE wwe (FAXT-FCPu) / CPU Serial - 0. 385 1.8 2. 1e1 1. 3e2 2. de2 CPU Serial ... |

### Slide 22: Task2：Ansys APDL仿真案例

- Slide XML: `ppt/slides/slide22.xml`

#### Visible Text

```text
Task2：Ansys APDL仿真案例
协助优化梁单元精度问题
2026/1/30
Regular Report
22
```

#### Speaker Notes

```text
None extracted.
```

### Slide 23: 2026/1/30

- Slide XML: `ppt/slides/slide23.xml`
- Notes XML: `ppt/notesSlides/notesSlide20.xml`
- Media count: `2`

#### Visible Text

```text
2026/1/30
Regular Report
23
```

#### Speaker Notes

```text
从9月到11月，作为上手的任务，我协助苏璞师兄做了6批Ansys仿真案例，其中每批案例基本都是54个工况。这类任务的要求基本一致，输出物也相对固定，就是提取数据并汇总到excel模板中，整体来说是比较机械的工作，能自由发挥的地方就是对apdl脚本做优化以及编写稳定的自动提取数据到excel中的脚本。典型的要求如左图所示、典型的提交内容如右图所示
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image24.png` | 图片 6 | 2708x1528 PNG | Ee Bi ES ESE Mena ¥ BRARUBHA / # EN y: . \ FU TT / # An sys \|! b £ ®S ont nvtDy CHONGQING RESEARCH INSTITUTE OF BIG DATA. / ® 32823261 @ #reao a #5 P / () Ua: SHBMRIWIM. 2. 4. 8... |
| `ppt/media/image25.png` | 图片 13 | 1040x608 PNG | ea . exam a uh / 50 .stfolder 2026/1/22 15:00 SESE / 50 SLR-3 2026/1/22 15:13 SUSE / 50 SLR-4 2026/1/22 15:16 SUSE / Su SLR-S 2026/1/22 15:15 SUSE / 50 SLR-6 2026/1/22 15:16 SUS... |

### Slide 24: 2026/1/30

- Slide XML: `ppt/slides/slide24.xml`
- Notes XML: `ppt/notesSlides/notesSlide21.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
24
```

#### Speaker Notes

```text
典型的表格样式如此页
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image26.png` | 图片 7 | 2560x1008 PNG | A B c D E F G H I J K L M N fe) Pp Q « / 1 14 0-BEK 6Omm: / 2 1 5.3333E+05 —-0.0000E+00 + —-0.0000E+00 ~—-0.0000E+00 ~—:0.0000E+00 ~—-0.0000E+00 ~—--5.3333E+05 —0.0000E+00 ~—-0.... |

### Slide 25: 2026/1/30

- Slide XML: `ppt/slides/slide25.xml`
- Notes XML: `ppt/notesSlides/notesSlide22.xml`
- Media count: `1`

#### Visible Text

```text
2026/1/30
Regular Report
25
```

#### Speaker Notes

```text
和此页所示，不再赘述
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image27.png` | 图片 9 | 2560x1008 PNG | A \|B © D — F cs H 1 i K L M N «a / Fi / 8: E ] ro ro / 1, 2B: BSR, KSL=60mm; BIE, SE=8mm, AEh=20mm; (KABLLSLR=3) mE 5 cy / 2, tPBh: PEARMBE=2.065MPa ; SBeALLV=03 Sm f / 3, DARE:... |

### Slide 26: 感谢您的指正

- Slide XML: `ppt/slides/slide26.xml`
- Media count: `1`

#### Visible Text

```text
感谢您的指正
```

#### Speaker Notes

```text
None extracted.
```

#### Embedded Media

| Target | Name / alt text | Size | OCR excerpt |
| --- | --- | --- | --- |
| `ppt/media/image4.jpeg` | 图片 1 | 1600x501 JPEG | en . Se h th ~ 6 @ § Vs ae ROP aes io / BSS SK SA ee i See / @= eA ay er Sa ad CL (ee, ‘ty, ~ iy, ee ot teat . 5 / i <a / A) = oA 9 ae, Ee Pacis © Ueda be |
