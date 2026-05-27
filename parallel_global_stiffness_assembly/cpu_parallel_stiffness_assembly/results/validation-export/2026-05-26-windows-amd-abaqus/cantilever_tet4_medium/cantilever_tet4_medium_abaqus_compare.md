# Validation Displacement Comparison

- Validation level: finite-element probe displacement.
- MATLAB source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_tet4_medium\cantilever_tet4_medium_matlab_displacements.csv`
- Abaqus source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_tet4_medium\cantilever_tet4_medium_abaqus_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `168`, probe `free_tip_center`, abs `0.00046956113390805219`, rel `4.6743669575184488e-08`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 156 | root_center | 6.2207420477075443e-37 | 6.2207420477075442e-07 | reported_no_hard_threshold |
| 162 | midspan_center | 8.6305939352855816e-05 | 2.7548330551703286e-08 | reported_no_hard_threshold |
| 168 | free_tip_center | 0.00046956113390805219 | 4.6743669575184488e-08 | reported_no_hard_threshold |
