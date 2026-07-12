#pragma once

#include "csc3_demo/assembly_helper.h"

namespace csc3_demo::evidence {

struct CandidateTimings {
    double symbolic_pattern_ms;
    double symbolic_scatter_ms;
    double symbolic_total_ms;
    double numeric_reset_ms;
    double numeric_kernel_ms;
    double numeric_total_ms;
};

struct BenchmarkAccess {
    [[nodiscard]] static CandidateTimings timings(const SymmetricCscAssembler& assembler) noexcept;
    [[nodiscard]] static bool
    symbolic_used_requested_team_in_all_regions(const SymmetricCscAssembler& assembler) noexcept;
    [[nodiscard]] static bool
    numeric_used_requested_team(const SymmetricCscAssembler& assembler) noexcept;
};

inline CandidateTimings BenchmarkAccess::timings(const SymmetricCscAssembler& assembler) noexcept {
    return CandidateTimings{
        assembler.benchmark_timings_.symbolic_pattern_ms,
        assembler.benchmark_timings_.symbolic_scatter_ms,
        assembler.benchmark_timings_.symbolic_total_ms,
        assembler.benchmark_timings_.numeric_reset_ms,
        assembler.benchmark_timings_.numeric_kernel_ms,
        assembler.benchmark_timings_.numeric_total_ms,
    };
}

inline bool BenchmarkAccess::symbolic_used_requested_team_in_all_regions(
    const SymmetricCscAssembler& assembler) noexcept {
    return assembler.symbolic_used_requested_team_in_all_regions_;
}

inline bool
BenchmarkAccess::numeric_used_requested_team(const SymmetricCscAssembler& assembler) noexcept {
    return assembler.numeric_used_requested_team_;
}

} // namespace csc3_demo::evidence
