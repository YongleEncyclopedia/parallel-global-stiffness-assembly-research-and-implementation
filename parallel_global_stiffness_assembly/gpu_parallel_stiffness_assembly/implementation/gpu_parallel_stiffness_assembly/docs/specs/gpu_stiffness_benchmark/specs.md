# OPSX Specs: gpu-stiffness-benchmark

## 1. Requirements

### 1.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 禁用 ScanAssembler，从 AssemblerFactory 移除 PrefixScan | P0 | 待实施 |
| FR-02 | 支持五规模测试: 6K / 12K / 120K / 600K / 1.2M DOFs | P0 | 待实施 |
| FR-03 | GPU 算法结果与 CPU 串行基线误差 < 1e-10 | P0 | 验证中 |
| FR-04 | 生成 benchmark_results.csv 包含完整数据 | P0 | 已实现 |
| FR-05 | 生成可视化图表: exec_time.png, speedup.png, scaling.png | P1 | 已实现 |
| FR-06 | 更新技术报告性能数据部分 | P1 | 待实施 |

### 1.2 Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-01 | GPU 加速比 | Speedup vs CPU | > 10x |
| NFR-02 | 大规模组装时间 | 1.2M DOFs | < 100ms |
| NFR-03 | 数值精度 | Relative Error | < 1e-10 |
| NFR-04 | 内存使用 | 线性增长 | O(n) |

---

## 2. PBT Properties (Code-Level)

### PBT-01: Numerical Correctness Invariant
- **Category**: invariant
- **Invariant**: 在所有规模下，Atomic_WarpAgg、Block、WorkQueue 的组装结果相对误差必须 < 1e-10
- **Falsification**: 针对每个规模分别生成 Hex8/Tet4 网格，运行 CPU 与三种 GPU 算法，计算相对误差
- **Boundary**: 最小 6K DOFs，最大 1.2M DOFs；Hex8 与 Tet4
- **Related Code**: `apps/benchmark/main.cpp:30`

### PBT-02: Algorithm Exclusion Invariant
- **Category**: invariant
- **Invariant**: 基准测试算法集合必须排除 PrefixScan，仅包含 CPU_Serial、Atomic、Block、WorkQueue
- **Falsification**: 读取算法列表并检查是否包含 PrefixScan
- **Boundary**: 所有规模与元素类型
- **Related Code**: `src/assembly/assembler_factory.cpp:53`

### PBT-03: CSR Structure Consistency
- **Category**: invariant
- **Invariant**: GPU 结果的 CSR 结构必须与 CPU 参考结构一致（nnz 相同）
- **Falsification**: 对不同规模/元素类型运行 CPU 与 GPU，若 nnz 不一致则为反例
- **Boundary**: 稀疏度极高或极低的网格
- **Related Code**: `apps/benchmark/main.cpp:30`

### PBT-04: Speedup Bounds
- **Category**: bounds
- **Invariant**: Speedup 必须为有限正数（cpu_time_ms > 0 且 avg_time > 0）
- **Falsification**: 构造异常计时场景，检查 speedup 是否非正或非有限
- **Boundary**: 极小规模导致计时分辨率不足；极大规模导致溢出或超时
- **Related Code**: `apps/benchmark/main.cpp:169`

### PBT-05: DOFs Divisibility
- **Category**: bounds
- **Invariant**: DOFs 必须是 3 的整数倍（DOFS_PER_NODE=3）
- **Falsification**: 随机生成网格规模并校验 mesh.num_dofs() % 3 == 0
- **Boundary**: 最小网格（1x1x1）与最大规模（1.2M DOFs）
- **Related Code**: `include/core/types.h:31`

### PBT-06: Algorithm Name Consistency
- **Category**: invariant
- **Invariant**: 基准测试输出的算法名称必须与 AlgorithmType 映射一致
- **Falsification**: 读取输出/CSV 中的 Algorithm 字段，与 algorithm_to_string 映射对比
- **Boundary**: 所有算法与所有规模
- **Related Code**: `include/core/types.h:102`

### PBT-07: Benchmark Iterations
- **Category**: invariant
- **Invariant**: 每个算法的平均时间必须基于 5 次基准运行，预热 2 次
- **Falsification**: 验证 assemble 调用次数是否为 warmup_runs + benchmark_runs
- **Boundary**: 所有规模与元素类型
- **Related Code**: `include/assembly/assembly_options.h:35`

---

## 3. PBT Properties (System-Level)

### SYS-01: Correctness Invariance
- **Property**: 任何有效网格上，所有启用的 GPU 算法组装结果必须与 CPU_Serial 等价（误差 < 1e-6）
- **Boundary**: 极小网格(1-8元素)、极大网格(>1M DOFs)、高长宽比、Hex8/Tet4
- **Counterexample**: 生成随机网格，计算 GPU vs CPU 相对误差，超过阈值即为反例

### SYS-02: Monotonic Time Complexity
- **Property**: 问题规模增大时，执行时间必须非递减
- **Boundary**: 跨越 L2 缓存容量、GPU 显存容量的规模
- **Counterexample**: 若大规模时间 < 小规模时间，即为反例

### SYS-03: Non-decreasing Speedup
- **Property**: GPU 加速比随问题规模增大应保持或增加
- **Boundary**: 小→中、中→大规模过渡点
- **Counterexample**: 若大规模加速比 < 小规模加速比，即为反例

### SYS-04: Output Artifact Integrity
- **Property**: 完整执行后必须生成所有输出文件且非空
- **Files**: benchmark_results.csv, exec_time.png, speedup.png, scaling.png, summary.md
- **Counterexample**: 任何文件缺失或为空即为反例

### SYS-05: CSV Schema Integrity
- **Property**: CSV 必须包含正确表头和 7 列数据，类型正确
- **Header**: Algorithm,Elements,DOFs,Time_ms,Speedup,Error,Status
- **Counterexample**: 列数不对、类型解析失败即为反例

---

## 4. Constraints Summary

### Hard Constraints
| ID | Constraint | Source |
|----|------------|--------|
| HC-01 | CUDA Toolkit ≥ 13.1 | CMakeLists.txt |
| HC-02 | Compute Capability ≥ 7.0 | cuda_utils.cuh |
| HC-03 | C++17 Standard | CMakeLists.txt |
| HC-04 | CSR Structure Precomputed | assembler_interface.h |
| HC-05 | DoFs/node = 3 (fixed) | types.h |
| HC-06 | Sorted Column Indices | csr_matrix.cpp |

### Soft Constraints (User Decisions)
| ID | Decision | Value |
|----|----------|-------|
| SD-01 | ScanAssembler | **Disabled** |
| SD-02 | Test Scales | **5 (6K/12K/120K/600K/1.2M)** |
| SD-03 | Build Scripts | **Keep as-is** |
| SD-04 | Tech Report | **Update data only** |

---

**Generated**: 2026-01-30
**Status**: Ready for Design
