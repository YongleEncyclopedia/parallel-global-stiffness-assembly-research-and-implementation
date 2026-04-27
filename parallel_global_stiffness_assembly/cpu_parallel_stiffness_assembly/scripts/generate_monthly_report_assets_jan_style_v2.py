#!/usr/bin/env python3
"""V2 January-style assets: white background, PKU red header, larger text, no overflow."""
from pathlib import Path
import textwrap
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Circle, Polygon
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation_assets" / "2026-04-monthly-report-jan-style-v2"
OUT.mkdir(parents=True, exist_ok=True)

for fp in ["/System/Library/Fonts/PingFang.ttc","/System/Library/Fonts/STHeiti Medium.ttc","/System/Library/Fonts/Supplemental/Songti.ttc"]:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

W,H=1600,900
RED="#8B0000"; RED2="#B01822"; BLACK="#222222"; GRAY="#666666"; LG="#D9D9D9"; VLG="#F5F5F5"
BLUE="#4472C4"; ORANGE="#ED7D31"; GREEN="#70AD47"; PURPLE="#7030A0"; CYAN="#5B9BD5"; YELLOW="#FFC000"; BROWN="#A0522D"
COLS=[BLUE,ORANGE,GREEN,PURPLE,CYAN,RED2]

def wrap(s,n): return "\n".join(textwrap.wrap(s,n,break_long_words=True,replace_whitespace=False))
def figax(title,page):
    fig=plt.figure(figsize=(16,9),facecolor="white")
    ax=plt.axes([0,0,1,1]); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis('off')
    ax.add_patch(Rectangle((0,830),W,70,facecolor=RED,edgecolor='none'))
    ax.add_patch(Rectangle((42,852),18,18,facecolor='white',edgecolor='white'))
    ax.text(75,865,title,fontsize=25,color='white',fontweight='bold',va='center')
    ax.text(1515,866,"北京大学重庆大数据研究院",fontsize=14,color='white',ha='right',va='center')
    ax.plot([55,1545],[45,45],color='#E0E0E0',lw=1)
    ax.text(60,24,"2026/04/30",fontsize=11,color='#999999',va='center')
    ax.text(800,24,"Monthly Report | Parallel Global Stiffness Assembly",fontsize=11,color='#999999',ha='center',va='center')
    ax.text(1540,24,str(page),fontsize=11,color='#999999',ha='right',va='center')
    return fig,ax
def tx(ax,x,y,s,fs=16,c=BLACK,w='normal',ha='left',va='center',**kw): ax.text(x,y,s,fontsize=fs,color=c,fontweight=w,ha=ha,va=va,**kw)
def box(ax,x,y,w,h,fc='white',ec=LG,lw=1.4,r=0):
    p=FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.01,rounding_size={r}",facecolor=fc,edgecolor=ec,linewidth=lw) if r else Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,linewidth=lw)
    ax.add_patch(p); return p
def arr(ax,x1,y1,x2,y2,c=GRAY,lw=2): ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=16,lw=lw,color=c))
def save(fig,name):
    p=OUT/f"{name}.png"; s=OUT/f"{name}.svg"
    fig.savefig(p,facecolor='white',dpi=220); fig.savefig(s,facecolor='white'); plt.close(fig); return [p,s]

