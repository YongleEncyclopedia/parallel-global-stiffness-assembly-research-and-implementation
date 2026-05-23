# Monthly Intern Report Source Deck Extracts

This directory stores AI-readable extracts of monthly intern-report slide decks that are directly relevant to the current CPU parallel global stiffness assembly project.

## Repository Existence Check

A repository search found only partial references before this directory was added:

- `docs/requirements/cpu-parallel-stiffness-assembly-design.md` mentioned the 2026-01 monthly report as historical background.
- 2026-04 benchmark/result assets existed under `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/`, but not the detailed PPT narrative.
- No raw PPTX copy or slide-level AI-readable extraction for the two requested Jiang Haohua monthly reports was present in the repository.

The raw PPTX files remain outside this repository to respect the repository scope rule that excludes one-off slide binaries. The durable project context is kept here as Markdown and JSON.

## Extracted Decks

| Period | AI-readable file | Slides | Notes slides | Media refs | Source path |
| --- | --- | ---: | ---: | ---: | --- |
| 2026-01 | [`2026-01-intern-report-jiang-haohua.md`](2026-01-intern-report-jiang-haohua.md) | 26 | 20 | 26 | `/Users/haohua_jiang/Documents/Intern_Peking University_supu/2026年01月实习生汇报/2026年01月实习生汇报-江浩华.pptx` |
| 2026-04 | [`2026-04-intern-report-jiang-haohua-version5.md`](2026-04-intern-report-jiang-haohua-version5.md) | 13 | 13 | 11 | `/Users/haohua_jiang/Documents/Intern_Peking University_supu/2026年04月实习生汇报/2026年04月实习生汇报-江浩华_version5.pptx` |

## File Format

- `*.md`: human- and AI-readable narrative spine, reuse boundary, slide index, exact visible text, speaker notes, embedded-media metadata, and best-effort OCR snippets.
- `manifest.json`: machine-readable extraction with one object per deck and one record per slide.
- `extract_monthly_report_pptx.py`: repeatable extractor for these source decks.

## Regeneration

Run from the repository root:

```bash
"/Users/haohua_jiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" \
  docs/context/monthly-intern-reports/extract_monthly_report_pptx.py
```

The extractor uses Office Open XML directly and does not require PowerPoint or LibreOffice. If `tesseract` is available, it also performs best-effort English OCR on embedded images.

## Use In Current Project

- Use the 2026-01 deck to understand the original problem framing and algorithm-family taxonomy.
- Use the 2026-04 deck to understand the CPU-first pivot, real engineering mesh result narrative, and report-time interpretation of correctness, efficiency, and memory evidence.
- Use current `results/`, `docs/requirements/`, and `reports/` files for up-to-date benchmark facts.
