# Linux Intel CalculiX Validation and CPU Assembly Figure Package

## Figure Contract

- Core conclusion: Linux Intel full-host results support a solver-correct, CPU-atomic-first assembly path: MATLAB and CalculiX probe displacements agree within 2.839e-07 relative difference, `cpu_atomic` gives the best 20-thread assembly time, and `parallel_symbolic_reuse` reduces total time with an explicit RSS cost.
- Figure archetype: quantitative grid with one overview composite plus focused evidence figures.
- Target journal/output: Nature-style double-column computational methods figures; primary SVG with editable text, PDF and 600 dpi TIFF for submission-style export, PNG for quick preview.
- Backend: Python only (`csv/json` + `numpy/matplotlib`; no R and no pandas dependency).
- Final size: overview 7.3 x 6.5 in; focused figures 7.2 in wide.
- Panel map: solver agreement, backend scaling, symbolic-mode tradeoff, memory lifecycle, and accuracy guardrails.
- Evidence hierarchy: correctness is shown first; performance ranking and scaling are the main Intel CPU evidence; memory fields and isolated RSS are separated as validation/control evidence.
- Statistics needed: deterministic benchmark/probe summaries only; no inferential statistics because the source benchmark sweep used `repeat=1`.
- Source data needed: validation manifests and probe CSVs, backend tradeoff CSV, isolated symbolic memory CSV.
- Image-integrity notes: all panels are generated line art from numeric CSV/JSON; no image manipulation or raster-only annotations.
- Reviewer risk: benchmark timings are single-run measurements, so the figures should be read as host evidence rather than population-level timing statistics.

## Why These Charts

1. **Overview composite**: gives a single manuscript-ready page linking solver correctness to the Intel performance and memory story, so the reader does not have to reconcile separate reports.
2. **Solver validation probe agreement**: validates the required `validation_export -> MATLAB solve -> CalculiX displacement CSV -> comparison report` chain before any performance claim is interpreted.
3. **Backend time scaling**: shows why Intel CPU assembly should be led by `cpu_atomic`, and makes the weaker scaling of `private_csr` and `lock_guard` visible instead of only reporting a 20-thread endpoint.
4. **Memory lifecycle**: separates CSR/AssemblyPlan persistent memory, symbolic temporary memory, direct/no-symbolic transient memory, backend extra memory, and measured isolated RSS, matching the required evidence vocabulary.
5. **Symbolic mode tradeoff**: compares total time and numeric time for symbolic reuse and direct no-symbolic paths, which explains why parallel symbolic reuse is useful but not free.
6. **Accuracy guardrails**: confirms the performance and memory comparisons did not trade away matrix-level numerical agreement, and places solver-level probe differences beside assembly-level `rel_l2`.

## Shared Parameters and Source Data

- Solver validation source: `results/validation-export/2026-05-23-linux-intel-calculix/validation_export_manifest.json`, `results/validation-export/2026-05-23-linux-intel-calculix/calculix_validation_manifest.json`, and each case-level `*_calculix_probe_compare.csv`.
- Solver validation parameters: `L=1`, `W=0.2`, `T=0.1`, `E=1`, `nu=0.3`, `x=0` fixed, total `z` load `-1` on `x=L`.
- Solver versions: MATLAB `recorded in manifest`; CalculiX `This is Version 2.23`.
- Performance source: `results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv`.
- Memory source: `results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`.
- Performance parameters: mesh `3d-WindTurbineHub`, `Tet4`, `228384` nodes, `1113684` elements, `685152` DOFs, `27502200` nonzeros, `kernel=linear_elastic_solid`, 1..20 threads on Intel Core Ultra 7 265KF.
- Derived source-data summaries written by this script: `results/2026-05-27-nature-figure-summary/source_data/validation_probe_rows.csv`, `results/2026-05-27-nature-figure-summary/source_data/validation_probe_summary.csv`, `results/2026-05-27-nature-figure-summary/source_data/backend_20_thread_summary.csv`, `results/2026-05-27-nature-figure-summary/source_data/symbolic_20_thread_memory_summary.csv`.

## Figure Files

