# Fig. 1 Validation Error Summary

**绘制理由。** 这张图回答“求解级正确性是否在所有单元类型上同样成立”。相对差异和绝对差异分别处理尺度无关比较与工程量级比较，避免只看一种误差口径。

**数据来源。** `*_abaqus_compare.csv`，路径位于 `results\validation-export\2026-05-26-windows-amd-abaqus` 的四个 case 子目录。每行来自 MATLAB 对自研 C++ 导出的 `K/F/BC` 求解位移与 Abaqus/Standard ODB 抽取位移在同一 probe 节点上的三维位移范数差异。

**参数设置。** 几何 `L=1, W=0.2, T=0.1`，材料 `E=1, nu=0.3`，`x=0` 三向固定，`x=L` 总力 `-1` 沿 `load_dof=2`。Abaqus Hex8 使用 `C3D8` full integration，Tet4 使用 `C3D4`。

**可得结论。** Tet4/C3D4 的 probe 差异处在近零量级；Hex8/C3D8 的最大相对差异约为 1.8% 到 3.3%，不是硬阈值失败，但也不能写成商业求解器等价。

**合理解释。** Tet4 路径与 Abaqus 线性四面体的一致性较强；Hex8 虽同为 full integration，但可能仍存在单元刚度矩阵约定、节点顺序、数值积分实现细节或载荷等效化差异，需要后续单元级能量/刚度隔离。
