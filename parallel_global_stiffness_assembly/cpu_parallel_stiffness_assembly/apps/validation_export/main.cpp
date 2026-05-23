#include "assembly/symbolic_numeric_eval.h"
#include "core/mesh.h"
#include "core/platform.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <filesystem>
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
    std::string case_name = "cantilever_hex8_small";
    std::string mesh_mode = "case";
    std::string inp_path;
    ElementType element_type = ElementType::Hex8;
    int nx = -1;
    int ny = -1;
    int nz = -1;
    Real length = 1.0;
    Real width = 0.2;
    Real thickness = 0.1;
    Real young_modulus = 1.0;
    Real poisson_ratio = 0.3;
    Real total_load = -1.0;
    int load_dof = 2;
    StiffnessModel stiffness_model = StiffnessModel::LinearElasticSolid;
    std::string out_dir = "validation-export";
    std::string prefix = "validation";
    bool case_name_explicit = false;
    bool allow_legacy_synthetic = false;
};

struct Bounds {
    Real xmin = 0.0;
    Real xmax = 0.0;
    Real ymin = 0.0;
    Real ymax = 0.0;
    Real zmin = 0.0;
    Real zmax = 0.0;
};

struct ForceEntry {
    Index node = 0;
    int dof = 0;
    Real force = 0.0;
};

struct BoundaryEntry {
    Index node = 0;
    int dof = 0;
    Real value = 0.0;
};

struct ProbeEntry {
    std::string name;
    Index node = 0;
    Node target;
    Node actual;
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

std::string lower_ascii(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

std::string element_type_lower(ElementType type) {
    switch (type) {
    case ElementType::Hex8: return "hex8";
    case ElementType::Tet4: return "tet4";
    }
    return "unknown";
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
        << "Validation export for solve-level FEM checks\n\n"
        << "Usage:\n  " << exe << " [options]\n\n"
        << "Options:\n"
        << "  --case cantilever_hex8_small|cantilever_hex8_medium|cantilever_tet4_small|cantilever_tet4_medium\n"
        << "  --mesh case|cube|inp\n"
        << "  --inp PATH\n"
        << "  --case-name NAME\n"
        << "  --element tet4|hex8\n"
        << "  --nx N --ny N --nz N\n"
        << "  --length L --width W --thickness T\n"
        << "  --E VALUE --nu VALUE\n"
        << "  --total-load VALUE\n"
        << "  --load-dof 0|1|2\n"
        << "  --stiffness-model linear_elastic_solid\n"
        << "  --kernel MODEL                   deprecated alias; physics_solid maps to linear_elastic_solid, physics_tet4 is Tet4/C3D4-only\n"
        << "  --allow-legacy-synthetic         allow deprecated legacy_synthetic/simplified smoke model\n"
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
        } else if (arg == "--case") {
            cfg.case_name = require_value(arg);
            cfg.mesh_mode = "case";
        } else if (arg == "--mesh") cfg.mesh_mode = require_value(arg);
        else if (arg == "--inp") cfg.inp_path = require_value(arg);
        else if (arg == "--case-name") {
            cfg.case_name = require_value(arg);
            cfg.case_name_explicit = true;
        } else if (arg == "--element") cfg.element_type = parse_element_type(require_value(arg));
        else if (arg == "--nx") cfg.nx = std::stoi(require_value(arg));
        else if (arg == "--ny") cfg.ny = std::stoi(require_value(arg));
        else if (arg == "--nz") cfg.nz = std::stoi(require_value(arg));
        else if (arg == "--length" || arg == "--L") cfg.length = std::stod(require_value(arg));
        else if (arg == "--width" || arg == "--W") cfg.width = std::stod(require_value(arg));
        else if (arg == "--thickness" || arg == "--T") cfg.thickness = std::stod(require_value(arg));
        else if (arg == "--E" || arg == "--young") cfg.young_modulus = std::stod(require_value(arg));
        else if (arg == "--nu" || arg == "--poisson") cfg.poisson_ratio = std::stod(require_value(arg));
        else if (arg == "--total-load") cfg.total_load = std::stod(require_value(arg));
        else if (arg == "--load-dof") cfg.load_dof = std::stoi(require_value(arg));
        else if (arg == "--stiffness-model") cfg.stiffness_model = parse_stiffness_model(require_value(arg));
        else if (arg == "--kernel") cfg.stiffness_model = parse_kernel_type(require_value(arg));
        else if (arg == "--allow-legacy-synthetic") cfg.allow_legacy_synthetic = true;
        else if (arg == "--out-dir") cfg.out_dir = require_value(arg);
        else if (arg == "--prefix") cfg.prefix = require_value(arg);
        else throw std::invalid_argument("Unknown argument: " + arg);
    }
    if (cfg.length <= 0.0 || cfg.width <= 0.0 || cfg.thickness <= 0.0) {
        throw std::invalid_argument("--length, --width, and --thickness must be positive");
    }
    if (cfg.young_modulus <= 0.0) throw std::invalid_argument("--E must be positive");
    if (cfg.poisson_ratio <= -1.0 || cfg.poisson_ratio >= 0.5) {
        throw std::invalid_argument("--nu must be in (-1, 0.5)");
    }
    if (cfg.load_dof < 0 || cfg.load_dof >= constants::DOFS_PER_NODE) {
        throw std::invalid_argument("--load-dof must be 0, 1, or 2");
    }
    if (is_legacy_synthetic(cfg.stiffness_model) && !cfg.allow_legacy_synthetic) {
        throw std::invalid_argument(
            "legacy_synthetic/simplified is a deprecated synthetic smoke model; pass --allow-legacy-synthetic to use it");
    }
    return cfg;
}

