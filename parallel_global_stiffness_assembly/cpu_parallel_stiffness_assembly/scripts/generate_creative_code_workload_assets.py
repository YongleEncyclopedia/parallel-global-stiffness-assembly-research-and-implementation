#!/usr/bin/env python3
"""Creative visual assets for CPU parallel stiffness assembly report.
Not tied to previous PPT style: cinematic, colorful, presentation-ready.
"""
from pathlib import Path
import math, random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch, Wedge, Polygon
from matplotlib import patheffects, font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation_assets" / "2026-04-creative-code-workload"
OUT.mkdir(parents=True, exist_ok=True)

for fp in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Supplemental/Songti.ttc"]:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

W,H=1600,900
BG="#050816"; BG2="#0B1026"; TEXT="#F8FAFC"; MUTED="#D7E2FF"
CYAN="#28D7FF"; BLUE="#5B8CFF"; GREEN="#4ADE80"; ORANGE="#FF9F43"; PURPLE="#B26BFF"; PINK="#FF4D8D"; YELLOW="#FFD166"; RED="#FF5C5C"
COLORS=[CYAN,BLUE,GREEN,ORANGE,PURPLE,PINK,YELLOW,RED]

groups={
 'CUDA Legacy / Validation': {'files':8,'lines':1908,'color':PURPLE,'short':'CUDA验证'},
 'Experiment Scripts': {'files':8,'lines':1759,'color':ORANGE,'short':'实验脚本'},
 'Other Support': {'files':18,'lines':939,'color':'#64748B','short':'辅助文件'},
 'Core Data Structures': {'files':10,'lines':864,'color':CYAN,'short':'核心结构'},
 'Benchmark CLI': {'files':1,'lines':681,'color':YELLOW,'short':'Benchmark'},
 'CPU Algorithms': {'files':7,'lines':527,'color':PINK,'short':'CPU算法'},
 'Assembly Framework': {'files':9,'lines':422,'color':BLUE,'short':'组装框架'},
 'Build System': {'files':5,'lines':298,'color':GREEN,'short':'构建系统'},
 'Tests & Correctness': {'files':5,'lines':250,'color':RED,'short':'测试验证'},
}
algs=[('serial',24,CYAN),('atomic',49,ORANGE),('private_csr',86,GREEN),('coo_sort_reduce',110,PURPLE),('graph_coloring',108,BLUE),('row_owner',97,PINK)]
total_files=71; total_lines=7648

def glow_text(ax,x,y,s,size=24,color=TEXT,weight='bold',ha='left',va='center',alpha=1):
    t=ax.text(x,y,s,fontsize=size,color=color,fontweight=weight,ha=ha,va=va,alpha=alpha)
    t.set_path_effects([patheffects.withStroke(linewidth=4, foreground=(0,0,0,0.25))])
    return t

def setup():
    fig=plt.figure(figsize=(16,9),facecolor=BG)
    ax=plt.axes([0,0,1,1]); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis('off')
    # gradient background
    nx,ny=600,340
    x=np.linspace(0,1,nx); y=np.linspace(0,1,ny)
    X,Y=np.meshgrid(x,y)
    grad=np.zeros((ny,nx,3))
    base=np.array([5,8,22])/255; top=np.array([13,20,45])/255
    grad[:]=base*(1-Y[...,None])+top*Y[...,None]
    # colored radial glows
    for cx,cy,col,amp in [(0.15,0.8,np.array([40,215,255])/255,.22),(0.82,0.75,np.array([178,107,255])/255,.18),(0.7,0.18,np.array([255,77,141])/255,.16)]:
        d=((X-cx)**2+(Y-cy)**2)**0.5
        grad += col*np.clip(1-d/0.55,0,1)[...,None]*amp
    grad=np.clip(grad,0,1)
    ax.imshow(grad,extent=[0,W,0,H],origin='lower',aspect='auto')
    # stars/dots deterministic
    random.seed(7)
    for _ in range(120):
        ax.add_patch(Circle((random.uniform(20,W-20),random.uniform(70,H-30)),random.uniform(0.8,2.2),facecolor='white',edgecolor='none',alpha=random.uniform(.08,.28)))
    return fig,ax

