# Validation Fixtures

These small Abaqus `.inp` files mirror the generated cantilever validation
cases used by `validation_export`. They are intentionally tiny so they can be
checked into the repository, loaded by the C++ parser, and reused as Abaqus
model seeds.

- `cantilever_hex8_small.inp`: one C3D8 block with dimensions `1 x 0.2 x 0.1`.
- `cantilever_tet4_small.inp`: the same block decomposed into six C3D4
  tetrahedra.

The executable-generated cases remain the default for regression tests because
they include enough nodes to place the `free_tip_center` and `midspan_center`
probes exactly at mesh nodes.
