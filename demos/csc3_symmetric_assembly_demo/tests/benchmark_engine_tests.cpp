#include "csc3_demo_tools/benchmark.h"
#include "csc3_demo_tools/evidence.h"

// 这里测试 benchmark 引擎本身：样本统计、小型 Tet4/Hex8 算例、线程选择和
// 配置校验。测试中的短计时只用于核对字段关系，不代表实际性能。

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstddef>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo;
using namespace csc3_demo::evidence;

constexpr double kClockToleranceMs = 1.0e-6;

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

void require_close(double actual, double expected, double tolerance, const std::string& label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(label + " mismatch");
    }
}

template <typename Exception, typename Fn>
void require_throws(Fn&& function, const std::string& label) {
    try {
        std::forward<Fn>(function)();
    } catch (const Exception&) {
        return;
    } catch (const std::exception& exception) {
        throw std::runtime_error(label + " threw the wrong exception: " + exception.what());
    }
    throw std::runtime_error(label + " did not throw");
}

void require_finite_nonnegative(double value, const std::string& label) {
    require_true(std::isfinite(value) && value >= 0.0, label + " must be finite and nonnegative");
}

std::vector<int> available_test_threads() {
    if (max_openmp_threads() >= 2) {
        return {1, 2};
    }
    return {1};
}

// 测试算例故意缩到一个网格胞元、一次预热和两次记录。这里要验证的是引擎生成的
// 字段和统计关系，而不是在 CI runner 上取得有意义的性能数字。
BenchmarkConfiguration small_configuration(BenchmarkCase benchmark_case) {
    BenchmarkConfiguration configuration;
    configuration.benchmark_case = benchmark_case;
    configuration.thread_counts = available_test_threads();
    configuration.warmup_count = 1;
    configuration.repeat_count = 2;
    configuration.amortization_count = 3;
    configuration.performance_evidence_level = PerformanceEvidenceLevel::CiSmoke;
    return configuration;
}

// 该值只统计矩阵和 HelpInfo 中各 vector 的有效数据字节，不是进程峰值内存。
std::size_t expected_payload_bytes(const AssemblyCase& assembly_case, int thread_count) {
    AssemblyHelper helper;
    Csc3Matrix matrix;
    HelpInfo plan;
    BenchmarkAccess::symbolic(helper, matrix, plan, make_dof_coding_info(assembly_case),
                              thread_count);
    return matrix.col_ptr.size() * sizeof(Index) + matrix.row_idx.size() * sizeof(Index) +
           matrix.values.size() * sizeof(double) + plan.element_ids.size() * sizeof(ElementId) +
           plan.element_dof_offsets.size() * sizeof(Index) +
           plan.element_dofs.size() * sizeof(Index) + plan.entry_offsets.size() * sizeof(Index) +
           plan.scatter.size() * sizeof(Index);
}

void require_statistics_finite(const SummaryStatistics& statistics, std::size_t expected_count,
                               const std::string& label) {
    require_equal(statistics.sample_count, expected_count, label + " count");
    require_finite_nonnegative(statistics.mean_ms, label + " mean");
    require_finite_nonnegative(statistics.median_ms, label + " median");
    require_finite_nonnegative(statistics.population_standard_deviation_ms,
                               label + " population stddev");
    require_finite_nonnegative(statistics.minimum_ms, label + " minimum");
    require_finite_nonnegative(statistics.maximum_ms, label + " maximum");
    require_finite_nonnegative(statistics.coefficient_of_variation,
                               label + " coefficient of variation");
    require_true(statistics.minimum_ms <= statistics.median_ms &&
                     statistics.median_ms <= statistics.maximum_ms,
                 label + " ordering is invalid");
}

