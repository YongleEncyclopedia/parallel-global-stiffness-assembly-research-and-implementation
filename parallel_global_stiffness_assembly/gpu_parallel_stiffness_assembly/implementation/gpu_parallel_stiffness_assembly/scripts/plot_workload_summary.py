#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_workload_summary.py - 项目工作量统计与可视化
生成紧凑的PPT汇报图表
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['font.size'] = 11

# ============ 项目工作量数据 ============
CODE_STATS = {
    'C++/CUDA 核心代码': 3344,      # headers + sources (2110 + 1234)
    '测试与应用程序': 458,
    'Python 脚本': 842,
    'CMake 构建': 316,
    '技术文档': 491,
}

ALGORITHM_COUNT = {
    'GPU 算法实现': 4,               # Atomic, Block, Scan, WorkQueue
    'CUDA 核函数': 8,                # __global__ kernels
    'CUDA 设备函数': 16,             # __device__ functions
    'C++ 核心类': 14,                # Classes
}

PERFORMANCE_HIGHLIGHTS = {
    '峰值加速比': 97.82,             # x
    '最大测试规模': 397953,          # DOFs
    '数值精度': 1e-16,               # 相对误差
    'GPU 算法数': 4,
}

TEST_SCALES = ['1K', '4K', '36K', '207K', '398K']
SPEEDUPS = [1.9, 8.3, 97.8, 36.2, 35.3]


def plot_code_distribution(output_dir):
    """代码分布饼图 - 紧凑版"""
    fig, ax = plt.subplots(figsize=(6, 4.5))

    labels = list(CODE_STATS.keys())
    sizes = list(CODE_STATS.values())
    total = sum(sizes)

    colors = ['#0d6efd', '#198754', '#fd7e14', '#6c757d', '#dc3545']
    explode = (0.03, 0, 0, 0, 0)

    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=None, autopct='',
        colors=colors, startangle=90, pctdistance=0.75,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )

    # 添加标签和百分比
    for i, (wedge, label, size) in enumerate(zip(wedges, labels, sizes)):
        angle = (wedge.theta2 + wedge.theta1) / 2
        x = 0.7 * np.cos(np.radians(angle))
        y = 0.7 * np.sin(np.radians(angle))
        pct = size / total * 100
        ax.annotate(f'{size:,}\n({pct:.0f}%)',
                   xy=(x, y), ha='center', va='center',
                   fontsize=9, fontweight='bold', color='white')

    # 图例
    legend_labels = [f'{l}' for l in labels]
    ax.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5),
             fontsize=9, frameon=False)

    ax.set_title(f'代码规模分布 (总计 {total:,} 行)', fontsize=13, fontweight='bold', pad=10)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'workload_code_dist.png'),
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print("[OK] Saved: workload_code_dist.png")


def plot_speedup_highlight(output_dir):
    """加速比亮点图 - 紧凑版"""
    fig, ax = plt.subplots(figsize=(7, 4))

    x = np.arange(len(TEST_SCALES))
    colors = ['#6c757d' if s < 50 else '#0d6efd' for s in SPEEDUPS]
    colors[2] = '#dc3545'  # 峰值用红色

    bars = ax.bar(x, SPEEDUPS, color=colors, edgecolor='white', linewidth=1)

    # 标注数值
    for bar, speedup in zip(bars, SPEEDUPS):
        height = bar.get_height()
        ax.annotate(f'{speedup:.1f}x',
                   xy=(bar.get_x() + bar.get_width()/2, height),
                   xytext=(0, 3), textcoords='offset points',
                   ha='center', va='bottom', fontsize=10, fontweight='bold',
                   color='#dc3545' if speedup > 50 else '#333')

    ax.set_xticks(x)
    ax.set_xticklabels([f'{s} DOFs' for s in TEST_SCALES], fontsize=10)
    ax.set_ylabel('加速比 (GPU vs CPU)', fontsize=11, fontweight='bold')
    ax.set_title('GPU 并行组装性能 (RTX 5080, Hex8单元)', fontsize=12, fontweight='bold')

    # 基线
    ax.axhline(y=1, color='#adb5bd', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.text(4.3, 1, 'CPU基线', va='center', fontsize=8, color='#adb5bd')

    # 峰值标注
    ax.annotate('峰值 97.8x', xy=(2, 97.8), xytext=(3.5, 85),
               arrowprops=dict(arrowstyle='->', color='#dc3545', lw=1.5),
               fontsize=10, fontweight='bold', color='#dc3545')

    ax.set_ylim(0, 115)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'workload_speedup.png'),
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print("[OK] Saved: workload_speedup.png")


def plot_project_summary(output_dir):
    """项目概览卡片图 - 紧凑版"""
    fig, axes = plt.subplots(1, 4, figsize=(10, 2.5))

    metrics = [
        ('5,451', '代码总行数', '#0d6efd'),
        ('4', 'GPU算法', '#198754'),
        ('97.8x', '峰值加速比', '#dc3545'),
        ('< 1e-15', '数值精度', '#fd7e14'),
    ]

    for ax, (value, label, color) in zip(axes, metrics):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # 背景圆角矩形
        rect = mpatches.FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                                        boxstyle="round,pad=0.05,rounding_size=0.1",
                                        facecolor=color, alpha=0.1,
                                        edgecolor=color, linewidth=2)
        ax.add_patch(rect)

        # 数值
        ax.text(0.5, 0.6, value, ha='center', va='center',
               fontsize=20, fontweight='bold', color=color)
        # 标签
        ax.text(0.5, 0.25, label, ha='center', va='center',
               fontsize=11, color='#333')

    fig.suptitle('GPU 并行刚度矩阵组装 - 项目成果概览', fontsize=13, fontweight='bold', y=1.05)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'workload_summary_cards.png'),
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print("[OK] Saved: workload_summary_cards.png")


