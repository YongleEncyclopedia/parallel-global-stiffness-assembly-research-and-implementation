#include "csc3_demo_tools/benchmark.h"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo::evidence;

constexpr const char* kExpectedCsvHeader =
    "schema_version,case_name,element_type,nx,ny,nz,node_count,element_count,"
    "dof_count,nnz,thread_count,sample_index,sample_kind,input_prepare_ms,"
    "serial_symbolic_ms,serial_numeric_ms,symbolic_pattern_ms,"
    "symbolic_scatter_ms,symbolic_total_ms,numeric_reset_ms,numeric_kernel_ms,"
    "numeric_total_ms,amortized_total_ms,symbolic_speedup,numeric_speedup,"
    "relative_frobenius_error,max_absolute_error,matrix_correctness_status,"
    "estimated_persistent_bytes,performance_evidence_level";

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

SummaryStatistics statistics(double base) {
    return SummaryStatistics{1, base, base, 0.0, base, base, 0.0};
}

CandidateTimings timings(double pattern) {
    return CandidateTimings{
        pattern,
        0.25,
        pattern + 0.75,
        0.1,
        0.4,
        0.75,
    };
}

ValidationResult synthetic_validation(ElementType element_type,
                                      int thread_count) {
    ValidationResult validation;
    validation.case_name = element_type == ElementType::Tet4
                               ? "cube_tet4_1x1x1"
                               : "cube_hex8_1x1x1";
    validation.element_type = element_type;
    validation.node_count = 8;
    validation.element_count = element_type == ElementType::Tet4 ? 6 : 1;
    validation.dof_count = 24;
    validation.thread_count = thread_count;
    validation.matrix = MatrixComparison{
        true,
        1.0e-12,
        2.0e-12,
        1.0e-8,
        true,
    };
    validation.displacement = DisplacementComparison{
        3.0e-12,
        4.0e-12,
        5.0e-12,
        6.0e-6,
        7.0e-6,
        true,
    };
    validation.passed = true;
    return validation;
}

BenchmarkResult synthetic_result() {
    BenchmarkResult result;
    result.configuration.benchmark_case = BenchmarkCase::GeneratedTet4;
    result.configuration.nx = 1;
    result.configuration.ny = 2;
    result.configuration.nz = 3;
    result.configuration.thread_counts = {1, 2};
    result.configuration.warmup_count = 1;
    result.configuration.repeat_count = 1;
    result.configuration.amortization_count = 2;
    result.configuration.performance_evidence_level =
        PerformanceEvidenceLevel::CiSmoke;
    result.case_name = "cube,\"quoted\"\n立方体";
    result.element_type = "Tet4";
    result.node_count = 24;
    result.element_count = 36;
    result.dof_count = 72;
    result.nonzero_count = 999;
    result.input_prepare_ms = 0.125;
    result.correctness = BenchmarkCorrectness{
        true,
        1.0e-12,
        2.0e-12,
        1.0e-8,
        "PASS",
    };
    result.serial_measured.symbolic_total_ms = statistics(2.1);
    result.serial_measured.numeric_total_ms = statistics(3.1);

    ThreadBenchmarkSummary summary;
    summary.thread_count = 1;
    summary.symbolic_thread_count_observed = 1;
    summary.numeric_thread_count_observed = 1;
    summary.symbolic_pattern_ms = statistics(0.12345678901234566);
    summary.symbolic_scatter_ms = statistics(0.25);
    summary.symbolic_total_ms = statistics(0.8734567890123457);
    summary.numeric_reset_ms = statistics(0.1);
    summary.numeric_kernel_ms = statistics(0.4);
    summary.numeric_algorithm_ms = statistics(0.5);
    summary.numeric_total_ms = statistics(0.75);
    summary.amortized_total_ms = statistics(1.1867283945061728);
    summary.symbolic_speedup =
        result.serial_measured.symbolic_total_ms.median_ms /
        summary.symbolic_total_ms.median_ms;
    summary.numeric_speedup =
        result.serial_measured.numeric_total_ms.median_ms /
        (summary.numeric_reset_ms.median_ms +
         summary.numeric_kernel_ms.median_ms);
    result.per_thread_measured.push_back(summary);

    BenchmarkSample warmup;
    warmup.thread_count = 1;
    warmup.sample_index = 0;
    warmup.sample_kind = SampleKind::Warmup;
    warmup.input_prepare_ms = result.input_prepare_ms;
    warmup.serial_symbolic_ms = 2.1;
    warmup.serial_numeric_ms = 3.1;
    warmup.candidate_timings = timings(0.2);
    warmup.amortized_total_ms =
        warmup.candidate_timings.symbolic_total_ms / 2.0 +
        warmup.candidate_timings.numeric_total_ms;
    warmup.symbolic_speedup = summary.symbolic_speedup;
    warmup.numeric_speedup = summary.numeric_speedup;
    result.samples.push_back(warmup);

    BenchmarkSample measured = warmup;
    measured.sample_index = 1;
    measured.sample_kind = SampleKind::Measured;
    measured.candidate_timings = timings(0.12345678901234566);
    measured.amortized_total_ms =
        measured.candidate_timings.symbolic_total_ms / 2.0 +
        measured.candidate_timings.numeric_total_ms;
    result.samples.push_back(measured);

    ThreadBenchmarkSummary second_summary = summary;
    second_summary.thread_count = 2;
    second_summary.symbolic_thread_count_observed = 2;
    second_summary.numeric_thread_count_observed = 2;
    result.per_thread_measured.push_back(second_summary);
    BenchmarkSample second_warmup = warmup;
    second_warmup.thread_count = 2;
    result.samples.push_back(second_warmup);
    BenchmarkSample second_measured = measured;
    second_measured.thread_count = 2;
    result.samples.push_back(second_measured);

    result.estimated_persistent_bytes = 123456;
    result.performance_evidence_level = "ci-smoke";
    result.performance_gate_status = "NOT_APPLICABLE_GENERATED_CASE";
    result.performance_gate = evaluate_performance_gate(
        result.configuration.benchmark_case,
        result.configuration.performance_evidence_level,
        result.per_thread_measured);
    result.validation_cases = {
        synthetic_validation(ElementType::Tet4, 2),
        synthetic_validation(ElementType::Hex8, 2),
    };
    return result;
}

