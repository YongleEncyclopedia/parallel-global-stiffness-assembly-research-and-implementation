#include "csc3_demo_tools/benchmark.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <ios>
#include <limits>
#include <locale>
#include <ostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>

namespace csc3_demo::evidence {
namespace {

constexpr const char* kCsvHeader =
    "schema_version,case_name,element_type,nx,ny,nz,node_count,element_count,"
    "dof_count,nnz,thread_count,sample_index,sample_kind,input_prepare_ms,"
    "serial_symbolic_ms,serial_numeric_ms,symbolic_pattern_ms,"
    "symbolic_scatter_ms,symbolic_total_ms,numeric_reset_ms,numeric_kernel_ms,"
    "numeric_total_ms,amortized_total_ms,symbolic_speedup,numeric_speedup,"
    "relative_frobenius_error,max_absolute_error,matrix_correctness_status,"
    "estimated_persistent_bytes,performance_evidence_level";

constexpr double kRelativeFrobeniusTolerance = 1.0e-8;
constexpr double kTimingConsistencyToleranceMs = 1.0e-6;

std::string benchmark_case_name(BenchmarkCase benchmark_case) {
    switch (benchmark_case) {
    case BenchmarkCase::GeneratedTet4:
        return "generated-tet4";
    case BenchmarkCase::GeneratedHex8:
        return "generated-hex8";
    }
    throw std::invalid_argument("invalid benchmark case");
}

std::string evidence_level_name(PerformanceEvidenceLevel evidence_level) {
    switch (evidence_level) {
    case PerformanceEvidenceLevel::CiSmoke:
        return "ci-smoke";
    case PerformanceEvidenceLevel::LocalSmoke:
        return "local-smoke";
    case PerformanceEvidenceLevel::Formal:
        return "formal";
    }
    throw std::invalid_argument("invalid performance evidence level");
}

std::string sample_kind_name(SampleKind sample_kind) {
    switch (sample_kind) {
    case SampleKind::Warmup:
        return "warmup";
    case SampleKind::Measured:
        return "measured";
    }
    throw std::runtime_error("invalid benchmark sample kind");
}

void require_finite_nonnegative(double value, const char* label) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::runtime_error(std::string(label) +
                                 " must be finite and nonnegative");
    }
}

void require_finite_positive(double value, const char* label) {
    if (!std::isfinite(value) || value <= 0.0) {
        throw std::runtime_error(std::string(label) +
                                 " must be finite and positive");
    }
}

std::size_t checked_multiply(std::size_t left,
                             std::size_t right,
                             const char* label) {
    if (left != 0 && right > std::numeric_limits<std::size_t>::max() / left) {
        throw std::overflow_error(std::string(label) +
                                  " exceeds representable capacity");
    }
    return left * right;
}

std::size_t checked_add(std::size_t left,
                        std::size_t right,
                        const char* label) {
    if (right > std::numeric_limits<std::size_t>::max() - left) {
        throw std::overflow_error(std::string(label) +
                                  " exceeds representable capacity");
    }
    return left + right;
}

bool valid_utf8(const std::string& text) noexcept {
    const auto* bytes = reinterpret_cast<const unsigned char*>(text.data());
    std::size_t index = 0;
    while (index < text.size()) {
        const unsigned char first = bytes[index];
        if (first <= 0x7FU) {
            ++index;
            continue;
        }
        std::size_t continuation_count = 0;
        unsigned char second_minimum = 0x80U;
        unsigned char second_maximum = 0xBFU;
        if (first >= 0xC2U && first <= 0xDFU) {
            continuation_count = 1;
        } else if (first >= 0xE0U && first <= 0xEFU) {
            continuation_count = 2;
            if (first == 0xE0U) {
                second_minimum = 0xA0U;
            } else if (first == 0xEDU) {
                second_maximum = 0x9FU;
            }
        } else if (first >= 0xF0U && first <= 0xF4U) {
            continuation_count = 3;
            if (first == 0xF0U) {
                second_minimum = 0x90U;
            } else if (first == 0xF4U) {
                second_maximum = 0x8FU;
            }
        } else {
            return false;
        }
        if (continuation_count > text.size() - index - 1) {
            return false;
        }
        const unsigned char second = bytes[index + 1];
        if (second < second_minimum || second > second_maximum) {
            return false;
        }
        for (std::size_t continuation = 2;
             continuation <= continuation_count;
             ++continuation) {
            const unsigned char value = bytes[index + continuation];
            if (value < 0x80U || value > 0xBFU) {
                return false;
            }
        }
        index += continuation_count + 1;
    }
    return true;
}