def plot_combined_compact(output_dir):
    """组合紧凑图 - 适合单页PPT"""
    fig = plt.figure(figsize=(12, 5))

    # 左侧: 代码分布
    ax1 = fig.add_subplot(1, 2, 1)
    labels = list(CODE_STATS.keys())
    sizes = list(CODE_STATS.values())
    total = sum(sizes)
    colors = ['#0d6efd', '#198754', '#fd7e14', '#6c757d', '#dc3545']

    wedges, texts, autotexts = ax1.pie(
        sizes, labels=None, autopct='',
        colors=colors, startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )

    # 简化图例
    legend_labels = [f'{l} ({s:,})' for l, s in zip(labels, sizes)]
    ax1.legend(wedges, legend_labels, loc='upper left', bbox_to_anchor=(-0.1, 1),
              fontsize=8, frameon=False)
    ax1.set_title(f'代码规模: {total:,} 行', fontsize=12, fontweight='bold')

    # 右侧: 性能加速比
    ax2 = fig.add_subplot(1, 2, 2)
    x = np.arange(len(TEST_SCALES))
    colors_bar = ['#6c757d' if s < 50 else '#0d6efd' for s in SPEEDUPS]
    colors_bar[2] = '#dc3545'

    bars = ax2.bar(x, SPEEDUPS, color=colors_bar, edgecolor='white', linewidth=1)

    for bar, speedup in zip(bars, SPEEDUPS):
        height = bar.get_height()
        ax2.annotate(f'{speedup:.0f}x' if speedup > 10 else f'{speedup:.1f}x',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 2), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold',
                    color='#dc3545' if speedup > 50 else '#333')

    ax2.set_xticks(x)
    ax2.set_xticklabels(TEST_SCALES, fontsize=9)
    ax2.set_xlabel('自由度数 (DOFs)', fontsize=10)
    ax2.set_ylabel('加速比', fontsize=10)
    ax2.set_title('GPU 加速性能 (RTX 5080)', fontsize=12, fontweight='bold')
    ax2.axhline(y=1, color='#adb5bd', linestyle='--', linewidth=1, alpha=0.7)
    ax2.set_ylim(0, 115)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'workload_combined.png'),
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print("[OK] Saved: workload_combined.png")


def generate_presentation_text():
    """生成汇报陈述词"""
    text = """
================================================================================
                     GPU 并行刚度矩阵组装 - 工作汇报陈述词
================================================================================

【项目规模】
  - 代码总量: 5,451 行 (C++/CUDA 3,344 + Python 842 + CMake 316 + 测试 458 + 文档 491)
  - 核心算法: 4 种 GPU 并行组装算法 (Atomic/Block/Scan/WorkQueue)
  - CUDA 实现: 8 个核函数 + 16 个设备函数

【性能成果】
  - 峰值加速比: 97.8x (36K DOFs 规模, GPU Atomic 算法)
  - 大规模稳定加速: 35x (200K~400K DOFs)
  - 数值精度: 相对误差 < 1e-15 (接近机器精度)

【技术亮点】
  - Warp 级聚合原子操作, 减少全局内存冲突
  - Grid-stride 循环模式, 最大化 SM 利用率
  - 按项计算单刚, 降低寄存器压力
  - 支持 Hex8/Tet4 单元, 可扩展至百万自由度

【测试覆盖】
  - 5 个测试规模: 1K → 4K → 36K → 207K → 398K DOFs
  - 完整正确性验证: GPU 结果与 CPU 基线对比
  - PBT 属性验证: 6 项全部通过

================================================================================
                            建议的 PPT 陈述 (30秒版)
================================================================================

"本项目实现了 GPU 并行刚度矩阵组装框架，代码量约 5,500 行，包含 4 种 GPU 算法。
在 RTX 5080 上测试，峰值加速比达 97.8 倍，大规模问题稳定在 35 倍加速。
数值精度保持机器精度级别，已通过完整的正确性和属性验证。"

================================================================================
"""
    return text


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_dir = os.path.join(project_dir, 'results', 'figures')

    os.makedirs(output_dir, exist_ok=True)

    print("Generating workload statistics charts...")
    print("-" * 50)

    plot_code_distribution(output_dir)
    plot_speedup_highlight(output_dir)
    plot_project_summary(output_dir)
    plot_combined_compact(output_dir)

    # 输出陈述词
    presentation_text = generate_presentation_text()
    print(presentation_text)

    # 保存陈述词到文件
    with open(os.path.join(output_dir, 'presentation_notes.txt'), 'w', encoding='utf-8') as f:
        f.write(presentation_text)
    print("[OK] Saved: presentation_notes.txt")

    print("-" * 50)
    print(f"\n[SUCCESS] All charts saved to: {output_dir}")


if __name__ == "__main__":
    main()
