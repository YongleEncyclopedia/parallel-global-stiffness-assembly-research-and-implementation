# CSC3 Symmetric Assembly Demo

> **INTERNAL EVALUATION ONLY.** Distribution policy remains unresolved and is
> tracked by [Issue #37](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/37).

This standalone C++17 source demo defines the version `0.2.0` public surface
for assembling the upper triangle of a symmetric matrix in CSC3 form. Its only
production candidate is the combination of deterministic OpenMP parallel
symbolic construction and OpenMP atomic numeric assembly:

- `build_symbolic_parallel(...)` canonicalizes the topology and constructs the
  CSC3 pattern and scatter plan deterministically for the same valid input,
  independent of the requested OpenMP thread count.
- `assemble_numeric_atomic(...)` performs race-free atomic accumulation from a
  complete batch of dense element matrices. Floating-point addition order can
  vary with OpenMP scheduling, so numeric values are not promised to be
  bitwise identical across executions.

Serial code in tests or future benchmarks is reference material only. There is
no serial fallback and `CSC3_DEMO_REQUIRE_OPENMP=OFF` intentionally fails at
configure time. Requesting `thread_count == 1` still executes the supported
OpenMP path; it does not select a separate serial implementation.

## Matrix and input contract

`Csc3Matrix` stores only entries in the upper triangle, so every stored pair
satisfies $0 \le r \le c < n$. All three arrays are zero-based:

- `column_offsets` has length $n+1$; column $c$ occupies the half-open range
  `[column_offsets[c], column_offsets[c + 1])` in the other two arrays.
- `row_indices` contains strictly increasing row indices within each column.
- `values` corresponds one-to-one with `row_indices` and uses the physical
  units supplied by the caller; the demo performs no unit conversion.

The final `column_offsets` entry equals both `row_indices.size()` and
`values.size()`. A successful symbolic build initializes all `values` to zero.

### Symbolic input

`ElementDofMap` is a complete element-to-global-DOF topology:

- `element_ids` is nonempty and contains unique, nonnegative identifiers.
- `element_dof_offsets` has `element_ids.size() + 1` entries, begins at zero,
  is monotone, and ends at `global_dof_indices.size()`.
- Every element segment is nonempty and contains no repeated global DOF.
- Global DOF indices are nonnegative and their distinct values are exactly the
  compact range $[0,n)$; a DOF may appear in multiple elements.

Input element order is arbitrary. Symbolic construction sorts elements by
ascending `ElementId`, while preserving each element's local DOF order. Within
every CSC3 column, row indices are sorted in ascending order. The returned
`AssemblyPlan` uses the same canonical element order, and each scatter segment
enumerates local upper-triangular pairs in row-major order.

### Numeric input and overwrite behavior

`ElementMatrixBatch` must provide exactly one full dense matrix for every
element in `assembly_plan().element_ids`, in that canonical order. If element
$e$ has local dimension $d_e$, its segment contains exactly $d_e^2$ finite
values in row-major order. `element_value_offsets` begins at zero, is monotone,
has one terminal entry, and ends at `values_row_major.size()`.

Each local matrix must be symmetric within the documented combined absolute
and relative tolerance. The upper local entry is the value assembled; the
lower entry is used to validate symmetry. Partial batches and per-element
updates are unsupported.

Every successful `assemble_numeric_atomic(...)` call first resets the complete
CSC3 value array and then assembles the supplied batch. Repeating the same call
therefore overwrites rather than accumulates onto the previous result.

### Exceptions, ownership, and the thread-count contract

- Invalid topology, batch layout, non-finite or materially nonsymmetric values,
  and nonpositive thread counts throw `std::invalid_argument`.
- Numeric assembly before a successful symbolic build throws
  `std::logic_error`. Representability failures throw `std::overflow_error`;
  normal allocation exceptions may also propagate.
- Input structs own their vectors. The assembler copies and canonicalizes the
  topology and does not retain either input object. Accessors return const
  references tied to assembler-owned members. A mutating call can replace their
  contents and invalidate pointers, iterators, or references into their vectors;
  no returned reference survives the assembler itself.
- One `SymmetricCscAssembler` instance is not internally synchronized. Do not
  call it, or read its state while mutating it, concurrently. Independent
  instances may be used concurrently.
- `thread_count` must be positive and is a request to the OpenMP runtime, not a
  guarantee. Runtime policy and available resources may produce a smaller
  team. The two `*_thread_count_used()` accessors report the team sizes that
  were actually observed.

The normative details, including exact invariants and naming rules, are in
[the API and naming contract](docs/api-and-naming-contract.md). Existing users
must follow [the version `0.2.0` migration guide](MIGRATION.md); compatibility
aliases are intentionally absent.

## Prerequisites and delivery preset

All platforms require CMake `3.21` or newer, Ninja, a C++17 compiler, and a
working OpenMP C++ runtime. The evidence and JUnit workflow requires CMake
`3.21` or newer. The C++ build and tests do not require Python. The acceptance
test runner additionally requires Python `3.10` or newer and the dependency
declared in `requirements-test.txt`. Run the preset commands from this
directory.

### Linux

Use GCC `9` or newer with its `libgomp` runtime. On current Debian or Ubuntu
systems, install `cmake`, `ninja-build`, and `g++`, then confirm
`cmake --version` reports at least `3.21`:

```bash
cmake --preset delivery
cmake --build --preset delivery
ctest --preset delivery --output-on-failure
```

Clang is also usable when its matching OpenMP development package is installed
and CMake can discover that runtime, but the compiler and runtime must be
selected consistently by the caller.

### macOS

Install the Xcode Command Line Tools, CMake, Ninja, and Homebrew `libomp`.
AppleClang does not provide its own OpenMP runtime, so export the portable CMake
package hint before configuring:

```bash
brew install cmake ninja libomp
export OpenMP_ROOT="$(brew --prefix libomp)"
cmake --preset delivery
cmake --build --preset delivery
ctest --preset delivery --output-on-failure
```

The preset deliberately contains no Homebrew path.

### Windows

Use Visual Studio 2022 Build Tools with the **Desktop development with C++**
workload, including the MSVC v143 x64/x86 build tools, plus CMake `3.21` or
newer and Ninja on `PATH`. Run an **x64 Native Tools Command Prompt for VS
2022** so CMake can find `cl.exe` and enable its `/openmp` support, then run:

```powershell
cmake --preset delivery
cmake --build --preset delivery
ctest --preset delivery --output-on-failure
```

The delivery preset configures `Release`, requires OpenMP, enables warnings as
errors, sets `CSC3_DEMO_BUILD_CPP_TESTS=ON`, and enables both the nine C++
tests and the Python acceptance runner. The authoritative names and order for
those C++ tests are recorded in
[`tests/ctest/expected-cpp-tests.txt`](tests/ctest/expected-cpp-tests.txt).
Executables are written to `build/delivery/bin` and libraries to
`build/delivery/lib` for both single- and multi-config generators.

## Minimal source integration

This task intentionally provides a build-tree target, not an installable CMake
package. Add the source directory and link the public alias:

```cmake
add_subdirectory(path/to/csc3_symmetric_assembly_demo)
target_link_libraries(my_solver PRIVATE csc3_demo::csc3_demo)
```

When included as a subproject, the demo's internal C++ and acceptance tests are
disabled by default without changing the parent project's `BUILD_TESTING`
value. A top-level `BUILD_TESTING=ON` configuration enables the C++ tests; the
Python acceptance runner remains an explicit
`CSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON` opt-in.

The public API is available through one header. The matrix batch below follows
the canonical element order `10, 20`, even though the topology arrives as
`20, 10`:

```cpp
#include "csc3_demo/assembly_helper.h"

int main() {
    const csc3_demo::ElementDofMap topology{
        {20, 10},
        {0, 2, 4},
        {1, 2, 0, 1},
    };
    const csc3_demo::ElementMatrixBatch element_matrices{
        {0, 4, 8},
        {
            2.0, -1.0, -1.0, 2.0,
            3.0, -2.0, -2.0, 3.0,
        },
    };

    csc3_demo::SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(topology, 4);
    assembler.assemble_numeric_atomic(element_matrices, 4);

    const csc3_demo::Csc3Matrix& matrix = assembler.matrix();
    return matrix.dimension == 3 ? 0 : 1;
}
```

## Evidence and release status

The CTest suite checks behavior, including deterministic symbolic structure,
atomic high-contention assembly, validation, and an independent public-header
consumer. CI duration is operational feedback only; it is not formal
performance evidence and must not be quoted as such.

The repository includes a checked macOS `LOCAL_SMOKE` evidence bundle and its
Chinese report. They demonstrate the evidence pipeline but are not a formal
performance result for a later package commit. Generated formal correctness
and performance reporting remains owned by
[Issue #44](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/44).

The deterministic source-delivery procedure is documented in
[`packaging/README.md`](packaging/README.md). It creates a Git-blob whitelist
archive with `BUILD_INFO.json`, `MANIFEST.sha256`, raw evidence, the selected
report, third-party dependency notices, and an internal-evaluation statement.
The portable verifier checks archive integrity before extraction and can run a
full clean-room build, CTest suite, and independent consumer integration.

Formal research-institute acceptance is intentionally separate from local
smoke and CI. A registered operator must execute the
[controlled Linux Intel formal runbook](packaging/LINUX_FORMAL_RUNBOOK.zh-CN.md),
then follow the
[two-stage acceptance workflow](packaging/TWO_STAGE_ACCEPTANCE_WORKFLOW.zh-CN.md).
The mandatory handoff order is `draft`, human decision, `render`, `validate`,
then `finalize`. `scripts/prepare_acceptance_materials.py draft` freezes the
candidate facts as `acceptance-machine-facts.json` under the
[machine-facts schema](packaging/ACCEPTANCE_MACHINE_FACTS.schema.json) and
creates `acceptance-decision.json` under the
[decision schema](packaging/ACCEPTANCE_DECISION.schema.json). Humans edit only
`acceptance-decision.json`; the machine facts remain immutable.

After all four roles approve the same candidate, machine facts, and
organizational decision, `scripts/prepare_acceptance_materials.py render`
creates the acceptance record, completed checklist, and completed delivery note
as deterministic renderer outputs. Those outputs follow the
[acceptance-record schema](packaging/ACCEPTANCE_RECORD.schema.json),
[checklist template](packaging/ACCEPTANCE_CHECKLIST.zh-CN.md), and
[delivery-note template](packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md); they must
not be copied or edited manually. `scripts/validate_acceptance_record.py` then
performs cross-field validation, and `scripts/finalize_delivery.py`
independently rerenders and verifies the sidecars before creating the hash-bound
final directory. The automated Linux run produces only a `PACKAGE_CANDIDATE`.
Until the full sequence passes, formal acceptance remains `PENDING` and no
existing ZIP should be submitted as an accepted deliverable.

The entire source package remains **INTERNAL EVALUATION ONLY** until
[Issue #37](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/37)
resolves distribution policy.
