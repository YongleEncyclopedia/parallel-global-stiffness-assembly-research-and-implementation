#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/platform.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace fem;

namespace {

struct Config {
    std::string mesh_mode = "cube";
    std::string inp_path;
    std::string case_name;
    ElementType element_type = ElementType::Tet4;
    int nx = 6;
    int ny = 6;
    int nz = 6;
    std::vector<AlgorithmType> algorithms;
    std::vector<int> thread_counts{1};
    KernelType kernel = KernelType::Simplified;
    int warmup = 0;
    int repeat = 1;
    bool check = false;
    bool threads_all = false;
    std::string csv_path = "benchmark_results_cpu.csv";
    std::string json_path;
    std::string summary_md_path;
    Size max_transient_bytes = static_cast<Size>(8ull * 1024ull * 1024ull * 1024ull);
    Real young = constants::DEFAULT_YOUNG_MODULUS;
    Real poisson = constants::DEFAULT_POISSON_RATIO;
};

struct RunRecord {
    std::string case_name;
    std::string mesh_name;
    std::string algorithm;
    int threads = 1;
    int effective_threads = 1;
    std::string status = "PASS";
    std::string skip_reason;
    AssemblyStats stats;
    MatrixError error;
    double speedup = 0.0;
    double efficiency = 0.0;
    double preprocess_share = 0.0;
    double peak_rss_mb = 0.0;
    double assembly_mean_ms = 0.0;
    double assembly_min_ms = 0.0;
    double assembly_max_ms = 0.0;
    double assembly_std_ms = 0.0;
    double total_mean_ms = 0.0;
    double total_min_ms = 0.0;
    double total_max_ms = 0.0;
    double total_std_ms = 0.0;
    int run_count = 0;
    std::string message;
    std::string platform;
    std::string omp_proc_bind;
    std::string omp_places;
    std::string omp_dynamic;
};

std::vector<std::string> split(const std::string& s, char sep) {
    std::vector<std::string> out;
    std::string token;
    std::stringstream ss(s);
    while (std::getline(ss, token, sep)) {
        if (!token.empty()) out.push_back(token);
    }
    return out;
}

std::string csv_escape(const std::string& value) {
    std::string out = value;
    Size pos = 0;
    while ((pos = out.find('"', pos)) != std::string::npos) {
        out.insert(pos, 1, '"');
        pos += 2;
    }
    return '"' + out + '"';
}

std::string json_escape(const std::string& value) {
    std::ostringstream os;
    for (char ch : value) {
        switch (ch) {
        case '\\': os << "\\\\"; break;
        case '"': os << "\\\""; break;
        case '\n': os << "\\n"; break;
        case '\r': os << "\\r"; break;
        case '\t': os << "\\t"; break;
        default: os << ch; break;
        }
    }
    return os.str();
}

double mean_value(const std::vector<double>& values) {
    if (values.empty()) return 0.0;
    const double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

double min_value(const std::vector<double>& values) {
    return values.empty() ? 0.0 : *std::min_element(values.begin(), values.end());
}

double max_value(const std::vector<double>& values) {
    return values.empty() ? 0.0 : *std::max_element(values.begin(), values.end());
}

double stddev_value(const std::vector<double>& values) {
    if (values.size() < 2) return 0.0;
    const double mu = mean_value(values);
    double sq = 0.0;
    for (double value : values) sq += (value - mu) * (value - mu);
    return std::sqrt(sq / static_cast<double>(values.size()));
}

std::vector<int> parse_threads_range(const std::string& text) {
    const auto parts = split(text, ':');
    if (parts.size() < 2 || parts.size() > 3) {
        throw std::invalid_argument("Invalid --threads-range, expected start:end[:step]");
    }
    const int begin = std::stoi(parts[0]);
    const int end = std::stoi(parts[1]);
    const int step = parts.size() == 3 ? std::stoi(parts[2]) : 1;
    if (begin <= 0 || end <= 0 || step <= 0 || begin > end) {
        throw std::invalid_argument("Invalid --threads-range values");
    }
    std::vector<int> out;
    for (int value = begin; value <= end; value += step) out.push_back(value);
    return out;
}

std::vector<int> parse_threads(const std::string& text) {
    std::vector<int> out;
    for (const auto& token : split(text, ',')) out.push_back(std::stoi(token));
    return out;
}

std::vector<AlgorithmType> parse_algorithms(const std::string& text) {
    if (to_lower_ascii(text) == "all") return AssemblerFactory::get_available_algorithms();
    std::vector<AlgorithmType> out;
    for (const auto& token : split(text, ',')) out.push_back(parse_algorithm_type(token));
    return out;
}

void normalize_threads(Config& cfg) {
    std::set<int> unique;
    if (cfg.threads_all) {
        for (int t = 1; t <= max_thread_count(); ++t) unique.insert(t);
    }
    for (int t : cfg.thread_counts) {
        if (t > 0) unique.insert(t);
    }
    if (unique.empty()) unique.insert(1);
    cfg.thread_counts.assign(unique.begin(), unique.end());
}

std::string infer_case_name(const Config& cfg) {
    if (!cfg.case_name.empty()) return cfg.case_name;
    if (to_lower_ascii(cfg.mesh_mode) == "inp") {
        return std::filesystem::path(cfg.inp_path).stem().string();
    }
    return "cube_" + to_lower_ascii(element_type_to_string(cfg.element_type)) + "_" +
           std::to_string(cfg.nx) + "x" + std::to_string(cfg.ny) + "x" + std::to_string(cfg.nz);
}

bool is_git_lfs_pointer(const std::string& path) {
    std::ifstream in(path);
    if (!in) return false;
    std::string line1;
    std::string line2;
    std::getline(in, line1);
    std::getline(in, line2);
    return line1.rfind("version https://git-lfs.github.com/spec/v1", 0) == 0 &&
           line2.rfind("oid sha256:", 0) == 0;
}

std::string classify_skip_reason(const std::string& message) {
    const auto lowered = to_lower_ascii(message);
    if (lowered.find("above limit") != std::string::npos || lowered.find("transient memory") != std::string::npos) {
        return "RESOURCE_LIMIT";
    }
    if (lowered.find("git lfs pointer") != std::string::npos) return "INPUT_NOT_READY";
    if (lowered.find("unknown argument") != std::string::npos) return "CLI_ERROR";
    return "EXECUTION_ERROR";
}

void print_usage(const char* exe) {
    std::cout
        << "CPU 并行整体刚度矩阵组装基准程序 / CPU Parallel Stiffness Assembly Benchmark\n\n"
        << "用法 / Usage:\n  " << exe << " [options]\n\n"
        << "主要参数 / Main options:\n"
        << "  --mesh cube|inp                  网格来源，默认 cube\n"
        << "  --element tet4|hex8              规则块体单元类型，默认 tet4\n"
        << "  --nx N --ny N --nz N             规则块体分辨率，默认 6 6 6\n"
        << "  --inp PATH                       Abaqus .inp 路径，用于 --mesh inp\n"
        << "  --case-name NAME                 结果中的实验名称，默认由输入自动推断\n"
        << "  --algo LIST                      serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner,all\n"
        << "  --threads N                      单个线程数\n"
        << "  --threads-list 1,2,4,8           线程列表\n"
        << "  --threads-range 1:14[:step]      线程范围\n"
        << "  --threads-all                    自动扫描 1..max_threads\n"
        << "  --kernel simplified|physics_tet4 局部刚度 kernel\n"
        << "  --warmup N --repeat N            预热次数 / 正式重复次数\n"
        << "  --check                          与 1 线程串行基线对比正确性\n"
        << "  --csv PATH                       CSV 输出路径\n"
        << "  --json PATH                      JSON 输出路径\n"
        << "  --summary-md PATH                Markdown 摘要路径\n"
        << "  --max-memory-gb X                瞬时内存上限，默认 8 GiB\n"
        << "  --help\n";
}

Config parse_args(int argc, char** argv) {
    Config cfg;
    cfg.algorithms = {
        AlgorithmType::CpuSerial,
        AlgorithmType::CpuAtomic,
        AlgorithmType::CpuPrivateCsr,
        AlgorithmType::CpuCooSortReduce,
        AlgorithmType::CpuGraphColoring,
        AlgorithmType::CpuRowOwner,
    };
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto require_value = [&](const std::string& name) -> std::string {
            if (i + 1 >= argc) throw std::invalid_argument("Missing value for " + name);
            return argv[++i];
        };
        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            std::exit(0);
        } else if (arg == "--mesh") cfg.mesh_mode = require_value(arg);
        else if (arg == "--element") cfg.element_type = parse_element_type(require_value(arg));
        else if (arg == "--nx") cfg.nx = std::stoi(require_value(arg));
        else if (arg == "--ny") cfg.ny = std::stoi(require_value(arg));
        else if (arg == "--nz") cfg.nz = std::stoi(require_value(arg));
        else if (arg == "--inp") cfg.inp_path = require_value(arg);
        else if (arg == "--case-name") cfg.case_name = require_value(arg);
        else if (arg == "--algo" || arg == "--algorithms") cfg.algorithms = parse_algorithms(require_value(arg));
        else if (arg == "--threads") cfg.thread_counts = {std::stoi(require_value(arg))};
        else if (arg == "--threads-list") cfg.thread_counts = parse_threads(require_value(arg));
        else if (arg == "--threads-range") cfg.thread_counts = parse_threads_range(require_value(arg));
        else if (arg == "--threads-all") cfg.threads_all = true;
        else if (arg == "--kernel") cfg.kernel = parse_kernel_type(require_value(arg));
        else if (arg == "--warmup") cfg.warmup = std::stoi(require_value(arg));
        else if (arg == "--repeat") cfg.repeat = std::max(1, std::stoi(require_value(arg)));
        else if (arg == "--check") cfg.check = true;
        else if (arg == "--csv") cfg.csv_path = require_value(arg);
        else if (arg == "--json") cfg.json_path = require_value(arg);
        else if (arg == "--summary-md") cfg.summary_md_path = require_value(arg);
        else if (arg == "--max-memory-gb") {
            const double gb = std::stod(require_value(arg));
            cfg.max_transient_bytes = static_cast<Size>(gb * 1024.0 * 1024.0 * 1024.0);
        } else if (arg == "--young") cfg.young = std::stod(require_value(arg));
        else if (arg == "--poisson") cfg.poisson = std::stod(require_value(arg));
        else throw std::invalid_argument("Unknown argument: " + arg);
    }
    normalize_threads(cfg);
    cfg.case_name = infer_case_name(cfg);
    return cfg;
}

