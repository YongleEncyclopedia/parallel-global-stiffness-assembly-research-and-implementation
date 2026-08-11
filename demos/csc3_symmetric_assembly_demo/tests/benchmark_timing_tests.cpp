#include "csc3_demo_tools/benchmark.h"

// 这里检查 benchmark 的计时口径，不比较机器快慢。重点是各阶段耗时非负、
// 总耗时覆盖子阶段，并且失败调用不会改写上一份有效计时。

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace {

using namespace csc3_demo;
using namespace csc3_demo::evidence;

using TimingsReturn = decltype(BenchmarkAccess::timings(std::declval<const AssemblyHelper&>()));
static_assert(std::is_same_v<TimingsReturn, CandidateTimings>);
static_assert(!std::is_reference_v<TimingsReturn>);

constexpr double kTimingToleranceMs = 1.0e-6;

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
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

bool same_bits(double left, double right) {
    return std::memcmp(&left, &right, sizeof(double)) == 0;
}

bool same_timings(const CandidateTimings& left, const CandidateTimings& right) {
    return same_bits(left.symbolic_pattern_ms, right.symbolic_pattern_ms) &&
           same_bits(left.symbolic_scatter_ms, right.symbolic_scatter_ms) &&
           same_bits(left.symbolic_total_ms, right.symbolic_total_ms) &&
           same_bits(left.numeric_reset_ms, right.numeric_reset_ms) &&
           same_bits(left.numeric_kernel_ms, right.numeric_kernel_ms) &&
           same_bits(left.numeric_total_ms, right.numeric_total_ms);
}

DofCodingInfo chain_input() {
    return DofCodingInfo{
        {{20, {1, 2}}, {10, {0, 1}}},
        {{0, {0}}, {1, {1}}, {2, {2}}},
    };
}

// 符号组装分为 pattern 和 scatter 两段；total 至少应覆盖这两段，并记录实际线程数。
void test_symbolic_timings_and_team_observation() {
    for (const int thread_count : {1, std::min(2, max_openmp_threads())}) {
        AssemblyHelper helper;
        Csc3Matrix csc3;
        HelpInfo help_info;
        BenchmarkAccess::symbolic(helper, csc3, help_info, chain_input(), thread_count);
        const CandidateTimings timings = BenchmarkAccess::timings(helper);
        require_true(std::isfinite(timings.symbolic_pattern_ms) &&
                         timings.symbolic_pattern_ms >= 0.0,
                     "symbolic_pattern_ms is invalid");
        require_true(std::isfinite(timings.symbolic_scatter_ms) &&
                         timings.symbolic_scatter_ms >= 0.0,
                     "symbolic_scatter_ms is invalid");
        require_true(std::isfinite(timings.symbolic_total_ms) &&
                         timings.symbolic_total_ms + kTimingToleranceMs >=
                             timings.symbolic_pattern_ms + timings.symbolic_scatter_ms,
                     "symbolic_total_ms does not cover both phases");
        require_true(BenchmarkAccess::symbolic_used_requested_team_in_all_regions(helper),
                     "a symbolic region used the wrong team size");
        require_true(helper.symbolic_thread_count_used() == thread_count,
                     "reported symbolic team size is wrong");
    }
}

// 非法输入失败后，矩阵、HelpInfo 和计时快照都应保持在上一次成功调用的状态。
void test_failed_symbolic_preserves_snapshot() {
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    BenchmarkAccess::symbolic(helper, csc3, help_info, chain_input(), 1);
    const CandidateTimings before = BenchmarkAccess::timings(helper);
    const Csc3Matrix matrix_before = csc3;
    const HelpInfo help_before = help_info;

    require_throws<std::invalid_argument>(
        [&] { BenchmarkAccess::symbolic(helper, csc3, help_info, DofCodingInfo{}, 1); },
        "invalid symbolic call");
    require_true(same_timings(BenchmarkAccess::timings(helper), before),
                 "failed symbolic changed timing data");
    require_true(csc3.col_ptr == matrix_before.col_ptr && help_info.scatter == help_before.scatter,
                 "failed symbolic changed output data");
}

// 数值阶段单独记录清零和 atomic 累加，numeric_total_ms 应覆盖两者。
void test_benchmark_records_numeric_phases() {
    BenchmarkConfiguration configuration;
    configuration.benchmark_case = BenchmarkCase::GeneratedTet4;
    configuration.nx = 1;
    configuration.ny = 1;
    configuration.nz = 1;
    configuration.thread_counts = {1};
    configuration.warmup_count = 1;
    configuration.repeat_count = 1;
    configuration.performance_evidence_level = PerformanceEvidenceLevel::CiSmoke;
    const BenchmarkResult result = run_benchmark(configuration);
    require_true(result.samples.size() == 2, "benchmark sample count is wrong");
    for (const BenchmarkSample& sample : result.samples) {
        require_true(std::isfinite(sample.candidate_timings.numeric_reset_ms) &&
                         sample.candidate_timings.numeric_reset_ms >= 0.0,
                     "numeric_reset_ms is invalid");
        require_true(std::isfinite(sample.candidate_timings.numeric_kernel_ms) &&
                         sample.candidate_timings.numeric_kernel_ms >= 0.0,
                     "numeric_kernel_ms is invalid");
        require_true(sample.candidate_timings.numeric_total_ms + kTimingToleranceMs >=
                         sample.candidate_timings.numeric_reset_ms +
                             sample.candidate_timings.numeric_kernel_ms,
                     "numeric_total_ms does not cover reset and add loop");
    }
}

// BenchmarkAccess 只供测试工具使用，不能出现在研发调用的公共接口中。
void test_public_header_does_not_expose_benchmark_controls() {
    std::ifstream header(CSC3_DEMO_PUBLIC_HEADER_PATH);
    require_true(header.good(), "could not open public header");
    const std::string contents{std::istreambuf_iterator<char>(header),
                               std::istreambuf_iterator<char>()};
    const std::size_t class_begin = contents.find("class AssemblyHelper");
    const std::size_t public_begin = contents.find("public:", class_begin);
    const std::size_t private_begin = contents.find("private:", public_begin);
    require_true(class_begin != std::string::npos && public_begin != std::string::npos &&
                     private_begin != std::string::npos,
                 "AssemblyHelper declaration is incomplete");
    std::string public_section = contents.substr(public_begin, private_begin - public_begin);
    std::transform(public_section.begin(), public_section.end(), public_section.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    require_true(public_section.find("benchmark") == std::string::npos,
                 "public interface exposes benchmark controls");
    require_true(public_section.find("void symbolic(csc3matrix& csc3, helpinfo& help_info,") !=
                     std::string::npos,
                 "public symbolic signature does not match the R&D interface");
    require_true(public_section.find("const elementstiffness& element_stiffness") !=
                     std::string::npos,
                 "public add signature does not match the R&D interface");
}

} // namespace

int main() {
    try {
        test_symbolic_timings_and_team_observation();
        test_failed_symbolic_preserves_snapshot();
        test_benchmark_records_numeric_phases();
        test_public_header_does_not_expose_benchmark_controls();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
