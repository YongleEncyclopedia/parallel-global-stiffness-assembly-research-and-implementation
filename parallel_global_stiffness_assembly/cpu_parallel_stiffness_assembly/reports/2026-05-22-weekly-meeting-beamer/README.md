# 2026-05-22 Weekly Meeting Beamer

This folder contains the Beamer deck for the 2026-05-22 weekly meeting.

## Purpose

The deck answers three mentor-facing questions:

1. Whether symbolic assembly is parallelized and whether it is worth parallelizing under fixed numeric backend conditions.
2. Whether correctness is verified on each test run, with the current C++ `cpu_serial` matrix as the reference.
3. How symbolic+numeric memory differs from direct/no-symbolic memory, especially the previously reported 2.39 GiB direct transient buffer.

## Evidence Policy

- No heavy benchmark was rerun for this deck.
- Reused evidence comes from merged result packages under `results/`.
- Derived figures are generated only from existing CSV files by `generate_weekly_meeting_figures.py`.
- MATLAB sparse-pattern figures are used as visualization cross-checks, not as an external correct matrix.
- Python and MATLAB sparse-pattern figures use the same matrix display convention: row index downward, column index rightward, and black nonzero marks.
- CSR triplet-window assets are small excerpts from a fresh `stiffness_pattern_export` run; full WindHub pattern CSV/MTX files are not stored in this report folder.

## Meeting Rehearsal

- `mentor_qna_rehearsal.md` contains mentor-facing self Q&A for meeting practice.
- The Q&A keeps the deck's first-person Chinese speaking style and separates confirmed evidence from future cross-checks.
- The normal Beamer PDF includes only a one-slide Q&A preparation entry so the main report does not become an appendix-heavy deck.

## Build

From this directory:

```bash
/opt/homebrew/bin/tectonic weekly_meeting_20260522_beamer.tex
```

The normal PDF hides speaker notes. Notes are kept in the `.tex` source for meeting preparation.
