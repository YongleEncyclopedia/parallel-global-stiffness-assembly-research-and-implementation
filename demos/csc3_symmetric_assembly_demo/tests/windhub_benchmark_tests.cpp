#include "csc3_demo_tools/benchmark.h"

// 本文件检查 WindHub 实验规则和失败处理，不用小型夹具冒充工程网格性能结果。
// 真正的线程扫描仍需在目标 Windows 主机上对实体 WindHub 输入运行。

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
        throw std::runtime_error(label + " threw the wrong exception: " + exception.what());
    }
    throw std::runtime_error(label + " did not throw");
}

class TemporaryDirectory {
  public:
    TemporaryDirectory() {
        static std::size_t sequence = 0;
        const auto tick = std::chrono::steady_clock::now().time_since_epoch().count();
        path_ =
            std::filesystem::temp_directory_path() /
            ("csc3-windhub-benchmark-" + std::to_string(tick) + "-" + std::to_string(sequence++));
        std::filesystem::create_directories(path_);
    }

    ~TemporaryDirectory() {
        std::error_code error;
        std::filesystem::remove_all(path_, error);
    }

    const std::filesystem::path& path() const noexcept {
        return path_;
    }

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
    // 性能门槛测试只需要可控的统计量，因此直接构造摘要；真实计时由 benchmark
    // 端到端测试和目标 Windows 主机的独立进程实验负责。
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

ThreadBenchmarkSummary thread_summary(int thread_count, double symbolic_speedup,
                                      double numeric_speedup, double symbolic_cv,
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

SerialBenchmarkSummary serial_summary(double symbolic_cv, double numeric_cv) {
    SerialBenchmarkSummary summary;
    summary.symbolic_total_ms = statistics(1.0, symbolic_cv);
    summary.numeric_total_ms = statistics(1.0, numeric_cv);
    return summary;
}

ScatterCorrectness scatter_correctness(bool passed) {
    ScatterCorrectness scatter;
    scatter.symbolic_plan_check_count = 21;
    scatter.symbolic_plan_match_count = passed ? 21 : 20;
    scatter.numeric_setup_plan_check_count = 3;
    scatter.numeric_setup_plan_match_count = passed ? 3 : 2;
    scatter.status = passed ? "PASS" : "FAIL";
    return scatter;
}

// 正式门槛使用数值加速比 $\ge 1.5$、符号加速比 $>1$、变异系数 $\le 0.05$。
// $p=1$ 只作基线，不得拿它满足并行性能门槛。
void test_performance_gate_boundaries_and_p1_exclusion() {
    const SerialBenchmarkSummary serial_at_threshold = serial_summary(0.05, 0.05);
    const ScatterCorrectness passing_scatter = scatter_correctness(true);
    const std::vector<ThreadBenchmarkSummary> threshold_summaries{
        thread_summary(1, 100.0, 100.0, 0.0, 0.0),
        thread_summary(2, 1.0, 1.5, 0.0, 0.05),
        thread_summary(4, 1.000001, 1.49, 0.05, 0.0),
    };
    PerformanceGate gate =
        evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal,
                                  serial_at_threshold, threshold_summaries, passing_scatter);
    require_equal(gate.status, std::string("PASS"), "formal gate status");
    require_true(gate.performance_requirements_met,
                 "passing formal gate did not meet performance requirements");
    require_true(gate.serial_symbolic_cv_requirement_met,
                 "serial symbolic CV threshold equality did not pass");
    require_true(gate.serial_numeric_cv_requirement_met,
                 "serial numeric CV threshold equality did not pass");
    require_true(gate.scatter_requirement_met, "passing scatter evidence did not pass the gate");
    require_true(gate.formal_requirements_met,
                 "passing performance and scatter evidence did not pass formal requirements");
    require_true(gate.numeric_requirement_met, "numeric threshold equality did not pass");
    require_true(gate.symbolic_requirement_met,
                 "strict symbolic threshold did not pass above equality");
    require_equal(gate.numeric_thread_count, 2, "numeric gate thread");
    require_equal(gate.symbolic_thread_count, 4, "symbolic gate thread");

    gate = evaluate_performance_gate(
        BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal, serial_at_threshold,
        {thread_summary(1, 100.0, 100.0, 0.0, 0.0), thread_summary(2, 1.0, 1.5, 0.0, 0.050001)},
        passing_scatter);
    require_equal(gate.status, std::string("FAIL"), "failing formal gate");
    require_true(!gate.numeric_requirement_met, "numeric CV above the boundary passed");
    require_true(!gate.symbolic_requirement_met,
                 "symbolic equality incorrectly passed strict threshold");
    require_true(!gate.performance_requirements_met,
                 "failed formal gate met the performance requirements");

    gate = evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal,
                                     serial_summary(0.050001, 0.05), threshold_summaries,
                                     passing_scatter);
    require_equal(gate.status, std::string("FAIL"), "serial symbolic CV failure status");
    require_true(!gate.serial_symbolic_cv_requirement_met,
                 "serial symbolic CV above the boundary passed");
    require_true(gate.symbolic_requirement_met,
                 "serial symbolic CV failure erased passing candidate diagnostics");
    require_equal(gate.symbolic_thread_count, 4,
                  "serial symbolic CV failure erased the candidate thread");
    require_true(!gate.performance_requirements_met,
                 "serial CV failure met performance requirements");
    require_true(!gate.formal_requirements_met,
                 "serial symbolic CV failure met formal requirements");

