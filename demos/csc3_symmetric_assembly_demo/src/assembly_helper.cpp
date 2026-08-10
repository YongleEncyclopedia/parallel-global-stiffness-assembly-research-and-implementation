#include "csc3_demo/assembly_helper.h"

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

using SteadyClock = std::chrono::steady_clock;
using Offset = Index;
using GlobalDofIndex = Index;

// 符号阶段先在局部候选对象上完成全部工作，最后才提交到成员状态。这里要求移动赋值
// 不抛异常，以保证提交点之前的任何校验、分配或搜索失败都不会破坏上一次成功结果。
static_assert(std::is_nothrow_move_assignable_v<Csc3Matrix>);
static_assert(std::is_nothrow_move_assignable_v<HelpInfo>);

double elapsed_milliseconds(SteadyClock::time_point start, SteadyClock::time_point end) noexcept {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

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
// 以免一个错误的超大编号触发无意义的矩阵分配。
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
    symbolic_with_thread_count(csc3, help_info, dof_coding_info, max_openmp_threads());
}

void AssemblyHelper::symbolic_with_thread_count(Csc3Matrix& csc3, HelpInfo& help_info,
                                                const DofCodingInfo& dof_coding_info,
                                                int thread_count) {
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

        // 阶段 1：两遍计数构造“全局自由度 -> 关联单元”的压缩邻接。
        // 第一遍计数并做前缀和，第二遍按规范单元次序填充。邻接只依赖拓扑，不涉及刚度值。
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

        // 预估各列候选行数并预留容量。该上界允许重复项，真正的排序去重在列所有权
        // 并行区内完成，从而避免多个线程向同一列容器写入。
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
        // 阶段 2：确定性列所有权。每次循环迭代独占一个 column_rows[column]，不同线程
        // 没有共享写入；schedule(static) 只决定列的归属，不影响每列排序后的结果。
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

        // 各列长度确定后串行前缀和生成 CSC3 列偏移。由此得到的全局条目位置固定，
        // 后续并行填充按互不重叠的列区间写入，无需锁或 atomic。
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

        // 阶段 3：构造局部上三角条目到 CSC3 values 的 scatter 映射。每个单元的目标
        // 区间由 entry_offsets 预先固定，因此线程只写各自单元的连续区间。
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

        // 结构和散射表均有效后再交给调用方。
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
    std::fill(csc3.values.begin(), csc3.values.end(), 0.0);
}

void AssemblyHelper::add(Csc3Matrix& csc3, const HelpInfo& help_info,
                         const ElementStiffness& element_stiffness) const {
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
    for (std::size_t position = scatter_begin; position < scatter_end; ++position) {
        const Index target = help_info.scatter[position];
        if (target < 0 || static_cast<std::size_t>(target) >= csc3.values.size()) {
            throw std::invalid_argument("scatter target is outside CSC3 values");
        }
    }

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
    return symbolic_thread_count_used_;
}

bool openmp_enabled() noexcept {
    return true;
}

int max_openmp_threads() noexcept {
    return omp_get_max_threads();
}

} // namespace csc3_demo
