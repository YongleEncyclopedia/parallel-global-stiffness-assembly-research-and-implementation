# Mentor Next Steps Beamer Package

This directory contains a Chinese-first LaTeX beamer source package for the mentor next-step discussion on parallel global stiffness matrix assembly.

## Files

- `mentor_next_steps_beamer.tex`: main beamer source.
- `assets/`: copied PNG figures from existing benchmark result directories.
- `asset_manifest.md`: source path and slide purpose for each copied figure.

## Compile

Use XeLaTeX because the deck uses `ctexbeamer` for Chinese text:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error mentor_next_steps_beamer.tex
```

If `latexmk` is not available, compile with XeLaTeX directly:

```bash
xelatex -interaction=nonstopmode -halt-on-error mentor_next_steps_beamer.tex
xelatex -interaction=nonstopmode -halt-on-error mentor_next_steps_beamer.tex
```

## Current Local Verification Boundary

On the current machine, `latexmk`, `xelatex`, and `pdflatex` are not installed. This package was therefore verified by checking:

- all `\includegraphics{...}` references point to files under `assets/`;
- no absolute image paths are used inside the `.tex`;
- every original source path listed in `asset_manifest.md` exists in the repository;
- the deck uses `ctexbeamer`, so the intended compile path is XeLaTeX.

No benchmark was rerun and no new data figure was generated for this package.