void require_utf8(const std::string& text, const char* label) {
    if (!valid_utf8(text)) {
        throw std::runtime_error(std::string(label) + " is not valid UTF-8");
    }
}

void validate_cli_configuration(const BenchmarkConfiguration& configuration) {
    static_cast<void>(benchmark_case_name(configuration.benchmark_case));
    const std::string evidence =
        evidence_level_name(configuration.performance_evidence_level);
    if (evidence == "formal") {
        throw std::invalid_argument(
            "formal evidence is restricted to the WindHub controlled-host workflow");
    }
    if (configuration.nx <= 0 || configuration.ny <= 0 ||
        configuration.nz <= 0) {
        throw std::invalid_argument("generated grid dimensions must be positive");
    }
    if (configuration.warmup_count < 0) {
        throw std::invalid_argument("warmup must be nonnegative");
    }
    if (configuration.repeat_count < 1) {
        throw std::invalid_argument("repeat must be positive");
    }
    if (configuration.amortization_count < 1) {
        throw std::invalid_argument("amortization count must be positive");
    }
    if (configuration.thread_counts.empty()) {
        throw std::invalid_argument("threads list must not be empty");
    }
    const int available_threads = max_openmp_threads();
    std::set<int> unique_threads;
    for (const int thread_count : configuration.thread_counts) {
        if (thread_count <= 0) {
            throw std::invalid_argument(
                "threads list must contain only positive values");
        }
        if (!unique_threads.insert(thread_count).second) {
            throw std::invalid_argument("threads list must contain unique values");
        }
        if (thread_count > available_threads) {
            throw std::invalid_argument(
                "a requested thread count exceeds the current OpenMP maximum");
        }
    }
}

void validate_statistics(const SummaryStatistics& statistics,
                         std::size_t expected_count,
                         const char* label) {
    if (statistics.sample_count != expected_count) {
        throw std::runtime_error(std::string(label) +
                                 " has an unexpected sample count");
    }
    require_finite_nonnegative(statistics.mean_ms, label);
    require_finite_nonnegative(statistics.median_ms, label);
    require_finite_nonnegative(statistics.population_standard_deviation_ms,
                               label);
    require_finite_nonnegative(statistics.minimum_ms, label);
    require_finite_nonnegative(statistics.maximum_ms, label);
    require_finite_nonnegative(statistics.coefficient_of_variation, label);
    if (statistics.minimum_ms > statistics.median_ms ||
        statistics.median_ms > statistics.maximum_ms) {
        throw std::runtime_error(std::string(label) +
                                 " has inconsistent order statistics");
    }
}

void validate_candidate_timings(const CandidateTimings& timings) {
    require_finite_nonnegative(timings.symbolic_pattern_ms,
                               "symbolic_pattern_ms");
    require_finite_nonnegative(timings.symbolic_scatter_ms,
                               "symbolic_scatter_ms");
    require_finite_nonnegative(timings.symbolic_total_ms,
                               "symbolic_total_ms");
    require_finite_nonnegative(timings.numeric_reset_ms,
                               "numeric_reset_ms");
    require_finite_nonnegative(timings.numeric_kernel_ms,
                               "numeric_kernel_ms");
    require_finite_nonnegative(timings.numeric_total_ms,
                               "numeric_total_ms");
    if (timings.symbolic_total_ms + kTimingConsistencyToleranceMs <
            timings.symbolic_pattern_ms + timings.symbolic_scatter_ms ||
        timings.numeric_total_ms + kTimingConsistencyToleranceMs <
            timings.numeric_reset_ms + timings.numeric_kernel_ms) {
        throw std::runtime_error("phase timings exceed their API total");
    }
}