- `fig00_overview_composite`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.tiff`
- `fig01_solver_validation_probe_agreement`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.tiff`
- `fig02_backend_time_scaling`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.tiff`
- `fig03_memory_lifecycle`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.tiff`
- `fig04_symbolic_mode_tradeoff`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.tiff`
- `fig05_accuracy_guardrails`: `pdf` `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.pdf`, `png` `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.png`, `svg` `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.svg`, `tiff` `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.tiff`

## Figure 00: Overview Composite

- Files: `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.svg`, `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig00_overview_composite.png`
- Data source: validation probe summaries, backend timing CSV, isolated symbolic memory CSV.
- Parameters: all panels use `linear_elastic_solid`; performance panels use the 3d-WindTurbineHub Tet4 mesh and 1..20 Intel physical-core sweep.
- Conclusion: the full evidence chain is internally consistent: the worst CalculiX-vs-MATLAB probe relative difference is 2.839e-07, the 20-thread `cpu_atomic` assembly time is 139.2 ms, and `parallel_symbolic_reuse` reaches 876.9 ms total time with 3.28 GiB measured RSS.
- Interpretation: the validation panel establishes that the exported `K/F/BC` solve agrees with an external open solver at selected physical probes; the backend panels show that atomic updates are faster than private CSR or lock guarding on this host; the memory panel prevents conflating estimated component bytes with measured isolated RSS.

## Figure 01: Solver Validation Probe Agreement

- Files: `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.svg`, `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig01_solver_validation_probe_agreement.png`
- Data source: `results/validation-export/2026-05-23-linux-intel-calculix/calculix_validation_manifest.json` plus four case-level `*_calculix_probe_compare.csv` files.
- Parameters: four cases are `cantilever_hex8_small`, `cantilever_hex8_medium`, `cantilever_tet4_small`, and `cantilever_tet4_medium`; fixed/load/material settings are the shared validation parameters above.
- Conclusion: all four validation cases report sub-micro relative probe differences, with worst relative difference 2.839e-07 and worst absolute difference 0.00414979.
- Interpretation: the largest absolute difference occurs on the larger meshes because displacements are larger in magnitude, while the relative differences remain close across Hex8/Tet4 and small/medium cases. This supports using CalculiX as the Linux open-source solver probe without fabricating commercial-solver evidence.

## Figure 02: Backend Time Scaling

- Files: `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.svg`, `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig02_backend_time_scaling.png`
- Data source: `results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv`.
- Parameters: algorithms `cpu_atomic`, `cpu_private_csr`, and `cpu_lock_guard`; thread range 1..20; `repeat=1`; `kernel=linear_elastic_solid`.
- Conclusion: at 20 threads, `cpu_atomic` is fastest (139.2 ms), ahead of `cpu_private_csr` (433.3 ms) and `cpu_lock_guard` (536.5 ms).
- Interpretation: `private_csr` starts with a strong 1-thread baseline but its per-thread private storage and merge overhead dominate at high thread counts; `lock_guard` avoids atomics but lock contention keeps it slower; `cpu_atomic` gives the best observed speed/memory tradeoff on this Intel host.

## Figure 03: Memory Lifecycle

- Files: `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.svg`, `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig03_memory_lifecycle.png`
- Data source: `results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv` and derived `results/2026-05-27-nature-figure-summary/source_data/symbolic_20_thread_memory_summary.csv`.
- Parameters: selected 20-thread comparison uses serial symbolic + atomic numeric, parallel symbolic reuse + atomic numeric, and direct no-symbolic mode.
- Conclusion: 20-thread measured isolated RSS is 2.51 GiB for serial symbolic + parallel numeric, 3.28 GiB for parallel symbolic reuse, and 3.75 GiB for direct no-symbolic.
- Interpretation: CSR and AssemblyPlan are persistent symbolic assets; parallel symbolic adds a smaller symbolic temporary allocation; direct no-symbolic avoids symbolic persistence but pays a large transient memory component. The isolated RSS markers are kept separate because allocator/runtime overhead makes measured resident memory different from simple byte-field sums.

## Figure 04: Symbolic Mode Tradeoff

- Files: `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.svg`, `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig04_symbolic_mode_tradeoff.png`
- Data source: `results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`.
- Parameters: modes `serial_symbolic_parallel_numeric`, `parallel_symbolic_parallel_numeric`, and `direct_no_symbolic_background`; atomic backend for symbolic reuse rows; no backend for direct no-symbolic rows.
- Conclusion: at 20 threads, parallel symbolic reuse (876.9 ms) is much faster than serial symbolic + parallel numeric (3705.8 ms) and direct no-symbolic (2494.7 ms).
- Interpretation: the speedup comes from parallelizing the symbolic construction/reuse path while preserving the sparse output structure; direct no-symbolic remains competitive only relative to serial symbolic at low thread counts, but its transient memory and total time are worse at the 20-thread endpoint.

## Figure 05: Accuracy Guardrails

- Files: `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.svg`, `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.pdf`, `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.tiff`, `results/2026-05-27-nature-figure-summary/figures/fig05_accuracy_guardrails.png`
- Data source: `results/2026-05-23-linux-intel-linear-elastic-full-host/windhub_backend_tradeoff.csv`, `results/2026-05-23-linux-intel-linear-elastic-full-host/isolated_symbolic_memory/isolated_symbolic_memory.csv`, and validation probe CSVs.
- Parameters: backend and symbolic panels use the same `linear_elastic_solid` WindHub benchmark; validation bar uses the four CalculiX probe cases.
- Conclusion: backend and symbolic matrix-level `rel_l2` stay around floating-point noise, with maxima 1.519e-16 and 1.618e-16; solver probe relative differences are larger but still below 2.839e-07.
- Interpretation: the assembly implementation variants produce numerically equivalent matrices relative to their references, while the solver probe comparison includes independent solver I/O and displacement extraction effects. Keeping both scales visible prevents overclaiming bitwise equality at the solver level.
