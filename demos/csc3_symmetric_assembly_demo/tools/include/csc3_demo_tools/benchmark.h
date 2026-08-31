// benchmark 的运行配置、原始样本和汇总结果放在这里。
// 执行、结果检查和文件输出共用这些定义，避免统计口径不一致。
#pragma once

#include "csc3_demo/assembly_helper.h"
#include "csc3_demo_tools/evidence.h"

#include <cstddef>
#include <filesystem>
#include <iosfwd>
#include <string>
#include <vector>

namespace csc3_demo::evidence {

inline constexpr const char* kBenchmarkSchemaVersion = "csc3-demo-benchmark-v3";

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

enum class SampleKind {
    // Warmup 样本保留在原始结果中，但不参与统计。
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
    // 只有 WindHub 使用输入文件；生成式算例使用下面三个网格尺寸。
    std::filesystem::path input_path;
    int nx = 1;
    int ny = 1;
    int nz = 1;
    // 按给定顺序逐项运行，不在同一进程内并发不同线程配置。
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
    /// 总体标准差与均值之比。
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
    /// 不预建 CSC3 或 scatter，逐单元生成贡献并排序归并的独立串行参考总时间。
    double serial_direct_ms = 0.0;
    // 以下两项只用于与候选阶段分别对照，不构成串行参考总时间。
    double serial_symbolic_ms = 0.0;
    double serial_numeric_ms = 0.0;
    // 候选路径的分阶段时间来自同一次样本。
    CandidateTimings candidate_timings{};
    double amortized_total_ms = 0.0;
    double symbolic_speedup = 0.0;
    double numeric_speedup = 0.0;
    bool symbolic_plan_matches_serial = false;
    bool numeric_setup_plan_matches_serial = false;
};

struct SerialBenchmarkSummary {
    /// 整体加速比和矩阵正确性采用的直接串行组装基线。
    SummaryStatistics direct_total_ms;
    // 两阶段串行路径仅作为分阶段诊断基线。
    SummaryStatistics symbolic_total_ms;
    SummaryStatistics numeric_total_ms;
};

struct ThreadBenchmarkSummary {
    // 一项对应一个请求线程数，observed 字段记录 OpenMP 实际提供的线程数。
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
    // 非正式算例仍计算结果，但 applicable 为 false，不据此下性能结论。
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
    // warmup 和 measured 原始样本都保留，汇总值可以由它们重新计算。
    std::vector<BenchmarkSample> samples;
    ScatterCorrectness scatter_correctness;
    std::size_t estimated_persistent_bytes = 0;
    std::string performance_evidence_level;
    std::string performance_gate_status;
    PerformanceGate performance_gate;
    std::vector<ValidationResult> validation_cases;
};

/// 汇总一组正式测量值；数组为空或含非法时间时抛出异常。
[[nodiscard]] SummaryStatistics summarize_measured_values(const std::vector<double>& values);

[[nodiscard]] PerformanceGate
evaluate_performance_gate(BenchmarkCase benchmark_case, PerformanceEvidenceLevel evidence_level,
                          const SerialBenchmarkSummary& serial_measured,
                          const std::vector<ThreadBenchmarkSummary>& per_thread_measured,
                          const ScatterCorrectness& scatter_correctness);

/// 小型正确性验证优先使用 2 线程；未请求 2 线程时取第一个并行配置。
[[nodiscard]] int select_validation_thread_count(const std::vector<int>& requested_thread_counts);

/// 运行串行基线和全部线程配置，返回原始样本、统计量和正确性结果。
[[nodiscard]] BenchmarkResult run_benchmark(const BenchmarkConfiguration& configuration);

/// 生成式 Tet4/Hex8 算例的便捷入口，不接受 WindHub。
[[nodiscard]] BenchmarkResult run_generated_benchmark(const BenchmarkConfiguration& configuration);

/// 序列化前会重新核对原始样本、汇总值和状态字段。
[[nodiscard]] std::string samples_csv_text(const BenchmarkResult& result);
[[nodiscard]] std::string summary_json_text(const BenchmarkResult& result);

/// 结果文件必须事先不存在，防止覆盖上一轮实验。
void write_samples_csv(const BenchmarkResult& result, const std::filesystem::path& path);
void write_summary_json(const BenchmarkResult& result, const std::filesystem::path& path);

/// 成功返回 0；参数、运行或验收失败返回 1，并把原因写入 standard_error。
int run_benchmark_cli(const std::vector<std::string>& arguments, std::ostream& standard_output,
                      std::ostream& standard_error);

/// benchmark 需要指定线程数并读取内部计时，因此通过这个窄接口访问 AssemblyHelper。
/// 求解器集成不需要使用 BenchmarkAccess。
struct BenchmarkAccess {
    /// benchmark 可指定线程数；研发侧仍使用不带线程参数的 symbolic()。
    static void symbolic(AssemblyHelper& helper, Csc3Matrix& csc3, HelpInfo& help_info,
                         const DofCodingInfo& dof_coding_info, int thread_count);
    [[nodiscard]] static CandidateTimings timings(const AssemblyHelper& helper) noexcept;
    [[nodiscard]] static bool
    symbolic_used_requested_team_in_all_regions(const AssemblyHelper& helper) noexcept;
};

inline void BenchmarkAccess::symbolic(AssemblyHelper& helper, Csc3Matrix& csc3, HelpInfo& help_info,
                                      const DofCodingInfo& dof_coding_info, int thread_count) {
    helper.symbolic_with_thread_count(csc3, help_info, dof_coding_info, thread_count);
}

inline CandidateTimings BenchmarkAccess::timings(const AssemblyHelper& helper) noexcept {
    return CandidateTimings{
        helper.benchmark_timings_.symbolic_pattern_ms,
        helper.benchmark_timings_.symbolic_scatter_ms,
        helper.benchmark_timings_.symbolic_total_ms,
        0.0,
        0.0,
        0.0,
    };
}

inline bool BenchmarkAccess::symbolic_used_requested_team_in_all_regions(
    const AssemblyHelper& helper) noexcept {
    return helper.symbolic_used_requested_team_in_all_regions_;
}

} // namespace csc3_demo::evidence
