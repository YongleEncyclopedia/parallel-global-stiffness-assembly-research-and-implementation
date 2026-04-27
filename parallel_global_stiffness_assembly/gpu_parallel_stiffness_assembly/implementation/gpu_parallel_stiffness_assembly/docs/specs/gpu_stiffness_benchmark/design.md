# OPSX Design: gpu-stiffness-benchmark

## 1. Technical Decisions

### 1.1 Algorithm Selection

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Algorithm | **Atomic_WarpAgg** | 最高加速比 (47.2x @ 1.2M DOFs)，实现简洁 |
| Secondary Algorithm | **WorkQueue** | 动态负载均衡，适用于不均匀网格 |
| Tertiary Algorithm | **Block** | 线程块并行，中等性能 |
| **Disabled** | ~~PrefixScan~~ | 实现不完整，行为与 Atomic 相同 |

### 1.2 Test Configuration

```yaml
benchmark:
  scales:
    - name: "tiny"
      nx: 6
      ny: 6
      nz: 6
      approx_dofs: 6K
    - name: "small"
      nx: 10
      ny: 10
      nz: 10
      approx_dofs: 12K
    - name: "medium"
      nx: 22
      ny: 22
      nz: 22
      approx_dofs: 120K
    - name: "large"
      nx: 40
      ny: 40
      nz: 40
      approx_dofs: 600K
    - name: "xlarge"
      nx: 50
      ny: 50
      nz: 50
      approx_dofs: 1.2M

  warmup_runs: 2
  benchmark_runs: 5
  element_type: hex8  # primary, tet4 as secondary
```

### 1.3 Build Configuration

```cmake
# Fixed settings
CMAKE_CUDA_ARCHITECTURES: "86;89;120"
CMAKE_CXX_STANDARD: 17
CMAKE_CUDA_STANDARD: 17
BUILD_TESTS: ON
BUILD_BENCHMARKS: ON

# NVCC flags
-allow-unsupported-compiler  # For VS 2026 compatibility
--expt-relaxed-constexpr
--extended-lambda
-lineinfo
```

### 1.4 Precision Configuration

```cpp
// Validation thresholds
constexpr double RELATIVE_ERROR_TOLERANCE = 1e-10;
constexpr double NEAR_ZERO_THRESHOLD = 1e-15;
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     benchmark_assembly                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ CLI Parser  │→│ Mesh Gen    │→│ CSR Precompute      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              AssemblerFactory                          │ │
│  │  ┌──────────┐ ┌───────┐ ┌───────────┐                │ │
│  │  │ CPU_Ser  │ │Atomic │ │  Block    │ [Scan:OFF]    │ │
│  │  └──────────┘ └───────┘ └───────────┘ ┌──────────┐  │ │
│  │                                       │WorkQueue │   │ │
│  │                                       └──────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Timing      │→│ CSV Output  │→│ Error Calculation   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 plot_benchmark_results.py                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ CSV Parser  │→│ Plotting    │→│ Summary Gen         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│        ↓                ↓                    ↓              │
│  [exec_time.png] [speedup.png] [scaling.png] [summary.md]   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. File Changes

### 3.1 Modified Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/assembly/assembler_factory.cpp` | MODIFY | 移除 PrefixScan 从 get_available_algorithms() |
| `apps/benchmark/main.cpp` | MODIFY | 添加 5 规模测试支持，更新默认参数 |
| `docs/技术报告.md` | MODIFY | 更新性能数据表格和图表引用 |

### 3.2 Generated Files (No Manual Edit)

| File | Generator | Content |
|------|-----------|---------|
| `benchmark_results.csv` | benchmark_assembly | 测试数据 |
| `results/figures/exec_time.png` | plot_benchmark_results.py | 执行时间图 |
| `results/figures/speedup.png` | plot_benchmark_results.py | 加速比图 |
| `results/figures/scaling.png` | plot_benchmark_results.py | 扩展性图 |
| `results/figures/summary.md` | plot_benchmark_results.py | 摘要表 |

---

## 4. Code Changes (Exact Specifications)

### 4.1 Disable ScanAssembler

**File**: `src/assembly/assembler_factory.cpp`

**Before**:
```cpp
std::vector<AlgorithmType> AssemblerFactory::get_available_algorithms() {
    return {
        AlgorithmType::CpuSerial,
        AlgorithmType::Atomic,
        AlgorithmType::Block,
        AlgorithmType::PrefixScan,
        AlgorithmType::WorkQueue
    };
}
```

**After**:
```cpp
std::vector<AlgorithmType> AssemblerFactory::get_available_algorithms() {
    return {
        AlgorithmType::CpuSerial,
        AlgorithmType::Atomic,
        AlgorithmType::Block,
        // AlgorithmType::PrefixScan,  // DISABLED: incomplete two-phase implementation
        AlgorithmType::WorkQueue
    };
}
```

### 4.2 Five-Scale Test Support

**File**: `apps/benchmark/main.cpp`

**Add constant**:
```cpp
// Test scales for comprehensive benchmarking
const std::vector<std::tuple<int, int, int, std::string>> TEST_SCALES = {
    {6, 6, 6, "tiny"},      // ~6K DOFs
    {10, 10, 10, "small"},  // ~12K DOFs
    {22, 22, 22, "medium"}, // ~120K DOFs
    {40, 40, 40, "large"},  // ~600K DOFs
    {50, 50, 50, "xlarge"}  // ~1.2M DOFs
};
```

---

## 5. Validation Criteria

### 5.1 Build Success
- [ ] CMake configure exits with code 0
- [ ] `fem_core.lib` generated
- [ ] `fem_assembly.lib` generated
- [ ] `benchmark_assembly.exe` generated

### 5.2 Functional Correctness
- [ ] Atomic vs CPU: error < 1e-10
- [ ] Block vs CPU: error < 1e-10
- [ ] WorkQueue vs CPU: error < 1e-10
- [ ] PrefixScan NOT in algorithm list

### 5.3 Performance Targets
- [ ] Speedup > 10x at 12K DOFs
- [ ] Speedup > 20x at 120K DOFs
- [ ] Speedup > 40x at 1.2M DOFs

### 5.4 Output Artifacts
- [ ] benchmark_results.csv exists and valid schema
- [ ] exec_time.png exists and non-empty
- [ ] speedup.png exists and non-empty
- [ ] scaling.png exists and non-empty
- [ ] summary.md exists and contains table

---

**Generated**: 2026-01-30
**Status**: Ready for Tasks