def card(ax,x,y,w,h,fc="#0F172A",ec="#24304D",lw=1.4,r=22,alpha=.92):
    p=FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.02,rounding_size={r}",facecolor=fc,edgecolor=ec,linewidth=lw,alpha=alpha)
    ax.add_patch(p); return p

def arr(ax,x1,y1,x2,y2,c=CYAN,lw=2.2,rad=0):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=18,lw=lw,color=c,alpha=.9,connectionstyle=f"arc3,rad={rad}"))

def save(fig,name):
    png=OUT/f"{name}.png"; svg=OUT/f"{name}.svg"
    fig.savefig(png,facecolor=BG,dpi=220)
    fig.savefig(svg,facecolor=BG)
    plt.close(fig); return [png,svg]

def slide_constellation():
    fig,ax=setup()
    glow_text(ax,80,835,"Codebase Constellation",34,TEXT)
    glow_text(ax,82,795,"CPU并行整体刚度矩阵组装项目 · 代码结构星图",19,MUTED,'normal')
    # central core
    cx,cy=800,455
    for r,a in [(190,.08),(140,.10),(92,.14)]: ax.add_patch(Circle((cx,cy),r,facecolor=CYAN,edgecolor='none',alpha=a))
    ax.add_patch(Circle((cx,cy),78,facecolor="#0F172A",edgecolor=CYAN,lw=2.6,alpha=.98))
    glow_text(ax,cx,cy+18,"CPU Assembly",22,CYAN,ha='center')
    glow_text(ax,cx,cy-18,"Core",16,TEXT,ha='center')
    # satellites
    nodes=[('Input\nMesh/.inp',520,650,BLUE),('Core Data\nMesh/CSR/DOF',810,700,CYAN),('Assembly\nPlan+Kernels',1080,630,ORANGE),('CPU Backends\n6 Algorithms',1160,390,PINK),('Benchmark\nCLI',850,230,YELLOW),('Scripts\nExperiments',520,260,GREEN),('Tests\nCorrectness',350,450,RED)]
    for label,x,y,c in nodes:
        arr(ax,cx,cy,x,y,c,1.7,rad=.08 if x<cx else -.08)
        ax.add_patch(Circle((x,y),48,facecolor=c,edgecolor='white',lw=1.2,alpha=.22))
        ax.add_patch(Circle((x,y),32,facecolor="#10182E",edgecolor=c,lw=2.2,alpha=.98))
        glow_text(ax,x,y,label,14.5,TEXT,ha='center')
    # metrics orbit
    stats=[('71','files'),('7,648','lines'),('6','CPU algos'),('9','modules')]
    for i,(n,l) in enumerate(stats):
        ang=math.radians(25+i*38); x=cx+330*math.cos(ang); y=cy+330*math.sin(ang)
        card(ax,x-70,y-45,140,90,fc="#111827",ec=COLORS[i],r=18,alpha=.88)
        glow_text(ax,x,y+12,n,25,COLORS[i],ha='center')
        glow_text(ax,x,y-22,l,12,MUTED,'normal',ha='center')
    glow_text(ax,82,90,"One project, one pipeline: data structures → assembly framework → algorithm backends → benchmark evidence",17,MUTED,'normal')
    return save(fig,"01_creative_codebase_constellation")

