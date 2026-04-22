#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/platform.h"

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace fem;

namespace {

struct Config {
    std::string mesh_mode = "cube";
    std::string inp_path;
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
    std::string csv_path = "benchmark_results_cpu.csv";
    Size max_transient_bytes = static_cast<Size>(8ull * 1024ull * 1024ull * 1024ull);
    Real young = constants::DEFAULT_YOUNG_MODULUS;
    Real poisson = constants::DEFAULT_POISSON_RATIO;
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

void print_usage(const char* exe) {
    std::cout << "CPU Parallel Global Stiffness Assembly Benchmark\n\n"
              << "Usage:\n  " << exe << " [options]\n\n"
              << "Options:\n"
              << "  --mesh cube|inp                  Mesh source, default cube\n"
              << "  --element tet4|hex8              Cube element type, default tet4\n"
              << "  --nx N --ny N --nz N              Cube resolution, default 6 6 6\n"
              << "  --inp PATH                       Abaqus .inp path for --mesh inp\n"
              << "  --algo LIST                      serial,atomic,private_csr,coo_sort_reduce,coloring,row_owner,all\n"
              << "  --threads N                      Single thread count\n"
              << "  --threads-list 1,2,4,8           Multiple thread counts\n"
              << "  --kernel simplified|physics_tet4 Local stiffness kernel\n"
              << "  --warmup N --repeat N            Repetitions, default 0/1\n"
              << "  --check                          Compare every algorithm to serial baseline\n"
              << "  --csv PATH                       CSV output path\n"
              << "  --max-memory-gb X                Transient memory guard, default 8\n"
              << "  --help\n";
}

std::vector<AlgorithmType> parse_algorithms(const std::string& text) {
    if (to_lower_ascii(text) == "all") return AssemblerFactory::get_available_algorithms();
    std::vector<AlgorithmType> out;
    for (const auto& token : split(text, ',')) out.push_back(parse_algorithm_type(token));
    return out;
}

std::vector<int> parse_threads(const std::string& text) {
    std::vector<int> out;
    for (const auto& token : split(text, ',')) out.push_back(std::stoi(token));
    return out;
}

Config parse_args(int argc, char** argv) {
    Config cfg;
    cfg.algorithms = {AlgorithmType::CpuSerial, AlgorithmType::CpuAtomic, AlgorithmType::CpuGraphColoring};
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
        else if (arg == "--algo" || arg == "--algorithms") cfg.algorithms = parse_algorithms(require_value(arg));
        else if (arg == "--threads") cfg.thread_counts = {std::stoi(require_value(arg))};
        else if (arg == "--threads-list") cfg.thread_counts = parse_threads(require_value(arg));
        else if (arg == "--kernel") cfg.kernel = parse_kernel_type(require_value(arg));
        else if (arg == "--warmup") cfg.warmup = std::stoi(require_value(arg));
        else if (arg == "--repeat") cfg.repeat = std::max(1, std::stoi(require_value(arg)));
        else if (arg == "--check") cfg.check = true;
        else if (arg == "--csv") cfg.csv_path = require_value(arg);
        else if (arg == "--max-memory-gb") {
            const double gb = std::stod(require_value(arg));
            cfg.max_transient_bytes = static_cast<Size>(gb * 1024.0 * 1024.0 * 1024.0);
        } else if (arg == "--young") cfg.young = std::stod(require_value(arg));
        else if (arg == "--poisson") cfg.poisson = std::stod(require_value(arg));
        else throw std::invalid_argument("Unknown argument: " + arg);
    }
    return cfg;
}

Mesh build_mesh(const Config& cfg) {
    if (to_lower_ascii(cfg.mesh_mode) == "cube") {
        if (cfg.element_type == ElementType::Tet4) return Mesh::make_cube_tet4(cfg.nx, cfg.ny, cfg.nz);
        return Mesh::make_cube_hex8(cfg.nx, cfg.ny, cfg.nz);
    }
    if (to_lower_ascii(cfg.mesh_mode) == "inp") {
        if (cfg.inp_path.empty()) throw std::invalid_argument("--mesh inp requires --inp PATH");
        return Mesh::load_from_inp(cfg.inp_path);
    }
    throw std::invalid_argument("Unsupported mesh mode: " + cfg.mesh_mode);
}

struct RunRecord {
    std::string algorithm;
    int threads = 1;
    std::string status = "PASS";
    AssemblyStats stats;
    MatrixError error;
    double speedup = 0.0;
    std::string message;
};

RunRecord run_one(AlgorithmType algo,
                  int threads,
                  const Config& cfg,
                  const Mesh& mesh,
                  const CsrMatrix& csr,
                  const AssemblyPlan& plan,
                  const CsrMatrix* reference,
                  double serial_time_ms) {
    RunRecord record;
    record.algorithm = algorithm_to_string(algo);
    record.threads = threads;
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
        auto stats = assembler->get_stats();
        if (stats.preprocess_time_ms == 0.0) {
            stats.preprocess_time_ms = std::chrono::duration<double, std::milli>(prep1 - prep0).count();
        }

        for (int i = 0; i < cfg.warmup; ++i) assembler->assemble();
        double total = 0.0;
        double best = std::numeric_limits<double>::infinity();
        for (int i = 0; i < cfg.repeat; ++i) {
            assembler->assemble();
            auto s = assembler->get_stats();
            total += s.assembly_time_ms;
            best = std::min(best, s.assembly_time_ms);
        }
        stats = assembler->get_stats();
        stats.assembly_time_ms = total / cfg.repeat;
        stats.total_time_ms = stats.preprocess_time_ms + stats.assembly_time_ms;
        if (!stats.diagnostics.empty()) record.message = stats.diagnostics;
        record.stats = stats;
        if (reference) record.error = compare_values(*reference, assembler->get_result());
        record.speedup = stats.assembly_time_ms > 0.0 ? serial_time_ms / stats.assembly_time_ms : 0.0;
        if (cfg.check && reference && (!record.error.same_structure || record.error.relative_l2 > 1.0e-8)) {
            record.status = "FAIL";
            record.message = "correctness check failed";
        }
    } catch (const std::exception& ex) {
        record.status = "FAIL";
        record.message = ex.what();
    }
    return record;
}