std::vector<std::vector<std::string>> parse_csv(const std::string& text) {
    std::vector<std::vector<std::string>> records;
    std::vector<std::string> record;
    std::string field;
    bool quoted = false;
    for (std::size_t index = 0; index < text.size(); ++index) {
        const char character = text[index];
        if (quoted) {
            if (character == '"') {
                if (index + 1 < text.size() && text[index + 1] == '"') {
                    field.push_back('"');
                    ++index;
                } else {
                    quoted = false;
                }
            } else {
                field.push_back(character);
            }
            continue;
        }
        if (character == '"' && field.empty()) {
            quoted = true;
        } else if (character == ',') {
            record.push_back(field);
            field.clear();
        } else if (character == '\n') {
            record.push_back(field);
            field.clear();
            records.push_back(record);
            record.clear();
        } else if (character != '\r') {
            field.push_back(character);
        }
    }
    require_true(!quoted, "CSV ended inside a quoted field");
    if (!field.empty() || !record.empty()) {
        record.push_back(field);
        records.push_back(record);
    }
    return records;
}

class JsonSyntaxValidator {
public:
    explicit JsonSyntaxValidator(const std::string& text) : text_(text) {}

    bool valid() {
        try {
            skip_space();
            parse_value();
            skip_space();
            return position_ == text_.size();
        } catch (const std::runtime_error&) {
            return false;
        }
    }

private:
    void fail() const {
        throw std::runtime_error("invalid JSON");
    }

    void skip_space() {
        while (position_ < text_.size() &&
               (text_[position_] == ' ' || text_[position_] == '\n' ||
                text_[position_] == '\r' || text_[position_] == '\t')) {
            ++position_;
        }
    }

    bool consume(char expected) {
        skip_space();
        if (position_ < text_.size() && text_[position_] == expected) {
            ++position_;
            return true;
        }
        return false;
    }

    void parse_value() {
        skip_space();
        if (position_ >= text_.size()) {
            fail();
        }
        switch (text_[position_]) {
        case '{':
            parse_object();
            return;
        case '[':
            parse_array();
            return;
        case '"':
            parse_string();
            return;
        case 't':
            parse_literal("true");
            return;
        case 'f':
            parse_literal("false");
            return;
        case 'n':
            parse_literal("null");
            return;
        default:
            parse_number();
        }
    }

