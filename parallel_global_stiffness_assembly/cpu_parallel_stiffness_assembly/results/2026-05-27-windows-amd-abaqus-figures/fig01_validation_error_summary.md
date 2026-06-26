# Fig. 1 Validation Error Summary

**绘制理由。** 这张图回答“悬臂块求解级正确性是否在所有单元类型上同样成立”。主相对差异固定为自由端挠度百分比；逐 probe 三维位移向量差异只作为诊断量，避免把固定端近零位移或中间 probe 当成最终挠度结论。

**数据来源。** `*_abaqus_compare.csv`，路径位于 `results/validation-export/2026-05-26-windows-amd-abaqus` 的四个 case 子目录。每行来自 MATLAB 对自研 C++ 导出的 `K/F/BC` 求解位移与 Abaqus/Standard ODB 抽取位移在同一 probe 节点上的三维位移范数差异；本图的主柱状图和绝对差异图只取 `free_tip_center` 的 `Uz`，并按 `100*abs(abs(matlab_uz)-abs(abaqus_uz))/abs(abaqus_uz)` 转为百分比。

**参数设置。** 几何 `L=1, W=0.2, T=0.1`，材料 `E=1, nu=0.3`，`x=0` 三向固定，`x=L` 总力 `-1` 沿 `load_dof=2`。Abaqus Hex8 使用 `C3D8` full integration，Tet4 使用 `C3D4`。

**可得结论。** Tet4/C3D4 的自由端挠度百分比差异处在近零量级；Hex8/C3D8 的自由端挠度百分比差异约为 1.78% 到 2.98%，不是硬阈值失败，但也不能写成商业求解器等价。

**合理解释。** Tet4 路径与 Abaqus 线性四面体的一致性较强；Hex8 虽同为 full integration，但可能仍存在单元刚度矩阵约定、节点顺序、数值积分实现细节或载荷等效化差异，需要后续单元级能量/刚度隔离。
