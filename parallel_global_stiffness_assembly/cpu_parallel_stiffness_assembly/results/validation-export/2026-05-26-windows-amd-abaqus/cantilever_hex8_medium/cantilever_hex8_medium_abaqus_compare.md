# Validation Displacement Comparison

- Validation level: finite-element probe displacement.
- MATLAB source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_hex8_medium\cantilever_hex8_medium_matlab_displacements.csv`
- Abaqus source: `results\validation-export\2026-05-26-windows-amd-abaqus\cantilever_hex8_medium\cantilever_hex8_medium_abaqus_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max difference: node `168`, probe `free_tip_center`, abs `472.37268621999647`, rel `0.029805500991983754`.

| node | probe | abs diff | rel diff | status |
| ---: | --- | ---: | ---: | --- |
| 156 | root_center | 2.7979038119367946e-37 | 2.7979038119367943e-07 | reported_no_hard_threshold |
| 162 | midspan_center | 165.5995445874305 | 0.03347134166150334 | reported_no_hard_threshold |
| 168 | free_tip_center | 472.37268621999647 | 0.029805500991983754 | reported_no_hard_threshold |