Mesh build_mesh(const Config& cfg) {
    if (to_lower_ascii(cfg.mesh_mode) == "cube") {
        Mesh mesh = cfg.element_type == ElementType::Tet4
                        ? Mesh::make_cube_tet4(cfg.nx, cfg.ny, cfg.nz)
                        : Mesh::make_cube_hex8(cfg.nx, cfg.ny, cfg.nz);
        mesh.name = cfg.case_name;
        return mesh;
    }
    if (to_lower_ascii(cfg.mesh_mode) == "inp") {
        if (cfg.inp_path.empty()) throw std::invalid_argument("--mesh inp requires --inp PATH");
        if (is_git_lfs_pointer(cfg.inp_path)) {
            throw std::runtime_error("Input file is still a Git LFS pointer. Run `git lfs pull` and retry.");
        }
        Mesh mesh = Mesh::load_from_inp(cfg.inp_path);
        mesh.name = cfg.case_name;
        return mesh;
    }
    throw std::invalid_argument("Unsupported mesh mode: " + cfg.mesh_mode);
}

void average_stage_fields(AssemblyStats& dst, const std::vector<AssemblyStats>& samples) {
    if (samples.empty()) return;
    const double inv = 1.0 / static_cast<double>(samples.size());
    for (const auto& s : samples) {
        dst.assembly_zero_ms += s.assembly_zero_ms * inv;
        dst.assembly_generate_ms += s.assembly_generate_ms * inv;
        dst.assembly_numeric_ms += s.assembly_numeric_ms * inv;
        dst.assembly_merge_ms += s.assembly_merge_ms * inv;
        dst.assembly_sort_ms += s.assembly_sort_ms * inv;
        dst.assembly_reduce_ms += s.assembly_reduce_ms * inv;
    }
}

