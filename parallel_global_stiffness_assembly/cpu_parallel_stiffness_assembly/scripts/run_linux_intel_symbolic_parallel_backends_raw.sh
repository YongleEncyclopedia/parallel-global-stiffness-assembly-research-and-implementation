#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPU_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CPU_ROOT"

OUT_DIR="${OUT_DIR:-results/2026-06-26-linux-intel-symbolic-parallel-backends-raw}"
MESH="${MESH:-../../examples/3d-WindTurbineHub.inp}"
THREADS_RANGE="${THREADS_RANGE:-1:20}"
BACKENDS="${BACKENDS:-atomic,private_csr,lock_guard,coloring,row_owner}"
MODES="${MODES:-symbolic_reuse_serial,parallel_symbolic_reuse}"
STIFFNESS_MODEL="${STIFFNESS_MODEL:-linear_elastic_solid}"
MAX_MEMORY_GB="${MAX_MEMORY_GB:-32}"
SYMBOLIC_EXE="${SYMBOLIC_EXE:-build/cpu-release/bin/symbolic_numeric_eval}"
TARBALL="${TARBALL:-linux_intel_symbolic_parallel_backends_raw_2026-06-26.tar.gz}"

mkdir -p "$OUT_DIR"
exec > >(tee "$OUT_DIR/run.log") 2>&1

run() {
  echo "+ $*"
  "$@"
}

run_omp() {
  echo "+ OMP_DYNAMIC=FALSE OMP_PROC_BIND=close OMP_PLACES=cores $*"
  OMP_DYNAMIC=FALSE OMP_PROC_BIND=close OMP_PLACES=cores "$@"
}

mesh_element_cards() {
  local mesh="$1"
  if command -v rg >/dev/null 2>&1; then
    rg -n '^\*ELEMENT' "$mesh"
  else
    grep -n '^\*ELEMENT' "$mesh"
  fi
}

write_run_commands() {
  cat > "$OUT_DIR/run_commands.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$CPU_ROOT"
OUT_DIR="$OUT_DIR" \\
MESH="$MESH" \\
THREADS_RANGE="$THREADS_RANGE" \\
BACKENDS="$BACKENDS" \\
MODES="$MODES" \\
STIFFNESS_MODEL="$STIFFNESS_MODEL" \\
MAX_MEMORY_GB="$MAX_MEMORY_GB" \\
bash scripts/run_linux_intel_symbolic_parallel_backends_raw.sh
EOF
}

write_platform_info() {
  {
    echo "# Linux Intel symbolic-parallel backend raw data"
    echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "## git"
    git rev-parse HEAD
    git status --short
    echo
    echo "## system"
    uname -a
    lscpu
    echo
    echo "## platform detector"
    python3 scripts/inspect_cpu_platform.py
    echo
    echo "## cmake"
    cmake --version
    echo
    echo "## compiler"
    c++ --version
    g++ --version
    echo
    echo "## mesh"
    wc -c "$MESH"
    mesh_element_cards "$MESH"
    echo
    echo "## experiment"
    echo "mesh=$MESH"
    echo "threads_range=$THREADS_RANGE"
    echo "backends=$BACKENDS"
    echo "modes=$MODES"
    echo "stiffness_model=$STIFFNESS_MODEL"
    echo "max_memory_gb=$MAX_MEMORY_GB"
  } > "$OUT_DIR/platform_info.txt"
}

write_readme() {
  cat > "$OUT_DIR/README_raw_data.md" <<'EOF'
# Linux Intel symbolic-parallel backend raw data

This package reruns the original isolated symbolic-memory experiment style used by the monthly-report figure.

Measurement scope:
- Baseline: serial symbolic assembly + serial numeric assembly.
- Parallel rows: parallel symbolic assembly + parallel numeric assembly.
- Direct no-symbolic assembly is intentionally excluded.
- Five numeric backends are included: atomic, private_csr, lock_guard, coloring, row_owner.
- Thread range: 1..20.
- Repetition policy: one quick isolated run per row.
- Memory: isolated subprocess peak RSS.
- Timing: symbolic_total_ms + numeric_ms = amortized_total_ms.

Linux side only generates raw data. Plotting is done later on the Mac side.
EOF
}

echo "== Linux Intel symbolic-parallel backend raw run =="
echo "CPU root: $CPU_ROOT"
echo "Output directory: $OUT_DIR"
echo "Mesh: $MESH"

if [[ ! -f "$MESH" ]]; then
  echo "Mesh file does not exist: $MESH" >&2
  exit 1
fi

ELEMENT_CARDS="$(mesh_element_cards "$MESH")"
echo "$ELEMENT_CARDS"
if ! printf '%s\n' "$ELEMENT_CARDS" | grep -qi 'TYPE=C3D4'; then
  echo "WindHub mesh element type is not confirmed as C3D4. Stop before benchmark." >&2
  exit 1
fi

write_run_commands
write_platform_info

run cmake -S . -B build/cpu-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DPGSA_ENABLE_OPENMP=ON \
  -DBUILD_TESTS=ON \
  -DBUILD_BENCHMARKS=ON \
  -DPython3_EXECUTABLE=/usr/bin/python3

run cmake --build build/cpu-release --target symbolic_numeric_eval -j
run ctest --test-dir build/cpu-release --output-on-failure

run_omp python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe "$SYMBOLIC_EXE" \
  --out-root /tmp/pgsa_symbolic_backend_smoke \
  --mesh cube \
  --element tet4 \
  --nx 1 --ny 1 --nz 1 \
  --stiffness-model "$STIFFNESS_MODEL" \
  --assemblies-list 1 \
  --threads-list 1,2 \
  --backend-list "$BACKENDS" \
  --mode-list "$MODES" \
  --max-memory-gb "$MAX_MEMORY_GB"

run_omp python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe "$SYMBOLIC_EXE" \
  --out-root "$OUT_DIR/isolated_symbolic_memory" \
  --mesh inp \
  --inp "$MESH" \
  --case-name 3d-WindTurbineHub \
  --stiffness-model "$STIFFNESS_MODEL" \
  --assemblies-list 1 \
  --threads-range "$THREADS_RANGE" \
  --backend-list "$BACKENDS" \
  --mode-list "$MODES" \
  --max-memory-gb "$MAX_MEMORY_GB"

write_readme

run python3 scripts/verify_symbolic_parallel_backends_raw.py \
  --csv "$OUT_DIR/isolated_symbolic_memory/isolated_symbolic_memory.csv" \
  --threads-range "$THREADS_RANGE"

run tar -czf "$TARBALL" "$OUT_DIR"

echo "== Completed =="
echo "CSV: $OUT_DIR/isolated_symbolic_memory/isolated_symbolic_memory.csv"
echo "Metadata: $OUT_DIR/platform_info.txt"
echo "Commands: $OUT_DIR/run_commands.sh"
echo "Package: $TARBALL"
