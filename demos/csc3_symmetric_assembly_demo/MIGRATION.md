# Migration to CSC3 Demo `0.2.0`

Version `0.2.0` intentionally replaces the prototype API with a typed,
flattened, parallel-only contract. It provides no compatibility aliases. A
consumer must update names and data flow in one change; code written against
the removed API is expected to fail at compile time until migrated.

## Old-to-new mapping

| Removed `0.1.x` name | `0.2.0` replacement | Required migration |
| --- | --- | --- |
| `Index` | `GlobalDofIndex` or `Offset` | Use `GlobalDofIndex` for zero-based DOF coordinates and `Offset` for flattened-array boundaries or targets. |
| `NodeId` | No public replacement | Resolve node topology to global DOFs before calling the demo. |
| `DofCodingInfo` | `ElementDofMap` | Supply the complete flattened element-to-global-DOF map. |
| `DofCodingInfo::elems` | `ElementDofMap::element_ids`, `element_dof_offsets`, and `global_dof_indices` | Flatten each element's resolved global DOFs into one segment. Input element order may be arbitrary. |
| `DofCodingInfo::node_dofs` | Folded into `ElementDofMap::global_dof_indices` | Perform node-to-DOF resolution in the caller; the public API no longer owns a node layer. |
| `Csc3Matrix::n` | `Csc3Matrix::dimension` | Rename the matrix row and column count. |
| `Csc3Matrix::col_ptr` | `Csc3Matrix::column_offsets` | Use zero-based `Offset` values; the terminal entry still identifies the stored-entry count. |
| `Csc3Matrix::row_idx` | `Csc3Matrix::row_indices` | Use zero-based `GlobalDofIndex` values. |
| `HelpInfo` | `AssemblyPlan` | Read canonical topology and scatter data from the explicit plan type. |
| `HelpInfo::element_dofs` | `AssemblyPlan::global_dof_indices` | Use the more specific global-DOF name. |
| `HelpInfo::entry_offsets` | `AssemblyPlan::element_scatter_offsets` | Use the per-element offsets into the scatter array. |
| `HelpInfo::scatter` | `AssemblyPlan::scatter_indices` | Use zero-based `Offset` targets into `Csc3Matrix::values`. |
| `AssemblyHelper` | `SymmetricCscAssembler` | Replace the helper with the owning two-stage assembler. |
| `AssemblyHelper::symbolic` | `SymmetricCscAssembler::build_symbolic_parallel` | Pass an `ElementDofMap` and an explicit positive `thread_count`. |
| `AssemblyHelper::zero_values` | No separate call | Every successful `assemble_numeric_atomic` call resets all values before assembly. |
| `AssemblyHelper::add` | `SymmetricCscAssembler::assemble_numeric_atomic` | Per-element updates are removed; construct one complete `ElementMatrixBatch`. |
| `AssemblyHelper::add_parallel` | `SymmetricCscAssembler::assemble_numeric_atomic` | Replace the element-ID map with a flattened batch ordered by `assembly_plan().element_ids`. |
| `AssemblyHelper::help_info` | `SymmetricCscAssembler::assembly_plan` | The returned const reference is still assembler-owned. |
| `ke_row_major` | `ElementMatrixBatch::values_row_major` | Concatenate one full, finite, symmetric row-major matrix per canonical element. |
| `size` | No public parameter | The local dimension $d_e$ comes from the symbolic plan; each value segment must contain exactly $d_e^2$ entries. |
| `threads` | `thread_count` | Pass a positive OpenMP thread request; query the corresponding `*_thread_count_used()` method for the observed team size. |
| `expand_upper_csc_to_dense` | No public replacement | Keep dense expansion in consumer validation or test code if needed. |
| `generate_demo_report` | No public replacement | Formal generated reporting is separated from the assembly API and tracked by Issue #44. |
| Eigen `add` overload | No public replacement | Flatten the caller's matrix into `ElementMatrixBatch::values_row_major`; no Eigen type crosses the public boundary. |

## Data-flow migration

The old API accepted node connectivity and a node-to-DOF map. The new API
starts after that resolution step. For every input element:

1. Resolve its nodes to the element's ordered global DOF list.
2. Append its identifier to `ElementDofMap::element_ids`.
3. Append the ordered DOFs to `ElementDofMap::global_dof_indices` and append the
   new terminal size to `element_dof_offsets`.
4. Call `build_symbolic_parallel(...)` with a positive `thread_count`.

The assembler sorts elements by ascending identifier while preserving each
element's local DOF order. Numeric data must then follow
`assembly_plan().element_ids`, not the original input order:

1. Create `element_value_offsets` beginning with zero.
2. For each canonical element, append its complete $d_e \times d_e$ row-major
   symmetric matrix to `values_row_major`.
3. Append the new terminal value count after every matrix.
4. Call `assemble_numeric_atomic(...)` once for the complete batch.

Partial `add(...)` loops are not equivalent to the new contract. A numeric call
always clears the prior values and performs a complete one-shot assembly.

## Minimal call-site rewrite

Before:

```cpp
csc3_demo::AssemblyHelper helper;
helper.symbolic(info);
helper.add_parallel(element_matrices, threads);
const auto& matrix = helper.matrix();
```

After:

```cpp
csc3_demo::SymmetricCscAssembler assembler;
assembler.build_symbolic_parallel(element_dof_map, thread_count);
assembler.assemble_numeric_atomic(element_matrix_batch, thread_count);
const csc3_demo::Csc3Matrix& matrix = assembler.matrix();
```

The new build also requires OpenMP. There is no compatibility option or serial
fallback: `CSC3_DEMO_REQUIRE_OPENMP=OFF` is an intentional configuration error.