def slide_city():
    fig,ax=setup()
    glow_text(ax,80,835,"Code City: Workload Skyline",34,TEXT)
    glow_text(ax,82,795,"每个模块是一栋楼，高度代表代码行数，窗格代表文件数量",18,MUTED,'normal')
    items=sorted(groups.items(), key=lambda kv: kv[1]['lines'], reverse=True)
    max_lines=max(v['lines'] for _,v in items)
    base_y=150; start_x=90; gap=22; bw=145
    for i,(name,v) in enumerate(items):
        h=95+v['lines']/max_lines*430; x=start_x+i*(bw+gap); c=v['color']
        # shadow
        ax.add_patch(Polygon([(x+18,base_y-12),(x+bw+18,base_y-12),(x+bw+45,base_y+8),(x+45,base_y+8)],facecolor='black',alpha=.22,edgecolor='none'))
        card(ax,x,base_y,bw,h,fc="#10182E",ec=c,lw=2,r=14,alpha=.96)
        ax.add_patch(Rectangle((x,base_y+h-34),bw,34,facecolor=c,edgecolor='none',alpha=.86))
        glow_text(ax,x+bw/2,base_y+h-17,v['short'],13,'white',ha='center')
        # windows
        rows=max(2,min(9,v['files']//2+1)); cols=4
        for rr in range(rows):
            for cc in range(cols):
                wx=x+20+cc*28; wy=base_y+24+rr*34
                if wy<base_y+h-48:
                    ax.add_patch(Rectangle((wx,wy),13,16,facecolor=c,edgecolor='none',alpha=.28+0.06*((rr+cc)%2)))
        glow_text(ax,x+bw/2,base_y+h+36,f"{v['lines']}",19,c,ha='center')
        glow_text(ax,x+bw/2,base_y-32,f"{v['files']} files",12,MUTED,'normal',ha='center')
    # skyline base and totals
    ax.plot([60,1540],[base_y,base_y],color="#334155",lw=2)
    card(ax,1030,690,450,90,fc="#0F172A",ec=CYAN,r=24,alpha=.88)
    glow_text(ax,1060,738,"Total workload",16,MUTED,'normal')
    glow_text(ax,1300,738,f"{total_files} files / {total_lines:,} lines",24,CYAN,ha='center')
    return save(fig,"02_creative_workload_skyline")

def slide_neural_architecture():
    fig,ax=setup()
    glow_text(ax,80,835,"Assembly Pipeline Map",34,TEXT)
    glow_text(ax,82,795,"从网格输入到实验图表：代码结构与数据流的可视化地图",18,MUTED,'normal')
    cols=[('Input Layer', ['Mesh generator','.inp parser','Tet4 / Hex8'], BLUE),('Core Layer',['Mesh','DofMap','CSR Matrix','SoA'], CYAN),('Planning Layer',['CSR pattern','Scatter plan','Element kernel'], ORANGE),('Algorithm Layer',['serial','atomic','private_csr','coloring','row_owner'], PINK),('Evidence Layer',['CSV/JSON','Summary.md','Figures'], GREEN)]
    xs=[120,410,700,990,1280]
    for ci,(title,items,c) in enumerate(cols):
        x=xs[ci]
        card(ax,x,165,210,545,fc="#0E162B",ec=c,lw=1.8,r=26,alpha=.9)
        glow_text(ax,x+105,680,title,16,c,ha='center')
        for j,it in enumerate(items):
            y=600-j*88
            ax.add_patch(Circle((x+105,y),30,facecolor=c,edgecolor='white',lw=1.0,alpha=.22))
            ax.add_patch(Circle((x+105,y),20,facecolor="#10182E",edgecolor=c,lw=1.8,alpha=.98))
            glow_text(ax,x+105,y-48,it,13.8,TEXT,'normal',ha='center')
            if ci<len(cols)-1 and j < len(cols[ci+1][1]):
                arr(ax,x+130,y,xs[ci+1]+80,600-j*88, c, 1.3)
    # algorithm chips
    card(ax,510,80,580,58,fc="#111827",ec="#334155",r=20,alpha=.85)
    glow_text(ax,800,110,"统一入口：AssemblerFactory 选择不同CPU算法，同一Benchmark口径比较",16,MUTED,'normal',ha='center')
    return save(fig,"03_creative_pipeline_map")

def slide_algorithm_radar():
    fig,ax=setup()
    glow_text(ax,80,835,"Algorithm Portfolio",34,TEXT)
    glow_text(ax,82,795,"六类CPU算法实现路线：基线、同步、私有化、规约、着色、Owner独占写",18,MUTED,'normal')
    cx,cy=800,430
    # rings
    for r in [95,165,235,305]:
        ax.add_patch(Circle((cx,cy),r,facecolor='none',edgecolor='#26324F',lw=1.2,alpha=.75))
    for k in range(12):
        ang=2*math.pi*k/12; ax.plot([cx,cx+320*math.cos(ang)],[cy,cy+320*math.sin(ang)],color='#1E293B',lw=.8,alpha=.65)
    maxv=max(v for _,v,_ in algs)
    for i,(name,val,c) in enumerate(algs):
        ang=2*math.pi*i/len(algs)+math.pi/6
        r=115+val/maxv*175; x=cx+r*math.cos(ang); y=cy+r*math.sin(ang)
        arr(ax,cx,cy,x,y,c,1.4)
        ax.add_patch(Circle((x,y),44,facecolor=c,edgecolor='white',lw=1.2,alpha=.26))
        ax.add_patch(Circle((x,y),28,facecolor="#10182E",edgecolor=c,lw=2.2))
        glow_text(ax,x,y+7,str(val),18,c,ha='center')
        glow_text(ax,x,y-55,name,13.5,TEXT,'normal',ha='center')
    ax.add_patch(Circle((cx,cy),70,facecolor="#10182E",edgecolor=CYAN,lw=2.5))
    glow_text(ax,cx,cy+12,"CPU",22,CYAN,ha='center')
    glow_text(ax,cx,cy-20,"Backends",13,TEXT,'normal',ha='center')
    # side legend
    labels=[('serial','正确性基线',CYAN),('atomic','原子同步',ORANGE),('private_csr','私有化规约',GREEN),('coo_sort_reduce','排序规约',PURPLE),('graph_coloring','冲突调度',BLUE),('row_owner','独占写',PINK)]
    card(ax,1110,170,350,320,fc="#0F172A",ec="#334155",r=24,alpha=.88)
    glow_text(ax,1140,455,"Implementation routes",16,MUTED,'normal')
    for i,(a,b,c) in enumerate(labels):
        y=410-i*42; ax.add_patch(Circle((1145,y),8,facecolor=c,edgecolor='none'))
        glow_text(ax,1165,y+4,a,14,TEXT,'bold'); glow_text(ax,1290,y+4,b,13.5,MUTED,'normal')
    return save(fig,"04_creative_algorithm_portfolio")

def slide_treemap_dashboard():
    fig,ax=setup()
    glow_text(ax,80,835,"Workload Treemap Dashboard",34,TEXT)
    glow_text(ax,82,795,"以面积展示代码工作量：哪些模块贡献了当前项目的主要实现规模",18,MUTED,'normal')
    # manual treemap layout proportional-ish
    total=sum(v['lines'] for v in groups.values())
    x0,y0,w,h=95,150,930,560
    items=sorted(groups.items(), key=lambda kv: kv[1]['lines'], reverse=True)
    # slice-and-dice rows
    cur_y=y0; remaining=items[:]
    rows=[remaining[:2], remaining[2:5], remaining[5:]]
    row_heights=[210,185,165]
    for row,rh in zip(rows,row_heights):
        row_sum=sum(v['lines'] for _,v in row); cur_x=x0
        for name,v in row:
            rw=w*v['lines']/row_sum
            c=v['color']; card(ax,cur_x,cur_y,rw-10,rh-10,fc="#10182E",ec=c,lw=2,r=18,alpha=.94)
            ax.add_patch(Rectangle((cur_x+12,cur_y+rh-48),rw-34,25,facecolor=c,edgecolor='none',alpha=.85))
            glow_text(ax,cur_x+24,cur_y+rh-35,v['short'],14,'white')
            glow_text(ax,cur_x+24,cur_y+65,f"{v['lines']} lines",22,c)
            glow_text(ax,cur_x+24,cur_y+35,f"{v['files']} files",13,MUTED,'normal')
            cur_x += rw
        cur_y += rh
    # right KPI rail
    card(ax,1095,575,360,135,fc="#10182E",ec=CYAN,lw=2,r=26,alpha=.92)
    glow_text(ax,1128,665,"Project scale",16,MUTED,'normal'); glow_text(ax,1275,625,f"{total_lines:,} lines",32,CYAN,ha='center')
    card(ax,1095,395,360,135,fc="#10182E",ec=PINK,lw=2,r=26,alpha=.92)
    glow_text(ax,1128,485,"Tracked files",16,MUTED,'normal'); glow_text(ax,1275,445,f"{total_files} files",32,PINK,ha='center')
    card(ax,1095,215,360,135,fc="#10182E",ec=GREEN,lw=2,r=26,alpha=.92)
    glow_text(ax,1128,305,"Main CPU algorithms",16,MUTED,'normal'); glow_text(ax,1275,265,"6 routes",32,GREEN,ha='center')
    return save(fig,"05_creative_workload_treemap")

if __name__ == "__main__":
    outs=[]
    for fn in [slide_constellation, slide_city, slide_neural_architecture, slide_algorithm_radar, slide_treemap_dashboard]:
        outs += fn()
    print("Generated creative assets:")
    for p in outs: print(p)
