#pragma once

#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace csc3_demo {

namespace evidence {
struct BenchmarkAccess;
}

using Index = std::int32_t;
using ElementId = std::int32_t;
using NodeId = std::int32_t;

// 研发接口使用的自由度编码表。
// elems 保存“单元 -> 节点”，node_dofs 保存“节点 -> 全局自由度”。
// 节点在单元中的顺序同时决定单元刚度矩阵的局部自由度顺序。
struct DofCodingInfo {
    std::unordered_map<ElementId, std::vector<NodeId>> elems;
    std::unordered_map<NodeId, std::vector<Index>> node_dofs;
};

// 对称矩阵上三角的 CSC3 存储。所有索引均从 0 开始。
// 第 j 列位于 [col_ptr[j], col_ptr[j + 1])，列内行号严格递增且不大于 j。
struct Csc3Matrix {
    Index n = 0;
    std::vector<Index> col_ptr;
    std::vector<Index> row_idx;
    std::vector<double> values;
};

// Symbolic() 生成的散射表。
// 每个单元的自由度和上三角散射位置分别由 element_dof_offsets、entry_offsets 分段。
struct HelpInfo {
    std::vector<ElementId> element_ids;
    std::vector<Index> element_dof_offsets;
    std::vector<Index> element_dofs;
    std::vector<Index> entry_offsets;
    std::vector<Index> scatter;
};

// 单个单元刚度矩阵的只读视图。values_row_major 由调用方持有，
// 在 add() 返回前必须保持有效。
struct ElementStiffness {
    ElementId elem_id = 0;
    const double* values_row_major = nullptr;
    std::size_t value_count = 0;
};

class AssemblyHelper {
  public:
    // 根据自由度编码生成 CSC3 结构和散射表。函数内部使用 OpenMP 并行处理列和单元；
    // 线程数由当前 OpenMP 运行环境决定，例如 OMP_NUM_THREADS=8。
    void Symbolic(Csc3Matrix& csc3, HelpInfo& help_info, const DofCodingInfo& dof_coding_info);

    // 数值组装前调用一次。不得与 add() 并发执行。
    void zero_values(Csc3Matrix& csc3) const noexcept;

    // 将一个完整、对称、行主序的单元刚度矩阵累加到 CSC3。
    // 多个线程可以针对不同单元并发调用；共享条目使用 OpenMP atomic 更新。
    void add(Csc3Matrix& csc3, const HelpInfo& help_info,
             const ElementStiffness& element_stiffness) const;

    [[nodiscard]] int symbolic_thread_count_used() const noexcept;

  private:
    struct BenchmarkTimings {
        double symbolic_pattern_ms = 0.0;
        double symbolic_scatter_ms = 0.0;
        double symbolic_total_ms = 0.0;
    };

    void symbolic_with_thread_count(Csc3Matrix& csc3, HelpInfo& help_info,
                                    const DofCodingInfo& dof_coding_info, int thread_count);

    friend struct evidence::BenchmarkAccess;

    BenchmarkTimings benchmark_timings_;
    int symbolic_thread_count_used_ = 0;
    bool symbolic_used_requested_team_in_all_regions_ = false;
};

[[nodiscard]] bool openmp_enabled() noexcept;
[[nodiscard]] int max_openmp_threads() noexcept;

} // namespace csc3_demo
