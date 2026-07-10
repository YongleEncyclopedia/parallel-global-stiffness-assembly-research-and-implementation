# 2026-07-10 macOS ARM64 MATLAB 四例 smoke

## 结论

基于提交 `8451261ce6585875ba53c3c4097a1811c59e4c0a`，四个固定 validation case 均完成 `linear_elastic_solid` 七文件导出和 MATLAB 求解。Runner manifest 的最终状态为 `SOLVER_RUN_COMPLETE`，四例的 export 与 MATLAB 状态均为 `PASS`。

本结果证明 C++ 导出、Matrix Market 下三角重建、零基 CSV 映射、Dirichlet 消元、MATLAB 线性求解及结果落盘可以在当前许可证主机上闭环。它不是与 Abaqus、CalculiX 或 COMSOL 的独立求解器对比，也不设置物理 hard threshold。

## 环境

- macOS 26.5.2（build `25F84`），Apple M5，`arm64`
- MacBook Pro `Mac17,2`，$10$ 个物理核心（$4$ 个性能核心、$6$ 个能效核心），$16\,\mathrm{GiB}$ 内存
- AppleClang 21.0.0、CMake 4.3.4、Ninja 1.13、Python 3.12.13
- `cpu-serial` Release 构建，`PGSA_HAS_OPENMP=0`
- MATLAB 26.1.0.3276743（R2026a Update 3），许可证探测为 `true`
- MATLAB 线性求解器：backslash

机器可读环境见 [`environment.json`](environment.json)。该文件不保存主机序列号、硬件 UUID、UDID、用户名或凭据。

## 可复制命令

工作目录为 CPU 子项目根目录：

```bash
export PATH=/Users/macbook_prom5/.codex/venvs/pgsa-issue19/bin:$PATH
cmake --preset cpu-serial
cmake --build --preset cpu-serial
ctest --preset cpu-serial --output-on-failure

python scripts/run_validation_export.py \
  --validation-export build/cpu-serial \
  --out-root results/validation-export/2026-07-10-macos-arm64-matlab-smoke \
  --run-matlab \
  --matlab-bin /Applications/MATLAB_R2026a.app/bin/matlab
```

本次为了同步保存标准输出，首次运行时预先创建输出目录并添加了 `--overwrite`，完整命令展开见 [`run.log`](run.log) 和 [`validation_export_manifest.json`](validation_export_manifest.json)。

## 四例求解摘要

下表中的 $r_{\mathrm{abs}}$、$r_{\mathrm{rel}}$ 和 $\lVert f_f'\rVert_2$ 直接来自每例 `*_matlab_solve_metadata.json`。`PASS` 只表示输出完整且残差为有限非负数，不代表人为设定的物理阈值判断。

| case | 单元 | 节点 | 单元数 | 自由度 | 约束自由度 | $r_{\mathrm{abs}}$ | $r_{\mathrm{rel}}$ | $\lVert f_f'\rVert_2$ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `cantilever_hex8_small` | Hex8 | $27$ | $8$ | $81$ | $27$ | $6.39179667083594\times10^{-13}$ | $1.917539001250782\times10^{-12}$ | $0.3333333333333333$ |
| `cantilever_hex8_medium` | Hex8 | $325$ | $192$ | $975$ | $75$ | $6.55729356475507\times10^{-12}$ | $3.278646782377535\times10^{-11}$ | $0.2$ |
| `cantilever_tet4_small` | Tet4 | $27$ | $48$ | $81$ | $27$ | $4.707023307876212\times10^{-13}$ | $1.412106992362864\times10^{-12}$ | $0.3333333333333333$ |
| `cantilever_tet4_medium` | Tet4 | $325$ | $1152$ | $975$ | $75$ | $7.54790045133528\times10^{-12}$ | $3.77395022566764\times10^{-11}$ | $0.2$ |

## 文件契约

每个 case 目录包含：

1. `K.mtx` 对应的 Matrix Market 对称下三角矩阵；
2. `force.csv`、`bc.csv`、`probes.csv`、`nodes.csv`、`elements.csv`；
3. C++ `metadata.json`；
4. MATLAB 全节点位移、probe summary 和 solve metadata。

根目录还包含：

- `validation_export_manifest.json`：四例命令与 export/MATLAB 状态；
- `environment.json`：去敏后的机器、工具链和许可证环境；
- `run.log`：实际 runner 与 MATLAB 调用记录；
- `SHA256SUMS`：除清单自身以外所有证据文件的 SHA-256。

重新核验哈希：

```bash
shasum -a 256 -c SHA256SUMS
```

## 解释边界

- 四例使用相同的 $K u=f$、材料、载荷、约束和 `linear_elastic_solid` 导出路径。
- MATLAB metadata 中的绝对文件路径记录本次实际 worktree，是 provenance；worktree 删除后不应把这些路径当作当前入口。
- Abaqus、CalculiX 和 COMSOL 的跨求解器差异仍由各自结果包与后续 Issues 负责，本 smoke 不更新这些结论。
