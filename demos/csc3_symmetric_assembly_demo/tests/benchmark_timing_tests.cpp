#include "csc3_demo_tools/benchmark.h"

#include <omp.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

using csc3_demo::ElementDofMap;
using csc3_demo::ElementMatrixBatch;
using csc3_demo::SymmetricCscAssembler;
using csc3_demo::evidence::BenchmarkAccess;
using csc3_demo::evidence::CandidateTimings;

using TimingsReturn =
    decltype(BenchmarkAccess::timings(std::declval<const SymmetricCscAssembler&>()));
static_assert(std::is_same_v<TimingsReturn, CandidateTimings>);
static_assert(!std::is_reference_v<TimingsReturn>);
static_assert(!std::is_pointer_v<TimingsReturn>);

constexpr double kTimingToleranceMs = 1.0e-6;

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

template <typename Exception, typename Fn> void require_throws(Fn&& fn, const std::string& label) {
    try {
        std::forward<Fn>(fn)();
    } catch (const Exception&) {
        return;
    } catch (const std::exception& exception) {
        throw std::runtime_error(label + " threw the wrong exception: " + exception.what());
    } catch (...) {
        throw std::runtime_error(label + " threw a non-standard exception");
    }
    throw std::runtime_error(label + " did not throw");
}

ElementDofMap chain_topology_unordered() {
    return ElementDofMap{
        {20, 10},
        {0, 2, 4},
        {1, 2, 0, 1},
    };
}

ElementMatrixBatch chain_matrices_canonical() {
    return ElementMatrixBatch{
        {0, 4, 8},
        {
            3.0,
            -2.0,
            -2.0,
            3.0,
            2.0,
            -1.0,
            -1.0,
            2.0,
        },
    };
}

bool same_double_bits(double left, double right) {
    return std::memcmp(&left, &right, sizeof(double)) == 0;
}

bool same_timing_bits(const CandidateTimings& left, const CandidateTimings& right) {
    return same_double_bits(left.symbolic_pattern_ms, right.symbolic_pattern_ms) &&
           same_double_bits(left.symbolic_scatter_ms, right.symbolic_scatter_ms) &&
           same_double_bits(left.symbolic_total_ms, right.symbolic_total_ms) &&
           same_double_bits(left.numeric_reset_ms, right.numeric_reset_ms) &&
           same_double_bits(left.numeric_kernel_ms, right.numeric_kernel_ms) &&
           same_double_bits(left.numeric_total_ms, right.numeric_total_ms);
}

void require_valid_timing(double value, const std::string& label) {
    require_true(std::isfinite(value), label + " is not finite");
    require_true(value >= 0.0, label + " is negative");
}

void require_all_timings_valid(const CandidateTimings& timings) {
    require_valid_timing(timings.symbolic_pattern_ms, "symbolic_pattern_ms");
    require_valid_timing(timings.symbolic_scatter_ms, "symbolic_scatter_ms");
    require_valid_timing(timings.symbolic_total_ms, "symbolic_total_ms");
    require_valid_timing(timings.numeric_reset_ms, "numeric_reset_ms");
    require_valid_timing(timings.numeric_kernel_ms, "numeric_kernel_ms");
    require_valid_timing(timings.numeric_total_ms, "numeric_total_ms");
}

void test_successful_timings_cover_named_subphases() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);
    assembler.assemble_numeric_atomic(chain_matrices_canonical(), 2);

    const CandidateTimings timings = BenchmarkAccess::timings(assembler);
    require_all_timings_valid(timings);
    require_true(timings.symbolic_total_ms + kTimingToleranceMs >=
                     timings.symbolic_pattern_ms + timings.symbolic_scatter_ms,
                 "symbolic total does not cover the named subphases");
    require_true(timings.numeric_total_ms + kTimingToleranceMs >=
                     timings.numeric_reset_ms + timings.numeric_kernel_ms,
                 "numeric total does not cover the named subphases");
}

void test_successful_symbolic_clears_numeric_telemetry() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);
    assembler.assemble_numeric_atomic(chain_matrices_canonical(), 2);
    const CandidateTimings before = BenchmarkAccess::timings(assembler);
    require_all_timings_valid(before);
    require_true(BenchmarkAccess::numeric_used_requested_team(assembler),
                 "numeric setup did not use the requested team");

    assembler.build_symbolic_parallel(chain_topology_unordered(), 1);
    const CandidateTimings after = BenchmarkAccess::timings(assembler);
    require_true(same_double_bits(after.numeric_reset_ms, 0.0),
                 "symbolic rebuild did not clear numeric_reset_ms");
    require_true(same_double_bits(after.numeric_kernel_ms, 0.0),
                 "symbolic rebuild did not clear numeric_kernel_ms");
    require_true(same_double_bits(after.numeric_total_ms, 0.0),
                 "symbolic rebuild did not clear numeric_total_ms");
    require_true(!BenchmarkAccess::numeric_used_requested_team(assembler),
                 "symbolic rebuild did not clear numeric team validity");
}

