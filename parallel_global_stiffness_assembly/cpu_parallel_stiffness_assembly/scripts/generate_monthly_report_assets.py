#!/usr/bin/env python3
"""Generate slide-ready visual assets for monthly CPU FEM assembly report."""
from pathlib import Path
import math
import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation_assets" / "2026-04-monthly-report"
OUT.mkdir(parents=True, exist_ok=True)

# Prefer macOS Chinese fonts; fall back gracefully.
font_candidates = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]
for fp in font_candidates:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        prop = font_manager.FontProperties(fname=fp)
        plt.rcParams["font.family"] = prop.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160

BG = "#08111f"
PANEL = "#0f172a"
PANEL2 = "#111827"
GRID = "#233044"
TEXT = "#e5f2ff"
MUTED = "#94a3b8"
CYAN = "#22d3ee"
BLUE = "#60a5fa"
GREEN = "#34d399"
AMBER = "#fbbf24"
ORANGE = "#fb923c"
VIOLET = "#a78bfa"
ROSE = "#fb7185"

metrics_groups = {
    "CPU算法": {"files": 7, "lines": 527, "color": GREEN},
    "核心数据结构": {"files": 10, "lines": 864, "color": CYAN},
    "组装框架": {"files": 9, "lines": 422, "color": BLUE},
    "Benchmark CLI": {"files": 1, "lines": 681, "color": AMBER},
    "实验脚本": {"files": 5, "lines": 974, "color": ORANGE},
    "测试与正确性": {"files": 5, "lines": 250, "color": ROSE},
    "CUDA历史/验证": {"files": 8, "lines": 1908, "color": VIOLET},
    "构建系统": {"files": 5, "lines": 298, "color": "#38bdf8"},
    "其他辅助": {"files": 18, "lines": 939, "color": "#64748b"},
}
alg_lines = [
    ("serial", 24, "串行CSR基线", "无同步；正确性/加速比参考", CYAN),
    ("atomic", 49, "OpenMP atomic", "共享CSR原子累加", AMBER),
    ("private_csr", 86, "线程私有CSR", "无冲突写入 + nnz归并", GREEN),
    ("coo_sort_reduce", 110, "COO排序规约", "贡献列表 + sort/reduce", ORANGE),
    ("coloring", 108, "图着色", "同色单元无共享节点并行", VIOLET),
    ("row_owner", 97, "行拥有者", "owner-computes；按行独占写", ROSE),
]

def setup_fig(w=16, h=9):
    fig = plt.figure(figsize=(w, h), facecolor=BG)
    ax = plt.axes([0, 0, 1, 1])
    ax.set_xlim(0, 1600)
    ax.set_ylim(0, 900)
    ax.axis("off")
    # subtle grid
    for x in range(0, 1601, 80):
        ax.plot([x, x], [0, 900], color=GRID, lw=0.45, alpha=0.35)
    for y in range(0, 901, 80):
        ax.plot([0, 1600], [y, y], color=GRID, lw=0.45, alpha=0.35)
    return fig, ax

def rounded(ax, x, y, w, h, fc=PANEL, ec=CYAN, lw=1.8, r=18, alpha=0.96):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.012,rounding_size={r}",
                       linewidth=lw, edgecolor=ec, facecolor=fc, alpha=alpha)
    ax.add_patch(p)
    return p

def label(ax, x, y, s, size=22, color=TEXT, weight="normal", ha="left", va="center", alpha=1, rotation=0):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, alpha=alpha, rotation=rotation)

def arrow(ax, x1, y1, x2, y2, color=CYAN, lw=2.2, style="-|>", rad=0.0, alpha=0.9, ls="-"):
    a = FancyArrowPatch((x1,y1), (x2,y2), arrowstyle=style, mutation_scale=16,
                        lw=lw, color=color, alpha=alpha, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)


