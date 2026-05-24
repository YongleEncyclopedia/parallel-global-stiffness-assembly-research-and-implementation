# MATLAB vs CalculiX Probe Displacement Comparison

- MATLAB source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/cantilever_tet4_medium_matlab_displacements.csv`
- CalculiX source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/calculix/cantilever_tet4_medium_calculix_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max probe difference: node `168` / CalculiX node `169`, probe `free_tip_center`, abs `0.0028523270476277637`, rel `2.8394215747600078e-07`.

| node | CalculiX node | probe | abs diff | rel diff | status |
| ---: | ---: | --- | ---: | ---: | --- |
| 156 | 157 | root_center | 0 | 0 | reported_no_hard_threshold |
| 162 | 163 | midspan_center | 0.00029857611126836371 | 9.5303689178256417e-08 | reported_no_hard_threshold |
| 168 | 169 | free_tip_center | 0.0028523270476277637 | 2.8394215747600078e-07 | reported_no_hard_threshold |
