# Project Long-Term Beamer

This directory contains the long-term living Beamer deck for the CPU parallel global stiffness assembly project.

It is intentionally separate from date-stamped short-term Beamer packages such as `../2026-05-14-mentor-next-steps-beamer/`.

## Purpose

- Personal project handbook for background knowledge, implementation structure, benchmark evidence, and progress tracking.
- Newcomer-friendly explanation of concepts that appeared in mentor discussions, especially symbolic/numeric assembly, CSR, scatter plan, `section/closure`, P/E-core profiles, and benchmark evidence.
- Stable knowledge sink: after each short-term meeting deck, only durable conclusions should be merged here.

## Files

- `project_long_term_beamer.tex`: main Beamer entry.
- `sections/*.tex`: modular chapter files.
- `source_index.md`: source manifest for local docs, result figures, and external references.

## Asset Policy

This long-term deck directly references figures under `../../results/...`.

This is different from short-term packages that copy selected figures into an `assets/` directory. The reason is that this deck is a living project handbook: if result figures are updated in place, the long-term Beamer should track them after the corresponding text and source index are reviewed.

The tradeoff is that moving or deleting result directories can break compilation. Run the path checks below after edits.

## Compile

Preferred full TeX route with Chinese Beamer support:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error project_long_term_beamer.tex
```

If `latexmk` is unavailable:

```bash
xelatex -interaction=nonstopmode -halt-on-error project_long_term_beamer.tex
xelatex -interaction=nonstopmode -halt-on-error project_long_term_beamer.tex
```

On this machine, `/opt/homebrew/bin/tectonic` is available and can be tried:

```bash
/opt/homebrew/bin/tectonic project_long_term_beamer.tex
```

2026-05-16 local verification: `tectonic project_long_term_beamer.tex` completed and wrote `project_long_term_beamer.pdf`. The TeX engine reported macOS font reproducibility / ToUnicode warnings, but no fatal errors.

## Maintenance Checks

Run from this directory:

```bash
rg '\\input\\{|\\resultfig\\{|\\includegraphics\\{' project_long_term_beamer.tex sections
```

Run from this directory to list all direct result figure references:

```bash
perl -ne 'while(/\\resultfig(?:\[[^\]]+\])?\{([^}]+)\}/g){print "$1\n"}' sections/*.tex
```

Any new figure, table, or external reference used in slides should also be recorded in `source_index.md`.

## Language

The deck uses Chinese explanations with English technical terms, code identifiers, paths, and source titles preserved.
