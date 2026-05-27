#!/usr/bin/env python3
"""Build a Nature-style redraw package from existing PGSA result artifacts.

The script is intentionally data-first: it reads committed CSV/JSON result files
and writes a separate publication-style figure package without overwriting older
presentation or benchmark images.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


OUT_DIR = Path("results") / "nature-figures-2026-05-26"
EXPECTED_FORMATS = frozenset({".svg", ".pdf", ".png"})
VISUAL_EXTENSIONS = frozenset({".png", ".svg", ".pdf", ".jpg", ".jpeg"})
LEGEND_REQUIRED_SECTIONS = frozenset({"data_source", "test_background", "result_conclusion", "interpretation"})
LEGEND_SECTION_ORDER = ("data_source", "test_background", "result_conclusion", "interpretation")
LEGEND_SECTION_LABELS = {
    "data_source": "数据来源",
    "test_background": "测试背景",
    "result_conclusion": "结果结论",
    "interpretation": "原因解释",
}
REQUIRED_SOURCE_FAMILIES = frozenset(
    {
        "benchmark_12_charts",
        "cpu_benchmark",
        "thread_scaling",
        "cross_platform",
        "symbolic_memory",
        "sparse_pattern",
        "validation",
        "basic_metrics_schema",
    }
)


@dataclass(frozen=True)
class FigureSpec:
    stem: str
    title: str
    family: str
    conclusion: str
    source_families: tuple[str, ...]


FIGURE_SPECS = (
    FigureSpec(
        "fig01_benchmark_three_axis_summary",
        "Three-axis benchmark summary",
        "quantitative grid",
        "Correctness, memory, and assembly-time evidence must be read together, not as speedup alone.",
        ("benchmark_12_charts",),
    ),
    FigureSpec(
        "fig02_cpu_benchmark_dashboard",
        "CPU benchmark dashboard",
        "quantitative grid",
        "WindHub-scale timing shows different algorithms trade assembly time against memory and preprocessing.",
        ("cpu_benchmark",),
    ),
    FigureSpec(
        "fig03_thread_scaling_platforms",
        "Thread-scaling platform comparison",
        "quantitative grid",
        "Thread scaling changes by platform profile, with oversubscription and memory pressure visible in the same view.",
        ("thread_scaling",),
    ),
    FigureSpec(
        "fig04_core_profile_comparison",
        "Core-profile acceleration comparison",
        "quantitative grid",
        "Full-host, performance-core, and efficiency-core profiles expose platform-specific acceleration limits.",
        ("cross_platform", "thread_scaling"),
    ),
    FigureSpec(
        "fig05_symbolic_memory_lifecycle",
        "Symbolic and numeric memory lifecycle",
        "quantitative grid",
        "Symbolic reuse shifts cost from repeated direct assembly into persistent CSR and scatter-plan storage.",
        ("symbolic_memory",),
    ),
    FigureSpec(
        "fig06_backend_tradeoff",
        "Numeric backend tradeoff",
        "quantitative grid",
        "Atomic, private-CSR, and lock-guard backends separate synchronization cost from memory growth.",
        ("symbolic_memory",),
    ),
    FigureSpec(
        "fig07_sparse_pattern_windows",
        "Sparse stiffness matrix pattern windows",
        "asymmetric mixed-modality figure",
        "The WindHub stiffness matrix is highly sparse, structured, and reproducibly exported from serial and parallel paths.",
        ("sparse_pattern",),
    ),
    FigureSpec(
        "fig08_solver_validation",
        "Finite-element solver validation",
        "quantitative grid",
        "Independent COMSOL and CalculiX probe comparisons close the solve-level validation loop.",
        ("validation",),
    ),
    FigureSpec(
        "fig09_basic_metrics_schema_coverage",
        "Basic-metrics schema coverage",
        "quantitative grid",
        "The cross-platform v2 packages make correctness, memory, and assembly-time fields first-class review artifacts.",
        ("basic_metrics_schema",),
    ),
)


ALGORITHM_ORDER = [
    "cpu_serial",
    "cpu_atomic",
    "cpu_lock_guard",
    "cpu_private_csr",
    "cpu_coo_sort_reduce",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

THREAD_ALGORITHMS = [
    "cpu_atomic",
    "cpu_private_csr",
    "cpu_row_owner",
    "cpu_graph_coloring",
]

ALGO_LABELS = {
    "cpu_serial": "Serial",
    "cpu_atomic": "Atomic",
    "cpu_lock_guard": "Lock guard",
    "cpu_private_csr": "Private CSR",
    "cpu_coo_sort_reduce": "COO sort-reduce",
    "cpu_row_owner": "Row owner",
    "cpu_graph_coloring": "Coloring",
}

PALETTE = {
    "baseline_dark": "#484878",
    "baseline_mid": "#7884B4",
    "baseline_soft": "#B4C0E4",
    "ours_tiny": "#E4E4F0",
    "ours_base": "#E4CCD8",
    "ours_large": "#F0C0CC",
    "neutral_light": "#D8D8D8",
    "neutral_mid": "#A8A8A8",
    "neutral_dark": "#606060",
    "delta_up": "#2E9E44",
    "delta_down": "#E53935",
    "ink": "#272727",
}

ALGO_COLORS = {
    "cpu_serial": PALETTE["neutral_dark"],
    "cpu_atomic": PALETTE["baseline_dark"],
    "cpu_lock_guard": PALETTE["delta_down"],
    "cpu_private_csr": PALETTE["baseline_mid"],
    "cpu_coo_sort_reduce": PALETTE["ours_large"],
    "cpu_row_owner": PALETTE["delta_up"],
    "cpu_graph_coloring": PALETTE["ours_base"],
}


def figure_legends() -> dict[str, dict[str, str]]:
    return {
        "fig01_benchmark_three_axis_summary": {
            "data_source": (
                "本图读取 `results/2026-04-28-12charts-repeat3-threads1to14/csv/` 下四个基准 CSV，"
                "覆盖规则立方体网格与 WindHub 网格、legacy synthetic 与 Tet4 弹性局部刚度模型。"
                "绘图只使用 `status=PASS` 的记录，并从 `speedup`、`extra_memory_bytes`、`rel_l2`、"
                "`max_abs` 等字段提取每个算法和场景的确定性摘要。"
            ),
            "test_background": (
                "这组测试的目的不是单独追求最高加速比，而是把矩阵正确性、额外内存和装配耗时放在同一证据链中审阅。"
                "每个场景都以 `cpu_serial` 作为正确性和性能基线，比较 `cpu_atomic`、`cpu_private_csr`、"
                "`cpu_graph_coloring`、`cpu_row_owner` 与 `cpu_coo_sort_reduce` 在 1 到 14 线程区间的行为。"
            ),
            "result_conclusion": (
                "热图显示所有通过记录的相对矩阵误差基本处在浮点舍入量级，最大绝对误差也保持在可解释的小范围内。"
                "同时，加速收益和内存代价并不同步：在 WindHub Tet4 弹性场景中，`cpu_row_owner` 和 `cpu_atomic` "
                "能给出较高加速，但 row-owner 类策略需要显著额外存储，而 atomic 类策略的内存增量更低。"
            ),
            "interpretation": (
                "这种形态来自有限元全局刚度矩阵装配的共享写入冲突：不同单元会向同一全局自由度贡献条目。"
                "原子加法减少临时存储但付出同步代价；私有 CSR 或 row-owner 策略通过拆分写入路径降低冲突，"
                "因而更容易加速，但需要保留 per-thread 或 owner 分区数据。误差非零主要来自并行归约顺序变化，"
                "不是稀疏结构或物理模型的系统性失配。"
            ),
        },
        "fig02_cpu_benchmark_dashboard": {
            "data_source": (
                "本图来自 `results/2026-04-22/csv/` 下的 CPU 基准 CSV，尤其是 WindHub simplified、"
                "WindHub physics Tet4 以及单独的 `windhub_physics_tet4_coo_sort_reduce.csv`。"
                "脚本读取 `assembly_mean_ms` 或 `assembly_ms`、`speedup`、`extra_memory_bytes`、`threads` "
                "等字段，并按 WindHub 场景汇总时间曲线、最快记录的内存成本和最高加速比。"
            ),
            "test_background": (
                "该图对应项目早期 CPU 主线基准：在真实 WindHub 网格上比较串行装配、原子写入、私有 CSR、"
                "图着色、row-owner 和 COO sort-reduce 后端。测试关注真实大规模网格下的装配阶段，而不是小网格上的函数级微基准。"
            ),
            "result_conclusion": (
                "WindHub physics Tet4 中，私有 CSR、row-owner 和 atomic 后端形成主要可用候选；"
                "COO sort-reduce 在该规模下耗时明显偏高且额外内存更大。图中同时保留速度和内存面板，说明最快策略并不自动等于最适合作为默认后端。"
            ),
            "interpretation": (
                "私有 CSR 与 row-owner 通过减少热点写入冲突提升数值装配效率，但需要额外的矩阵副本、owner 映射或合并工作。"
                "Atomic 后端几乎不增加算法性额外内存，但热点自由度上的原子操作会限制扩展性。COO sort-reduce 需要先生成大量三元组再排序归并，"
                "因此在 WindHub 这类 2750 万非零条目的矩阵上会被内存流量和排序成本主导。"
            ),
        },
        "fig03_thread_scaling_platforms": {
            "data_source": (
                "本图汇总六个 `thread_scaling_combined.csv` 文件，覆盖 Apple M4 Max full host、performance QoS、"
                "efficiency QoS，以及 Intel Core Ultra 7 265KF full host、P-core、E-core 配置。"
                "每个平台配置按算法选择 `assembly_ms` 最小的 PASS 记录，并展示对应的 `speedup` 与 `extra_memory_bytes`。"
            ),
            "test_background": (
                "线程扩展测试用于回答同一 PGSA 后端在不同异构 CPU 资源绑定下是否仍保持相同排序。"
                "因此图中不只看线程数增加后的速度，也把性能核、效率核和全主机配置分开，避免把操作系统调度和核心类型差异混成一个平均值。"
            ),
            "result_conclusion": (
                "结果显示扩展性具有明显平台和核心配置依赖：Apple 与 Intel 的 full-host、性能核心和效率核心配置并不产生同一组最优速度。"
                "私有 CSR 往往能取得更高速度，但图中同步显示其额外内存会随线程和缓冲区规模增加。"
            ),
            "interpretation": (
                "这种差异来自三类因素叠加：核心微架构吞吐、共享内存带宽、以及同步或合并阶段的串行残留。"
                "性能核心通常提高单线程和缓存层级表现，效率核心在内存密集的稀疏装配中更容易受带宽和频率限制；"
                "全主机运行虽然线程更多，但也可能引入跨核心类型调度和共享资源竞争。"
            ),
        },
        "fig04_core_profile_comparison": {
            "data_source": (
                "本图使用与线程扩展相同的 cross-platform CSV 数据，但重新组织为相对 full-host 的装配时间比。"
                "脚本在 Apple M4 Max 和 Intel U7 265KF 两个平台内分别找出每个算法、每个核心配置的最快 PASS 记录，"
                "再用该配置的 `assembly_ms` 除以同平台 full-host 最快时间。"
            ),
            "test_background": (
                "该图的背景问题是：full-host 是否总是最有解释力的比较对象，以及只用性能核或效率核是否能暴露算法瓶颈。"
                "比值小于或接近 1 表示受限核心配置接近全主机表现；显著大于 1 表示该算法依赖更多核心或更高带宽。"
            ),
            "result_conclusion": (
                "图中可以看到性能核心配置在若干算法上接近 full-host，而效率核心配置通常明显慢于 full-host。"
                "这说明 PGSA 的线程扩展不能只按逻辑线程数解释，必须把核心类型和绑定策略作为实验条件写入结果包。"
            ),
            "interpretation": (
                "有限元装配包含局部刚度计算、稀疏索引访问和全局写入三部分。性能核心更适合局部计算和同步密集段，"
                "效率核心在频率和缓存资源上受限时会放大原子写入或 merge 阶段成本。full-host 可能受益于更多并发，"
                "但如果算法合并阶段或内存带宽先达到瓶颈，单纯增加核心并不会线性改善装配时间。"
            ),
        },
        "fig05_symbolic_memory_lifecycle": {
            "data_source": (
                "本图读取 `results/2026-05-20-linux-intel-symbolic-memory-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`。"
                "该文件包含 WindHub physics Tet4 在 Linux Intel full-host 上的 symbolic CSR 构建时间、scatter-plan 时间、"
                "数值装配时间、估算峰值字节数和隔离进程 RSS。"
            ),
            "test_background": (
                "symbolic/numeric 解耦测试用于区分两类成本：一次性建立稀疏结构和映射计划的 symbolic 阶段，以及每次载荷或材料更新时重复执行的 numeric 阶段。"
                "图中比较 serial symbolic reuse、direct no-symbolic、serial symbolic with parallel numeric 与 parallel symbolic reuse 等路径。"
            ),
            "result_conclusion": (
                "结果表明 symbolic reuse 会把成本从反复生成和排序矩阵条目的 direct 路径转移到持久 CSR 与 scatter-plan 存储。"
                "direct no-symbolic 的瞬时内存峰值和排序归并成本更高，而 symbolic 路径在多次装配场景下更适合摊销前处理成本。"
            ),
            "interpretation": (
                "原因是 WindHub 的稀疏拓扑在同一网格和单元类型下保持稳定：非零模式不需要每次重新发现。"
                "提前保存 CSR 结构和散射计划会增加常驻内存，但能避免每轮数值装配都生成大量临时 triplet 或 bucket 数据。"
                "因此 symbolic reuse 的优势会随重复装配次数增加而放大，而单次装配时需要同时报告前处理成本和持久内存。"
            ),
        },
        "fig06_backend_tradeoff": {
            "data_source": (
                "本图读取 `results/2026-05-20-linux-intel-symbolic-memory-full-host/windhub_backend_tradeoff.csv`，"
                "使用同一 WindHub physics Tet4、Linux Intel full-host 实验中的 atomic、private CSR 和 lock-guard 后端记录。"
                "面板分别绘制 `assembly_ms`、`speedup` 和 `extra_memory_bytes` 随线程变化的曲线。"
            ),
            "test_background": (
                "该测试专门拆分数值装配后端的同步策略：atomic 使用硬件原子写入，private CSR 使用线程私有缓冲再合并，"
                "lock-guard 使用互斥锁保护共享条目。它帮助判断同步开销、内存放大和可扩展性之间的取舍。"
            ),
            "result_conclusion": (
                "图中 private CSR 通常能在中等线程数获得较好速度，但额外内存随线程缓冲增长；atomic 内存代价最低，"
                "但在热点写入密集时扩展受限；lock-guard 的装配时间明显偏高，说明粗粒度或频繁互斥不适合该稀疏装配热点。"
            ),
            "interpretation": (
                "全局刚度装配的冲突来自多个单元同时更新相邻自由度的矩阵项。Atomic 把冲突压缩到硬件同步指令，"
                "成本比互斥锁低但仍会在高冲突条目上排队；private CSR 通过本地累积减少写入冲突，代价是额外存储和后处理合并；"
                "lock-guard 每次写入都可能进入软件锁路径，因此锁管理成本吞没并行收益。"
            ),
        },
        "fig07_sparse_pattern_windows": {
            "data_source": (
                "本图读取周会材料资产中的 `windhub_physics_tet4_visual_exact_window_serial.csv`、"
                "`windhub_physics_tet4_visual_exact_window_auto_serial.csv` 以及配套 metadata JSON。"
                "metadata 记录 WindHub physics Tet4 的 228,384 个节点、685,152 个自由度、27,502,200 个非零项，"
                "并记录 serial 与 14 线程 atomic 路径具有相同稀疏结构。"
            ),
            "test_background": (
                "稀疏模式图用于解释为什么 PGSA 需要专门处理内存布局和并行写入冲突。"
                "面板 a 展示矩阵原点附近的精确窗口，面板 b 展示自动选择的高密度对角窗口；图题还报告可视化用 RCM 重排前后的带宽变化。"
            ),
            "result_conclusion": (
                "图中非零项高度集中在局部对角带和块状邻域中，说明矩阵既稀疏又有明显有限元连接结构。"
                "metadata 中 RCM 可视化带宽从 392,948 降至 9,314，进一步说明节点排序会显著影响观察到的带宽和局部性。"
            ),
            "interpretation": (
                "这种结构由有限元网格的局部支撑决定：每个单元只耦合自身节点自由度及其邻近节点，因此全局矩阵不会形成密集连接。"
                "WindHub 几何复杂且原始编号不完全按空间局部性排列，所以原始带宽较大；RCM 将相邻连接聚到对角附近，"
                "但该重排只用于可视化，不改变实际 benchmark 的数值矩阵。"
            ),
        },
        "fig08_solver_validation": {
            "data_source": (
                "本图读取 `results/validation-export/2026-05-23-macos-comsol/` 与 "
                "`results/validation-export/2026-05-23-linux-intel-calculix/` 下的 probe compare CSV。"
                "每个 cantilever Tet4/Hex8、小/中等网格案例都包含 root、midspan 和 free-tip 探针位移，"
                "字段包括 MATLAB/PGSA 侧位移、外部求解器位移、`abs_diff` 与诊断用 `rel_diff`；"
                "本图主指标从 `free_tip_center` 的 `Uz` 派生为自由端挠度相对差异百分比。"
            ),
            "test_background": (
                "该验证不是只检查矩阵条目，而是检查有限元求解结果是否能与独立求解器闭环。"
                "COMSOL 6.2 LiveLink 和 CalculiX 分别作为外部参考，探针覆盖固定端、跨中和自由端，以检测边界条件、载荷方向和刚度矩阵缩放是否一致。"
            ),
            "result_conclusion": (
                "CalculiX 与 COMSOL 对比均按自由端挠度百分比报告。"
                "逐 probe `rel_diff` 仍可用于诊断节点映射和中间截面趋势，但不作为最终正确性百分比。"
            ),
            "interpretation": (
                "CalculiX 与当前导出链在网格、载荷和单元公式上更接近，因此差异更接近舍入和输出精度误差。"
                "COMSOL 的差异略大，主要可由 LiveLink 导入网格、默认积分设置、载荷面积分布和探针插值细节解释。"
                "由于最大误差集中在位移幅值最大的自由端，绝对差异看起来较大，但相对差异仍保持在验证可解释范围内。"
            ),
        },
        "fig09_basic_metrics_schema_coverage": {
            "data_source": (
                "本图读取三个 cross-platform v2 benchmark package JSON：Linux Intel symbolic-memory full-host、"
                "2026-05-23 linear-elastic full-host 与 2026-05-24 linear-elastic full-host。"
                "脚本逐个 experiment family 统计 records 数量，并检查 `matrix_correctness_status`、`estimated_peak_bytes`、"
                "`isolated_peak_rss_mb`、`serial_direct_baseline_ms`、`speedup_vs_serial_direct` 等基础指标字段是否出现。"
            ),
            "test_background": (
                "该图服务于结果包质量审计：PGSA 不应只保留图片或单次 benchmark 摘要，而应把正确性、内存和装配耗时作为可机器读取的评估契约。"
                "因此它把 thread_scaling、symbolic_direct、lock_vs_atomic、correctness_sparse 和 memory_lifecycle 等 family 放入同一覆盖矩阵。"
            ),
            "result_conclusion": (
                "完整 full-host 包包含较多 thread-scaling、symbolic-direct、lock-vs-atomic 和 memory-lifecycle 记录，"
                "而 2026-05-24 包更像 smoke package，每个 family 只保留少量记录。字段覆盖矩阵显示 memory 相关字段主要集中在 symbolic_direct，"
                "提示仍需继续把三轴指标规范推广到其他 family。"
            ),
            "interpretation": (
                "这种覆盖形态反映了仓库从 benchmark 结果向可移交结果包过渡的阶段性状态。"
                "早期 thread-scaling 与 lock-vs-atomic 记录已经有时间、线程和内存原始字段，但未全部映射到统一的基础指标字段名；"
                "symbolic-direct 因为本轮重点是 memory lifecycle，最先补齐 estimated peak 与 isolated RSS。"
                "因此该图既证明已有结果可追溯，也暴露下一步 schema 归一化的工作边界。"
            ),
        },
    }


def validate_figure_legends() -> None:
    expected_stems = {spec.stem for spec in FIGURE_SPECS}
    legends = figure_legends()
    if set(legends) != expected_stems:
        missing = sorted(expected_stems - set(legends))
        extra = sorted(set(legends) - expected_stems)
        raise RuntimeError(f"Figure legend stem mismatch; missing={missing}, extra={extra}")
    for stem, sections in legends.items():
        if set(sections) != LEGEND_REQUIRED_SECTIONS:
            raise RuntimeError(f"Figure legend section mismatch for {stem}: {sorted(sections)}")


def write_figure_legends(project_root: Path) -> Path:
    validate_figure_legends()
    path = out_root(project_root) / "figure_legends.md"
    lines = [
        "# PGSA Nature-Style Figure Legends",
        "",
        "本文件为本轮 Nature 风格重绘图包的详细图例说明。每张图均按数据来源、测试背景、结果结论和原因解释组织，便于审稿、汇报和后续复现实验时直接核对。",
        "",
    ]
    specs_by_stem = {spec.stem: spec for spec in FIGURE_SPECS}
    for stem, sections in figure_legends().items():
        spec = specs_by_stem[stem]
        lines.extend(
            [
                f"## {stem}",
                "",
                f"**图件定位**：{spec.conclusion}",
                "",
            ]
        )
        for section in LEGEND_SECTION_ORDER:
            lines.extend([f"**{LEGEND_SECTION_LABELS[section]}**：{sections[section]}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def out_root(project_root: Path) -> Path:
    return project_root / OUT_DIR


def figure_base(project_root: Path, stem: str) -> Path:
    return out_root(project_root) / stem


def planned_nature_outputs(project_root: Path) -> list[Path]:
    outputs = [out_root(project_root) / "manifest.md", out_root(project_root) / "figure_legends.md"]
    for spec in FIGURE_SPECS:
        base = figure_base(project_root, spec.stem)
        for suffix in sorted(EXPECTED_FORMATS):
            outputs.append(base.with_suffix(suffix))
    return outputs


def legacy_visual_inventory(project_root: Path) -> dict[str, int]:
    counts = {"reports": 0, "results": 0, "total": 0}
    output_root = out_root(project_root).resolve()
    for top_level in ("results", "reports"):
        root = project_root / top_level
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in VISUAL_EXTENSIONS:
                try:
                    if path.resolve().is_relative_to(output_root):
                        continue
                except FileNotFoundError:
                    continue
                counts[top_level] += 1
                counts["total"] += 1
    return counts


def _glob_sorted(root: Path, pattern: str) -> list[Path]:
    return sorted(root.glob(pattern))


def source_family_inputs(project_root: Path) -> dict[str, list[Path]]:
    results = project_root / "results"
    reports = project_root / "reports"
    repeat3 = results / "2026-04-28-12charts-repeat3-threads1to14" / "csv"
    cpu_0422 = results / "2026-04-22" / "csv"
    thread_roots = [
        "2026-05-11-thread-scaling",
        "2026-05-11-thread-scaling-linux-intel",
        "2026-05-12-thread-scaling-linux-intel-pcore",
        "2026-05-12-thread-scaling-linux-intel-ecore",
        "2026-05-14-thread-scaling-macos-m4max-performance-qos",
        "2026-05-14-thread-scaling-macos-m4max-efficiency-qos",
    ]
    weekly_assets = reports / "2026-05-22-weekly-meeting-beamer" / "assets"

    validation = _glob_sorted(results, "validation-export/2026-05-23-macos-comsol/*/*_comsol_compare.csv")
    validation += _glob_sorted(results, "validation-export/2026-05-23-linux-intel-calculix/*/*_calculix_probe_compare.csv")

    return {
        "benchmark_12_charts": [
            repeat3 / "01_cube_tet4_8x8x8_simplified.csv",
            repeat3 / "02_cube_tet4_8x8x8_physics_tet4.csv",
            repeat3 / "03_windhub_simplified.csv",
            repeat3 / "04_windhub_physics_tet4.csv",
        ],
        "cpu_benchmark": [
            cpu_0422 / "cube_tet4_simplified.csv",
            cpu_0422 / "windhub_simplified.csv",
            cpu_0422 / "windhub_physics_tet4.csv",
            cpu_0422 / "windhub_physics_tet4_coo_sort_reduce.csv",
        ],
        "thread_scaling": [results / name / "thread_scaling_combined.csv" for name in thread_roots],
        "cross_platform": [
            results / "2026-05-11-thread-scaling" / "thread_scaling_combined.csv",
            results / "2026-05-14-thread-scaling-macos-m4max-performance-qos" / "thread_scaling_combined.csv",
            results / "2026-05-14-thread-scaling-macos-m4max-efficiency-qos" / "thread_scaling_combined.csv",
            results / "2026-05-11-thread-scaling-linux-intel" / "thread_scaling_combined.csv",
            results / "2026-05-12-thread-scaling-linux-intel-pcore" / "thread_scaling_combined.csv",
            results / "2026-05-12-thread-scaling-linux-intel-ecore" / "thread_scaling_combined.csv",
        ],
        "symbolic_memory": [
            results / "2026-05-20-linux-intel-symbolic-memory-full-host" / "isolated_symbolic_memory" / "isolated_symbolic_memory.csv",
            results / "2026-05-20-linux-intel-symbolic-memory-full-host" / "windhub_backend_tradeoff.csv",
        ],
        "sparse_pattern": [
            weekly_assets / "windhub_physics_tet4_visual_exact_window_serial.csv",
            weekly_assets / "windhub_physics_tet4_visual_exact_window_auto_serial.csv",
            weekly_assets / "windhub_physics_tet4_visual_metadata.json",
            weekly_assets / "windhub_physics_tet4_pattern_metadata.json",
        ],
        "validation": validation,
        "basic_metrics_schema": [
            results / "2026-05-20-linux-intel-symbolic-memory-full-host" / "cross-platform-v2" / "benchmark_package_v2.json",
            results / "2026-05-23-linux-intel-linear-elastic-full-host" / "cross-platform-v2" / "benchmark_package_v2.json",
            results / "2026-05-24-linux-intel-linear-elastic-full-host" / "cross-platform-v2" / "benchmark_package_v2.json",
        ],
    }


def validate_source_inputs(project_root: Path) -> dict[str, object]:
    families = source_family_inputs(project_root)
    missing = [path for paths in families.values() for path in paths if not path.exists() or path.stat().st_size == 0]
    return {
        "families": sorted(families),
        "missing": [str(path.relative_to(project_root)) for path in missing],
    }


def _import_plotting():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    return plt, np, pd


def apply_nature_style(plt) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "axes.edgecolor": PALETTE["ink"],
            "axes.labelcolor": PALETTE["ink"],
            "xtick.color": PALETTE["ink"],
            "ytick.color": PALETTE["ink"],
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save_publication(fig, base: Path, plt, *, dpi: int = 450) -> list[Path]:
    base.parent.mkdir(parents=True, exist_ok=True)
    paths = [base.with_suffix(".svg"), base.with_suffix(".pdf"), base.with_suffix(".png")]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    fig.savefig(paths[2], dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"empty figure output: {path}")
    return paths


def panel_label(ax, label: str) -> None:
    ax.text(-0.08, 1.04, label, transform=ax.transAxes, fontsize=8, fontweight="bold", va="bottom")


def clean_axis(ax, *, grid: bool = False) -> None:
    if grid:
        ax.grid(axis="y", color="#D8D8D8", linewidth=0.45, alpha=0.55)
        ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def dataset_label(row: dict[str, object]) -> str:
    case = str(row.get("case_name") or row.get("mesh") or "")
    model = str(row.get("stiffness_model") or row.get("kernel") or "")
    case = case.replace("3d-WindTurbineHub", "WindHub").replace("cube_tet4_8x8x8", "Cube")
    model = model.replace("linear_elastic_solid", "linear elastic").replace("physics_tet4", "Tet4 elastic")
    model = model.replace("simplified", "legacy synthetic")
    return f"{case}\n{model}"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fnum(value: object, default: float = 0.0) -> float:
    if value in ("", None, "None"):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bytes_to_gib(value: float) -> float:
    return value / (1024.0**3)


def read_many_csv(paths: Iterable[Path], pd):
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        frame["source_path"] = path.as_posix()
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _best_pass_by(df, pd, group_cols: list[str], metric: str, *, largest: bool):
    passed = df[df["status"].fillna("PASS") == "PASS"].copy()
    passed[metric] = pd.to_numeric(passed[metric], errors="coerce")
    passed = passed.dropna(subset=[metric])
    idx = passed.groupby(group_cols)[metric].idxmax() if largest else passed.groupby(group_cols)[metric].idxmin()
    return passed.loc[idx].copy()


def plot_benchmark_three_axis(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    df = read_many_csv(families["benchmark_12_charts"], pd)
    df["stiffness_model"] = df.get("stiffness_model", df.get("kernel"))
    df = df[df["status"] == "PASS"].copy()
    df["scenario"] = df.apply(lambda row: dataset_label(row.to_dict()), axis=1)
    for col in ("speedup", "extra_memory_bytes", "rel_l2", "max_abs"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    algorithms = [name for name in ALGORITHM_ORDER if name != "cpu_serial" and name in set(df["algorithm"])]
    scenarios = list(dict.fromkeys(df["scenario"].tolist()))

    best_speed = _best_pass_by(df, pd, ["scenario", "algorithm"], "speedup", largest=True)
    best_mem = _best_pass_by(df, pd, ["scenario", "algorithm"], "extra_memory_bytes", largest=False)
    max_error = df.groupby(["scenario", "algorithm"], as_index=False).agg({"rel_l2": "max", "max_abs": "max"})

    def matrix(source, value_col: str, transform=lambda x: x):
        lookup = {(row["scenario"], row["algorithm"]): transform(float(row[value_col])) for _, row in source.iterrows()}
        return np.array([[lookup.get((scenario, algorithm), np.nan) for algorithm in algorithms] for scenario in scenarios])

    speed = matrix(best_speed, "speedup")
    memory = matrix(best_mem, "extra_memory_bytes", lambda x: bytes_to_gib(x))
    rel_l2 = matrix(max_error, "rel_l2", lambda x: math.log10(max(x, 1.0e-18)))
    max_abs = matrix(max_error, "max_abs", lambda x: math.log10(max(x, 1.0e-18)))

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), constrained_layout=True)
    panels = [
        (axes[0, 0], speed, "Best speedup vs serial", "x", "a", "viridis"),
        (axes[0, 1], memory, "Minimum extra memory at PASS rows", "GiB", "b", "Blues"),
        (axes[1, 0], rel_l2, "Maximum matrix relative error", "log10 rel_l2", "c", "magma_r"),
        (axes[1, 1], max_abs, "Maximum matrix absolute error", "log10 max_abs", "d", "magma_r"),
    ]
    for ax, values, title, colorbar_label, label, cmap in panels:
        im = ax.imshow(values, cmap=cmap, aspect="auto")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xticks(range(len(algorithms)))
        ax.set_xticklabels([ALGO_LABELS[name] for name in algorithms], rotation=35, ha="right")
        ax.set_yticks(range(len(scenarios)))
        ax.set_yticklabels(scenarios)
        panel_label(ax, label)
        fig.colorbar(im, ax=ax, fraction=0.046, label=colorbar_label)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                if np.isnan(values[i, j]):
                    continue
                text = f"{values[i, j]:.2f}" if colorbar_label in {"x", "GiB"} else f"{values[i, j]:.1f}"
                ax.text(j, i, text, ha="center", va="center", fontsize=5.7, color="white" if cmap != "Blues" else PALETTE["ink"])
    fig.suptitle("PGSA benchmark evidence: correctness, memory, and assembly time", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig01_benchmark_three_axis_summary"), plt)


def plot_cpu_benchmark_dashboard(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    df = read_many_csv(families["cpu_benchmark"], pd)
    df["stiffness_model"] = df.get("stiffness_model", df.get("kernel"))
    df = df[df["status"] == "PASS"].copy()
    df["scenario"] = df.apply(lambda row: dataset_label(row.to_dict()), axis=1)
    for col in ("assembly_mean_ms", "assembly_ms", "speedup", "extra_memory_bytes"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "assembly_mean_ms" not in df or df["assembly_mean_ms"].sum() <= 0:
        df["assembly_mean_ms"] = df["assembly_ms"]
    windhub = df[df["case_name"].astype(str).str.contains("WindTurbineHub")].copy()
    algorithms = [name for name in ALGORITHM_ORDER if name in set(windhub["algorithm"])]

    fig = plt.figure(figsize=(7.2, 5.8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2)
    ax_time = fig.add_subplot(grid[0, :])
    ax_mem = fig.add_subplot(grid[1, 0])
    ax_speed = fig.add_subplot(grid[1, 1])

    for algorithm in algorithms:
        rows = windhub[windhub["algorithm"] == algorithm].sort_values("threads")
        if rows.empty:
            continue
        color = ALGO_COLORS.get(algorithm, PALETTE["neutral_mid"])
        ax_time.plot(rows["threads"], rows["assembly_mean_ms"], marker="o", linewidth=1.3, markersize=3.2, color=color, label=ALGO_LABELS[algorithm])
        last = rows.iloc[-1]
        ax_time.text(float(last["threads"]) + 0.2, float(last["assembly_mean_ms"]), ALGO_LABELS[algorithm], fontsize=5.8, color=color, va="center")
    ax_time.set_yscale("log")
    ax_time.set_xlabel("Threads")
    ax_time.set_ylabel("Assembly time (ms, log)")
    ax_time.set_title("WindHub assembly scaling", loc="left", fontweight="bold")
    clean_axis(ax_time, grid=True)
    panel_label(ax_time, "a")

    best = _best_pass_by(windhub, pd, ["scenario", "algorithm"], "assembly_mean_ms", largest=False)
    best["extra_gib"] = best["extra_memory_bytes"].map(bytes_to_gib)
    labels = [ALGO_LABELS.get(name, name) for name in algorithms if name in set(best["algorithm"])]
    mem_values = [float(best[best["algorithm"] == name]["extra_gib"].min()) for name in algorithms if name in set(best["algorithm"])]
    speed_values = [float(best[best["algorithm"] == name]["speedup"].max()) for name in algorithms if name in set(best["algorithm"])]
    colors = [ALGO_COLORS.get(name, PALETTE["neutral_mid"]) for name in algorithms if name in set(best["algorithm"])]
    y = np.arange(len(labels))
    ax_mem.barh(y, mem_values, color=colors)
    ax_mem.set_yticks(y)
    ax_mem.set_yticklabels(labels)
    ax_mem.set_xlabel("Extra memory at fastest row (GiB)")
    ax_mem.set_title("Memory cost", loc="left", fontweight="bold")
    clean_axis(ax_mem, grid=True)
    panel_label(ax_mem, "b")
    ax_speed.barh(y, speed_values, color=colors)
    ax_speed.set_yticks(y)
    ax_speed.set_yticklabels([])
    ax_speed.axvline(1.0, color=PALETTE["neutral_mid"], linestyle=(0, (4, 3)), linewidth=0.8)
    ax_speed.set_xlabel("Best speedup")
    ax_speed.set_title("Acceleration", loc="left", fontweight="bold")
    clean_axis(ax_speed, grid=True)
    panel_label(ax_speed, "c")
    fig.suptitle("CPU benchmark dashboard from existing result CSVs", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig02_cpu_benchmark_dashboard"), plt)


def _profile_label(path: Path) -> tuple[str, str, str]:
    name = path.parent.name
    if "linux-intel" in name:
        platform = "Intel U7 265KF"
    else:
        platform = "Apple M4 Max"
    if "pcore" in name:
        profile = "P-core"
        profile_id = "performance_core_only"
    elif "ecore" in name:
        profile = "E-core"
        profile_id = "efficiency_core_only"
    elif "performance-qos" in name:
        profile = "Performance QoS"
        profile_id = "performance_core_only"
    elif "efficiency-qos" in name:
        profile = "Efficiency QoS"
        profile_id = "efficiency_core_only"
    else:
        profile = "Full host"
        profile_id = "full_host"
    return platform, profile, profile_id


def thread_scaling_best_rows(paths: list[Path], pd):
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        platform, profile, profile_id = _profile_label(path)
        frame["platform_name"] = platform
        frame["profile_label"] = profile
        frame["profile_id"] = profile_id
        frame["source_root"] = path.parent.name
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["status"] == "PASS") & (df["algorithm"].isin(THREAD_ALGORITHMS))].copy()
    if "env_group" in df:
        df = df[df["env_group"].fillna("bound") == "bound"].copy()
    for col in ("assembly_ms", "assembly_mean_ms", "speedup", "extra_memory_bytes", "threads"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "assembly_ms" not in df or df["assembly_ms"].sum() <= 0:
        df["assembly_ms"] = df["assembly_mean_ms"]
    idx = df.groupby(["platform_name", "profile_label", "profile_id", "algorithm"])["assembly_ms"].idxmin()
    return df.loc[idx].copy()


def plot_thread_scaling_platforms(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    best = thread_scaling_best_rows(families["thread_scaling"], pd)
    profiles = list(dict.fromkeys((best["platform_name"] + "\n" + best["profile_label"]).tolist()))
    algorithms = [name for name in THREAD_ALGORITHMS if name in set(best["algorithm"])]
    speed = np.full((len(algorithms), len(profiles)), np.nan)
    memory = np.full_like(speed, np.nan, dtype=float)
    for i, algorithm in enumerate(algorithms):
        for j, profile in enumerate(profiles):
            platform, label = profile.split("\n", 1)
            row = best[(best["algorithm"] == algorithm) & (best["platform_name"] == platform) & (best["profile_label"] == label)]
            if not row.empty:
                speed[i, j] = float(row.iloc[0]["speedup"])
                memory[i, j] = bytes_to_gib(float(row.iloc[0]["extra_memory_bytes"]))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), constrained_layout=True)
    for ax, values, title, cbar, label, cmap in [
        (axes[0], speed, "Best speedup", "x", "a", "viridis"),
        (axes[1], memory, "Extra memory at best time", "GiB", "b", "Blues"),
    ]:
        im = ax.imshow(values, aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(profiles)))
        ax.set_xticklabels(profiles, rotation=35, ha="right")
        ax.set_yticks(range(len(algorithms)))
        ax.set_yticklabels([ALGO_LABELS[name] for name in algorithms])
        ax.set_title(title, loc="left", fontweight="bold")
        panel_label(ax, label)
        fig.colorbar(im, ax=ax, fraction=0.046, label=cbar)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                if not np.isnan(values[i, j]):
                    ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=5.8)
    fig.suptitle("Thread scaling across platform profiles", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig03_thread_scaling_platforms"), plt)


def plot_core_profile_comparison(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    best = thread_scaling_best_rows(families["cross_platform"], pd)
    algorithms = [name for name in THREAD_ALGORITHMS if name in set(best["algorithm"])]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), sharey=True, constrained_layout=True)
    for ax, platform, panel in zip(axes, ["Apple M4 Max", "Intel U7 265KF"], ["a", "b"]):
        sub = best[best["platform_name"] == platform]
        full = {row["algorithm"]: float(row["assembly_ms"]) for _, row in sub[sub["profile_id"] == "full_host"].iterrows()}
        y = np.arange(len(algorithms))
        width = 0.24
        for offset, profile_id, label, color in [
            (-width, "full_host", "Full host", PALETTE["baseline_dark"]),
            (0.0, "performance_core_only", "Performance/P-core", PALETTE["baseline_mid"]),
            (width, "efficiency_core_only", "Efficiency/E-core", PALETTE["ours_large"]),
        ]:
            values = []
            threads = []
            for algorithm in algorithms:
                row = sub[(sub["algorithm"] == algorithm) & (sub["profile_id"] == profile_id)]
                if row.empty or not full.get(algorithm):
                    values.append(np.nan)
                    threads.append("")
                else:
                    values.append(float(row.iloc[0]["assembly_ms"]) / full[algorithm])
                    threads.append(f"{int(row.iloc[0]['threads'])}T")
            ax.barh(y + offset, values, height=width * 0.9, color=color, label=label)
            for yi, value, thread in zip(y + offset, values, threads):
                if not np.isnan(value):
                    ax.text(value, yi, f" {value:.2f}x {thread}", va="center", fontsize=5.4)
        ax.axvline(1.0, color=PALETTE["neutral_mid"], linestyle=(0, (4, 3)), linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels([ALGO_LABELS[name] for name in algorithms])
        ax.set_xlabel("Best assembly-time ratio vs full host")
        ax.set_title(platform, loc="left", fontweight="bold")
        clean_axis(ax, grid=True)
        panel_label(ax, panel)
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.08, -0.28), ncol=3)
    fig.suptitle("Core-profile acceleration comparison", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig04_core_profile_comparison"), plt)


def plot_symbolic_memory_lifecycle(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    df = pd.read_csv(families["symbolic_memory"][0])
    for col in ("threads", "amortized_total_ms", "estimated_peak_bytes", "isolated_peak_rss_mb"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    backends = ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.3), constrained_layout=True)
    for backend in backends:
        for mode, linestyle in [("serial_symbolic_parallel_numeric", "-"), ("parallel_symbolic_reuse", "--")]:
            rows = df[(df["numeric_backend"] == backend) & (df["mode"] == mode)].sort_values("threads")
            if rows.empty:
                continue
            axes[0].plot(rows["threads"], rows["amortized_total_ms"], color=ALGO_COLORS[backend], linestyle=linestyle, linewidth=1.1, label=f"{ALGO_LABELS[backend]} / {mode.replace('_', ' ')}")
            axes[1].plot(rows["threads"], rows["isolated_peak_rss_mb"] / 1024.0, color=ALGO_COLORS[backend], linestyle=linestyle, linewidth=1.1)
    for ax, ylabel, title, label in [
        (axes[0], "Amortized total time (ms)", "Symbolic strategy time", "a"),
        (axes[1], "Isolated RSS (GiB)", "Measured process memory", "b"),
    ]:
        ax.set_xlabel("Threads")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
        clean_axis(ax, grid=True)
        panel_label(ax, label)

    physical = int(df["physical_cores"].max()) if "physical_cores" in df else int(df["threads"].max())
    selected = []
    for mode, backend, label in [
        ("symbolic_reuse_serial", "cpu_serial", "Serial reuse"),
        ("direct_no_symbolic_parallel", "none", "Direct no-symbolic"),
        ("serial_symbolic_parallel_numeric", "cpu_atomic", "Atomic numeric"),
        ("parallel_symbolic_reuse", "cpu_atomic", "Parallel symbolic"),
    ]:
        rows = df[(df["mode"] == mode) & (df["numeric_backend"] == backend)]
        if "threads" in rows and not rows.empty:
            exact = rows[rows["threads"] == physical]
            row = exact.iloc[0] if not exact.empty else rows.sort_values("threads").iloc[-1]
            selected.append((label, bytes_to_gib(float(row["estimated_peak_bytes"]))))
    axes[2].barh([item[0] for item in selected], [item[1] for item in selected], color=[PALETTE["neutral_mid"], PALETTE["ours_large"], PALETTE["baseline_mid"], PALETTE["baseline_dark"]][: len(selected)])
    axes[2].set_xlabel("Estimated peak memory (GiB)")
    axes[2].set_title("Lifecycle peak comparison", loc="left", fontweight="bold")
    clean_axis(axes[2], grid=True)
    panel_label(axes[2], "c")
    fig.suptitle("Symbolic and numeric memory lifecycle", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig05_symbolic_memory_lifecycle"), plt)


def plot_backend_tradeoff(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    df = pd.read_csv(families["symbolic_memory"][1])
    df = df[df["status"] == "PASS"].copy()
    for col in ("threads", "assembly_ms", "extra_memory_bytes", "speedup"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    algorithms = ["cpu_atomic", "cpu_private_csr", "cpu_lock_guard"]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.2), constrained_layout=True)
    for algorithm in algorithms:
        rows = df[df["algorithm"] == algorithm].sort_values("threads")
        if rows.empty:
            continue
        color = ALGO_COLORS[algorithm]
        axes[0].plot(rows["threads"], rows["assembly_ms"], marker="o", markersize=2.5, linewidth=1.1, color=color, label=ALGO_LABELS[algorithm])
        axes[1].plot(rows["threads"], rows["speedup"], marker="o", markersize=2.5, linewidth=1.1, color=color)
        axes[2].plot(rows["threads"], rows["extra_memory_bytes"].map(bytes_to_gib), marker="o", markersize=2.5, linewidth=1.1, color=color)
    for ax, ylabel, title, label in [
        (axes[0], "Assembly time (ms)", "Time", "a"),
        (axes[1], "Speedup vs serial", "Speedup", "b"),
        (axes[2], "Extra memory (GiB)", "Memory", "c"),
    ]:
        ax.set_xlabel("Threads")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
        clean_axis(ax, grid=True)
        panel_label(ax, label)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.8, -0.22), ncol=3)
    fig.suptitle("Numeric backend tradeoff on WindHub", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig06_backend_tradeoff"), plt)


def _load_sparse_window(path: Path, max_points: int, pd):
    df = pd.read_csv(path)
    if len(df) > max_points:
        step = max(1, len(df) // max_points)
        df = df.iloc[::step].copy()
    return df


def plot_sparse_pattern_windows(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    fixed = _load_sparse_window(families["sparse_pattern"][0], 85000, pd)
    auto = _load_sparse_window(families["sparse_pattern"][1], 85000, pd)
    metadata = json.loads(families["sparse_pattern"][2].read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), constrained_layout=True)
    for ax, df, title, label in [
        (axes[0], fixed, "Exact window near matrix origin", "a"),
        (axes[1], auto, "Auto-selected dense diagonal window", "b"),
    ]:
        rows = pd.to_numeric(df["row"], errors="coerce")
        cols = pd.to_numeric(df["col"], errors="coerce")
        row0 = float(rows.min())
        col0 = float(cols.min())
        ax.scatter(cols - col0, rows - row0, s=0.04, c=PALETTE["ink"], alpha=0.72, rasterized=True)
        ax.set_aspect("equal", adjustable="box")
        ax.invert_yaxis()
        ax.set_xlabel("Column offset")
        ax.set_ylabel("Row offset")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.text(0.02, 0.98, f"shown points={len(df):,}", transform=ax.transAxes, va="top", fontsize=6, bbox={"facecolor": "white", "edgecolor": PALETTE["neutral_light"], "pad": 2})
        clean_axis(ax)
        panel_label(ax, label)
    visual = metadata.get("visualization", {})
    fig.suptitle(
        f"WindHub sparse pattern windows; RCM bandwidth {visual.get('rcm_bandwidth', 'n/a')} vs original {visual.get('original_bandwidth', 'n/a')}",
        x=0.02,
        ha="left",
        fontweight="bold",
    )
    return save_publication(fig, figure_base(project_root, "fig07_sparse_pattern_windows"), plt)


def plot_solver_validation(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    rows = []
    for path in families["validation"]:
        frame = pd.read_csv(path)
        solver = "COMSOL" if "comsol" in path.name else "CalculiX"
        case = path.parent.name.replace("cantilever_", "").replace("_", " ")
        tip = frame[frame["probe"] == "free_tip_center"].iloc[0]
        reference_uz_column = next(column for column in frame.columns if column.endswith("_uz") and column != "matlab_uz")
        matlab_uz = float(tip["matlab_uz"])
        reference_uz = float(tip[reference_uz_column])
        free_tip_abs_diff = abs(abs(matlab_uz) - abs(reference_uz))
        free_tip_rel_pct = 100.0 * free_tip_abs_diff / max(abs(reference_uz), 1.0e-30)
        rows.append(
            {
                "solver": solver,
                "case": case,
                "free_tip_abs_deflection_diff": free_tip_abs_diff,
                "free_tip_deflection_rel_pct": free_tip_rel_pct,
            }
        )
    df = pd.DataFrame(rows)
    cases = sorted(df["case"].unique())
    solvers = ["COMSOL", "CalculiX"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), constrained_layout=True)
    x = np.arange(len(cases))
    width = 0.34
    for ax, metric, ylabel, title, panel in [
        (axes[0], "free_tip_deflection_rel_pct", "Free-tip deflection diff (%)", "Free-tip deflection error", "a"),
        (axes[1], "free_tip_abs_deflection_diff", "Free-tip |Uz| absolute diff", "Absolute deflection gap", "b"),
    ]:
        for offset, solver, color in [(-width / 2, "COMSOL", PALETTE["baseline_mid"]), (width / 2, "CalculiX", PALETTE["ours_large"])]:
            values = []
            for case in cases:
                row = df[(df["case"] == case) & (df["solver"] == solver)]
                values.append(max(float(row.iloc[0][metric]), 1.0e-16) if not row.empty else np.nan)
            ax.bar(x + offset, values, width=width, label=solver, color=color)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(cases, rotation=35, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
        clean_axis(ax, grid=True)
        panel_label(ax, panel)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.06, -0.25), ncol=2)
    fig.suptitle("Solve-level validation against independent finite-element references", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig08_solver_validation"), plt)


def plot_basic_metrics_schema_coverage(project_root: Path, families: dict[str, list[Path]]) -> list[Path]:
    plt, np, pd = _import_plotting()
    apply_nature_style(plt)
    rows = []
    for path in families["basic_metrics_schema"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        package = path.parents[1].name.replace("2026-05-", "05-")
        for experiment in data.get("experiments", []):
            family = experiment.get("experiment_family", "")
            records = experiment.get("records", [])
            field_presence = 0
            if records:
                keys = set().union(*(record.keys() for record in records if isinstance(record, dict)))
                for key in ["matrix_correctness_status", "estimated_peak_bytes", "isolated_peak_rss_mb", "serial_direct_baseline_ms", "speedup_vs_serial_direct"]:
                    field_presence += int(key in keys)
            rows.append({"package": package, "family": family, "records": len(records), "fields": field_presence})
    df = pd.DataFrame(rows)
    packages = list(dict.fromkeys(df["package"].tolist()))
    families_order = list(dict.fromkeys(df["family"].tolist()))
    record_matrix = np.zeros((len(families_order), len(packages)))
    field_matrix = np.zeros_like(record_matrix)
    for i, family in enumerate(families_order):
        for j, package in enumerate(packages):
            row = df[(df["family"] == family) & (df["package"] == package)]
            if not row.empty:
                record_matrix[i, j] = float(row.iloc[0]["records"])
                field_matrix[i, j] = float(row.iloc[0]["fields"])

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), constrained_layout=True)
    for ax, values, title, cbar, label, cmap in [
        (axes[0], record_matrix, "Records per package family", "records", "a", "Blues"),
        (axes[1], field_matrix, "Basic-metric field coverage", "fields present", "b", "viridis"),
    ]:
        im = ax.imshow(values, aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(packages)))
        ax.set_xticklabels(packages, rotation=35, ha="right")
        ax.set_yticks(range(len(families_order)))
        ax.set_yticklabels([item.replace("_", " ") for item in families_order])
        ax.set_title(title, loc="left", fontweight="bold")
        panel_label(ax, label)
        fig.colorbar(im, ax=ax, fraction=0.046, label=cbar)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                ax.text(j, i, f"{values[i, j]:.0f}", ha="center", va="center", fontsize=5.8)
    fig.suptitle("Cross-platform v2 package coverage for basic metrics", x=0.02, ha="left", fontweight="bold")
    return save_publication(fig, figure_base(project_root, "fig09_basic_metrics_schema_coverage"), plt)


PLOTTERS = {
    "fig01_benchmark_three_axis_summary": plot_benchmark_three_axis,
    "fig02_cpu_benchmark_dashboard": plot_cpu_benchmark_dashboard,
    "fig03_thread_scaling_platforms": plot_thread_scaling_platforms,
    "fig04_core_profile_comparison": plot_core_profile_comparison,
    "fig05_symbolic_memory_lifecycle": plot_symbolic_memory_lifecycle,
    "fig06_backend_tradeoff": plot_backend_tradeoff,
    "fig07_sparse_pattern_windows": plot_sparse_pattern_windows,
    "fig08_solver_validation": plot_solver_validation,
    "fig09_basic_metrics_schema_coverage": plot_basic_metrics_schema_coverage,
}


def write_manifest(project_root: Path, generated: dict[str, list[Path]], families: dict[str, list[Path]]) -> Path:
    manifest = out_root(project_root) / "manifest.md"
    inventory = legacy_visual_inventory(project_root)
    lines = [
        "# PGSA Nature-Style Figure Redraw Package",
        "",
        "This package redraws project visualizations from existing repository results using the Python backend only.",
        "",
        "## Figure Contract",
        "",
        "- Core conclusion: PGSA algorithm evidence must be reviewed through correctness, memory, assembly-time, platform, symbolic/numeric, sparse-pattern, and solver-validation views.",
        "- Figure archetype: quantitative grid, with one asymmetric mixed-modality sparse-pattern figure.",
        "- Backend: Python / matplotlib only.",
        "- Export contract: SVG keeps editable text; PDF is a vector submission copy; PNG is the visual preview.",
        "- Source data: committed CSV/JSON result artifacts only; no benchmark was rerun by this plotting script.",
        "- Statistics: benchmark panels report deterministic summaries from PASS rows; no inferential statistics are introduced.",
        "- Image integrity: sparse-pattern panels plot row/column pairs from exported CSV windows without local contrast manipulation.",
        "- Detailed figure legends: [figure_legends.md](figure_legends.md).",
        "",
        "## Figures",
        "",
        "| Figure | Archetype | Conclusion | Exports | Source families |",
        "| --- | --- | --- | --- | --- |",
    ]
    specs_by_stem = {spec.stem: spec for spec in FIGURE_SPECS}
    for stem, paths in generated.items():
        spec = specs_by_stem[stem]
        exports = ", ".join(f"[{path.suffix[1:]}]({path.name})" for path in paths)
        lines.append(
            f"| `{stem}` | {spec.family} | {spec.conclusion} | {exports} | {', '.join(spec.source_families)} |"
        )
    lines.extend(["", "## Source Data", "", "| Family | Files |", "| --- | --- |"])
    for family in sorted(families):
        rels = "<br>".join(f"`{path.relative_to(project_root).as_posix()}`" for path in families[family])
        lines.append(f"| `{family}` | {rels} |")
    lines.extend(
        [
            "",
            "## Coverage Audit",
            "",
            f"- Existing visual artifacts under `results/` and `reports/`, excluding this redraw package: {inventory['total']} files.",
            f"- Inventory split: `results/` {inventory['results']} files; `reports/` {inventory['reports']} files.",
            f"- Redraw output: {len(FIGURE_SPECS)} Nature-style figures exported in {len(EXPECTED_FORMATS)} formats each, plus this manifest and detailed legend file.",
            "- Coverage unit: project visualization families and their source CSV/JSON data, not a destructive one-to-one overwrite of legacy snapshots or compiled slide PDFs.",
        ]
    )
    lines.extend(
        [
            "",
            "## QA Notes",
            "",
            "- All plotted outputs are regenerated into this directory and checked for non-zero file size.",
            "- Detailed legends are regenerated from the script and checked for required sections per figure.",
            "- Text is generated by matplotlib with `svg.fonttype = none` and `pdf.fonttype = 42`.",
            "- Legacy `presentation_charts` directories are used only as historical context; this package reads source CSV/JSON instead of copying old image snapshots.",
            "",
        ]
    )
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return manifest


def validate_outputs(project_root: Path) -> None:
    missing = [path for path in planned_nature_outputs(project_root) if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing or empty Nature figure outputs:\n" + "\n".join(str(path) for path in missing))
    for svg in out_root(project_root).glob("*.svg"):
        text = svg.read_text(encoding="utf-8", errors="ignore")
        if "<text" not in text:
            raise RuntimeError(f"SVG text is not editable or no text nodes were found: {svg}")


def build_package(project_root: Path) -> Path:
    families = source_family_inputs(project_root)
    validation = validate_source_inputs(project_root)
    if validation["missing"]:
        raise FileNotFoundError("Missing source data:\n" + "\n".join(validation["missing"]))
    out_root(project_root).mkdir(parents=True, exist_ok=True)
    generated: dict[str, list[Path]] = {}
    for spec in FIGURE_SPECS:
        generated[spec.stem] = PLOTTERS[spec.stem](project_root, families)
    write_figure_legends(project_root)
    manifest = write_manifest(project_root, generated, families)
    validate_outputs(project_root)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    validation = validate_source_inputs(project_root)
    if validation["missing"]:
        raise FileNotFoundError("Missing source data:\n" + "\n".join(validation["missing"]))
    if args.validate_only:
        print("[OK] source inputs are present")
        return 0
    manifest = build_package(project_root)
    print(f"[OK] Nature-style figure package: {manifest.parent}")
    print(f"[OK] Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
