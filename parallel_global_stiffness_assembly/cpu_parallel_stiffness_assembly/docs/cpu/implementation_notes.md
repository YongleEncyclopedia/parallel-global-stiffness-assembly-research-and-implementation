# CPU Backend Implementation Notes

## Stage separation

The benchmark separates:

1. mesh creation or `.inp` parsing,
2. CSR symbolic sparsity construction,
3. element-local scatter-address precomputation,
4. algorithm-specific preprocessing,
5. numeric assembly.

This is important because graph coloring, COO generation, private CSR allocation, and row-owner task construction have very different preprocessing and memory costs.

## Algorithm interpretation

- `cpu_serial` is the only correctness and speedup baseline.
- `cpu_atomic` is the CPU AddTo baseline. It keeps natural element order and relies on OpenMP atomics for conflicts.
- `cpu_graph_coloring` preserves the earlier CPU graph-coloring idea and measures color count and load distribution.
- `cpu_private_csr` trades memory for synchronization-free writes.
- `cpu_coo_sort_reduce` tests whether sort/reduce is competitive with direct CSR AddTo.
- `cpu_row_owner` is an owner-computes prototype. It is conflict-free by row ownership, but can recompute one element matrix more than once if its rows are owned by different threads.

## Practical caution for WindTurbineHub

For million-element C3D4 meshes, start with:

```bash
--algo serial,atomic,coloring --kernel simplified
```

Then add memory-heavy algorithms one at a time with a realistic `--max-memory-gb` value.
