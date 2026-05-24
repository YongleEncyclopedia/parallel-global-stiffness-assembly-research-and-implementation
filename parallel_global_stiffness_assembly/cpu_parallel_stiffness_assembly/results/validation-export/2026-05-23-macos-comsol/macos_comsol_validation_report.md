# macOS + COMSOL Solve-Level Validation Report

Date: 2026-05-23

## Scope

This package validates the C++ `validation_export` solve-level path on macOS using MATLAB and COMSOL:

- C++ exports self-assembled `K/F/BC/probes/metadata`.
- MATLAB solves the exported self-assembled stiffness system.
- COMSOL 6.2 is used as an independent finite-element displacement reference at the same probe points.
- macOS/Apple Silicon results here are correctness evidence only; they are not the Intel/AMD performance conclusion.
- All validation exports use `--stiffness-model linear_elastic_solid`. No `legacy_synthetic` result is used.

## Git State

Repository root:

`/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation`

CPU project root:

`/Users/macstudio/Documents/Intern_Peking University_supu/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`

Git state recorded after this validation package was generated:

- Branch: `main`
- Commit: `0568262508d2553eefc53f3549c336501adc5465`
- Initial pre-work status: clean `main...origin/main`
- Final dirty status: expected local changes from this validation package:
  - modified `scripts/compare_validation_displacements.py`
  - added `tests/python/test_compare_validation_displacements.py`
  - added `results/validation-export/2026-05-23-macos-comsol/**`

No commit, push, file deletion, Beamer rewrite, or historical report rewrite was performed.

## Environment

| Item | Value |
| --- | --- |
| Host | Apple M4 Max |
| OS | macOS 26.5, build 25F71, arm64 |
| Kernel | Darwin 25.5.0 |
| Compiler | Apple clang 21.0.0, `/usr/bin/c++` |
| CMake | 4.3.2 |
| Build type | Release |
| OpenMP | enabled, `OpenMP_CXX_SPEC_DATE=202011`, `/opt/homebrew/opt/libomp/lib/libomp.dylib` |
| Git LFS | `git-lfs/3.7.1` |
| MATLAB | R2026a, `26.1.0.3203278`, `MACA64`, `/Applications/MATLAB_R2026a.app/bin/matlab` |
| COMSOL | COMSOL Multiphysics 6.2.0.339, `/Applications/COMSOL62/Multiphysics/bin/comsol` |
| COMSOL automation | LiveLink for MATLAB through local `mphserver` on port `20361` |

`matlab` and `comsol` were not in `PATH`; absolute application paths were used.

## Commands

The repository root has no `CMakeLists.txt`, so the requested CMake workflow was executed from the CPU project root.

```bash
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
python3 tests/correctness/verify_validation_export.py build/cpu-release/bin/validation_export /tmp/pgsa_validation_export_verify
```

Validation export and MATLAB solve:

```bash
RESULT_ROOT="results/validation-export/$(date +%F)-macos-comsol"
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-release/bin/validation_export \
  --out-root "$RESULT_ROOT" \
  --cases cantilever_hex8_small,cantilever_hex8_medium,cantilever_tet4_small,cantilever_tet4_medium \
  --stiffness-model linear_elastic_solid \
  --run-matlab \
  --matlab-bin /Applications/MATLAB_R2026a.app/bin/matlab
```

COMSOL automation:

```bash
/Applications/COMSOL62/Multiphysics/bin/comsol mphserver -port 20361 -silent -login never -multi on
/Applications/MATLAB_R2026a.app/bin/matlab -batch \
  "addpath('results/validation-export/2026-05-23-macos-comsol'); run_comsol_validation('results/validation-export/2026-05-23-macos-comsol',20361)"
```

COMSOL comparison:

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab "$CASE_DIR/${PREFIX}_matlab_displacements.csv" \
  --abaqus "$CASE_DIR/${PREFIX}_comsol_displacements.csv" \
  --reference-solver comsol \
  --probes "$CASE_DIR/${PREFIX}_probes.csv" \
  --out-csv "$CASE_DIR/${PREFIX}_comsol_compare.csv" \
  --out-md "$CASE_DIR/${PREFIX}_comsol_compare.md"