int choose_or_default(int value, int fallback) {
    return value > 0 ? value : fallback;
}

Mesh build_case_mesh(Config& cfg) {
    const std::string name = lower_ascii(cfg.case_name);
    if (name == "cantilever_hex8_small") {
        cfg.element_type = ElementType::Hex8;
        Mesh mesh = Mesh::make_cube_hex8(choose_or_default(cfg.nx, 2),
                                         choose_or_default(cfg.ny, 2),
                                         choose_or_default(cfg.nz, 2),
                                         cfg.length,
                                         cfg.width,
                                         cfg.thickness);
        mesh.name = "cantilever_hex8_small";
        return mesh;
    }
    if (name == "cantilever_hex8_medium") {
        cfg.element_type = ElementType::Hex8;
        Mesh mesh = Mesh::make_cube_hex8(choose_or_default(cfg.nx, 12),
                                         choose_or_default(cfg.ny, 4),
                                         choose_or_default(cfg.nz, 4),
                                         cfg.length,
                                         cfg.width,
                                         cfg.thickness);
        mesh.name = "cantilever_hex8_medium";
        return mesh;
    }
    if (name == "cantilever_tet4_small") {
        cfg.element_type = ElementType::Tet4;
        Mesh mesh = Mesh::make_cube_tet4(choose_or_default(cfg.nx, 2),
                                         choose_or_default(cfg.ny, 2),
                                         choose_or_default(cfg.nz, 2),
                                         cfg.length,
                                         cfg.width,
                                         cfg.thickness);
        mesh.name = "cantilever_tet4_small";
        return mesh;
    }
    if (name == "cantilever_tet4_medium") {
        cfg.element_type = ElementType::Tet4;
        Mesh mesh = Mesh::make_cube_tet4(choose_or_default(cfg.nx, 12),
                                         choose_or_default(cfg.ny, 4),
                                         choose_or_default(cfg.nz, 4),
                                         cfg.length,
                                         cfg.width,
                                         cfg.thickness);
        mesh.name = "cantilever_tet4_medium";
        return mesh;
    }
    throw std::invalid_argument("Unsupported validation case: " + cfg.case_name);
}

Mesh build_mesh(Config& cfg) {
    const std::string mode = lower_ascii(cfg.mesh_mode);
    if (mode == "case") return build_case_mesh(cfg);
    if (mode == "cube") {
        const int nx = choose_or_default(cfg.nx, 2);
        const int ny = choose_or_default(cfg.ny, 2);
        const int nz = choose_or_default(cfg.nz, 2);
        Mesh mesh = cfg.element_type == ElementType::Tet4
                        ? Mesh::make_cube_tet4(nx, ny, nz, cfg.length, cfg.width, cfg.thickness)
                        : Mesh::make_cube_hex8(nx, ny, nz, cfg.length, cfg.width, cfg.thickness);
        if (cfg.case_name_explicit) mesh.name = cfg.case_name;
        return mesh;
    }
    if (mode == "inp") {
        if (cfg.inp_path.empty()) throw std::invalid_argument("--mesh inp requires --inp PATH");
        if (is_git_lfs_pointer(cfg.inp_path)) {
            throw std::runtime_error("Input file is still a Git LFS pointer. Run `git lfs pull` and retry.");
        }
        Mesh mesh = Mesh::load_from_inp(cfg.inp_path);
        cfg.element_type = mesh.dominant_element_type();
        mesh.name = cfg.case_name_explicit ? cfg.case_name : std::filesystem::path(cfg.inp_path).stem().string();
        return mesh;
    }
    throw std::invalid_argument("Unsupported mesh mode: " + cfg.mesh_mode);
}

