# GPU并行刚-度矩阵组装测试框架与可视化方案设计

## 1. 测试框架设计方案

### 1.1. 总体架构

测试框架基于脚本自动化，通过配置文件驱动，实现数据生成、测试执行、结果收集与正确性验证的全流程管理。

```
/project_root
├── /src                    # 4类并行算法的CUDA源码
├── /bin                    # 编译后的可执行文件
│   ├── algo1_hex8.exe
│   ├── algo1_tet4.exe
│   ├── algo2_hex8.exe
│   └── ...
├── /cpu_baseline           # CPU串行组装基线程序（用于正确性验证和加速比计算）
├── /test_framework
│   ├── generate_structured_mesh.py    # 网格数据生成脚本
│   ├── run_tests.py        # 测试执行主脚本
│   ├── config.json         # 测试配置文件
│   ├── /results            # 存放原始测试数据的目录
│   └── /visualizations     # 存放生成图表的目录
├── /meshes                 # 统一生成的网格输入数据
│   ├── hex8_10k.mesh
│   ├── hex8_100k.mesh
│   ├── hex8_1M.mesh
│   ├── tet4_10k.mesh
│   └── ...
└── README.md               # 项目说明与使用指南
```

### 1.2. 统一输入数据生成

- **脚本:** `test_framework/generate_structured_mesh.py`
- **功能:**
    - 接收单元类型（`hex8`, `tet4`）和目标自由度（1万, 10万, 100万）作为参数。
    - 生成结构化立方体网格。
    - 输出格式为简单的文本文件 (`.mesh`)，包含节点坐标和单元连接关系，确保所有算法使用完全一致的输入。
- **示例:** `python generate_structured_mesh.py --type hex8 --dof 10000 --output ../meshes/hex8_10k.mesh`

### 1.3. 自动化测试执行

- **核心脚本:** `test_framework/run_tests.py`
- **配置文件:** `test_framework/config.json`，定义所有测试组合。

**`config.json` 示例:**
```json
{
  "global_settings": {
    "repetitions": 5, // 每项测试重复5次，取平均值
    "warmup_runs": 2  // 预热运行次数
  },
  "test_cases": [
    { "name": "algo1_hex8_10k", "executable": "algo1_hex8.exe", "mesh": "hex8_10k.mesh" },
    { "name": "algo1_hex8_100k", "executable": "algo1_hex8.exe", "mesh": "hex8_100k.mesh" },
    { "name": "algo1_hex8_1M", "executable": "algo1_hex8.exe", "mesh": "hex8_1M.mesh" },
    { "name": "algo2_hex8_10k", "executable": "algo2_hex8.exe", "mesh": "hex8_10k.mesh" },
    // ... all other combinations for hex8, tet4, and all 4 algorithms
  ]
}
```

- **执行流程:**
    1. 脚本读取 `config.json`。
    2. 遍历 `test_cases`，对每一项执行：
        a. **预热:** 运行可执行文件 `warmup_runs` 次。
        b. **正式测试:**
           - 使用 `nvprof` 或 `nsight compute` 包裹可执行文件，重复 `repetitions` 次。
           - `nsight compute --csv --metrics sm__cycles_elapsed.avg.per_second,dram__bytes_read.sum,dram__bytes_write.sum ./algo1_hex8.exe ../meshes/hex8_10k.mesh`
           - 解析程序标准输出，获取**组装时间**和**内存使用**。
           - `nvprof/nsight` 的输出用于后续的GPU利用率和内核分析。
    3. **结果存储:** 将所有性能指标（组装时间、内存、GPU指标）和测试配置一起保存为CSV文件，例如 `results/summary_YYYYMMDD_HHMMSS.csv`。

### 1.4. 性能指标与正确性验证

- **组装时间 (ms):** 由各个算法程序内部通过CUDA event计时，并输出到控制台。
- **内存使用 (MB):** 使用`cudaMemGetInfo`获取GPU内存占用，程序结束前输出。
- **GPU利用率 (%):** 从 `nsight compute` 结果中提取 `sm__cycles_elapsed.avg.per_second` (SM利用率) 等指标。
- **正确性验证:**
    1. **生成基准:** 使用 `cpu_baseline` 程序对每个 `.mesh` 文件生成一个`.mtx` (Matrix Market format) 格式的稀疏矩阵文件作为基准。
    2. **GPU结果输出:** 每个GPU程序在组装完成后，也将结果矩阵转储为 `.mtx` 格式。
    3. **比对:** 在测试脚本中，使用Python (`scipy.sparse`) 读取基准矩阵 `A_cpu` 和GPU生成的矩阵 `A_gpu`。
    4. **计算误差:** 计算弗罗贝尼乌斯范数 `norm(A_gpu - A_cpu) / norm(A_cpu)`。若小于阈值 (如 `1e-6`)，则认为结果正确。
    5. **记录结果:** 将误差和“通过/失败”状态记录到最终的CSV结果文件中。

