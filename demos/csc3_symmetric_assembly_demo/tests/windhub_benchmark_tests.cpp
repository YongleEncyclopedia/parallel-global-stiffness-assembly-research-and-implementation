#include "csc3_demo_tools/benchmark.h"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo::evidence;

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

template <typename Exception, typename Function>
void require_throws(Function&& function, const std::string& label) {
    try {
        std::forward<Function>(function)();
    } catch (const Exception&) {
        return;
    } catch (const std::exception& exception) {
        throw std::runtime_error(label + " threw the wrong exception: " +
                                 exception.what());
    }
    throw std::runtime_error(label + " did not throw");
}

class TemporaryDirectory {
public:
    TemporaryDirectory() {
        static std::size_t sequence = 0;
        const auto tick = std::chrono::steady_clock::now()
                              .time_since_epoch()
                              .count();
        path_ = std::filesystem::temp_directory_path() /
                ("csc3-windhub-benchmark-" + std::to_string(tick) + "-" +
                 std::to_string(sequence++));
        std::filesystem::create_directories(path_);
    }

    ~TemporaryDirectory() {
        std::error_code error;
        std::filesystem::remove_all(path_, error);
    }

    const std::filesystem::path& path() const noexcept { return path_; }

private:
    std::filesystem::path path_;
};

std::filesystem::path write_tet4(const std::filesystem::path& directory,
                                 const std::string& filename = "tiny.inp") {
    const std::filesystem::path path = directory / filename;
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output << "*Node\n"
              "10,0,0,0\n"
              "30,1,0,0\n"
              "20,0,1,0\n"
              "99,0,0,1\n"
              "*Element, type=C3D4\n"
              "17,10,30,20,99\n";
    if (!output) {
        throw std::runtime_error("could not create temporary C3D4 input");
    }
    return path;
}

SummaryStatistics statistics(double median, double cv) {
    SummaryStatistics result;
    result.sample_count = 7;
    result.mean_ms = median;
    result.median_ms = median;
    result.population_standard_deviation_ms = median * cv;
    result.minimum_ms = median;
    result.maximum_ms = median;
    result.coefficient_of_variation = cv;
    return result;
}

ThreadBenchmarkSummary thread_summary(int thread_count,
                                      double symbolic_speedup,
                                      double numeric_speedup,
                                      double symbolic_cv,
                                      double numeric_cv) {
    ThreadBenchmarkSummary summary;
    summary.thread_count = thread_count;
    summary.symbolic_thread_count_observed = thread_count;
    summary.numeric_thread_count_observed = thread_count;
    summary.symbolic_total_ms = statistics(1.0, symbolic_cv);
    summary.numeric_algorithm_ms = statistics(1.0, numeric_cv);
    summary.symbolic_speedup = symbolic_speedup;
    summary.numeric_speedup = numeric_speedup;
    return summary;
}

