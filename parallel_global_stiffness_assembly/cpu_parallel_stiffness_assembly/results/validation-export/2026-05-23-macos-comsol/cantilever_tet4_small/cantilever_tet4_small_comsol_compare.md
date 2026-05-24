# Validation Displacement Comparison

- MATLAB source: `results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_small/cantilever_tet4_small_matlab_displacements.csv`
- COMSOL source: `results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_small/cantilever_tet4_small_comsol_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `14`, probe `free_tip_center`, abs `0.60212270541508794`, rel `0.00079799014272406027`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 12 | root_center | 0 | 0 | reported_no_hard_threshold |
| 13 | midspan_center | 0.074092496920321022 | 0.0002979819273880457 | reported_no_hard_threshold |
| 14 | free_tip_center | 0.60212270541508794 | 0.00079799014272406027 | reported_no_hard_threshold |
