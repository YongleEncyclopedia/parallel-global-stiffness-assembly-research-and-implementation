# GPU并行刚度矩阵组装项目实施计划

**创建日期**: 2026-01-29
**硬件环境**: NVIDIA RTX 5080 (16GB, Compute 12.0), CUDA 13.1
**项目路径**: `D:/Intern_Peking University_supu/并行组装整体刚度矩阵`

---

## 1. 项目目录结构

```
parallel_stiffness_assembly/
├── CMakeLists.txt                    # 主构建脚本
├── CMakePresets.json                 # CMake预设配置
├── vcpkg.json                        # 依赖清单
├── README.md                         # 项目说明
│
├── cmake/
│   ├── CudaConfig.cmake              # CUDA编译配置
│   ├── CompilerFlags.cmake           # 编译器选项
│   └── Dependencies.cmake            # 依赖查找
│
├── include/
│   ├── core/
│   │   ├── types.h                   # 基础类型定义
│   │   ├── mesh.h                    # 网格数据结构
│   │   ├── dof_map.h                 # 自由度映射
│   │   ├── csr_matrix.h              # CSR稀疏矩阵
│   │   └── soa.h                     # SoA内存布局
│   │
│   ├── assembly/
│   │   ├── assembler_interface.h     # IAssembler抽象接口
│   │   ├── assembler_factory.h       # 工厂类
│   │   └── assembly_options.h        # 配置选项
│   │
│   └── backends/
│       ├── cuda/
│       │   ├── cuda_utils.cuh        # CUDA辅助宏/函数
│       │   ├── atomic_assembler.h    # 原子操作+Warp聚合
│       │   ├── block_assembler.h     # 线程块并行
│       │   ├── scan_assembler.h      # 前缀和分配
│       │   └── workqueue_assembler.h # 工作队列
│       └── cpu/
│           └── serial_assembler.h    # CPU串行基线
│
├── src/
│   ├── core/
│   │   ├── mesh.cpp
│   │   ├── dof_map.cpp
│   │   └── csr_matrix.cpp
│   │
│   ├── assembly/
│   │   ├── assembler_factory.cpp
│   │   └── assembly_options.cpp
│   │
│   └── backends/
│       ├── cuda/
│       │   ├── atomic_assembler.cu   # 算法1: 原子+Warp聚合
│       │   ├── block_assembler.cu    # 算法2: 线程块并行
│       │   ├── scan_assembler.cu     # 算法3: 前缀和
│       │   └── workqueue_assembler.cu# 算法4: 工作队列
│       └── cpu/
│           └── serial_assembler.cpp
│
├── apps/
│   └── benchmark/
│       └── main.cpp                  # 性能测试主程序
│
├── tests/
│   ├── unit/                         # 单元测试
│   │   ├── test_mesh.cpp
│   │   ├── test_csr.cpp
│   │   └── test_assemblers.cpp
│   └── correctness/                  # 正确性验证
│       └── verify_results.cpp
│
├── scripts/
│   ├── generate_structured_mesh.py              # 网格生成脚本
│   ├── run_benchmarks.py             # 自动化测试脚本
│   ├── plot_benchmark_results.py          # 可视化脚本
│   └── generate_report.py            # 报告生成脚本
│
├── data/
│   └── meshes/                       # 测试网格文件
│
├── results/                          # 测试结果
│   ├── raw/                          # 原始数据
│   └── figures/                      # 生成图表
│
└── docs/
    ├── report_template.md            # 报告模板
    └── technical_notes.md            # 技术说明
```

---

## 2. 核心数据结构设计

### 2.1 SoA节点坐标布局
```cpp
struct NodeCoordinates {
    std::vector<double> x;  // [num_nodes]
    std::vector<double> y;  // [num_nodes]
    std::vector<double> z;  // [num_nodes]
};

// GPU端
struct DeviceNodeCoordinates {
    double* d_x;
    double* d_y;
    double* d_z;
    size_t num_nodes;
};
```

### 2.2 CSR矩阵结构
```cpp
struct CsrMatrix {
    std::vector<int> row_ptr;    // [num_rows + 1]
    std::vector<int> col_ind;    // [nnz]
    std::vector<double> values;  // [nnz]

    size_t num_rows;
    size_t num_cols;
    size_t nnz;

    // 行内二分查找
    int find_col_index(int row, int col) const;
};
```

### 2.3 单元连接表
```cpp
// Hex8: 每单元8节点
struct Hex8Connectivity {
    std::vector<int> conn;  // [num_elements * 8]
    size_t num_elements;
};

// Tet4: 每单元4节点
struct Tet4Connectivity {
    std::vector<int> conn;  // [num_elements * 4]
    size_t num_elements;
};
```

### 2.4 统一Mesh接口
```cpp
class Mesh {
public:
    enum class ElementType { Hex8, Tet4 };

    NodeCoordinates nodes;
    ElementType element_type;

    // 根据类型返回对应连接表
    const int* get_connectivity() const;
    int nodes_per_element() const;
    int dofs_per_element() const;  // Hex8: 24, Tet4: 12
    size_t num_elements() const;
    size_t num_nodes() const;
    size_t num_dofs() const;  // num_nodes * 3
};
```

---

## 3. 算法接口设计

### 3.1 IAssembler抽象接口
```cpp
class IAssembler {
public:
    virtual ~IAssembler() = default;

    // 配置
    virtual void set_mesh(const Mesh& mesh) = 0;
    virtual void set_csr_structure(const CsrMatrix& csr) = 0;

    // 核心操作
    virtual void prepare() = 0;   // 预处理（如GPU内存分配）
    virtual void assemble() = 0;  // 执行组装
    virtual void cleanup() = 0;   // 资源释放

    // 结果获取
    virtual const CsrMatrix& get_result() const = 0;
    virtual double get_assembly_time_ms() const = 0;
    virtual size_t get_memory_usage_bytes() const = 0;

    // 算法信息
    virtual std::string get_name() const = 0;
};
```