RunRecord run_one(AlgorithmType algo,
                  int threads,
                  const Config& cfg,
                  const Mesh& mesh,
                  const CsrMatrix& csr,
                  const AssemblyPlan& plan,
                  const CsrMatrix* reference,
                  double serial_time_ms) {
    RunRecord record;
    record.case_name = cfg.case_name;
    record.mesh_name = mesh.name;
    record.algorithm = algorithm_to_string(algo);
    record.threads = threads;
    record.platform = platform_info_compact();
    record.omp_proc_bind = environment_value_or_empty("OMP_PROC_BIND");
    record.omp_places = environment_value_or_empty("OMP_PLACES");
    record.omp_dynamic = environment_value_or_empty("OMP_DYNAMIC");

    AssemblyOptions options;
    options.threads = threads;
    options.kernel = cfg.kernel;
    options.max_transient_bytes = cfg.max_transient_bytes;
    options.young_modulus = cfg.young;
    options.poisson_ratio = cfg.poisson;

    try {
        auto assembler = AssemblerFactory::create(algo, options);
        assembler->set_problem(mesh, csr, plan);
        const auto prep0 = std::chrono::steady_clock::now();
        assembler->prepare();
        const auto prep1 = std::chrono::steady_clock::now();
        auto prepare_stats = assembler->get_stats();
        if (prepare_stats.preprocess_time_ms == 0.0) {
            prepare_stats.preprocess_time_ms = std::chrono::duration<double, std::milli>(prep1 - prep0).count();
        }
        record.effective_threads = effective_thread_count(threads);

        for (int i = 0; i < cfg.warmup; ++i) assembler->assemble();

        std::vector<double> assembly_samples;
        std::vector<double> total_samples;
        std::vector<AssemblyStats> sample_stats;
        assembly_samples.reserve(static_cast<Size>(cfg.repeat));
        total_samples.reserve(static_cast<Size>(cfg.repeat));
        sample_stats.reserve(static_cast<Size>(cfg.repeat));
        for (int i = 0; i < cfg.repeat; ++i) {
            assembler->assemble();
            auto s = assembler->get_stats();
            assembly_samples.push_back(s.assembly_time_ms);
            total_samples.push_back(s.total_time_ms);
            sample_stats.push_back(s);
        }

        record.run_count = cfg.repeat;
        record.assembly_mean_ms = mean_value(assembly_samples);
        record.assembly_min_ms = min_value(assembly_samples);
        record.assembly_max_ms = max_value(assembly_samples);
        record.assembly_std_ms = stddev_value(assembly_samples);
        record.total_mean_ms = mean_value(total_samples);
        record.total_min_ms = min_value(total_samples);
        record.total_max_ms = max_value(total_samples);
        record.total_std_ms = stddev_value(total_samples);
        record.stats = prepare_stats;
        record.stats.assembly_time_ms = record.assembly_mean_ms;
        record.stats.total_time_ms = record.total_mean_ms;
        average_stage_fields(record.stats, sample_stats);
        record.peak_rss_mb = current_peak_rss_mb();

        if (reference) {
            record.error = compare_values(*reference, assembler->get_result());
        } else {
            record.error = compare_values(assembler->get_result(), assembler->get_result());
        }

        record.speedup = record.stats.assembly_time_ms > 0.0 ? serial_time_ms / record.stats.assembly_time_ms : 0.0;
        record.efficiency =
            record.effective_threads > 0 ? record.speedup / static_cast<double>(record.effective_threads) : 0.0;
        record.preprocess_share =
            record.stats.total_time_ms > 0.0 ? record.stats.preprocess_time_ms / record.stats.total_time_ms : 0.0;

        if (cfg.check && reference && (!record.error.same_structure || record.error.relative_l2 > 1.0e-8)) {
            record.status = "FAIL";
            record.message = "Correctness check failed";
        } else if (!record.stats.diagnostics.empty()) {
            record.message = record.stats.diagnostics;
        }
    } catch (const std::exception& ex) {
        record.status = "SKIP";
        record.skip_reason = classify_skip_reason(ex.what());
        record.message = ex.what();
        if (record.skip_reason == "INPUT_NOT_READY" || record.skip_reason == "CLI_ERROR") {
            record.status = "FAIL";
        }
    }
    return record;
}