void validate_result(const BenchmarkResult& result) {
    validate_cli_configuration(result.configuration);
    require_utf8(result.case_name, "case_name");
    require_utf8(result.element_type, "element_type");
    require_utf8(result.correctness.status, "matrix correctness status");
    require_utf8(result.performance_evidence_level,
                 "performance evidence level");
    require_utf8(result.performance_gate_status,
                 "performance gate status");
    if (result.case_name.empty() || result.element_type.empty()) {
        throw std::runtime_error("case name and element type must not be empty");
    }
    if (result.node_count == 0 || result.element_count == 0 ||
        result.dof_count == 0 || result.nonzero_count == 0) {
        throw std::runtime_error("benchmark case sizes must be positive");
    }
    require_finite_nonnegative(result.input_prepare_ms, "input_prepare_ms");
    require_finite_nonnegative(result.correctness.relative_frobenius_error,
                               "relative_frobenius_error");
    require_finite_nonnegative(result.correctness.max_absolute_error,
                               "max_absolute_error");
    require_finite_nonnegative(result.correctness.max_absolute_tolerance,
                               "max_absolute_tolerance");
    if (!result.correctness.structure_matches ||
        result.correctness.status != "PASS" ||
        result.correctness.relative_frobenius_error >
            kRelativeFrobeniusTolerance ||
        result.correctness.max_absolute_error >
            result.correctness.max_absolute_tolerance) {
        throw std::runtime_error("matrix correctness status is not PASS");
    }
    const std::string expected_evidence =
        evidence_level_name(result.configuration.performance_evidence_level);
    if (result.performance_evidence_level != expected_evidence) {
        throw std::runtime_error(
            "performance evidence level disagrees with configuration");
    }
    if (result.performance_gate_status !=
        "NOT_APPLICABLE_GENERATED_CASE") {
        throw std::runtime_error("generated performance gate status is invalid");
    }

    const std::size_t repeat_count =
        static_cast<std::size_t>(result.configuration.repeat_count);
    validate_statistics(result.serial_measured.symbolic_total_ms,
                        repeat_count,
                        "serial symbolic statistics");
    validate_statistics(result.serial_measured.numeric_total_ms,
                        repeat_count,
                        "serial numeric statistics");
    if (result.per_thread_measured.size() !=
        result.configuration.thread_counts.size()) {
        throw std::runtime_error("per-thread summary count is inconsistent");
    }
    for (std::size_t index = 0;
         index < result.per_thread_measured.size();
         ++index) {
        const ThreadBenchmarkSummary& summary =
            result.per_thread_measured[index];
        if (summary.thread_count != result.configuration.thread_counts[index]) {
            throw std::runtime_error("per-thread summary order is inconsistent");
        }
        validate_statistics(summary.symbolic_pattern_ms,
                            repeat_count,
                            "symbolic pattern statistics");
        validate_statistics(summary.symbolic_scatter_ms,
                            repeat_count,
                            "symbolic scatter statistics");
        validate_statistics(summary.symbolic_total_ms,
                            repeat_count,
                            "symbolic total statistics");
        validate_statistics(summary.numeric_reset_ms,
                            repeat_count,
                            "numeric reset statistics");
        validate_statistics(summary.numeric_kernel_ms,
                            repeat_count,
                            "numeric kernel statistics");
        validate_statistics(summary.numeric_total_ms,
                            repeat_count,
                            "numeric total statistics");
        validate_statistics(summary.amortized_total_ms,
                            repeat_count,
                            "amortized total statistics");
        require_finite_positive(summary.symbolic_speedup,
                                "symbolic_speedup");
        require_finite_positive(summary.numeric_speedup,
                                "numeric_speedup");
    }

    const std::size_t samples_per_thread = checked_add(
        static_cast<std::size_t>(result.configuration.warmup_count),
        static_cast<std::size_t>(result.configuration.repeat_count),
        "samples per thread");
    const std::size_t expected_samples = checked_multiply(
        samples_per_thread,
        result.configuration.thread_counts.size(),
        "benchmark sample count");
    if (result.samples.size() != expected_samples) {
        throw std::runtime_error("raw benchmark sample count is inconsistent");
    }
    for (std::size_t thread_ordinal = 0;
         thread_ordinal < result.configuration.thread_counts.size();
         ++thread_ordinal) {
        for (std::size_t sample_ordinal = 0;
             sample_ordinal < samples_per_thread;
             ++sample_ordinal) {
            const BenchmarkSample& sample =
                result.samples[thread_ordinal * samples_per_thread +
                               sample_ordinal];
            if (sample.thread_count !=
                    result.configuration.thread_counts[thread_ordinal] ||
                sample.sample_index != sample_ordinal) {
                throw std::runtime_error("raw sample identity is inconsistent");
            }
            const SampleKind expected_kind =
                sample_ordinal < static_cast<std::size_t>(
                                     result.configuration.warmup_count)
                    ? SampleKind::Warmup
                    : SampleKind::Measured;
            if (sample.sample_kind != expected_kind) {
                throw std::runtime_error("raw sample kind is inconsistent");
            }
            require_finite_nonnegative(sample.input_prepare_ms,
                                       "sample input_prepare_ms");
            require_finite_nonnegative(sample.serial_symbolic_ms,
                                       "sample serial_symbolic_ms");
            require_finite_nonnegative(sample.serial_numeric_ms,
                                       "sample serial_numeric_ms");
            validate_candidate_timings(sample.candidate_timings);
            require_finite_nonnegative(sample.amortized_total_ms,
                                       "sample amortized_total_ms");
            require_finite_positive(sample.symbolic_speedup,
                                    "sample symbolic_speedup");
            require_finite_positive(sample.numeric_speedup,
                                    "sample numeric_speedup");
            const double expected_amortized =
                sample.candidate_timings.symbolic_total_ms /
                    static_cast<double>(
                        result.configuration.amortization_count) +
                sample.candidate_timings.numeric_total_ms;
            const double amortized_tolerance =
                1.0e-12 * std::max(1.0, expected_amortized);
            if (std::abs(sample.amortized_total_ms - expected_amortized) >
                amortized_tolerance) {
                throw std::runtime_error(
                    "sample amortized timing is inconsistent");
            }
            const ThreadBenchmarkSummary& summary =
                result.per_thread_measured[thread_ordinal];
            if (sample.symbolic_speedup != summary.symbolic_speedup ||
                sample.numeric_speedup != summary.numeric_speedup) {
                throw std::runtime_error(
                    "sample speedup disagrees with its thread summary");
            }
        }
    }
}