Bounds compute_bounds(const Mesh& mesh) {
    if (mesh.nodes.empty()) throw std::runtime_error("Cannot compute bounds for an empty mesh");
    Bounds b;
    b.xmin = b.xmax = mesh.nodes.front().x;
    b.ymin = b.ymax = mesh.nodes.front().y;
    b.zmin = b.zmax = mesh.nodes.front().z;
    for (const auto& node : mesh.nodes) {
        b.xmin = std::min(b.xmin, node.x);
        b.xmax = std::max(b.xmax, node.x);
        b.ymin = std::min(b.ymin, node.y);
        b.ymax = std::max(b.ymax, node.y);
        b.zmin = std::min(b.zmin, node.z);
        b.zmax = std::max(b.zmax, node.z);
    }
    return b;
}

Real face_tolerance(const Bounds& b) {
    const Real span = std::max({std::abs(b.xmax - b.xmin),
                                std::abs(b.ymax - b.ymin),
                                std::abs(b.zmax - b.zmin),
                                Real{1.0}});
    return span * 1.0e-9;
}

std::vector<BoundaryEntry> build_fixed_bcs(const Mesh& mesh, const Bounds& bounds) {
    std::vector<BoundaryEntry> bcs;
    const Real tol = face_tolerance(bounds);
    for (Index node_index = 0; node_index < static_cast<Index>(mesh.nodes.size()); ++node_index) {
        const auto& node = mesh.nodes[static_cast<Size>(node_index)];
        if (std::abs(node.x - bounds.xmin) <= tol) {
            for (int dof = 0; dof < constants::DOFS_PER_NODE; ++dof) {
                bcs.push_back(BoundaryEntry{node_index, dof, 0.0});
            }
        }
    }
    if (bcs.empty()) throw std::runtime_error("No fixed-face boundary nodes were found at x=min");
    return bcs;
}

std::vector<ForceEntry> build_face_load(const Mesh& mesh, const Bounds& bounds, const Config& cfg) {
    std::vector<Index> loaded_nodes;
    const Real tol = face_tolerance(bounds);
    for (Index node_index = 0; node_index < static_cast<Index>(mesh.nodes.size()); ++node_index) {
        const auto& node = mesh.nodes[static_cast<Size>(node_index)];
        if (std::abs(node.x - bounds.xmax) <= tol) loaded_nodes.push_back(node_index);
    }
    if (loaded_nodes.empty()) throw std::runtime_error("No loaded-face nodes were found at x=max");

    std::vector<ForceEntry> forces;
    const Real nodal_force = cfg.total_load / static_cast<Real>(loaded_nodes.size());
    for (Index node : loaded_nodes) forces.push_back(ForceEntry{node, cfg.load_dof, nodal_force});
    return forces;
}

Index nearest_node(const Mesh& mesh, const Node& target) {
    Index best = 0;
    Real best_dist2 = std::numeric_limits<Real>::max();
    for (Index node_index = 0; node_index < static_cast<Index>(mesh.nodes.size()); ++node_index) {
        const auto& node = mesh.nodes[static_cast<Size>(node_index)];
        const Real dx = node.x - target.x;
        const Real dy = node.y - target.y;
        const Real dz = node.z - target.z;
        const Real dist2 = dx * dx + dy * dy + dz * dz;
        if (dist2 < best_dist2) {
            best_dist2 = dist2;
            best = node_index;
        }
    }
    return best;
}

