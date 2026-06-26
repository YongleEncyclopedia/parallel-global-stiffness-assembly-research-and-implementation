# Solver-validation case figures

This package contains two English Nature-style figures for monthly-report comparison:

- `fig_hex8_free_tip_deflection_validation`: structured Hex8/C3D8 cantilever.
- `fig_tet4_free_tip_deflection_validation`: Tet4/C3D4 cantilever.

The plotted metric is the free-tip vertical-deflection percentage discrepancy:

```text
100 * abs(abs(Uz_MATLAB_free_tip) - abs(Uz_FE_free_tip)) / abs(Uz_FE_free_tip)
```

The macOS+COMSOL values are recovered from the legacy report table, while Windows+Abaqus uses the current canonical `free_tip_deflection_rel_pct` summary. The Tet4 sparsity asset in the monthly slide is the unstructured Tet4 topology and is intentionally tracked separately from the three-platform solver-validation Tet4 case.