std::string csv_escape(const std::string& value) {
    if (value.find_first_of(",\"\r\n") == std::string::npos) {
        return value;
    }
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for (const char character : value) {
        if (character == '"') {
            escaped.push_back('"');
        }
        escaped.push_back(character);
    }
    escaped.push_back('"');
    return escaped;
}

std::string json_escape(const std::string& value) {
    static constexpr char kHexDigits[] = "0123456789abcdef";
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for (const unsigned char character : value) {
        switch (character) {
        case '"':
            escaped += "\\\"";
            break;
        case '\\':
            escaped += "\\\\";
            break;
        case '\b':
            escaped += "\\b";
            break;
        case '\f':
            escaped += "\\f";
            break;
        case '\n':
            escaped += "\\n";
            break;
        case '\r':
            escaped += "\\r";
            break;
        case '\t':
            escaped += "\\t";
            break;
        default:
            if (character < 0x20U) {
                escaped += "\\u00";
                escaped.push_back(kHexDigits[(character >> 4U) & 0x0FU]);
                escaped.push_back(kHexDigits[character & 0x0FU]);
            } else {
                escaped.push_back(static_cast<char>(character));
            }
        }
    }
    escaped.push_back('"');
    return escaped;
}

void append_statistics_json(std::ostream& output,
                            const SummaryStatistics& statistics,
                            const std::string& indent) {
    output << "{\n"
           << indent << "  \"sample_count\": " << statistics.sample_count
           << ",\n"
           << indent << "  \"mean_ms\": " << statistics.mean_ms << ",\n"
           << indent << "  \"median_ms\": " << statistics.median_ms << ",\n"
           << indent << "  \"population_standard_deviation_ms\": "
           << statistics.population_standard_deviation_ms << ",\n"
           << indent << "  \"minimum_ms\": " << statistics.minimum_ms
           << ",\n"
           << indent << "  \"maximum_ms\": " << statistics.maximum_ms
           << ",\n"
           << indent << "  \"coefficient_of_variation\": "
           << statistics.coefficient_of_variation << '\n'
           << indent << '}';
}

