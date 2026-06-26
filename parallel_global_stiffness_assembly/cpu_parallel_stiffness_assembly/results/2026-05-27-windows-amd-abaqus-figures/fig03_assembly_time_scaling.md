# Fig. 3 Assembly Time Scaling

**绘制理由。** 这张图回答“AMD Windows 上哪条自研 assembly 路径更快，以及快在哪里”。总时长、相对串行 symbolic baseline 的加速比、最佳线程分解和最佳总时长四个视角互相补充。

**数据来源。** `results/2026-05-26-windows-amd-abaqus-validation-performance/isolated_symbolic_memory/isolated_symbolic_memory.csv`。每一行由 `scripts/run_isolated_symbolic_memory_eval.py` 以独立子进程运行 `symbolic_numeric_eval.exe` 得到。

**参数设置。** WindHub 网格 `3d-WindTurbineHub.inp`，228,384 nodes、1,113,684 Tet4 elements、685,152 DOFs；材料模型 `linear_elastic_solid`；线程范围 `1:8`，对应 AMD Ryzen 7 9800X3D 的物理核心范围；主线后端为 `cpu_atomic`。

**可得结论。** 8 线程 `parallel_symbolic_reuse + cpu_atomic` 达到最低总时长约 1133 ms，相对 `serial symbolic + serial numeric` 的约 4078 ms 为约 3.6x；8 线程 direct/no-symbolic 仍约 2147 ms，慢于 symbolic reuse。

**合理解释。** direct/no-symbolic 省去显式 symbolic 阶段，但付出生成贡献、bucket/merge 与 sort/reduce 的大额代价；预构建 CSR/scatter plan 的 symbolic reuse 在真实 WindHub 网格上更适合复用并行数值写回。
