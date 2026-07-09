#!/usr/bin/env bash
set -euo pipefail

cd /home/haohua/Documents/GitHub/parallel-global-stiffness-assembly-research-and-implementation/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly

OUT_DIR=results/2026-06-26-intel-backend-thread-sweep-isolated-raw
MESH=../../examples/3d-WindTurbineHub.inp

python3 scripts/inspect_cpu_platform.py
git rev-parse HEAD
git status --short
uname -a
lscpu
cmake --version
c++ --version
g++ --version
gcc --version
git lfs pull
wc -c "$MESH"
sed -n "1,8p" "$MESH"

cmake -S . -B build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON \
  -DBUILD_TESTS=ON \
  -DBUILD_BENCHMARKS=ON \
  -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build/cpu-release --target benchmark_assembly -j
ctest --test-dir build/cpu-release --output-on-failure
./build/cpu-release/bin/benchmark_assembly --help

OMP_DYNAMIC=FALSE OMP_PROC_BIND=close OMP_PLACES=cores \
python3 scripts/run_isolated_backend_thread_sweep.py \
  --benchmark-exe ./build/cpu-release/bin/benchmark_assembly \
  --out-root "$OUT_DIR" \
  --mesh inp \
  --inp "$MESH" \
  --case-name 3d-WindTurbineHub \
  --kernel physics_tet4 \
  --algorithms serial,atomic,private_csr,lock_guard,coloring,row_owner \
  --threads-range 1:20 \
  --process-repeat 3 \
  --warmup 1

cp "$OUT_DIR/windhub_backend_thread_sweep_intel_isolated_repeats.csv" "$OUT_DIR/windhub_backend_thread_sweep_intel.csv"
cp "$OUT_DIR/windhub_backend_thread_sweep_intel_isolated.json" "$OUT_DIR/windhub_backend_thread_sweep_intel.json"
cp "$OUT_DIR/windhub_backend_thread_sweep_intel_isolated.md" "$OUT_DIR/windhub_backend_thread_sweep_intel.md"

tar -czf intel_backend_thread_sweep_isolated_raw_2026-06-26.tar.gz "$OUT_DIR"