void ensure_output_path_available(const std::filesystem::path& path) {
    if (path.empty() || path.filename().empty()) {
        throw std::runtime_error("output path must name a file");
    }
    std::error_code error;
    const bool exists = std::filesystem::exists(path, error);
    if (error) {
        throw std::runtime_error("could not inspect output path: " +
                                 error.message());
    }
    if (exists) {
        throw std::runtime_error("refusing to overwrite existing output: " +
                                 path.string());
    }
    const std::filesystem::path parent = path.parent_path();
    if (!parent.empty()) {
        const bool parent_is_directory =
            std::filesystem::is_directory(parent, error);
        if (error) {
            throw std::runtime_error("could not inspect output parent: " +
                                     error.message());
        }
        if (!parent_is_directory) {
            throw std::runtime_error(
                "output parent directory does not exist: " + parent.string());
        }
    }
}

void write_new_file(const std::filesystem::path& path,
                    const std::string& contents) {
    ensure_output_path_available(path);
    std::ofstream output(path, std::ios::binary | std::ios::out);
    output.imbue(std::locale::classic());
    if (!output.is_open()) {
        throw std::runtime_error("could not open output file: " + path.string());
    }
    output.write(contents.data(), static_cast<std::streamsize>(contents.size()));
    output.flush();
    if (!output.good()) {
        output.close();
        std::error_code remove_error;
        std::filesystem::remove(path, remove_error);
        throw std::runtime_error("failed while writing output file: " +
                                 path.string());
    }
    output.close();
    if (output.fail()) {
        std::error_code remove_error;
        std::filesystem::remove(path, remove_error);
        throw std::runtime_error("failed while closing output file: " +
                                 path.string());
    }
}

int parse_integer(const std::string& text, const char* option) {
    if (text.empty()) {
        throw std::invalid_argument(std::string(option) +
                                    " requires an integer value");
    }
    int value = 0;
    const char* begin = text.data();
    const char* end = begin + text.size();
    const auto parsed = std::from_chars(begin, end, value);
    if (parsed.ec != std::errc{} || parsed.ptr != end) {
        throw std::invalid_argument(std::string(option) +
                                    " requires a base-10 integer");
    }
    return value;
}

std::vector<int> parse_threads(const std::string& text) {
    if (text.empty()) {
        throw std::invalid_argument("--threads-list must not be empty");
    }
    std::vector<int> threads;
    std::size_t begin = 0;
    while (begin <= text.size()) {
        const std::size_t comma = text.find(',', begin);
        const std::size_t end = comma == std::string::npos ? text.size() : comma;
        if (end == begin) {
            throw std::invalid_argument(
                "--threads-list contains an empty entry");
        }
        threads.push_back(parse_integer(text.substr(begin, end - begin),
                                        "--threads-list"));
        if (comma == std::string::npos) {
            break;
        }
        begin = comma + 1;
    }
    return threads;
}

std::string join_threads(const std::vector<int>& thread_counts) {
    std::ostringstream output;
    output.imbue(std::locale::classic());
    for (std::size_t index = 0; index < thread_counts.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        output << thread_counts[index];
    }
    return output.str();
}

std::string help_text() {
    return
        "Usage: csc3_demo_benchmark [options]\n"
        "  --case {generated-tet4,generated-hex8}\n"
        "  --nx N --ny N --nz N\n"
        "  --threads-list 1,2,...\n"
        "  --warmup W\n"
        "  --repeat R\n"
        "  --amortization-count M\n"
        "  --evidence-level {ci-smoke,local-smoke,formal}\n"
        "  --samples-csv PATH\n"
        "  --summary-json PATH\n"
        "  --dry-run\n"
        "  --help\n"
        "  --version\n";
}

} // namespace

