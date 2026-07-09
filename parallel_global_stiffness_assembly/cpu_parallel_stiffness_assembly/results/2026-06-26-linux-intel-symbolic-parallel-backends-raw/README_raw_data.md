# Linux Intel symbolic-parallel backend raw data

This package reruns the original isolated symbolic-memory experiment style used by the monthly-report figure.

Measurement scope:
- Baseline: serial symbolic assembly + serial numeric assembly.
- Parallel rows: parallel symbolic assembly + parallel numeric assembly.
- Direct no-symbolic assembly is intentionally excluded.
- Five numeric backends are included: atomic, private_csr, lock_guard, coloring, row_owner.
- Thread range: 1..20.
- Repetition policy: one quick isolated run per row.
- Memory: isolated subprocess peak RSS.
- Timing: symbolic_total_ms + numeric_ms = amortized_total_ms.

Linux side only generates raw data. Plotting is done later on the Mac side.
