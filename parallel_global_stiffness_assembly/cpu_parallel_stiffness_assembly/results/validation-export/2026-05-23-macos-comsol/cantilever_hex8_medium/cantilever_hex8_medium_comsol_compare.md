# Validation Displacement Comparison

- MATLAB source: `results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_medium/cantilever_hex8_medium_matlab_displacements.csv`
- COMSOL source: `results/validation-export/2026-05-23-macos-comsol/cantilever_hex8_medium/cantilever_hex8_medium_comsol_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `168`, probe `free_tip_center`, abs `3.0175107977865991`, rel `0.00019620788352818085`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 156 | root_center | 0 | 0 | reported_no_hard_threshold |
| 162 | midspan_center | 1.7704916900941293e-05 | 3.7024835546223152e-09 | reported_no_hard_threshold |
| 168 | free_tip_center | 3.0175107977865991 | 0.00019620788352818085 | reported_no_hard_threshold |