void test_performance_gate_boundaries_and_p1_exclusion() {
    const std::vector<ThreadBenchmarkSummary> threshold_summaries{
        thread_summary(1, 100.0, 100.0, 0.0, 0.0),
        thread_summary(2, 1.0, 1.5, 0.0, 0.05),
        thread_summary(4, 1.000001, 1.49, 0.05, 0.0),
    };
    PerformanceGate gate = evaluate_performance_gate(
        BenchmarkCase::WindHub,
        PerformanceEvidenceLevel::Formal,
        threshold_summaries);
    require_equal(gate.status, std::string("PASS"), "formal gate status");
    require_true(gate.performance_requirements_met,
                 "passing formal gate did not meet performance requirements");
    require_true(gate.numeric_requirement_met,
                 "numeric threshold equality did not pass");
    require_true(gate.symbolic_requirement_met,
                 "strict symbolic threshold did not pass above equality");
    require_equal(gate.numeric_thread_count, 2, "numeric gate thread");
    require_equal(gate.symbolic_thread_count, 4, "symbolic gate thread");

    gate = evaluate_performance_gate(
        BenchmarkCase::WindHub,
        PerformanceEvidenceLevel::Formal,
        {thread_summary(1, 100.0, 100.0, 0.0, 0.0),
         thread_summary(2, 1.0, 1.5, 0.0, 0.050001)});
    require_equal(gate.status, std::string("FAIL"), "failing formal gate");
    require_true(!gate.numeric_requirement_met,
                 "numeric CV above the boundary passed");
    require_true(!gate.symbolic_requirement_met,
                 "symbolic equality incorrectly passed strict threshold");
    require_true(!gate.performance_requirements_met,
                 "failed formal gate met the performance requirements");

    gate = evaluate_performance_gate(
        BenchmarkCase::WindHub,
        PerformanceEvidenceLevel::LocalSmoke,
        threshold_summaries);
    require_equal(gate.status,
                  std::string("NON_FORMAL_LOCAL_SMOKE"),
                  "WindHub local-smoke gate status");
    require_true(!gate.performance_requirements_met,
                 "local smoke claimed formal performance acceptance");

    gate = evaluate_performance_gate(
        BenchmarkCase::GeneratedTet4,
        PerformanceEvidenceLevel::CiSmoke,
        threshold_summaries);
    require_equal(gate.status,
                  std::string("NOT_APPLICABLE_GENERATED_CASE"),
                  "generated gate status");

    require_throws<std::invalid_argument>(
        [&threshold_summaries] {
            static_cast<void>(evaluate_performance_gate(
                static_cast<BenchmarkCase>(999),
                PerformanceEvidenceLevel::Formal,
                threshold_summaries));
        },
        "invalid gate benchmark case");
    require_throws<std::invalid_argument>(
        [&threshold_summaries] {
            static_cast<void>(evaluate_performance_gate(
                BenchmarkCase::WindHub,
                static_cast<PerformanceEvidenceLevel>(999),
                threshold_summaries));
        },
        "invalid gate evidence level");
    std::vector<ThreadBenchmarkSummary> nonfinite_summaries{
        thread_summary(2, 2.0, 2.0, 0.0, 0.0)};
    nonfinite_summaries.front().numeric_speedup =
        std::numeric_limits<double>::infinity();
    require_throws<std::invalid_argument>(
        [&nonfinite_summaries] {
            static_cast<void>(evaluate_performance_gate(
                BenchmarkCase::WindHub,
                PerformanceEvidenceLevel::Formal,
                nonfinite_summaries));
        },
        "nonfinite gate statistic");
}

BenchmarkConfiguration windhub_configuration(
    const std::filesystem::path& input) {
    BenchmarkConfiguration configuration;
    configuration.benchmark_case = BenchmarkCase::WindHub;
    configuration.input_path = input;
    configuration.nx = 0;
    configuration.ny = 0;
    configuration.nz = 0;
    configuration.thread_counts = {1};
    configuration.warmup_count = 0;
    configuration.repeat_count = 1;
    configuration.performance_evidence_level =
        PerformanceEvidenceLevel::LocalSmoke;
    return configuration;
}

void test_small_windhub_case_uses_common_sparse_engine() {
    TemporaryDirectory temporary;
    BenchmarkConfiguration configuration =
        windhub_configuration(write_tet4(temporary.path()));
    const BenchmarkResult result = run_benchmark(configuration);
    require_equal(result.case_name, std::string("tiny.inp"), "case name");
    require_equal(result.element_type, std::string("Tet4"), "element type");
    require_equal(result.node_count, std::size_t{4}, "node count");
    require_equal(result.element_count, std::size_t{1}, "element count");
    require_equal(result.dof_count, std::size_t{12}, "DOF count");
    require_true(result.nonzero_count < result.dof_count * result.dof_count,
                 "WindHub benchmark path used dense matrix storage");
    require_equal(result.correctness.status,
                  std::string("PASS"),
                  "matrix correctness status");
    require_equal(result.performance_gate.status,
                  std::string("NON_FORMAL_LOCAL_SMOKE"),
                  "local performance gate");
    require_equal(result.per_thread_measured.front().symbolic_thread_count_observed,
                  1,
                  "WindHub observed symbolic team");
    require_equal(result.per_thread_measured.front().numeric_thread_count_observed,
                  1,
                  "WindHub observed numeric team");
    require_true(result.input_prepare_ms >= 0.0,
                 "input preparation timing is invalid");

    require_throws<std::invalid_argument>(
        [&configuration] {
            static_cast<void>(run_generated_benchmark(configuration));
        },
        "generated wrapper accepted WindHub");
}