### 3.2 工厂类
```cpp
enum class AlgorithmType {
    Atomic,      // 原子操作+Warp聚合
    Block,       // 线程块并行
    PrefixScan,  // 前缀和分配
    WorkQueue,   // 工作队列
    CpuSerial    // CPU串行基线
};

class AssemblerFactory {
public:
    static std::unique_ptr<IAssembler> create(
        AlgorithmType algorithm,
        const AssemblyOptions& options
    );
};
```

---

## 4. 四类CUDA算法实现要点

### 4.1 算法1: 原子操作 + Warp聚合（主力算法）

**核心思想**: 每线程处理一个单元，计算局部刚度矩阵后通过Warp内聚合减少原子操作冲突

**关键技术**:
- `__match_any_sync()` 检测Warp内写入同一地址的线程
- `__shfl_down_sync()` 进行Warp内部值累加
- Leader线程执行最终 `atomicAdd()`
- CSR列索引使用行内二分查找

**预期性能**: 最高，RTX 5080 Blackwell架构原子单元优化充分

### 4.2 算法2: 线程块并行

**核心思想**: 每个Thread Block负责一批单元，利用共享内存进行块内累加

**关键技术**:
- 共享内存缓冲局部矩阵贡献
- Block内同步 `__syncthreads()`
- 批量写回全局CSR

**适用场景**: Tet4等局部矩阵较小的单元（共享内存容量限制）

### 4.3 算法3: 前缀和分配

**核心思想**: 两阶段策略——先统计写入量分配位置，再无冲突填值

**关键技术**:
- Kernel 1: 统计每单元对CSR的写入数量
- 前缀和（Thrust `exclusive_scan`）分配写入偏移
- Kernel 2: 并行填值（无原子操作）

**特点**: 冲突最小，但内存开销和kernel启动次数较高

### 4.4 算法4: 工作队列动态负载均衡

**核心思想**: 任务队列驱动，处理Hex8/Tet4混合网格的负载不均问题

**关键技术**:
- 全局任务队列（原子计数器 + 任务数组）
- 每个Warp/Block动态领取任务
- 任务粒度可配置（单元级/行块级）

**适用场景**: 混合单元类型、非结构化网格

---

## 5. 测试框架设计

### 5.1 测试用例矩阵

| 单元类型 | 小型(1万DOF) | 中型(10万DOF) | 大型(100万DOF) |
|---------|-------------|--------------|---------------|
| Hex8    | hex8_10k    | hex8_100k    | hex8_1M       |
| Tet4    | tet4_10k    | tet4_100k    | tet4_1M       |

### 5.2 性能指标
- **组装时间**: CUDA Event计时（不含数据传输）
- **内存使用**: `cudaMemGetInfo()` 峰值
- **GPU利用率**: Nsight Compute SM Occupancy
- **正确性**: 与CPU基线的Frobenius范数相对误差 < 1e-6

### 5.3 可视化输出
- 执行时间对比图（分组条形图，对数坐标）
- 加速比对比图（相对于CPU串行）
- GPU内核耗时分布饼图

---

## 6. 实施任务分解

### 阶段1: 项目框架搭建 [预计4小时]
- [ ] 1.1 创建目录结构
- [ ] 1.2 配置CMake构建系统（CUDA 13.1, RTX 5080）
- [ ] 1.3 实现核心数据结构（Mesh, CsrMatrix, SoA）
- [ ] 1.4 实现CPU串行基线算法
- [ ] 1.5 实现网格生成脚本

### 阶段2: CUDA算法实现 [预计6小时]
- [ ] 2.1 实现算法1: 原子操作+Warp聚合
- [ ] 2.2 实现算法2: 线程块并行
- [ ] 2.3 实现算法3: 前缀和分配
- [ ] 2.4 实现算法4: 工作队列

### 阶段3: 测试与验证 [预计3小时]
- [ ] 3.1 实现正确性验证模块
- [ ] 3.2 实现自动化测试脚本
- [ ] 3.3 执行全部测试用例
- [ ] 3.4 收集性能数据

### 阶段4: 可视化与报告 [预计2小时]
- [ ] 4.1 实现可视化脚本
- [ ] 4.2 生成性能图表
- [ ] 4.3 撰写技术报告

---

## 7. 关键依赖

### 必需
- CUDA Toolkit 13.1+（需安装）
- CMake 3.25+（需安装）
- Python 3.8+（已有）
- C++17编译器（MSVC 2022）

### 推荐（通过vcpkg安装）
- Eigen3（矩阵运算）
- fmt（格式化输出）
- spdlog（日志）
- googletest（单元测试）

### Python包
- numpy
- matplotlib
- pandas
- scipy

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| CUDA Toolkit未安装 | 无法编译 | 首先安装CUDA 13.1 |
| CMake未安装 | 无法构建 | 安装CMake 3.25+ |
| 100万DOF显存不足 | 大规模测试失败 | 分批处理/动态规模调整 |
| Warp聚合在Blackwell架构行为变化 | 性能不如预期 | 准备fallback到普通原子 |

---

## 9. 成功标准

1. ✅ 4类算法全部实现且通过正确性验证
2. ✅ 至少一种GPU算法相对CPU达到20x+加速比
3. ✅ 生成完整的中文技术报告
4. ✅ 一键运行脚本可复现所有结果
