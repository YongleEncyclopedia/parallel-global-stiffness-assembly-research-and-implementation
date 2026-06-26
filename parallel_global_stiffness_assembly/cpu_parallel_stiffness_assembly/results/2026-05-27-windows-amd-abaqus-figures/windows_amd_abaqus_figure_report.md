# Windows AMD Abaqus Figure Report

## 图表选择理由

我选择四张定量图，而不是单张大而全的总图：验证误差、位移剖面、组装时间和内存权衡分别回答不同审稿问题。这样可以避免把求解正确性与 assembly 性能混成一个不可审查的结论。

1. `fig01_validation_error_summary`：用自由端挠度百分比证明哪些单元族与 Abaqus reference 对齐，哪些暴露差异。
2. `fig02_probe_displacement_profiles`：确认差异没有来自载荷方向或 probe 映射错位，并显示差异沿悬臂长度的位置。
3. `fig03_assembly_time_scaling`：展示 AMD 物理核心范围内的自研 assembly 时间扩展性。
4. `fig04_memory_tradeoff`：把 Windows OS 内存观测与 estimated lifecycle memory 分开，解释 direct/no-symbolic 的代价。

## 输出文件

- `fig01_validation_error_summary`: `fig01_validation_error_summary.svg`, `fig01_validation_error_summary.pdf`, `fig01_validation_error_summary.png`
- `fig02_probe_displacement_profiles`: `fig02_probe_displacement_profiles.svg`, `fig02_probe_displacement_profiles.pdf`, `fig02_probe_displacement_profiles.png`
- `fig03_assembly_time_scaling`: `fig03_assembly_time_scaling.svg`, `fig03_assembly_time_scaling.pdf`, `fig03_assembly_time_scaling.png`
- `fig04_memory_tradeoff`: `fig04_memory_tradeoff.svg`, `fig04_memory_tradeoff.pdf`, `fig04_memory_tradeoff.png`

## 单图说明

# Fig. 1 Validation Error Summary

**绘制理由。** 这张图回答“悬臂块求解级正确性是否在所有单元类型上同样成立”。主相对差异固定为自由端挠度百分比；逐 probe 三维位移向量差异只作为诊断量，避免把固定端近零位移或中间 probe 当成最终挠度结论。

**数据来源。** `*_abaqus_compare.csv`，路径位于 `results/validation-export/2026-05-26-windows-amd-abaqus` 的四个 case 子目录。每行来自 MATLAB 对自研 C++ 导出的 `K/F/BC` 求解位移与 Abaqus/Standard ODB 抽取位移在同一 probe 节点上的三维位移范数差异；本图的主柱状图和绝对差异图只取 `free_tip_center` 的 `Uz`，并按 `100*abs(abs(matlab_uz)-abs(abaqus_uz))/abs(abaqus_uz)` 转为百分比。

**参数设置。** 几何 `L=1, W=0.2, T=0.1`，材料 `E=1, nu=0.3`，`x=0` 三向固定，`x=L` 总力 `-1` 沿 `load_dof=2`。Abaqus Hex8 使用 `C3D8` full integration，Tet4 使用 `C3D4`。

**可得结论。** Tet4/C3D4 的自由端挠度百分比差异处在近零量级；Hex8/C3D8 的自由端挠度百分比差异约为 1.78% 到 2.98%，不是硬阈值失败，但也不能写成商业求解器等价。

**合理解释。** Tet4 路径与 Abaqus 线性四面体的一致性较强；Hex8 虽同为 full integration，但可能仍存在单元刚度矩阵约定、节点顺序、数值积分实现细节或载荷等效化差异，需要后续单元级能量/刚度隔离。


# Fig. 2 Probe Displacement Profiles

**绘制理由。** 挠度百分比只能给出最终正确性数字，不能说明差异发生在变形曲线的哪里；probe 位移剖面能直接显示 root、midspan、free tip 三个物理位置的 `Uz` 趋势。

**数据来源。** 同一组 `*_abaqus_compare.csv`，使用其中 `matlab_uz` 与 `abaqus_uz` 列。probe 位置来自 `*_probes.csv`，三点分别映射到 `x/L = 0, 0.5, 1`。

