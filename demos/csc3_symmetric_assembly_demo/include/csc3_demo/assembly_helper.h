#pragma once

#include <cstdint>
#include <vector>

namespace csc3_demo {

namespace evidence {
struct BenchmarkAccess;
}

/// 全局自由度的零基有符号索引类型；负值始终属于非法输入。
using GlobalDofIndex = std::int32_t;
/// 单元编号类型；公开输入要求编号非负且全局唯一。
using ElementId = std::int32_t;
/// 展平数组中的零基偏移类型；采用 64 位宽度以独立于自由度索引容量。
using Offset = std::uint64_t;

/// 拥有数据所有权的“单元—全局自由度”压缩输入。
///
/// `element_dof_offsets` 采用半开区间：第 $e$ 个输入单元的局部自由度位于
/// `[element_dof_offsets[e], element_dof_offsets[e+1])`。调用符号组装时会按
/// `element_ids` 升序规范化单元次序，但每个单元内部的局部自由度次序保持不变。
/// 全部全局自由度必须形成紧凑编号 $[0,\mathrm{dimension})$，单元内部不得重复。
struct ElementDofMap {
    /// 每个偏移分段对应一个单元编号；数组长度即单元数。
    std::vector<ElementId> element_ids;
    /// 指向 `global_dof_indices` 的零基偏移；长度必须为单元数加一，首项为零。
    std::vector<Offset> element_dof_offsets;
    /// 按各单元局部次序展平的零基全局自由度索引。
    std::vector<GlobalDofIndex> global_dof_indices;
};

/// 按规范化单元次序存放的完整稠密单元矩阵批次。
///
/// 每个分段必须是有限、对称的 $n_e\times n_e$ 行主序矩阵，其中 $n_e$ 是对应
/// 单元的局部自由度数。批次次序必须与符号阶段按 `element_ids` 升序得到的次序一致；
/// 因此输入拓扑不是升序时，调用方也必须按该规范次序提供矩阵分段。
struct ElementMatrixBatch {
    /// 指向 `values_row_major` 的零基偏移；长度必须为单元数加一，首项为零。
    std::vector<Offset> element_value_offsets;
    /// 每个分段保存一个完整的行主序方阵，而不是只保存上三角。
    std::vector<double> values_row_major;
};

/// 对称矩阵上三角的零基 CSC3 存储。
///
/// 第 $j$ 列的条目位于 `[column_offsets[j], column_offsets[j+1])`；对应行号严格
/// 递增并满足 $0\le i\le j$。`row_indices[k]` 与 `values[k]` 一一对应，未显式
/// 保存的下三角值由对称性 $K_{ji}=K_{ij}$ 定义。
struct Csc3Matrix {
    /// 方阵行列数，同时也是全局自由度数。
    GlobalDofIndex dimension = 0;
    /// 指向 `row_indices` 和 `values` 的列偏移；长度为 `dimension + 1`。
    std::vector<Offset> column_offsets;
    /// 各列内严格递增的零基行号，只包含上三角条目。
    std::vector<GlobalDofIndex> row_indices;
    /// 与 `row_indices` 一一对应的整体刚度矩阵数值。
    std::vector<double> values;
};

/// 符号阶段生成并拥有的规范拓扑及数值散射计划。
///
/// 对每个单元，`scatter_indices` 按局部上三角顺序
/// $(0,0),(0,1),\ldots,(0,n_e-1),(1,1),\ldots$ 存放目标 `values` 偏移。
/// 数值阶段因此无需重复搜索 CSC3 结构，只需根据该映射执行原子累加。
struct AssemblyPlan {
    /// 严格递增的规范单元编号。
    std::vector<ElementId> element_ids;
    /// 规范单元到 `global_dof_indices` 的零基偏移。
    std::vector<Offset> element_dof_offsets;
    /// 规范单元次序下的全局自由度；单元内部局部次序保持输入语义。
    std::vector<GlobalDofIndex> global_dof_indices;
    /// 每个单元在 `scatter_indices` 中的半开区间偏移。
    std::vector<Offset> element_scatter_offsets;
    /// 指向 `Csc3Matrix::values` 的零基目标偏移。
    std::vector<Offset> scatter_indices;
};

/// 同时拥有 CSC3 矩阵和装配计划的有状态组装器。
///
/// 一个实例不支持并发调用；可并行的是单次调用内部的 OpenMP 区域。只读引用的生命期
/// 绑定到组装器，后续成功的符号/数值调用可能替换其内容。所有输入会在返回前完成读取，
/// 不保留调用方缓冲区。参数校验失败时保持上一次成功状态不变。
class SymmetricCscAssembler {
  public:
    /// 构造确定性的并行符号结构与散射计划，并在全部阶段成功后原子式替换旧状态。
    /// 不同合法线程数必须得到逐项一致的 `column_offsets`、`row_indices` 和计划数组。
    /// @throws std::invalid_argument 拓扑不合法或 `thread_count <= 0`。
    /// @throws std::overflow_error 任一尺寸或偏移超出可表示范围。
    void build_symbolic_parallel(const ElementDofMap& element_dof_map, int thread_count);
    /// 使用 OpenMP atomic 完成一次完整数值组装：校验后先清零，再覆盖本次结果。
    /// 重复调用不会把旧的整体矩阵再次累加；方法不会保留 `element_matrices` 的引用。
    /// @throws std::logic_error 尚未成功执行符号阶段，或内部计划已损坏。
    /// @throws std::invalid_argument 数值、布局不合法或 `thread_count <= 0`。
    void assemble_numeric_atomic(const ElementMatrixBatch& element_matrices, int thread_count);
    /// 返回组装器拥有的矩阵；任一后续修改调用都可能使其数组内容发生变化。
    [[nodiscard]] const Csc3Matrix& matrix() const noexcept;
    /// 返回组装器拥有的计划；后续成功的符号调用会替换该计划。
    [[nodiscard]] const AssemblyPlan& assembly_plan() const noexcept;
    /// 返回最近一次成功符号调用的三个 OpenMP 区域中实际观察到的最大 team size。
    [[nodiscard]] int symbolic_thread_count_used() const noexcept;
    /// 返回最近一次成功数值调用实际观察到的 OpenMP team size。
    [[nodiscard]] int numeric_thread_count_used() const noexcept;

  private:
    struct BenchmarkTimings {
        double symbolic_pattern_ms = 0.0;
        double symbolic_scatter_ms = 0.0;
        double symbolic_total_ms = 0.0;
        double numeric_reset_ms = 0.0;
        double numeric_kernel_ms = 0.0;
        double numeric_total_ms = 0.0;
    };

    friend struct evidence::BenchmarkAccess;

    Csc3Matrix matrix_;
    AssemblyPlan assembly_plan_;
    BenchmarkTimings benchmark_timings_;
    int symbolic_thread_count_used_ = 0;
    int numeric_thread_count_used_ = 0;
    bool symbolic_used_requested_team_in_all_regions_ = false;
    bool numeric_used_requested_team_ = false;
    bool symbolic_ready_ = false;
};

/// 报告当前构建是否包含必需的 OpenMP 路径；本 demo 的可交付构建恒为 `true`。
[[nodiscard]] bool openmp_enabled() noexcept;
/// 返回调用线程当前 OpenMP 运行时允许的最大 team size。
[[nodiscard]] int max_openmp_threads() noexcept;

} // namespace csc3_demo
