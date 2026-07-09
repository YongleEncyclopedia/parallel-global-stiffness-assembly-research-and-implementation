#!/usr/bin/env bash
set -euo pipefail
cd "/home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly"
OUT_DIR="results/2026-06-26-linux-intel-symbolic-parallel-backends-raw" \
MESH="../../examples/3d-WindTurbineHub.inp" \
THREADS_RANGE="1:20" \
BACKENDS="atomic,private_csr,lock_guard,coloring,row_owner" \
MODES="symbolic_reuse_serial,parallel_symbolic_reuse" \
STIFFNESS_MODEL="linear_elastic_solid" \
MAX_MEMORY_GB="32" \
bash scripts/run_linux_intel_symbolic_parallel_backends_raw.sh
