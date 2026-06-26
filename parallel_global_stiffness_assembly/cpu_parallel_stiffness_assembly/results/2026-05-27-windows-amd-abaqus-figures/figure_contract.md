# Windows AMD Abaqus Figure Contract

Core conclusion:
Windows AMD 平台的 Abaqus validation 显示 Tet4/C3D4 自由端挠度百分比差异接近零，Hex8/C3D8 暴露百分级差异；同一平台上 parallel symbolic reuse + cpu_atomic 在 1-8 物理核内比 direct/no-symbolic 更快且 OS 峰值内存更低。

Figure archetype:
quantitative grid

Target journal/output:
Nature-family style technical figure package for a research report; editable SVG/PDF plus high-resolution PNG preview.

Backend:
Python only, using matplotlib for drawing, preview export, and QA.

Final size:
Double-column width, 183 mm class; each figure exported around 7.2 inch wide with readable 6-8 pt text.

Panel map:
a. Validation error heatmap and summary bars.
b. Probe displacement profiles for MATLAB self-solve versus Abaqus.
c. WindHub assembly time scaling and time decomposition.
d. Windows memory/time tradeoff and lifecycle peak comparison.

Evidence hierarchy:
Hero evidence: validation error split by element family and fastest symbolic reuse timing.
Validation evidence: per-probe displacement profiles and no-hard-threshold compare rows.
Controls/robustness: OS memory fallback fields, private bytes, and estimated lifecycle peak kept separate.

Statistics needed:
No inferential statistics; each row is a deterministic solver/benchmark run. No error bars are drawn because this package has no repeat distribution.

Source data needed:
The generated `source_data/validation_free_tip_deflection_summary.csv`, `source_data/validation_probe_errors.csv` and `source_data/performance_main_rows.csv` are clean figure source tables.

Image-integrity notes:
All panels are vector line/bar/heatmap graphics generated from CSV; no image adjustments or raster scientific images are used.

Reviewer risk:
Hex8/C3D8 free-tip deflection mismatch remains a real validation signal, not a pass/fail equivalence claim. Per-probe vector relative differences remain diagnostic. Windows memory uses peak working set fallback, not POSIX RSS.
