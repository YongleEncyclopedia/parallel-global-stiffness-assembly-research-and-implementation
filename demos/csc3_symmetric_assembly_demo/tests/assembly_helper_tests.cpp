#include "csc3_demo/assembly_helper.h"

// 核心类的单元测试。这里直接检查 CSC3 数组和 HelpInfo，便于接口改动后尽快发现
// 结构、散射位置或 atomic 累加行为的变化。

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#ifndef _OPENMP
#error "The CSC3 tests require OpenMP"
#endif

#include <omp.h>

namespace {

using namespace csc3_demo;

static_assert(std::is_same_v<Index, std::int32_t>);
static_assert(std::is_same_v<ElementId, std::int32_t>);
static_assert(std::is_same_v<NodeId, std::int32_t>);
static_assert(
    noexcept(std::declval<const AssemblyHelper&>().zero_values(std::declval<Csc3Matrix&>())));
static_assert(noexcept(std::declval<const AssemblyHelper&>().symbolic_thread_count_used()));
static_assert(noexcept(openmp_enabled()));
static_assert(noexcept(max_openmp_threads()));

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
void require_equal(const T& actual, const T& expected, const std::string& label) {
    if (actual != expected) {
        throw std::runtime_error(label + " mismatch");
    }
}

void require_close(const std::vector<double>& actual, const std::vector<double>& expected,
                   const std::string& label, double tolerance = 1.0e-11) {
    require_equal(actual.size(), expected.size(), label + " size");
    for (std::size_t i = 0; i < actual.size(); ++i) {
        const double scale = std::max({1.0, std::abs(actual[i]), std::abs(expected[i])});
        if (!std::isfinite(actual[i]) || std::abs(actual[i] - expected[i]) > tolerance * scale) {
            throw std::runtime_error(label + " differs at index " + std::to_string(i));
        }
    }
}

template <typename Exception, typename Function>
void require_throws(Function&& function, const std::string& label) {
    try {
        std::forward<Function>(function)();
    } catch (const Exception&) {
        return;
    } catch (const std::exception& exception) {
        throw std::runtime_error(label + " threw the wrong exception: " + exception.what());
    }
    throw std::runtime_error(label + " did not throw");
}

// 两个二自由度单元首尾相接：单元 10 使用自由度 0、1，单元 20 使用自由度
// 1、2。共享的自由度 1 可以同时检查散射表和数值叠加。
DofCodingInfo chain_dof_coding_info() {
    return DofCodingInfo{
        {{20, {1, 2}}, {10, {0, 1}}},
        {{0, {0}}, {1, {1}}, {2, {2}}},
    };
}

ElementStiffness stiffness_view(ElementId elem_id, const std::vector<double>& values) {
    return ElementStiffness{elem_id, values.data(), values.size()};
}

void assemble_chain(AssemblyHelper& helper, Csc3Matrix& csc3, const HelpInfo& help_info,
                    int thread_count) {
    const std::vector<double> element_10{3.0, -2.0, -2.0, 3.0};
    const std::vector<double> element_20{2.0, -1.0, -1.0, 2.0};
    helper.zero_values(csc3);
#pragma omp parallel for schedule(static) num_threads(thread_count)
    for (int element = 0; element < 2; ++element) {
        const ElementId elem_id = help_info.element_ids[static_cast<std::size_t>(element)];
        const auto& values = elem_id == 10 ? element_10 : element_20;
        helper.add(csc3, help_info, stiffness_view(elem_id, values));
    }
}

// 先用三自由度链式模型锁定最基本的接口结果。这个模型足够小，期望的 CSC3 数组
// 可以直接写在测试里，失败时也能一眼看出是列结构、scatter 还是数值出了问题。
void test_required_interface_and_exact_result() {
    omp_set_dynamic(0);
    omp_set_num_threads(std::min(4, max_openmp_threads()));

    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, chain_dof_coding_info());