def save(fig, name):
    png = OUT / f"{name}.png"
    svg = OUT / f"{name}.svg"
    fig.savefig(png, facecolor=BG, bbox_inches="tight", pad_inches=0.08, dpi=220)
    fig.savefig(svg, facecolor=BG, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return png, svg


def fig_architecture():
    fig, ax = setup_fig()
    label(ax, 80, 840, "CPU并行整体刚度矩阵组装平台：代码结构", 34, TEXT, "bold")
    label(ax, 82, 805, "统一网格 / CSR / Scatter Plan / Kernel，6类CPU算法在同一Benchmark入口下可复现实验", 17, MUTED)
    # layers
    layers = [
        ("输入与数据", 70, 620, [("规则网格 Tet4/Hex8", CYAN), ("Abaqus .inp", CYAN), ("3 DOF/node", CYAN)]),
        ("核心数据结构", 410, 620, [("Mesh", BLUE), ("DofMap", BLUE), ("CSR Matrix", BLUE), ("SoA", BLUE)]),
        ("组装框架", 740, 620, [("AssemblyPlan", VIOLET), ("Element Kernels", VIOLET), ("AssemblerFactory", VIOLET)]),
        ("CPU算法后端", 1070, 590, [("serial", GREEN), ("atomic", AMBER), ("private_csr", GREEN), ("coo_sort_reduce", ORANGE), ("coloring", VIOLET), ("row_owner", ROSE)]),
    ]
    for title,x,y,items in layers:
        rounded(ax,x,y,250,190,fc="#0b1728",ec=items[0][1])
        label(ax,x+20,y+160,title,22,TEXT,"bold")
        for i,(it,c) in enumerate(items):
            rounded(ax,x+20,y+112-i*32,205,24,fc="#111827",ec=c,lw=1.0,r=8,alpha=0.9)
            label(ax,x+32,y+124-i*32,it,13,TEXT)
    arrow(ax, 320,710,410,710, CYAN)
    arrow(ax, 660,710,740,710, BLUE)
    arrow(ax, 990,710,1070,710, VIOLET)
    # bottom pipeline
    rounded(ax, 145, 330, 1310, 170, fc="#0b1728", ec="#334155", lw=1.2, r=22)
    steps = [("解析网格", CYAN), ("建立DOF映射", BLUE), ("生成CSR结构", VIOLET), ("预计算scatter plan", AMBER), ("单元局部刚度ke", GREEN), ("并行写回/规约", ROSE), ("CSV/JSON/图表", ORANGE)]
    sx=210
    for i,(s,c) in enumerate(steps):
        rounded(ax, sx+i*175, 390, 140, 55, fc="#111827", ec=c, lw=1.8, r=14)
        label(ax, sx+i*175+70, 418, s, 14, TEXT, "bold", ha="center")
        if i < len(steps)-1:
            arrow(ax, sx+i*175+145, 418, sx+(i+1)*175-8, 418, c, lw=1.8)
    label(ax, 160, 480, "运行主链路", 17, MUTED, "bold")
    # stats cards
    cards=[("68", "源码/配置文件", CYAN), ("6,863", "统计行数", GREEN), ("6", "CPU组装算法", AMBER), ("统一", "Benchmark口径", ROSE)]
    for i,(num,txt,c) in enumerate(cards):
        x=220+i*300
        rounded(ax,x,120,220,120,fc="#0b1728",ec=c,lw=1.8,r=18)
        label(ax,x+110,180,num,35,c,"bold",ha="center")
        label(ax,x+110,145,txt,15,MUTED,ha="center")
    return save(fig, "01_code_architecture_overview")


def fig_workload():
    fig = plt.figure(figsize=(16,9), facecolor=BG)
    gs = fig.add_gridspec(2, 2, left=0.06, right=0.96, top=0.86, bottom=0.10, hspace=0.24, wspace=0.18)
    fig.text(0.06,0.935,"代码工作量与模块分布",fontsize=32,color=TEXT,fontweight="bold")
    fig.text(0.06,0.895,"CPU主线项目：68个源码/配置文件，约6,863行；包含算法、数据结构、Benchmark、绘图与验证体系",fontsize=15,color=MUTED)
    ax1=fig.add_subplot(gs[:,0], facecolor=PANEL)
    names=list(metrics_groups.keys())
    lines=[metrics_groups[n]["lines"] for n in names]
    colors=[metrics_groups[n]["color"] for n in names]
    y=range(len(names))
    ax1.barh(y, lines, color=colors, alpha=0.85)
    ax1.set_yticks(y, names, color=TEXT, fontsize=12)
    ax1.invert_yaxis()
    ax1.set_xlabel("Lines", color=MUTED)
    ax1.tick_params(colors=MUTED)
    ax1.grid(axis='x', color=GRID, alpha=0.45)
    for spine in ax1.spines.values(): spine.set_color("#334155")
    ax1.set_title("按模块统计的代码行数", color=TEXT, fontsize=18, pad=14, fontweight='bold')
    for i,v in enumerate(lines):
        ax1.text(v+35,i,f"{v} 行 / {metrics_groups[names[i]]['files']} 文件",va='center',color=TEXT,fontsize=11)
    ax2=fig.add_subplot(gs[0,1], facecolor=PANEL)
    alg_names=[a[0] for a in alg_lines]
    alg_vals=[a[1] for a in alg_lines]
    alg_cols=[a[4] for a in alg_lines]
    ax2.bar(range(len(alg_names)), alg_vals, color=alg_cols, alpha=0.9)
    ax2.set_xticks(range(len(alg_names)), alg_names, rotation=25, ha='right', color=TEXT, fontsize=10)
    ax2.tick_params(colors=MUTED)
    ax2.grid(axis='y', color=GRID, alpha=0.45)
    for spine in ax2.spines.values(): spine.set_color("#334155")
    ax2.set_title("6类CPU算法实现规模", color=TEXT, fontsize=17, pad=12, fontweight='bold')
    for i,v in enumerate(alg_vals): ax2.text(i,v+4,str(v),ha='center',color=TEXT,fontsize=10)
    ax3=fig.add_subplot(gs[1,1], facecolor=PANEL)
    labels=[".cpp", ".h", ".py", ".cu/.cuh", "脚本/构建"]
    vals=[2178,930,974,1908,108+467+129+35+134]
    cols=[BLUE,CYAN,ORANGE,VIOLET,AMBER]
    wedges, texts = ax3.pie(vals, colors=cols, startangle=120, wedgeprops={'width':0.42,'edgecolor':BG,'linewidth':2})
    ax3.set_title("语言/文件类型占比", color=TEXT, fontsize=17, pad=12, fontweight='bold')
    ax3.text(0,0,"6,863\nlines",ha='center',va='center',fontsize=22,color=TEXT,fontweight='bold')
    ax3.legend(wedges, [f"{l}: {v}" for l,v in zip(labels,vals)], loc='center left', bbox_to_anchor=(0.88,0.5), frameon=False, labelcolor=TEXT, fontsize=10)
    return save(fig, "02_code_workload_metrics")


def fig_principle():
    fig, ax = setup_fig()
    label(ax, 80, 840, "CPU算法基本原理：从单元贡献到全局CSR矩阵", 32, TEXT, "bold")
    label(ax, 82, 805, "核心挑战：多个单元会同时贡献到同一个全局自由度条目 K[i,j]，并行实现必须处理写冲突", 16, MUTED)
    # central matrix / elements
    rounded(ax, 80, 580, 280, 150, fc="#0b1728", ec=CYAN)
    label(ax, 220, 700, "有限元网格", 20, TEXT, "bold", ha="center")
    for i,(x,y,c) in enumerate([(135,630,CYAN),(210,655,BLUE),(285,625,GREEN),(210,610,AMBER)]):
        ax.add_patch(Circle((x,y),16,facecolor=c,edgecolor='white',lw=1.0,alpha=0.9))
    ax.plot([135,210,285,210,135],[630,655,625,610,630],color="#cbd5e1",lw=2)
    label(ax, 220, 595, "单元 e → 局部刚度矩阵 ke", 13, MUTED, ha="center")
    rounded(ax, 465, 570, 270, 170, fc="#0b1728", ec=VIOLET)
    label(ax, 600, 710, "局部到全局映射", 20, TEXT, "bold", ha="center")
    for i in range(4):
        for j in range(4):
            color = [CYAN,BLUE,GREEN,AMBER][(i+j)%4]
            ax.add_patch(Rectangle((525+j*32,640-i*24),28,20,facecolor=color,alpha=0.55,edgecolor=BG))
    label(ax,600,595,"scatter plan: (e,a,b) → CSR index",13,MUTED,ha="center")
    rounded(ax, 835, 570, 300, 170, fc="#0b1728", ec=GREEN)
    label(ax, 985, 710, "全局稀疏矩阵CSR", 20, TEXT, "bold", ha="center")
    # fake sparse matrix
    for i in range(6):
        for j in range(6):
            if abs(i-j)<=1 or (i+j)%5==0:
                ax.add_patch(Rectangle((910+j*28,635-i*18),20,12,facecolor=GREEN,alpha=0.65,edgecolor='none'))
    label(ax,985,595,"values[p] += ke[a,b]",13,MUTED,ha="center")
    arrow(ax, 365,650,460,650,CYAN)
    arrow(ax, 740,650,830,650,VIOLET)
    # conflict problem
    rounded(ax, 1215, 570, 300, 170, fc="#180f1a", ec=ROSE)
    label(ax, 1365, 708, "并发写冲突", 20, TEXT, "bold", ha="center")
    label(ax, 1365, 665, "多个线程同时更新\n同一CSR条目", 16, ROSE, "bold", ha="center")
    label(ax, 1365, 610, "算法差异 = 冲突处理策略", 13, MUTED, ha="center")
    arrow(ax, 1140,650,1210,650,ROSE,ls="--")
    # strategies
    strategies=[
        ("atomic", "直接原子累加", "内存少 / 可能争用", AMBER),
        ("private_csr", "线程私有values", "无冲突 / 归并+内存", GREEN),
        ("coo_sort_reduce", "贡献列表排序规约", "研究对照 / 排序成本", ORANGE),
        ("coloring", "同色单元并行", "无原子 / 颜色负载均衡", VIOLET),
        ("row_owner", "按CSR行分配owner", "独占写 / 可能重复计算", ROSE),
    ]
    x0=100; y0=285
    for i,(name,main,sub,c) in enumerate(strategies):
        x=x0+i*295
        rounded(ax,x,y0,245,135,fc="#0b1728",ec=c,lw=2,r=18)
        label(ax,x+18,y0+100,name,18,c,"bold")
        label(ax,x+18,y0+65,main,16,TEXT,"bold")
        label(ax,x+18,y0+35,sub,12,MUTED)
    label(ax, 105, 470, "当前实现的五种CPU并行冲突处理路线", 18, MUTED, "bold")
    # conclusion
    rounded(ax, 250, 95, 1100, 95, fc="#0b1728", ec="#334155", lw=1.5, r=20)
    label(ax, 800, 150, "统一前提保证公平比较：同一网格、同一CSR结构、同一scatter plan、同一局部刚度kernel", 19, TEXT, "bold", ha="center")
    label(ax, 800, 115, "因此实验观察到的性能差异主要来自并发冲突处理、预处理、归并和额外内存代价", 14, MUTED, ha="center")
    return save(fig, "03_cpu_algorithm_principle")


def fig_algorithm_matrix():
    fig, ax = setup_fig()
    label(ax, 80, 840, "CPU并行组装算法对比：实现思路与工程取舍", 32, TEXT, "bold")
    label(ax, 82, 805, "面向月底汇报的概览表：强调每种算法如何避免/处理共享CSR写冲突", 16, MUTED)
    headers=["算法", "核心思想", "同步/冲突处理", "额外内存", "当前定位"]
    colx=[80,300,620,925,1165]
    widths=[190,290,275,210,340]
    y=720; rowh=85
    for x,w,h in zip(colx,widths,headers):
        rounded(ax,x,y,w,55,fc="#162033",ec="#334155",lw=1.2,r=10)
        label(ax,x+12,y+28,h,15,TEXT,"bold")
    rows=[
        ("serial", "逐单元计算 ke 并直接累加", "无并行写", "≈0", "正确性与加速比基线", CYAN),
        ("atomic", "OpenMP并行遍历单元", "#pragma omp atomic", "低", "简单可靠的共享内存基线", AMBER),
        ("private_csr", "每线程一份CSR values", "最终逐nnz reduction", "高：threads×nnz", "真实网格上有竞争力", GREEN),
        ("coo_sort_reduce", "生成(csr_idx,value)贡献", "排序后按index规约", "很高：贡献列表", "研究对照组", ORANGE),
        ("coloring", "共享节点图着色分桶", "同色并行/颜色间串行", "中：冲突图/颜色桶", "重要CPU图着色基线", VIOLET),
        ("row_owner", "CSR行划分给线程owner", "每线程只写自有行", "中：owner任务表", "当前最强候选之一", ROSE),
    ]
    for r,row in enumerate(rows):
        yy=y-(r+1)*rowh
        bg = "#0b1728" if r%2==0 else "#101827"
        for x,w in zip(colx,widths):
            rounded(ax,x,yy,w,rowh-8,fc=bg,ec="#1f2a3d",lw=0.8,r=9)
        alg,idea,sync,mem,pos,c=row
        ax.add_patch(Circle((colx[0]+18, yy+rowh/2-4), 7, facecolor=c, edgecolor='none'))
        label(ax,colx[0]+34,yy+rowh/2-4,alg,15,c,"bold")
        label(ax,colx[1]+12,yy+rowh/2-4,idea,13,TEXT)
        label(ax,colx[2]+12,yy+rowh/2-4,sync,13,TEXT)
        label(ax,colx[3]+12,yy+rowh/2-4,mem,13,TEXT)
        label(ax,colx[4]+12,yy+rowh/2-4,pos,13,TEXT)
    # bottom note
    rounded(ax, 140, 80, 1320, 95, fc="#0b1728", ec=GREEN, lw=1.4, r=20)
    label(ax, 800, 135, "当前结论：row_owner 与 private_csr 是真实工程网格上的主线候选；atomic保留为低内存基线；coo_sort_reduce用于研究对照", 17, TEXT, "bold", ha="center")
    label(ax, 800, 105, "性能比较不只看组装时间，也同时记录 preprocess、阶段拆分、额外内存、误差与峰值RSS", 13, MUTED, ha="center")
    return save(fig, "04_cpu_algorithm_comparison_matrix")


def fig_build_workflow():
    fig, ax = setup_fig()
    label(ax, 80, 840, "可复现实验与结果产出流程", 32, TEXT, "bold")
    label(ax, 82, 805, "从输入网格到CSV/JSON/Markdown/图表，项目已形成闭环Benchmark流水线", 16, MUTED)
    stages=[
        ("Input", "规则网格\nTet4 / Hex8\nAbaqus .inp", CYAN),
        ("Build", "CMake + OpenMP\nRelease构建\nctest验证", BLUE),
        ("Benchmark", "benchmark_assembly\n6算法×线程数\n误差检查", VIOLET),
        ("Record", "CSV / JSON\n阶段耗时\n内存与误差", AMBER),
        ("Visualize", "plot_cpu_results.py\nDashboard\nSpeedup/Memory", GREEN),
        ("Report", "汇报图表\n结论摘要\n可复现归档", ROSE),
    ]
    for i,(title,body,c) in enumerate(stages):
        x=95+i*245
        rounded(ax,x,520,205,150,fc="#0b1728",ec=c,lw=2,r=20)
        label(ax,x+18,632,title,22,c,"bold")
        label(ax,x+102,575,body,15,TEXT,"bold",ha="center")
        if i<len(stages)-1: arrow(ax,x+212,595,x+238,595,c,lw=2.4)
    # metrics fields cloud
    rounded(ax, 135, 250, 610, 185, fc="#0b1728", ec=AMBER, lw=1.6, r=20)
    label(ax, 170, 400, "Benchmark记录字段", 19, AMBER, "bold")
    fields=["preprocess_ms", "assembly_mean/std_ms", "total_mean_ms", "speedup / efficiency", "rel_l2 / max_abs", "extra_memory_bytes", "peak_rss_mb", "算法阶段拆分"]
    for i,f in enumerate(fields):
        x=170+(i%2)*280; y=360-(i//2)*32
        label(ax,x,y,"• "+f,13,TEXT)
    rounded(ax, 855, 250, 610, 185, fc="#0b1728", ec=GREEN, lw=1.6, r=20)
    label(ax, 890, 400, "汇报中可强调的工程价值", 19, GREEN, "bold")
    vals=["统一入口避免算法各测各的", "结果字段完整，可解释性能来源", "真实工程网格与规则网格均支持", "图表脚本自动化，便于月度迭代"]
    for i,v in enumerate(vals): label(ax,890,360-i*38,"• "+v,14,TEXT)
    return save(fig, "05_reproducible_benchmark_workflow")

if __name__ == "__main__":
    outputs=[]
    for fn in [fig_architecture, fig_workload, fig_principle, fig_algorithm_matrix, fig_build_workflow]:
        outputs.extend(fn())
    print("Generated assets:")
    for p in outputs:
        print(p)
