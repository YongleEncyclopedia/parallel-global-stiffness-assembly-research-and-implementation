#include "csc3_demo/assembly_helper.h"

// 本文件实现研发规定的 AssemblyHelper。一次组装分为三步：
//   1. Symbolic() 根据单元拓扑建立 CSC3 上三角结构和散射表；
//   2. zero_values() 在新一轮数值组装前清零矩阵；
//   3. 调用方在 OpenMP 循环中逐单元调用 add()，以 atomic 方式累加刚度。
// 符号阶段不读取刚度值，数值阶段也不再搜索稀疏矩阵位置，两阶段通过 HelpInfo
// 中预先算好的 scatter 相连。

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <unordered_set>
#include <utility>
#include <vector>

#ifndef _OPENMP
#error "The CSC3 demo requires OpenMP"
#endif

#include <omp.h>

namespace csc3_demo {
namespace {

constexpr double kSymmetryAbsoluteTolerance = 1.0e-12;
constexpr double kSymmetryRelativeTolerance = 1.0e-10;

// 计时只供 benchmark 工具读取，不属于研发调用时需要准备的输入。
using SteadyClock = std::chrono::steady_clock;
using Offset = Index;
using GlobalDofIndex = Index;

// 符号阶段先在局部对象中完成全部工作，成功后再写入调用方提供的输出对象。这里要求
// 移动赋值不抛异常，避免校验、分配或搜索失败时留下只完成一部分的输出。
static_assert(std::is_nothrow_move_assignable_v<Csc3Matrix>);
static_assert(std::is_nothrow_move_assignable_v<HelpInfo>);

double elapsed_milliseconds(SteadyClock::time_point start, SteadyClock::time_point end) noexcept {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

// 下面这组小函数只处理尺寸和下标转换。把溢出检查集中在这里，主体算法读起来会
// 更接近“计数、前缀和、填充”三个步骤，也不会在不同分支里漏掉同一种边界条件。
[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

// 稀疏矩阵的偏移和条目数来自输入网格，所有加法、乘法和类型转换都先检查范围，
// 避免整数回绕后分配出尺寸错误的数组。
std::size_t checked_size_add(std::size_t left, std::size_t right, const char* label) {
    if (right > std::numeric_limits<std::size_t>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

Offset checked_offset_add(Offset left, Offset right, const char* label) {
    if (left < 0 || right < 0 || right > std::numeric_limits<Offset>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

Offset checked_offset_multiply(Offset left, Offset right, const char* label) {
    if (left < 0 || right < 0 || (left != 0 && right > std::numeric_limits<Offset>::max() / left)) {
        throw_overflow(label);
    }
    return left * right;
}

Offset checked_triangular_count(Offset dimension) {
    const Offset successor = checked_offset_add(dimension, 1, "element scatter count");
    if (dimension % 2 == 0) {
        return checked_offset_multiply(dimension / 2, successor, "element scatter count");
    }
    return checked_offset_multiply(dimension, successor / 2, "element scatter count");
}

Offset size_to_offset(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
        throw_overflow(label);
    }
    return static_cast<Offset>(value);
}

std::size_t offset_to_size(Offset value, const char* label) {
    if (value < 0) {
        throw std::logic_error(std::string(label) + " is negative");
    }
    return static_cast<std::size_t>(value);
}

GlobalDofIndex size_to_dimension(std::size_t value) {
    if (value > static_cast<std::size_t>(std::numeric_limits<GlobalDofIndex>::max())) {
        throw_overflow("matrix dimension");
    }
    return static_cast<GlobalDofIndex>(value);
}

std::int64_t size_to_parallel_bound(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max())) {
        throw_overflow(label);
    }
    return static_cast<std::int64_t>(value);
}

template <typename T> void ensure_vector_size(std::size_t count, const char* label) {
    const std::vector<T> probe;
    if (count > probe.max_size()) {
        throw_overflow(label);
    }
}

struct ValidatedTopology {
    HelpInfo plan;
    GlobalDofIndex dimension = 0;
};

// 将两级映射展开为按单元编号排序的自由度表。这里同时检查自由度是否为紧凑编号，
// 以免一个错误的超大编号触发无意义的矩阵分配。排序后的扁平数组也是后续并行
// 循环的统一输入，不再依赖 unordered_map 的遍历顺序。
ValidatedTopology validate_and_canonicalize(const DofCodingInfo& input) {
    if (input.elems.empty()) {
        throw std::invalid_argument("DofCodingInfo::elems must not be empty");
    }
    if (input.node_dofs.empty()) {
        throw std::invalid_argument("DofCodingInfo::node_dofs must not be empty");
    }

    std::vector<Index> unique_dofs;
    for (const auto& [node_id, dofs] : input.node_dofs) {
        if (node_id < 0 || dofs.empty()) {
            throw std::invalid_argument("each nonnegative node must own at least one DOF");
        }
        std::unordered_set<Index> local_dofs;
        for (const Index dof : dofs) {
            if (dof < 0 || !local_dofs.insert(dof).second) {
                throw std::invalid_argument("node DOFs must be nonnegative and unique");
            }
            unique_dofs.push_back(dof);
        }
    }
    std::sort(unique_dofs.begin(), unique_dofs.end());
    if (std::adjacent_find(unique_dofs.begin(), unique_dofs.end()) != unique_dofs.end()) {
        throw std::invalid_argument("a global DOF is assigned to more than one node");
    }
    const Index dimension = size_to_dimension(unique_dofs.size());
    for (std::size_t i = 0; i < unique_dofs.size(); ++i) {
        if (unique_dofs[i] != static_cast<Index>(i)) {
            throw std::invalid_argument("global DOFs must form compact numbering 0..n-1");
        }
    }

    std::vector<ElementId> element_ids;
    element_ids.reserve(input.elems.size());
    for (const auto& [element_id, nodes] : input.elems) {
        if (element_id < 0 || nodes.empty()) {
            throw std::invalid_argument("each nonnegative element must contain at least one node");
        }
        element_ids.push_back(element_id);
    }
    std::sort(element_ids.begin(), element_ids.end());

    ValidatedTopology result;
    result.dimension = dimension;
    result.plan.element_ids = element_ids;
    result.plan.element_dof_offsets.reserve(element_ids.size() + 1);
    result.plan.element_dof_offsets.push_back(0);

    for (const ElementId element_id : element_ids) {
        const auto& nodes = input.elems.at(element_id);
        std::unordered_set<NodeId> local_nodes;
        std::unordered_set<Index> local_dofs;
        for (const NodeId node_id : nodes) {
            if (!local_nodes.insert(node_id).second) {
                throw std::invalid_argument("an element contains a duplicate node");
            }
            const auto node = input.node_dofs.find(node_id);
            if (node == input.node_dofs.end()) {
                throw std::invalid_argument("an element refers to an unknown node");
            }
            for (const Index dof : node->second) {
                if (!local_dofs.insert(dof).second) {
                    throw std::invalid_argument("an element contains a duplicate DOF");
                }
                result.plan.element_dofs.push_back(dof);
            }
        }
        result.plan.element_dof_offsets.push_back(
            size_to_offset(result.plan.element_dofs.size(), "element DOF offset"));
    }
    return result;
}

bool materially_nonsymmetric(double upper, double lower) noexcept {
    // 同时使用绝对与相对门槛：接近零的条目由绝对误差保护，大量级条目由相对误差保护。
    const double difference = std::abs(upper - lower);
    const double scale = std::max(std::abs(upper), std::abs(lower));
    return difference > kSymmetryAbsoluteTolerance &&
           difference > kSymmetryRelativeTolerance * scale;
}

} // namespace

void AssemblyHelper::Symbolic(Csc3Matrix& csc3, HelpInfo& help_info,
                              const DofCodingInfo& dof_coding_info) {
    // 研发接口不要求调用方传线程数，默认使用 OpenMP 运行时给出的最大线程数。
    symbolic_with_thread_count(csc3, help_info, dof_coding_info, max_openmp_threads());
}

void AssemblyHelper::symbolic_with_thread_count(Csc3Matrix& csc3, HelpInfo& help_info,
                                                const DofCodingInfo& dof_coding_info,
                                                int thread_count) {
    // 这个私有入口允许测试和 benchmark 固定线程数，实际算法与 Symbolic() 相同。
    const SteadyClock::time_point symbolic_total_start = SteadyClock::now();
    BenchmarkTimings candidate_timings{};
    {
        if (thread_count <= 0) {
            throw std::invalid_argument("thread_count must be positive");
        }

        // 先在局部对象中完成构造。任何异常都不会改动调用方已有的矩阵和散射表。
        ValidatedTopology validated = validate_and_canonicalize(dof_coding_info);
        HelpInfo new_plan = std::move(validated.plan);
        Csc3Matrix new_matrix;
        new_matrix.n = validated.dimension;

        const SteadyClock::time_point symbolic_pattern_start = SteadyClock::now();
        const std::size_t dimension = static_cast<std::size_t>(new_matrix.n);
        const std::size_t dimension_plus_one =
            checked_size_add(dimension, 1, "DOF adjacency offset count");
        ensure_vector_size<Offset>(dimension_plus_one, "DOF adjacency offsets");
        std::vector<Offset> dof_element_offsets(dimension_plus_one, 0);

        // 阶段 1：两遍计数构造“全局自由度 → 关联单元”的压缩邻接。
        // 若要建立 CSC3 的某一列，先要知道哪些单元含有该列对应的自由度。第一遍
        // 统计关联数量并做前缀和，第二遍按单元顺序填入编号；整个过程不读取刚度值。
        for (const GlobalDofIndex dof : new_plan.element_dofs) {
            const std::size_t next = static_cast<std::size_t>(dof) + 1;
            dof_element_offsets[next] =
                checked_offset_add(dof_element_offsets[next], 1, "DOF incidence count");
        }
        for (std::size_t dof = 0; dof < dimension; ++dof) {
            dof_element_offsets[dof + 1] = checked_offset_add(
                dof_element_offsets[dof], dof_element_offsets[dof + 1], "DOF adjacency prefix");
        }

        const std::size_t incidence_count = new_plan.element_dofs.size();
        if (dof_element_offsets.back() !=
            size_to_offset(incidence_count, "DOF incidence array size")) {
            throw std::logic_error("DOF adjacency count does not match the canonical plan");
        }
        ensure_vector_size<Offset>(incidence_count, "DOF adjacency array");
        std::vector<Offset> dof_elements(incidence_count, 0);
        std::vector<Offset> fill_positions = dof_element_offsets;
        for (std::size_t element = 0; element < new_plan.element_ids.size(); ++element) {
            const std::size_t begin = offset_to_size(new_plan.element_dof_offsets[element],
                                                     "canonical element DOF offset");
            const std::size_t end = offset_to_size(new_plan.element_dof_offsets[element + 1],
                                                   "canonical element DOF offset");
            const Offset element_offset = size_to_offset(element, "canonical element ordinal");
            for (std::size_t local = begin; local < end; ++local) {
                const std::size_t dof = static_cast<std::size_t>(new_plan.element_dofs[local]);
                const std::size_t target =
                    offset_to_size(fill_positions[dof], "DOF adjacency fill position");
                dof_elements[target] = element_offset;
                fill_positions[dof] =
                    checked_offset_add(fill_positions[dof], 1, "DOF adjacency fill position");
            }
        }

        // 每个相关单元都可能向本列贡献若干行号。先按上界预留空间，候选项允许
        // 重复；排序和去重留到下一段并行循环中完成。
        ensure_vector_size<std::vector<GlobalDofIndex>>(dimension, "CSC3 column work array");
        std::vector<std::vector<GlobalDofIndex>> column_rows(dimension);
        for (std::size_t column = 0; column < dimension; ++column) {
            std::size_t candidate_count = 0;
            for (Offset position = dof_element_offsets[column];
                 position < dof_element_offsets[column + 1]; ++position) {
                const std::size_t element =
                    offset_to_size(dof_elements[offset_to_size(position, "DOF adjacency position")],
                                   "canonical element ordinal");
                const Offset local_dimension = new_plan.element_dof_offsets[element + 1] -
                                               new_plan.element_dof_offsets[element];
                candidate_count = checked_size_add(
                    candidate_count, offset_to_size(local_dimension, "local element dimension"),
                    "CSC3 column candidate count");
            }
            ensure_vector_size<GlobalDofIndex>(candidate_count, "CSC3 column candidates");
            column_rows[column].reserve(candidate_count);
        }

        int column_team_size = 0;
        // 阶段 2：每次循环迭代独占一列，不同线程不会同时修改同一个 rows。
        // CSC3 只保存上三角，所以每列仅保留主对角线及其上方的行号。最后排序、
        // 去重，使不同线程数下得到完全相同的列结构。
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                column_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (GlobalDofIndex column = 0; column < new_matrix.n; ++column) {
                auto& rows = column_rows[static_cast<std::size_t>(column)];
                const std::size_t column_index = static_cast<std::size_t>(column);
                for (Offset position = dof_element_offsets[column_index];
                     position < dof_element_offsets[column_index + 1]; ++position) {
                    const std::size_t element =
                        static_cast<std::size_t>(dof_elements[static_cast<std::size_t>(position)]);
                    const std::size_t begin =
                        static_cast<std::size_t>(new_plan.element_dof_offsets[element]);
                    const std::size_t end =
                        static_cast<std::size_t>(new_plan.element_dof_offsets[element + 1]);
                    for (std::size_t local = begin; local < end; ++local) {
                        const GlobalDofIndex row = new_plan.element_dofs[local];
                        if (row <= column) {
                            rows.push_back(row);
                        }
                    }
                }
                std::sort(rows.begin(), rows.end());
                rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
            }
        }

        // 各列长度确定后，用前缀和生成 col_ptr。此时每列在 row_idx 和 values 中的
        // 起止位置已经固定，后续填充不同列时不会发生写冲突。
        ensure_vector_size<Offset>(dimension_plus_one, "CSC3 column offsets");
        new_matrix.col_ptr.assign(dimension_plus_one, 0);
        for (std::size_t column = 0; column < dimension; ++column) {
            new_matrix.col_ptr[column + 1] =
                checked_offset_add(new_matrix.col_ptr[column],
                                   size_to_offset(column_rows[column].size(), "CSC3 column length"),
                                   "CSC3 nonzero count");
        }

        const std::size_t nonzero_count =
            offset_to_size(new_matrix.col_ptr.back(), "CSC3 nonzero count");
        ensure_vector_size<GlobalDofIndex>(nonzero_count, "CSC3 row indices");
        ensure_vector_size<double>(nonzero_count, "CSC3 values");
        new_matrix.row_idx.assign(nonzero_count, 0);
        new_matrix.values.assign(nonzero_count, 0.0);

        int row_fill_team_size = 0;
        // 把临时列容器复制到最终 row_idx。每个线程仍只写自己负责的列区间。
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                row_fill_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (GlobalDofIndex column = 0; column < new_matrix.n; ++column) {
                const std::size_t column_index = static_cast<std::size_t>(column);
                const std::size_t begin =
                    static_cast<std::size_t>(new_matrix.col_ptr[column_index]);
                const auto& rows = column_rows[column_index];
                for (std::size_t row = 0; row < rows.size(); ++row) {
                    new_matrix.row_idx[begin + row] = rows[row];
                }
            }
        }

        const SteadyClock::time_point symbolic_pattern_end = SteadyClock::now();
        candidate_timings.symbolic_pattern_ms =
            elapsed_milliseconds(symbolic_pattern_start, symbolic_pattern_end);

        // 阶段 3：为每个单元建立 scatter。它记录“局部上三角第几个条目”应写到
        // csc3.values 的哪个位置。数值组装反复使用这张表，无需再次搜索稀疏结构。
        const SteadyClock::time_point symbolic_scatter_start = SteadyClock::now();
        const std::size_t element_count = new_plan.element_ids.size();
        const std::size_t scatter_offset_count =
            checked_size_add(element_count, 1, "element scatter offset count");
        ensure_vector_size<Offset>(scatter_offset_count, "element scatter offsets");
        new_plan.entry_offsets.assign(scatter_offset_count, 0);
        for (std::size_t element = 0; element < element_count; ++element) {
            const Offset local_dimension =
                new_plan.element_dof_offsets[element + 1] - new_plan.element_dof_offsets[element];
            const Offset local_scatter_count = checked_triangular_count(local_dimension);
            new_plan.entry_offsets[element + 1] =
                checked_offset_add(new_plan.entry_offsets[element], local_scatter_count,
                                   "total element scatter count");
        }

        const std::size_t scatter_count =
            offset_to_size(new_plan.entry_offsets.back(), "total element scatter count");
        ensure_vector_size<Offset>(scatter_count, "element scatter indices");
        new_plan.scatter.assign(scatter_count, 0);
        const std::int64_t parallel_element_count =
            size_to_parallel_bound(element_count, "parallel element count");
        // 并行区内不能直接抛出跨越 OpenMP 边界的 C++ 异常；仅用原子标志汇总内部
        // 一致性失败，退出并行区后再以单一异常报告。
        std::atomic<bool> scatter_failure{false};
        int scatter_team_size = 0;
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                scatter_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (std::int64_t element_loop = 0; element_loop < parallel_element_count;
                 ++element_loop) {
                const std::size_t element = static_cast<std::size_t>(element_loop);
                const std::size_t dof_begin =
                    static_cast<std::size_t>(new_plan.element_dof_offsets[element]);
                const std::size_t dof_end =
                    static_cast<std::size_t>(new_plan.element_dof_offsets[element + 1]);
                std::size_t scatter_position =
                    static_cast<std::size_t>(new_plan.entry_offsets[element]);

                for (std::size_t local_row = dof_begin; local_row < dof_end; ++local_row) {
                    for (std::size_t local_column = local_row; local_column < dof_end;
                         ++local_column) {
                        const GlobalDofIndex first_dof = new_plan.element_dofs[local_row];
                        const GlobalDofIndex second_dof = new_plan.element_dofs[local_column];
                        const GlobalDofIndex row = std::min(first_dof, second_dof);
                        const GlobalDofIndex column = std::max(first_dof, second_dof);
                        const std::size_t column_index = static_cast<std::size_t>(column);
                        const std::size_t column_begin =
                            static_cast<std::size_t>(new_matrix.col_ptr[column_index]);
                        const std::size_t column_end =
                            static_cast<std::size_t>(new_matrix.col_ptr[column_index + 1]);
                        const auto begin =
                            new_matrix.row_idx.begin() + static_cast<std::ptrdiff_t>(column_begin);
                        const auto end =
                            new_matrix.row_idx.begin() + static_cast<std::ptrdiff_t>(column_end);
                        // 列内行号严格递增，可用二分搜索得到稳定的 CSC3 目标偏移。
                        const auto found = std::lower_bound(begin, end, row);
                        if (found == end || *found != row ||
                            scatter_position >= new_plan.scatter.size()) {
                            scatter_failure.store(true, std::memory_order_relaxed);
                        } else {
                            const std::size_t local_position =
                                static_cast<std::size_t>(found - begin);
                            new_plan.scatter[scatter_position] =
                                static_cast<Offset>(column_begin + local_position);
                        }
                        ++scatter_position;
                    }
                }
                if (scatter_position !=
                    static_cast<std::size_t>(new_plan.entry_offsets[element + 1])) {
                    scatter_failure.store(true, std::memory_order_relaxed);
                }
            }
        }

        if (scatter_failure.load(std::memory_order_relaxed)) {
            throw std::logic_error("failed to locate an element entry in the CSC3 structure");
        }
        const SteadyClock::time_point symbolic_scatter_end = SteadyClock::now();
        candidate_timings.symbolic_scatter_ms =
            elapsed_milliseconds(symbolic_scatter_start, symbolic_scatter_end);

        // 到这里结构和散射表才算完整，统一替换调用方的旧结果。
        csc3 = std::move(new_matrix);
        help_info = std::move(new_plan);
        symbolic_thread_count_used_ =
            std::max({column_team_size, row_fill_team_size, scatter_team_size});
        symbolic_used_requested_team_in_all_regions_ = column_team_size == thread_count &&
                                                       row_fill_team_size == thread_count &&
                                                       scatter_team_size == thread_count;
    }
    candidate_timings.symbolic_total_ms =
        elapsed_milliseconds(symbolic_total_start, SteadyClock::now());
    benchmark_timings_ = candidate_timings;
}

void AssemblyHelper::zero_values(Csc3Matrix& csc3) const noexcept {
    // add() 采用累加语义；每轮完整组装前应由调用方清零一次。
    std::fill(csc3.values.begin(), csc3.values.end(), 0.0);
}

void AssemblyHelper::add(Csc3Matrix& csc3, const HelpInfo& help_info,
                         const ElementStiffness& element_stiffness) const {
    // add() 不创建 OpenMP 并行区。它设计成由外层 parallel for 逐单元调用，内部只在
    // 最终写 csc3.values 时使用 atomic。下面所有检查都在第一次写入之前完成，
    // 因而非法输入不会留下只累加了一部分的单元矩阵。
    const ElementId elem_id = element_stiffness.elem_id;
    const double* element_stiffness_row_major = element_stiffness.values_row_major;
    const std::size_t value_count = element_stiffness.value_count;
    if (element_stiffness_row_major == nullptr && value_count != 0) {
        throw std::invalid_argument("element stiffness pointer is null");
    }
    if (csc3.n <= 0 || csc3.col_ptr.size() != static_cast<std::size_t>(csc3.n) + 1 ||
        csc3.row_idx.size() != csc3.values.size()) {
        throw std::invalid_argument("CSC3 storage is inconsistent");
    }
    if (help_info.element_dof_offsets.size() != help_info.element_ids.size() + 1 ||
        help_info.entry_offsets.size() != help_info.element_ids.size() + 1) {
        throw std::invalid_argument("HelpInfo offsets are inconsistent");
    }

    // Symbolic() 已将 element_ids 排序，可以用二分搜索找到当前单元在 HelpInfo 中
    // 的序号，再由相邻 offset 取得它的自由度区间和 scatter 区间。
    const auto found =
        std::lower_bound(help_info.element_ids.begin(), help_info.element_ids.end(), elem_id);
    if (found == help_info.element_ids.end() || *found != elem_id) {
        throw std::invalid_argument("element ID is not present in HelpInfo");
    }
    const std::size_t element = static_cast<std::size_t>(found - help_info.element_ids.begin());
    const std::size_t dof_begin =
        offset_to_size(help_info.element_dof_offsets[element], "element DOF offset");
    const std::size_t dof_end =
        offset_to_size(help_info.element_dof_offsets[element + 1], "element DOF offset");
    if (dof_end < dof_begin || dof_end > help_info.element_dofs.size()) {
        throw std::invalid_argument("element DOF range is invalid");
    }
    const std::size_t local_dimension = dof_end - dof_begin;
    if (local_dimension != 0 &&
        local_dimension > std::numeric_limits<std::size_t>::max() / local_dimension) {
        throw_overflow("element stiffness size");
    }
    if (value_count != local_dimension * local_dimension) {
        throw std::invalid_argument(
            "element stiffness must contain local_dimension squared values");
    }
    const std::size_t scatter_begin =
        offset_to_size(help_info.entry_offsets[element], "entry offset");
    const std::size_t scatter_end =
        offset_to_size(help_info.entry_offsets[element + 1], "entry offset");
    const std::size_t expected_entries =
        offset_to_size(checked_triangular_count(size_to_offset(local_dimension, "local dimension")),
                       "element entry count");
    if (scatter_end < scatter_begin || scatter_end - scatter_begin != expected_entries ||
        scatter_end > help_info.scatter.size()) {
        throw std::invalid_argument("element scatter range is invalid");
    }

    // 调用方传入完整的行主序局部矩阵。先检查所有数值有限，再检查上下三角是否在
    // 规定容差内对称；CSC3 最终只存其中的上三角。
    for (std::size_t row = 0; row < local_dimension; ++row) {
        for (std::size_t column = 0; column < local_dimension; ++column) {
            const double value = element_stiffness_row_major[row * local_dimension + column];
            if (!std::isfinite(value)) {
                throw std::invalid_argument("element stiffness must contain finite values");
            }
        }
    }
    for (std::size_t row = 0; row < local_dimension; ++row) {
        for (std::size_t column = row + 1; column < local_dimension; ++column) {
            const double upper = element_stiffness_row_major[row * local_dimension + column];
            const double lower = element_stiffness_row_major[column * local_dimension + row];
            if (materially_nonsymmetric(upper, lower)) {
                throw std::invalid_argument("element stiffness must be symmetric");
            }
        }
    }
    // 写入前把本单元会访问的所有目标位置检查一遍。这样即使 scatter 被破坏，也
    // 不会先改动矩阵再在循环中途报错。
    for (std::size_t position = scatter_begin; position < scatter_end; ++position) {
        const Index target = help_info.scatter[position];
        if (target < 0 || static_cast<std::size_t>(target) >= csc3.values.size()) {
            throw std::invalid_argument("scatter target is outside CSC3 values");
        }
    }

    // 按行主序遍历局部上三角，scatter 给出对应的全局位置。不同单元可能命中同一
    // 位置，因此最后一步必须使用 OpenMP atomic。
    std::size_t scatter_position = scatter_begin;
    for (std::size_t row = 0; row < local_dimension; ++row) {
        for (std::size_t column = row; column < local_dimension; ++column) {
            const std::size_t target =
                static_cast<std::size_t>(help_info.scatter[scatter_position++]);
            const double value = element_stiffness_row_major[row * local_dimension + column];
#pragma omp atomic
            csc3.values[target] += value;
        }
    }
}

int AssemblyHelper::symbolic_thread_count_used() const noexcept {
    // 这个值由最近一次成功的 Symbolic() 更新，测试工具用它确认并行区确实启动了
    // 请求的线程；研发侧正常组装不需要读取它。
    return symbolic_thread_count_used_;
}

bool openmp_enabled() noexcept {
    return true;
}

int max_openmp_threads() noexcept {
    return omp_get_max_threads();
}

} // namespace csc3_demo
