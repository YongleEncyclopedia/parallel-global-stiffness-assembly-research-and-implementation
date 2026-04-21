# Examples and External Inputs

## Public Repository Policy

Large engineering inputs are not stored directly in this repository.

In particular:

- `3d-WindTurbineHub.inp` is treated as an external local input

## Expected Local Workflow

When implementing and testing locally:

1. keep the engineering `.inp` file outside the public repository
2. point the parser or benchmark tool to the local file path
3. record only derived benchmark results or small synthetic examples in the repository

## Why

This keeps the public repository:

- lightweight
- easier to clone
- easier to reuse for planning and code generation
- safer for sharing while still preserving the intended engineering workflow
