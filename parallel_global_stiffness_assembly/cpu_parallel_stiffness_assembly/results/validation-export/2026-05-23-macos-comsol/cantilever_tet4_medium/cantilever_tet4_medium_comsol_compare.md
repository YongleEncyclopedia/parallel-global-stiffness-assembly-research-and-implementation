# Validation Displacement Comparison

- MATLAB source: `results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_medium/cantilever_tet4_medium_matlab_displacements.csv`
- COMSOL source: `results/validation-export/2026-05-23-macos-comsol/cantilever_tet4_medium/cantilever_tet4_medium_comsol_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `168`, probe `free_tip_center`, abs `1.7795110578297202`, rel `0.00017711466609625357`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 156 | root_center | 0 | 0 | reported_no_hard_threshold |
| 162 | midspan_center | 0.0036827307129219116 | 1.1755038810110551e-06 | reported_no_hard_threshold |
| 168 | free_tip_center | 1.7795110578297202 | 0.00017711466609625357 | reported_no_hard_threshold |
