#!/usr/bin/env bash
set -euo pipefail

cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

python3 scripts/inspect_cpu_platform.py
git rev-parse HEAD
git status --short
uname -a
lscpu
cmake --version
cc --version || true
c++ --version || true
gcc --version || true
g++ --version || true
git lfs pull
ls -lh ../../examples/3d-WindTurbineHub.inp
wc -c ../../examples/3d-WindTurbineHub.inp
sed -n "1,8p" ../../examples/3d-WindTurbineHub.inp

cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --target benchmark_assembly -j
cmake --build build/cpu-release -j
ctest --test-dir build/cpu-release --output-on-failure
./build/cpu-release/bin/benchmark_assembly --help

OMP_DYNAMIC=FALSE OMP_PROC_BIND=close OMP_PLACES=cores ./build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --kernel physics_tet4 \
  --algo serial,atomic,private_csr,lock_guard,coloring,row_owner \
  --threads-range 1:20 \
  --warmup 1 \
  --repeat 3 \
  --check \
  --schema-version pgsa-cross-platform-v1 \
  --platform-id linux-intel-core-ultra-7-265kf \
  --run-profile full_host \
  --env-group intel_backend_thread_sweep_raw \
  --csv results/2026-06-26-intel-backend-thread-sweep-raw/windhub_backend_thread_sweep_intel.csv \
  --json results/2026-06-26-intel-backend-thread-sweep-raw/windhub_backend_thread_sweep_intel.json \
  --summary-md results/2026-06-26-intel-backend-thread-sweep-raw/windhub_backend_thread_sweep_intel.md

tar -czf intel_backend_thread_sweep_raw_2026-06-26.tar.gz results/2026-06-26-intel-backend-thread-sweep-raw
