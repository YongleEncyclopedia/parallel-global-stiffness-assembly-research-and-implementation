// Benchmark 对外使用的数据结构和调用入口都放在这里。
// 实验执行、结果检查和 CSV/JSON 输出共用这些定义，避免各自维护一套口径。
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

/// 生成式算例用于回归检查，WindHub 用于工程网格实验。
enum class BenchmarkCase {
    GeneratedTet4,
    GeneratedHex8,
    WindHub,
};

enum class PerformanceEvidenceLevel {
    /// CI 只验证执行链路，不允许形成性能结论。
    CiSmoke,
    /// 开发机本地小规模检查，不允许替代受控主机验收。
    LocalSmoke,
    /// 满足受控主机、规模、重复数和 provenance 契约的正式证据。
    Formal,
};

/// 预热样本只留痕，不参与统计；Measured 样本用于计算汇总值。
enum class SampleKind {
    Warmup,
    Measured,
};

struct CandidateTimings {
    /// CSC3 pattern 构造（含 DOF 邻接、列排序去重和结构填充）。
    double symbolic_pattern_ms;
    /// 从单元局部上三角到整体 CSC3 条目的 scatter 计划构造。
    double symbolic_scatter_ms;
    /// 符号调用端到端耗时，包含输入校验与上述两个阶段。
    double symbolic_total_ms;
    /// 每次完整数值组装前将整体矩阵清零的耗时。
    double numeric_reset_ms;
    /// OpenMP atomic 累加 kernel 的耗时。
    double numeric_kernel_ms;
    /// 数值调用端到端耗时，包含校验、清零和 kernel。
    double numeric_total_ms;
};

/// 一次 benchmark 的不可变运行配置；所有计数字段必须为正数。
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
    /// 只统计 measured 样本，warmup 不进入任何汇总量。
    std::size_t sample_count = 0;
    double mean_ms = 0.0;
    double median_ms = 0.0;
    double population_standard_deviation_ms = 0.0;
    double minimum_ms = 0.0;
    double maximum_ms = 0.0;
    double coefficient_of_variation = 0.0;
};

struct BenchmarkCorrectness {
    /// 候选与独立串行参考的 CSC3 列偏移和行索引是否逐项一致。
    bool structure_matches = false;
    /// $e_F=\lVert K_p-K_s\rVert_F/\max(\lVert K_s\rVert_F,10^{-30})$。
    double relative_frobenius_error = 0.0;
    /// $e_{max}=\max_{i,j}|(K_p-K_s)_{ij}|$。
    double max_absolute_error = 0.0;
    double reference_max_absolute_value = 0.0;
    double max_absolute_tolerance = 0.0;
    std::string status;
};

struct BenchmarkSample {
    /// 每个 warmup/measured 重复均保留一行，防止汇总统计掩盖异常样本。
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
    /// 数值算法口径 $t_{numeric}=t_{reset}+t_{atomic\ kernel}$；用于数值加速比。
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
    /// 这里只判断计时阈值；主机身份、输入哈希和 provenance 由正式验收层另行判断。
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
    /// 结构化结果是 CSV、JSON、manifest 和报告生成器的唯一数据源。
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

/// 汇总一组 measured 时间；数组为空或含有非法时间值时抛出异常。
[[nodiscard]] SummaryStatistics summarize_measured_values(const std::vector<double>& values);

/// 根据计时汇总和 scatter 检查判断性能门槛。正式证据的主机与输入来源由验收层核对。
[[nodiscard]] PerformanceGate
evaluate_performance_gate(BenchmarkCase benchmark_case, PerformanceEvidenceLevel evidence_level,
                          const SerialBenchmarkSummary& serial_measured,
                          const std::vector<ThreadBenchmarkSummary>& per_thread_measured,
                          const ScatterCorrectness& scatter_correctness);

/// 验证优先使用 2 线程；未请求 2 线程时取第一个并行线程，否则退回 1 线程。
[[nodiscard]] int select_validation_thread_count(const std::vector<int>& requested_thread_counts);

/// 运行完整 benchmark，返回原始样本、统计结果和正确性检查；配置非法时抛出异常。
[[nodiscard]] BenchmarkResult run_benchmark(const BenchmarkConfiguration& configuration);

/// 生成式算例的便捷入口，不接受 WindHub 输入。
[[nodiscard]] BenchmarkResult run_generated_benchmark(const BenchmarkConfiguration& configuration);

/// 序列化前会重新核对原始样本、统计结果和状态字段。
[[nodiscard]] std::string samples_csv_text(const BenchmarkResult& result);
[[nodiscard]] std::string summary_json_text(const BenchmarkResult& result);

/// 只创建新文件，不覆盖已有实验结果。
void write_samples_csv(const BenchmarkResult& result, const std::filesystem::path& path);
void write_summary_json(const BenchmarkResult& result, const std::filesystem::path& path);

/// 命令成功返回 0；参数、运行或验收失败返回 1，并把原因写入 standard_error。
int run_benchmark_cli(const std::vector<std::string>& arguments, std::ostream& standard_output,
                      std::ostream& standard_error);

struct BenchmarkAccess {
    /// 测试/benchmark 侧的窄友元接口，只读取计时和实际 team size，不暴露给公共 API。
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