def s1():
    fig,ax=figax("2.1 代码整体结构：统一平台与算法后端",1)
    tx(ax,70,792,"主线目标：形成可复现实验平台，而不是单一算法原型。",20,BLACK,'bold')
    tx(ax,70,758,"统一输入、统一CSR、统一scatter plan、统一Benchmark。",16,GRAY)
    items=[('输入','网格 / .inp\n3 DOF/node',BLUE),('核心结构','Mesh / DofMap\nCSR Matrix',GREEN),('组装框架','AssemblyPlan\nElement Kernels',ORANGE),('算法后端','6类CPU算法\n统一工厂入口',PURPLE),('结果输出','CSV / JSON\nFigures / Summary',RED2)]
    for i,(h,b,c) in enumerate(items):
        x=90+i*300; y=585
        box(ax,x,y,235,125,'white',c,2)
        ax.add_patch(Rectangle((x,y+86),235,39,facecolor=c,edgecolor=c))
        tx(ax,x+117,y+105,h,18,'white','bold','center')
        tx(ax,x+117,y+51,b,16,BLACK,'bold','center')
        if i<4: arr(ax,x+242,y+62,x+292,y+62,c,2)
    box(ax,110,315,520,170,VLG,LG,1.2)
    tx(ax,140,455,"CPU主线目录",18,RED,'bold')
    for k,line in enumerate(["include/   core, assembly, backends", "src/       core, assembly, backends/cpu", "apps/      benchmark_assembly", "scripts/   experiments + plotting"]):
        tx(ax,145,420-k*34,line,15,BLACK if k<2 else GRAY)
    stats=[('68','源码/配置文件',BLUE),('6,863','统计行数',GREEN),('6','CPU算法',ORANGE),('统一','实验口径',RED2)]
    for i,(n,l,c) in enumerate(stats):
        x=740+i*190; box(ax,x,340,155,120,'white',c,2)
        tx(ax,x+77,405,n,32,c,'bold','center'); tx(ax,x+77,365,l,15,BLACK,'bold','center')
    tx(ax,740,302,"统计排除 build / results / data 等生成目录。",15,GRAY)
    return save(fig,"01_jan_style_v2_code_architecture")

def s2():
    fig=plt.figure(figsize=(16,9),facecolor='white')
    bg=plt.axes([0,0,1,1]); bg.set_xlim(0,W); bg.set_ylim(0,H); bg.axis('off')
    bg.add_patch(Rectangle((0,830),W,70,facecolor=RED,edgecolor='none')); bg.add_patch(Rectangle((42,852),18,18,facecolor='white'))
    bg.text(75,865,"2.2 代码工作量：模块分布与实现规模",fontsize=25,color='white',fontweight='bold',va='center')
    bg.text(1515,866,"北京大学重庆大数据研究院",fontsize=14,color='white',ha='right',va='center')
    bg.plot([55,1545],[45,45],color='#E0E0E0',lw=1); bg.text(60,24,"2026/04/30",fontsize=11,color='#999999',va='center'); bg.text(800,24,"Monthly Report | Parallel Global Stiffness Assembly",fontsize=11,color='#999999',ha='center',va='center'); bg.text(1540,24,"2",fontsize=11,color='#999999',ha='right',va='center')
    bg.text(70,795,"代码规模体现为三部分：基础设施、算法实现、实验与可视化工具链。",fontsize=20,color=BLACK,fontweight='bold')
    groups=[('CUDA历史/验证',1908,PURPLE),('实验脚本',974,ORANGE),('其他辅助',939,'#999999'),('核心数据结构',864,GREEN),('Benchmark CLI',681,BLUE),('CPU算法',527,RED2),('组装框架',422,CYAN),('测试/构建',548,BROWN)]
    ax=fig.add_axes([0.08,0.20,0.58,0.55]); names=[g[0] for g in groups]; vals=[g[1] for g in groups]
    ax.barh(range(len(vals)),vals,color=[g[2] for g in groups],alpha=.9); ax.set_yticks(range(len(vals)),names,fontsize=14,color=BLACK); ax.invert_yaxis()
    ax.set_xlabel('Lines of code',fontsize=13,color=GRAY); ax.grid(axis='x',color='#E6E6E6'); ax.set_axisbelow(True)
    ax.set_title('按模块统计的代码行数',fontsize=18,fontweight='bold',pad=12)
    for sp in ax.spines.values(): sp.set_color('#BBBBBB')
    ax.tick_params(axis='x',labelsize=12,colors=GRAY)
    for i,v in enumerate(vals): ax.text(v+40,i,str(v),va='center',fontsize=12,color=BLACK)
    # Right callout: no tiny pie/legend
    box(bg,1110,585,275,120,'white',BLUE,2); bg.text(1247,655,"68",fontsize=36,color=BLUE,fontweight='bold',ha='center'); bg.text(1247,615,"文件",fontsize=16,color=BLACK,fontweight='bold',ha='center')
    box(bg,1110,420,275,120,'white',GREEN,2); bg.text(1247,490,"6,863",fontsize=36,color=GREEN,fontweight='bold',ha='center'); bg.text(1247,450,"行统计代码",fontsize=16,color=BLACK,fontweight='bold',ha='center')
    box(bg,1080,175,335,165,VLG,LG,1.2)
    bg.text(1110,305,"算法文件规模",fontsize=18,color=RED,fontweight='bold')
    for i,(name,val,c) in enumerate([('serial',24,BLUE),('atomic',49,ORANGE),('private',86,GREEN),('coo',110,PURPLE),('coloring',108,CYAN),('owner',97,RED2)]):
        bg.add_patch(Rectangle((1115,270-i*22),val*1.25,12,facecolor=c,edgecolor='none'))
        bg.text(1260,276-i*22,f"{name}  {val}",fontsize=14,color=BLACK,va='center')
    return save(fig,"02_jan_style_v2_workload_metrics")

