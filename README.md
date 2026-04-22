# CPU Parallel Global Stiffness Assembly Research and Implementation

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
    └── cpu_parallel_stiffness_assembly/
```

## What Is Included

- the updated CPU-focused requirements document
- cross-platform constraints for macOS and Windows
- a curated copy of the existing `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly` codebase
- the large engineering mesh `examples/3d-WindTurbineHub.inp` tracked through Git LFS
- only the files that are useful for continued development

## Large-File Workflow

This repository uses Git LFS for the large engineering input:

- `examples/3d-WindTurbineHub.inp`

After cloning, install and initialize Git LFS once per machine, then pull the large objects:

```bash
brew install git-lfs
git lfs install
git lfs pull
```

On Windows, install Git LFS and run `git lfs install` from Git Bash before opening the project.

## Engineering Case Standard Run Flow

Use this as the canonical workflow for the real engineering case. Do not switch to ad hoc external paths when the repository copy exists.

```bash
git lfs pull

cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

/opt/homebrew/bin/cmake -S . -B build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON

/opt/homebrew/bin/cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
```

First validate the repository engineering mesh with the simplified kernel:

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel simplified --warmup 0 --repeat 1 --check \
  --csv results/windhub_simplified.csv
```

Then run the engineering kernel:

```bash
./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --algo serial,atomic,coloring,row_owner \
  --threads-list 1,2,4,8,14 \
  --kernel physics_tet4 --warmup 0 --repeat 1 --check \
  --csv results/windhub_physics_tet4.csv
```

If the file is still an LFS pointer instead of the real mesh, run `git lfs pull` again before debugging the benchmark.

## What Is Intentionally Excluded

- build products, editor caches, binaries, and one-off artifacts
- PDF literature bundles and compressed archives

## Current Position

The repository is intentionally not a polished release package. It is a clean handoff point for continuing implementation from the requirements and the existing codebase snapshot.
