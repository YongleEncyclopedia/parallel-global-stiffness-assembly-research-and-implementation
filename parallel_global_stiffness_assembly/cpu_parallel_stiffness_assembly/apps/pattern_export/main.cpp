#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/platform.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace fem;

namespace {

struct Config {
    std::string mesh_mode = "inp";
    std::string inp_path = "../../examples/3d-WindTurbineHub.inp";
    std::string case_name;
    ElementType element_type = ElementType::Tet4;
    int nx = 1;
    int ny = 1;
    int nz = 1;
    KernelType kernel = KernelType::PhysicsTet4;
    int threads = 1;
    AlgorithmType parallel_algo = AlgorithmType::CpuAtomic;
    std::string out_dir = "pattern-export";
    std::string prefix = "stiffness";
};

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

std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
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
        << "Sparse stiffness pattern export\n\n"
        << "Usage:\n  " << exe << " [options]\n\n"
        << "Options:\n"
        << "  --mesh cube|inp\n"
        << "  --inp PATH\n"
        << "  --case-name NAME\n"
        << "  --element tet4|hex8\n"
        << "  --nx N --ny N --nz N\n"
        << "  --kernel simplified|physics_tet4\n"
        << "  --threads N\n"
        << "  --parallel-algo atomic|lock_guard|private_csr|row_owner|coloring\n"
        << "  --out-dir PATH\n"
        << "  --prefix NAME\n"
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
        else if (arg == "--threads") cfg.threads = std::stoi(require_value(arg));
        else if (arg == "--parallel-algo") cfg.parallel_algo = parse_algorithm_type(require_value(arg));
        else if (arg == "--out-dir") cfg.out_dir = require_value(arg);
        else if (arg == "--prefix") cfg.prefix = require_value(arg);
        else throw std::invalid_argument("Unknown argument: " + arg);
    }
    return cfg;
}

Mesh build_mesh(const Config& cfg) {
    if (to_lower(cfg.mesh_mode) == "cube") {
        Mesh mesh = cfg.element_type == ElementType::Tet4
                        ? Mesh::make_cube_tet4(cfg.nx, cfg.ny, cfg.nz)
                        : Mesh::make_cube_hex8(cfg.nx, cfg.ny, cfg.nz);
        mesh.name = cfg.case_name.empty() ? mesh.name : cfg.case_name;
        return mesh;
    }
    if (to_lower(cfg.mesh_mode) == "inp") {
        if (cfg.inp_path.empty()) throw std::invalid_argument("--mesh inp requires --inp PATH");
        if (is_git_lfs_pointer(cfg.inp_path)) {
            throw std::runtime_error("Input file is still a Git LFS pointer. Run `git lfs pull` and retry.");
        }
        Mesh mesh = Mesh::load_from_inp(cfg.inp_path);
        mesh.name = cfg.case_name.empty() ? std::filesystem::path(cfg.inp_path).stem().string() : cfg.case_name;
        return mesh;
    }
    throw std::invalid_argument("Unsupported mesh mode: " + cfg.mesh_mode);
}

CsrMatrix assemble_matrix(const Mesh& mesh,
                          const CsrMatrix& csr,
                          const AssemblyPlan& plan,
                          AlgorithmType algo,
                          const AssemblyOptions& options) {
    auto assembler = AssemblerFactory::create(algo, options);
    assembler->set_problem(mesh, csr, plan);
    assembler->prepare();
    assembler->assemble();
    return assembler->get_result();
}

void write_csv_pattern(const std::filesystem::path& path, const CsrMatrix& matrix) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write CSV pattern: " + path.string());
    out << "row,col\n";
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            out << row << ',' << matrix.col_indices[p] << '\n';
        }
    }
}

void write_matrix_market_pattern(const std::filesystem::path& path, const CsrMatrix& matrix) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write MatrixMarket pattern: " + path.string());
    out << "%%MatrixMarket matrix coordinate pattern general\n";
    out << "% row and column indices are 1-based per MatrixMarket convention\n";
    out << matrix.n_rows << ' ' << matrix.n_cols << ' ' << matrix.nnz() << '\n';
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            out << row + 1 << ' ' << matrix.col_indices[p] + 1 << '\n';
        }
    }
}

void write_metadata(const std::filesystem::path& path,
                    const Config& cfg,
                    const Mesh& mesh,
                    const CsrMatrix& serial,
                    const CsrMatrix& parallel,
                    const MatrixError& error) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write metadata: " + path.string());
    out << "{\n"
        << "  \"case_name\": \"" << json_escape(mesh.name) << "\",\n"
        << "  \"kernel\": \"" << kernel_type_to_string(cfg.kernel) << "\",\n"
        << "  \"platform\": \"" << json_escape(platform_info_compact()) << "\",\n"
        << "  \"mesh\": {\n"
        << "    \"nodes\": " << mesh.num_nodes() << ",\n"
        << "    \"elements\": " << mesh.num_elements() << ",\n"
        << "    \"dofs\": " << mesh.num_dofs() << "\n"
        << "  },\n"
        << "  \"serial\": {\n"
        << "    \"algorithm\": \"cpu_serial\",\n"
        << "    \"nnz\": " << serial.nnz() << "\n"
        << "  },\n"
        << "  \"parallel\": {\n"
        << "    \"algorithm\": \"" << algorithm_to_string(cfg.parallel_algo) << "\",\n"
        << "    \"threads\": " << cfg.threads << ",\n"
        << "    \"nnz\": " << parallel.nnz() << "\n"
        << "  },\n"
        << "  \"correctness\": {\n"
        << "    \"same_structure\": " << (error.same_structure ? "true" : "false") << ",\n"
        << "    \"relative_l2\": " << error.relative_l2 << ",\n"
        << "    \"max_abs\": " << error.max_abs << "\n"
        << "  }\n"
        << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const Config cfg = parse_args(argc, argv);
        Mesh mesh = build_mesh(cfg);
        CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
        AssemblyPlan plan = build_assembly_plan(mesh, csr);

        AssemblyOptions serial_options;
        serial_options.threads = 1;
        serial_options.kernel = cfg.kernel;
        AssemblyOptions parallel_options = serial_options;
        parallel_options.threads = cfg.threads;

        CsrMatrix serial = assemble_matrix(mesh, csr, plan, AlgorithmType::CpuSerial, serial_options);
        CsrMatrix parallel = assemble_matrix(mesh, csr, plan, cfg.parallel_algo, parallel_options);
        const MatrixError error = compare_values(serial, parallel);
        if (!error.same_structure) {
            throw std::runtime_error("Serial and parallel stiffness matrices do not share the same sparse structure");
        }

        const auto out_dir = std::filesystem::path(cfg.out_dir);
        std::filesystem::create_directories(out_dir);
        write_csv_pattern(out_dir / (cfg.prefix + "_serial_pattern.csv"), serial);
        write_csv_pattern(out_dir / (cfg.prefix + "_parallel_pattern.csv"), parallel);
        write_matrix_market_pattern(out_dir / (cfg.prefix + "_serial_pattern.mtx"), serial);
        write_matrix_market_pattern(out_dir / (cfg.prefix + "_parallel_pattern.mtx"), parallel);
        write_metadata(out_dir / (cfg.prefix + "_metadata.json"), cfg, mesh, serial, parallel, error);

        std::cout << "pattern export complete: " << out_dir << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