std::string samples_csv_text(const BenchmarkResult& result) {
    validate_result(result);
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << std::setprecision(std::numeric_limits<double>::max_digits10);
    output << kCsvHeader << '\n';
    for (const BenchmarkSample& sample : result.samples) {
        const CandidateTimings& timings = sample.candidate_timings;
        output << csv_escape(kBenchmarkSchemaVersion) << ','
               << csv_escape(result.case_name) << ','
               << csv_escape(result.element_type) << ','
               << result.configuration.nx << ','
               << result.configuration.ny << ','
               << result.configuration.nz << ','
               << result.node_count << ','
               << result.element_count << ','
               << result.dof_count << ','
               << result.nonzero_count << ','
               << sample.thread_count << ','
               << sample.sample_index << ','
               << csv_escape(sample_kind_name(sample.sample_kind)) << ','
               << sample.input_prepare_ms << ','
               << sample.serial_symbolic_ms << ','
               << sample.serial_numeric_ms << ','
               << timings.symbolic_pattern_ms << ','
               << timings.symbolic_scatter_ms << ','
               << timings.symbolic_total_ms << ','
               << timings.numeric_reset_ms << ','
               << timings.numeric_kernel_ms << ','
               << timings.numeric_total_ms << ','
               << sample.amortized_total_ms << ','
               << sample.symbolic_speedup << ','
               << sample.numeric_speedup << ','
               << result.correctness.relative_frobenius_error << ','
               << result.correctness.max_absolute_error << ','
               << csv_escape(result.correctness.status) << ','
               << result.estimated_persistent_bytes << ','
               << csv_escape(result.performance_evidence_level) << '\n';
    }
    return output.str();
}

std::string summary_json_text(const BenchmarkResult& result) {
    validate_result(result);
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << std::setprecision(std::numeric_limits<double>::max_digits10);
    output << "{\n"
           << "  \"schema_version\": "
           << json_escape(kBenchmarkSchemaVersion) << ",\n"
           << "  \"configuration\": {\n"
           << "    \"case\": "
           << json_escape(benchmark_case_name(result.configuration.benchmark_case))
           << ",\n"
           << "    \"nx\": " << result.configuration.nx << ",\n"
           << "    \"ny\": " << result.configuration.ny << ",\n"
           << "    \"nz\": " << result.configuration.nz << ",\n"
           << "    \"thread_counts\": [";
    for (std::size_t index = 0;
         index < result.configuration.thread_counts.size();
         ++index) {
        if (index != 0) {
            output << ", ";
        }
        output << result.configuration.thread_counts[index];
    }
    output << "],\n"
           << "    \"warmup_count\": "
           << result.configuration.warmup_count << ",\n"
           << "    \"repeat_count\": "
           << result.configuration.repeat_count << ",\n"
           << "    \"amortization_count\": "
           << result.configuration.amortization_count << ",\n"
           << "    \"performance_evidence_level\": "
           << json_escape(result.performance_evidence_level) << '\n'
           << "  },\n"
           << "  \"case_sizes\": {\n"
           << "    \"case_name\": " << json_escape(result.case_name) << ",\n"
           << "    \"element_type\": " << json_escape(result.element_type)
           << ",\n"
           << "    \"node_count\": " << result.node_count << ",\n"
           << "    \"element_count\": " << result.element_count << ",\n"
           << "    \"dof_count\": " << result.dof_count << ",\n"
           << "    \"nnz\": " << result.nonzero_count << '\n'
           << "  },\n"
           << "  \"input_prepare_ms\": " << result.input_prepare_ms << ",\n"
           << "  \"correctness\": {\n"
           << "    \"structure_matches\": "
           << (result.correctness.structure_matches ? "true" : "false") << ",\n"
           << "    \"relative_frobenius_error\": "
           << result.correctness.relative_frobenius_error << ",\n"
           << "    \"max_absolute_error\": "
           << result.correctness.max_absolute_error << ",\n"
           << "    \"max_absolute_tolerance\": "
           << result.correctness.max_absolute_tolerance << ",\n"
           << "    \"status\": " << json_escape(result.correctness.status) << '\n'
           << "  },\n"
           << "  \"serial_measured_statistics\": {\n"
           << "    \"symbolic_total_ms\": ";
    append_statistics_json(output,
                           result.serial_measured.symbolic_total_ms,
                           "    ");
    output << ",\n    \"numeric_total_ms\": ";
    append_statistics_json(output,
                           result.serial_measured.numeric_total_ms,
                           "    ");
    output << "\n  },\n"
           << "  \"per_thread_measured_statistics\": [";
    for (std::size_t index = 0;
         index < result.per_thread_measured.size();
         ++index) {
        const ThreadBenchmarkSummary& summary =
            result.per_thread_measured[index];
        output << (index == 0 ? "\n" : ",\n")
               << "    {\n"
               << "      \"thread_count\": " << summary.thread_count << ",\n"
               << "      \"symbolic_pattern_ms\": ";
        append_statistics_json(output, summary.symbolic_pattern_ms, "      ");
        output << ",\n      \"symbolic_scatter_ms\": ";
        append_statistics_json(output, summary.symbolic_scatter_ms, "      ");
        output << ",\n      \"symbolic_total_ms\": ";
        append_statistics_json(output, summary.symbolic_total_ms, "      ");
        output << ",\n      \"numeric_reset_ms\": ";
        append_statistics_json(output, summary.numeric_reset_ms, "      ");
        output << ",\n      \"numeric_kernel_ms\": ";
        append_statistics_json(output, summary.numeric_kernel_ms, "      ");
        output << ",\n      \"numeric_total_ms\": ";
        append_statistics_json(output, summary.numeric_total_ms, "      ");
        output << ",\n      \"amortized_total_ms\": ";
        append_statistics_json(output, summary.amortized_total_ms, "      ");
        output << ",\n"
               << "      \"symbolic_speedup\": "
               << summary.symbolic_speedup << ",\n"
               << "      \"numeric_speedup\": "
               << summary.numeric_speedup << '\n'
               << "    }";
    }
    output << "\n  ],\n"
           << "  \"estimated_persistent_bytes\": "
           << result.estimated_persistent_bytes << ",\n"
           << "  \"estimated_persistent_memory_kind\": "
           << json_escape("owned_vector_payload_bytes_not_rss") << ",\n"
           << "  \"numeric_speedup_basis\": "
           << json_escape(
                  "serial_reset_plus_kernel_over_atomic_reset_plus_kernel")
           << ",\n"
           << "  \"performance_evidence_level\": "
           << json_escape(result.performance_evidence_level) << ",\n"
           << "  \"performance_gate_status\": "
           << json_escape(result.performance_gate_status) << '\n'
           << "}\n";
    return output.str();
}

