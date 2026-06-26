# Simple Assembly Quadrant Metrics

This package redraws the three platform-specific assembly comparison figures with a shared, sparse visual grammar:

- four fixed metric cards for Q1/Q2/Q3/Q4;
- only assembly time, memory, and speedup relative to Q1;
- no algorithm cartoons, CSR sketches, worker icons, dense matrices, arrows, or decorative gradients;
- consistent colors and layout across macOS, Linux Intel, and Windows AMD.

## Data Status

The source table is `source_data/assembly_quadrant_metric_rows.csv`.

- `†` marks placeholder estimates that must be replaced after a true `direct_no_symbolic_serial` retest.
- macOS memory is a pre-run lifecycle estimate, not OS peak capture.
- Linux memory is isolated process peak RSS.
- Windows memory is `GetProcessMemoryInfo` peak working set.
- The three platforms should not be compared by absolute memory value because the memory metrics are not identical.

## Outputs

Each platform is exported as SVG, PDF, PNG, and TIFF under `assets/`:

- `fig_macos_m4max_simple_assembly_metrics.*`
- `fig_linux_intel_simple_assembly_metrics.*`
- `fig_windows_amd_simple_assembly_metrics.*`

Regenerate with:

```bash
python3 parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/scripts/plot_simple_assembly_quadrant_metrics.py
```

## Figure Claim

Within each platform, the chart is intended to show that symbolic reuse improves over direct no-symbolic assembly, and that parallel symbolic reuse is the best tested path under the selected thread count. The current package is not final experimental evidence for Linux/Windows Q1 memory because those rows are placeholders.
