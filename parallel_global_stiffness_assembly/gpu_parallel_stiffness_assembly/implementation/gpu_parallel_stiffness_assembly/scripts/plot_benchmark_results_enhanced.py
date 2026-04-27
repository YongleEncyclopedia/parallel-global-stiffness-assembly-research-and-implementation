#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_benchmark_results_enhanced.py - 增强版性能结果可视化脚本

基于 2026-01-30 RTX 5080 实测数据生成美观的对比图表
- 计算耗时以科学计数法标注
- 专业配色方案
- 清晰的图例和标注
- 单元类型: Hex8 (八节点六面体)
"""

# 单元类型配置
ELEMENT_TYPE = "Hex8"
ELEMENT_TYPE_CN = "八节点六面体"

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.ticker import ScalarFormatter

# 设置中文字体和专业风格
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'
plt.rcParams['axes.edgecolor'] = '#dee2e6'
plt.rcParams['grid.color'] = '#dee2e6'
plt.rcParams['grid.alpha'] = 0.7
plt.rcParams['font.size'] = 11

# 专业配色方案
COLORS = {
    'CPU_Serial': '#6c757d',      # 灰色 - CPU基线
    'Atomic_WarpAgg': '#0d6efd',  # 蓝色 - Atomic
    'Block_Parallel': '#198754',  # 绿色 - Block
    'Work_Queue': '#fd7e14'       # 橙色 - WorkQueue
}

ALGO_LABELS = {
    'CPU_Serial': 'CPU Serial',
    'Atomic_WarpAgg': 'GPU Atomic',
    'Block_Parallel': 'GPU Block',
    'Work_Queue': 'GPU WorkQueue'
}

def format_sci(value, precision=2):
    """格式化为科学计数法字符串"""
    if value == 0:
        return "0"
    exp = int(np.floor(np.log10(abs(value))))
    mantissa = value / (10 ** exp)
    if exp == 0:
        return f"{value:.{precision}f}"
    return f"{mantissa:.{precision}f}e{exp}"


def plot_execution_time_enhanced(df, output_dir):
    """绘制执行时间对比图 - 增强版"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # 按 DOFs 分组
    dof_groups = df.groupby('DOFs')
    dof_values = sorted(df['DOFs'].unique())
    x = np.arange(len(dof_values))
    width = 0.2

    algorithms = ['CPU_Serial', 'Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue']

    for i, algo in enumerate(algorithms):
        times = []
        for dof in dof_values:
            time_val = df[(df['DOFs'] == dof) & (df['Algorithm'] == algo)]['Time_ms'].values
            times.append(time_val[0] if len(time_val) > 0 else 0)

        bars = ax.bar(x + i * width, times, width,
                     label=ALGO_LABELS[algo],
                     color=COLORS[algo],
                     edgecolor='white',
                     linewidth=0.5)

        # 在柱子上标注科学计数法耗时
        for j, (bar, time_val) in enumerate(zip(bars, times)):
            height = bar.get_height()
            if height > 0:
                # 根据柱子高度调整标注位置
                if height < 1:
                    label = f"{time_val:.3f}"
                else:
                    label = format_sci(time_val)

                ax.annotate(label,
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=7,
                           rotation=45,
                           color=COLORS[algo])

    ax.set_xlabel('自由度数 (DOFs)', fontsize=12, fontweight='bold')
    ax.set_ylabel('执行时间 (ms)', fontsize=12, fontweight='bold')
    ax.set_title(f'GPU 并行刚度矩阵组装 - 执行时间对比 ({ELEMENT_TYPE} 单元)\n(RTX 5080, CUDA 13.1, 2026-01-30 实测)',
                fontsize=14, fontweight='bold', pad=15)

    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([f'{d:,}' for d in dof_values])
    ax.set_yscale('log')
    ax.legend(loc='upper left', framealpha=0.95, edgecolor='#dee2e6')
    ax.grid(True, alpha=0.3, axis='y')

    # 添加硬件信息水印
    ax.text(0.98, 0.02, f'RTX 5080 | sm_120 | CUDA 13.1 | {ELEMENT_TYPE}',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, color='#adb5bd', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'exec_time_enhanced.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("[OK] Saved: exec_time_enhanced.png")


def plot_speedup_enhanced(df, output_dir):
    """绘制加速比对比图 - 增强版"""
    fig, ax = plt.subplots(figsize=(14, 8))

    dof_values = sorted(df['DOFs'].unique())
    x = np.arange(len(dof_values))
    width = 0.25

    gpu_algorithms = ['Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue']

    for i, algo in enumerate(gpu_algorithms):
        speedups = []
        for dof in dof_values:
            speedup_val = df[(df['DOFs'] == dof) & (df['Algorithm'] == algo)]['Speedup'].values
            speedups.append(speedup_val[0] if len(speedup_val) > 0 else 0)

        bars = ax.bar(x + i * width, speedups, width,
                     label=ALGO_LABELS[algo],
                     color=COLORS[algo],
                     edgecolor='white',
                     linewidth=0.5)

        # 在柱子上标注加速比
        for bar, speedup in zip(bars, speedups):
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{speedup:.1f}×',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=9,
                           fontweight='bold',
                           color=COLORS[algo])

    ax.set_xlabel('自由度数 (DOFs)', fontsize=12, fontweight='bold')
    ax.set_ylabel('加速比 (相对于 CPU Serial)', fontsize=12, fontweight='bold')
    ax.set_title(f'GPU 算法加速比对比 ({ELEMENT_TYPE} 单元)\n(RTX 5080, CUDA 13.1, 2026-01-30 实测)',
                fontsize=14, fontweight='bold', pad=15)

    ax.set_xticks(x + width)
    ax.set_xticklabels([f'{d:,}' for d in dof_values])

    # CPU 基线
    ax.axhline(y=1, color='#dc3545', linestyle='--', linewidth=2, alpha=0.7, label='CPU Baseline (1×)')

    # 标记峰值加速比
    max_speedup = df[df['Algorithm'] != 'CPU_Serial']['Speedup'].max()
    max_row = df[df['Speedup'] == max_speedup].iloc[0]
    ax.axhline(y=max_speedup, color='#28a745', linestyle=':', linewidth=1.5, alpha=0.5)
    ax.text(len(dof_values) - 0.5, max_speedup + 2, f'峰值: {max_speedup:.1f}× @ {max_row["DOFs"]:,} DOFs',
            ha='right', fontsize=10, color='#28a745', fontweight='bold')

    ax.legend(loc='upper right', framealpha=0.95, edgecolor='#dee2e6')
    ax.grid(True, alpha=0.3, axis='y')

    ax.text(0.98, 0.02, 'RTX 5080 | sm_120 | CUDA 13.1',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, color='#adb5bd', style='italic')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'speedup_enhanced.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("[OK] Saved: speedup_enhanced.png")


