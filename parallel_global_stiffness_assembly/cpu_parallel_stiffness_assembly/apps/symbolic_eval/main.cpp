#include "assembly/symbolic_numeric_eval.h"
#include "core/platform.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace fem;

namespace {

struct Config {
    std::string mesh_mode = "inp";
    std::string inp_path = "../../examples/3d-WindTurbineHub.inp";
    std::string case_name;
    ElementType element_type = ElementType::Tet4;
    int nx = 8;
    int ny = 8;
    int nz = 8;
    KernelType kernel = KernelType::PhysicsTet4;
    std::vector<int> assemblies{1, 3, 10, 30};
    std::vector<int> thread_counts{1};
    std::vector<AlgorithmType> numeric_backends{AlgorithmType::CpuAtomic};
    std::vector<std::string> mode_filters;
    std::string csv_path = "symbolic_numeric_eval.csv";
    std::string json_path;
    std::string summary_md_path;
    Size max_transient_bytes = static_cast<Size>(8ull * 1024ull * 1024ull * 1024ull);
    Real young = constants::DEFAULT_YOUNG_MODULUS;
    Real poisson = constants::DEFAULT_POISSON_RATIO;
};

struct OutputRecord {
    std::string case_name;
    std::string mode;
    std::string strategy_label;
    std::string numeric_backend;
    int threads = 1;
    int assemblies_per_symbolic = 1;
    int symbolic_builds = 0;
    double symbolic_csr_ms = 0.0;
    double symbolic_plan_ms = 0.0;
    double symbolic_total_ms = 0.0;
    Size symbolic_temporary_bytes = 0;
    double numeric_ms = 0.0;
    double direct_generate_ms = 0.0;
    double direct_bucket_merge_ms = 0.0;
    double direct_sort_reduce_ms = 0.0;
    double amortized_total_ms = 0.0;
    double symbolic_gain_vs_direct = 0.0;
    Size csr_bytes = 0;
    Size plan_bytes = 0;
    Size symbolic_persistent_bytes = 0;
    Size common_output_matrix_bytes = 0;
    Size numeric_backend_extra_bytes = 0;
    Size direct_transient_bytes = 0;
    Size estimated_peak_bytes = 0;
    long long delta_vs_serial_symbolic_serial_numeric_bytes = 0;
    double isolated_peak_rss_mb = 0.0;
    MatrixError error;
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

std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
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

std::vector<int> parse_assemblies(const std::string& text) {
    std::vector<int> out;
    for (const auto& token : split(text, ',')) {
        const int value = std::stoi(token);
        if (value <= 0) throw std::invalid_argument("--assemblies-list values must be positive");
        out.push_back(value);
    }
    if (out.empty()) throw std::invalid_argument("--assemblies-list cannot be empty");
    return out;
}

std::vector<int> parse_positive_int_list(const std::string& text, const std::string& option_name) {
    std::vector<int> out;
    for (const auto& token : split(text, ',')) {
        const int value = std::stoi(token);
        if (value <= 0) throw std::invalid_argument(option_name + " values must be positive");
        out.push_back(value);
    }
    if (out.empty()) throw std::invalid_argument(option_name + " cannot be empty");
    return out;
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

std::vector<AlgorithmType> parse_algorithms(const std::string& text) {
    std::vector<AlgorithmType> out;
    for (const auto& token : split(text, ',')) {
        out.push_back(parse_algorithm_type(token));
    }
    if (out.empty()) throw std::invalid_argument("backend list cannot be empty");
    return out;
}

std::vector<std::string> parse_modes(const std::string& text) {
    std::vector<std::string> out;
    for (const auto& token : split(text, ',')) {
        out.push_back(token);
    }
    if (out.empty()) throw std::invalid_argument("--mode-list cannot be empty");
    return out;
}

bool should_run_mode(const Config& cfg, const std::string& mode) {
    if (cfg.mode_filters.empty()) return true;
    return std::find(cfg.mode_filters.begin(), cfg.mode_filters.end(), mode) != cfg.mode_filters.end();
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

void print_usage(const char* exe) {
    std::cout
        << "符号/数值组装评估程序 / Symbolic-Numeric Assembly Evaluator\n\n"
        << "Usage:\n  " << exe << " [options]\n\n"
        << "Options:\n"
        << "  --mesh cube|inp                  default inp\n"
        << "  --inp PATH                       Abaqus .inp path for --mesh inp\n"
        << "  --case-name NAME                 result case name\n"
        << "  --element tet4|hex8              cube element type, default tet4\n"
        << "  --nx N --ny N --nz N             cube resolution, default 8 8 8\n"
        << "  --kernel simplified|physics_tet4 default physics_tet4\n"
        << "  --assemblies-list 1,3,10,30      assemblies per symbolic build\n"
        << "  --threads-list 1,2,4,8           parallel symbolic/direct thread list\n"
        << "  --threads-range 1:14[:step]      parallel symbolic/direct thread range\n"
        << "  --threads-all                    parallel symbolic/direct 1..physical_cores\n"
        << "  --backend-list atomic,lock_guard parallel symbolic numeric backends\n"
        << "  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,...\n"
        << "  --max-memory-gb X                direct no-symbolic transient memory limit\n"
        << "  --csv PATH --json PATH --summary-md PATH\n"
        << "  --young X --poisson X\n"
        << "  --help\n";
}

Config parse_args(int argc, char** argv) {
    Config cfg;
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
        else if (arg == "--inp") cfg.inp_path = require_value(arg);
        else if (arg == "--case-name") cfg.case_name = require_value(arg);
        else if (arg == "--element") cfg.element_type = parse_element_type(require_value(arg));
        else if (arg == "--nx") cfg.nx = std::stoi(require_value(arg));
        else if (arg == "--ny") cfg.ny = std::stoi(require_value(arg));
        else if (arg == "--nz") cfg.nz = std::stoi(require_value(arg));
        else if (arg == "--kernel") cfg.kernel = parse_kernel_type(require_value(arg));
        else if (arg == "--assemblies-list") cfg.assemblies = parse_assemblies(require_value(arg));
        else if (arg == "--threads-list") cfg.thread_counts = parse_positive_int_list(require_value(arg), arg);
        else if (arg == "--threads-range") cfg.thread_counts = parse_threads_range(require_value(arg));
        else if (arg == "--threads-all") {
            const auto cpu = get_cpu_topology_info();
            cfg.thread_counts.clear();
            for (int t = 1; t <= std::max(1, cpu.physical_cores); ++t) cfg.thread_counts.push_back(t);
        }
        else if (arg == "--backend-list" || arg == "--backends") cfg.numeric_backends = parse_algorithms(require_value(arg));
        else if (arg == "--mode-list" || arg == "--modes") cfg.mode_filters = parse_modes(require_value(arg));
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
    if (cfg.case_name.empty()) {
        cfg.case_name = to_lower(cfg.mesh_mode) == "inp"
                            ? std::filesystem::path(cfg.inp_path).stem().string()
                            : "cube_" + to_lower(element_type_to_string(cfg.element_type)) + "_" +
                                  std::to_string(cfg.nx) + "x" + std::to_string(cfg.ny) + "x" +
                                  std::to_string(cfg.nz);
    }
    return cfg;
}

Mesh build_mesh(const Config& cfg) {
    if (to_lower(cfg.mesh_mode) == "cube") {
        Mesh mesh = cfg.element_type == ElementType::Tet4
                        ? Mesh::make_cube_tet4(cfg.nx, cfg.ny, cfg.nz)
                        : Mesh::make_cube_hex8(cfg.nx, cfg.ny, cfg.nz);
        mesh.name = cfg.case_name;
        return mesh;
    }
    if (to_lower(cfg.mesh_mode) == "inp") {
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

AssemblyOptions make_options(const Config& cfg) {
    AssemblyOptions options;
    options.threads = 1;
    options.kernel = cfg.kernel;
    options.max_transient_bytes = cfg.max_transient_bytes;
    options.young_modulus = cfg.young;
    options.poisson_ratio = cfg.poisson;
    return options;
}

OutputRecord to_output(const Config& cfg,
                       const SymbolicEvaluationRecord& record,
                       const CsrMatrix& reference,
                       double direct_amortized_ms) {
    OutputRecord out;
    out.case_name = cfg.case_name;
    out.mode = record.mode;
    out.strategy_label = record.strategy_label;
    out.numeric_backend = record.numeric_backend;
    out.threads = record.threads;
    out.assemblies_per_symbolic = record.assemblies_per_symbolic;
    out.symbolic_builds = record.symbolic_builds;
    out.symbolic_csr_ms = record.symbolic_csr_ms;
    out.symbolic_plan_ms = record.symbolic_plan_ms;
    out.symbolic_total_ms = record.symbolic_total_ms;
    out.symbolic_temporary_bytes = record.symbolic_temporary_bytes;
    out.numeric_ms = record.numeric_ms;
    out.direct_generate_ms = record.direct_generate_ms;
    out.direct_bucket_merge_ms = record.direct_bucket_merge_ms;
    out.direct_sort_reduce_ms = record.direct_sort_reduce_ms;
    out.amortized_total_ms = record.amortized_total_ms;
    out.symbolic_gain_vs_direct = record.amortized_total_ms > 0.0
                                      ? direct_amortized_ms / record.amortized_total_ms
                                      : 0.0;
    out.csr_bytes = record.csr_bytes;
    out.plan_bytes = record.plan_bytes;
    out.symbolic_persistent_bytes = record.symbolic_persistent_bytes;
    out.common_output_matrix_bytes = record.common_output_matrix_bytes;
    out.numeric_backend_extra_bytes = record.numeric_backend_extra_bytes;
    out.direct_transient_bytes = record.direct_transient_bytes;
    out.estimated_peak_bytes = record.estimated_peak_bytes;
    out.delta_vs_serial_symbolic_serial_numeric_bytes = record.delta_vs_serial_symbolic_serial_numeric_bytes;
    out.isolated_peak_rss_mb = record.isolated_peak_rss_mb;
    out.error = compare_values(reference, record.matrix);
    return out;
}

void annotate_memory_deltas(std::vector<OutputRecord>& records) {
    for (auto& row : records) {
        Size baseline = 0;
        bool found = false;
        for (const auto& candidate : records) {
            if (candidate.strategy_label == "serial_symbolic_serial_numeric" &&
                candidate.assemblies_per_symbolic == row.assemblies_per_symbolic) {
                baseline = candidate.estimated_peak_bytes;
                found = true;
                break;
            }
        }
        if (!found) {
            row.delta_vs_serial_symbolic_serial_numeric_bytes = 0;
            continue;
        }
        const auto current = static_cast<long long>(std::min<Size>(
            row.estimated_peak_bytes, static_cast<Size>(std::numeric_limits<long long>::max())));
        const auto base = static_cast<long long>(std::min<Size>(
            baseline, static_cast<Size>(std::numeric_limits<long long>::max())));
        row.delta_vs_serial_symbolic_serial_numeric_bytes = current - base;
    }
}

void ensure_parent_dir(const std::string& path) {
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
}

void write_csv(const std::string& path,
               const std::vector<OutputRecord>& records,
               const Mesh& mesh,
               const Config& cfg) {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write CSV: " + path);
    const auto cpu = get_cpu_topology_info();
    out << "case_name,mesh,element_type,kernel,nodes,elements,dofs,mode,numeric_backend,threads,"
        << "strategy_label,assemblies_per_symbolic,symbolic_builds,symbolic_csr_ms,symbolic_plan_ms,"
        << "symbolic_total_ms,symbolic_temporary_bytes,numeric_ms,direct_generate_ms,"
        << "direct_bucket_merge_ms,direct_sort_reduce_ms,amortized_total_ms,symbolic_gain_vs_direct,"
        << "rel_l2,max_abs,csr_bytes,plan_bytes,symbolic_persistent_bytes,"
        << "common_output_matrix_bytes,numeric_backend_extra_bytes,direct_transient_bytes,"
        << "estimated_peak_bytes,delta_vs_serial_symbolic_serial_numeric_bytes,isolated_peak_rss_mb,"
        << "platform,cpu_model,"
        << "physical_cores,logical_cores\n";
    for (const auto& r : records) {
        out << csv_escape(r.case_name) << ','
            << csv_escape(mesh.name) << ','
            << element_type_to_string(mesh.dominant_element_type()) << ','
            << kernel_type_to_string(cfg.kernel) << ','
            << mesh.num_nodes() << ','
            << mesh.num_elements() << ','
            << mesh.num_dofs() << ','
            << r.mode << ','
            << r.numeric_backend << ','
            << r.threads << ','
            << r.strategy_label << ','
            << r.assemblies_per_symbolic << ','
            << r.symbolic_builds << ','
            << std::setprecision(10)
            << r.symbolic_csr_ms << ','
            << r.symbolic_plan_ms << ','
            << r.symbolic_total_ms << ','
            << r.symbolic_temporary_bytes << ','
            << r.numeric_ms << ','
            << r.direct_generate_ms << ','
            << r.direct_bucket_merge_ms << ','
            << r.direct_sort_reduce_ms << ','
            << r.amortized_total_ms << ','
            << r.symbolic_gain_vs_direct << ','
            << r.error.relative_l2 << ','
            << r.error.max_abs << ','
            << r.csr_bytes << ','
            << r.plan_bytes << ','
            << r.symbolic_persistent_bytes << ','
            << r.common_output_matrix_bytes << ','
            << r.numeric_backend_extra_bytes << ','
            << r.direct_transient_bytes << ','
            << r.estimated_peak_bytes << ','
            << r.delta_vs_serial_symbolic_serial_numeric_bytes << ','
            << r.isolated_peak_rss_mb << ','
            << csv_escape(platform_info_compact()) << ','
            << csv_escape(cpu.model) << ','
            << cpu.physical_cores << ','
            << cpu.logical_cores << '\n';
    }
}

void write_json(const std::string& path,
                const std::vector<OutputRecord>& records,
                const Mesh& mesh,
                const Config& cfg) {
    if (path.empty()) return;
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write JSON: " + path);
    const auto cpu = get_cpu_topology_info();
    out << "{\n"
        << "  \"case_name\": \"" << json_escape(cfg.case_name) << "\",\n"
        << "  \"mesh\": {\n"
        << "    \"name\": \"" << json_escape(mesh.name) << "\",\n"
        << "    \"element_type\": \"" << element_type_to_string(mesh.dominant_element_type()) << "\",\n"
        << "    \"kernel\": \"" << kernel_type_to_string(cfg.kernel) << "\",\n"
        << "    \"nodes\": " << mesh.num_nodes() << ",\n"
        << "    \"elements\": " << mesh.num_elements() << ",\n"
        << "    \"dofs\": " << mesh.num_dofs() << "\n"
        << "  },\n"
        << "  \"platform\": {\n"
        << "    \"compact\": \"" << json_escape(platform_info_compact()) << "\",\n"
        << "    \"cpu_model\": \"" << json_escape(cpu.model) << "\",\n"
        << "    \"physical_cores\": " << cpu.physical_cores << ",\n"
        << "    \"logical_cores\": " << cpu.logical_cores << "\n"
        << "  },\n"
        << "  \"records\": [\n";
    for (Size i = 0; i < records.size(); ++i) {
        const auto& r = records[i];
        out << "    {\n"
            << "      \"mode\": \"" << r.mode << "\",\n"
            << "      \"strategy_label\": \"" << r.strategy_label << "\",\n"
            << "      \"numeric_backend\": \"" << r.numeric_backend << "\",\n"
            << "      \"threads\": " << r.threads << ",\n"
            << "      \"assemblies_per_symbolic\": " << r.assemblies_per_symbolic << ",\n"
            << "      \"symbolic_builds\": " << r.symbolic_builds << ",\n"
            << "      \"symbolic_csr_ms\": " << r.symbolic_csr_ms << ",\n"
            << "      \"symbolic_plan_ms\": " << r.symbolic_plan_ms << ",\n"
            << "      \"symbolic_total_ms\": " << r.symbolic_total_ms << ",\n"
            << "      \"symbolic_temporary_bytes\": " << r.symbolic_temporary_bytes << ",\n"
            << "      \"numeric_ms\": " << r.numeric_ms << ",\n"
            << "      \"direct_generate_ms\": " << r.direct_generate_ms << ",\n"
            << "      \"direct_bucket_merge_ms\": " << r.direct_bucket_merge_ms << ",\n"
            << "      \"direct_sort_reduce_ms\": " << r.direct_sort_reduce_ms << ",\n"
            << "      \"amortized_total_ms\": " << r.amortized_total_ms << ",\n"
            << "      \"symbolic_gain_vs_direct\": " << r.symbolic_gain_vs_direct << ",\n"
            << "      \"csr_bytes\": " << r.csr_bytes << ",\n"
            << "      \"plan_bytes\": " << r.plan_bytes << ",\n"
            << "      \"symbolic_persistent_bytes\": " << r.symbolic_persistent_bytes << ",\n"
            << "      \"common_output_matrix_bytes\": " << r.common_output_matrix_bytes << ",\n"
            << "      \"numeric_backend_extra_bytes\": " << r.numeric_backend_extra_bytes << ",\n"
            << "      \"direct_transient_bytes\": " << r.direct_transient_bytes << ",\n"
            << "      \"estimated_peak_bytes\": " << r.estimated_peak_bytes << ",\n"
            << "      \"delta_vs_serial_symbolic_serial_numeric_bytes\": " << r.delta_vs_serial_symbolic_serial_numeric_bytes << ",\n"
            << "      \"isolated_peak_rss_mb\": " << r.isolated_peak_rss_mb << ",\n"
            << "      \"rel_l2\": " << r.error.relative_l2 << ",\n"
            << "      \"max_abs\": " << r.error.max_abs << "\n"
            << "    }" << (i + 1 == records.size() ? "\n" : ",\n");
    }
    out << "  ]\n}\n";
}

void write_summary_md(const std::string& path,
                      const std::vector<OutputRecord>& records,
                      const Mesh& mesh,
                      const Config& cfg) {
    if (path.empty()) return;
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write summary markdown: " + path);
    const auto cpu = get_cpu_topology_info();
    auto find_record = [&](const std::string& mode, int assemblies) -> const OutputRecord* {
        for (const auto& record : records) {
            if (record.mode == mode && record.assemblies_per_symbolic == assemblies) return &record;
        }
        return nullptr;
    };

    out << "# 符号/数值组装效率评估报告\n\n"
        << "## 固定术语\n\n"
        << "- 符号组装：拓扑、DOF、CSR 稀疏结构和 scatter 写入位置预计算，不计算 `Ke`。\n"
        << "- 数值组装/物理组装：计算 `physics_tet4` 单元刚度 `Ke`，并填充全局矩阵。\n"
        << "- 无符号直接组装：不复用 CSR pattern 或 scatter plan，每次直接生成 `(row,col,value)` 贡献并排序归并。\n\n"
        << "## Mentor 示例 vs 当前 C++ 实现\n\n"
        << "| Mentor MATLAB 示例 | 当前 C++ 主线 | 采用策略 |\n"
        << "| --- | --- | --- |\n"
        << "| `build_symbolic_pattern` 生成稀疏模式 | `CsrMatrix::build_sparsity` 生成 CSR pattern | 保留 C++ 实现，文档显式命名为符号组装 |\n"
        << "| `cellDofsCache` 缓存单元 DOF | `AssemblyPlan::dofs` 缓存单元 DOF | 直接对应 |\n"
        << "| `allocate_global_matrix` 预分配稀疏矩阵 | `CsrMatrix` 结构复用并清零 values | 直接对应 |\n"
        << "| `assemble_numeric` 计算 `Ke` 并块插入 | `cpu_serial` 等 assembler 计算 `Ke` 并按 scatter 写入 | C++ 额外缓存 CSR scatter 位置，数值阶段更工程化 |\n"
        << "| PETSc-style `section/closure` 教学结构 | 当前节点 DOF 直接映射 | 首阶段不重构，作为未来高阶 DOF 扩展参考 |\n\n"
        << "## 实验设置\n\n"
        << "- case: `" << cfg.case_name << "`\n"
        << "- mesh: nodes=" << mesh.num_nodes() << ", elements=" << mesh.num_elements()
        << ", dofs=" << mesh.num_dofs() << "\n"
        << "- kernel: `" << kernel_type_to_string(cfg.kernel) << "`\n"
        << "- platform: `" << platform_info_compact() << "`\n"
        << "- CPU: `" << cpu.model << "`, physical_cores=" << cpu.physical_cores
        << ", logical_cores=" << cpu.logical_cores << "\n\n"
        << "## 主结论\n\n"
        << "本报告当前主线回答两个问题：第一，在已经采用符号结构的前提下，哪个数值后端的速度/内存权衡最合理；第二，在同一数值后端下，并行符号构建相比串行符号构建是否值得。"
        << "`direct/no-symbolic` 只作为背景基线，用来说明不复用 CSR/scatter plan 的 transient contribution buffer 压力。\n\n"
        << "统一内存口径采用 lifecycle + baseline delta：`symbolic_persistent_bytes = csr_bytes + plan_bytes`，"
        << "`numeric_backend_extra_bytes` 记录数值后端额外结构，`estimated_peak_bytes` 按生命周期峰值估算，"
        << "`delta_vs_serial_symbolic_serial_numeric_bytes` 相对 `serial_symbolic_serial_numeric` 解释额外存储压力。"
        << "`isolated_peak_rss_mb` 由隔离 runner 填充；直接运行本程序时该列为 `0`。\n\n";

    for (const auto& r : records) {
        if (r.mode != "symbolic_reuse_serial") continue;
        const auto* direct = find_record("direct_no_symbolic_serial", r.assemblies_per_symbolic);
        if (!direct) continue;
        out << "- 组装 " << r.assemblies_per_symbolic << " 次：符号复用摊销总耗时 `"
            << std::fixed << std::setprecision(3) << r.amortized_total_ms
            << " ms`，无符号直接组装 `"
            << direct->amortized_total_ms << " ms`，相对收益 `"
            << r.symbolic_gain_vs_direct << "x`。\n";
    }

    out << "\n## 背景基线：符号复用 vs 无符号直接组装\n\n"
        << "这一节保留 `direct/no-symbolic` 作为 sanity baseline。`assemblies=1` 表示单次组装总成本；`assemblies>1` 表示同一稀疏结构下多次物理组装时，符号组装成本被摊销后的总成本。\n\n"
        << "| 组装次数 | 符号复用：符号总耗时 ms | 符号复用：数值 ms/次 | 符号复用：摊销总耗时 ms | 无符号直接：生成 ms/次 | 无符号直接：排序归并 ms/次 | 无符号直接：摊销总耗时 ms | 符号复用收益 | rel_l2 |\n"
        << "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n";
    for (const auto& r : records) {
        if (r.mode != "symbolic_reuse_serial") continue;
        const auto* direct = find_record("direct_no_symbolic_serial", r.assemblies_per_symbolic);
        if (!direct) continue;
        out << "| " << r.assemblies_per_symbolic
            << " | " << std::fixed << std::setprecision(3) << r.symbolic_total_ms
            << " | " << r.numeric_ms
            << " | " << r.amortized_total_ms
            << " | " << direct->direct_generate_ms
            << " | " << direct->direct_sort_reduce_ms
            << " | " << direct->amortized_total_ms
            << " | " << r.symbolic_gain_vs_direct
            << " | " << std::scientific << std::setprecision(3) << direct->error.relative_l2
            << " |\n";
    }

    out << "\n## 符号阶段并行化与数值后端选择\n\n"
        << "这一节是当前主决策表：`serial_symbolic_parallel_numeric` 固定串行 CSR/scatter plan 构建，只改变数值后端；"
        << "`parallel_symbolic_reuse` 使用并行 CSR/scatter plan 构建，并使用同一数值后端。"
        << "比较同一 backend、同一 threads 下两行，即可判断符号阶段是否也值得并行化。\n\n"
        << "| strategy | mode | backend | threads | assemblies | symbolic total ms | temporary bytes | numeric ms | amortized total ms | estimated peak bytes | delta bytes | rel_l2 |\n"
        << "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n";
    for (const auto& r : records) {
        if (r.mode != "parallel_symbolic_reuse" &&
            r.mode != "serial_symbolic_parallel_numeric" &&
            r.mode != "symbolic_reuse_serial") continue;
        out << "| `" << r.strategy_label
            << "` | `" << r.mode
            << "` | `" << r.numeric_backend
            << "` | " << r.threads
            << " | " << r.assemblies_per_symbolic
            << " | " << std::fixed << std::setprecision(3) << r.symbolic_total_ms
            << " | " << r.symbolic_temporary_bytes
            << " | " << r.numeric_ms
            << " | " << r.amortized_total_ms
            << " | " << r.estimated_peak_bytes
            << " | " << r.delta_vs_serial_symbolic_serial_numeric_bytes
            << " | " << std::scientific << std::setprecision(3) << r.error.relative_l2
            << " |\n";
    }

    out << "\n## 内存生命周期字段\n\n"
        << "| strategy | mode | backend | threads | symbolic persistent bytes | common output matrix bytes | backend extra bytes | direct transient bytes | isolated peak RSS MB |\n"
        << "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n";
    for (const auto& r : records) {
        out << "| `" << r.strategy_label
            << "` | `" << r.mode
            << "` | `" << r.numeric_backend
            << "` | " << r.threads
            << " | " << r.symbolic_persistent_bytes
            << " | " << r.common_output_matrix_bytes
            << " | " << r.numeric_backend_extra_bytes
            << " | " << r.direct_transient_bytes
            << " | " << std::fixed << std::setprecision(3) << r.isolated_peak_rss_mb
            << " |\n";
    }

    out << "\n## 控制实验：每次重建符号结构\n\n"
        << "### 为什么做这个控制实验\n\n"
        << "`symbolic_rebuild_serial` 不代表本项目推荐的使用场景，也不是 mentor 问题中的主评估对象。它用于隔离变量：如果同样采用当前 C++ 的两阶段路线，但故意不复用符号结果、每次都重建 CSR pattern 和 scatter plan，那么总成本会是多少。这个对照可以证明主线收益主要来自“符号结果复用”，而不是仅仅来自“代码路径叫做符号组装”。\n\n"
        << "### 做了什么\n\n"
        << "对每个 `assemblies_per_symbolic` 取值，`symbolic_rebuild_serial` 都重复执行完整的 `CsrMatrix::build_sparsity()` 和 `build_assembly_plan()`，随后执行一次串行 `physics_tet4` 数值组装。也就是说，组装 10 次时会重建 10 次符号结构；组装 30 次时会重建 30 次符号结构。\n\n"
        << "### 怎么做的\n\n"
        << "实现上它复用同一套符号构建函数和同一套串行数值组装函数，只改变生命周期：`symbolic_reuse_serial` 是一次构建、多次组装；`symbolic_rebuild_serial` 是每轮构建一次、组装一次。两者的数值结果都和符号复用参考矩阵比较，`rel_l2` 用于确认控制实验没有改变数学结果。\n\n"
        << "### 如何解释\n\n"
        << "如果 `symbolic_rebuild_serial` 明显慢于 `symbolic_reuse_serial`，说明多次组装场景下必须复用符号结构；如果它仍快于无符号直接组装，说明即便不复用，预先构建 CSR/scatter 也比直接贡献排序归并更高效。但项目主结论仍应以 `symbolic_reuse_serial` 为准。\n\n"
        << "| 组装次数 | 符号构建次数 | 平均 CSR 构建 ms | 平均 scatter plan ms | 平均符号总耗时 ms | 平均数值 ms/次 | 摊销总耗时 ms | 相对无符号收益 | rel_l2 |\n"
        << "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n";
    for (const auto& r : records) {
        if (r.mode != "symbolic_rebuild_serial") continue;
        out << "| " << r.assemblies_per_symbolic
            << " | " << r.symbolic_builds
            << " | " << std::fixed << std::setprecision(3) << r.symbolic_csr_ms
            << " | " << r.symbolic_plan_ms
            << " | " << r.symbolic_total_ms
            << " | " << r.numeric_ms
            << " | " << r.amortized_total_ms
            << " | " << r.symbolic_gain_vs_direct
            << " | " << std::scientific << std::setprecision(3) << r.error.relative_l2
            << " |\n";
    }
}

std::vector<OutputRecord> run_evaluation(const Config& cfg, const Mesh& mesh) {
    const AssemblyOptions options = make_options(cfg);
    CsrMatrix reference_matrix;
    {
        const auto reference_artifacts = build_symbolic_artifacts(mesh);
        auto reference_once = assemble_symbolic_serial_once(mesh, reference_artifacts, options);
        reference_matrix = std::move(reference_once.matrix);
    }

    std::vector<OutputRecord> out;
    for (int assemblies : cfg.assemblies) {
        std::cout << "[eval] assemblies_per_symbolic=" << assemblies << "\n";
        std::optional<double> direct_ms;
        if (should_run_mode(cfg, "direct_no_symbolic_serial")) {
            auto direct = evaluate_direct_no_symbolic_serial(mesh, options, assemblies);
            direct_ms = direct.amortized_total_ms;
            out.push_back(to_output(cfg, direct, reference_matrix, direct.amortized_total_ms));
        }
        if (should_run_mode(cfg, "symbolic_reuse_serial")) {
            auto reuse = evaluate_symbolic_reuse_serial(mesh, options, assemblies);
            out.push_back(to_output(cfg, reuse, reference_matrix, direct_ms.value_or(0.0)));
        }
        if (should_run_mode(cfg, "symbolic_rebuild_serial")) {
            auto rebuild = evaluate_symbolic_rebuild_serial(mesh, options, assemblies);
            out.push_back(to_output(cfg, rebuild, reference_matrix, direct_ms.value_or(0.0)));
        }

        for (int threads : cfg.thread_counts) {
            AssemblyOptions parallel_options = options;
            parallel_options.threads = threads;
            std::optional<double> direct_parallel_ms;
            if (should_run_mode(cfg, "direct_no_symbolic_parallel")) {
                auto direct_parallel = evaluate_direct_no_symbolic_parallel(mesh, parallel_options, assemblies);
                direct_parallel_ms = direct_parallel.amortized_total_ms;
                out.push_back(to_output(cfg, direct_parallel, reference_matrix, direct_parallel.amortized_total_ms));
            }
            for (AlgorithmType backend : cfg.numeric_backends) {
                if (should_run_mode(cfg, "serial_symbolic_parallel_numeric")) {
                    auto serial_symbolic_parallel =
                        evaluate_serial_symbolic_parallel_numeric(mesh, parallel_options, assemblies, backend);
                    out.push_back(to_output(cfg,
                                            serial_symbolic_parallel,
                                            reference_matrix,
                                            direct_parallel_ms.value_or(0.0)));
                }
                if (should_run_mode(cfg, "parallel_symbolic_reuse")) {
                    auto parallel_reuse = evaluate_parallel_symbolic_reuse(mesh, parallel_options, assemblies, backend);
                    out.push_back(to_output(cfg,
                                            parallel_reuse,
                                            reference_matrix,
                                            direct_parallel_ms.value_or(0.0)));
                }
            }
        }
    }
    annotate_memory_deltas(out);
    return out;
}

} // namespace

int main(int argc, char** argv) {
    try {
        const Config cfg = parse_args(argc, argv);
        Mesh mesh = build_mesh(cfg);

        std::cout << "============================================================\n"
                  << " 符号/数值组装效率评估程序\n"
                  << " Symbolic-Numeric Assembly Evaluator\n"
                  << "============================================================\n"
                  << mesh_summary(mesh) << "\n"
                  << "kernel=" << kernel_type_to_string(cfg.kernel)
                  << ", assemblies=";
        for (Size i = 0; i < cfg.assemblies.size(); ++i) {
            std::cout << (i == 0 ? "" : ",") << cfg.assemblies[i];
        }
        std::cout << "\n";

        auto records = run_evaluation(cfg, mesh);
        write_csv(cfg.csv_path, records, mesh, cfg);
        write_json(cfg.json_path, records, mesh, cfg);
        write_summary_md(cfg.summary_md_path, records, mesh, cfg);

        std::cout << "CSV: " << cfg.csv_path << "\n";
        if (!cfg.json_path.empty()) std::cout << "JSON: " << cfg.json_path << "\n";
        if (!cfg.summary_md_path.empty()) std::cout << "Summary: " << cfg.summary_md_path << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