void write_csv_header(std::ofstream& out) {
    out << "case_name,mesh,element_type,kernel,nodes,elements,dofs,nnz,algorithm,threads,effective_threads,"
        << "run_count,preprocess_ms,assembly_ms,total_ms,assembly_mean_ms,assembly_min_ms,assembly_max_ms,"
        << "assembly_std_ms,total_mean_ms,total_min_ms,total_max_ms,total_std_ms,speedup,efficiency,"
        << "preprocess_share,rel_l2,max_abs,extra_memory_bytes,peak_rss_mb,colors,prepare_allocate_ms,"
        << "prepare_coloring_ms,prepare_owner_partition_ms,assembly_zero_ms,assembly_generate_ms,"
        << "assembly_numeric_ms,assembly_merge_ms,assembly_sort_ms,assembly_reduce_ms,status,skip_reason,"
        << "diagnostics,platform,omp_proc_bind,omp_places,omp_dynamic\n";
}

void write_csv_record(std::ofstream& out,
                      const Mesh& mesh,
                      const CsrMatrix& csr,
                      const RunRecord& r,
                      KernelType kernel) {
    out << csv_escape(r.case_name) << ','
        << csv_escape(mesh.name) << ','
        << element_type_to_string(mesh.dominant_element_type()) << ','
        << kernel_type_to_string(kernel) << ','
        << mesh.num_nodes() << ','
        << mesh.num_elements() << ','
        << mesh.num_dofs() << ','
        << csr.nnz() << ','
        << r.algorithm << ','
        << r.threads << ','
        << r.effective_threads << ','
        << r.run_count << ','
        << std::setprecision(10)
        << r.stats.preprocess_time_ms << ','
        << r.stats.assembly_time_ms << ','
        << r.stats.total_time_ms << ','
        << r.assembly_mean_ms << ','
        << r.assembly_min_ms << ','
        << r.assembly_max_ms << ','
        << r.assembly_std_ms << ','
        << r.total_mean_ms << ','
        << r.total_min_ms << ','
        << r.total_max_ms << ','
        << r.total_std_ms << ','
        << r.speedup << ','
        << r.efficiency << ','
        << r.preprocess_share << ','
        << r.error.relative_l2 << ','
        << r.error.max_abs << ','
        << r.stats.extra_memory_bytes << ','
        << r.peak_rss_mb << ','
        << r.stats.colors << ','
        << r.stats.prepare_allocate_ms << ','
        << r.stats.prepare_coloring_ms << ','
        << r.stats.prepare_owner_partition_ms << ','
        << r.stats.assembly_zero_ms << ','
        << r.stats.assembly_generate_ms << ','
        << r.stats.assembly_numeric_ms << ','
        << r.stats.assembly_merge_ms << ','
        << r.stats.assembly_sort_ms << ','
        << r.stats.assembly_reduce_ms << ','
        << r.status << ','
        << csv_escape(r.skip_reason) << ','
        << csv_escape(r.message) << ','
        << csv_escape(r.platform) << ','
        << csv_escape(r.omp_proc_bind) << ','
        << csv_escape(r.omp_places) << ','
        << csv_escape(r.omp_dynamic) << '\n';
}

