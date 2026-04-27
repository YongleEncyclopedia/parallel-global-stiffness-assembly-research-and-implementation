# OPSX Tasks: gpu-stiffness-benchmark

## Zero-Decision Implementation Plan

> **Principle**: 每个任务都是纯机械执行，无需任何判断或决策。

---

## Phase 1: Code Modification

### TASK-01: Disable ScanAssembler
**Effort**: 5 min | **Dependencies**: None

**Exact Steps**:
1. Open `src/assembly/assembler_factory.cpp`
2. Locate function `get_available_algorithms()` (around line 50-60)
3. Comment out `AlgorithmType::PrefixScan` line
4. Add comment: `// DISABLED: incomplete two-phase implementation`
5. Save file

**Verification**:
```bash
grep -n "PrefixScan" src/assembly/assembler_factory.cpp
# Expected: Only commented line appears
```

---

## Phase 2: Build

### TASK-02: Build Project
**Effort**: 10 min | **Dependencies**: TASK-01

**Exact Steps**:
1. Open "x64 Native Tools Command Prompt for VS 2022/2026"
2. Navigate to project root:
   ```batch
   cd "D:\Intern_Peking University_supu\并行组装整体刚度矩阵\parallel_stiffness_assembly"
   ```
3. Execute build script:
   ```batch
   build_and_benchmark.bat
   ```
4. Wait for completion

**Verification**:
```batch
dir build\bin\benchmark_assembly.exe
# Expected: File exists, size > 0
```

**Fallback** (if build_and_benchmark.bat fails):
```batch
mkdir build && cd build
cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
nmake
cd ..
```

---

## Phase 3: Benchmark Execution

### TASK-03: Run Tiny Scale (6K DOFs)
**Effort**: 2 min | **Dependencies**: TASK-02

**Exact Command**:
```batch
build\bin\benchmark_assembly.exe 6 6 6 hex8
```

**Expected Output**: Algorithm table with 4 rows (CPU_Serial, Atomic, Block, WorkQueue)

---

### TASK-04: Run Small Scale (12K DOFs)
**Effort**: 2 min | **Dependencies**: TASK-02

**Exact Command**:
```batch
build\bin\benchmark_assembly.exe 10 10 10 hex8
```

---

### TASK-05: Run Medium Scale (120K DOFs)
**Effort**: 5 min | **Dependencies**: TASK-02

**Exact Command**:
```batch
build\bin\benchmark_assembly.exe 22 22 22 hex8
```

---

### TASK-06: Run Large Scale (600K DOFs)
**Effort**: 10 min | **Dependencies**: TASK-02

**Exact Command**:
```batch
build\bin\benchmark_assembly.exe 40 40 40 hex8
```

---

### TASK-07: Run XLarge Scale (1.2M DOFs)
**Effort**: 15 min | **Dependencies**: TASK-02

**Exact Command**:
```batch
build\bin\benchmark_assembly.exe 50 50 50 hex8
```

---

## Phase 4: Visualization

### TASK-08: Generate Charts
**Effort**: 2 min | **Dependencies**: TASK-03 ~ TASK-07

**Exact Command**:
```batch
python scripts\plot_benchmark_results.py
```

**Verification**:
```batch
dir results\figures\*.png results\figures\summary.md
# Expected: exec_time.png, speedup.png, scaling.png, summary.md
```

---

## Phase 5: Documentation Update

### TASK-09: Update Technical Report
**Effort**: 15 min | **Dependencies**: TASK-08

**Exact Steps**:
1. Open `docs/技术报告.md`
2. Locate "性能数据" section (around line 100-150)
3. Replace performance table with data from `benchmark_results.csv`
4. Update figure references to point to `results/figures/`
5. Update "测试日期" to current date (2026-01-30)
6. Save file

**Data Mapping**:
| CSV Column | Report Column |
|------------|---------------|
| Algorithm | 算法 |
| DOFs | 自由度数 |
| Time_ms | 时间(ms) |
| Speedup | 加速比 |
| Error | 误差 |

---

## Phase 6: Validation

### TASK-10: Verify All PBT Properties
**Effort**: 5 min | **Dependencies**: TASK-03 ~ TASK-07

**Checklist**:
- [ ] PBT-01: All GPU errors < 1e-10 ✓
- [ ] PBT-02: PrefixScan NOT in output ✓
- [ ] PBT-03: nnz consistent across algorithms ✓
- [ ] PBT-04: All speedups > 0 and finite ✓
- [ ] PBT-05: All DOFs divisible by 3 ✓
- [ ] PBT-06: Algorithm names match enum ✓
- [ ] PBT-07: 5 runs per benchmark ✓

**Verification Script** (optional):
```python
import pandas as pd
df = pd.read_csv('benchmark_results.csv')
assert 'Prefix_Scan' not in df['Algorithm'].values
assert all(df['Error'] < 1e-10)
assert all(df['DOFs'] % 3 == 0)
assert all(df['Speedup'] > 0)
print("All PBT properties PASS")
```

---

## Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 1. Code Mod | TASK-01 | 5 min |
| 2. Build | TASK-02 | 10 min |
| 3. Benchmark | TASK-03~07 | 34 min |
| 4. Visualize | TASK-08 | 2 min |
| 5. Docs | TASK-09 | 15 min |
| 6. Validate | TASK-10 | 5 min |
| **Total** | **10 tasks** | **~71 min** |

---

**Generated**: 2026-01-30
**Status**: Ready for Implementation
**Next Command**: `/ccg:spec-impl gpu-stiffness-benchmark`