void test_failed_symbolic_preserves_last_successful_snapshot() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);
    assembler.assemble_numeric_atomic(chain_matrices_canonical(), 2);
    const CandidateTimings before = BenchmarkAccess::timings(assembler);
    const bool symbolic_team_before =
        BenchmarkAccess::symbolic_used_requested_team_in_all_regions(assembler);
    const bool numeric_team_before = BenchmarkAccess::numeric_used_requested_team(assembler);

    require_throws<std::invalid_argument>(
        [&assembler] { assembler.build_symbolic_parallel(ElementDofMap{}, 2); },
        "invalid symbolic call");

    require_true(same_timing_bits(BenchmarkAccess::timings(assembler), before),
                 "invalid symbolic call changed the timing snapshot");
    require_equal(BenchmarkAccess::symbolic_used_requested_team_in_all_regions(assembler),
                  symbolic_team_before, "invalid symbolic call symbolic team validity");
    require_equal(BenchmarkAccess::numeric_used_requested_team(assembler), numeric_team_before,
                  "invalid symbolic call numeric team validity");
}

void test_failed_numeric_preserves_last_successful_snapshot() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);
    assembler.assemble_numeric_atomic(chain_matrices_canonical(), 2);
    const CandidateTimings before = BenchmarkAccess::timings(assembler);
    const bool numeric_team_before = BenchmarkAccess::numeric_used_requested_team(assembler);

    ElementMatrixBatch invalid = chain_matrices_canonical();
    invalid.values_row_major.front() = std::numeric_limits<double>::quiet_NaN();
    require_throws<std::invalid_argument>(
        [&assembler, &invalid] { assembler.assemble_numeric_atomic(invalid, 2); },
        "invalid numeric call");

    require_true(same_timing_bits(BenchmarkAccess::timings(assembler), before),
                 "invalid numeric call changed the timing snapshot");
    require_equal(BenchmarkAccess::numeric_used_requested_team(assembler), numeric_team_before,
                  "invalid numeric call team validity");
}

void test_requested_teams_are_observed_in_every_region() {
    for (const int thread_count : {1, 2}) {
        SymmetricCscAssembler assembler;
        assembler.build_symbolic_parallel(chain_topology_unordered(), thread_count);
        require_true(BenchmarkAccess::symbolic_used_requested_team_in_all_regions(assembler),
                     "a symbolic region did not use the requested team");
        assembler.assemble_numeric_atomic(chain_matrices_canonical(), thread_count);
        require_true(BenchmarkAccess::numeric_used_requested_team(assembler),
                     "the numeric region did not use the requested team");
    }
}

void test_timing_access_is_read_only_and_internal() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 1);
    const CandidateTimings before = BenchmarkAccess::timings(assembler);
    CandidateTimings detached = BenchmarkAccess::timings(assembler);
    detached.symbolic_total_ms = -1.0;
    require_equal(detached.symbolic_total_ms, -1.0, "detached timing mutation");
    require_true(same_timing_bits(BenchmarkAccess::timings(assembler), before),
                 "mutating the returned value changed assembler telemetry");

    std::ifstream header(CSC3_DEMO_PUBLIC_HEADER_PATH);
    require_true(header.good(), "could not open the production public header");
    const std::string contents{std::istreambuf_iterator<char>(header),
                               std::istreambuf_iterator<char>()};
    const std::size_t class_begin = contents.find("class SymmetricCscAssembler");
    const std::size_t public_begin = contents.find("public:", class_begin);
    const std::size_t private_begin = contents.find("private:", public_begin);
    require_true(class_begin != std::string::npos && public_begin != std::string::npos &&
                     private_begin != std::string::npos,
                 "could not locate the assembler public section");
    std::string public_section = contents.substr(public_begin, private_begin - public_begin);
    std::transform(
        public_section.begin(), public_section.end(), public_section.begin(),
        [](unsigned char character) { return static_cast<char>(std::tolower(character)); });
    require_true(public_section.find("timing") == std::string::npos,
                 "production public section exposes timing API");
    require_true(public_section.find("benchmark") == std::string::npos,
                 "production public section exposes benchmark API");
}

void test_existing_correctness_and_overwrite_behavior() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);
    const ElementMatrixBatch matrices = chain_matrices_canonical();
    assembler.assemble_numeric_atomic(matrices, 2);
    const std::vector<double> first = assembler.matrix().values;
    require_equal(first, std::vector<double>{3.0, -2.0, 5.0, -1.0, 2.0}, "assembled CSC3 values");
    assembler.assemble_numeric_atomic(matrices, 2);
    require_equal(assembler.matrix().values, first, "one-shot overwrite values");
}

} // namespace

int main() {
    try {
        omp_set_dynamic(0);
        test_successful_timings_cover_named_subphases();
        test_successful_symbolic_clears_numeric_telemetry();
        test_failed_symbolic_preserves_last_successful_snapshot();
        test_failed_numeric_preserves_last_successful_snapshot();
        test_requested_teams_are_observed_in_every_region();
        test_timing_access_is_read_only_and_internal();
        test_existing_correctness_and_overwrite_behavior();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