**参数设置。** 四个悬臂 case 使用相同材料、边界与载荷；图中灰色连线表示每个 probe 上 MATLAB 与 Abaqus 的局部差异，不代表连续插值误差。

**可得结论。** 四个 case 都保持悬臂梁从 root 到 tip 位移增大的整体物理趋势；Tet4 曲线几乎重合，Hex8 曲线在 midspan 与 tip 处出现可见偏移。图内标注的百分比为 `free_tip_center` 挠度相对差异。

**合理解释。** 位移趋势一致说明边界、载荷方向、节点映射和求解流程没有明显错位；Hex8 偏移集中在非固定 probe，符合单元刚度或积分细节差异对柔度预测产生系统性影响的表现。


# Fig. 3 Assembly Time Scaling

**绘制理由。** 这张图回答“AMD Windows 上哪条自研 assembly 路径更快，以及快在哪里”。总时长、相对串行 symbolic baseline 的加速比、最佳线程分解和最佳总时长四个视角互相补充。

**数据来源。** `results/2026-05-26-windows-amd-abaqus-validation-performance/isolated_symbolic_memory/isolated_symbolic_memory.csv`。每一行由 `scripts/run_isolated_symbolic_memory_eval.py` 以独立子进程运行 `symbolic_numeric_eval.exe` 得到。

**参数设置。** WindHub 网格 `3d-WindTurbineHub.inp`，228,384 nodes、1,113,684 Tet4 elements、685,152 DOFs；材料模型 `linear_elastic_solid`；线程范围 `1:8`，对应 AMD Ryzen 7 9800X3D 的物理核心范围；主线后端为 `cpu_atomic`。

**可得结论。** 8 线程 `parallel_symbolic_reuse + cpu_atomic` 达到最低总时长约 1133 ms，相对 `serial symbolic + serial numeric` 的约 4078 ms 为约 3.6x；8 线程 direct/no-symbolic 仍约 2147 ms，慢于 symbolic reuse。

**合理解释。** direct/no-symbolic 省去显式 symbolic 阶段，但付出生成贡献、bucket/merge 与 sort/reduce 的大额代价；预构建 CSR/scatter plan 的 symbolic reuse 在真实 WindHub 网格上更适合复用并行数值写回。


# Fig. 4 Memory and Time Tradeoff

**绘制理由。** 性能结论不能只看时间；direct/no-symbolic 的核心成本之一是瞬时 contribution buffer。该图把 OS 观测内存、private bytes、时间-内存运行点和 estimated lifecycle peak 放在一起，避免把模型估计冒充系统观测。

**数据来源。** `results/2026-05-26-windows-amd-abaqus-validation-performance/isolated_symbolic_memory/isolated_symbolic_memory.csv` 的 `isolated_peak_working_set_mb`、`isolated_peak_private_bytes_mb` 和 `estimated_peak_bytes`。Windows 下 `isolated_peak_rss_mb` 是历史 schema 列名，本轮实际度量为 `windows_peak_working_set`。

**参数设置。** 每个策略/线程组合在独立子进程中运行；OS 内存来自 Windows `GetProcessMemoryInfo.PeakWorkingSetSize`，private bytes 来自采样到的 `PeakPagefileUsage`/`PrivateUsage`。

**可得结论。** symbolic reuse 的 peak working set 约 2.26 GiB 并随线程变化很小；direct/no-symbolic 在同一线程范围内约 3.65 到 5.45 GiB，且 8 线程 estimated lifecycle peak 也明显高于 symbolic reuse。

**合理解释。** symbolic reuse 的持久 CSR/plan 与输出矩阵占主导，内存较稳定；direct/no-symbolic 需要一次性保存大量贡献并排序归并，导致临时内存和 OS 观测峰值都更高。


## QA 说明

- 绘图后应运行脚本内置 QA 或外部检查，确认每张 PNG 非空、尺寸有效，且 SVG/PDF/PNG 三种格式均存在。
- 所有图由同一 Python 脚本生成，未混用 R 或交互式绘图后端。
- `source_data/` 下保留清洗后的图表源数据，便于后续复核或重绘。
