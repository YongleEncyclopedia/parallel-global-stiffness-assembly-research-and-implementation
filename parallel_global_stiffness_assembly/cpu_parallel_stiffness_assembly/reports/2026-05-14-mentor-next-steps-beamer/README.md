# 2026-05-14-mentor-next-steps-beamer 报告包目录

## 用途

保存对应日期的 Beamer、README、asset manifest、演练稿或问答材料。

## 存放内容

- 直接文件：`README.md`、`asset_manifest.md`、`mentor_next_steps_beamer.pdf`、`mentor_next_steps_beamer.tex`
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