void require_validation_cases(const BenchmarkResult& result, int expected_thread_count) {
    require_equal(result.validation_cases.size(), std::size_t{2}, "validation case count");
    const ValidationResult& tet4 = result.validation_cases[0];
    require_equal(tet4.case_name, std::string("cube_tet4_1x1x1"), "Tet4 validation case name");
    require_equal(tet4.element_type, ElementType::Tet4, "Tet4 validation element type");
    require_equal(tet4.node_count, std::size_t{8}, "Tet4 validation nodes");
    require_equal(tet4.element_count, std::size_t{6}, "Tet4 validation elements");
    require_equal(tet4.dof_count, std::size_t{24}, "Tet4 validation DOFs");
    require_equal(tet4.thread_count, expected_thread_count, "Tet4 validation thread count");
    require_true(tet4.matrix.passed && tet4.displacement.passed && tet4.passed,
                 "Tet4 validation evidence did not pass");

    const ValidationResult& hex8 = result.validation_cases[1];
    require_equal(hex8.case_name, std::string("cube_hex8_1x1x1"), "Hex8 validation case name");
    require_equal(hex8.element_type, ElementType::Hex8, "Hex8 validation element type");
    require_equal(hex8.node_count, std::size_t{8}, "Hex8 validation nodes");
    require_equal(hex8.element_count, std::size_t{1}, "Hex8 validation elements");
    require_equal(hex8.dof_count, std::size_t{24}, "Hex8 validation DOFs");
    require_equal(hex8.thread_count, expected_thread_count, "Hex8 validation thread count");
    require_true(hex8.matrix.passed && hex8.displacement.passed && hex8.passed,
                 "Hex8 validation evidence did not pass");
}