    void parse_object() {
        require_or_fail(consume('{'));
        if (consume('}')) {
            return;
        }
        for (;;) {
            skip_space();
            require_or_fail(position_ < text_.size() && text_[position_] == '"');
            parse_string();
            require_or_fail(consume(':'));
            parse_value();
            if (consume('}')) {
                return;
            }
            require_or_fail(consume(','));
        }
    }

    void parse_array() {
        require_or_fail(consume('['));
        if (consume(']')) {
            return;
        }
        for (;;) {
            parse_value();
            if (consume(']')) {
                return;
            }
            require_or_fail(consume(','));
        }
    }

    void parse_string() {
        require_or_fail(position_ < text_.size() && text_[position_] == '"');
        ++position_;
        while (position_ < text_.size()) {
            const unsigned char character =
                static_cast<unsigned char>(text_[position_++]);
            if (character == '"') {
                return;
            }
            require_or_fail(character >= 0x20U);
            if (character == '\\') {
                require_or_fail(position_ < text_.size());
                const char escaped = text_[position_++];
                if (escaped == 'u') {
                    for (int digit = 0; digit < 4; ++digit) {
                        require_or_fail(position_ < text_.size());
                        const char value = text_[position_++];
                        require_or_fail((value >= '0' && value <= '9') ||
                                        (value >= 'a' && value <= 'f') ||
                                        (value >= 'A' && value <= 'F'));
                    }
                } else {
                    require_or_fail(escaped == '"' || escaped == '\\' ||
                                    escaped == '/' || escaped == 'b' ||
                                    escaped == 'f' || escaped == 'n' ||
                                    escaped == 'r' || escaped == 't');
                }
            }
        }
        fail();
    }

    void parse_number() {
        if (position_ < text_.size() && text_[position_] == '-') {
            ++position_;
        }
        require_or_fail(position_ < text_.size());
        if (text_[position_] == '0') {
            ++position_;
        } else {
            require_or_fail(text_[position_] >= '1' && text_[position_] <= '9');
            while (position_ < text_.size() && text_[position_] >= '0' &&
                   text_[position_] <= '9') {
                ++position_;
            }
        }
        if (position_ < text_.size() && text_[position_] == '.') {
            ++position_;
            const std::size_t fraction_start = position_;
            while (position_ < text_.size() && text_[position_] >= '0' &&
                   text_[position_] <= '9') {
                ++position_;
            }
            require_or_fail(position_ > fraction_start);
        }
        if (position_ < text_.size() &&
            (text_[position_] == 'e' || text_[position_] == 'E')) {
            ++position_;
            if (position_ < text_.size() &&
                (text_[position_] == '+' || text_[position_] == '-')) {
                ++position_;
            }
            const std::size_t exponent_start = position_;
            while (position_ < text_.size() && text_[position_] >= '0' &&
                   text_[position_] <= '9') {
                ++position_;
            }
            require_or_fail(position_ > exponent_start);
        }
    }

    void parse_literal(const char* literal) {
        while (*literal != '\0') {
            require_or_fail(position_ < text_.size() &&
                            text_[position_] == *literal);
            ++position_;
            ++literal;
        }
    }

    void require_or_fail(bool condition) const {
        if (!condition) {
            fail();
        }
    }

    const std::string& text_;
    std::size_t position_ = 0;
};