---

## 2. 可视化方案设计

- **工具:** Python (Matplotlib, Seaborn, Pandas)
- **脚本:** `test_framework/plot_benchmark_results.py`
- **输入:** `results/summary_*.csv` 文件
- **输出:** PNG格式的图表，保存在 `visualizations/` 目录下。

### 2.1. 执行时间对比图

- **图表类型:** 分组条形图。
- **X轴:** 自由度规模 (1万, 10万, 100万)。
- **Y轴:** 平均执行时间 (ms, 对数坐标)。
- **分组:** 4种不同的并行算法。
- **规范:**
    - 为 `Hex8` 和 `Tet4` 单元分别生成一张图。
    - 图表标题明确（如“Hex8单元执行时间对比”）。
    - 包含图例，清晰标注算法名称。

### 2.2. 加速比对比图

- **定义:** 加速比 = `CPU串行组装时间` / `GPU并行组装时间`。
- **图表类型:** 分组条形图。
- **X轴:** 自由度规模。
- **Y轴:** 加速比 (Speedup)。
- **分组:** 4种不同的并行算法。
- **规范:**
    - 同上，为 `Hex8` 和 `Tet4` 分别生成图表。
    - 图表标题明确（如“Tet4单元加速比对比”）。

### 2.3. GPU内核分析可视化

- **数据源:** `nsight compute` 生成的CSV报告。
- **可视化:**
    - **数据表:** 生成一个Markdown或CSV表格，总结关键内核的性能。
        - **行:** 主要的CUDA Kernel。
        - **列:** `Kernel Name`, `Calls`, `Avg Duration (us)`, `DRAM Read (GB/s)`, `DRAM Write (GB/s)`, `SM Occupancy (%)`。
    - **饼图:** 对于某个特定的大规模算例（如`algo1_hex8_1M`），展示其运行耗时最长的Top 5内核的时间占比。

### 2.4. 正确性验证摘要

- **形式:** 在测试报告的开头部分生成一个Markdown表格。
- **内容:**
    - **行:** 每个测试用例。
    - **列:** `Test Case Name`, `Correctness Status`, `Relative Error`。
    - **示例:**

| 测试用例         | 正确性状态 | 相对误差    |
|------------------|------------|-------------|
| algo1_hex8_10k   | ✅ 通过     | 1.23e-7     |
| algo1_hex8_100k  | ✅ 通过     | 2.45e-7     |
| algo2_tet4_1M    | ❌ 失败     | 5.67e-2     |

---

## 3. 测试报告模板框架 (中文)

**文件名:** `GPU并行组装算法性能评测报告_YYYYMMDD.md`

```markdown
# GPU并行刚度矩阵组装四种并行算法性能评测报告

**日期:** YYYY年MM月DD日
**硬件环境:** NVIDIA RTX 5080 (16GB)
**软件环境:** CUDA 13.1, Driver X.X

## 1. 摘要

本报告旨在评测四种不同的GPU并行算法在刚度矩阵组装任务上的性能。测试涵盖了六面体（Hex8）和四面体（Tet4）两种单元类型，以及三种不同问题规模（1万、10万、100万自由度）。报告从执行时间、加速比、内存使用和GPU内核效率等维度对算法进行了全面的分析与比较。

## 2. 测试设计与环境

### 2.1. 硬件与软件环境
- **GPU:** NVIDIA RTX 5080 (16GB显存)
- **CPU:** [填写CPU型号]
- **操作系统:** [填写操作系统]
- **CUDA版本:** 13.1

### 2.2. 测试用例
- **单元类型:** Hex8, Tet4
- **自由度规模:** 1万 (小型), 10万 (中型), 100万 (大型)

### 2.3. 评测指标
- **执行时间:** 完成矩阵组装所需的壁钟时间（ms）。
- **加速比:** 相对于[CPU基准程序名]的单线程执行时间的性能提升倍数。
- **内存占用:** GPU显存的峰值占用（MB）。
- **正确性:** 与CPU基准结果的相对误差。

## 3. 测试结果与分析

### 3.1. 正确性验证

| 测试用例         | 正确性状态 | 相对误差 |
|------------------|------------|----------|
| ...              | ...        | ...      |

*所有算法均通过正确性验证，误差在可接受范围内。*

### 3.2. 执行时间分析

**图1: Hex8单元不同规模下各算法执行时间对比 (对数坐标)**
![Hex8执行时间](./visualizations/exec_time_hex8.png)

**图2: Tet4单元不同规模下各算法执行时间对比 (对数坐标)**
![Tet4执行时间](./visualizations/exec_time_tet4.png)

*分析:* 从图中可以看出，算法A在所有规模下表现最优... 算法B在小规模时有优势，但在大规模下扩展性不佳...

### 3.3. 加速比分析

**图3: Hex8单元加速比对比**
![Hex8加速比](./visualizations/speedup_hex8.png)

**图4: Tet4单元加速比对比**
![Tet4加速比](./visualizations/speedup_tet4.png)

*分析:* 算法A在百万自由度规模下取得了最高XX倍的加速比...

### 3.4. GPU资源利用率分析 (以百万自由度Hex8单元为例)

**表1: 算法A关键内核性能指标**
| Kernel Name | Avg Duration (us) | SM Occupancy (%) |
|-------------|-------------------|------------------|
| ...         | ...               | ...              |

**图5: 算法A核心内核耗时占比**
![Kernel耗时占比](./visualizations/kernel_pie_chart_algoA_hex8_1M.png)

*分析:* 算法A的主要瓶颈在于`some_kernel`，其占据了总时间的XX%... 算法B的SM Occupancy较低，可能存在指令延迟或线程束发散问题...

## 4. 结论

综合所有测试结果，我们的结论如下：
- **性能最优算法:** 算法A在扩展性和绝对性能上均表现最佳。
- **资源效率:** 算法C虽然速度不是最快，但其GPU资源利用率最高，最具进一步优化的潜力。
- **适用场景:** 对于中小规模问题，算法B的实现简单且性能可接受。对于追求极致性能的大规模计算，推荐使用算法A。

```

