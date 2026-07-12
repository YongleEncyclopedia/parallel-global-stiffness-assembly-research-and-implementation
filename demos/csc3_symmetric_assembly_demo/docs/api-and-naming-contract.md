# CSC3 API and Naming Contract

This document is the normative public contract for version `0.2.0` of the
CSC3 symmetric assembly demo. The only supported implementation is OpenMP
parallel symbolic construction followed by OpenMP atomic numeric assembly.

## Public API inventory

### Types and aliases

| Public name | Kind | Contract |
| --- | --- | --- |
| `GlobalDofIndex` | `std::int32_t` alias | A nonnegative, zero-based global DOF index in the compact range $[0,n)$. |
| `ElementId` | `std::int32_t` alias | A unique, nonnegative element identifier; it is an identity, not an input ordinal. |
| `Offset` | `std::uint64_t` alias | A nonnegative, zero-based offset into a flattened owned array. |
| `ElementDofMap` | owning struct | Complete flattened element-to-global-DOF topology input. |
| `ElementMatrixBatch` | owning struct | Complete batch of dense element matrices in canonical element order. |
| `Csc3Matrix` | owning struct | Zero-based CSC3 upper-triangle structure and values. |
| `AssemblyPlan` | owning struct | Canonicalized topology and numeric scatter targets. |
| `SymmetricCscAssembler` | owning class | Owns the current matrix and plan and exposes the two-stage API. |

### Public fields

| Owner | Field | Meaning |
| --- | --- | --- |
| `ElementDofMap` | `element_ids` | One nonnegative, unique identifier per input element segment. |
| `ElementDofMap` | `element_dof_offsets` | Zero-based segment offsets into `global_dof_indices`; length is the element count plus one. |
| `ElementDofMap` | `global_dof_indices` | Flattened zero-based global DOFs in each element's local order. |
| `ElementMatrixBatch` | `element_value_offsets` | Zero-based segment offsets into `values_row_major`; length is the canonical element count plus one. |
| `ElementMatrixBatch` | `values_row_major` | Flattened finite values for one full row-major square matrix per canonical element. |
| `Csc3Matrix` | `dimension` | Matrix row and column count $n$. |
| `Csc3Matrix` | `column_offsets` | Zero-based CSC column offsets; length is $n+1$. |
| `Csc3Matrix` | `row_indices` | Zero-based row indices, strictly increasing within each column. |
| `Csc3Matrix` | `values` | Stored upper-triangle values corresponding one-to-one with `row_indices`. |
| `AssemblyPlan` | `element_ids` | Element identifiers in strictly increasing canonical order. |
| `AssemblyPlan` | `element_dof_offsets` | Zero-based offsets into the plan's `global_dof_indices`. |
| `AssemblyPlan` | `global_dof_indices` | Flattened global DOFs with each element's local order preserved. |
| `AssemblyPlan` | `element_scatter_offsets` | Zero-based offsets into `scatter_indices`, one segment per canonical element. |
| `AssemblyPlan` | `scatter_indices` | Zero-based target offsets into `Csc3Matrix::values`. |

### Functions and methods

| Public call | Contract |
| --- | --- |
| `build_symbolic_parallel(element_dof_map, thread_count)` | Validates and copies a complete topology, sorts elements by ascending identifier, builds deterministic CSC3 structure and scatter data, and replaces prior assembler state on success. |
| `assemble_numeric_atomic(element_matrices, thread_count)` | Validates a complete canonical matrix batch, clears all stored values, and atomically assembles the batch. |
| `matrix()` | Returns a const reference to assembler-owned matrix state. |
| `assembly_plan()` | Returns a const reference to assembler-owned canonical plan state. |
| `symbolic_thread_count_used()` | Returns the largest OpenMP team size observed during the most recent successful symbolic call, or zero before one succeeds. |
| `numeric_thread_count_used()` | Returns the OpenMP team size observed during the most recent successful numeric call, or zero before one succeeds or after a new symbolic build. |
| `openmp_enabled()` | Returns `true` for every supported build; configuration fails instead of producing a serial fallback. |
| `max_openmp_threads()` | Returns the calling thread's current OpenMP maximum-team-size setting. |

## Naming rules

- Public types and type aliases use `PascalCase`.
- Functions, methods, parameters, local variables, and public fields use
  `snake_case`.
- Private data members use `snake_case_` with one trailing underscore.
- `_id` denotes one stable identifier, while `_ids` denotes a collection of
  identifiers. An identifier must not be presented as an ordinal.
- `_indices` denotes zero-based indices or indexed identifiers in a collection.
- `_offsets` denotes zero-based boundaries or prefix sums into a flattened
  array; an offsets array normally includes its terminal boundary.
- `_count` denotes a dimensionless number of items or threads.
- `_ms` denotes elapsed time in milliseconds.
- `_bytes` denotes a storage quantity in bytes.