int run_cli(const std::vector<std::string>& arguments,
            std::string& standard_output,
            std::string& standard_error) {
    std::ostringstream output;
    std::ostringstream error;
    const int exit_code = run_benchmark_cli(arguments, output, error);
    standard_output = output.str();
    standard_error = error.str();
    return exit_code;
}

void test_cli_case_input_and_formal_output_contract() {
    TemporaryDirectory temporary;
    const std::filesystem::path input = write_tet4(temporary.path());
    const std::filesystem::path pointer = temporary.path() / "pointer.inp";
    {
        std::ofstream output(pointer);
        output << "version https://git-lfs.github.com/spec/v1\n"
                  "oid sha256:abc\nsize 100\n";
    }

    std::string output;
    std::string error;
    require_true(run_cli({"--case", "windhub", "--dry-run"}, output, error) != 0,
                 "WindHub dry-run accepted missing input");
    require_true(run_cli({"--case", "generated-tet4", "--input", input.string(),
                          "--dry-run"},
                         output,
                         error) != 0,
                 "generated case accepted --input");
    require_true(run_cli({"--case", "windhub", "--input", pointer.string(),
                          "--dry-run"},
                         output,
                         error) != 0,
                 "WindHub dry-run accepted an LFS pointer");
    require_true(run_cli({"--case", "windhub", "--input", input.string(),
                          "--evidence-level", "formal", "--warmup", "1",
                          "--repeat", "7", "--threads-list", "1", "--dry-run"},
                         output,
                         error) != 0,
                 "formal WindHub accepted too few warmups");

    const std::filesystem::path csv = temporary.path() / "formal.csv";
    const std::filesystem::path json = temporary.path() / "formal.json";
    const int formal_exit = run_cli(
        {"--case", "windhub", "--input", input.string(),
         "--evidence-level", "formal", "--warmup", "2", "--repeat", "7",
         "--threads-list", "1", "--samples-csv", csv.string(),
         "--summary-json", json.string()},
        output,
        error);
    require_true(formal_exit != 0,
                 "formal run without a p>1 configuration passed its gate");
    require_true(std::filesystem::is_regular_file(csv) &&
                     std::filesystem::is_regular_file(json),
                 "formal gate failure did not preserve CSV/JSON evidence");
    std::ifstream json_input(json, std::ios::binary);
    const std::string json_text{std::istreambuf_iterator<char>(json_input),
                                std::istreambuf_iterator<char>()};
    require_true(json_text.find("\"performance_gate\"") != std::string::npos &&
                     json_text.find("\"status\": \"FAIL\"") !=
                         std::string::npos,
                 "formal JSON omitted explicit failed performance gate");
    require_true(json_text.find(input.string()) == std::string::npos,
                 "summary JSON leaked an absolute input path");
    require_true(json_text.find("\"numeric_algorithm_ms\"") !=
                     std::string::npos,
                 "summary JSON omitted reset-plus-kernel statistics");
    require_true(json_text.find("\"symbolic_thread_count_observed\": 1") !=
                         std::string::npos &&
                     json_text.find("\"numeric_thread_count_observed\": 1") !=
                         std::string::npos,
                 "summary JSON omitted observed OpenMP team sizes");
}

void test_invalid_windhub_programmatic_configurations() {
    TemporaryDirectory temporary;
    const std::filesystem::path input = write_tet4(temporary.path());
    BenchmarkConfiguration configuration = windhub_configuration(input);
    configuration.input_path.clear();
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "missing WindHub input");
    configuration.input_path = input;
    configuration.performance_evidence_level =
        PerformanceEvidenceLevel::Formal;
    configuration.warmup_count = 1;
    configuration.repeat_count = 7;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "formal warmup minimum");
    configuration.warmup_count = 2;
    configuration.repeat_count = 6;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "formal repeat minimum");
}

} // namespace

int main() {
    try {
        test_performance_gate_boundaries_and_p1_exclusion();
        test_small_windhub_case_uses_common_sparse_engine();
        test_cli_case_input_and_formal_output_contract();
        test_invalid_windhub_programmatic_configurations();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