void require_successful_result(const BenchmarkResult& result, BenchmarkCase expected_case,
                               const std::string& expected_element_type) {
    // 一个成功结果应同时包含输入规模、串行基线、各线程样本和两种单元的正确性证据。
    // 这些检查集中写在一起，Tet4 与 Hex8 测试便可共用同一套判据。
    require_equal(result.configuration.benchmark_case, expected_case, "benchmark case");
    require_equal(result.element_type, expected_element_type, "element type");
    require_true(result.node_count > 0, "node count must be positive");
    require_true(result.element_count > 0, "element count must be positive");
    require_true(result.dof_count > 0, "DOF count must be positive");
    require_true(result.nonzero_count > 0, "nonzero count must be positive");
    require_finite_nonnegative(result.input_prepare_ms, "input preparation time");
    require_true(result.correctness.structure_matches, "serial and candidate structures differ");
    require_true(result.correctness.status == "PASS", "matrix correctness did not pass");
    require_finite_nonnegative(result.correctness.relative_frobenius_error,
                               "relative Frobenius error");
    require_finite_nonnegative(result.correctness.max_absolute_error, "maximum absolute error");
    require_true(result.correctness.relative_frobenius_error <= 1.0e-8,
                 "relative Frobenius threshold exceeded");
    require_true(result.correctness.max_absolute_error <= result.correctness.max_absolute_tolerance,
                 "maximum absolute threshold exceeded");
    require_equal(result.performance_gate_status, std::string("NOT_APPLICABLE_GENERATED_CASE"),
                  "generated performance gate status");
    require_equal(result.performance_evidence_level, std::string("ci-smoke"),
                  "performance evidence level");

    const std::size_t repeat_count = static_cast<std::size_t>(result.configuration.repeat_count);
    require_statistics_finite(result.serial_measured.direct_total_ms, repeat_count,
                              "direct serial");
    require_statistics_finite(result.serial_measured.symbolic_total_ms, repeat_count,
                              "serial symbolic");
    require_statistics_finite(result.serial_measured.numeric_total_ms, repeat_count,
                              "serial numeric");
    require_equal(result.per_thread_measured.size(), result.configuration.thread_counts.size(),
                  "per-thread summary count");

    const std::size_t samples_per_thread = static_cast<std::size_t>(
        result.configuration.warmup_count + result.configuration.repeat_count);
    require_equal(result.samples.size(),
                  samples_per_thread * result.configuration.thread_counts.size(),
                  "raw sample row count");
    require_equal(result.scatter_correctness.symbolic_plan_check_count, result.samples.size(),
                  "root symbolic plan check count");
    require_equal(result.scatter_correctness.symbolic_plan_match_count, result.samples.size(),
                  "root symbolic plan match count");
    require_equal(result.scatter_correctness.numeric_setup_plan_check_count,
                  result.configuration.thread_counts.size(), "root numeric setup plan check count");
    require_equal(result.scatter_correctness.numeric_setup_plan_match_count,
                  result.configuration.thread_counts.size(), "root numeric setup plan match count");
    require_equal(result.scatter_correctness.status, std::string("PASS"),
                  "root scatter correctness status");

    std::vector<double> first_thread_serial_direct;
    std::vector<double> first_thread_serial_symbolic;
    std::vector<double> first_thread_serial_numeric;
    for (std::size_t thread_ordinal = 0; thread_ordinal < result.configuration.thread_counts.size();
         ++thread_ordinal) {
        const int thread_count = result.configuration.thread_counts[thread_ordinal];
        const ThreadBenchmarkSummary& summary = result.per_thread_measured[thread_ordinal];
        require_equal(summary.thread_count, thread_count, "summary thread count");
        require_equal(summary.symbolic_thread_count_observed, thread_count,
                      "observed symbolic thread count");
        require_equal(summary.numeric_thread_count_observed, thread_count,
                      "observed numeric thread count");
        require_equal(summary.symbolic_plan_check_count, samples_per_thread,
                      "thread symbolic plan check count");
        require_equal(summary.symbolic_plan_match_count, samples_per_thread,
                      "thread symbolic plan match count");
        require_true(summary.numeric_setup_plan_matches_serial,
                     "thread numeric setup plan differs from serial");
        require_equal(summary.scatter_status, std::string("PASS"),
                      "thread scatter correctness status");
        require_statistics_finite(summary.symbolic_pattern_ms, repeat_count, "symbolic pattern");
        require_statistics_finite(summary.symbolic_scatter_ms, repeat_count, "symbolic scatter");
        require_statistics_finite(summary.symbolic_total_ms, repeat_count, "symbolic total");
        require_statistics_finite(summary.numeric_reset_ms, repeat_count, "numeric reset");
        require_statistics_finite(summary.numeric_kernel_ms, repeat_count, "numeric kernel");
        require_statistics_finite(summary.numeric_algorithm_ms, repeat_count,
                                  "numeric reset plus kernel");
        require_statistics_finite(summary.numeric_total_ms, repeat_count, "numeric total");
        require_statistics_finite(summary.amortized_total_ms, repeat_count, "amortized total");
        require_true(std::isfinite(summary.symbolic_speedup) && summary.symbolic_speedup >= 0.0,
                     "symbolic speedup must be finite and nonnegative");
        require_true(std::isfinite(summary.numeric_speedup) && summary.numeric_speedup >= 0.0,
                     "numeric speedup must be finite and nonnegative");

        std::size_t warmup_rows = 0;
        std::size_t measured_rows = 0;
        std::vector<double> measured_atomic_reset_plus_kernel;
        for (std::size_t row_offset = 0; row_offset < samples_per_thread; ++row_offset) {
            const BenchmarkSample& sample =
                result.samples[thread_ordinal * samples_per_thread + row_offset];
            require_equal(sample.thread_count, thread_count, "sample thread count");
            require_true(sample.symbolic_plan_matches_serial,
                         "raw symbolic plan differs from serial");
            require_true(sample.numeric_setup_plan_matches_serial,
                         "raw numeric setup plan differs from serial");
            if (sample.sample_kind == SampleKind::Warmup) {
                ++warmup_rows;
            } else {
                ++measured_rows;
            }
            require_finite_nonnegative(sample.serial_direct_ms, "sample direct serial");
            require_finite_nonnegative(sample.serial_symbolic_ms, "sample serial symbolic");
            require_finite_nonnegative(sample.serial_numeric_ms, "sample serial numeric");
            if (thread_ordinal == 0) {
                first_thread_serial_direct.push_back(sample.serial_direct_ms);
                first_thread_serial_symbolic.push_back(sample.serial_symbolic_ms);
                first_thread_serial_numeric.push_back(sample.serial_numeric_ms);
            } else {
                require_close(sample.serial_direct_ms, first_thread_serial_direct[row_offset],
                              0.0, "shared direct serial sample");
                require_close(sample.serial_symbolic_ms, first_thread_serial_symbolic[row_offset],
                              0.0, "shared serial symbolic sample");
                require_close(sample.serial_numeric_ms, first_thread_serial_numeric[row_offset],
                              0.0, "shared serial numeric sample");
            }
            require_finite_nonnegative(sample.candidate_timings.symbolic_pattern_ms,
                                       "sample symbolic pattern");
            require_finite_nonnegative(sample.candidate_timings.symbolic_scatter_ms,
                                       "sample symbolic scatter");
            require_finite_nonnegative(sample.candidate_timings.symbolic_total_ms,
                                       "sample symbolic total");
            require_finite_nonnegative(sample.candidate_timings.numeric_reset_ms,
                                       "sample numeric reset");
            require_finite_nonnegative(sample.candidate_timings.numeric_kernel_ms,
                                       "sample numeric kernel");
            require_finite_nonnegative(sample.candidate_timings.numeric_total_ms,
                                       "sample numeric total");
            require_true(sample.candidate_timings.symbolic_total_ms + kClockToleranceMs >=
                             sample.candidate_timings.symbolic_pattern_ms +
                                 sample.candidate_timings.symbolic_scatter_ms,
                         "symbolic total is smaller than named phases");
            require_true(sample.candidate_timings.numeric_total_ms + kClockToleranceMs >=
                             sample.candidate_timings.numeric_reset_ms +
                                 sample.candidate_timings.numeric_kernel_ms,
                         "numeric total is smaller than named phases");
            require_close(sample.amortized_total_ms,
                          sample.candidate_timings.symbolic_total_ms /
                                  static_cast<double>(result.configuration.amortization_count) +
                              sample.candidate_timings.numeric_total_ms,
                          1.0e-12, "sample amortized total");
            if (sample.sample_kind == SampleKind::Measured) {
                measured_atomic_reset_plus_kernel.push_back(
                    sample.candidate_timings.numeric_reset_ms +
                    sample.candidate_timings.numeric_kernel_ms);
            }
        }
        require_equal(warmup_rows, static_cast<std::size_t>(result.configuration.warmup_count),
                      "warmup row count");
        require_equal(measured_rows, repeat_count, "measured row count");
        const SummaryStatistics atomic_algorithm =
            summarize_measured_values(measured_atomic_reset_plus_kernel);
        require_close(summary.numeric_algorithm_ms.median_ms, atomic_algorithm.median_ms, 0.0,
                      "numeric algorithm median");
        require_close(summary.symbolic_speedup,
                      result.serial_measured.symbolic_total_ms.median_ms /
                          summary.symbolic_total_ms.median_ms,
                      1.0e-12, "median symbolic speedup");
        require_close(summary.numeric_speedup,
                      result.serial_measured.numeric_total_ms.median_ms /
                          atomic_algorithm.median_ms,
                      1.0e-12, "median numeric reset-plus-kernel speedup");
    }
}

