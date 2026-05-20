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

## Current Local Verification

On 2026-05-16 this package was compiled locally with:

```bash
/opt/homebrew/bin/tectonic mentor_next_steps_beamer.tex
```

The generated `mentor_next_steps_beamer.pdf` was written successfully. The TeX engine reported macOS font reproducibility / ToUnicode warnings, but no fatal errors.

This revision also includes new WindHub sparse-pattern assets generated from:

- `results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_python.png`
- `results/2026-05-16-mentor-action-items/sparse_pattern/windhub_physics_tet4_spy_matlab.png`
