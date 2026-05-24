# MATLAB vs CalculiX Probe Displacement Comparison

- MATLAB source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/cantilever_hex8_medium_matlab_displacements.csv`
- CalculiX source: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/calculix/cantilever_hex8_medium_calculix_displacements.csv`
- Threshold policy: no hard pass/fail threshold; report differences and interpretation status.
- Max probe difference: node `168` / CalculiX node `169`, probe `free_tip_center`, abs `0.0041497915462973232`, rel `2.6988530574971226e-07`.

| node | CalculiX node | probe | abs diff | rel diff | status |
| ---: | ---: | --- | ---: | ---: | --- |
| 156 | 157 | root_center | 0 | 0 | reported_no_hard_threshold |
| 162 | 163 | midspan_center | 0.00010315626059507471 | 2.1572219385268731e-08 | reported_no_hard_threshold |
| 168 | 169 | free_tip_center | 0.0041497915462973232 | 2.6988530574971226e-07 | reported_no_hard_threshold |
