# Fig. 2 Probe Displacement Profiles

**绘制理由。** 挠度百分比只能给出最终正确性数字，不能说明差异发生在变形曲线的哪里；probe 位移剖面能直接显示 root、midspan、free tip 三个物理位置的 `Uz` 趋势。

**数据来源。** 同一组 `*_abaqus_compare.csv`，使用其中 `matlab_uz` 与 `abaqus_uz` 列。probe 位置来自 `*_probes.csv`，三点分别映射到 `x/L = 0, 0.5, 1`。

**参数设置。** 四个悬臂 case 使用相同材料、边界与载荷；图中灰色连线表示每个 probe 上 MATLAB 与 Abaqus 的局部差异，不代表连续插值误差。

**可得结论。** 四个 case 都保持悬臂梁从 root 到 tip 位移增大的整体物理趋势；Tet4 曲线几乎重合，Hex8 曲线在 midspan 与 tip 处出现可见偏移。图内标注的百分比为 `free_tip_center` 挠度相对差异。

**合理解释。** 位移趋势一致说明边界、载荷方向、节点映射和求解流程没有明显错位；Hex8 偏移集中在非固定 probe，符合单元刚度或积分细节差异对柔度预测产生系统性影响的表现。
