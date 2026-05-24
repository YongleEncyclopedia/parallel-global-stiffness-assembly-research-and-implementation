# Validation Displacement Comparison

- MATLAB source: `results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_small/cantilever_hex8_small_matlab_displacements.csv`
- COMSOL source: `results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_small/cantilever_hex8_small_comsol_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `14`, probe `free_tip_center`, abs `1.4233997908661422`, rel `0.00076212099012000652`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 12 | root_center | 0 | 0 | reported_no_hard_threshold |
| 13 | midspan_center | 0.39104015696455008 | 0.00066664222889585404 | reported_no_hard_threshold |
| 14 | free_tip_center | 1.4233997908661422 | 0.00076212099012000652 | reported_no_hard_threshold |
