# Parallel Global Stiffness Assembly Research and Implementation

This repository is a document-first public workspace for the next stage of the project:

- shift the focus from GPU-first exploration to CPU parallel assembly research
- validate first on `macOS + Mac Studio`
- keep the codebase ready for later migration to `Windows + Intel U7 265KF`
- give a clean starting point for future implementation work

## Start Here

The primary project document is:

- [CPU parallel stiffness assembly design](docs/requirements/cpu-parallel-stiffness-assembly-design.md)

Read these next:

- [Cross-platform strategy](docs/platform/cross-platform-strategy.md)
- [Repository scope and curation notes](docs/context/repository-scope.md)
- [Implementation planning entry](docs/plans/README.md)
- [External example and engineering input policy](examples/README.md)

## Repository Layout

```text
.
├── docs/
│   ├── context/
│   ├── plans/
│   ├── platform/
│   └── requirements/
├── examples/
└── parallel_global_stiffness_assembly/
    └── parallel_stiffness_assembly/
```

## What Is Included

- the updated CPU-focused requirements document
- cross-platform constraints for macOS and Windows
- a curated copy of the existing `parallel_global_stiffness_assembly/parallel_stiffness_assembly` codebase
- only the files that are useful for continued development

## What Is Intentionally Excluded

- large raw engineering inputs such as `3d-WindTurbineHub.inp`
- build products, editor caches, binaries, and one-off artifacts
- PDF literature bundles and compressed archives

## Current Position

The repository is intentionally not a polished release package. It is a clean handoff point for continuing implementation from the requirements and the existing codebase snapshot.