    require_equal(csc3.n, Index{3}, "matrix dimension");
    require_equal(csc3.col_ptr, std::vector<Index>{0, 1, 3, 5}, "column pointers");
    require_equal(csc3.row_idx, std::vector<Index>{0, 0, 1, 1, 2}, "row indices");
    require_equal(help_info.element_ids, std::vector<ElementId>{10, 20}, "element IDs");
    require_equal(help_info.element_dof_offsets, std::vector<Index>{0, 2, 4}, "DOF offsets");
    require_equal(help_info.element_dofs, std::vector<Index>{0, 1, 1, 2}, "element DOFs");
    require_equal(help_info.entry_offsets, std::vector<Index>{0, 3, 6}, "entry offsets");
    require_equal(help_info.scatter, std::vector<Index>{0, 1, 2, 2, 3, 4}, "scatter table");

    assemble_chain(helper, csc3, help_info, std::min(2, max_openmp_threads()));
    require_close(csc3.values, {3.0, -2.0, 5.0, -1.0, 2.0}, "assembled values");
}

// 符号组装采用不同线程数时，CSC3 结构和每个单元的散射位置应逐项相同。
void test_symbolic_is_deterministic() {
    Csc3Matrix baseline_matrix;
    HelpInfo baseline_help;
    AssemblyHelper baseline_helper;
    omp_set_num_threads(1);
    baseline_helper.Symbolic(baseline_matrix, baseline_help, chain_dof_coding_info());

    for (const int thread_count :
         {1, std::min(2, max_openmp_threads()), std::min(4, max_openmp_threads())}) {
        omp_set_num_threads(thread_count);
        Csc3Matrix candidate_matrix;
        HelpInfo candidate_help;
        AssemblyHelper candidate_helper;
        candidate_helper.Symbolic(candidate_matrix, candidate_help, chain_dof_coding_info());
        require_equal(candidate_matrix.n, baseline_matrix.n, "deterministic n");
        require_equal(candidate_matrix.col_ptr, baseline_matrix.col_ptr, "deterministic col_ptr");
        require_equal(candidate_matrix.row_idx, baseline_matrix.row_idx, "deterministic row_idx");
        require_equal(candidate_help.element_ids, baseline_help.element_ids,
                      "deterministic element IDs");
        require_equal(candidate_help.element_dof_offsets, baseline_help.element_dof_offsets,
                      "deterministic DOF offsets");
        require_equal(candidate_help.element_dofs, baseline_help.element_dofs,
                      "deterministic element DOFs");
        require_equal(candidate_help.entry_offsets, baseline_help.entry_offsets,
                      "deterministic entry offsets");
        require_equal(candidate_help.scatter, baseline_help.scatter, "deterministic scatter");
    }
}

// 2048 个单元都写入同三个 CSC3 条目，故意制造高冲突。三个期望值分别是
// $2048 \times 1$、$2048 \times 0.25$ 和 $2048 \times 2$。
void test_atomic_add_under_contention() {
    constexpr int kElementCount = 2048;
    DofCodingInfo input;
    input.node_dofs = {{0, {0}}, {1, {1}}};
    for (int element = 0; element < kElementCount; ++element) {
        input.elems.emplace(element, std::vector<NodeId>{0, 1});
    }

    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    omp_set_num_threads(std::min(8, max_openmp_threads()));
    helper.Symbolic(csc3, help_info, input);
    helper.zero_values(csc3);
    const std::vector<double> stiffness{1.0, 0.25, 0.25, 2.0};
    int observed_threads = 0;
#pragma omp parallel num_threads(8)
    {
#pragma omp single
        {
            observed_threads = omp_get_num_threads();
        }
#pragma omp for schedule(static)
        for (int element = 0; element < kElementCount; ++element) {
            helper.add(csc3, help_info, stiffness_view(element, stiffness));
        }
    }
    require_true(observed_threads > 1, "numeric path did not use multiple threads");
    require_close(csc3.values, {2048.0, 512.0, 4096.0}, "contention result");
}

// 每轮数值组装都必须先清零；连续执行两轮不应保留上一轮的数值。
void test_zero_values_makes_repeated_runs_reproducible() {
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, chain_dof_coding_info());
    assemble_chain(helper, csc3, help_info, 2);
    const std::vector<double> first = csc3.values;
    assemble_chain(helper, csc3, help_info, 2);
    require_equal(csc3.values, first, "repeated assembly");
}

