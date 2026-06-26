# Figure contract

- Core conclusion: solve-level free-tip deflection comparison is small for Tet4/C3D4 on all three references, while Hex8/C3D8 shows a Windows/Abaqus discrepancy that should be reported as a validation signal.
- Evidence chain: each figure maps the same free-tip percentage metric across macOS+COMSOL, Linux+CalculiX, and Windows+Abaqus; metadata cards define the mesh and stiffness sparsity context.
- Archetype: quantitative grid with a metadata sidecar.
- Backend: Python-only matplotlib export.
- Export contract: SVG primary with editable text, plus PDF, PNG, TIFF, and a source CSV.
- Review risk: macOS+COMSOL values are recovered from a legacy report table, not a current CSV package; Tet4 solver-validation and unstructured-Tet4 sparsity assets are not the same mesh.