// 先用手算样本核对均值、中位数、标准差和加速比，再检查汇总结果自洽。
void test_known_statistics_and_validation() {
    const SummaryStatistics statistics = summarize_measured_values({1.0, 2.0, 3.0, 4.0});
    require_equal(statistics.sample_count, std::size_t{4}, "statistics count");
    require_close(statistics.mean_ms, 2.5, 0.0, "statistics mean");
    require_close(statistics.median_ms, 2.5, 0.0, "statistics median");
    require_close(statistics.population_standard_deviation_ms, std::sqrt(1.25), 1.0e-15,
                  "statistics population stddev");
    require_close(statistics.minimum_ms, 1.0, 0.0, "statistics minimum");
    require_close(statistics.maximum_ms, 4.0, 0.0, "statistics maximum");
    require_close(statistics.coefficient_of_variation, std::sqrt(1.25) / 2.5, 1.0e-15,
                  "statistics coefficient of variation");

    const SummaryStatistics zeros = summarize_measured_values({0.0, 0.0});
    require_close(zeros.coefficient_of_variation, 0.0, 0.0, "zero coefficient of variation");
    require_throws<std::invalid_argument>([] { static_cast<void>(summarize_measured_values({})); },
                                          "empty statistics input");
    require_throws<std::invalid_argument>(
        [] {
            static_cast<void>(
                summarize_measured_values({1.0, std::numeric_limits<double>::infinity()}));
        },
        "nonfinite statistics input");
}

// 两种生成式单元都走一遍完整 benchmark，并同时检查矩阵与位移验证结果。
void test_generated_tet4_and_hex8_benchmarks() {
    const BenchmarkConfiguration tet4_configuration =
        small_configuration(BenchmarkCase::GeneratedTet4);
    const BenchmarkResult tet4 = run_generated_benchmark(tet4_configuration);
    require_successful_result(tet4, BenchmarkCase::GeneratedTet4, "Tet4");
    require_validation_cases(tet4, tet4_configuration.thread_counts.size() > 1
                                       ? tet4_configuration.thread_counts[1]
                                       : 1);
    require_equal(tet4.estimated_persistent_bytes,
                  expected_payload_bytes(make_cube_case(ElementType::Tet4, 1, 1, 1),
                                         tet4_configuration.thread_counts.back()),
                  "Tet4 persistent payload bytes");

    BenchmarkConfiguration hex8_configuration = small_configuration(BenchmarkCase::GeneratedHex8);
    hex8_configuration.thread_counts = {1};
    const BenchmarkResult hex8 = run_generated_benchmark(hex8_configuration);
    require_successful_result(hex8, BenchmarkCase::GeneratedHex8, "Hex8");
    require_validation_cases(hex8, 1);
    require_equal(hex8.estimated_persistent_bytes,
                  expected_payload_bytes(make_cube_case(ElementType::Hex8, 1, 1, 1), 1),
                  "Hex8 persistent payload bytes");

    BenchmarkConfiguration sparse_configuration = small_configuration(BenchmarkCase::GeneratedTet4);
    sparse_configuration.nx = 2;
    sparse_configuration.ny = 2;
    sparse_configuration.nz = 2;
    sparse_configuration.thread_counts = {1};
    sparse_configuration.warmup_count = 0;
    sparse_configuration.repeat_count = 1;
    const BenchmarkResult sparse = run_generated_benchmark(sparse_configuration);
    require_true(sparse.dof_count == 81 && sparse.element_count == 48,
                 "medium sparse Tet4 case sizes are incorrect");
    require_true(sparse.nonzero_count < sparse.dof_count * sparse.dof_count,
                 "medium benchmark evidence unexpectedly became dense");
}

