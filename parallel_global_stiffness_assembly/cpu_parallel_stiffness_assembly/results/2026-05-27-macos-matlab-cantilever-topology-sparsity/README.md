# macOS + MATLAB cantilever topology and sparsity figures

- MATLAB: `26.1.0.3030274 (R2026a) Prerelease`
- PDE Toolbox available: `true`
- validation_export: `/Users/haohua_jiang/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/build/codex-matlab-cantilever/bin/validation_export`

These figures visualize mesh topology and global stiffness sparsity only; they do not claim displacement-solve correctness.

| case | mesh source | stiffness model provenance | nodes | elements | DOFs | nnz(K) |
|---|---|---:|---:|---:|---:|---:|
| `cantilever_hex8_medium` | validation_export generated structured Hex8 grid, nx=12, ny=4, nz=4 | `legacy_synthetic` | 325 | 192 | 975 | 56277 |
| `cantilever_tet4_unstructured_medium` | MATLAB PDE Toolbox linear Tet4 mesh, Hmax=0.05 | `linear_elastic_solid` | 344 | 1098 | 1032 | 33858 |

Tet4 case uses MATLAB PDE Toolbox `generateMesh(..., 'GeometricOrder', 'linear', 'Hmax', 0.05)` on the same `L=1, W=0.2, T=0.1` cantilever block.
