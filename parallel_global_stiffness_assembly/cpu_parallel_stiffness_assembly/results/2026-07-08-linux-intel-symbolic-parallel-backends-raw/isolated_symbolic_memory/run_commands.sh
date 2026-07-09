#!/usr/bin/env bash
set -euo pipefail

# symbolic_reuse_serial-a1-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list symbolic_reuse_serial

# symbolic_reuse_serial-a1-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list symbolic_reuse_serial

# symbolic_reuse_serial-a1-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/symbolic_reuse_serial-a1-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list symbolic_reuse_serial

# parallel_symbolic_reuse-a1-t1-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t1-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t1-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 1 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t2-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t2-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 2 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t3-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t3-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 3 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t4-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t4-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 4 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t5-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t5-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 5 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t6-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t6-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 6 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t7-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t7-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 7 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t8-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t8-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 8 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t9-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t9-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 9 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t10-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t10-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 10 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t11-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t11-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 11 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t12-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t12-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 12 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t13-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t13-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 13 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t14-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t14-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 14 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t15-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t15-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 15 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t16-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t16-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 16 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t17-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t17-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 17 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t18-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t18-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 18 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t19-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t19-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 19 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-atomic-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-atomic-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-atomic-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-atomic-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list atomic --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-private_csr-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-private_csr-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-private_csr-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-private_csr-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list private_csr --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-lock_guard-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-lock_guard-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-lock_guard-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-lock_guard-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list lock_guard --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-coloring-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-coloring-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-coloring-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-coloring-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list coloring --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-row_owner-r1
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r1/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r1/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r1/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-row_owner-r2
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r2/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r2/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r2/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list row_owner --mode-list parallel_symbolic_reuse

# parallel_symbolic_reuse-a1-t20-row_owner-r3
build/cpu-release/bin/symbolic_numeric_eval --mesh inp --stiffness-model linear_elastic_solid --max-memory-gb 32.0 --csv /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r3/row.csv --json /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r3/row.json --summary-md /tmp/pgsa-iso-jo0afxhg/parallel_symbolic_reuse-a1-t20-row_owner-r3/row.md --case-name 3d-WindTurbineHub --inp ../../examples/3d-WindTurbineHub.inp --assemblies-list 1 --threads-list 20 --backend-list row_owner --mode-list parallel_symbolic_reuse
