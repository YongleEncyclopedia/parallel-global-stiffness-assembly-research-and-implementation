# Examples and External Inputs

## Public Repository Policy

Small benchmark examples are stored directly in this repository.
The large engineering input is stored through Git LFS.

In particular:

- `3d-WindTurbineHub.inp` is versioned as `examples/3d-WindTurbineHub.inp`
- collaborators must install Git LFS before cloning or pulling large-file updates

## Expected Local Workflow

When implementing and testing locally:

1. install Git LFS once on the workstation
2. clone the repository normally
3. run `git lfs pull` to materialize the large engineering input locally
4. keep only selected benchmark-sized engineering inputs in LFS and avoid adding ad hoc raw dumps

## Why

This keeps the public repository:

- lightweight
- easier to clone
- easier to reuse for planning and code generation
- safer for sharing while still preserving the intended engineering workflow
- able to retain one canonical engineering input in both local and remote copies