def s3():
    fig,ax=figax("2.3 CPU算法原理：从单元贡献到全局CSR",3)
    tx(ax,70,792,"核心挑战：多个单元可能同时贡献到同一个全局矩阵条目。",20,BLACK,'bold')
    tx(ax,70,758,"并行算法的本质差异，是如何处理 CSR values[p] 的并发写。",16,GRAY)
    steps=[('有限元单元','element e',BLUE),('局部矩阵','ke[a,b]',GREEN),('散射映射','CSR index',ORANGE),('全局矩阵','K values[p]',PURPLE),('冲突处理','同步 / 规约 / owner',RED2)]
    for i,(h,b,c) in enumerate(steps):
        x=110+i*295; y=610; box(ax,x,y,210,100,'white',c,2)
        tx(ax,x+105,y+64,h,18,c,'bold','center'); tx(ax,x+105,y+32,b,15,BLACK,'bold','center')
        if i<4: arr(ax,x+218,y+50,x+285,y+50,c,2)
    # bigger concept illustrations
    box(ax,150,335,350,180,VLG,LG,1.2); tx(ax,175,485,"单元贡献",18,RED,'bold')
    pts=[(250,390),(320,455),(410,390),(325,360)]; ax.add_patch(Polygon(pts,closed=True,facecolor='#DDEBF7',edgecolor=BLUE,lw=2))
    for p in pts: ax.add_patch(Circle(p,16,facecolor=BLUE,edgecolor='white',lw=1.5))
    tx(ax,325,330,"每个单元生成一组局部贡献",16,GRAY,'normal','center')
    box(ax,625,335,350,180,VLG,LG,1.2); tx(ax,650,485,"局部矩阵 ke",18,RED,'bold')
    for i in range(4):
        for j in range(4): ax.add_patch(Rectangle((735+j*42,435-i*32),36,26,facecolor=COLS[(i+j)%6],edgecolor='white'))
    tx(ax,800,330,"通过scatter plan映射到CSR位置",16,GRAY,'normal','center')
    box(ax,1100,335,350,180,VLG,LG,1.2); tx(ax,1125,485,"全局CSR矩阵",18,RED,'bold')
    for i in range(7):
        for j in range(7):
            if abs(i-j)<=1 or (i+j)%5==0: ax.add_patch(Rectangle((1210+j*29,445-i*20),23,14,facecolor=GREEN,edgecolor='white'))
    tx(ax,1275,330,"不同线程可能写入同一 values[p]",16,RED2,'bold','center')
    arr(ax,505,425,620,425,GRAY,1.8); arr(ax,980,425,1095,425,GRAY,1.8)
    # strategies in one clean line, no small descriptions
    tx(ax,120,250,"五类并行处理路线：",18,BLACK,'bold')
    for i,(name,c) in enumerate([('atomic',ORANGE),('private_csr',GREEN),('coo_sort_reduce',PURPLE),('coloring',CYAN),('row_owner',RED2)]):
        x=390+i*215; box(ax,x,215,170,55,'white',c,2); tx(ax,x+85,242,name,14.5,c,'bold','center')
    return save(fig,"03_jan_style_v2_cpu_principle")

