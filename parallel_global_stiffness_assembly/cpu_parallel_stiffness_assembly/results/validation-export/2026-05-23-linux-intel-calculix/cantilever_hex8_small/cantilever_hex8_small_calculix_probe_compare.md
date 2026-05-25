# MATLAB vs CalculiX Probe Displacement Comparison

- MATLAB source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/cantilever_hex8_small_matlab_displacements.csv`
- CalculiX source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/calculix/cantilever_hex8_small_calculix_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max probe difference: node `14` / CalculiX node `15`, probe `free_tip_center`, abs `0.00022160861863085673`, rel `1.1874483586193381e-07`.

| node | CalculiX node | probe | abs diff | rel diff | status |
| ---: | ---: | --- | ---: | ---: | --- |
| 12 | 13 | root_center | 0 | 0 | reported_no_hard_threshold |
| 13 | 14 | midspan_center | 2.2271299826577669e-05 | 3.7942643724850059e-08 | reported_no_hard_threshold |
| 14 | 15 | free_tip_center | 0.00022160861863085673 | 1.1874483586193381e-07 | reported_no_hard_threshold |
