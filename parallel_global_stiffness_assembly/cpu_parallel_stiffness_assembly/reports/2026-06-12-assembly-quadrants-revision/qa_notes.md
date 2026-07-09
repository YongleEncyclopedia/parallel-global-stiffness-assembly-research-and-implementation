# 四象限组装图 revision QA

## Figure contract

- Core conclusion: symbolic + numeric assembly is faster than direct/no-symbolic sorting, and parallel symbolic reuse is the best of the four routes.
- Archetype: schematic-led composite + quantitative grid.
- Source data: `source_data/quadrant_selected_rows.csv` copied from the existing curated quadrant package.

## Numeric checks

- Serial symbolic vs serial direct: `1.68x`.
- Parallel symbolic vs serial symbolic: `4.67x`.
- Parallel symbolic vs parallel direct: `2.52x`.
- Parallel symbolic vs serial direct: `7.85x`.

## Runtime availability

- Python/matplotlib: available in this environment.
- Rscript: `not found`.
- MATLAB: `/Applications/MATLAB_R2026a.app/bin/matlab`.

## Render results

- Python: rendered successfully with 9 planned files.
  - Main PNG: `4800 x 2700`.
  - Standalone schematic PNGs: `2400 x 1080`.
  - SVG text nodes: main `92`, direct schematic `10`, two-stage schematic `9`.
- MATLAB: rendered successfully with 9 planned files.
  - Main PNG: `4800 x 2700`.
  - Standalone schematic PNGs: `3000 x 1350`.
  - SVG text nodes: `0`; MATLAB exported text as vector paths, so use this branch as visual reference rather than editable-text source.
- R: not rendered because `Rscript` is not installed on this machine (`zsh: command not found: Rscript`). The R script is present and uses the same CSV, metrics assertions, and output names.

## Notes

- The Python folder also contains no-suffix files from the first dry run before the backend suffix naming bug was fixed. The planned Python outputs are the files with `.python.` in the name.
- Old `2026-05-27-assembly-quadrants` assets were not overwritten.

## Expected outputs

- `python/assembly_quadrants_revised.python.svg`
- `python/assembly_quadrants_revised.python.pdf`
- `python/assembly_quadrants_revised.python.png`
- `python/direct_assembly_schematic.python.svg`
- `python/direct_assembly_schematic.python.pdf`
- `python/direct_assembly_schematic.python.png`
- `python/two_stage_assembly_schematic.python.svg`
- `python/two_stage_assembly_schematic.python.pdf`
- `python/two_stage_assembly_schematic.python.png`
- `r/assembly_quadrants_revised.r.svg`
- `r/assembly_quadrants_revised.r.pdf`
- `r/assembly_quadrants_revised.r.png`
- `r/direct_assembly_schematic.r.svg`
- `r/direct_assembly_schematic.r.pdf`
- `r/direct_assembly_schematic.r.png`
- `r/two_stage_assembly_schematic.r.svg`
- `r/two_stage_assembly_schematic.r.pdf`
- `r/two_stage_assembly_schematic.r.png`
- `matlab/assembly_quadrants_revised.matlab.svg`
- `matlab/assembly_quadrants_revised.matlab.pdf`
- `matlab/assembly_quadrants_revised.matlab.png`
- `matlab/direct_assembly_schematic.matlab.svg`
- `matlab/direct_assembly_schematic.matlab.pdf`
- `matlab/direct_assembly_schematic.matlab.png`
- `matlab/two_stage_assembly_schematic.matlab.svg`
- `matlab/two_stage_assembly_schematic.matlab.pdf`
- `matlab/two_stage_assembly_schematic.matlab.png`
- `source_data/quadrant_selected_rows.csv`
- `source_manifest.json`
- `qa_notes.md`