// 正确性验证优先用 2 线程；未请求 2 线程时，使用线程列表中的第一个并行配置。
void test_validation_thread_selection_prefers_two_then_first_parallel() {
    require_equal(select_validation_thread_count({1, 2}), 2,
                  "validation thread selection prefers two");
    require_equal(select_validation_thread_count({1, 3}), 3,
                  "validation thread selection uses the first parallel team");
    require_equal(select_validation_thread_count({1}), 1,
                  "validation thread selection falls back to one");

    BenchmarkConfiguration configuration = small_configuration(BenchmarkCase::GeneratedTet4);
    configuration.warmup_count = 0;
    configuration.repeat_count = 1;
    require_validation_cases(run_generated_benchmark(configuration),
                             select_validation_thread_count(configuration.thread_counts));
}

// 这些配置会让样本数或线程含义变得不明确，应在开始计时前直接拒绝。
void test_invalid_engine_configurations_are_rejected() {
    BenchmarkConfiguration configuration = small_configuration(BenchmarkCase::GeneratedTet4);

    configuration.warmup_count = -1;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "negative warmup count");
    configuration.warmup_count = 0;
    configuration.repeat_count = 0;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "zero repeat count");
    configuration.repeat_count = 1;
    configuration.amortization_count = 0;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "zero amortization count");
    configuration.amortization_count = 1;
    configuration.thread_counts.clear();
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "empty thread list");
    configuration.thread_counts = {1, 1};
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "duplicate thread list");
    configuration.thread_counts = {0};
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "nonpositive thread count");
    configuration.thread_counts = {1};
    configuration.nx = 0;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "nonpositive grid dimension");
    configuration.nx = 1;
    configuration.performance_evidence_level = PerformanceEvidenceLevel::Formal;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "formal generated evidence");

    configuration.performance_evidence_level = PerformanceEvidenceLevel::CiSmoke;
    if (max_openmp_threads() < std::numeric_limits<int>::max()) {
        configuration.thread_counts = {max_openmp_threads() + 1};
        require_throws<std::invalid_argument>(
            [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
            "unavailable OpenMP team");
    }
}

// 串行参考和 benchmark 控制只属于测试工具，不能混入交付给研发的公共类。
void test_production_header_has_no_serial_or_benchmark_api() {
    std::ifstream header(CSC3_DEMO_PUBLIC_HEADER_PATH);
    require_true(header.good(), "could not open production public header");
    const std::string contents{std::istreambuf_iterator<char>(header),
                               std::istreambuf_iterator<char>()};
    const std::size_t class_begin = contents.find("class AssemblyHelper");
    const std::size_t public_begin = contents.find("public:", class_begin);
    const std::size_t private_begin = contents.find("private:", public_begin);
    require_true(class_begin != std::string::npos && public_begin != std::string::npos &&
                     private_begin != std::string::npos,
                 "could not locate assembler public section");
    std::string public_section = contents.substr(public_begin, private_begin - public_begin);
    std::transform(
        public_section.begin(), public_section.end(), public_section.begin(),
        [](unsigned char character) { return static_cast<char>(std::tolower(character)); });
    require_true(public_section.find("serial") == std::string::npos,
                 "production public section exposes serial baseline API");
    require_true(public_section.find("benchmark") == std::string::npos,
                 "production public section exposes benchmark API");
}

} // namespace

int main() {
    try {
        // 先核对纯统计函数，再运行小型端到端算例，最后检查拒绝路径和公共接口边界。
        test_known_statistics_and_validation();
        test_generated_tet4_and_hex8_benchmarks();
        test_validation_thread_selection_prefers_two_then_first_parallel();
        test_invalid_engine_configurations_are_rejected();
        test_production_header_has_no_serial_or_benchmark_api();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