def s4():
    fig,ax=figax("2.4 CPU并行算法：六种实现路线",4)
    tx(ax,70,792,"每种算法对应一种冲突处理策略：直接同步、私有化、规约、调度或owner独占写。",19,BLACK,'bold')
    cards=[('serial','串行基线','正确性与加速比参考',BLUE),('atomic','原子累加','低内存；可能产生热点争用',ORANGE),('private_csr','线程私有CSR','无写冲突；归并和内存代价高',GREEN),('coo_sort_reduce','排序规约','研究对照；排序成本高',PURPLE),('coloring','图着色并行','同色单元无冲突；需预处理',CYAN),('row_owner','行拥有者','独占写；真实网格强候选',RED2)]
    for i,(en,cn,desc,c) in enumerate(cards):
        x=105+(i%3)*485; y=490-(i//3)*235
        box(ax,x,y,405,165,'white',c,2)
        ax.add_patch(Rectangle((x,y+122),405,43,facecolor=c,edgecolor=c))
        tx(ax,x+25,y+143,en,17,'white','bold')
        tx(ax,x+25,y+92,cn,20,BLACK,'bold')
        tx(ax,x+25,y+50,wrap(desc,18),15.5,GRAY)
    box(ax,170,125,1260,70,'#FFF7F7','#E5B8B8',1.2)
    tx(ax,800,160,"汇报重点：row_owner 与 private_csr 是主线候选；atomic 保留为低内存基线。",18,RED,'bold','center')
    return save(fig,"04_jan_style_v2_algorithm_cards")

def s5():
    fig,ax=figax("2.5 可复现实验流程：从输入到图表",5)
    tx(ax,70,792,"实验闭环已脚本化：构建、运行、记录、绘图、归档均可重复执行。",19,BLACK,'bold')
    steps=[('Input','网格 / .inp',BLUE),('Build','CMake + OpenMP',GREEN),('Benchmark','6算法 × 线程数',ORANGE),('Record','CSV / JSON',PURPLE),('Visualize','图表 / Dashboard',CYAN),('Report','PPT素材 / 结论',RED2)]
    for i,(h,b,c) in enumerate(steps):
        x=85+i*250; y=590; box(ax,x,y,200,115,'white',c,2)
        ax.add_patch(Rectangle((x,y),200,34,facecolor=c,edgecolor=c))
        tx(ax,x+100,y+17,h,15,'white','bold','center'); tx(ax,x+100,y+73,b,15.5,BLACK,'bold','center')
        if i<5: arr(ax,x+208,y+58,x+238,y+58,c,2)
    box(ax,135,325,560,185,VLG,LG,1.2); tx(ax,165,475,"Benchmark核心字段",19,RED,'bold')
    for i,f in enumerate(['assembly time','total time','speedup / efficiency','rel_l2 / max_abs','extra memory','stage breakdown']): tx(ax,180+(i%2)*255,432-(i//2)*45,'• '+f,16,BLACK)
    box(ax,895,325,560,185,VLG,LG,1.2); tx(ax,925,475,"工程价值",19,RED,'bold')
    for i,v in enumerate(['统一入口，便于公平对比','统一数据结构，避免口径差异','自动图表，支持月度迭代']): tx(ax,940,430-i*50,'• '+v,16,BLACK)
    box(ax,250,165,1100,70,'white','#BFBFBF',1.2); tx(ax,285,200,"输出归档：results/YYYY-MM-DD/  →  csv / json / summaries / figures / presentation_assets",17,BLACK,'bold')
    return save(fig,"05_jan_style_v2_reproducible_workflow")

if __name__=='__main__':
    outs=[]
    for f in [s1,s2,s3,s4,s5]: outs+=f()
    print('Generated V2 January-style assets:')
    for p in outs: print(p)
