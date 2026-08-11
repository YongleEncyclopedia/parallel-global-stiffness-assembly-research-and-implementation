#pragma once

// 这是 Demo 的公开接口，只包含类型和函数声明。
// 算法实现在 src/assembly_helper.cpp。一次完整组装按以下顺序执行：
//   1. Symbolic() 根据单元拓扑生成 CSC3 上三角结构和 HelpInfo；
//   2. zero_values() 清空上一轮数值；
//   3. 调用方建立 OpenMP 并行循环，每个单元调用一次 add()。
// Symbolic() 自己建立并行区，add() 不建立并行区，只对共享矩阵条目做原子累加。

#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace csc3_demo {

namespace evidence {
// BenchmarkAccess 只供测试和性能工具读取内部计时，不属于研发调用接口。
struct BenchmarkAccess;
} // namespace evidence

// Demo 中的全局自由度、稀疏矩阵位置、单元编号和节点编号均使用有符号 32 位整数。
// 输入编号必须非负；全局自由度还必须连续编号为 0, 1, ..., n - 1。
using Index = std::int32_t;
using ElementId = std::int32_t;
using NodeId = std::int32_t;

// 研发接口使用的自由度编码表。
// elems 保存“单元 -> 节点”，node_dofs 保存“节点 -> 全局自由度”。
// 节点在单元中的顺序同时决定单元刚度矩阵的局部自由度顺序。
struct DofCodingInfo {
    // 单元编号 -> 该单元的有序节点列表。单元内不能出现重复节点。
    std::unordered_map<ElementId, std::vector<NodeId>> elems;
    // 节点编号 -> 该节点的有序全局自由度列表。一个自由度只能属于一个节点。
    std::unordered_map<NodeId, std::vector<Index>> node_dofs;
};

// 对称矩阵上三角的 CSC3 存储。所有索引均从 0 开始。
// 第 j 列位于 [col_ptr[j], col_ptr[j + 1])，列内行号严格递增且不大于 j。
struct Csc3Matrix {
    // 整体矩阵阶数，即全局自由度总数。
    Index n = 0;
    // 列偏移，长度为 n + 1；首项为 0，末项为存储的上三角条目数。
    std::vector<Index> col_ptr;
    // 每个条目的行号，长度与 values 相同。
    std::vector<Index> row_idx;
    // CSC3 数值。Symbolic() 分配空间，zero_values() 和 add() 修改数值。
    std::vector<double> values;
};

// Symbolic() 生成的散射表。
// element_ids 中第 e 个单元的自由度和散射位置，分别由两个 offsets 数组的
// [e, e + 1) 相邻项分段。数值组装通过 scatter 直接找到 csc3.values，
// 不再搜索稀疏矩阵。
struct HelpInfo {
    // 按单元编号升序排列；下面三个分段数组都使用这里的单元顺序。
    std::vector<ElementId> element_ids;
    // element_dofs 的分段偏移，长度为 element_ids.size() + 1。
    std::vector<Index> element_dof_offsets;
    // 展平后的单元自由度，单元内顺序与 DofCodingInfo 的节点、自由度顺序一致。
    std::vector<Index> element_dofs;
    // scatter 的分段偏移，长度为 element_ids.size() + 1。
    std::vector<Index> entry_offsets;
    // 局部上三角条目对应的 csc3.values 下标，顺序与局部矩阵的行主序上三角一致。
    std::vector<Index> scatter;
};

// 单个单元刚度矩阵的只读视图。values_row_major 由调用方持有，
// 在 add() 返回前必须保持有效。
struct ElementStiffness {
    // 必须是 HelpInfo::element_ids 中已经登记的单元。
    ElementId elem_id = 0;
    // 指向完整、对称、行主序的局部矩阵，而不是只传上三角。
    const double* values_row_major = nullptr;
    // 必须等于该单元局部自由度数的平方。
    std::size_t value_count = 0;
};

// AssemblyHelper 不持有网格、CSC3 或单元刚度矩阵；这些对象都由调用方管理。
// 类内部只保存符号阶段的线程观测和 benchmark 计时。
class AssemblyHelper {
  public:
    // 根据自由度编码生成 CSC3 结构和散射表，并替换 csc3、help_info 中的旧结果。
    // 函数内部使用 OpenMP 并行处理列和单元；线程数由当前 OpenMP 环境决定，
    // 例如 OMP_NUM_THREADS=8。输入不合法或规模超出 Index 范围时抛出标准异常；
    // 构造失败不会留下只完成一部分的输出。
    void Symbolic(Csc3Matrix& csc3, HelpInfo& help_info, const DofCodingInfo& dof_coding_info);

    // 每轮数值组装前调用一次，只清空 values，不改变 CSC3 结构或 HelpInfo。
    // 不得与 add() 并发执行。
    void zero_values(Csc3Matrix& csc3) const noexcept;

    // 将一个完整、有限、对称、行主序的单元刚度矩阵累加到 CSC3。
    // add() 不创建并行区；调用方应在外层 OpenMP 循环中让每个单元恰好调用一次。
    // 多个线程可以并发调用，共享条目使用 OpenMP atomic 更新。输入不合法时会在
    // 本单元写入前抛出 std::invalid_argument，因此并行调用前应保证输入已经准备正确，
    // 不要让异常越过 OpenMP 并行区边界。
    void add(Csc3Matrix& csc3, const HelpInfo& help_info,
             const ElementStiffness& element_stiffness) const;

    // 返回最近一次 Symbolic() 的三个并行阶段实际观察到的最大线程数。
    [[nodiscard]] int symbolic_thread_count_used() const noexcept;

  private:
    // 以下成员只为 benchmark 和测试固定线程数、拆分计时，不改变公开调用顺序。
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

// 交付构建强制启用 OpenMP；这两个查询函数供示例和调用方读取运行时状态。
[[nodiscard]] bool openmp_enabled() noexcept;
[[nodiscard]] int max_openmp_threads() noexcept;

} // namespace csc3_demo
