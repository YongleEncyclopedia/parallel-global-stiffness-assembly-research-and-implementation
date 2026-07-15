#pragma once

#include "csc3_demo/assembly_helper.h"
#include "csc3_demo_tools/evidence.h"

#include <cstddef>
#include <filesystem>
#include <iosfwd>
#include <string>
#include <vector>

namespace csc3_demo::evidence {

inline constexpr const char* kBenchmarkSchemaVersion = "csc3-demo-benchmark-v2";

enum class BenchmarkCase {
    GeneratedTet4,
    GeneratedHex8,
    WindHub,
};

enum class PerformanceEvidenceLevel {
    CiSmoke,
    LocalSmoke,
    Formal,
};

enum class SampleKind {
    Warmup,
    Measured,
};

struct CandidateTimings {
    double symbolic_pattern_ms;
    double symbolic_scatter_ms;
    double symbolic_total_ms;
    double numeric_reset_ms;
    double numeric_kernel_ms;
    double numeric_total_ms;
};

struct BenchmarkConfiguration {
    BenchmarkCase benchmark_case = BenchmarkCase::GeneratedTet4;
    std::filesystem::path input_path;
    int nx = 1;
    int ny = 1;
    int nz = 1;
    std::vector<int> thread_counts{1, 2};
    int warmup_count = 2;
    int repeat_count = 7;
    int amortization_count = 1;
    PerformanceEvidenceLevel performance_evidence_level = PerformanceEvidenceLevel::LocalSmoke;
};

struct SummaryStatistics {
    std::size_t sample_count = 0;
    double mean_ms = 0.0;
    double median_ms = 0.0;
    double population_standard_deviation_ms = 0.0;
    double minimum_ms = 0.0;
    double maximum_ms = 0.0;
    double coefficient_of_variation = 0.0;
};

struct BenchmarkCorrectness {
    bool structure_matches = false;
    double relative_frobenius_error = 0.0;
    double max_absolute_error = 0.0;
    double reference_max_absolute_value = 0.0;
    double max_absolute_tolerance = 0.0;
    std::string status;
};

struct BenchmarkSample {
    int thread_count = 0;
    std::size_t sample_index = 0;
    SampleKind sample_kind = SampleKind::Warmup;
    double input_prepare_ms = 0.0;
    double serial_symbolic_ms = 0.0;
    double serial_numeric_ms = 0.0;
    CandidateTimings candidate_timings{};
    double amortized_total_ms = 0.0;
    double symbolic_speedup = 0.0;
    double numeric_speedup = 0.0;
    bool symbolic_plan_matches_serial = false;
    bool numeric_setup_plan_matches_serial = false;
};

struct SerialBenchmarkSummary {
    SummaryStatistics symbolic_total_ms;
    SummaryStatistics numeric_total_ms;
};

struct ThreadBenchmarkSummary {
    int thread_count = 0;
    int symbolic_thread_count_observed = 0;
    int numeric_thread_count_observed = 0;
    std::size_t symbolic_plan_check_count = 0;
    std::size_t symbolic_plan_match_count = 0;
    bool numeric_setup_plan_matches_serial = false;
    std::string scatter_status;
    SummaryStatistics symbolic_pattern_ms;
    SummaryStatistics symbolic_scatter_ms;
    SummaryStatistics symbolic_total_ms;
    SummaryStatistics numeric_reset_ms;
    SummaryStatistics numeric_kernel_ms;
    /// Reset plus atomic kernel only; this is the numeric speedup denominator.
    SummaryStatistics numeric_algorithm_ms;
    SummaryStatistics numeric_total_ms;
    SummaryStatistics amortized_total_ms;
    double symbolic_speedup = 0.0;
    double numeric_speedup = 0.0;
};

struct ScatterCorrectness {
    std::size_t symbolic_plan_check_count = 0;
    std::size_t symbolic_plan_match_count = 0;
    std::size_t numeric_setup_plan_check_count = 0;
    std::size_t numeric_setup_plan_match_count = 0;
    std::string status;
};

struct PerformanceGate {
    std::string status;
    bool applicable = false;
    /// Algorithmic timing thresholds only; host/provenance acceptance is external.
    bool performance_requirements_met = false;
    bool numeric_requirement_met = false;
    bool symbolic_requirement_met = false;
    bool serial_symbolic_cv_requirement_met = false;
    bool serial_numeric_cv_requirement_met = false;
    bool scatter_requirement_met = false;
    bool formal_requirements_met = false;
    int numeric_thread_count = 0;
    int symbolic_thread_count = 0;
    double numeric_speedup_threshold = 1.5;
    double symbolic_speedup_threshold = 1.0;
    double maximum_coefficient_of_variation = 0.05;
};

struct BenchmarkResult {
    BenchmarkConfiguration configuration;
    std::string case_name;
    std::string element_type;
    std::size_t node_count = 0;
    std::size_t element_count = 0;
    std::size_t dof_count = 0;
    std::size_t nonzero_count = 0;
    double input_prepare_ms = 0.0;
    BenchmarkCorrectness correctness;
    SerialBenchmarkSummary serial_measured;
    std::vector<ThreadBenchmarkSummary> per_thread_measured;
    std::vector<BenchmarkSample> samples;
    ScatterCorrectness scatter_correctness;
    std::size_t estimated_persistent_bytes = 0;
    std::string performance_evidence_level;
    std::string performance_gate_status;
    PerformanceGate performance_gate;
    std::vector<ValidationResult> validation_cases;
};

[[nodiscard]] SummaryStatistics summarize_measured_values(const std::vector<double>& values);

[[nodiscard]] PerformanceGate
evaluate_performance_gate(BenchmarkCase benchmark_case, PerformanceEvidenceLevel evidence_level,
                          const SerialBenchmarkSummary& serial_measured,
                          const std::vector<ThreadBenchmarkSummary>& per_thread_measured,
                          const ScatterCorrectness& scatter_correctness);

[[nodiscard]] int select_validation_thread_count(const std::vector<int>& requested_thread_counts);

[[nodiscard]] BenchmarkResult run_benchmark(const BenchmarkConfiguration& configuration);

[[nodiscard]] BenchmarkResult run_generated_benchmark(const BenchmarkConfiguration& configuration);

[[nodiscard]] std::string samples_csv_text(const BenchmarkResult& result);
[[nodiscard]] std::string summary_json_text(const BenchmarkResult& result);

void write_samples_csv(const BenchmarkResult& result, const std::filesystem::path& path);
void write_summary_json(const BenchmarkResult& result, const std::filesystem::path& path);

int run_benchmark_cli(const std::vector<std::string>& arguments, std::ostream& standard_output,
                      std::ostream& standard_error);

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
