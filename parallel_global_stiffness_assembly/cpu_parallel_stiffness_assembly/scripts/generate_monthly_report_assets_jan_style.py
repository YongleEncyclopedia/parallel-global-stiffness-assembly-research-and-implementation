#!/usr/bin/env python3
"""Generate January-report-style slide assets for CPU FEM assembly monthly report.
Style reference: white academic report pages, PKU deep-red header, thin lines,
flat Office-like charts, generous margins, low-density text.
"""
from pathlib import Path
import textwrap
import math
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Circle, Polygon
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation_assets" / "2026-04-monthly-report-jan-style"
OUT.mkdir(parents=True, exist_ok=True)

font_candidates = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
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

W, H = 1600, 900
RED = "#8B0000"       # deep academic red
RED2 = "#B01822"
BLACK = "#222222"
GRAY = "#666666"
LGRAY = "#D9D9D9"
VLGRAY = "#F4F4F4"
BLUE = "#4472C4"
ORANGE = "#ED7D31"
GREEN = "#70AD47"
PURPLE = "#7030A0"
CYAN = "#5B9BD5"
YELLOW = "#FFC000"
BROWN = "#A0522D"


def wrap_cn(s, width):
    # Chinese text has no spaces, textwrap still cuts by char count.
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=True, replace_whitespace=False))


def setup(title, section="2. CPU并行整体刚度矩阵组装", page=""):
    fig = plt.figure(figsize=(16, 9), facecolor="white")
    ax = plt.axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    # Header bar, matching January report style
    ax.add_patch(Rectangle((0, 830), W, 70, facecolor=RED, edgecolor="none"))
    ax.add_patch(Rectangle((42, 852), 18, 18, facecolor="white", edgecolor="white"))
    ax.text(75, 865, title, fontsize=24, color="white", fontweight="bold", va="center", ha="left")
    ax.text(1515, 866, "北京大学重庆大数据研究院", fontsize=13, color="white", va="center", ha="right")
    # Footer
    ax.plot([55, 1545], [45, 45], color="#E0E0E0", lw=1)
    ax.text(60, 24, "2026/04/30", fontsize=10, color="#9A9A9A", va="center")
    ax.text(800, 24, "Monthly Report | Parallel Global Stiffness Assembly", fontsize=10, color="#9A9A9A", ha="center", va="center")
    ax.text(1540, 24, page, fontsize=10, color="#9A9A9A", ha="right", va="center")
    return fig, ax


def box(ax, x, y, w, h, fc="white", ec=LGRAY, lw=1.2, radius=0):
    if radius:
        p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={radius}", facecolor=fc, edgecolor=ec, linewidth=lw)
    else:
        p = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(p); return p


def arrow(ax, x1, y1, x2, y2, color=GRAY, lw=1.8, rad=0):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=15,lw=lw,color=color,connectionstyle=f"arc3,rad={rad}"))


def text(ax, x, y, s, size=14, color=BLACK, weight="normal", ha="left", va="center", **kw):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, **kw)


def save(fig, name):
    png = OUT / f"{name}.png"
    svg = OUT / f"{name}.svg"
    # fixed canvas; no tight bbox to avoid unpredictable cropping
    fig.savefig(png, facecolor="white", dpi=220)
    fig.savefig(svg, facecolor="white")
    plt.close(fig)
    return png, svg