std::vector<ProbeEntry> build_probes(const Mesh& mesh, const Bounds& bounds) {
    const Real yc = 0.5 * (bounds.ymin + bounds.ymax);
    const Real zc = 0.5 * (bounds.zmin + bounds.zmax);
    const std::array<std::pair<const char*, Node>, 3> targets{{
        {"free_tip_center", Node{bounds.xmax, yc, zc}},
        {"midspan_center", Node{0.5 * (bounds.xmin + bounds.xmax), yc, zc}},
        {"root_center", Node{bounds.xmin, yc, zc}},
    }};

    std::vector<ProbeEntry> probes;
    for (const auto& [name, target] : targets) {
        const Index node_index = nearest_node(mesh, target);
        probes.push_back(ProbeEntry{name, node_index, target, mesh.nodes[static_cast<Size>(node_index)]});
    }
    return probes;
}

void write_matrix_market_symmetric(const std::filesystem::path& path, const CsrMatrix& matrix) {
    Size lower_nnz = 0;
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            if (matrix.col_indices[p] <= row) ++lower_nnz;
        }
    }

    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write MatrixMarket stiffness matrix: " + path.string());
    out << "%%MatrixMarket matrix coordinate real symmetric\n";
    out << "% lower triangle only; row and column indices are 1-based per MatrixMarket convention\n";
    out << matrix.n_rows << ' ' << matrix.n_cols << ' ' << lower_nnz << '\n';
    out << std::setprecision(17);
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index col = matrix.col_indices[p];
            if (col <= row) out << row + 1 << ' ' << col + 1 << ' ' << matrix.values[p] << '\n';
        }
    }
}

void write_force_csv(const std::filesystem::path& path, const std::vector<ForceEntry>& forces) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write force CSV: " + path.string());
    out << "node,dof,force\n";
    out << std::setprecision(17);
    for (const auto& force : forces) {
        out << force.node << ',' << force.dof << ',' << force.force << '\n';
    }
}

void write_bc_csv(const std::filesystem::path& path, const std::vector<BoundaryEntry>& bcs) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write BC CSV: " + path.string());
    out << "node,dof,value\n";
    out << std::setprecision(17);
    for (const auto& bc : bcs) out << bc.node << ',' << bc.dof << ',' << bc.value << '\n';
}

void write_probes_csv(const std::filesystem::path& path, const std::vector<ProbeEntry>& probes) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write probes CSV: " + path.string());
    out << "name,node,target_x,target_y,target_z,x,y,z\n";
    out << std::setprecision(17);
    for (const auto& probe : probes) {
        out << probe.name << ','
            << probe.node << ','
            << probe.target.x << ','
            << probe.target.y << ','
            << probe.target.z << ','
            << probe.actual.x << ','
            << probe.actual.y << ','
            << probe.actual.z << '\n';
    }
}

Size symmetric_lower_nnz(const CsrMatrix& matrix) {
    Size lower_nnz = 0;
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            if (matrix.col_indices[p] <= row) ++lower_nnz;
        }
    }
    return lower_nnz;
}