    gate = evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal,
                                     serial_summary(0.05, 0.050001), threshold_summaries,
                                     passing_scatter);
    require_equal(gate.status, std::string("FAIL"), "serial numeric CV failure status");
    require_true(!gate.serial_numeric_cv_requirement_met,
                 "serial numeric CV above the boundary passed");
    require_true(gate.numeric_requirement_met,
                 "serial numeric CV failure erased passing candidate diagnostics");
    require_equal(gate.numeric_thread_count, 2,
                  "serial numeric CV failure erased the candidate thread");
    require_true(!gate.performance_requirements_met,
                 "serial numeric CV failure met performance requirements");
    require_true(!gate.formal_requirements_met,
                 "serial numeric CV failure met formal requirements");

    gate = evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal,
                                     serial_at_threshold, threshold_summaries,
                                     scatter_correctness(false));
    require_equal(gate.status, std::string("FAIL"), "scatter failure formal status");
    require_true(gate.performance_requirements_met,
                 "scatter failure incorrectly changed performance requirements");
    require_true(!gate.scatter_requirement_met, "failed scatter evidence passed the gate");
    require_true(!gate.formal_requirements_met,
                 "failed scatter evidence passed formal requirements");

    gate = evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::LocalSmoke,
                                     serial_at_threshold, threshold_summaries, passing_scatter);
    require_equal(gate.status, std::string("NON_FORMAL_LOCAL_SMOKE"),
                  "WindHub local-smoke gate status");
    require_true(!gate.performance_requirements_met,
                 "local smoke claimed formal performance acceptance");
    require_true(!gate.formal_requirements_met, "local smoke claimed combined formal acceptance");

    gate =
        evaluate_performance_gate(BenchmarkCase::GeneratedTet4, PerformanceEvidenceLevel::CiSmoke,
                                  serial_at_threshold, threshold_summaries, passing_scatter);
    require_equal(gate.status, std::string("NOT_APPLICABLE_GENERATED_CASE"),
                  "generated gate status");

    require_throws<std::invalid_argument>(
        [&serial_at_threshold, &threshold_summaries, &passing_scatter] {
            static_cast<void>(evaluate_performance_gate(
                static_cast<BenchmarkCase>(999), PerformanceEvidenceLevel::Formal,
                serial_at_threshold, threshold_summaries, passing_scatter));
        },
        "invalid gate benchmark case");
    require_throws<std::invalid_argument>(
        [&serial_at_threshold, &threshold_summaries, &passing_scatter] {
            static_cast<void>(evaluate_performance_gate(
                BenchmarkCase::WindHub, static_cast<PerformanceEvidenceLevel>(999),
                serial_at_threshold, threshold_summaries, passing_scatter));
        },
        "invalid gate evidence level");
    std::vector<ThreadBenchmarkSummary> nonfinite_summaries{thread_summary(2, 2.0, 2.0, 0.0, 0.0)};
    nonfinite_summaries.front().numeric_speedup = std::numeric_limits<double>::infinity();
    require_throws<std::invalid_argument>(
        [&serial_at_threshold, &nonfinite_summaries, &passing_scatter] {
            static_cast<void>(evaluate_performance_gate(
                BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal, serial_at_threshold,
                nonfinite_summaries, passing_scatter));
        },
        "nonfinite gate statistic");

    SerialBenchmarkSummary nonfinite_serial = serial_at_threshold;
    nonfinite_serial.numeric_total_ms.coefficient_of_variation =
        std::numeric_limits<double>::infinity();
    require_throws<std::invalid_argument>(
        [&nonfinite_serial, &threshold_summaries, &passing_scatter] {
            static_cast<void>(
                evaluate_performance_gate(BenchmarkCase::WindHub, PerformanceEvidenceLevel::Formal,
                                          nonfinite_serial, threshold_summaries, passing_scatter));
        },
        "nonfinite serial gate statistic");
}