def slide_architecture():
    fig, ax = setup("2.1 代码整体结构：统一平台与算法后端", page="1")
    text(ax, 70, 795, "主线目标：把整体刚度矩阵组装推进为可复现实验平台，而不是单一算法原型。", 18, BLACK, "bold")
    text(ax, 70, 762, "统一输入、统一CSR稀疏结构、统一scatter plan、统一Benchmark口径。", 14, GRAY)

    y0 = 575
    cols = [
        (80, "输入", ["规则网格 Tet4 / Hex8", "Abaqus .inp", "3 DOF / node"], BLUE),
        (370, "核心数据结构", ["Mesh", "DofMap", "CSR Matrix", "SoA"], GREEN),
        (660, "组装框架", ["AssemblyPlan", "Element Kernels", "AssemblerFactory"], ORANGE),
        (950, "CPU算法后端", ["serial / atomic", "private_csr", "coo_sort_reduce", "coloring / row_owner"], PURPLE),
        (1240, "结果输出", ["CSV / JSON", "Markdown摘要", "Figures / Dashboard"], RED2),
    ]
    for i,(x,head,items,c) in enumerate(cols):
        box(ax, x, y0, 220, 150, fc="white", ec=c, lw=2)
        ax.add_patch(Rectangle((x, y0+112), 220, 38, facecolor=c, edgecolor=c))
        text(ax, x+110, y0+131, head, 16, "white", "bold", ha="center")
        for k,it in enumerate(items):
            text(ax, x+18, y0+84-k*29, "• " + it, 12.5, BLACK)
        if i < len(cols)-1:
            arrow(ax, x+225, y0+75, cols[i+1][0]-10, y0+75, c, 1.8)

    # Directory structure as clean tree
    box(ax, 85, 250, 620, 230, fc=VLGRAY, ec=LGRAY)
    text(ax, 110, 452, "当前CPU主线目录", 17, RED, "bold")
    tree = [
        "cpu_parallel_stiffness_assembly/",
        "  include/core, include/assembly, include/backends",
        "  src/core, src/assembly, src/backends/cpu",
        "  apps/benchmark/main.cpp",
        "  scripts/run_cpu_experiments.py, plot_cpu_results.py",
        "  tests/unit, tests/correctness",
        "  docs/cpu, results/YYYY-MM-DD"
    ]
    for k,line in enumerate(tree):
        text(ax, 120, 415-k*25, line, 12.5, BLACK if k==0 else GRAY)

    # Stats blocks
    stats = [("68", "源码/配置文件", BLUE), ("6,863", "统计行数", GREEN), ("6", "CPU算法", ORANGE), ("统一", "实验口径", RED2)]
    for i,(num,lab,c) in enumerate(stats):
        x = 780 + i*185
        box(ax, x, 300, 150, 135, fc="white", ec=c, lw=2)
        text(ax, x+75, 380, num, 31, c, "bold", ha="center")
        text(ax, x+75, 335, lab, 13, BLACK, ha="center")
    text(ax, 780, 260, "注：统计排除了build、results、data等生成目录；保留CUDA历史内容作为对照/验证资产。", 12, GRAY)
    return save(fig, "01_jan_style_code_architecture")


