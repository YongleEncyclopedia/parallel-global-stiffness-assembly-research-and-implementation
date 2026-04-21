# Repository Scope and Curation Notes

## Purpose

This repository is intentionally curated for continued CPU project work.

It is not a full mirror of the original working directory.

## Included on Purpose

- the updated CPU-focused requirements
- platform migration guidance
- a curated `parallel_global_stiffness_assembly` folder
- the existing `parallel_stiffness_assembly` source tree for reference and continuation

## Excluded on Purpose

- presentation decks
- full literature archives
- compressed backups
- build directories
- editor metadata
- raw engineering inputs that are too large or not suitable for a public repo

## Why the Curated `parallel_global_stiffness_assembly` Folder Exists

The original project history contains useful structure and code, especially:

- the existing benchmark framework
- the mesh, CSR, and assembler abstractions
- the current CPU serial baseline
- the source tree that future implementation can extend

The folder is preserved to keep that continuity, but only as a cleaned subset.

## Source of Truth

For future implementation work, use this priority order:

1. `docs/requirements/cpu-parallel-stiffness-assembly-design.md`
2. `docs/platform/cross-platform-strategy.md`
3. `parallel_global_stiffness_assembly/parallel_stiffness_assembly/`

If the historical code and the updated requirement document conflict, the requirement document should win.
