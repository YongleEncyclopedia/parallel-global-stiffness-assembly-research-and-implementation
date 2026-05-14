# Cross-Platform Strategy

## Target Platforms

The project is expected to evolve in this order:

1. `macOS` on `Mac Studio` for first-pass validation and design-driven implementation
2. `Windows` on `Intel U7 265KF` for later migration and benchmark reproduction

This means the implementation should be treated as a cross-platform CPU project from the beginning, not as a single-machine prototype.

## Practical Constraints

- `macOS Apple Silicon` and `Windows Intel x86_64` have different CPU architectures
- compiler stacks will differ: `AppleClang/Clang` on macOS and `MSVC` on Windows
- `OpenMP` availability and setup differ by platform
- path handling, shell behavior, and line endings differ

## Design Rules

- Prefer `CMake` as the main build entry
- Prefer standard `C++17`
- Keep platform-specific code isolated
- Avoid hard-coding shell-only workflows
- Prefer Python for small automation tasks when reasonable
- Record compiler, OS, CPU architecture, and thread backend in benchmark output

## Immediate Development Bias

During the first implementation phase:

- prioritize correctness and clean abstractions on macOS
- do not introduce shortcuts that would block Windows migration
- treat platform-specific workarounds as explicit compatibility layers, not hidden assumptions

## Expected Follow-Up

After the initial macOS validation:

- confirm the minimum working CMake flow on Windows
- reproduce the same benchmark inputs and output fields
- compare algorithm behavior separately from platform effects

## Benchmark Schema Rule

Cross-platform benchmark results must use the versioned package schema documented in:

- [cross-platform-benchmark-schema.md](cross-platform-benchmark-schema.md)

Before testing a new CPU platform, run `scripts/inspect_cpu_platform.py` and explicitly state whether the CPU has homogeneous cores or distinct performance/efficiency core classes. If the platform can isolate P/E core resources reliably, collect `full_host`, `performance_core_only`, and `efficiency_core_only`; otherwise mark unsupported profiles as `not_applicable` or `missing` with evidence.