def slide_workload():
    fig = plt.figure(figsize=(16, 9), facecolor="white")
    ax_bg = plt.axes([0,0,1,1]); ax_bg.set_xlim(0,W); ax_bg.set_ylim(0,H); ax_bg.axis('off')
    # header/footer manually
    ax_bg.add_patch(Rectangle((0,830),W,70,facecolor=RED,edgecolor='none'))
    ax_bg.add_patch(Rectangle((42,852),18,18,facecolor='white',edgecolor='white'))
    ax_bg.text(75,865,"2.2 代码工作量：模块分布与实现规模",fontsize=24,color='white',fontweight='bold',va='center')
    ax_bg.text(1515,866,"北京大学重庆大数据研究院",fontsize=13,color='white',va='center',ha='right')
    ax_bg.plot([55,1545],[45,45],color='#E0E0E0',lw=1)
    ax_bg.text(60,24,"2026/04/30",fontsize=10,color='#9A9A9A',va='center')
    ax_bg.text(800,24,"Monthly Report | Parallel Global Stiffness Assembly",fontsize=10,color='#9A9A9A',ha='center',va='center')
    ax_bg.text(1540,24,"2",fontsize=10,color='#9A9A9A',ha='right',va='center')
    ax_bg.text(70,795,"当前代码不仅包含算法文件，也包含网格/CSR基础设施、Benchmark入口、绘图脚本和测试验证。",fontsize=16,color=BLACK,fontweight='bold')

    groups = [("CUDA历史/验证",1908,PURPLE),("实验脚本",974,ORANGE),("其他辅助",939,"#999999"),("核心数据结构",864,GREEN),("Benchmark CLI",681,BLUE),("CPU算法",527,RED2),("组装框架",422,CYAN),("构建系统",298,YELLOW),("测试与正确性",250,BROWN)]
    ax1 = fig.add_axes([0.07,0.16,0.48,0.62], facecolor='white')
    names=[g[0] for g in groups]; vals=[g[1] for g in groups]; cols=[g[2] for g in groups]
    ax1.barh(range(len(vals)), vals, color=cols, alpha=0.88)
    ax1.set_yticks(range(len(vals)), names, fontsize=11, color=BLACK)
    ax1.invert_yaxis(); ax1.set_xlabel("Lines", fontsize=11, color=GRAY)
    ax1.grid(axis='x', color='#E6E6E6', lw=0.8); ax1.set_axisbelow(True)
    for s in ax1.spines.values(): s.set_color('#BBBBBB'); s.set_linewidth(0.8)
    ax1.tick_params(colors=GRAY, labelsize=10)
    ax1.set_title("按模块统计的代码行数", fontsize=16, color=BLACK, fontweight='bold', pad=12)
    for i,v in enumerate(vals): ax1.text(v+35,i,str(v),va='center',fontsize=10,color=BLACK)

    ax2 = fig.add_axes([0.63,0.49,0.28,0.28], facecolor='white')
    alg=[('serial',24,BLUE),('atomic',49,ORANGE),('private',86,GREEN),('coo',110,PURPLE),('coloring',108,CYAN),('owner',97,RED2)]
    ax2.bar([a[0] for a in alg],[a[1] for a in alg],color=[a[2] for a in alg],alpha=0.9)
    ax2.set_title("CPU算法文件行数", fontsize=15, fontweight='bold', color=BLACK)
    ax2.grid(axis='y', color='#E6E6E6'); ax2.tick_params(axis='x', labelrotation=25, labelsize=9, colors=BLACK); ax2.tick_params(axis='y', labelsize=9, colors=GRAY)
    for s in ax2.spines.values(): s.set_color('#BBBBBB')
    for i,a in enumerate(alg): ax2.text(i,a[1]+4,str(a[1]),ha='center',fontsize=9)

    ax3 = fig.add_axes([0.62,0.16,0.30,0.25], facecolor='white')
    labels=["C++", "Header", "Python", "CUDA", "Build/Script"]
    vals=[2178,930,974,1908,873]
    cols=[BLUE,GREEN,ORANGE,PURPLE,RED2]
    ax3.pie(vals, labels=None, colors=cols, startangle=90, wedgeprops={'edgecolor':'white','linewidth':1}, autopct=lambda p:f'{p:.0f}%', textprops={'fontsize':9,'color':BLACK})
    ax3.set_title("文件类型占比", fontsize=15, color=BLACK, fontweight='bold')
    ax3.legend(labels, loc='center left', bbox_to_anchor=(1.0,0.5), fontsize=9, frameon=False)
    return save(fig, "02_jan_style_workload_metrics")


