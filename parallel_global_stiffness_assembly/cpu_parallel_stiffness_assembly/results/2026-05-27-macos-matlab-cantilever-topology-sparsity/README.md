# macOS + MATLAB cantilever topology and sparsity figures

- MATLAB: `26.1.0.3030274 (R2026a) Prerelease`
- PDE Toolbox available: `true`
- validation_export: `build/codex-hex8-physics/bin/validation_export`（生成时使用的历史构建路径）

These figures visualize mesh topology and global stiffness sparsity only; they do not claim displacement-solve correctness.

仓库保留可复核的 Matrix Market/CSV/JSON 源数据和 PNG 预览；MATLAB `.fig`、重复 SVG 和 contact-sheet PDF 属于可重建派生产物，已在 Issue #49 第一阶段清理。

| case | mesh source | stiffness model provenance | nodes | elements | DOFs | nnz(K) |
|---|---|---:|---:|---:|---:|---:|
| `cantilever_hex8_medium` | validation_export generated structured Hex8 grid, nx=12, ny=4, nz=4 | `linear_elastic_solid` | 325 | 192 | 975 | 56277 |
| `cantilever_tet4_unstructured_medium` | MATLAB PDE Toolbox linear Tet4 mesh, Hmax=0.05 | `linear_elastic_solid` | 344 | 1098 | 1032 | 33858 |

Tet4 case uses MATLAB PDE Toolbox `generateMesh(..., 'GeometricOrder', 'linear', 'Hmax', 0.05)` on the same `L=1, W=0.2, T=0.1` cantilever block.
