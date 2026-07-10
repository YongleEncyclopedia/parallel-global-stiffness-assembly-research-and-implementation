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

## 历史 tar 清理来源

Issue #28 删除了源码树根部的冗余归档 `intel_backend_thread_sweep_isolated_raw_2026-06-26.tar.gz`。删除前记录：

- tar SHA256：`0b04b5c4000c23f7805085e8a3bd451d5032e3e3081430ccc01aab1fe5ecd8fb`
- 比较结论：清理前基线 `eca50af` 中，归档文件集合与展开目录完全相同，没有归档独有内容。
- 换行说明：`windhub_backend_thread_sweep_intel.csv`、`windhub_backend_thread_sweep_intel_isolated_repeats.csv`、`windhub_backend_thread_sweep_intel_isolated_summary.csv` 仅有 CRLF/LF 差异；统一为 LF 后逐字节一致。其余成员原始字节一致。
- 成员：`README_raw_data.md`
- 成员：`platform_info.txt`
- 成员：`run_commands.sh`
- 成员：`windhub_backend_thread_sweep_intel.csv`
- 成员：`windhub_backend_thread_sweep_intel.json`
- 成员：`windhub_backend_thread_sweep_intel.md`
- 成员：`windhub_backend_thread_sweep_intel_isolated.json`
- 成员：`windhub_backend_thread_sweep_intel_isolated.md`
- 成员：`windhub_backend_thread_sweep_intel_isolated_repeats.csv`
- 成员：`windhub_backend_thread_sweep_intel_isolated_summary.csv`

因此除本节新增的审计说明外，本目录在规范化文本换行后保留了该 tar 的完整展开内容。

机器可读逐成员哈希见 [`../2026-06-26-archive-provenance.tsv`](../2026-06-26-archive-provenance.tsv)；其中 `working_tree_sha256` 记录清理前基线 `eca50af`。