def plot_scaling_enhanced(df, output_dir):
    """绘制扩展性分析图 - 增强版"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    algorithms = ['CPU_Serial', 'Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue']
    markers = ['s', 'o', '^', 'D']

    # 左图：执行时间 vs DOFs (log-log)
    for algo, marker in zip(algorithms, markers):
        data = df[df['Algorithm'] == algo].sort_values('DOFs')
        ax1.plot(data['DOFs'], data['Time_ms'],
                marker=marker, markersize=10, linewidth=2.5,
                label=ALGO_LABELS[algo], color=COLORS[algo],
                markeredgecolor='white', markeredgewidth=1)

        # 在最后一个点标注科学计数法耗时
        last_row = data.iloc[-1]
        time_label = format_sci(last_row['Time_ms'])
        ax1.annotate(f'{time_label} ms',
                    xy=(last_row['DOFs'], last_row['Time_ms']),
                    xytext=(10, 0),
                    textcoords='offset points',
                    fontsize=9,
                    color=COLORS[algo],
                    fontweight='bold')

    ax1.set_xlabel('自由度数 (DOFs)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('执行时间 (ms)', fontsize=12, fontweight='bold')
    ax1.set_title('算法扩展性分析 - 执行时间', fontsize=13, fontweight='bold')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.legend(loc='upper left', framealpha=0.95)
    ax1.grid(True, alpha=0.3)

    # 右图：加速比 vs DOFs
    gpu_algos = ['Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue']
    for algo, marker in zip(gpu_algos, markers[1:]):
        data = df[df['Algorithm'] == algo].sort_values('DOFs')
        ax2.plot(data['DOFs'], data['Speedup'],
                marker=marker, markersize=10, linewidth=2.5,
                label=ALGO_LABELS[algo], color=COLORS[algo],
                markeredgecolor='white', markeredgewidth=1)

        # 标注每个点的加速比
        for _, row in data.iterrows():
            ax2.annotate(f'{row["Speedup"]:.1f}×',
                        xy=(row['DOFs'], row['Speedup']),
                        xytext=(0, 8),
                        textcoords='offset points',
                        ha='center',
                        fontsize=8,
                        color=COLORS[algo])

    ax2.set_xlabel('自由度数 (DOFs)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('加速比', fontsize=12, fontweight='bold')
    ax2.set_title('算法扩展性分析 - 加速比', fontsize=13, fontweight='bold')
    ax2.set_xscale('log')
    ax2.axhline(y=1, color='#dc3545', linestyle='--', linewidth=2, alpha=0.5, label='CPU Baseline')
    ax2.legend(loc='upper right', framealpha=0.95)
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f'GPU 并行刚度矩阵组装 - 扩展性分析 ({ELEMENT_TYPE} 单元)\n(RTX 5080, CUDA 13.1, 2026-01-30 实测)',
                fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'scaling_enhanced.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("[OK] Saved: scaling_enhanced.png")


def plot_heatmap_comparison(df, output_dir):
    """绘制热力图对比 - 新增"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 准备数据透视表
    time_pivot = df.pivot(index='Algorithm', columns='DOFs', values='Time_ms')
    speedup_pivot = df.pivot(index='Algorithm', columns='DOFs', values='Speedup')

    # 排序算法
    algo_order = ['CPU_Serial', 'Atomic_WarpAgg', 'Block_Parallel', 'Work_Queue']
    time_pivot = time_pivot.reindex(algo_order)
    speedup_pivot = speedup_pivot.reindex(algo_order)

    # 左图：执行时间热力图
    im1 = ax1.imshow(np.log10(time_pivot.values + 0.001), cmap='YlOrRd', aspect='auto')
    ax1.set_xticks(range(len(time_pivot.columns)))
    ax1.set_xticklabels([f'{c:,}' for c in time_pivot.columns], rotation=45, ha='right')
    ax1.set_yticks(range(len(time_pivot.index)))
    ax1.set_yticklabels([ALGO_LABELS[a] for a in time_pivot.index])
    ax1.set_xlabel('DOFs', fontweight='bold')
    ax1.set_title('执行时间 (ms) - 对数尺度', fontweight='bold')

    # 在热力图上标注数值（科学计数法）
    for i in range(len(time_pivot.index)):
        for j in range(len(time_pivot.columns)):
            val = time_pivot.iloc[i, j]
            text = format_sci(val, 1) if val >= 1 else f'{val:.3f}'
            ax1.text(j, i, text, ha='center', va='center', fontsize=8,
                    color='white' if val > 10 else 'black', fontweight='bold')

    # 右图：加速比热力图
    im2 = ax2.imshow(speedup_pivot.values, cmap='YlGn', aspect='auto')
    ax2.set_xticks(range(len(speedup_pivot.columns)))
    ax2.set_xticklabels([f'{c:,}' for c in speedup_pivot.columns], rotation=45, ha='right')
    ax2.set_yticks(range(len(speedup_pivot.index)))
    ax2.set_yticklabels([ALGO_LABELS[a] for a in speedup_pivot.index])
    ax2.set_xlabel('DOFs', fontweight='bold')
    ax2.set_title('加速比 (相对于CPU)', fontweight='bold')

    # 在热力图上标注数值
    for i in range(len(speedup_pivot.index)):
        for j in range(len(speedup_pivot.columns)):
            val = speedup_pivot.iloc[i, j]
            ax2.text(j, i, f'{val:.1f}×', ha='center', va='center', fontsize=9,
                    color='white' if val > 50 else 'black', fontweight='bold')

    fig.suptitle(f'GPU 并行刚度矩阵组装 - 性能热力图 ({ELEMENT_TYPE} 单元)\n(RTX 5080, CUDA 13.1, 2026-01-30 实测)',
                fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heatmap_comparison.png'), dpi=200, bbox_inches='tight')
    plt.close()
    print("[OK] Saved: heatmap_comparison.png")


def generate_enhanced_summary(df, output_dir):
    """生成增强版摘要报告"""

    # 计算统计数据
    gpu_df = df[df['Algorithm'] != 'CPU_Serial']
    max_speedup = gpu_df['Speedup'].max()
    max_speedup_row = df[df['Speedup'] == max_speedup].iloc[0]

    best_algo_by_scale = []
    for dof in sorted(df['DOFs'].unique()):
        scale_df = df[(df['DOFs'] == dof) & (df['Algorithm'] != 'CPU_Serial')]
        best = scale_df.loc[scale_df['Time_ms'].idxmin()]
        best_algo_by_scale.append({
            'DOFs': dof,
            'Best_Algo': best['Algorithm'],
            'Time_ms': best['Time_ms'],
            'Speedup': best['Speedup']
        })

    md_content = f"""# 🚀 GPU 并行刚度矩阵组装 - 性能测试报告

## 📊 测试环境

| 项目 | 配置 |
|------|------|
| **GPU** | NVIDIA GeForce RTX 5080 |
| **计算能力** | sm_120 (Compute 12.0) |
| **CUDA** | v13.1.115 |
| **编译器** | MSVC 19.44 (VS 2022) |
| **单元类型** | {ELEMENT_TYPE} ({ELEMENT_TYPE_CN}) |
| **测试日期** | 2026-01-30 |

---

## 📈 性能摘要

### 峰值性能
"""
    md_content += f"- **最高加速比**: **{max_speedup:.2f}×** ({ALGO_LABELS[max_speedup_row['Algorithm']]} @ {max_speedup_row['DOFs']:,} DOFs)\n"
    md_content += f"- **最快 GPU 时间**: {gpu_df['Time_ms'].min():.3f} ms\n"
    md_content += f"- **最大测试规模**: {df['DOFs'].max():,} DOFs ({df['Elements'].max():,} 单元)\n\n"

    md_content += "### 各规模最佳算法\n\n"
    md_content += "| 规模 | DOFs | 最佳算法 | 执行时间 | 加速比 |\n"
    md_content += "|------|------|----------|----------|--------|\n"

    scale_names = ['Tiny', 'Small', 'Medium', 'Large', 'XLarge']
    for i, row in enumerate(best_algo_by_scale):
        time_sci = format_sci(row['Time_ms'])
        md_content += f"| {scale_names[i]} | {row['DOFs']:,} | {ALGO_LABELS[row['Best_Algo']]} | {time_sci} ms | {row['Speedup']:.1f}× |\n"

    md_content += "\n---\n\n## 📋 完整测试数据\n\n"
    md_content += "| 算法 | 单元数 | DOFs | 时间 (ms) | 加速比 | 误差 | 状态 |\n"
    md_content += "|------|--------|------|-----------|--------|------|------|\n"

    for _, row in df.iterrows():
        time_str = format_sci(row['Time_ms']) if row['Time_ms'] >= 1 else f"{row['Time_ms']:.3f}"
        error_str = f"{row['Error']:.2e}"
        status_emoji = "✅" if row['Status'] == 'PASS' else "❌"
        md_content += f"| {ALGO_LABELS.get(row['Algorithm'], row['Algorithm'])} | {row['Elements']:,} | {row['DOFs']:,} | {time_str} | {row['Speedup']:.2f}× | {error_str} | {status_emoji} |\n"

    md_content += f"""
---

## 🔍 关键发现

1. **峰值加速比出现在中等规模** (36K DOFs)，达到 **97.82×**，此时 GPU 并行度充分利用且未受内存带宽限制

2. **Atomic 与 Block 算法性能相当**，在所有规模下差异 < 5%

3. **WorkQueue 算法适合非结构化网格**，动态调度开销在结构化网格上导致性能略低

4. **大规模问题 (>200K DOFs)** 加速比稳定在 **35×** 左右，受限于 GPU 内存带宽

5. **数值精度优秀**，所有 GPU 算法相对误差 < 1.1e-16（接近机器精度）

---

## 📁 生成的图表

- `exec_time_enhanced.png` - 执行时间对比图（科学计数法标注）
- `speedup_enhanced.png` - 加速比对比图
- `scaling_enhanced.png` - 扩展性分析图
- `heatmap_comparison.png` - 性能热力图

---

*Generated: 2026-01-30 | RTX 5080 实测数据 | 单元类型: {ELEMENT_TYPE}*
"""

    with open(os.path.join(output_dir, 'summary_enhanced.md'), 'w', encoding='utf-8') as f:
        f.write(md_content)

    print("[OK] Saved: summary_enhanced.md")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(project_dir, 'results')
    figures_dir = os.path.join(results_dir, 'figures')

    os.makedirs(figures_dir, exist_ok=True)

    # 加载实测数据
    csv_path = os.path.join(results_dir, 'benchmark_results_2026-01-30.csv')
    if not os.path.exists(csv_path):
        print(f"Error: Data file not found: {csv_path}")
        return

    print(f"Loading actual measurement data from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records\n")

    print("Generating enhanced visualizations...")
    print("-" * 40)

    plot_execution_time_enhanced(df, figures_dir)
    plot_speedup_enhanced(df, figures_dir)
    plot_scaling_enhanced(df, figures_dir)
    plot_heatmap_comparison(df, figures_dir)
    generate_enhanced_summary(df, figures_dir)

    print("-" * 40)
    print(f"\n[SUCCESS] All enhanced figures saved to: {figures_dir}")


if __name__ == "__main__":
    main()
