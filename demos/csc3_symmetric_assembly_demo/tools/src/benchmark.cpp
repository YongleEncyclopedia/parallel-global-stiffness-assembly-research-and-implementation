// 这个文件把一次 benchmark 串起来：准备算例、建立独立串行基线、运行各线程配置，
// 最后汇总正确性和计时结果。命令行解析与文件输出在 benchmark_io.cpp。
#include "csc3_demo_tools/benchmark.h"

#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifndef _OPENMP
#error "The CSC3 benchmark requires OpenMP"
#endif

#include <omp.h>

namespace csc3_demo::evidence {

int select_validation_thread_count(const std::vector<int>& requested_thread_counts) {
    // 小型验证优先固定为 2 线程，便于在各平台上覆盖真实并行路径。
    const auto two = std::find(requested_thread_counts.begin(), requested_thread_counts.end(), 2);
    if (two != requested_thread_counts.end()) {
        return 2;
    }
    const auto parallel =
        std::find_if(requested_thread_counts.begin(), requested_thread_counts.end(),
                     [](int thread_count) { return thread_count > 1; });
    return parallel != requested_thread_counts.end() ? *parallel : 1;
}

namespace {

using Clock = std::chrono::steady_clock;

constexpr double kRelativeFrobeniusTolerance = 1.0e-8;
constexpr double kMaximumAbsoluteBaseTolerance = 1.0e-10;
constexpr double kMaximumAbsoluteScaleTolerance = 1.0e-8;
constexpr double kNormFloor = 1.0e-30;
constexpr double kSymmetryAbsoluteTolerance = 1.0e-12;
constexpr double kSymmetryRelativeTolerance = 1.0e-10;

[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

// 尺寸检查沿用组装类的处理原则：先确认计算不会溢出，再申请 vector。benchmark
// 可能读取工程网格，不能让一个损坏的输入把回绕后的尺寸当成正常规模。
std::size_t checked_add(std::size_t left, std::size_t right, const char* label) {
    if (right > std::numeric_limits<std::size_t>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

std::size_t checked_multiply(std::size_t left, std::size_t right, const char* label) {
    if (left != 0 && right > std::numeric_limits<std::size_t>::max() / left) {
        throw_overflow(label);
    }
    return left * right;
}

std::size_t offset_to_size(Offset value, const char* label) {
    if constexpr (std::numeric_limits<Offset>::digits > std::numeric_limits<std::size_t>::digits) {
        if (value > static_cast<Offset>(std::numeric_limits<std::size_t>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<std::size_t>(value);
}

Offset size_to_offset(std::size_t value, const char* label) {
    if constexpr (std::numeric_limits<std::size_t>::digits > std::numeric_limits<Offset>::digits) {
        if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<Offset>(value);
}

Index size_to_index(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<Index>::max())) {
        throw_overflow(label);
    }
    return static_cast<Index>(value);
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) noexcept {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

std::string evidence_level_name(PerformanceEvidenceLevel level) {
    switch (level) {
    case PerformanceEvidenceLevel::CiSmoke:
        return "ci-smoke";
    case PerformanceEvidenceLevel::LocalSmoke:
        return "local-smoke";
    case PerformanceEvidenceLevel::Formal:
        return "formal";
    }
    throw std::invalid_argument("invalid performance evidence level");
}

ElementType generated_element_type(BenchmarkCase benchmark_case) {
    switch (benchmark_case) {
    case BenchmarkCase::GeneratedTet4:
        return ElementType::Tet4;
    case BenchmarkCase::GeneratedHex8:
        return ElementType::Hex8;
    case BenchmarkCase::WindHub:
        break;
    }
    throw std::invalid_argument("invalid benchmark case");
}

std::string element_type_name(ElementType element_type) {
    switch (element_type) {
    case ElementType::Tet4:
        return "Tet4";
    case ElementType::Hex8:
        return "Hex8";
    }
    throw std::invalid_argument("invalid element type");
}

void validate_configuration(const BenchmarkConfiguration& configuration) {
    // 所有入口都先经过这里，避免 CLI、单元测试和外部调用采用不同的实验规则。
    const std::string level = evidence_level_name(configuration.performance_evidence_level);
    switch (configuration.benchmark_case) {
    case BenchmarkCase::GeneratedTet4:
    case BenchmarkCase::GeneratedHex8:
        if (!configuration.input_path.empty()) {
            throw std::invalid_argument("generated benchmark cases do not accept an input path");
        }
        if (level == "formal") {
            throw std::invalid_argument(
                "formal evidence is restricted to the WindHub controlled-host workflow");
        }
        if (configuration.nx <= 0 || configuration.ny <= 0 || configuration.nz <= 0) {
            throw std::invalid_argument("generated grid dimensions must be positive");
        }
        break;
    case BenchmarkCase::WindHub:
        if (configuration.input_path.empty()) {
            throw std::invalid_argument("WindHub benchmark requires an input path");
        }
        if (configuration.nx != 0 || configuration.ny != 0 || configuration.nz != 0) {
            throw std::invalid_argument("WindHub benchmark does not accept grid dimensions");
        }
        if (level == "formal" && (configuration.warmup_count != kFormalWarmupCount ||
                                  configuration.repeat_count != kFormalRepeatCount ||
                                  configuration.amortization_count != kFormalAmortizationCount)) {
            throw std::invalid_argument(
                "formal WindHub evidence requires warmup_count=2, repeat_count=7, and "
                "amortization_count=1");
        }
        break;
    default:
        throw std::invalid_argument("invalid benchmark case");
    }
    if (configuration.warmup_count < 0) {
        throw std::invalid_argument("warmup_count must be nonnegative");
    }
    if (configuration.repeat_count < 1) {
        throw std::invalid_argument("repeat_count must be positive");
    }
    if (configuration.amortization_count < 1) {
        throw std::invalid_argument("amortization_count must be positive");
    }
    if (configuration.thread_counts.empty()) {
        throw std::invalid_argument("thread_counts must not be empty");
    }
    std::set<int> unique_threads;
    const int available_threads = max_openmp_threads();
    for (const int thread_count : configuration.thread_counts) {
        if (thread_count <= 0) {
            throw std::invalid_argument("thread_counts must contain only positive values");
        }
        if (!unique_threads.insert(thread_count).second) {
            throw std::invalid_argument("thread_counts must contain unique values");
        }
        if (thread_count > available_threads) {
            throw std::invalid_argument(
                "a requested thread count exceeds the current OpenMP maximum");
        }
    }
}

AssemblyCase prepare_benchmark_case(const BenchmarkConfiguration& configuration) {
    // 生成式算例和 .inp 工程算例在这里汇合。后面的计时、串行参考和并行候选只接收
    // AssemblyCase，因而不会因为输入来源不同形成两套性能口径。
    switch (configuration.benchmark_case) {
    case BenchmarkCase::GeneratedTet4:
    case BenchmarkCase::GeneratedHex8:
        return make_cube_case(generated_element_type(configuration.benchmark_case),
                              configuration.nx, configuration.ny, configuration.nz);
    case BenchmarkCase::WindHub:
        return load_abaqus_case(configuration.input_path);
    }
    throw std::invalid_argument("invalid benchmark case");
}

struct SerialSymbolicState {
    Csc3Matrix matrix;
    HelpInfo plan;
};

HelpInfo canonicalize_topology(const FlatDofTopology& topology, GlobalDofIndex& dimension) {
    // 输入是测试工具使用的三个扁平数组。这里把它们整理成研发接口使用的 HelpInfo，
    // 同时完成偏移、编号和重复自由度检查。
    const std::size_t element_count = topology.element_ids.size();
    if (element_count == 0) {
        throw std::invalid_argument("element_dof_map must contain at least one element");
    }
    if (topology.element_dof_offsets.size() !=
        checked_add(element_count, 1, "element DOF offset count")) {
        throw std::invalid_argument(
            "element_dof_offsets must contain one entry per element plus one");
    }
    if (topology.element_dof_offsets.front() != 0) {
        throw std::invalid_argument("element_dof_offsets must start at zero");
    }
    for (std::size_t index = 1; index < topology.element_dof_offsets.size(); ++index) {
        if (topology.element_dof_offsets[index] < topology.element_dof_offsets[index - 1]) {
            throw std::invalid_argument("element_dof_offsets must be monotone");
        }
    }
    if (topology.element_dof_offsets.back() !=
        size_to_offset(topology.global_dof_indices.size(), "global DOF array size")) {
        throw std::invalid_argument(
            "the final element DOF offset must equal global_dof_indices.size()");
    }

    // 先按单元编号确定稳定顺序。串行和并行路径都使用这个顺序，比较时才不会把
    // 输入排列差异误认为算法差异。
    std::vector<std::size_t> ordinals(element_count, 0);
    std::iota(ordinals.begin(), ordinals.end(), std::size_t{0});
    for (const ElementId element_id : topology.element_ids) {
        if (element_id < 0) {
            throw std::invalid_argument("element IDs must be nonnegative");
        }
    }
    std::sort(ordinals.begin(), ordinals.end(), [&topology](std::size_t left, std::size_t right) {
        return topology.element_ids[left] < topology.element_ids[right];
    });
    for (std::size_t index = 1; index < ordinals.size(); ++index) {
        if (topology.element_ids[ordinals[index - 1]] == topology.element_ids[ordinals[index]]) {
            throw std::invalid_argument("element IDs must be unique");
        }
    }

    HelpInfo plan;
    plan.element_ids.reserve(element_count);
    plan.element_dof_offsets.reserve(element_count + 1);
    plan.element_dof_offsets.push_back(0);
    GlobalDofIndex maximum_dof = -1;
    for (const std::size_t ordinal : ordinals) {
        const std::size_t begin =
            offset_to_size(topology.element_dof_offsets[ordinal], "element DOF offset");
        const std::size_t end =
            offset_to_size(topology.element_dof_offsets[ordinal + 1], "element DOF offset");
        if (begin == end) {
            throw std::invalid_argument("each element must contain at least one DOF");
        }
        std::vector<GlobalDofIndex> local_dofs;
        local_dofs.reserve(end - begin);
        for (std::size_t position = begin; position < end; ++position) {
            const GlobalDofIndex dof = topology.global_dof_indices[position];
            if (dof < 0) {
                throw std::invalid_argument("global DOF indices must be nonnegative");
            }
            local_dofs.push_back(dof);
            maximum_dof = std::max(maximum_dof, dof);
        }
        // 排序副本只用于检查重复自由度；写入 plan 的仍是单元原有局部顺序。
        std::sort(local_dofs.begin(), local_dofs.end());
        if (std::adjacent_find(local_dofs.begin(), local_dofs.end()) != local_dofs.end()) {
            throw std::invalid_argument("an element contains duplicate local DOFs");
        }
        plan.element_ids.push_back(topology.element_ids[ordinal]);
        plan.element_dofs.insert(
            plan.element_dofs.end(),
            topology.global_dof_indices.begin() + static_cast<std::ptrdiff_t>(begin),
            topology.global_dof_indices.begin() + static_cast<std::ptrdiff_t>(end));
        plan.element_dof_offsets.push_back(
            size_to_index(plan.element_dofs.size(), "canonical global DOF array size"));
    }
    if (maximum_dof < 0) {
        throw std::invalid_argument("topology must contain at least one global DOF");
    }
    // 全局自由度必须紧凑编号为 0..n-1，不能在矩阵中留下无意义的空行、空列。
    const std::size_t dimension_size =
        checked_add(static_cast<std::size_t>(maximum_dof), 1, "matrix dimension");
    dimension = size_to_index(dimension_size, "matrix dimension");
    std::vector<bool> observed_dofs(dimension_size, false);
    for (const GlobalDofIndex dof : plan.element_dofs) {
        observed_dofs[static_cast<std::size_t>(dof)] = true;
    }
    if (std::find(observed_dofs.begin(), observed_dofs.end(), false) != observed_dofs.end()) {
        throw std::invalid_argument("global DOF indices must form compact numbering 0..n-1");
    }
    return plan;
}

SerialSymbolicState build_serial_symbolic(const FlatDofTopology& topology) {
    // 串行基线独立搜索 CSC3 结构和 scatter 位置，不调用候选 AssemblyHelper。
    // 候选符号组装如果出错，不会在参考路径中得到同样的错误结果。
    SerialSymbolicState result;
    result.plan = canonicalize_topology(topology, result.matrix.n);
    const std::size_t dimension = static_cast<std::size_t>(result.matrix.n);
    std::vector<std::vector<GlobalDofIndex>> column_rows(dimension);

    const std::size_t element_count = result.plan.element_ids.size();
    result.plan.entry_offsets.assign(element_count + 1, 0);
    // 第一遍遍历单元，收集每一列可能出现的上三角行号，并计算各单元需要的
    // scatter 条目数。
    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t begin = offset_to_size(result.plan.element_dof_offsets[element],
                                                 "canonical element DOF offset");
        const std::size_t end = offset_to_size(result.plan.element_dof_offsets[element + 1],
                                               "canonical element DOF offset");
        const std::size_t local_dimension = end - begin;
        const std::size_t triangular_count =
            checked_multiply(local_dimension, checked_add(local_dimension, 1, "local dimension"),
                             "local triangular count") /
            2;
        result.plan.entry_offsets[element + 1] = size_to_index(
            checked_add(offset_to_size(result.plan.entry_offsets[element], "scatter offset"),
                        triangular_count, "total scatter count"),
            "total scatter count");
        for (std::size_t local_row = begin; local_row < end; ++local_row) {
            for (std::size_t local_column = local_row; local_column < end; ++local_column) {
                const GlobalDofIndex first = result.plan.element_dofs[local_row];
                const GlobalDofIndex second = result.plan.element_dofs[local_column];
                const GlobalDofIndex row = std::min(first, second);
                const GlobalDofIndex column = std::max(first, second);
                column_rows[static_cast<std::size_t>(column)].push_back(row);
            }
        }
    }

    // 每列独立排序去重，再通过前缀和形成 CSC3 的列偏移。
    result.matrix.col_ptr.assign(dimension + 1, 0);
    for (std::size_t column = 0; column < dimension; ++column) {
        auto& rows = column_rows[column];
        std::sort(rows.begin(), rows.end());
        rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
        result.matrix.col_ptr[column + 1] = size_to_index(
            checked_add(offset_to_size(result.matrix.col_ptr[column], "column offset"), rows.size(),
                        "CSC3 nonzero count"),
            "CSC3 nonzero count");
    }
    const std::size_t nonzero_count =
        offset_to_size(result.matrix.col_ptr.back(), "CSC3 nonzero count");
    result.matrix.row_idx.resize(nonzero_count);
    result.matrix.values.assign(nonzero_count, 0.0);
    for (std::size_t column = 0; column < dimension; ++column) {
        const std::size_t begin = offset_to_size(result.matrix.col_ptr[column], "column offset");
        std::copy(column_rows[column].begin(), column_rows[column].end(),
                  result.matrix.row_idx.begin() + static_cast<std::ptrdiff_t>(begin));
    }

    // 最后一遍按局部上三角顺序查找整体矩阵位置。数值阶段按 scatter 累加，
    // 不再搜索稀疏结构。
    const std::size_t scatter_count =
        offset_to_size(result.plan.entry_offsets.back(), "total scatter count");
    result.plan.scatter.assign(scatter_count, 0);
    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t dof_begin = offset_to_size(result.plan.element_dof_offsets[element],
                                                     "canonical element DOF offset");
        const std::size_t dof_end = offset_to_size(result.plan.element_dof_offsets[element + 1],
                                                   "canonical element DOF offset");
        std::size_t scatter_position =
            offset_to_size(result.plan.entry_offsets[element], "scatter offset");
        for (std::size_t local_row = dof_begin; local_row < dof_end; ++local_row) {
            for (std::size_t local_column = local_row; local_column < dof_end; ++local_column) {
                const GlobalDofIndex first = result.plan.element_dofs[local_row];
                const GlobalDofIndex second = result.plan.element_dofs[local_column];
                const GlobalDofIndex row = std::min(first, second);
                const GlobalDofIndex column = std::max(first, second);
                const std::size_t column_index = static_cast<std::size_t>(column);
                const std::size_t column_begin =
                    offset_to_size(result.matrix.col_ptr[column_index], "column offset");
                const std::size_t column_end =
                    offset_to_size(result.matrix.col_ptr[column_index + 1], "column offset");
                const auto begin =
                    result.matrix.row_idx.begin() + static_cast<std::ptrdiff_t>(column_begin);
                const auto end =
                    result.matrix.row_idx.begin() + static_cast<std::ptrdiff_t>(column_end);
                const auto found = std::lower_bound(begin, end, row);
                if (found == end || *found != row) {
                    throw std::logic_error(
                        "serial symbolic builder could not locate a scatter target");
                }
                result.plan.scatter[scatter_position++] = size_to_index(
                    column_begin + static_cast<std::size_t>(found - begin), "scatter target");
            }
        }
    }
    return result;
}

bool plans_match(const HelpInfo& left, const HelpInfo& right) noexcept {
    return left.element_ids == right.element_ids &&
           left.element_dof_offsets == right.element_dof_offsets &&
           left.element_dofs == right.element_dofs && left.entry_offsets == right.entry_offsets &&
           left.scatter == right.scatter;
}

struct SerialNumericKernelPlan {
    std::vector<std::size_t> local_dimensions;
    std::vector<std::size_t> value_begins;
    std::vector<std::size_t> scatter_begins;
};

SerialNumericKernelPlan prepare_serial_numeric_kernel(const HelpInfo& plan,
                                                      const ElementMatrixBatch& element_matrices,
                                                      std::size_t matrix_value_count) {
    // 尺寸、对称性和 scatter 范围不属于计时 kernel，提前检查可以保持串行基线
    // 的时间口径稳定。
    const std::size_t element_count = plan.element_ids.size();
    if (element_matrices.element_value_offsets.size() != element_count + 1) {
        throw std::invalid_argument("element matrix offsets do not match the plan");
    }
    if (plan.element_dof_offsets.size() != element_count + 1 ||
        plan.entry_offsets.size() != element_count + 1) {
        throw std::invalid_argument("serial numeric plan offsets are inconsistent");
    }
    if (element_matrices.element_value_offsets.front() != 0 ||
        element_matrices.element_value_offsets.back() !=
            size_to_offset(element_matrices.values_row_major.size(),
                           "element matrix value array size")) {
        throw std::invalid_argument("element matrix offsets are inconsistent");
    }

    SerialNumericKernelPlan kernel_plan;
    kernel_plan.local_dimensions.reserve(element_count);
    kernel_plan.value_begins.reserve(element_count);
    kernel_plan.scatter_begins.reserve(element_count);
    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t dof_begin =
            offset_to_size(plan.element_dof_offsets[element], "element DOF offset");
        const std::size_t dof_end =
            offset_to_size(plan.element_dof_offsets[element + 1], "element DOF offset");
        const std::size_t local_dimension = dof_end - dof_begin;
        const std::size_t value_begin = offset_to_size(
            element_matrices.element_value_offsets[element], "element matrix value offset");
        const std::size_t value_end = offset_to_size(
            element_matrices.element_value_offsets[element + 1], "element matrix value offset");
        if (value_end - value_begin !=
            checked_multiply(local_dimension, local_dimension, "local matrix size")) {
            throw std::invalid_argument("element matrix size does not match the plan");
        }
        const std::size_t scatter_begin =
            offset_to_size(plan.entry_offsets[element], "element scatter offset");
        const std::size_t scatter_end =
            offset_to_size(plan.entry_offsets[element + 1], "element scatter offset");
        const std::size_t triangular_count =
            checked_multiply(local_dimension, checked_add(local_dimension, 1, "local dimension"),
                             "local triangular count") /
            2;
        if (scatter_end - scatter_begin != triangular_count || scatter_end > plan.scatter.size()) {
            throw std::invalid_argument("serial numeric scatter offsets are inconsistent");
        }
        for (std::size_t position = value_begin; position < value_end; ++position) {
            if (!std::isfinite(element_matrices.values_row_major[position])) {
                throw std::invalid_argument("element matrices must contain finite values");
            }
        }
        for (std::size_t row = 0; row < local_dimension; ++row) {
            for (std::size_t column = row + 1; column < local_dimension; ++column) {
                const double upper =
                    element_matrices.values_row_major[value_begin + row * local_dimension + column];
                const double lower =
                    element_matrices.values_row_major[value_begin + column * local_dimension + row];
                const double difference = std::abs(upper - lower);
                const double scale = std::max(std::abs(upper), std::abs(lower));
                if (difference > kSymmetryAbsoluteTolerance &&
                    difference > kSymmetryRelativeTolerance * scale) {
                    throw std::invalid_argument(
                        "element matrices must be symmetric: element=" + std::to_string(element) +
                        ", row=" + std::to_string(row) + ", column=" + std::to_string(column) +
                        ", upper=" + std::to_string(upper) + ", lower=" + std::to_string(lower));
                }
            }
        }
        for (std::size_t position = scatter_begin; position < scatter_end; ++position) {
            if (offset_to_size(plan.scatter[position], "scatter target") >= matrix_value_count) {
                throw std::invalid_argument("serial numeric scatter target is out of range");
            }
        }
        kernel_plan.local_dimensions.push_back(local_dimension);
        kernel_plan.value_begins.push_back(value_begin);
        kernel_plan.scatter_begins.push_back(scatter_begin);
    }
    return kernel_plan;
}

void assemble_serial_numeric_kernel(const HelpInfo& plan,
                                    const ElementMatrixBatch& element_matrices,
                                    const SerialNumericKernelPlan& kernel_plan,
                                    std::vector<double>& values) noexcept {
    // 与候选数值路径一样，每个样本先清零，再按单元顺序累加局部上三角。
    std::fill(values.begin(), values.end(), 0.0);
    for (std::size_t element = 0; element < plan.element_ids.size(); ++element) {
        const std::size_t local_dimension = kernel_plan.local_dimensions[element];
        const std::size_t value_begin = kernel_plan.value_begins[element];
        std::size_t scatter_position = kernel_plan.scatter_begins[element];
        for (std::size_t row = 0; row < local_dimension; ++row) {
            for (std::size_t column = row; column < local_dimension; ++column) {
                const std::size_t target =
                    static_cast<std::size_t>(plan.scatter[scatter_position++]);
                values[target] +=
                    element_matrices.values_row_major[value_begin + row * local_dimension + column];
            }
        }
    }
}

struct DirectSerialContribution {
    GlobalDofIndex row = 0;
    GlobalDofIndex column = 0;
    double value = 0.0;
};

Csc3Matrix assemble_direct_serial(const FlatDofTopology& topology,
                                  const ElementMatrixBatch& element_matrices,
                                  GlobalDofIndex dimension) {
    // 与 CPU 主线 assemble_direct_no_symbolic_once() 采用同一算法定义：不预建
    // 稀疏结构或 scatter，先直接生成 (row,column,value) 贡献，再排序归并。
    // CSC3 只存对称上三角，因此这里只生成局部上三角贡献，并按 (column,row)
    // 排序；这是存储格式适配，不改变“无符号直接组装”的基准语义。
    const std::size_t element_count = topology.element_ids.size();
    if (topology.element_dof_offsets.size() != element_count + 1 ||
        element_matrices.element_value_offsets.size() != element_count + 1) {
        throw std::logic_error("direct serial input offsets are inconsistent");
    }
    std::size_t contribution_count = 0;
    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t dof_begin =
            offset_to_size(topology.element_dof_offsets[element], "element DOF offset");
        const std::size_t dof_end =
            offset_to_size(topology.element_dof_offsets[element + 1], "element DOF offset");
        if (dof_end < dof_begin || dof_end > topology.global_dof_indices.size()) {
            throw std::logic_error("direct serial element DOF range is invalid");
        }
        const std::size_t local_dimension = dof_end - dof_begin;
        const std::size_t value_begin =
            offset_to_size(element_matrices.element_value_offsets[element], "element value offset");
        const std::size_t value_end = offset_to_size(
            element_matrices.element_value_offsets[element + 1], "element value offset");
        const std::size_t expected_value_count =
            checked_multiply(local_dimension, local_dimension, "element matrix value count");
        if (value_end < value_begin || value_end > element_matrices.values_row_major.size() ||
            value_end - value_begin != expected_value_count) {
            throw std::logic_error("direct serial element matrix range is invalid");
        }
        const std::size_t triangular_count =
            checked_multiply(local_dimension, checked_add(local_dimension, 1, "local dimension"),
                             "direct serial triangular contribution count") /
            2;
        contribution_count =
            checked_add(contribution_count, triangular_count, "direct serial contribution count");
    }
    std::vector<DirectSerialContribution> contributions;
    contributions.reserve(contribution_count);

    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t dof_begin =
            offset_to_size(topology.element_dof_offsets[element], "element DOF offset");
        const std::size_t dof_end =
            offset_to_size(topology.element_dof_offsets[element + 1], "element DOF offset");
        const std::size_t local_dimension = dof_end - dof_begin;
        const std::size_t value_begin =
            offset_to_size(element_matrices.element_value_offsets[element], "element value offset");
        for (std::size_t local_row = 0; local_row < local_dimension; ++local_row) {
            for (std::size_t local_column = local_row; local_column < local_dimension;
                 ++local_column) {
                const GlobalDofIndex first = topology.global_dof_indices[dof_begin + local_row];
                const GlobalDofIndex second = topology.global_dof_indices[dof_begin + local_column];
                const GlobalDofIndex row = std::min(first, second);
                const GlobalDofIndex column = std::max(first, second);
                contributions.push_back(DirectSerialContribution{
                    row, column,
                    element_matrices.values_row_major[value_begin + local_row * local_dimension +
                                                      local_column]});
            }
        }
    }
    if (contributions.size() != contribution_count) {
        throw std::logic_error("direct serial contribution count is inconsistent");
    }
    std::sort(contributions.begin(), contributions.end(), [](const auto& left, const auto& right) {
        if (left.column != right.column) {
            return left.column < right.column;
        }
        return left.row < right.row;
    });

    Csc3Matrix matrix;
    matrix.n = dimension;
    const std::size_t dimension_size = static_cast<std::size_t>(dimension);
    matrix.col_ptr.assign(dimension_size + 1, 0);
    std::size_t nonzero_count = 0;
    for (std::size_t position = 0; position < contributions.size();) {
        const DirectSerialContribution& contribution = contributions[position];
        if (contribution.row < 0 || contribution.column < 0 || contribution.column >= dimension ||
            contribution.row > contribution.column) {
            throw std::logic_error("direct serial assembly produced an invalid CSC3 entry");
        }
        ++nonzero_count;
        const GlobalDofIndex row = contribution.row;
        const GlobalDofIndex column = contribution.column;
        do {
            ++position;
        } while (position < contributions.size() && contributions[position].row == row &&
                 contributions[position].column == column);
    }
    matrix.row_idx.resize(nonzero_count);
    matrix.values.resize(nonzero_count);
    std::size_t current_column = 0;
    std::size_t output_position = 0;
    for (std::size_t position = 0; position < contributions.size();) {
        const GlobalDofIndex row = contributions[position].row;
        const GlobalDofIndex column_index = contributions[position].column;
        const std::size_t column = static_cast<std::size_t>(column_index);
        while (current_column < column) {
            matrix.col_ptr[current_column + 1] =
                size_to_index(output_position, "direct serial CSC3 column offset");
            ++current_column;
        }
        double sum = 0.0;
        do {
            sum += contributions[position].value;
            ++position;
        } while (position < contributions.size() && contributions[position].row == row &&
                 contributions[position].column == column_index);
        if (!std::isfinite(sum)) {
            throw std::runtime_error("direct serial assembly produced a non-finite value");
        }
        matrix.row_idx[output_position] = row;
        matrix.values[output_position] = sum;
        ++output_position;
    }
    while (current_column < dimension_size) {
        matrix.col_ptr[current_column + 1] =
            size_to_index(nonzero_count, "direct serial CSC3 column offset");
        ++current_column;
    }
    return matrix;
}

class ScaledNorm {
  public:
    void add(double value) noexcept {
        const double magnitude = std::abs(value);
        if (!std::isfinite(magnitude)) {
            finite_ = false;
            return;
        }
        if (magnitude == 0.0) {
            return;
        }
        if (scale_ < magnitude) {
            const double ratio = scale_ / magnitude;
            sum_squares_ = 1.0 + sum_squares_ * ratio * ratio;
            scale_ = magnitude;
        } else {
            const double ratio = magnitude / scale_;
            sum_squares_ += ratio * ratio;
        }
    }

    [[nodiscard]] bool finite() const noexcept {
        return finite_;
    }

    [[nodiscard]] bool zero() const noexcept {
        return scale_ == 0.0;
    }

    [[nodiscard]] double value() const noexcept {
        if (!finite_) {
            return std::numeric_limits<double>::infinity();
        }
        return scale_ == 0.0 ? 0.0 : scale_ * std::sqrt(sum_squares_);
    }

    [[nodiscard]] double relative_to(const ScaledNorm& reference,
                                     double reference_floor) const noexcept {
        if (!finite_ || !reference.finite_) {
            return std::numeric_limits<double>::infinity();
        }
        if (zero()) {
            return 0.0;
        }
        if (reference.value() < reference_floor) {
            return value() / reference_floor;
        }
        return (scale_ / reference.scale_) * std::sqrt(sum_squares_ / reference.sum_squares_);
    }

  private:
    double scale_ = 0.0;
    double sum_squares_ = 1.0;
    bool finite_ = true;
};

BenchmarkCorrectness compare_sparse(const Csc3Matrix& candidate, const Csc3Matrix& serial_structure,
                                    const std::vector<double>& serial_values) {
    BenchmarkCorrectness result;
    for (const double reference_value : serial_values) {
        result.reference_max_absolute_value =
            std::max(result.reference_max_absolute_value, std::abs(reference_value));
    }
    result.max_absolute_tolerance =
        kMaximumAbsoluteBaseTolerance +
        kMaximumAbsoluteScaleTolerance * result.reference_max_absolute_value;
    result.structure_matches = candidate.n == serial_structure.n &&
                               candidate.col_ptr == serial_structure.col_ptr &&
                               candidate.row_idx == serial_structure.row_idx &&
                               candidate.values.size() == serial_values.size();
    if (!result.structure_matches) {
        result.relative_frobenius_error = kComparisonFailureError;
        result.max_absolute_error = kComparisonFailureError;
        result.status = "FAIL";
        return result;
    }

    ScaledNorm difference_norm;
    ScaledNorm reference_norm;
    double max_absolute_error = 0.0;
    for (std::size_t column = 0; column < static_cast<std::size_t>(candidate.n); ++column) {
        const std::size_t begin =
            offset_to_size(candidate.col_ptr[column], "candidate column offset");
        const std::size_t end =
            offset_to_size(candidate.col_ptr[column + 1], "candidate column offset");
        for (std::size_t position = begin; position < end; ++position) {
            const double candidate_value = candidate.values[position];
            const double reference_value = serial_values[position];
            const double difference = candidate_value - reference_value;
            difference_norm.add(difference);
            reference_norm.add(reference_value);
            if (candidate.row_idx[position] != static_cast<GlobalDofIndex>(column)) {
                difference_norm.add(difference);
                reference_norm.add(reference_value);
            }
            max_absolute_error =
                std::max(max_absolute_error, std::abs(candidate_value - reference_value));
        }
    }
    result.relative_frobenius_error = difference_norm.relative_to(reference_norm, kNormFloor);
    result.max_absolute_error = max_absolute_error;
    const bool finite = std::isfinite(result.relative_frobenius_error) &&
                        std::isfinite(result.max_absolute_error) &&
                        std::isfinite(result.reference_max_absolute_value) &&
                        std::isfinite(result.max_absolute_tolerance);
    if (!finite) {
        result.relative_frobenius_error = kComparisonFailureError;
        result.max_absolute_error = kComparisonFailureError;
    }
    result.status = finite && result.relative_frobenius_error <= kRelativeFrobeniusTolerance &&
                            result.max_absolute_error <= result.max_absolute_tolerance
                        ? "PASS"
                        : "FAIL";
    return result;
}

std::size_t vector_payload_bytes(std::size_t count, std::size_t element_size, const char* label) {
    return checked_multiply(count, element_size, label);
}

std::size_t estimated_persistent_bytes(const Csc3Matrix& matrix, const HelpInfo& plan) {
    std::size_t total = 0;
    const auto add_payload = [&total](std::size_t count, std::size_t element_size,
                                      const char* label) {
        total = checked_add(total, vector_payload_bytes(count, element_size, label),
                            "persistent vector payload bytes");
    };
    add_payload(matrix.col_ptr.size(), sizeof(Index), "col_ptr bytes");
    add_payload(matrix.row_idx.size(), sizeof(GlobalDofIndex), "row_indices bytes");
    add_payload(matrix.values.size(), sizeof(double), "values bytes");
    add_payload(plan.element_ids.size(), sizeof(ElementId), "element_ids bytes");
    add_payload(plan.element_dof_offsets.size(), sizeof(Index), "element_dof_offsets bytes");
    add_payload(plan.element_dofs.size(), sizeof(GlobalDofIndex), "global_dof_indices bytes");
    add_payload(plan.entry_offsets.size(), sizeof(Index), "entry_offsets bytes");
    add_payload(plan.scatter.size(), sizeof(Index), "scatter bytes");
    return total;
}

CandidateTimings assemble_parallel_numeric(AssemblyHelper& helper, Csc3Matrix& csc3,
                                           const HelpInfo& help_info,
                                           const ElementMatrixBatch& element_matrices,
                                           int thread_count, int& observed_thread_count) {
    // 这里照研发侧的调用方式执行：清零后由外部 OpenMP 循环逐单元调用 add()。
    CandidateTimings timings{};
    const Clock::time_point total_start = Clock::now();
    const Clock::time_point reset_start = Clock::now();
    helper.zero_values(csc3);
    const Clock::time_point reset_end = Clock::now();
    timings.numeric_reset_ms = elapsed_ms(reset_start, reset_end);

    const std::int64_t element_count = static_cast<std::int64_t>(help_info.element_ids.size());
    const Clock::time_point kernel_start = Clock::now();
#pragma omp parallel num_threads(thread_count)
    {
#pragma omp single
        {
            observed_thread_count = omp_get_num_threads();
        }
#pragma omp for schedule(static)
        for (std::int64_t element_loop = 0; element_loop < element_count; ++element_loop) {
            const std::size_t element = static_cast<std::size_t>(element_loop);
            const std::size_t begin = offset_to_size(
                element_matrices.element_value_offsets[element], "element matrix offset");
            const std::size_t end = offset_to_size(
                element_matrices.element_value_offsets[element + 1], "element matrix offset");
            helper.add(csc3, help_info,
                       ElementStiffness{help_info.element_ids[element],
                                        element_matrices.values_row_major.data() + begin,
                                        end - begin});
        }
    }
    const Clock::time_point kernel_end = Clock::now();
    timings.numeric_kernel_ms = elapsed_ms(kernel_start, kernel_end);
    timings.numeric_total_ms = elapsed_ms(total_start, kernel_end);
    return timings;
}

std::vector<double> measured_tail(const std::vector<double>& values, std::size_t warmup_count) {
    // 预热样本仍保存在原始记录中，但不进入均值、中位数和变异系数。
    return std::vector<double>(values.begin() + static_cast<std::ptrdiff_t>(warmup_count),
                               values.end());
}

double positive_speedup(double serial_median, double candidate_median) {
    if (!std::isfinite(serial_median) || !std::isfinite(candidate_median) || serial_median < 0.0 ||
        candidate_median <= 0.0) {
        throw std::runtime_error("benchmark timings cannot produce a finite nonnegative speedup");
    }
    const double speedup = serial_median / candidate_median;
    if (!std::isfinite(speedup) || speedup < 0.0) {
        throw std::runtime_error("benchmark speedup must be finite and nonnegative");
    }
    return speedup;
}

void merge_correctness(BenchmarkCorrectness& aggregate, const BenchmarkCorrectness& current) {
    aggregate.structure_matches = aggregate.structure_matches && current.structure_matches;
    aggregate.relative_frobenius_error =
        std::max(aggregate.relative_frobenius_error, current.relative_frobenius_error);
    aggregate.max_absolute_error =
        std::max(aggregate.max_absolute_error, current.max_absolute_error);
    aggregate.reference_max_absolute_value =
        std::max(aggregate.reference_max_absolute_value, current.reference_max_absolute_value);
    aggregate.max_absolute_tolerance =
        kMaximumAbsoluteBaseTolerance +
        kMaximumAbsoluteScaleTolerance * aggregate.reference_max_absolute_value;
    if (current.status != "PASS") {
        aggregate.status = "FAIL";
    }
}

} // namespace

SummaryStatistics summarize_measured_values(const std::vector<double>& values) {
    if (values.empty()) {
        throw std::invalid_argument("statistics require at least one measured value");
    }
    for (const double value : values) {
        if (!std::isfinite(value) || value < 0.0) {
            throw std::invalid_argument("statistics values must be finite and nonnegative");
        }
    }
    std::vector<double> sorted = values;
    std::sort(sorted.begin(), sorted.end());
    long double sum = 0.0L;
    for (const double value : values) {
        sum += static_cast<long double>(value);
    }
    const long double mean = sum / static_cast<long double>(values.size());
    long double squared_difference_sum = 0.0L;
    for (const double value : values) {
        const long double difference = static_cast<long double>(value) - mean;
        squared_difference_sum += difference * difference;
    }
    const long double variance = squared_difference_sum / static_cast<long double>(values.size());
    const std::size_t middle = sorted.size() / 2;
    const double median = sorted.size() % 2 == 0
                              ? sorted[middle - 1] + (sorted[middle] - sorted[middle - 1]) / 2.0
                              : sorted[middle];

    SummaryStatistics result;
    result.sample_count = values.size();
    result.mean_ms = static_cast<double>(mean);
    result.median_ms = median;
    result.population_standard_deviation_ms = static_cast<double>(std::sqrt(variance));
    result.minimum_ms = sorted.front();
    result.maximum_ms = sorted.back();
    if (result.mean_ms == 0.0) {
        if (result.maximum_ms != 0.0) {
            throw std::runtime_error(
                "zero-mean nonzero samples have an undefined coefficient of variation");
        }
        result.coefficient_of_variation = 0.0;
    } else {
        result.coefficient_of_variation = result.population_standard_deviation_ms / result.mean_ms;
    }
    if (!std::isfinite(result.mean_ms) || !std::isfinite(result.median_ms) ||
        !std::isfinite(result.population_standard_deviation_ms) ||
        !std::isfinite(result.coefficient_of_variation)) {
        throw std::runtime_error("statistics are not finite");
    }
    return result;
}

BenchmarkResult run_generated_benchmark(const BenchmarkConfiguration& configuration) {
    // 这个入口只接受生成式 Tet4/Hex8，主要供 CI 和小型正确性测试使用。
    if (configuration.benchmark_case == BenchmarkCase::WindHub) {
        throw std::invalid_argument(
            "run_generated_benchmark accepts only generated benchmark cases");
    }
    return run_benchmark(configuration);
}

PerformanceGate
evaluate_performance_gate(BenchmarkCase benchmark_case, PerformanceEvidenceLevel evidence_level,
                          const SerialBenchmarkSummary& serial_measured,
                          const std::vector<ThreadBenchmarkSummary>& per_thread_measured,
                          const ScatterCorrectness& scatter_correctness) {
    const std::string evidence_level_text = evidence_level_name(evidence_level);
    PerformanceGate gate;
    switch (benchmark_case) {
    case BenchmarkCase::GeneratedTet4:
    case BenchmarkCase::GeneratedHex8:
        if (evidence_level_text == "formal") {
            throw std::invalid_argument("formal performance gates are restricted to WindHub");
        }
        gate.status = "NOT_APPLICABLE_GENERATED_CASE";
        return gate;
    case BenchmarkCase::WindHub:
        break;
    default:
        throw std::invalid_argument("invalid benchmark case");
    }

    gate.applicable = true;
    const double serial_symbolic_cv = serial_measured.symbolic_total_ms.coefficient_of_variation;
    const double serial_numeric_cv = serial_measured.numeric_total_ms.coefficient_of_variation;
    if (!std::isfinite(serial_symbolic_cv) || serial_symbolic_cv < 0.0 ||
        !std::isfinite(serial_numeric_cv) || serial_numeric_cv < 0.0) {
        throw std::invalid_argument(
            "performance gate serial statistics must be finite and nonnegative");
    }
    gate.serial_symbolic_cv_requirement_met =
        serial_symbolic_cv <= gate.maximum_coefficient_of_variation;
    gate.serial_numeric_cv_requirement_met =
        serial_numeric_cv <= gate.maximum_coefficient_of_variation;

    if (scatter_correctness.symbolic_plan_match_count >
            scatter_correctness.symbolic_plan_check_count ||
        scatter_correctness.numeric_setup_plan_match_count >
            scatter_correctness.numeric_setup_plan_check_count) {
        throw std::invalid_argument("scatter correctness match counts exceed check counts");
    }
    const bool scatter_counts_pass = scatter_correctness.symbolic_plan_check_count > 0 &&
                                     scatter_correctness.symbolic_plan_match_count ==
                                         scatter_correctness.symbolic_plan_check_count &&
                                     scatter_correctness.numeric_setup_plan_check_count > 0 &&
                                     scatter_correctness.numeric_setup_plan_match_count ==
                                         scatter_correctness.numeric_setup_plan_check_count;
    const std::string expected_scatter_status = scatter_counts_pass ? "PASS" : "FAIL";
    if (scatter_correctness.status != expected_scatter_status) {
        throw std::invalid_argument("scatter correctness status contradicts its counts");
    }
    gate.scatter_requirement_met = scatter_counts_pass;

    std::set<int> observed_threads;
    for (const ThreadBenchmarkSummary& summary : per_thread_measured) {
        if (summary.thread_count <= 0 || !observed_threads.insert(summary.thread_count).second) {
            throw std::invalid_argument(
                "performance gate thread counts must be positive and unique");
        }
        if (!std::isfinite(summary.numeric_speedup) || summary.numeric_speedup < 0.0 ||
            !std::isfinite(summary.symbolic_speedup) || summary.symbolic_speedup < 0.0 ||
            !std::isfinite(summary.numeric_algorithm_ms.coefficient_of_variation) ||
            summary.numeric_algorithm_ms.coefficient_of_variation < 0.0 ||
            !std::isfinite(summary.symbolic_total_ms.coefficient_of_variation) ||
            summary.symbolic_total_ms.coefficient_of_variation < 0.0) {
            throw std::invalid_argument(
                "performance gate statistics must be finite and nonnegative");
        }
        if (summary.thread_count <= 1) {
            continue;
        }
        const bool numeric_eligible = summary.numeric_speedup >= gate.numeric_speedup_threshold &&
                                      summary.numeric_algorithm_ms.coefficient_of_variation <=
                                          gate.maximum_coefficient_of_variation;
        if (numeric_eligible && !gate.numeric_requirement_met) {
            gate.numeric_requirement_met = true;
            gate.numeric_thread_count = summary.thread_count;
        }
        const bool symbolic_eligible = summary.symbolic_speedup > gate.symbolic_speedup_threshold &&
                                       summary.symbolic_total_ms.coefficient_of_variation <=
                                           gate.maximum_coefficient_of_variation;
        if (symbolic_eligible && !gate.symbolic_requirement_met) {
            gate.symbolic_requirement_met = true;
            gate.symbolic_thread_count = summary.thread_count;
        }
    }

    if (evidence_level != PerformanceEvidenceLevel::Formal) {
        gate.status = evidence_level == PerformanceEvidenceLevel::CiSmoke
                          ? "NON_FORMAL_CI_SMOKE"
                          : "NON_FORMAL_LOCAL_SMOKE";
        return gate;
    }
    gate.performance_requirements_met =
        gate.numeric_requirement_met && gate.symbolic_requirement_met &&
        gate.serial_numeric_cv_requirement_met && gate.serial_symbolic_cv_requirement_met;
    gate.formal_requirements_met =
        gate.performance_requirements_met && gate.scatter_requirement_met;
    gate.status = gate.formal_requirements_met ? "PASS" : "FAIL";
    return gate;
}

BenchmarkResult run_benchmark(const BenchmarkConfiguration& configuration) {
    // 一次调用完整处理一个线程列表。各线程配置依次执行，不会在同一进程内并发跑
    // 多组实验；正式 Windows runner 还会把每个样本放进独立子进程。
    validate_configuration(configuration);

    // 输入准备不计入组装时间。生成式算例在这里创建，工程算例在这里读取 .inp。
    const Clock::time_point input_start = Clock::now();
    AssemblyCase assembly_case = prepare_benchmark_case(configuration);
    const DofCodingInfo dof_coding_info = make_dof_coding_info(assembly_case);
    const double input_prepare_ms = elapsed_ms(input_start, Clock::now());
    const ElementType element_type = assembly_case.element_type;

    const std::size_t warmup_count = static_cast<std::size_t>(configuration.warmup_count);
    const std::size_t repeat_count = static_cast<std::size_t>(configuration.repeat_count);
    const std::size_t total_sample_count =
        checked_add(warmup_count, repeat_count, "total benchmark sample count");
    // 串行符号阶段每个样本都从头建立结构；最后一个样本留下来作为比较基线。
    std::vector<double> serial_symbolic_times;
    serial_symbolic_times.reserve(total_sample_count);
    SerialSymbolicState serial_state;
    for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
        const Clock::time_point start = Clock::now();
        SerialSymbolicState sample_state = build_serial_symbolic(assembly_case.element_dof_map);
        const double duration = elapsed_ms(start, Clock::now());
        if (!std::isfinite(duration) || duration < 0.0) {
            throw std::runtime_error("serial symbolic timing is invalid");
        }
        serial_symbolic_times.push_back(duration);
        if (sample_index == total_sample_count - 1) {
            serial_state = std::move(sample_state);
        }
    }

