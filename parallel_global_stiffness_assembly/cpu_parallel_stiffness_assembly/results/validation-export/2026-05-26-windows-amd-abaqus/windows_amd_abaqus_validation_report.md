# Windows AMD Abaqus Validation Report

## 范围与结论

- 本报告只评价 `validation_export -> MATLAB -> Abaqus/Standard -> probe compare` 的求解级正确性闭环。
- `validation_export` 已导出 `K.mtx`、`force.csv`、`bc.csv`、`probes.csv` 和 `metadata.json`；MATLAB 求解自研 C++ 矩阵；Abaqus 位移 CSV 进入同一 probe 差异表。
- 不设置硬阈值，也不因 Abaqus 是商业软件直接声明等价。Tet4/C3D4 probe 差异达到近零量级；Hex8/C3D8 存在 1.8% 到 3.3% 的 probe 相对差异，属于需要单元刚度/积分约定继续隔离的可报告差异。
- Abaqus 求解耗时不参与 assembly speedup；性能报告只比较自研 assembly。

## 环境记录

| 项 | 记录 |
| --- | --- |
| 日期 | 2026-05-26 |
| 操作系统 | Microsoft Windows 11 专业工作站版, Version 10.0.26200, Build 26200, 64 位 |
| CPU | AMD Ryzen 7 9800X3D 8-Core Processor |
| 核心 | 8 physical cores, 16 logical processors, MaxClockSpeed 4700 MHz |
| 内存 | 33,410,088,960 bytes physical, Abaqus system info reported 31,863 MB physical memory |
| 电源计划 | Balanced / 平衡 (`381b4222-f694-41f0-9685-ff5bb260df2e`) |
| CMake / generator | CMake 4.3.3, Ninja |
| C++ compiler | GNU 15.2.0, `C:/msys64/mingw64/bin/c++.exe` |
| OpenMP | `-fopenmp`, OpenMP spec date 201511, `libgomp` + `mingwthrd` |
| Python | Python 3.13.13 |
| MATLAB | 25.2.0.2998904 (R2025b) |
| Abaqus | Abaqus 2025, installed under `D:\SIMULIA`, command `D:\SIMULIA\Commands\abaqus.BAT` |
| 备注 | `scripts/inspect_cpu_platform.py` 在本机把 physical cores 误报为 16；本报告采用 `Win32_Processor.NumberOfCores = 8` 作为线程主线范围依据。Abaqus system info 未找到 C++/Fortran compiler，但本轮未使用用户子程序。 |

## 模型对齐检查

| 检查项 | 状态 |
| --- | --- |
| 几何/单位 | `L=1, W=0.2, T=0.1`；无量纲材料与载荷，MATLAB 与 Abaqus 使用同一坐标。 |
| 材料 | `E=1`, `nu=0.3`, Abaqus `*Elastic`。 |
| 约束 | `x=0` 面三向位移固定；Abaqus `FIXED, 1, 3, 0.`。 |
| 载荷 | `x=L` 面节点均分总力 `-1`；C++ `load_dof=2` 对应 Abaqus DOF 3。 |
| Hex8 | Abaqus `C3D8`，full integration；未使用 `C3D8R`。 |
| Tet4 | Abaqus `C3D4`，线性四面体。 |
| probe 映射 | Abaqus node label = C++ 0-based node + 1；每个 case 写出 `abaqus/*_node_mapping.csv`。 |
| Windows 路径 | Abaqus job 使用短别名 `h8s/h8m/t4s/t4m`，避免 Abaqus/Windows 255 字符路径限制；别名只影响文件名，不影响模型。 |

## Case 摘要

| case | Abaqus element | nodes | elements | max abs diff | max abs location | max rel diff | max rel location | 解释状态 |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| `cantilever_hex8_small` | `C3D8` | 27 | 8 | 33.736949 | node `14` / `free_tip_center` | 0.017756 | node `14` / `free_tip_center` | Hex8/C3D8 同为 full integration，但 probe 差异未到近零；需后续用单元级刚度/能量检查隔离实现或 Abaqus 约定差异。 |
| `cantilever_hex8_medium` | `C3D8` | 325 | 192 | 472.372686 | node `168` / `free_tip_center` | 0.033471 | node `162` / `midspan_center` | Hex8/C3D8 同为 full integration，但 probe 差异未到近零；需后续用单元级刚度/能量检查隔离实现或 Abaqus 约定差异。 |
| `cantilever_tet4_small` | `C3D4` | 27 | 48 | 4.49979e-06 | node `13` / `midspan_center` | 7.47052e-07 | node `12` / `root_center` | Tet4/C3D4 probe 位移与 MATLAB 自研矩阵求解近零差异；root 相对差异受近零分母影响。 |
| `cantilever_tet4_medium` | `C3D4` | 325 | 1152 | 0.000469561 | node `168` / `free_tip_center` | 6.22074e-07 | node `156` / `root_center` | Tet4/C3D4 probe 位移与 MATLAB 自研矩阵求解近零差异；root 相对差异受近零分母影响。 |

## 主要产物

- validation manifest: `results\validation-export\2026-05-26-windows-amd-abaqus\validation_export_manifest.json`
- Abaqus manifest: `results\validation-export\2026-05-26-windows-amd-abaqus\abaqus_validation_manifest.json`
- 每个 case 目录包含 C++ 导出的 `K/force/bc/probes/metadata`、MATLAB 位移、Abaqus 位移、probe compare CSV/MD、Abaqus `.inp/.odb` 与节点映射表。
- Abaqus 自动化脚本：`scripts/run_abaqus_validation.py`；ODB 抽取脚本：`scripts/extract_abaqus_displacements.py`。

## 风险与限制

- Hex8 的 1.8% 到 3.3% 差异不能写成等价；它是本轮商业求解器参考给出的有效差异信号。
- Abaqus `.bat` 在 Windows 上返回码对部分失败不够可靠；runner 已增加 ODB 存在性检查。
- 本结果目录保留了一次长 job name 触发 Windows path limit 后产生的早期 Abaqus 日志文件；最终 manifest 指向短别名 job 的 `.inp/.odb`。
