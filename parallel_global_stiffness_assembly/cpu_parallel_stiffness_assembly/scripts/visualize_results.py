#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualize_results.py - 性能结果可视化脚本

读取基准测试结果并生成图表
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
matplotlib.rcParams['axes.unicode_minus'] = False

def load_results(csv_path):
    """加载 CSV 结果文件"""
    return pd.read_csv(csv_path)


def plot_execution_time(df, output_dir, elem_type=None):
    """绘制执行时间对比图"""
    if elem_type:
        df = df[df['Elements'].astype(str).str.contains(elem_type, case=False)]

    fig, ax = plt.subplots(figsize=(10, 6))

    algorithms = df['Algorithm'].unique()
    x = np.arange(len(df['DOFs'].unique()))
    width = 0.15

    for i, algo in enumerate(algorithms):
        data = df[df['Algorithm'] == algo]
        bars = ax.bar(x + i * width, data['Time_ms'], width, label=algo)

    ax.set_xlabel('自由度数 (DOFs)')
    ax.set_ylabel('执行时间 (ms)')
    ax.set_title('各算法执行时间对比')
    ax.set_xticks(x + width * (len(algorithms) - 1) / 2)
    ax.set_xticklabels(df['DOFs'].unique())
    ax.legend()
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    filename = f'exec_time_{elem_type}.png' if elem_type else 'exec_time.png'
    plt.savefig(os.path.join(output_dir, filename), dpi=150)
    plt.close()
    print(f"Saved: {filename}")


def plot_speedup(df, output_dir, elem_type=None):
    """绘制加速比对比图"""
    if elem_type:
        df = df[df['Elements'].astype(str).str.contains(elem_type, case=False)]

    fig, ax = plt.subplots(figsize=(10, 6))

    algorithms = df['Algorithm'].unique()
    x = np.arange(len(df['DOFs'].unique()))
    width = 0.15

    for i, algo in enumerate(algorithms):
        if algo == 'CPU_Serial':
            continue
        data = df[df['Algorithm'] == algo]
        bars = ax.bar(x + i * width, data['Speedup'], width, label=algo)

    ax.set_xlabel('自由度数 (DOFs)')
    ax.set_ylabel('加速比 (相对于 CPU)')
    ax.set_title('GPU 算法加速比对比')
    ax.set_xticks(x + width * (len(algorithms) - 2) / 2)
    ax.set_xticklabels(df['DOFs'].unique())
    ax.legend()
    ax.axhline(y=1, color='r', linestyle='--', alpha=0.5, label='CPU baseline')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    filename = f'speedup_{elem_type}.png' if elem_type else 'speedup.png'
    plt.savefig(os.path.join(output_dir, filename), dpi=150)
    plt.close()
    print(f"Saved: {filename}")


def plot_scaling(df, output_dir):
    """绘制扩展性分析图"""
    fig, ax = plt.subplots(figsize=(10, 6))

    for algo in df['Algorithm'].unique():
        data = df[df['Algorithm'] == algo].sort_values('DOFs')
        ax.plot(data['DOFs'], data['Time_ms'], 'o-', label=algo, markersize=8)

    ax.set_xlabel('自由度数 (DOFs)')
    ax.set_ylabel('执行时间 (ms)')
    ax.set_title('算法扩展性分析')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'scaling.png'), dpi=150)
    plt.close()
    print("Saved: scaling.png")


def generate_summary_table(df, output_dir):
    """生成摘要表格（Markdown）"""
    summary = df.groupby('Algorithm').agg({
        'Time_ms': 'mean',
        'Speedup': 'mean',
        'Error': 'max',
        'Status': lambda x: 'PASS' if all(x == 'PASS') else 'FAIL'
    }).round(3)

    md_content = "# 性能测试结果摘要\n\n"
    md_content += "| 算法 | 平均时间 (ms) | 平均加速比 | 最大误差 | 状态 |\n"
    md_content += "|------|--------------|------------|----------|------|\n"

    for algo, row in summary.iterrows():
        status_emoji = "✅" if row['Status'] == 'PASS' else "❌"
        md_content += f"| {algo} | {row['Time_ms']:.3f} | {row['Speedup']:.2f}x | {row['Error']:.2e} | {status_emoji} {row['Status']} |\n"

    with open(os.path.join(output_dir, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(md_content)

    print("Saved: summary.md")


def main():
    # 默认路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    results_dir = os.path.join(project_dir, 'results')
    figures_dir = os.path.join(results_dir, 'figures')

    os.makedirs(figures_dir, exist_ok=True)

    # 查找最新的结果文件
    csv_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
    if not csv_files:
        # 检查项目根目录
        csv_files = [f for f in os.listdir(project_dir) if f.endswith('.csv')]
        if csv_files:
            results_dir = project_dir

    if not csv_files:
        print("No CSV result files found!")
        print("Run the benchmark first: ./benchmark_assembly")
        sys.exit(1)

    latest_csv = os.path.join(results_dir, sorted(csv_files)[-1])
    print(f"Loading results from: {latest_csv}")

    df = load_results(latest_csv)
    print(f"Loaded {len(df)} records")

    # 生成图表
    print("\nGenerating visualizations...")
    plot_execution_time(df, figures_dir)
    plot_speedup(df, figures_dir)
    plot_scaling(df, figures_dir)
    generate_summary_table(df, figures_dir)

    print("\nDone! All figures saved to:", figures_dir)


if __name__ == "__main__":
    main()