void write_json(const std::string& path, const std::vector<RunRecord>& records, const Mesh& mesh, const CsrMatrix& csr,
                KernelType kernel) {
    if (path.empty()) return;
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write JSON: " + path);
    out << "{\n"
        << "  \"case_name\": \"" << json_escape(records.empty() ? mesh.name : records.front().case_name) << "\",\n"
        << "  \"mesh\": {\n"
        << "    \"name\": \"" << json_escape(mesh.name) << "\",\n"
        << "    \"element_type\": \"" << element_type_to_string(mesh.dominant_element_type()) << "\",\n"
        << "    \"kernel\": \"" << kernel_type_to_string(kernel) << "\",\n"
        << "    \"nodes\": " << mesh.num_nodes() << ",\n"
        << "    \"elements\": " << mesh.num_elements() << ",\n"
        << "    \"dofs\": " << mesh.num_dofs() << ",\n"
        << "    \"nnz\": " << csr.nnz() << "\n"
        << "  },\n"
        << "  \"records\": [\n";
    for (Size i = 0; i < records.size(); ++i) {
        const auto& r = records[i];
        out << "    {\n"
            << "      \"algorithm\": \"" << r.algorithm << "\",\n"
            << "      \"threads\": " << r.threads << ",\n"
            << "      \"effective_threads\": " << r.effective_threads << ",\n"
            << "      \"run_count\": " << r.run_count << ",\n"
            << "      \"status\": \"" << r.status << "\",\n"
            << "      \"skip_reason\": \"" << json_escape(r.skip_reason) << "\",\n"
            << "      \"speedup\": " << r.speedup << ",\n"
            << "      \"efficiency\": " << r.efficiency << ",\n"
            << "      \"preprocess_share\": " << r.preprocess_share << ",\n"
            << "      \"assembly_mean_ms\": " << r.assembly_mean_ms << ",\n"
            << "      \"assembly_min_ms\": " << r.assembly_min_ms << ",\n"
            << "      \"assembly_max_ms\": " << r.assembly_max_ms << ",\n"
            << "      \"assembly_std_ms\": " << r.assembly_std_ms << ",\n"
            << "      \"total_mean_ms\": " << r.total_mean_ms << ",\n"
            << "      \"peak_rss_mb\": " << r.peak_rss_mb << ",\n"
            << "      \"extra_memory_bytes\": " << r.stats.extra_memory_bytes << ",\n"
            << "      \"rel_l2\": " << r.error.relative_l2 << ",\n"
            << "      \"max_abs\": " << r.error.max_abs << ",\n"
            << "      \"diagnostics\": \"" << json_escape(r.message) << "\"\n"
            << "    }" << (i + 1 == records.size() ? "\n" : ",\n");
    }
    out << "  ]\n}\n";
}