def slide_principle():
    fig, ax = setup("2.3 CPU算法原理：从单元贡献到全局CSR", page="3")
    text(ax, 70, 795, "整体刚度矩阵组装的核心问题：多个单元会贡献到同一个全局条目 K[i,j]。", 17, BLACK, "bold")
    text(ax, 70, 765, "并行算法的差异主要体现在：如何处理共享CSR values[p] 的并发写冲突。", 14, GRAY)

    # main pipeline
    y=595
    nodes=[("有限元网格", "节点/单元", BLUE), ("局部刚度", "计算 ke", GREEN), ("Scatter Plan", "映射到CSR index", ORANGE), ("全局CSR", "values[p]累加", PURPLE), ("冲突处理", "同步或规约", RED2)]
    for i,(h,b,c) in enumerate(nodes):
        x=95+i*295
        box(ax,x,y,210,115,fc='white',ec=c,lw=2)
        text(ax,x+105,y+76,h,17,c,'bold',ha='center')
        text(ax,x+105,y+38,b,13,BLACK,ha='center')
        if i < len(nodes)-1: arrow(ax,x+218,y+57,x+285,y+57,c,1.8)
    # illustrative grid and matrix
    box(ax, 120, 325, 330, 170, fc=VLGRAY, ec=LGRAY)
    text(ax, 145, 468, "单元贡献", 15, RED, "bold")
    pts=[(205,390),(285,435),(360,385),(280,360)]
    ax.add_patch(Polygon(pts, closed=True, facecolor='#DDEBF7', edgecolor=BLUE, lw=1.5))
    for px,py in pts: ax.add_patch(Circle((px,py),13,facecolor=BLUE,edgecolor='white',lw=1))
    text(ax, 285, 345, "每个单元生成局部矩阵 ke", 12, GRAY, ha='center')

    box(ax, 520, 325, 330, 170, fc=VLGRAY, ec=LGRAY)
    text(ax, 545, 468, "局部矩阵 ke", 15, RED, "bold")
    for i in range(4):
        for j in range(4):
            col=[BLUE,GREEN,ORANGE,PURPLE][(i+j)%4]
            ax.add_patch(Rectangle((620+j*42,430-i*30),35,24,facecolor=col,edgecolor='white',alpha=0.85))
    text(ax,685,345,"ke[a,b]",12,GRAY,ha='center')

    box(ax, 920, 325, 330, 170, fc=VLGRAY, ec=LGRAY)
    text(ax, 945, 468, "全局CSR K", 15, RED, "bold")
    for i in range(7):
        for j in range(7):
            if abs(i-j)<=1 or (i+j)%5==0:
                ax.add_patch(Rectangle((1015+j*28,440-i*19),22,13,facecolor=GREEN,edgecolor='white'))
    text(ax,1085,345,"values[p] += ke[a,b]",12,GRAY,ha='center')
    arrow(ax,455,410,515,410,GRAY,1.4); arrow(ax,855,410,915,410,GRAY,1.4)

    box(ax, 1285, 325, 215, 170, fc="#FFF2F2", ec=RED2, lw=1.8)
    text(ax, 1392, 452, "并发写冲突", 16, RED2, "bold", ha='center')
    text(ax, 1392, 400, "多个线程\n更新同一位置", 13, BLACK, ha='center')
    text(ax, 1392, 348, "需同步 / 规约 / 分配owner", 11.5, GRAY, ha='center')
    arrow(ax,1255,410,1280,410,RED2,1.4)

    strategies=[("atomic", "原子累加", ORANGE), ("private_csr", "私有CSR后归并", GREEN), ("coo_sort_reduce", "排序规约", PURPLE), ("coloring", "同色无冲突", CYAN), ("row_owner", "行拥有者", RED2)]
    for i,(name,desc,c) in enumerate(strategies):
        x=145+i*285
        box(ax,x,150,210,78,fc='white',ec=c,lw=1.8)
        text(ax,x+105,195,name,14,c,'bold',ha='center')
        text(ax,x+105,166,desc,11.5,BLACK,ha='center')
    return save(fig, "03_jan_style_cpu_principle")


def slide_algorithm_cards():
    fig, ax = setup("2.4 CPU并行算法：六种实现路线", page="4")
    text(ax,70,795,"为避免表格过密，本页按算法卡片展示核心思想和工程取舍。",16,BLACK,'bold')
    cards=[
        ("serial", "串行基线", "逐单元计算 ke，直接累加到CSR。", "作用：正确性与加速比参考。", BLUE),
        ("atomic", "原子直接累加", "OpenMP并行遍历单元；写回阶段使用atomic。", "优点：内存低；缺点：热点争用。", ORANGE),
        ("private_csr", "线程私有CSR", "每线程维护一份values，最后按nnz归并。", "优点：无写冲突；代价：内存高。", GREEN),
        ("coo_sort_reduce", "COO排序规约", "先生成(csr_index,value)贡献，再排序reduce。", "定位：研究对照组，排序成本较高。", PURPLE),
        ("coloring", "图着色并行", "共享节点即冲突；同色单元可并行组装。", "代价：着色预处理与负载均衡。", CYAN),
        ("row_owner", "行拥有者", "按CSR行分配owner；线程只写自有行。", "当前：真实网格上最强候选之一。", RED2),
    ]
    for idx,(name,h,body,foot,c) in enumerate(cards):
        col=idx%3; row=idx//3
        x=105+col*485; y=470-row*230
        box(ax,x,y,405,165,fc='white',ec=c,lw=2)
        ax.add_patch(Rectangle((x,y+126),405,39,facecolor=c,edgecolor=c))
        text(ax,x+20,y+145,name,16,'white','bold')
        text(ax,x+25,y+100,h,17,BLACK,'bold')
        text(ax,x+25,y+67,wrap_cn(body,23),12.2,BLACK,va='center')
        text(ax,x+25,y+24,wrap_cn(foot,24),11.5,GRAY,va='center')
    box(ax, 150, 125, 1300, 65, fc="#FFF7F7", ec="#E5B8B8", lw=1)
    text(ax, 800, 158, "当前汇报重点：row_owner 与 private_csr 作为主线候选；atomic作为低内存基线；coo_sort_reduce用于解释规约路线。", 15, RED, 'bold', ha='center')
    return save(fig, "04_jan_style_algorithm_cards")