New public names must be semantically specific. Vague bare names such as `n`,
`size`, `info`, and `help` are forbidden. Use names such as `dimension`,
`thread_count`, `element_dof_map`, or `assembly_plan` that expose meaning and
units.

## Zero-based ranges and units

- A valid `GlobalDofIndex` is in $[0,n)$, where $n$ is the matrix dimension.
  The distinct input DOFs must equal that entire compact range.
- A valid `ElementId` is in $[0,2^{31}-1]$ and is unique within one topology.
- An `Offset` is in $[0,2^{64}-1]$ and must also be representable by the host
  container before it is used for memory indexing.
- DOF indices, element identifiers, offsets, dimensions, and thread counts are
  dimensionless. Matrix `values` retain the caller's physical unit, such as a
  stiffness unit; no conversion or unit metadata is applied.
- Future public timing and storage fields must use `_ms` and `_bytes`
  respectively so the unit is explicit.

## Topology and canonical ordering

For $m$ input elements:

1. `element_ids` has length $m$, contains no duplicate, and is nonempty.
2. `element_dof_offsets` has length $m+1$, starts at zero, is monotone, and its
   terminal offset equals `global_dof_indices.size()`.
3. Every element owns at least one DOF and has no repeated DOF in its local
   segment. Sharing a DOF between different elements is valid.
4. Element IDs and global DOFs are nonnegative. The distinct global DOFs are
   exactly $0,1,\ldots,n-1$.

Input elements may be unordered. The assembly plan sorts them by ascending
`ElementId`; local DOF order inside each element is preserved. The numeric batch
has no element-ID field, so its segments must follow
`assembly_plan().element_ids` exactly. This makes a batch complete and
unambiguous: partial, missing, duplicate, or unknown-element updates have no
representation in the public API.

## CSC3 invariants

After a successful symbolic build, all of the following hold:

- `dimension` is $n>0$.
- `column_offsets.size()` is $n+1$, `column_offsets[0]` is zero, and offsets are
  monotone.
- `column_offsets[n]` equals both `row_indices.size()` and `values.size()`.
- For column $c$, positions in
  $[\mathtt{column\_offsets}[c],\mathtt{column\_offsets}[c+1])$ have strictly
  increasing row indices satisfying $0 \le r \le c<n$.
- The stored pattern is the union of all upper-triangular global DOF pairs
  induced by the element topology. Every numbered global DOF contributes its
  diagonal entry.
- Symbolic `values` are zero initialized.

For a canonical element with local dimension $d_e$,
`element_scatter_offsets` reserves $d_e(d_e+1)/2$ targets. `scatter_indices`
enumerates local pairs $(i,j)$ in row-major upper-triangular order:
$0 \le i \le j < d_e$. Every target is a valid zero-based position in
`Csc3Matrix::values`.

## Dense local matrix contract

For each canonical element $e$, the numeric segment contains exactly $d_e^2$
finite `double` values and represents a full $d_e \times d_e$ row-major matrix.
For off-diagonal entries $a_{ij}$ and $a_{ji}$, the batch is rejected when both
parts of the combined tolerance are exceeded:

$$
|a_{ij}-a_{ji}| > 10^{-12}
\quad\text{and}\quad
|a_{ij}-a_{ji}| > 10^{-10}\max(|a_{ij}|,|a_{ji}|).
$$

The upper local value $a_{ij}$ for $i\le j$ is assembled; the lower value is
only a symmetry check. The assembler does not average the pair.

Every successful numeric call is one-shot: it overwrites the entire CSC3 value
array rather than accumulating on a previous call. OpenMP atomics make shared
updates race-free, but floating-point summation order is not a bitwise
determinism guarantee.

## Ownership, lifetime, exceptions, and thread safety

All public data structs own their `std::vector` storage. Symbolic construction
copies and canonicalizes `ElementDofMap`; numeric assembly borrows
`ElementMatrixBatch` only for the duration of the call. No input pointer or
reference is retained.

`matrix()` and `assembly_plan()` return const references to assembler-owned
member objects. The member-object references remain tied to that assembler,
but a mutating call can replace their contents and invalidate every pointer,
iterator, or reference derived from their vectors. Nothing returned from an
accessor outlives the assembler.

The public exception contract is:

- `std::invalid_argument` for nonpositive `thread_count`, malformed topology or
  offsets, invalid local dimensions, non-finite values, or a materially
  nonsymmetric matrix.
- `std::logic_error` when numeric assembly precedes symbolic construction or an
  internal plan invariant is violated.
- `std::overflow_error` when a count, offset, dimension, or allocation request
  cannot be represented by the public or host index types.
- Standard allocation exceptions may propagate.

A single `SymmetricCscAssembler` instance is not thread-safe for concurrent
calls, including reads concurrent with mutation. Callers may operate on
independent instances concurrently. A positive `thread_count` is an OpenMP
request; the runtime may provide fewer threads. Query the recorded team-size
accessors after successful calls when the observed count matters.
