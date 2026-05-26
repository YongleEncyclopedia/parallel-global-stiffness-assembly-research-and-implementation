# 2026-05-22-weekly-meeting-beamer 报告包目录

## 用途

保存对应日期的 Beamer、README、asset manifest、演练稿或问答材料。

## 存放内容

- 直接文件：`README.md`、`asset_manifest.md`、`generate_weekly_meeting_figures.py`、`mentor_qna_rehearsal.md`、`numeric_assembly_algorithm_rehearsal.md`、`weekly_meeting_20260522_beamer.pdf`、`weekly_meeting_20260522_beamer.tex`
- 子目录：`assets/`

## 不应存放

后续新实验的原始主数据。

## 维护提示

报告包是时间快照，修改时保留 provenance。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports](../README.md)
- 子目录：[`assets/`](assets/README.md)


## 原有说明

以下保留本文件原有的详细说明；本节之前的内容是统一补充的中文目录维护说明。

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
- RCM `K(p,p)` and exact-window assets are visualization-only evidence: they explain numbering and display scale, but do not alter benchmark assembly or correctness baselines.

## Meeting Rehearsal

- `mentor_qna_rehearsal.md` contains mentor-facing self Q&A for meeting practice.
- `numeric_assembly_algorithm_rehearsal.md` explains how numeric assembly reuses CSR/scatter and how the five main parallel backends handle write conflicts.
- The Q&A keeps the deck's first-person Chinese speaking style and separates confirmed evidence from future cross-checks.
- The normal Beamer PDF includes only a one-slide Q&A preparation entry so the main report does not become an appendix-heavy deck.

## Build

From this directory:

```bash
/opt/homebrew/bin/tectonic weekly_meeting_20260522_beamer.tex
```

The normal PDF hides speaker notes. Notes are kept in the `.tex` source for meeting preparation.