class TemporaryDirectory {
public:
    TemporaryDirectory() {
        const auto stamp = std::chrono::steady_clock::now()
                               .time_since_epoch()
                               .count();
        path_ = std::filesystem::temp_directory_path() /
                ("csc3-demo-benchmark-io-" + std::to_string(stamp));
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

std::string read_file(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    require_true(input.good(), "could not read expected output file");
    return std::string{std::istreambuf_iterator<char>(input),
                       std::istreambuf_iterator<char>()};
}

void test_csv_schema_escaping_and_round_trip_numbers() {
    const BenchmarkResult result = synthetic_result();
    const std::string csv = samples_csv_text(result);
    require_true(csv.rfind(std::string(kExpectedCsvHeader) + "\n", 0) == 0,
                 "CSV header is not exact");
    const auto records = parse_csv(csv);
    require_equal(records.size(), std::size_t{5}, "CSV record count");
    require_equal(records.front().size(), std::size_t{30}, "CSV header field count");
    for (std::size_t row = 1; row < records.size(); ++row) {
        require_equal(records[row].size(), std::size_t{30}, "CSV data field count");
        require_equal(records[row][0],
                      std::string(kBenchmarkSchemaVersion),
                      "CSV schema version");
        require_equal(records[row][1], result.case_name, "CSV escaped case name");
        require_equal(records[row][27], std::string("PASS"), "CSV status");
        require_equal(records[row][29], std::string("ci-smoke"), "CSV evidence level");
        const std::vector<std::size_t> numeric_fields{
            3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15,
            16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28,
        };
        for (const std::size_t field : numeric_fields) {
            std::size_t consumed = 0;
            const double parsed = std::stod(records[row][field], &consumed);
            require_true(consumed == records[row][field].size() &&
                             std::isfinite(parsed),
                         "CSV numeric field is not finite and parseable");
        }
    }
    require_true(csv.find("\"cube,\"\"quoted\"\"\n立方体\"") !=
                     std::string::npos,
                 "CSV did not quote comma, quote, and newline");
    require_true(csv.find("0.12345678901234566") != std::string::npos,
                 "CSV did not retain round-trip double precision");
}

void test_json_is_valid_complete_utf8_without_fabricated_provenance() {
    const BenchmarkResult result = synthetic_result();
    const std::string json = summary_json_text(result);
    require_true(JsonSyntaxValidator(json).valid(), "summary is not valid JSON");
    for (const std::string& required : {
             "\"schema_version\"",
             "\"configuration\"",
             "\"case_sizes\"",
             "\"correctness\"",
             "\"validation_cases_schema_version\": \"csc3-demo-validation-v1\"",
             "\"validation_thresholds\"",
             "\"relative_frobenius_error_max\": 1e-08",
             "\"relative_displacement_error_max\": 1e-08",
             "\"relative_residual_max\": 1e-10",
             "\"validation_cases\"",
             "\"case_name\": \"cube_tet4_1x1x1\"",
             "\"case_name\": \"cube_hex8_1x1x1\"",
             "\"element_type\": \"Tet4\"",
             "\"element_type\": \"Hex8\"",
             "\"node_count\": 8",
             "\"element_count\": 6",
             "\"dof_count\": 24",
             "\"thread_count\": 2",
             "\"matrix\"",
             "\"displacement\"",
             "\"structure_matches\": true",
             "\"relative_displacement_error\"",
             "\"parallel_relative_residual\"",
             "\"serial_relative_residual\"",
             "\"parallel_displacement_norm\"",
             "\"serial_displacement_norm\"",
             "\"status\": \"PASS\"",
             "\"serial_measured_statistics\"",
             "\"per_thread_measured_statistics\"",
             "\"symbolic_speedup\"",
             "\"numeric_speedup\"",
             "\"numeric_speedup_basis\": "
             "\"serial_reset_plus_kernel_over_atomic_reset_plus_kernel\"",
             "\"estimated_persistent_memory_kind\": \"owned_vector_payload_bytes_not_rss\"",
             "\"performance_evidence_level\": \"ci-smoke\"",
             "\"performance_gate_status\": \"NOT_APPLICABLE_GENERATED_CASE\"",
             "\"performance_gate\"",
             "\"numeric_algorithm_ms\"",
             "\"symbolic_thread_count_observed\": 1",
             "\"numeric_thread_count_observed\": 1",
             "立方体"}) {
        require_true(json.find(required) != std::string::npos,
                     "summary JSON is missing " + required);
    }
    for (const std::string& forbidden : {
             "git_sha", "dirty", "operating_system", "cpu_model",
             "input_sha256", "formal_pass"}) {
        require_true(json.find(forbidden) == std::string::npos,
                     "summary JSON fabricated provenance field " + forbidden);
    }
}

void test_malformed_validation_evidence_is_rejected() {
    const auto require_rejected = [](const BenchmarkResult& result,
                                     const std::string& label) {
        require_throws<std::runtime_error>(
            [&result] { static_cast<void>(summary_json_text(result)); },
            label);
    };

    BenchmarkResult result = synthetic_result();
    result.validation_cases.clear();
    require_rejected(result, "missing validation cases");

    result = synthetic_result();
    result.validation_cases.push_back(result.validation_cases.back());
    require_rejected(result, "extra validation case");

    result = synthetic_result();
    std::swap(result.validation_cases[0], result.validation_cases[1]);
    require_rejected(result, "swapped validation cases");

    result = synthetic_result();
    result.validation_cases[0].case_name = "wrong";
    require_rejected(result, "wrong validation identity");

    result = synthetic_result();
    result.validation_cases[0].node_count = 9;
    require_rejected(result, "wrong validation size");

    result = synthetic_result();
    result.validation_cases[1].thread_count = 1;
    require_rejected(result, "wrong validation thread");

    result = synthetic_result();
    result.validation_cases[0].matrix.relative_frobenius_error =
        std::numeric_limits<double>::quiet_NaN();
    require_rejected(result, "nonfinite validation metric");

    result = synthetic_result();
    result.validation_cases[0].matrix.max_absolute_error = -1.0;
    require_rejected(result, "negative validation metric");

    result = synthetic_result();
    result.validation_cases[0].matrix.relative_frobenius_error = 1.1e-8;
    require_rejected(result, "matrix threshold failure");

    result = synthetic_result();
    result.validation_cases[0].matrix.max_absolute_error = 2.0e-8;
    require_rejected(result, "matrix absolute threshold failure");

    result = synthetic_result();
    result.validation_cases[0].displacement.relative_displacement_error = 1.1e-8;
    require_rejected(result, "displacement threshold failure");

    result = synthetic_result();
    result.validation_cases[0].displacement.parallel_relative_residual = 1.1e-10;
    require_rejected(result, "parallel residual threshold failure");

    result = synthetic_result();
    result.validation_cases[0].displacement.serial_relative_residual = 1.1e-10;
    require_rejected(result, "serial residual threshold failure");

    result = synthetic_result();
    result.validation_cases[0].displacement.parallel_displacement_norm = 0.0;
    require_rejected(result, "nonpositive displacement norm");

    result = synthetic_result();
    result.validation_cases[0].matrix.structure_matches = false;
    require_rejected(result, "validation structure mismatch");

    result = synthetic_result();
    result.validation_cases[0].matrix.passed = false;
    require_rejected(result, "contradictory validation matrix status");

    result = synthetic_result();
    result.validation_cases[0].passed = false;
    require_rejected(result, "contradictory validation case status");
}

void test_invalid_result_is_rejected_before_serialization() {
    BenchmarkResult result = synthetic_result();
    result.correctness.status = "FAIL";
    require_throws<std::runtime_error>(
        [&result] { static_cast<void>(samples_csv_text(result)); },
        "failed correctness CSV");
    require_throws<std::runtime_error>(
        [&result] { static_cast<void>(summary_json_text(result)); },
        "failed correctness JSON");

    result = synthetic_result();
    result.samples.front().candidate_timings.numeric_total_ms =
        std::numeric_limits<double>::infinity();
    require_throws<std::runtime_error>(
        [&result] { static_cast<void>(samples_csv_text(result)); },
        "nonfinite timing CSV");
    require_throws<std::runtime_error>(
        [&result] { static_cast<void>(summary_json_text(result)); },
        "nonfinite timing JSON");

    result = synthetic_result();
    result.case_name = std::string{"\xC0\xAF", 2};
    require_throws<std::runtime_error>(
        [&result] { static_cast<void>(summary_json_text(result)); },
        "invalid UTF-8 JSON");
}

void test_recomputed_evidence_rejects_summary_and_raw_tampering() {
    const auto require_rejected = [](const BenchmarkResult& result,
                                     const std::string& label) {
        require_throws<std::runtime_error>(
            [&result] { static_cast<void>(samples_csv_text(result)); },
            label + " CSV");
        require_throws<std::runtime_error>(
            [&result] { static_cast<void>(summary_json_text(result)); },
            label + " JSON");
    };

    using StatisticField = double SummaryStatistics::*;
    const std::vector<StatisticField> statistic_fields{
        &SummaryStatistics::mean_ms,
        &SummaryStatistics::median_ms,
        &SummaryStatistics::population_standard_deviation_ms,
        &SummaryStatistics::minimum_ms,
        &SummaryStatistics::maximum_ms,
        &SummaryStatistics::coefficient_of_variation,
    };
    for (const StatisticField field : statistic_fields) {
        BenchmarkResult result = synthetic_result();
        result.serial_measured.symbolic_total_ms.*field += 0.01;
        require_rejected(result, "tampered serial symbolic statistic");
    }
    {
        BenchmarkResult result = synthetic_result();
        ++result.serial_measured.symbolic_total_ms.sample_count;
        require_rejected(result, "tampered summary sample count");
    }
    {
        BenchmarkResult result = synthetic_result();
        result.serial_measured.numeric_total_ms.mean_ms += 0.01;
        require_rejected(result, "tampered serial numeric statistic");
    }

    using PhaseField = SummaryStatistics ThreadBenchmarkSummary::*;
    const std::vector<PhaseField> phase_fields{
        &ThreadBenchmarkSummary::symbolic_pattern_ms,
        &ThreadBenchmarkSummary::symbolic_scatter_ms,
        &ThreadBenchmarkSummary::symbolic_total_ms,
        &ThreadBenchmarkSummary::numeric_reset_ms,
        &ThreadBenchmarkSummary::numeric_kernel_ms,
        &ThreadBenchmarkSummary::numeric_algorithm_ms,
        &ThreadBenchmarkSummary::numeric_total_ms,
        &ThreadBenchmarkSummary::amortized_total_ms,
    };
    for (const PhaseField field : phase_fields) {
        BenchmarkResult result = synthetic_result();
        (result.per_thread_measured.front().*field).mean_ms += 0.01;
        require_rejected(result, "tampered per-thread phase statistic");
    }

    {
        BenchmarkResult result = synthetic_result();
        result.per_thread_measured.front().symbolic_speedup += 0.1;
        result.samples[0].symbolic_speedup =
            result.per_thread_measured.front().symbolic_speedup;
        result.samples[1].symbolic_speedup =
            result.per_thread_measured.front().symbolic_speedup;
        require_rejected(result, "tampered symbolic speedup");
    }
    {
        BenchmarkResult result = synthetic_result();
        result.per_thread_measured.front().numeric_speedup += 0.1;
        result.samples[0].numeric_speedup =
            result.per_thread_measured.front().numeric_speedup;
        result.samples[1].numeric_speedup =
            result.per_thread_measured.front().numeric_speedup;
        require_rejected(result, "tampered numeric speedup");
    }
    {
        BenchmarkResult result = synthetic_result();
        result.samples[2].serial_symbolic_ms += 0.01;
        require_rejected(result, "cross-thread serial symbolic mismatch");
    }
    {
        BenchmarkResult result = synthetic_result();
        result.samples[3].serial_numeric_ms += 0.01;
        require_rejected(result, "cross-thread serial numeric mismatch");
    }
    {
        BenchmarkResult result = synthetic_result();
        result.samples.front().input_prepare_ms += 0.01;
        require_rejected(result, "sample input preparation mismatch");
    }
}

void test_help_version_and_deterministic_dry_run() {
    std::ostringstream output;
    std::ostringstream error;
    require_equal(run_benchmark_cli({"--help"}, output, error), 0, "help exit code");
    require_true(output.str().find("--threads-list") != std::string::npos,
                 "help omits supported options");
    require_true(error.str().empty(), "help wrote to stderr");

    output.str("");
    output.clear();
    require_equal(run_benchmark_cli({"--version"}, output, error),
                  0,
                  "version exit code");
    require_equal(output.str(),
                  std::string("csc3_demo_benchmark 0.2.0\n"),
                  "version output");

    output.str("");
    output.clear();
    error.str("");
    error.clear();
    require_equal(run_benchmark_cli({"--dry-run"}, output, error),
                  0,
                  "default dry-run exit code");
    const std::string default_plan = output.str();
    for (const std::string& expected : {
             "case=generated-tet4\n",
             "grid=1x1x1\n",
             "threads=1,2\n",
             "warmup=2\n",
             "repeat=7\n",
             "amortization_count=1\n",
             "performance_evidence_level=local-smoke\n",
         }) {
        require_true(default_plan.find(expected) != std::string::npos,
                     "default dry-run omitted " + expected);
    }

    TemporaryDirectory temporary;
    const std::filesystem::path csv = temporary.path() / "dry.csv";
    const std::filesystem::path json = temporary.path() / "dry.json";
    const std::vector<std::string> arguments{
        "--case", "generated-hex8",
        "--nx", "2", "--ny", "3", "--nz", "4",
        "--threads-list", "1",
        "--warmup", "0", "--repeat", "1",
        "--amortization-count", "2",
        "--evidence-level", "ci-smoke",
        "--samples-csv", csv.string(),
        "--summary-json", json.string(),
        "--dry-run",
    };
    output.str("");
    output.clear();
    error.str("");
    error.clear();
    require_equal(run_benchmark_cli(arguments, output, error),
                  0,
                  "dry-run exit code");
    const std::string first_plan = output.str();
    output.str("");
    output.clear();
    require_equal(run_benchmark_cli(arguments, output, error),
                  0,
                  "second dry-run exit code");
    require_equal(output.str(), first_plan, "deterministic dry-run plan");
    require_true(first_plan.find("case=generated-hex8") != std::string::npos &&
                     first_plan.find("grid=2x3x4") != std::string::npos &&
                     first_plan.find("threads=1") != std::string::npos &&
                     first_plan.find("mode=dry-run") != std::string::npos,
                 "dry-run plan is incomplete");
    require_true(error.str().empty(), "dry-run wrote to stderr");
    require_true(!std::filesystem::exists(csv) &&
                     !std::filesystem::exists(json),
                 "dry-run created output files");
}

int run_invalid(const std::vector<std::string>& arguments) {
    std::ostringstream output;
    std::ostringstream error;
    const int exit_code = run_benchmark_cli(arguments, output, error);
    require_true(exit_code != 0, "invalid CLI unexpectedly succeeded");
    require_true(!error.str().empty(), "invalid CLI did not explain the error");
    return exit_code;
}

void test_invalid_arguments_and_output_contracts() {
    TemporaryDirectory temporary;
    const std::filesystem::path csv = temporary.path() / "samples.csv";
    const std::filesystem::path json = temporary.path() / "summary.json";
    const std::string csv_text = csv.string();
    const std::string json_text = json.string();

    for (const std::vector<std::string>& arguments : {
             std::vector<std::string>{"--unknown"},
             {"--case"},
             {"--case", "bad", "--dry-run"},
             {"--case", "generated-tet4", "--case", "generated-hex8", "--dry-run"},
             {"--nx", "1x", "--dry-run"},
             {"--nx", "0", "--dry-run"},
             {"--threads-list", "", "--dry-run"},
             {"--threads-list", "1,,2", "--dry-run"},
             {"--threads-list", "1,1", "--dry-run"},
             {"--threads-list", "0", "--dry-run"},
             {"--warmup", "-1", "--dry-run"},
             {"--repeat", "0", "--dry-run"},
             {"--amortization-count", "0", "--dry-run"},
             {"--evidence-level", "bad", "--dry-run"},
             {"--evidence-level", "formal", "--dry-run"},
             {"--threads-list", "1", "--warmup", "0", "--repeat", "1"},
             {"--threads-list", "1", "--warmup", "0", "--repeat", "1",
              "--samples-csv", csv_text},
             {"--threads-list", "1", "--warmup", "0", "--repeat", "1",
              "--samples-csv", csv_text, "--summary-json", csv_text},
         }) {
        static_cast<void>(run_invalid(arguments));
    }

    if (csc3_demo::max_openmp_threads() < std::numeric_limits<int>::max()) {
        static_cast<void>(run_invalid({
            "--threads-list",
            std::to_string(csc3_demo::max_openmp_threads() + 1),
            "--dry-run",
        }));
    }

    const std::filesystem::path missing_parent =
        temporary.path() / "missing";
    static_cast<void>(run_invalid({
        "--threads-list", "1", "--warmup", "0", "--repeat", "1",
        "--samples-csv", (missing_parent / "samples.csv").string(),
        "--summary-json", (missing_parent / "summary.json").string(),
    }));
    require_true(!std::filesystem::exists(missing_parent),
                 "CLI created a missing output parent");

    {
        std::ofstream existing(csv);
        existing << "sentinel";
    }
    static_cast<void>(run_invalid({
        "--threads-list", "1", "--warmup", "0", "--repeat", "1",
        "--samples-csv", csv_text, "--summary-json", json_text,
    }));
    require_equal(read_file(csv), std::string("sentinel"), "existing output contents");
    require_true(!std::filesystem::exists(json),
                 "existing-output rejection created the peer file");
}

void test_normal_cli_writes_both_outputs_and_refuses_overwrite() {
    TemporaryDirectory temporary;
    const std::filesystem::path csv = temporary.path() / "samples.csv";
    const std::filesystem::path json = temporary.path() / "summary.json";
    const std::vector<std::string> arguments{
        "--case", "generated-tet4",
        "--threads-list", "1",
        "--warmup", "0",
        "--repeat", "1",
        "--amortization-count", "1",
        "--evidence-level", "ci-smoke",
        "--samples-csv", csv.string(),
        "--summary-json", json.string(),
    };
    std::ostringstream output;
    std::ostringstream error;
    require_equal(run_benchmark_cli(arguments, output, error),
                  0,
                  "normal CLI exit code");
    require_true(error.str().empty(), "normal CLI wrote to stderr");
    require_true(std::filesystem::is_regular_file(csv) &&
                     std::filesystem::is_regular_file(json),
                 "normal CLI did not write both outputs");
    const std::string first_csv = read_file(csv);
    const std::string first_json = read_file(json);
    require_true(first_csv.rfind(std::string(kExpectedCsvHeader) + "\n", 0) == 0,
                 "CLI CSV header is invalid");
    require_true(JsonSyntaxValidator(first_json).valid(),
                 "CLI JSON is invalid");
    require_true(output.str().find("matrix_correctness_status=PASS") !=
                     std::string::npos,
                 "normal CLI omitted success status");

    output.str("");
    output.clear();
    error.str("");
    error.clear();
    require_true(run_benchmark_cli(arguments, output, error) != 0,
                 "normal CLI overwrote existing outputs");
    require_equal(read_file(csv), first_csv, "CSV after overwrite refusal");
    require_equal(read_file(json), first_json, "JSON after overwrite refusal");
}

void test_direct_file_writers_refuse_existing_paths() {
    TemporaryDirectory temporary;
    const std::filesystem::path existing = temporary.path() / "existing.txt";
    {
        std::ofstream output(existing);
        output << "sentinel";
    }
    const BenchmarkResult result = synthetic_result();
    require_throws<std::runtime_error>(
        [&result, &existing] { write_samples_csv(result, existing); },
        "CSV writer existing path");
    require_throws<std::runtime_error>(
        [&result, &existing] { write_summary_json(result, existing); },
        "JSON writer existing path");
    require_equal(read_file(existing), std::string("sentinel"), "writer overwrite refusal");
}

void test_zero_serial_baseline_is_reported_as_zero_speedup() {
    BenchmarkResult result = synthetic_result();
    result.serial_measured.symbolic_total_ms = statistics(0.0);
    result.serial_measured.numeric_total_ms = statistics(0.0);
    for (ThreadBenchmarkSummary& summary : result.per_thread_measured) {
        summary.symbolic_speedup = 0.0;
        summary.numeric_speedup = 0.0;
    }
    for (BenchmarkSample& sample : result.samples) {
        sample.serial_symbolic_ms = 0.0;
        sample.serial_numeric_ms = 0.0;
        sample.symbolic_speedup = 0.0;
        sample.numeric_speedup = 0.0;
    }
    result.performance_gate = evaluate_performance_gate(
        result.configuration.benchmark_case,
        result.configuration.performance_evidence_level,
        result.per_thread_measured);
    result.performance_gate_status = result.performance_gate.status;
    const std::string csv = samples_csv_text(result);
    const std::string json = summary_json_text(result);
    require_true(!csv.empty() && !json.empty(),
                 "zero serial baseline could not be serialized");
}

} // namespace

int main() {
    try {
        test_csv_schema_escaping_and_round_trip_numbers();
        test_json_is_valid_complete_utf8_without_fabricated_provenance();
        test_malformed_validation_evidence_is_rejected();
        test_invalid_result_is_rejected_before_serialization();
        test_recomputed_evidence_rejects_summary_and_raw_tampering();
        test_help_version_and_deterministic_dry_run();
        test_invalid_arguments_and_output_contracts();
        test_normal_cli_writes_both_outputs_and_refuses_overwrite();
        test_direct_file_writers_refuse_existing_paths();
        test_zero_serial_baseline_is_reported_as_zero_speedup();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