BenchmarkConfiguration windhub_configuration(const std::filesystem::path& input) {
    BenchmarkConfiguration configuration;
    configuration.benchmark_case = BenchmarkCase::WindHub;
    configuration.input_path = input;
    configuration.nx = 0;
    configuration.ny = 0;
    configuration.nz = 0;
    configuration.thread_counts = {1};
    configuration.warmup_count = 0;
    configuration.repeat_count = 1;
    configuration.performance_evidence_level = PerformanceEvidenceLevel::LocalSmoke;
    return configuration;
}

// 用一个临时 C3D4 网格确认 WindHub 入口走公共稀疏引擎，而不是另写一条稠密捷径。
void test_small_windhub_case_uses_common_sparse_engine() {
    TemporaryDirectory temporary;
    BenchmarkConfiguration configuration = windhub_configuration(write_tet4(temporary.path()));
    const BenchmarkResult result = run_benchmark(configuration);
    require_equal(result.case_name, std::string("tiny.inp"), "case name");
    require_equal(result.element_type, std::string("Tet4"), "element type");
    require_equal(result.node_count, std::size_t{4}, "node count");
    require_equal(result.element_count, std::size_t{1}, "element count");
    require_equal(result.dof_count, std::size_t{12}, "DOF count");
    require_true(result.nonzero_count < result.dof_count * result.dof_count,
                 "WindHub benchmark path used dense matrix storage");
    require_equal(result.correctness.status, std::string("PASS"), "matrix correctness status");
    require_equal(result.performance_gate.status, std::string("NON_FORMAL_LOCAL_SMOKE"),
                  "local performance gate");
    require_equal(result.per_thread_measured.front().symbolic_thread_count_observed, 1,
                  "WindHub observed symbolic team");
    require_equal(result.per_thread_measured.front().numeric_thread_count_observed, 1,
                  "WindHub observed numeric team");
    require_true(result.input_prepare_ms >= 0.0, "input preparation timing is invalid");

    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_generated_benchmark(configuration)); },
        "generated wrapper accepted WindHub");
}

int run_cli(const std::vector<std::string>& arguments, std::string& standard_output,
            std::string& standard_error) {
    std::ostringstream output;
    std::ostringstream error;
    const int exit_code = run_benchmark_cli(arguments, output, error);
    standard_output = output.str();
    standard_error = error.str();
    return exit_code;
}

