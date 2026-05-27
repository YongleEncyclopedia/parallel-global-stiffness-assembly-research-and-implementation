# Validation Displacement Comparison

- Validation level: finite-element probe displacement.
- MATLAB source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_tet4_small\cantilever_tet4_small_matlab_displacements.csv`
- Abaqus source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_tet4_small\cantilever_tet4_small_abaqus_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `13`, probe `midspan_center`, abs `4.4997914218258866e-06`, rel `1.8102332504803508e-08`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 12 | root_center | 7.470520502027096e-37 | 7.4705205020270952e-07 | reported_no_hard_threshold |
| 13 | midspan_center | 4.4997914218258866e-06 | 1.8102332504803508e-08 | reported_no_hard_threshold |
| 14 | free_tip_center | 1.7470671906460184e-06 | 2.3172105167644751e-09 | reported_no_hard_threshold |