```

The path argument remains `--abaqus` for backward compatibility, but the output labels and CSV columns are `COMSOL` / `comsol_*` when `--reference-solver comsol` is used.

## Build And Test Results

| Check | Result |
| --- | --- |
| CMake configure | passed |
| CMake build | passed |
| CTest | passed, 11/11 |
| `verify_validation_export.py` | passed |
| New comparison-script unittest | passed |

## Result Root

`results/validation-export/2026-05-23-macos-comsol`

Top-level files:

- `validation_export_manifest.json`
- `run_comsol_validation.m`
- `comsol_reference_status.csv`
- `macos_comsol_validation_report.md`

Each case directory contains:

- `*_K.mtx`
- `*_force.csv`
- `*_bc.csv`
- `*_probes.csv`
- `*_metadata.json`
- `*_matlab_displacements.csv`
- `*_matlab_probe_summary.csv`
- `*_comsol_displacements.csv`
- `*_comsol_compare.csv`
- `*_comsol_compare.md`
- `*_comsol_reference.mph`

## MATLAB Solve Status

| Case | Nodes | Elements | Fixed DOFs | Free DOFs | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `cantilever_hex8_small` | 27 | 8 | 27 | 54 | solved |
| `cantilever_hex8_medium` | 325 | 192 | 75 | 900 | solved |
| `cantilever_tet4_small` | 27 | 48 | 27 | 54 | solved |
| `cantilever_tet4_medium` | 325 | 1152 | 75 | 900 | solved |

## COMSOL Reference Status

The COMSOL workflow directly builds imported meshes matching the C++ structured-grid node coordinates and element connectivity, then solves small-strain isotropic linear elasticity with linear displacement shape functions.

| Case | COMSOL mesh | Fixed boundary count | Loaded boundary count | Status |
| --- | --- | ---: | ---: | --- |
| `cantilever_hex8_small` | imported linear hexahedral mesh | 1 | 1 | solved |
| `cantilever_hex8_medium` | imported linear hexahedral mesh | 1 | 1 | solved |
| `cantilever_tet4_small` | imported linear tetrahedral mesh | 1 | 1 | solved |
| `cantilever_tet4_medium` | imported linear tetrahedral mesh | 1 | 1 | solved |

COMSOL load equivalence:

- Loaded face area: `W*T = 0.2*0.1 = 0.02`
- COMSOL traction: `Fz = -50`
- Integrated total force: `-50 * 0.02 = -1`
- Direction: `z` displacement/load component, matching `load_dof=2`

No GUI-only COMSOL export was needed. The only manual runtime prerequisite is starting `mphserver` before running `run_comsol_validation.m`.

## Probe Difference Summary

Differences are vector norms of MATLAB displacement minus COMSOL displacement at the exported probe nodes. No hard pass/fail threshold is imposed.

| Case | Max abs diff | Max abs location | Max rel diff | Max rel location | Interpretation |
| --- | ---: | --- | ---: | --- | --- |
| `cantilever_hex8_small` | `1.4233997908661422` | node `14`, `free_tip_center` | `0.00076212099012000652` | node `14`, `free_tip_center` | consistent at sub-0.1% relative level |
| `cantilever_hex8_medium` | `3.0175107977865991` | node `168`, `free_tip_center` | `0.00019620788352818085` | node `168`, `free_tip_center` | consistent at sub-0.1% relative level |
| `cantilever_tet4_small` | `0.60212270541508794` | node `14`, `free_tip_center` | `0.00079799014272406027` | node `14`, `free_tip_center` | consistent at sub-0.1% relative level |
| `cantilever_tet4_medium` | `1.7795110578297202` | node `168`, `free_tip_center` | `0.00017711466609625357` | node `168`, `free_tip_center` | consistent at sub-0.1% relative level |

The largest absolute differences occur at the free tip, where displacements are largest. Root-center probes are exactly fixed in both MATLAB and COMSOL outputs.

## Equivalence Checklist

| Item | C++/MATLAB export | COMSOL reference | Status |
| --- | --- | --- | --- |
| Geometry | `L=1`, `W=0.2`, `T=0.1` | same imported coordinates | matched |
| Coordinates | block from `x=0` to `x=L` | same | matched |
| Material | isotropic linear elasticity, `E=1`, `nu=0.3` | same `E`, `nu` through COMSOL material `Enu` group | matched |
| Kinematics | small-strain linear elastic solid | Solid Mechanics stationary linear solve | matched |
| Hex element formulation | `Hex8/C3D8`, 2x2x2 Gauss full integration in C++ | imported linear hexahedral COMSOL mesh, linear displacement order | closest COMSOL reference; integration is COMSOL default |
| Tet element formulation | `Tet4/C3D4`, constant-strain Tet4 | imported linear tetrahedral COMSOL mesh, linear displacement order | matched |
| Boundary condition | `x=0` fixed in `ux,uy,uz` | `Fixed` on `x=0` boundary | matched |
| Load | total `-1` on `x=L`, `load_dof=2` | uniform `FperArea_z=-50` on area `0.02` | matched total force |
| Units | dimensionless/SI-consistent numerical values | same numerical values | matched |
| Probe mapping | exported node probes | evaluated at same coordinates and node ids | matched, nearest distance `0` |

The COMSOL imported Hex8 vertex order differs from the C++ local order. `run_comsol_validation.m` maps C++ Hex8 ordering to COMSOL's imported-mesh ordering before solving; this is a mesh-import convention change only, not a change to the C++ validation export.

## Notes And Risks

- COMSOL's exact internal quadrature setting for imported linear hexahedra is not separately exported by this workflow; it is treated as the closest COMSOL Solid Mechanics reference to C3D8/full integration.
- The comparison script change is backward compatible: existing Abaqus-style invocations still work, while `--reference-solver comsol` changes labels and column names for this report.
- The result-root COMSOL workflow is intentionally local to this package. If this becomes a recurring workflow, promote it to `scripts/` with broader tests and CLI options.
