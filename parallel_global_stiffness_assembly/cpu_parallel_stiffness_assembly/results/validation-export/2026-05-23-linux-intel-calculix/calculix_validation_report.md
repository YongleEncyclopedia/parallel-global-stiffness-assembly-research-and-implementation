# Linux Intel CalculiX Validation Report

## Environment

- Platform: `Linux 6.17.0-29-generic x86_64`
- MATLAB: `26.1.0.3251617 (R2026a) Update 2`
- CalculiX: `This is Version 2.23`
- Material: `E=1.0, nu=0.3`
- Geometry/load: `L=1.0, W=0.2, T=0.1`, x=0 fixed, x=L total z-load `-1.0`.
- Threshold policy: no hard pass/fail threshold; report probe differences.

## Commands

```bash
python3 results/validation-export/2026-05-23-linux-intel-calculix/run_calculix_validation.py --root results/validation-export/2026-05-23-linux-intel-calculix --ccx-bin ccx
(cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/calculix && ccx -i cantilever_hex8_small)
(cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/calculix && ccx -i cantilever_tet4_small)
(cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/calculix && ccx -i cantilever_hex8_medium)
(cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/calculix && ccx -i cantilever_tet4_medium)
```

## Probe Summary

| case | element | nodes | elements | max probe | max abs diff | max rel diff | status |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| cantilever_hex8_small | hex8 | 27 | 8 | free_tip_center | 0.000221609 | 1.18745e-07 | reported_no_hard_threshold |
| cantilever_tet4_small | tet4 | 27 | 48 | midspan_center | 3.10123e-05 | 1.2476e-07 | reported_no_hard_threshold |
| cantilever_hex8_medium | hex8 | 325 | 192 | free_tip_center | 0.00414979 | 2.69885e-07 | reported_no_hard_threshold |
| cantilever_tet4_medium | tet4 | 325 | 1152 | free_tip_center | 0.00285233 | 2.83942e-07 | reported_no_hard_threshold |

## Outputs

- `cantilever_hex8_small`: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/calculix/cantilever_hex8_small_calculix_displacements.csv`, `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_small/cantilever_hex8_small_calculix_probe_compare.md`
- `cantilever_tet4_small`: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/calculix/cantilever_tet4_small_calculix_displacements.csv`, `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_small/cantilever_tet4_small_calculix_probe_compare.md`
- `cantilever_hex8_medium`: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/calculix/cantilever_hex8_medium_calculix_displacements.csv`, `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_hex8_medium/cantilever_hex8_medium_calculix_probe_compare.md`
- `cantilever_tet4_medium`: `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/calculix/cantilever_tet4_medium_calculix_displacements.csv`, `/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/validation-export/2026-05-23-linux-intel-calculix/cantilever_tet4_medium/cantilever_tet4_medium_calculix_probe_compare.md`