    // 候选数值组装需要一份 AssemblyHelper 生成的结构。先用 1 线程建立它，
    // 随后另行计时独立串行 kernel，二者不能混成同一项时间。
    AssemblyHelper numeric_reference_helper;
    Csc3Matrix numeric_reference_matrix;
    HelpInfo numeric_reference_help;
    BenchmarkAccess::symbolic(numeric_reference_helper, numeric_reference_matrix,
                              numeric_reference_help, dof_coding_info, 1);
    if (!BenchmarkAccess::symbolic_used_requested_team_in_all_regions(numeric_reference_helper)) {
        throw std::runtime_error(
            "OpenMP did not provide the requested team for numeric reference setup");
    }
    std::vector<double> serial_values(serial_state.matrix.values.size(), 0.0);
    const SerialNumericKernelPlan serial_numeric_plan = prepare_serial_numeric_kernel(
        serial_state.plan, assembly_case.element_matrices, serial_values.size());
    std::vector<double> serial_numeric_times;
    serial_numeric_times.reserve(total_sample_count);
    for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
        const Clock::time_point start = Clock::now();
        assemble_serial_numeric_kernel(serial_state.plan, assembly_case.element_matrices,
                                       serial_numeric_plan, serial_values);
        const double duration = elapsed_ms(start, Clock::now());
        if (!std::isfinite(duration) || duration < 0.0) {
            throw std::runtime_error("serial numeric timing is invalid");
        }
        serial_numeric_times.push_back(duration);
    }

