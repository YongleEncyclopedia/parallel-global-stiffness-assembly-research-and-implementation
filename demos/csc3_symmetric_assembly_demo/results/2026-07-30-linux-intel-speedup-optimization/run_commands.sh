#!/usr/bin/env bash
set -euo pipefail

ROOT=/tmp/csc3-issue44-linux-20260729-worktree
DEMO="${ROOT}/demos/csc3_symmetric_assembly_demo"
PYTHON=/tmp/csc3-issue44-linux-20260729-venv/bin/python
RELEASE_BUILD=/tmp/csc3-issue44-speedup-20260730-baseline/build
SANITIZER_BUILD=/tmp/csc3-issue44-speedup-20260730-sanitizers/build
RUNNER="${DEMO}/results/2026-07-29-linux-intel-issue-44/scripts/run_linux_process_benchmark.py"
OUT=/tmp/csc3-issue44-speedup-20260730-process-r1

cd "${DEMO}"

cmake --preset delivery -B "${RELEASE_BUILD}" \
  "-DPython3_EXECUTABLE:FILEPATH=${PYTHON}"
cmake --build "${RELEASE_BUILD}" --config Release --parallel
env OMP_NUM_THREADS=2 OMP_THREAD_LIMIT=2 OMP_DYNAMIC=false \
  ctest --test-dir "${RELEASE_BUILD}" -C Release --label-regex ci \
  --output-on-failure --no-tests=error

cmake --preset ci-sanitizers -B "${SANITIZER_BUILD}" \
  "-DPython3_EXECUTABLE:FILEPATH=${PYTHON}"
cmake --build "${SANITIZER_BUILD}" --config Debug --parallel
env OMP_NUM_THREADS=2 OMP_THREAD_LIMIT=2 OMP_DYNAMIC=false \
  ctest --test-dir "${SANITIZER_BUILD}" -C Debug --label-regex ci \
  --output-on-failure --no-tests=error

"${PYTHON}" -m unittest discover \
  -s "${DEMO}/tests/python" -p 'test_*.py' -v

"${PYTHON}" "${RUNNER}" \
  --repository-root "${ROOT}" \
  --benchmark-executable "${RELEASE_BUILD}/bin/csc3_demo_benchmark" \
  --input "${ROOT}/examples/3d-WindTurbineHub.inp" \
  --out-dir "${OUT}" \
  --maximum-threads 20 \
  --warmup 2 \
  --repeat 7 \
  --compiler 'g++ 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1)' \
  --cmake 'cmake 3.28.3' \
  --ninja 'ninja 1.11.1' \
  --openmp-runtime 'GNU libgomp 14.2.0-4ubuntu2~24.04.1'
