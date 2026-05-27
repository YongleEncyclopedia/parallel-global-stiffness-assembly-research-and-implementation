# Validation Displacement Comparison

- Validation level: finite-element probe displacement.
- MATLAB source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_hex8_small\cantilever_hex8_small_matlab_displacements.csv`
- Abaqus source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_hex8_small\cantilever_hex8_small_abaqus_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `14`, probe `free_tip_center`, abs `33.736949148262056`, rel `0.01775632895341258`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 12 | root_center | 7.0306740247554916e-37 | 7.0306740247554908e-07 | reported_no_hard_threshold |
| 13 | midspan_center | 10.297730083986494 | 0.017241316872821787 | reported_no_hard_threshold |
| 14 | free_tip_center | 33.736949148262056 | 0.01775632895341258 | reported_no_hard_threshold |