void write_samples_csv(const BenchmarkResult& result,
                       const std::filesystem::path& path) {
    write_new_file(path, samples_csv_text(result));
}

void write_summary_json(const BenchmarkResult& result,
                        const std::filesystem::path& path) {
    write_new_file(path, summary_json_text(result));
}

int run_benchmark_cli(const std::vector<std::string>& arguments,
                      std::ostream& standard_output,
                      std::ostream& standard_error) {
    try {
        standard_output.imbue(std::locale::classic());
        standard_error.imbue(std::locale::classic());
        if (arguments.size() == 1 && arguments.front() == "--help") {
            standard_output << help_text();
            return 0;
        }
        if (arguments.size() == 1 && arguments.front() == "--version") {
            standard_output << "csc3_demo_benchmark 0.2.0\n";
            return 0;
        }

        BenchmarkConfiguration configuration;
        std::filesystem::path samples_path;
        std::filesystem::path summary_path;
        bool dry_run = false;
        std::set<std::string> seen_options;
        const auto mark_seen = [&seen_options](const std::string& option) {
            if (!seen_options.insert(option).second) {
                throw std::invalid_argument("duplicate option: " + option);
            }
        };
        const auto option_value = [&arguments](std::size_t& index,
                                               const std::string& option) {
            if (index + 1 >= arguments.size()) {
                throw std::invalid_argument(option + " requires a value");
            }
            ++index;
            return arguments[index];
        };

        for (std::size_t index = 0; index < arguments.size(); ++index) {
            const std::string& option = arguments[index];
            if (option == "--help" || option == "--version") {
                throw std::invalid_argument(option + " must be used alone");
            }
            if (option == "--dry-run") {
                mark_seen(option);
                dry_run = true;
            } else if (option == "--case") {
                mark_seen(option);
                const std::string value = option_value(index, option);
                if (value == "generated-tet4") {
                    configuration.benchmark_case =
                        BenchmarkCase::GeneratedTet4;
                } else if (value == "generated-hex8") {
                    configuration.benchmark_case =
                        BenchmarkCase::GeneratedHex8;
                } else {
                    throw std::invalid_argument("unsupported benchmark case: " +
                                                value);
                }
            } else if (option == "--nx") {
                mark_seen(option);
                configuration.nx =
                    parse_integer(option_value(index, option), "--nx");
            } else if (option == "--ny") {
                mark_seen(option);
                configuration.ny =
                    parse_integer(option_value(index, option), "--ny");
            } else if (option == "--nz") {
                mark_seen(option);
                configuration.nz =
                    parse_integer(option_value(index, option), "--nz");
            } else if (option == "--threads-list") {
                mark_seen(option);
                configuration.thread_counts =
                    parse_threads(option_value(index, option));
            } else if (option == "--warmup") {
                mark_seen(option);
                configuration.warmup_count =
                    parse_integer(option_value(index, option), "--warmup");
            } else if (option == "--repeat") {
                mark_seen(option);
                configuration.repeat_count =
                    parse_integer(option_value(index, option), "--repeat");
            } else if (option == "--amortization-count") {
                mark_seen(option);
                configuration.amortization_count = parse_integer(
                    option_value(index, option), "--amortization-count");
            } else if (option == "--evidence-level") {
                mark_seen(option);
                const std::string value = option_value(index, option);
                if (value == "ci-smoke") {
                    configuration.performance_evidence_level =
                        PerformanceEvidenceLevel::CiSmoke;
                } else if (value == "local-smoke") {
                    configuration.performance_evidence_level =
                        PerformanceEvidenceLevel::LocalSmoke;
                } else if (value == "formal") {
                    configuration.performance_evidence_level =
                        PerformanceEvidenceLevel::Formal;
                } else {
                    throw std::invalid_argument(
                        "unsupported performance evidence level: " + value);
                }
            } else if (option == "--samples-csv") {
                mark_seen(option);
                samples_path = std::filesystem::u8path(
                    option_value(index, option));
            } else if (option == "--summary-json") {
                mark_seen(option);
                summary_path = std::filesystem::u8path(
                    option_value(index, option));
            } else {
                throw std::invalid_argument("unknown option: " + option);
            }
        }

        validate_cli_configuration(configuration);
        if (!samples_path.empty()) {
            ensure_output_path_available(samples_path);
        }
        if (!summary_path.empty()) {
            ensure_output_path_available(summary_path);
        }
        if (!samples_path.empty() && !summary_path.empty() &&
            samples_path.lexically_normal() == summary_path.lexically_normal()) {
            throw std::invalid_argument(
                "samples CSV and summary JSON paths must differ");
        }

        if (dry_run) {
            standard_output
                << "schema_version=" << kBenchmarkSchemaVersion << '\n'
                << "case=" << benchmark_case_name(configuration.benchmark_case)
                << '\n'
                << "grid=" << configuration.nx << 'x' << configuration.ny
                << 'x' << configuration.nz << '\n'
                << "threads=" << join_threads(configuration.thread_counts) << '\n'
                << "warmup=" << configuration.warmup_count << '\n'
                << "repeat=" << configuration.repeat_count << '\n'
                << "amortization_count=" << configuration.amortization_count
                << '\n'
                << "performance_evidence_level="
                << evidence_level_name(
                       configuration.performance_evidence_level)
                << '\n'
                << "samples_csv="
                << (samples_path.empty() ? "<not-set>" : samples_path.string())
                << '\n'
                << "summary_json="
                << (summary_path.empty() ? "<not-set>" : summary_path.string())
                << '\n'
                << "mode=dry-run\n";
            return 0;
        }

        if (samples_path.empty() || summary_path.empty()) {
            throw std::invalid_argument(
                "normal mode requires --samples-csv and --summary-json");
        }
        const BenchmarkResult result = run_generated_benchmark(configuration);
        if (result.correctness.status != "PASS" ||
            !result.correctness.structure_matches) {
            throw std::runtime_error("matrix correctness status is not PASS");
        }
        const std::string csv = samples_csv_text(result);
        const std::string json = summary_json_text(result);
        write_new_file(samples_path, csv);
        try {
            write_new_file(summary_path, json);
        } catch (...) {
            std::error_code remove_error;
            std::filesystem::remove(samples_path, remove_error);
            throw;
        }
        standard_output << "samples_csv=" << samples_path.string() << '\n'
                        << "summary_json=" << summary_path.string() << '\n'
                        << "matrix_correctness_status=PASS\n";
        return 0;
    } catch (const std::exception& exception) {
        standard_error << "error: " << exception.what() << '\n';
        return 1;
    } catch (...) {
        standard_error << "error: unknown failure\n";
        return 1;
    }
}

} // namespace csc3_demo::evidence