void write_csv_header(std::ofstream& out) {
    out << "mesh,element_type,kernel,nodes,elements,dofs,nnz,algorithm,threads,"
        << "preprocess_ms,assembly_ms,total_ms,rel_l2,max_abs,speedup,"
        << "extra_memory_bytes,status,colors,diagnostics,platform\n";
}

void write_csv_record(std::ofstream& out,
                      const Mesh& mesh,
                      const CsrMatrix& csr,
                      const RunRecord& r,
                      KernelType kernel) {
    out << '"' << mesh.name << "\"," << element_type_to_string(mesh.dominant_element_type()) << ','
        << kernel_type_to_string(kernel) << ','
        << mesh.num_nodes() << ',' << mesh.num_elements() << ',' << mesh.num_dofs() << ',' << csr.nnz() << ','
        << r.algorithm << ',' << r.threads << ','
        << std::setprecision(10) << r.stats.preprocess_time_ms << ','
        << r.stats.assembly_time_ms << ',' << r.stats.total_time_ms << ','
        << r.error.relative_l2 << ',' << r.error.max_abs << ',' << r.speedup << ','
        << r.stats.extra_memory_bytes << ',' << r.status << ',' << r.stats.colors << ','
        << '"' << r.message << "\","
        << '"' << platform_info_compact() << "\"\n";
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
        std::cout << " CPU Parallel Global Stiffness Assembly Benchmark\n";
        std::cout << "============================================================\n";
        std::cout << mesh_summary(mesh) << "\n";
        std::cout << "nnz=" << csr.nnz() << ", csr_memory=" << memory_string(csr.bytes())
                  << ", plan_memory=" << memory_string(plan.bytes()) << "\n";
        std::cout << "kernel=" << kernel_type_to_string(cfg.kernel)
                  << ", platform=" << platform_info_compact() << "\n";
        std::cout << "precompute: mesh=" << mesh_ms << " ms, csr=" << csr_ms
                  << " ms, scatter_plan=" << plan_ms << " ms\n\n";

        CsrMatrix reference;
        RunRecord baseline;
        {
            baseline = run_one(AlgorithmType::CpuSerial, 1, cfg, mesh, csr, plan, nullptr, 0.0);
            if (baseline.status != "PASS") throw std::runtime_error("Serial baseline failed: " + baseline.message);
            auto assembler = AssemblerFactory::create(AlgorithmType::CpuSerial, AssemblyOptions{});
            AssemblyOptions options;
            options.kernel = cfg.kernel;
            options.young_modulus = cfg.young;
            options.poisson_ratio = cfg.poisson;
            options.max_transient_bytes = cfg.max_transient_bytes;
            assembler = AssemblerFactory::create(AlgorithmType::CpuSerial, options);
            assembler->set_problem(mesh, csr, plan);
            assembler->prepare();
            assembler->assemble();
            reference = assembler->get_result();
            baseline.speedup = 1.0;
            baseline.error = compare_values(reference, reference);
        }
        const double serial_time_ms = baseline.stats.assembly_time_ms;

        std::ofstream csv(cfg.csv_path);
        if (!csv) throw std::runtime_error("Cannot write CSV: " + cfg.csv_path);
        write_csv_header(csv);

        std::cout << std::left << std::setw(24) << "algorithm"
                  << std::right << std::setw(8) << "threads"
                  << std::setw(14) << "prep_ms"
                  << std::setw(14) << "asm_ms"
                  << std::setw(12) << "speedup"
                  << std::setw(14) << "rel_l2"
                  << std::setw(10) << "status" << "\n";
        std::cout << std::string(88, '-') << "\n";

        for (int threads : cfg.thread_counts) {
            for (AlgorithmType algo : cfg.algorithms) {
                if (algo == AlgorithmType::CpuSerial && threads != 1) continue;
                const CsrMatrix* ref_ptr = cfg.check ? &reference : nullptr;
                RunRecord rec;
                if (algo == AlgorithmType::CpuSerial) {
                    rec = baseline;
                    rec.threads = 1;
                } else {
                    rec = run_one(algo, threads, cfg, mesh, csr, plan, ref_ptr, serial_time_ms);
                }
                std::cout << std::left << std::setw(24) << rec.algorithm
                          << std::right << std::setw(8) << rec.threads
                          << std::setw(14) << std::fixed << std::setprecision(3) << rec.stats.preprocess_time_ms
                          << std::setw(14) << rec.stats.assembly_time_ms
                          << std::setw(12) << std::setprecision(3) << rec.speedup
                          << std::setw(14) << std::scientific << std::setprecision(2) << rec.error.relative_l2
                          << std::setw(10) << rec.status << "\n";
                if (rec.status != "PASS" && !rec.message.empty()) {
                    std::cout << "  note: " << rec.message << "\n";
                }
                write_csv_record(csv, mesh, csr, rec, cfg.kernel);
            }
        }
        std::cout << "\nResults saved to " << cfg.csv_path << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
