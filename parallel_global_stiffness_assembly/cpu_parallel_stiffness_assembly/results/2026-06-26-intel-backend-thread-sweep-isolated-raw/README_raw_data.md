# Intel Backend Thread Sweep Raw Data

This directory contains the corrected Intel platform raw benchmark data for `3d-WindTurbineHub.inp` using the Tet4 physical stiffness kernel (`physics_tet4`). This run supersedes the earlier non-isolated run that mixed algorithms in one process and could not attribute memory correctly.

The thread range is the complete `1..20`. Downstream plotting may filter to any fixed thread count, but the raw package keeps the full sweep.

No plotting was performed in this run. No plotting script was modified. This package only contains raw benchmark data, platform metadata, commands, and Markdown/CSV/JSON summaries.

## Measurement Semantics

Each runnable algorithm/thread/repeat is measured in a fresh subprocess. The measured wall-time fields are:

- `symbolic_ms`: CSR symbolic construction + scatter/assembly plan construction + backend prepare time.
- `numeric_ms`: numerical global stiffness assembly time for that isolated algorithm/thread process.
- `symbolic_numeric_total_ms`: `symbolic_ms + numeric_ms`.
- `isolated_peak_rss_mb`: peak RSS of that isolated measurement subprocess, not a shared multi-algorithm process.

Correctness checks are run separately and recorded in the summary status fields. The correctness subprocess is not used as the memory measurement row.

`cpu_serial` is treated as the single-thread baseline. `cpu_serial` with threads `2..20` is retained as explicit `SKIP / NOT_APPLICABLE` rows rather than being silently omitted.

The default downstream speedup baseline should be `cpu_serial` at 1 thread using `symbolic_numeric_total_ms`.

## Algorithms Included

- `cpu_serial`
- `cpu_atomic`
- `cpu_private_csr`
- `cpu_lock_guard`
- `cpu_graph_coloring`
- `cpu_row_owner`

Direct assembly outputs such as `direct_no_symbolic_*` are not present. `cpu_coo_sort_reduce` is not included.

## Files

- `windhub_backend_thread_sweep_intel.csv`: compatibility raw CSV alias; repeat-level isolated measurements.
- `windhub_backend_thread_sweep_intel.json`: compatibility JSON alias; includes repeat and summary records.
- `windhub_backend_thread_sweep_intel.md`: compatibility Markdown summary alias.
- `windhub_backend_thread_sweep_intel_isolated_repeats.csv`: repeat-level raw isolated measurements.
- `windhub_backend_thread_sweep_intel_isolated_summary.csv`: one row per algorithm/thread status summary.
- `windhub_backend_thread_sweep_intel_isolated.json`: JSON package with repeat records, summary records, and commands.
- `windhub_backend_thread_sweep_intel_isolated.md`: Markdown summary table.
- `platform_info.txt`: CPU/OS/compiler/OpenMP/git/mesh metadata.
- `run_commands.sh`: commands used for build, validation, benchmark, aliases, and tar packaging.
- `README_raw_data.md`: this note.