void write_metadata(const std::filesystem::path& path,
                    const Config& cfg,
                    const Mesh& mesh,
                    const Bounds& bounds,
                    const CsrMatrix& matrix,
                    double symbolic_ms,
                    double numeric_ms,
                    const std::vector<ForceEntry>& forces,
                    const std::vector<BoundaryEntry>& bcs,
                    const std::vector<ProbeEntry>& probes) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write metadata JSON: " + path.string());
    out << std::setprecision(17);
    out << "{\n"
        << "  \"case_name\": \"" << json_escape(mesh.name) << "\",\n"
        << "  \"stiffness_model\": \"" << stiffness_model_to_string(cfg.stiffness_model) << "\",\n"
        << "  \"kernel\": \"" << stiffness_model_to_string(cfg.stiffness_model) << "\",\n"
        << "  \"element_type\": \"" << element_type_lower(mesh.dominant_element_type()) << "\",\n"
        << "  \"index_base\": 0,\n"
        << "  \"platform\": \"" << json_escape(platform_info_compact()) << "\",\n"
        << "  \"material\": {\n"
        << "    \"E\": " << cfg.young_modulus << ",\n"
        << "    \"nu\": " << cfg.poisson_ratio << "\n"
        << "  },\n"
        << "  \"mesh\": {\n"
        << "    \"nodes\": " << mesh.num_nodes() << ",\n"
        << "    \"elements\": " << mesh.num_elements() << ",\n"
        << "    \"dofs\": " << mesh.num_dofs() << ",\n"
        << "    \"bounds\": {\n"
        << "      \"xmin\": " << bounds.xmin << ", \"xmax\": " << bounds.xmax << ",\n"
        << "      \"ymin\": " << bounds.ymin << ", \"ymax\": " << bounds.ymax << ",\n"
        << "      \"zmin\": " << bounds.zmin << ", \"zmax\": " << bounds.zmax << "\n"
        << "    }\n"
        << "  },\n"
        << "  \"matrix\": {\n"
        << "    \"format\": \"MatrixMarket coordinate real symmetric\",\n"
        << "    \"rows\": " << matrix.n_rows << ",\n"
        << "    \"cols\": " << matrix.n_cols << ",\n"
        << "    \"nnz\": " << matrix.nnz() << ",\n"
        << "    \"lower_triangle_nnz\": " << symmetric_lower_nnz(matrix) << "\n"
        << "  },\n"
        << "  \"boundary\": {\n"
        << "    \"fixed_face\": \"x=0\",\n"
        << "    \"fixed_dofs\": " << bcs.size() << "\n"
        << "  },\n"
        << "  \"load\": {\n"
        << "    \"loaded_face\": \"x=L\",\n"
        << "    \"total_load\": " << cfg.total_load << ",\n"
        << "    \"load_dof\": " << cfg.load_dof << ",\n"
        << "    \"loaded_nodes\": " << forces.size() << "\n"
        << "  },\n"
        << "  \"probes\": [\n";
    for (Size i = 0; i < probes.size(); ++i) {
        const auto& probe = probes[i];
        out << "    {\"name\": \"" << json_escape(probe.name) << "\", \"node\": " << probe.node << "}";
        out << (i + 1 == probes.size() ? "\n" : ",\n");
    }
    out << "  ],\n"
        << "  \"assembly\": {\n"
        << "    \"symbolic_ms\": " << symbolic_ms << ",\n"
        << "    \"numeric_ms\": " << numeric_ms << ",\n"
        << "    \"numeric_backend\": \"cpu_serial_export_reference\"\n"
        << "  },\n"
        << "  \"files\": {\n"
        << "    \"K\": \"" << json_escape(cfg.prefix + "_K.mtx") << "\",\n"
        << "    \"force\": \"" << json_escape(cfg.prefix + "_force.csv") << "\",\n"
        << "    \"bc\": \"" << json_escape(cfg.prefix + "_bc.csv") << "\",\n"
        << "    \"probes\": \"" << json_escape(cfg.prefix + "_probes.csv") << "\"\n"
        << "  }\n"
        << "}\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        Config cfg = parse_args(argc, argv);
        Mesh mesh = build_mesh(cfg);
        if (mesh.empty()) throw std::runtime_error("Validation mesh is empty");

        AssemblyOptions options;
        options.stiffness_model = cfg.stiffness_model;
        options.young_modulus = cfg.young_modulus;
        options.poisson_ratio = cfg.poisson_ratio;

        SymbolicArtifacts artifacts = build_symbolic_artifacts(mesh);
        SymbolicSerialResult assembled = assemble_symbolic_serial_once(mesh, artifacts, options);

        const Bounds bounds = compute_bounds(mesh);
        const auto bcs = build_fixed_bcs(mesh, bounds);
        const auto forces = build_face_load(mesh, bounds, cfg);
        const auto probes = build_probes(mesh, bounds);

        const std::filesystem::path out_dir(cfg.out_dir);
        std::filesystem::create_directories(out_dir);
        write_matrix_market_symmetric(out_dir / (cfg.prefix + "_K.mtx"), assembled.matrix);
        write_force_csv(out_dir / (cfg.prefix + "_force.csv"), forces);
        write_bc_csv(out_dir / (cfg.prefix + "_bc.csv"), bcs);
        write_probes_csv(out_dir / (cfg.prefix + "_probes.csv"), probes);
        write_metadata(out_dir / (cfg.prefix + "_metadata.json"),
                       cfg,
                       mesh,
                       bounds,
                       assembled.matrix,
                       artifacts.total_ms(),
                       assembled.numeric_ms,
                       forces,
                       bcs,
                       probes);

        std::cout << "validation_export complete: " << out_dir << "/" << cfg.prefix << "_*\n";
        std::cout << mesh_summary(mesh) << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "validation_export failed: " << ex.what() << "\n";
        return 1;
    }
}