def slide_workflow():
    fig, ax = setup("2.5 可复现实验流程：从输入到图表", page="5")
    text(ax,70,795,"项目已形成完整实验闭环：构建、运行、记录、绘图、归档均可脚本化。",16,BLACK,'bold')
    steps=[("Input", "规则网格\n工程.inp", BLUE), ("Build", "CMake\nOpenMP", GREEN), ("Benchmark", "6算法\n多线程", ORANGE), ("Record", "CSV/JSON\n误差/内存", PURPLE), ("Visualize", "曲线/柱状\nDashboard", CYAN), ("Report", "PPT素材\n结论归档", RED2)]
    for i,(h,b,c) in enumerate(steps):
        x=95+i*245
        box(ax,x,570,190,120,fc='white',ec=c,lw=2)
        ax.add_patch(Rectangle((x,570),190,30,facecolor=c,edgecolor=c))
        text(ax,x+95,585,h,14,'white','bold',ha='center')
        text(ax,x+95,638,b,14,BLACK,'bold',ha='center')
        if i<len(steps)-1: arrow(ax,x+198,630,x+238,630,c,1.8)

    # lower two panels
    box(ax, 115, 265, 620, 215, fc=VLGRAY, ec=LGRAY)
    text(ax,145,448,"Benchmark记录字段",17,RED,'bold')
    fields=["preprocess_ms", "assembly_mean / std_ms", "total_mean_ms", "speedup / efficiency", "rel_l2 / max_abs", "extra_memory_bytes", "peak_rss_mb", "阶段拆分字段"]
    for i,f in enumerate(fields):
        text(ax,155+(i%2)*285,405-(i//2)*38,"• "+f,12.5,BLACK)

    box(ax, 865, 265, 620, 215, fc=VLGRAY, ec=LGRAY)
    text(ax,895,448,"适合汇报强调的工程价值",17,RED,'bold')
    vals=["统一入口：避免算法各测各的", "统一数据结构：保证公平比较", "结果完整：可解释时间与内存代价", "自动绘图：支持月度迭代复现"]
    for i,v in enumerate(vals):
        text(ax,905,405-i*38,"• "+v,13.5,BLACK)

    # minimal output file strip
    box(ax, 200, 140, 1200, 60, fc='white', ec='#BFBFBF')
    text(ax,230,170,"results/YYYY-MM-DD/",14,BLACK,'bold')
    text(ax,465,170,"csv/",13,BLUE,'bold')
    text(ax,590,170,"json/",13,GREEN,'bold')
    text(ax,725,170,"summaries/",13,ORANGE,'bold')
    text(ax,910,170,"figures/",13,PURPLE,'bold')
    text(ax,1085,170,"presentation_assets/",13,RED2,'bold')
    return save(fig, "05_jan_style_reproducible_workflow")

if __name__ == "__main__":
    outputs=[]
    for fn in [slide_architecture, slide_workload, slide_principle, slide_algorithm_cards, slide_workflow]:
        outputs += list(fn())
    print("Generated January-style assets:")
    for p in outputs:
        print(p)