    // 直接串行参考在一次遍历中同时发现稀疏位置并累加数值。它不复用上面的
    // 两阶段结构或 scatter；后者只保留给符号、数值阶段的诊断性对照。
    std::vector<double> serial_direct_times;
    serial_direct_times.reserve(total_sample_count);
    Csc3Matrix direct_serial_reference;
    for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
        const Clock::time_point start = Clock::now();
        Csc3Matrix sample_reference = assemble_direct_serial(
            assembly_case.element_dof_map, assembly_case.element_matrices,
            size_to_index(assembly_case.force.size(), "direct serial matrix dimension"));
        const double duration = elapsed_ms(start, Clock::now());
        if (!std::isfinite(duration) || duration < 0.0) {
            throw std::runtime_error("direct serial timing is invalid");
        }
        serial_direct_times.push_back(duration);
        if (sample_index == total_sample_count - 1) {
            direct_serial_reference = std::move(sample_reference);
        }
    }

    BenchmarkResult result;
    result.configuration = configuration;
    result.case_name = assembly_case.name;
    result.element_type = element_type_name(element_type);
    result.node_count = assembly_case.nodes.size();
    result.element_count = assembly_case.element_dof_map.element_ids.size();
    result.dof_count = static_cast<std::size_t>(direct_serial_reference.n);
    result.nonzero_count = direct_serial_reference.values.size();
    result.input_prepare_ms = input_prepare_ms;
    result.estimated_persistent_bytes =
        estimated_persistent_bytes(numeric_reference_matrix, numeric_reference_help);
    result.performance_evidence_level =
        evidence_level_name(configuration.performance_evidence_level);
    result.correctness.structure_matches = true;
    result.correctness.status = "PASS";

    const std::vector<double> measured_serial_symbolic =
        measured_tail(serial_symbolic_times, warmup_count);
    const std::vector<double> measured_serial_numeric =
        measured_tail(serial_numeric_times, warmup_count);
    const std::vector<double> measured_serial_direct =
        measured_tail(serial_direct_times, warmup_count);
    result.serial_measured.direct_total_ms = summarize_measured_values(measured_serial_direct);
    result.serial_measured.symbolic_total_ms = summarize_measured_values(measured_serial_symbolic);
    result.serial_measured.numeric_total_ms = summarize_measured_values(measured_serial_numeric);

    const std::size_t samples_per_thread = total_sample_count;
    result.samples.reserve(checked_multiply(samples_per_thread, configuration.thread_counts.size(),
                                            "raw benchmark sample count"));
    result.per_thread_measured.reserve(configuration.thread_counts.size());

    // 各线程配置按调用方给出的顺序逐项执行，一个配置完成后才开始下一个。
    for (const int thread_count : configuration.thread_counts) {
        std::vector<CandidateTimings> symbolic_timings;
        std::vector<bool> symbolic_plan_matches;
        symbolic_timings.reserve(samples_per_thread);
        symbolic_plan_matches.reserve(samples_per_thread);
        for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
            AssemblyHelper symbolic_helper;
            Csc3Matrix symbolic_matrix;
            HelpInfo symbolic_help;
            BenchmarkAccess::symbolic(symbolic_helper, symbolic_matrix, symbolic_help,
                                      dof_coding_info, thread_count);
            if (!BenchmarkAccess::symbolic_used_requested_team_in_all_regions(symbolic_helper)) {
                throw std::runtime_error(
                    "OpenMP did not provide the requested team in every symbolic region");
            }
            symbolic_timings.push_back(BenchmarkAccess::timings(symbolic_helper));
            symbolic_plan_matches.push_back(plans_match(symbolic_help, serial_state.plan));
        }

        AssemblyHelper numeric_helper;
        Csc3Matrix numeric_matrix;
        HelpInfo numeric_help;
        BenchmarkAccess::symbolic(numeric_helper, numeric_matrix, numeric_help, dof_coding_info,
                                  thread_count);
        if (!BenchmarkAccess::symbolic_used_requested_team_in_all_regions(numeric_helper)) {
            throw std::runtime_error("OpenMP did not provide the requested team for numeric setup");
        }
        const bool numeric_setup_plan_matches_serial = plans_match(numeric_help, serial_state.plan);
        std::vector<CandidateTimings> numeric_timings;
        numeric_timings.reserve(samples_per_thread);
        int numeric_thread_count_observed = 0;
        for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
            int observed_thread_count = 0;
            numeric_timings.push_back(assemble_parallel_numeric(
                numeric_helper, numeric_matrix, numeric_help, assembly_case.element_matrices,
                thread_count, observed_thread_count));
            if (observed_thread_count != thread_count) {
                throw std::runtime_error("OpenMP did not provide the requested numeric team");
            }
            numeric_thread_count_observed = observed_thread_count;
            merge_correctness(result.correctness,
                              compare_sparse(numeric_matrix, direct_serial_reference,
                                             direct_serial_reference.values));
        }

        // warmup 样本留在原始记录中；下面的统计数组只收集 measured 部分。
        std::vector<double> pattern_values;
        std::vector<double> scatter_values;
        std::vector<double> symbolic_total_values;
        std::vector<double> reset_values;
        std::vector<double> kernel_values;
        std::vector<double> numeric_algorithm_values;
        std::vector<double> numeric_total_values;
        std::vector<double> amortized_values;
        for (std::size_t sample_index = warmup_count; sample_index < total_sample_count;
             ++sample_index) {
            const CandidateTimings& symbolic = symbolic_timings[sample_index];
            const CandidateTimings& numeric = numeric_timings[sample_index];
            pattern_values.push_back(symbolic.symbolic_pattern_ms);
            scatter_values.push_back(symbolic.symbolic_scatter_ms);
            symbolic_total_values.push_back(symbolic.symbolic_total_ms);
            reset_values.push_back(numeric.numeric_reset_ms);
            kernel_values.push_back(numeric.numeric_kernel_ms);
            numeric_algorithm_values.push_back(numeric.numeric_reset_ms +
                                               numeric.numeric_kernel_ms);
            numeric_total_values.push_back(numeric.numeric_total_ms);
            amortized_values.push_back(symbolic.symbolic_total_ms /
                                           static_cast<double>(configuration.amortization_count) +
                                       numeric.numeric_total_ms);
        }

        ThreadBenchmarkSummary summary;
        summary.thread_count = thread_count;
        summary.symbolic_thread_count_observed = numeric_helper.symbolic_thread_count_used();
        summary.numeric_thread_count_observed = numeric_thread_count_observed;
        summary.symbolic_plan_check_count = symbolic_plan_matches.size();
        summary.symbolic_plan_match_count = static_cast<std::size_t>(
            std::count(symbolic_plan_matches.begin(), symbolic_plan_matches.end(), true));
        summary.numeric_setup_plan_matches_serial = numeric_setup_plan_matches_serial;
        summary.scatter_status =
            summary.symbolic_plan_match_count == summary.symbolic_plan_check_count &&
                    summary.numeric_setup_plan_matches_serial
                ? "PASS"
                : "FAIL";
        summary.symbolic_pattern_ms = summarize_measured_values(pattern_values);
        summary.symbolic_scatter_ms = summarize_measured_values(scatter_values);
        summary.symbolic_total_ms = summarize_measured_values(symbolic_total_values);
        summary.numeric_reset_ms = summarize_measured_values(reset_values);
        summary.numeric_kernel_ms = summarize_measured_values(kernel_values);
        summary.numeric_algorithm_ms = summarize_measured_values(numeric_algorithm_values);
        summary.numeric_total_ms = summarize_measured_values(numeric_total_values);
        summary.amortized_total_ms = summarize_measured_values(amortized_values);
        summary.symbolic_speedup =
            positive_speedup(result.serial_measured.symbolic_total_ms.median_ms,
                             summary.symbolic_total_ms.median_ms);
        summary.numeric_speedup =
            positive_speedup(result.serial_measured.numeric_total_ms.median_ms,
                             summary.numeric_algorithm_ms.median_ms);
        result.per_thread_measured.push_back(summary);
        result.scatter_correctness.symbolic_plan_check_count += summary.symbolic_plan_check_count;
        result.scatter_correctness.symbolic_plan_match_count += summary.symbolic_plan_match_count;
        ++result.scatter_correctness.numeric_setup_plan_check_count;
        if (summary.numeric_setup_plan_matches_serial) {
            ++result.scatter_correctness.numeric_setup_plan_match_count;
        }

        for (std::size_t sample_index = 0; sample_index < total_sample_count; ++sample_index) {
            const std::size_t index = sample_index;
            BenchmarkSample sample;
            sample.thread_count = thread_count;
            sample.sample_index = sample_index;
            sample.sample_kind =
                sample_index < warmup_count ? SampleKind::Warmup : SampleKind::Measured;
            sample.input_prepare_ms = input_prepare_ms;
            sample.serial_direct_ms = serial_direct_times[index];
            sample.serial_symbolic_ms = serial_symbolic_times[index];
            sample.serial_numeric_ms = serial_numeric_times[index];
            sample.candidate_timings = symbolic_timings[index];
            sample.candidate_timings.numeric_reset_ms = numeric_timings[index].numeric_reset_ms;
            sample.candidate_timings.numeric_kernel_ms = numeric_timings[index].numeric_kernel_ms;
            sample.candidate_timings.numeric_total_ms = numeric_timings[index].numeric_total_ms;
            sample.amortized_total_ms = sample.candidate_timings.symbolic_total_ms /
                                            static_cast<double>(configuration.amortization_count) +
                                        sample.candidate_timings.numeric_total_ms;
            sample.symbolic_speedup = summary.symbolic_speedup;
            sample.numeric_speedup = summary.numeric_speedup;
            sample.symbolic_plan_matches_serial = symbolic_plan_matches[index];
            sample.numeric_setup_plan_matches_serial = numeric_setup_plan_matches_serial;
            result.samples.push_back(sample);
        }
    }

    // 根级状态由全部原始检查数重新汇总，不直接沿用某一个线程配置的结果。
    result.scatter_correctness.status =
        result.scatter_correctness.symbolic_plan_check_count > 0 &&
                result.scatter_correctness.symbolic_plan_match_count ==
                    result.scatter_correctness.symbolic_plan_check_count &&
                result.scatter_correctness.numeric_setup_plan_check_count > 0 &&
                result.scatter_correctness.numeric_setup_plan_match_count ==
                    result.scatter_correctness.numeric_setup_plan_check_count
            ? "PASS"
            : "FAIL";

    if (result.correctness.status != "PASS") {
        result.correctness.status = "FAIL";
    }
    result.performance_gate = evaluate_performance_gate(
        configuration.benchmark_case, configuration.performance_evidence_level,
        result.serial_measured, result.per_thread_measured, result.scatter_correctness);
    result.performance_gate_status = result.performance_gate.status;
    // 工程网格只验证组装矩阵。额外的小型 Tet4/Hex8 算例用于检查位移和残差，
    // 证明候选矩阵能够进入完整求解流程。
    const int validation_threads = select_validation_thread_count(configuration.thread_counts);
    result.validation_cases.push_back(
        validate_case(make_cube_case(ElementType::Tet4, 1, 1, 1), validation_threads));
    result.validation_cases.push_back(
        validate_case(make_cube_case(ElementType::Hex8, 1, 1, 1), validation_threads));
    return result;
}

} // namespace csc3_demo::evidence
