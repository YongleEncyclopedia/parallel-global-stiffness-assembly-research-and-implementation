# 悬臂梁最大挠度相对差异图

## 用途

比较三类平台上 MATLAB 自研矩阵求解结果与参考有限元求解器结果的自由端最大挠度相对差异。

## 当前口径

- 两张图分别使用“四面体单元”和“六面体单元”的直观名称。
- 指标统一为百分比：

$$
\mathrm{relative\ difference}(\%) =
100\frac{\left|\left|U_z^{\mathrm{MATLAB}}\right|-\left|U_z^{\mathrm{FE}}\right|\right|}
{\left|U_z^{\mathrm{FE}}\right|}.
$$

- Windows AMD + Abaqus 的六面体单元值采用复测结果 `0.000005823%`，不使用早期 `2.98%` 图件。

## 内容

- `source_data/free_tip_max_deflection_relative_difference.csv`：唯一绘图数据源。
- `assets/fig_tet4_simple_deflection_validation.*`：四面体单元。
- `assets/fig_hex8_simple_deflection_validation.*`：六面体单元。

工作树保留 `SVG`、`PDF`、`PNG`；可由脚本重建的 `TIFF` 不保留。
