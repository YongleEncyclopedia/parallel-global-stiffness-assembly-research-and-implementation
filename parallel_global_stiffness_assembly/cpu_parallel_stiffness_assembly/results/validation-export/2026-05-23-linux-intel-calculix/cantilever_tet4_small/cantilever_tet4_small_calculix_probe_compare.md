# MATLAB vs CalculiX Probe Displacement Comparison

- MATLAB source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/cantilever_tet4_small_matlab_displacements.csv`
- CalculiX source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/calculix/cantilever_tet4_small_calculix_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max probe difference: node `13` / CalculiX node `14`, probe `midspan_center`, abs `3.1012267949597027e-05`, rel `1.2476010405767169e-07`.

| node | CalculiX node | probe | abs diff | rel diff | status |
| ---: | ---: | --- | ---: | ---: | --- |
| 12 | 13 | root_center | 0 | 0 | reported_no_hard_threshold |
| 13 | 14 | midspan_center | 3.1012267949597027e-05 | 1.2476010405767169e-07 | reported_no_hard_threshold |
| 14 | 15 | free_tip_center | 1.8578956364620351e-05 | 2.4642069949935336e-08 | reported_no_hard_threshold |