void write_summary_md(const std::string& path, const std::vector<RunRecord>& records) {
    if (path.empty()) return;
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write summary markdown: " + path);
    out << "# CPU 并行整体刚度矩阵组装实验摘要\n\n";
    if (!records.empty()) {
        const RunRecord* fastest = nullptr;
        const RunRecord* best_speedup = nullptr;
        const RunRecord* lowest_extra_memory = nullptr;
        for (const auto& record : records) {
            if (record.status != "PASS") continue;
            if (!fastest || record.assembly_mean_ms < fastest->assembly_mean_ms) fastest = &record;
            if (record.algorithm != "cpu_serial" && (!best_speedup || record.speedup > best_speedup->speedup)) {
                best_speedup = &record;
            }
            if (!lowest_extra_memory || record.stats.extra_memory_bytes < lowest_extra_memory->stats.extra_memory_bytes) {
                lowest_extra_memory = &record;
            }
        }
        if (fastest) {
            out << "- 最快单次平均组装：`" << fastest->algorithm << "` @ " << fastest->threads
                << " 线程，`" << std::fixed << std::setprecision(3) << fastest->assembly_mean_ms << " ms`\n";
        }
        if (best_speedup) {
            out << "- 最高加速比：`" << best_speedup->algorithm << "` @ " << best_speedup->threads
                << " 线程，`" << std::fixed << std::setprecision(3) << best_speedup->speedup << "x`\n";
        }
        if (lowest_extra_memory) {
            out << "- 最低额外内存：`" << lowest_extra_memory->algorithm << "`，`"
                << memory_string(lowest_extra_memory->stats.extra_memory_bytes) << "`\n\n";
        }
    }
    out << "| 算法 | 线程 | 平均组装时间 (ms) | 加速比 | 并行效率 | 额外内存 | 状态 |\n";
    out << "| --- | ---: | ---: | ---: | ---: | ---: | --- |\n";
    for (const auto& record : records) {
        out << "| " << record.algorithm
            << " | " << record.threads
            << " | " << std::fixed << std::setprecision(3) << record.assembly_mean_ms
            << " | " << record.speedup
            << " | " << record.efficiency
            << " | " << memory_string(record.stats.extra_memory_bytes)
            << " | " << record.status << " |\n";
    }
}

} // namespace

