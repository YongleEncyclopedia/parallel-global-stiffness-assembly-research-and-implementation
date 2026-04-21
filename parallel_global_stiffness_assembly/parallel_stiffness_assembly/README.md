# GPU并行刚度矩阵组装性能测试项目

## 项目概述

本项目实现并对比了四种GPU并行算法用于有限元刚度矩阵组装，旨在评估在用户级主机（RTX 5080）上替代CPU串行算法的可行性。

### 实现的算法

1. **原子操作 + Warp聚合** (`Atomic_WarpAgg`) - 主力算法
2. **线程块并行** (`Block_Parallel`) - 共享内存优化
3. **前缀和分配** (`Prefix_Scan`) - 两阶段策略
4. **工作队列** (`Work_Queue`) - 动态负载均衡
5. **CPU串行** (`CPU_Serial`) - 基准参考

### 支持的单元类型

- Hex8 (8节点六面体)
- Tet4 (4节点四面体)

---

## 系统要求

### 硬件

- NVIDIA GPU (Compute Capability 8.0+)
- 推荐: RTX 30系列 / RTX 40系列 / RTX 50系列

### 软件

- CUDA Toolkit 13.1+
- CMake 3.25+
- C++17 编译器 (MSVC 2022 / GCC 10+ / Clang 12+)
- Python 3.8+ (用于脚本)
- Python 包: numpy, matplotlib, pandas, scipy

---

## 快速开始

### 一键构建和运行 (Windows)

```batch
build_and_run.bat
```

### 手动构建

```bash
# 1. 创建构建目录
mkdir build && cd build

# 2. 配置 CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# 3. 编译
cmake --build . --config Release

# 4. 运行基准测试
./bin/benchmark_assembly 20 20 20 hex8
```

### 使用 CMake Presets

```bash
cmake --preset default
cmake --build build/default
```

---

## 测试用例

### 生成测试网格

```bash
# 生成所有标准测试网格
python scripts/generate_mesh.py --all

# 生成指定规模的网格
python scripts/generate_mesh.py --type hex8 --dof 100000 -o data/meshes/hex8_100k.mesh
```

### 测试用例矩阵

| 单元类型 | 小型 (1万DOF) | 中型 (10万DOF) | 大型 (100万DOF) |
|---------|--------------|---------------|----------------|
| Hex8    | hex8_10k     | hex8_100k     | hex8_1M        |
| Tet4    | tet4_10k     | tet4_100k     | tet4_1M        |

---

## 运行基准测试

### 命令行参数

```
benchmark_assembly [nx] [ny] [nz] [element_type]

参数:
  nx, ny, nz    - 网格在各方向的单元数 (默认: 20 20 20)
  element_type  - 单元类型: hex8 或 tet4 (默认: hex8)

示例:
  benchmark_assembly 30 30 30 hex8    # 约 27000 个 Hex8 单元
  benchmark_assembly 50 50 50 tet4    # 约 750000 个 Tet4 单元
```

### 输出示例

```
========================================================
  GPU Parallel Stiffness Matrix Assembly Benchmark
========================================================

Generating mesh...
  Element type: Hex8
  Nodes: 9261
  Elements: 8000
  DOFs: 27783

Precomputing CSR structure...
  NNZ: 531441
  Memory: 6.08 MB

Running benchmarks...
           Algorithm       Elements          DOFs      Time (ms)        Speedup          Error         Status
-----------------------------------------------------------------------------------------------------------
          CPU_Serial           8000         27783         125.234           1.00       0.00e+00           PASS
       Atomic_WarpAgg          8000         27783           4.512          27.76       2.34e-15           PASS
      Block_Parallel           8000         27783           4.891          25.61       2.34e-15           PASS
        Prefix_Scan            8000         27783           5.123          24.44       2.34e-15           PASS
         Work_Queue            8000         27783           4.234          29.58       2.34e-15           PASS

Benchmark completed.
Results saved to benchmark_results.csv
```

---

## 可视化结果

```bash
# 生成性能图表
python scripts/visualize_results.py
```

生成的图表保存在 `results/figures/` 目录：

- `exec_time.png` - 执行时间对比图
- `speedup.png` - 加速比对比图
- `scaling.png` - 扩展性分析图
- `summary.md` - 结果摘要表格

---

## 项目结构

```
parallel_stiffness_assembly/
├── CMakeLists.txt          # 主构建脚本
├── CMakePresets.json       # CMake 预设
├── README.md               # 本文件
│
├── include/                # 头文件
│   ├── core/               # 核心数据结构
│   ├── assembly/           # 组装器接口
│   └── backends/           # 后端实现
│       ├── cpu/            # CPU 实现
│       └── cuda/           # CUDA 实现
│
├── src/                    # 源代码
│   ├── core/
│   ├── assembly/
│   └── backends/
│
├── apps/benchmark/         # 基准测试程序
├── tests/                  # 测试代码
├── scripts/                # Python 脚本
├── data/meshes/            # 测试网格数据
├── results/                # 测试结果
└── docs/                   # 文档
```

---

## 技术细节

### 数据结构

- **SoA (Structure of Arrays)**: 节点坐标分离存储，优化 GPU 内存访问
- **CSR (Compressed Sparse Row)**: 稀疏矩阵存储格式，预计算结构
- **行内二分查找**: CSR 列索引查找，O(log n) 复杂度

### 算法设计

1. **原子操作 + Warp聚合**
   - 每线程处理一个单元
   - Warp 内预规约减少原子冲突
   - 适用于通用场景

2. **线程块并行**
   - 利用共享内存累加
   - 块内同步后批量写入
   - 适用于小型局部矩阵

3. **前缀和分配**
   - 两阶段：计数 + 填值
   - 无冲突写入
   - 内存开销较大

4. **工作队列**
   - 动态任务分配
   - 解决负载不均问题
   - 适用于混合单元类型

---

## 性能基准

（待实际测试后填充）

| 算法 | 10K DOF | 100K DOF | 1M DOF | 备注 |
|-----|---------|----------|--------|------|
| CPU Serial | - ms | - ms | - ms | 基准 |
| Atomic | - ms | - ms | - ms | **推荐** |
| Block | - ms | - ms | - ms | |
| Scan | - ms | - ms | - ms | |
| WorkQueue | - ms | - ms | - ms | |

---

## 常见问题

### Q: 编译时找不到 CUDA

**A**: 确保 CUDA Toolkit 已安装，并使用 x64 Native Tools Command Prompt for VS 2022

### Q: 运行时 CUDA 错误

**A**: 检查 GPU 驱动版本是否与 CUDA Toolkit 兼容

### Q: 结果误差过大

**A**: 检查 CSR 结构预计算是否正确，确认列索引已排序

---

## 许可证

MIT License

---

## 参考文献

1. Cecka, Lew, & Darve. "Assembly of finite element methods on graphics processors", IJNME, 2011.
2. Markall et al. "Finite element assembly strategies on multi- and many-core architectures", IJNMF, 2013.