---

## 4. 用户体验与可复现性设计

### 4.1. README 结构

**`README.md`**
```markdown
# GPU Parallel Stiffness Matrix Assembly Project

This project implements and benchmarks 4 different parallel algorithms for finite element stiffness matrix assembly on NVIDIA GPUs.

## 1. System Requirements
- NVIDIA GPU with Compute Capability 8.0+
- CUDA Toolkit 13.1 or newer
- Python 3.8+ (with Pandas, Matplotlib, Seaborn, Scipy)
- A C++ compiler (for CPU baseline)
- `nsight-compute` command-line tool in PATH

## 2. Quick Start (One-Click Run)

This single command will build the project, generate mesh data, run all tests, and create visualizations.

```bash
# For Windows
build_and_benchmark.bat

# For Linux
./build_and_benchmark.sh
```
After execution, a full report can be found at `test_framework/GPU并行组装算法性能评测报告_YYYYMMDD.md`.

## 3. Manual Setup & Execution

### Step 1: Build Binaries
- Navigate to the `/src` directory.
- Run `make` (or use the provided Visual Studio solution) to compile all CUDA source files.
- Binaries will be placed in `/bin`.
- Compile the CPU baseline in `/cpu_baseline`.

### Step 2: Generate Mesh Data
- Navigate to `/test_framework`.
- Run `python generate_structured_mesh.py --all` to generate all required mesh files into `/meshes`.

### Step 3: Run Tests
- In the `/test_framework` directory, execute the main test script:
- `python run_tests.py`
- This will read `config.json` and store raw results in the `/results` directory.

### Step 4: Generate Visualizations & Report
- `python plot_benchmark_results.py`
- This will generate all charts and the final Markdown report.

## 4. Framework Structure
- `/src`: CUDA source code for the algorithms.
- `/bin`: Compiled executables.
- `/test_framework`: Scripts for automation, testing, and visualization.
- `/meshes`: Input data.
- ... (briefly explain other directories)

## 5. Reproducibility
The test results can be fully reproduced by following the steps above. The `config.json` file explicitly defines all test parameters, and the scripts ensure that the environment and process are consistent.

```

### 4.2. 一键运行脚本设计

**`build_and_benchmark.bat` (Windows):**
```bat
@echo OFF
ECHO [Step 1/5] Building CUDA programs...
cd src
make
cd ..
ECHO Build complete.

ECHO [Step 2/5] Building CPU baseline...
cd cpu_baseline
g++ -o cpu_baseline.exe main.cpp
cd ..
ECHO CPU baseline built.

ECHO [Step 3/5] Generating mesh data...
cd test_framework
python generate_structured_mesh.py --all
ECHO Mesh data generated.

ECHO [Step 4/5] Running all performance tests...
python run_tests.py
ECHO Tests complete. Results are in /results.

ECHO [Step 5/5] Generating visualizations and final report...
python plot_benchmark_results.py
ECHO All tasks finished. Report generated.

pause
```
*(A `.sh` version for Linux would have a similar structure using `#!/bin/bash`)*