int main(int argc, char** argv) {
    try {
        const Config cfg = parse_args(argc, argv);
        const auto t_mesh0 = std::chrono::steady_clock::now();
        Mesh mesh = build_mesh(cfg);
        const auto t_mesh1 = std::chrono::steady_clock::now();
        CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
        const auto t_csr1 = std::chrono::steady_clock::now();
        AssemblyPlan plan = build_assembly_plan(mesh, csr);
        const auto t_plan1 = std::chrono::steady_clock::now();

        const double mesh_ms = std::chrono::duration<double, std::milli>(t_mesh1 - t_mesh0).count();
        const double csr_ms = std::chrono::duration<double, std::milli>(t_csr1 - t_mesh1).count();
        const double plan_ms = std::chrono::duration<double, std::milli>(t_plan1 - t_csr1).count();

        std::cout << "============================================================\n";
        std::cout << " CPU 并行整体刚度矩阵组装基准程序\n";
        std::cout << " CPU Parallel Stiffness Assembly Benchmark\n";
        std::cout << "============================================================\n";
        std::cout << mesh_summary(mesh) << "\n";
        std::cout << "case_name=" << cfg.case_name
                  << ", nnz=" << csr.nnz()
                  << ", csr_memory=" << memory_string(csr.bytes())
                  << ", plan_memory=" << memory_string(plan.bytes()) << "\n";
        std::cout << "kernel=" << kernel_type_to_string(cfg.kernel)
                  << ", platform=" << platform_info_compact()
                  << ", max_threads=" << max_thread_count() << "\n";
        std::cout << "precompute: mesh=" << mesh_ms << " ms, csr=" << csr_ms
                  << " ms, scatter_plan=" << plan_ms << " ms\n\n";

        const CsrMatrix* ref_ptr = nullptr;
        CsrMatrix reference;
        RunRecord baseline = run_one(AlgorithmType::CpuSerial, 1, cfg, mesh, csr, plan, nullptr, 1.0);
        if (baseline.status != "PASS") {
            throw std::runtime_error("Serial baseline failed: " + baseline.message);
        }
        {
            AssemblyOptions options;
            options.threads = 1;
            options.kernel = cfg.kernel;
            options.young_modulus = cfg.young;
            options.poisson_ratio = cfg.poisson;
            options.max_transient_bytes = cfg.max_transient_bytes;
            auto assembler = AssemblerFactory::create(AlgorithmType::CpuSerial, options);
            assembler->set_problem(mesh, csr, plan);
            assembler->prepare();
            assembler->assemble();
            reference = assembler->get_result();
            baseline.error = compare_values(reference, reference);
            baseline.speedup = 1.0;
            baseline.efficiency = 1.0;
            baseline.preprocess_share =
                baseline.stats.total_time_ms > 0.0 ? baseline.stats.preprocess_time_ms / baseline.stats.total_time_ms : 0.0;
        }
        ref_ptr = cfg.check ? &reference : nullptr;
        const double serial_time_ms = baseline.assembly_mean_ms;

        const auto csv_parent = std::filesystem::path(cfg.csv_path).parent_path();
        if (!csv_parent.empty()) std::filesystem::create_directories(csv_parent);
        std::ofstream csv(cfg.csv_path);
        if (!csv) throw std::runtime_error("Cannot write CSV: " + cfg.csv_path);
        write_csv_header(csv);

        std::vector<RunRecord> records;
        std::cout << std::left << std::setw(24) << "algorithm"
                  << std::right << std::setw(8) << "thr"
                  << std::setw(12) << "eff_thr"
                  << std::setw(14) << "prep_ms"
                  << std::setw(14) << "asm_ms"
                  << std::setw(12) << "speedup"
                  << std::setw(12) << "eff"
                  << std::setw(14) << "rel_l2"
                  << std::setw(10) << "status" << "\n";
        std::cout << std::string(120, '-') << "\n";

        for (int threads : cfg.thread_counts) {
            for (AlgorithmType algo : cfg.algorithms) {
                if (algo == AlgorithmType::CpuSerial && threads != 1) continue;
                RunRecord rec = (algo == AlgorithmType::CpuSerial)
                                    ? baseline
                                    : run_one(algo, threads, cfg, mesh, csr, plan, ref_ptr, serial_time_ms);
                std::cout << std::left << std::setw(24) << rec.algorithm
                          << std::right << std::setw(8) << rec.threads
                          << std::setw(12) << rec.effective_threads
                          << std::setw(14) << std::fixed << std::setprecision(3) << rec.stats.preprocess_time_ms
                          << std::setw(14) << rec.assembly_mean_ms
                          << std::setw(12) << rec.speedup
                          << std::setw(12) << rec.efficiency
                          << std::setw(14) << std::scientific << std::setprecision(2) << rec.error.relative_l2
                          << std::setw(10) << rec.status << "\n";
                if (!rec.message.empty()) {
                    std::cout << "  note: " << rec.message << "\n";
                }
                write_csv_record(csv, mesh, csr, rec, cfg.kernel);
                records.push_back(rec);
            }
        }

        write_json(cfg.json_path, records, mesh, csr, cfg.kernel);
        write_summary_md(cfg.summary_md_path, records);

        std::cout << "\n结果已保存 / Results saved to " << cfg.csv_path << "\n";
        if (!cfg.json_path.empty()) std::cout << "JSON: " << cfg.json_path << "\n";
        if (!cfg.summary_md_path.empty()) std::cout << "Summary: " << cfg.summary_md_path << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