// CLI 需要实体输入和固定的正式实验参数；即使性能门槛失败，也要保留 CSV/JSON。
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
    require_true(run_cli({"--case", "generated-tet4", "--input", input.string(), "--dry-run"},
                         output, error) != 0,
                 "generated case accepted --input");
    require_true(run_cli({"--case", "windhub", "--input", pointer.string(), "--dry-run"}, output,
                         error) != 0,
                 "WindHub dry-run accepted an LFS pointer");
    require_true(
        run_cli({"--case", "windhub", "--input", input.string(), "--evidence-level", "formal",
                 "--warmup", "1", "--repeat", "7", "--threads-list", "1", "--dry-run"},
                output, error) != 0,
        "formal WindHub accepted too few warmups");
    require_true(
        run_cli({"--case", "windhub", "--input", input.string(), "--evidence-level", "formal",
                 "--warmup", "3", "--repeat", "7", "--threads-list", "1", "--dry-run"},
                output, error) != 0,
        "formal WindHub accepted a noncanonical warmup count");
    require_true(
        run_cli({"--case", "windhub", "--input", input.string(), "--evidence-level", "formal",
                 "--warmup", "2", "--repeat", "8", "--threads-list", "1", "--dry-run"},
                output, error) != 0,
        "formal WindHub accepted a noncanonical repeat count");
    require_true(run_cli({"--case", "windhub", "--input", input.string(), "--evidence-level",
                          "formal", "--warmup", "2", "--repeat", "7", "--amortization-count", "2",
                          "--threads-list", "1", "--dry-run"},
                         output, error) != 0,
                 "formal WindHub accepted a noncanonical amortization count");

    const std::filesystem::path csv = temporary.path() / "formal.csv";
    const std::filesystem::path json = temporary.path() / "formal.json";
    const int formal_exit =
        run_cli({"--case", "windhub", "--input", input.string(), "--evidence-level", "formal",
                 "--warmup", "2", "--repeat", "7", "--threads-list", "1", "--samples-csv",
                 csv.string(), "--summary-json", json.string()},
                output, error);
    require_true(formal_exit != 0, "formal run without a p>1 configuration passed its gate");
    require_true(std::filesystem::is_regular_file(csv) && std::filesystem::is_regular_file(json),
                 "formal gate failure did not preserve CSV/JSON evidence");
    std::ifstream json_input(json, std::ios::binary);
    const std::string json_text{std::istreambuf_iterator<char>(json_input),
                                std::istreambuf_iterator<char>()};
    require_true(json_text.find("\"performance_gate\"") != std::string::npos &&
                     json_text.find("\"status\": \"FAIL\"") != std::string::npos,
                 "formal JSON omitted explicit failed performance gate");
    require_true(json_text.find(input.string()) == std::string::npos,
                 "summary JSON leaked an absolute input path");
    require_true(json_text.find("\"numeric_algorithm_ms\"") != std::string::npos,
                 "summary JSON omitted reset-plus-kernel statistics");
    require_true(json_text.find("\"symbolic_thread_count_observed\": 1") != std::string::npos &&
                     json_text.find("\"numeric_thread_count_observed\": 1") != std::string::npos,
                 "summary JSON omitted observed OpenMP team sizes");
}

// 直接调用 C++ API 时也要执行同样的输入、预热、重复次数和摊销次数检查。
void test_invalid_windhub_programmatic_configurations() {
    TemporaryDirectory temporary;
    const std::filesystem::path input = write_tet4(temporary.path());
    BenchmarkConfiguration configuration = windhub_configuration(input);
    configuration.input_path.clear();
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "missing WindHub input");
    configuration.input_path = input;
    configuration.performance_evidence_level = PerformanceEvidenceLevel::Formal;
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
    configuration.warmup_count = 3;
    configuration.repeat_count = 7;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "formal warmup exact value");
    configuration.warmup_count = 2;
    configuration.repeat_count = 8;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "formal repeat exact value");
    configuration.repeat_count = 7;
    configuration.amortization_count = 2;
    require_throws<std::invalid_argument>(
        [&configuration] { static_cast<void>(run_benchmark(configuration)); },
        "formal amortization exact value");
}

} // namespace

int main() {
    try {
        // 顺序对应“门槛公式、公共引擎、命令行契约、C++ API 契约”四个层次。
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