// 这些输入依次覆盖空映射、缺少节点自由度、未知节点、重复节点、重复自由度、
// 非紧凑自由度和负单元编号。失败后，上一份有效输出仍应保持不变。
void test_symbolic_rejects_bad_mappings_without_changing_outputs() {
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, chain_dof_coding_info());
    const Csc3Matrix old_matrix = csc3;
    const HelpInfo old_help = help_info;

    const std::vector<DofCodingInfo> invalid_inputs{
        {},
        {{{1, {0}}}, {}},
        {{{1, {2}}}, {{0, {0}}}},
        {{{1, {0, 0}}}, {{0, {0}}}},
        {{{1, {0}}}, {{0, {0, 0}}}},
        {{{1, {0}}}, {{0, {1}}}},
        {{{-1, {0}}}, {{0, {0}}}},
    };
    for (const auto& invalid : invalid_inputs) {
        require_throws<std::invalid_argument>([&] { helper.Symbolic(csc3, help_info, invalid); },
                                              "invalid DofCodingInfo");
        require_equal(csc3.col_ptr, old_matrix.col_ptr, "matrix after failed symbolic");
        require_equal(help_info.scatter, old_help.scatter, "help after failed symbolic");
    }
}

// add() 必须在写矩阵前完成检查，不能让未知单元、错误矩阵尺寸、非有限值或
// 非对称局部矩阵留下部分累加结果。
void test_add_rejects_bad_input_before_writing() {
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, chain_dof_coding_info());
    helper.zero_values(csc3);
    const std::vector<double> zero = csc3.values;

    require_throws<std::invalid_argument>(
        [&] {
            const std::vector<double> values{1.0};
            helper.add(csc3, help_info, stiffness_view(99, values));
        },
        "unknown element");
    require_throws<std::invalid_argument>(
        [&] {
            const std::vector<double> values{1.0, 0.0, 0.0};
            helper.add(csc3, help_info, stiffness_view(10, values));
        },
        "wrong matrix size");
    require_throws<std::invalid_argument>(
        [&] {
            const std::vector<double> values{1.0, std::numeric_limits<double>::quiet_NaN(), 0.0,
                                             1.0};
            helper.add(csc3, help_info, stiffness_view(10, values));
        },
        "nonfinite matrix");
    require_throws<std::invalid_argument>(
        [&] {
            const std::vector<double> values{1.0, 2.0, 3.0, 1.0};
            helper.add(csc3, help_info, stiffness_view(10, values));
        },
        "nonsymmetric matrix");
    require_equal(csc3.values, zero, "values after rejected add");
}

// 对称性检查同时使用绝对容差和相对容差：小量级误差由前者控制，大量级矩阵
// 中的舍入差异由后者控制。
void test_symmetry_tolerance() {
    DofCodingInfo input{{{1, {0, 1}}}, {{0, {0}}, {1, {1}}}};
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, input);

    helper.zero_values(csc3);
    const std::vector<double> relative_values{2.0, 1.0e12 + 50.0, 1.0e12, 3.0};
    helper.add(csc3, help_info, stiffness_view(1, relative_values));
    require_close(csc3.values, {2.0, 1.0e12 + 50.0, 3.0}, "relative tolerance");

    helper.zero_values(csc3);
    const std::vector<double> absolute_values{2.0, 1.0e-13, 0.0, 3.0};
    helper.add(csc3, help_info, stiffness_view(1, absolute_values));
    require_close(csc3.values, {2.0, 1.0e-13, 3.0}, "absolute tolerance");
}

} // namespace

int main() {
    try {
        // 测试按“正常结果、并行确定性、原子冲突、重复调用、错误输入”的顺序执行。
        // 前一组失败后立即退出，避免后续异常掩盖最先出现的接口问题。
        require_true(openmp_enabled(), "OpenMP is disabled");
        test_required_interface_and_exact_result();
        test_symbolic_is_deterministic();
        test_atomic_add_under_contention();
        test_zero_values_makes_repeated_runs_reproducible();
        test_symbolic_rejects_bad_mappings_without_changing_outputs();
        test_add_rejects_bad_input_before_writing();
        test_symmetry_tolerance();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
