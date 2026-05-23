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
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

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
    int csr_window_start = 0;
    int csr_window_rows = 4;
    int visualization_bins = 1800;
    int exact_window_row_start = 0;
    int exact_window_col_start = 0;
    int exact_window_size = 4096;
    bool skip_full_patterns = false;
};

struct VisualizationStats {
    Size original_bandwidth = 0;
    Size rcm_bandwidth = 0;
    Size rcm_nnz = 0;
    int visualization_bins = 0;
    int exact_window_row_start = 0;
    int exact_window_col_start = 0;
    int exact_window_size = 0;
    int exact_window_auto_row_start = 0;
    int exact_window_auto_col_start = 0;
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
        << "  --csr-window-start ROW\n"
        << "  --csr-window-rows N\n"
        << "  --visualization-bins N\n"
        << "  --exact-window-row-start ROW\n"
        << "  --exact-window-col-start COL\n"
        << "  --exact-window-size N\n"
        << "  --skip-full-patterns\n"
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
        else if (arg == "--csr-window-start") cfg.csr_window_start = std::stoi(require_value(arg));
        else if (arg == "--csr-window-rows") cfg.csr_window_rows = std::stoi(require_value(arg));
        else if (arg == "--visualization-bins") cfg.visualization_bins = std::stoi(require_value(arg));
        else if (arg == "--exact-window-row-start") cfg.exact_window_row_start = std::stoi(require_value(arg));
        else if (arg == "--exact-window-col-start") cfg.exact_window_col_start = std::stoi(require_value(arg));
        else if (arg == "--exact-window-size") cfg.exact_window_size = std::stoi(require_value(arg));
        else if (arg == "--skip-full-patterns") cfg.skip_full_patterns = true;
        else throw std::invalid_argument("Unknown argument: " + arg);
    }
    if (cfg.csr_window_start < 0) throw std::invalid_argument("--csr-window-start must be non-negative");
    if (cfg.csr_window_rows <= 0) throw std::invalid_argument("--csr-window-rows must be positive");
    if (cfg.visualization_bins <= 0) throw std::invalid_argument("--visualization-bins must be positive");
    if (cfg.exact_window_row_start < 0) throw std::invalid_argument("--exact-window-row-start must be non-negative");
    if (cfg.exact_window_col_start < 0) throw std::invalid_argument("--exact-window-col-start must be non-negative");
    if (cfg.exact_window_size <= 0) throw std::invalid_argument("--exact-window-size must be positive");
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

void write_csr_window(const std::filesystem::path& path,
                      const CsrMatrix& matrix,
                      int start_row,
                      int row_count) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write CSR window: " + path.string());

    const Index first = std::min<Index>(static_cast<Index>(start_row), matrix.n_rows);
    const Index last = std::min<Index>(matrix.n_rows, first + static_cast<Index>(row_count));
    out << "row,row_offset_begin,row_offset_end,p,col,value\n";
    out << std::setprecision(17);
    for (Index row = first; row < last; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            out << row << ','
                << begin << ','
                << end << ','
                << p << ','
                << matrix.col_indices[p] << ','
                << matrix.values[p] << '\n';
        }
    }
}

void write_csr_window_summary(const std::filesystem::path& path,
                              const CsrMatrix& matrix,
                              int start_row,
                              int row_count) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write CSR window summary: " + path.string());

    const Index first = std::min<Index>(static_cast<Index>(start_row), matrix.n_rows);
    const Index last = std::min<Index>(matrix.n_rows, first + static_cast<Index>(row_count));
    out << "# CSR Window Summary\n\n";
    out << "- Matrix shape: `" << matrix.n_rows << " x " << matrix.n_cols << "`\n";
    out << "- Total nnz: `" << matrix.nnz() << "`\n";
    out << "- Row window: `[" << first << ", " << last << ")`\n\n";
    out << "| row | row_offsets[row] | row_offsets[row+1] | row nnz |\n";
    out << "| --- | ---: | ---: | ---: |\n";
    for (Index row = first; row < last; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        out << "| " << row << " | " << begin << " | " << end << " | " << (end - begin) << " |\n";
    }
}

Size matrix_bandwidth(const CsrMatrix& matrix) {
    Size bandwidth = 0;
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index col = matrix.col_indices[p];
            const auto delta = row > col ? row - col : col - row;
            bandwidth = std::max(bandwidth, static_cast<Size>(delta));
        }
    }
    return bandwidth;
}

Size permuted_bandwidth(const CsrMatrix& matrix, const std::vector<Index>& old_to_new) {
    Size bandwidth = 0;
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Index new_row = old_to_new[static_cast<Size>(row)];
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index new_col = old_to_new[static_cast<Size>(matrix.col_indices[p])];
            const auto delta = new_row > new_col ? new_row - new_col : new_col - new_row;
            bandwidth = std::max(bandwidth, static_cast<Size>(delta));
        }
    }
    return bandwidth;
}

std::vector<Index> reverse_cuthill_mckee(const CsrMatrix& matrix) {
    const Size n = static_cast<Size>(matrix.n_rows);
    std::vector<Index> degree(n, 0);
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        Index d = 0;
        for (Size p = begin; p < end; ++p) {
            if (matrix.col_indices[p] != row) ++d;
        }
        degree[static_cast<Size>(row)] = d;
    }

    std::vector<Index> candidates(n);
    std::iota(candidates.begin(), candidates.end(), 0);
    std::sort(candidates.begin(), candidates.end(), [&](Index a, Index b) {
        if (degree[static_cast<Size>(a)] != degree[static_cast<Size>(b)]) {
            return degree[static_cast<Size>(a)] < degree[static_cast<Size>(b)];
        }
        return a < b;
    });

    std::vector<unsigned char> visited(n, 0);
    std::vector<Index> order;
    order.reserve(n);
    std::queue<Index> q;
    std::vector<Index> neighbors;

    for (Index start : candidates) {
        if (visited[static_cast<Size>(start)]) continue;
        visited[static_cast<Size>(start)] = 1;
        q.push(start);
        while (!q.empty()) {
            const Index row = q.front();
            q.pop();
            order.push_back(row);
            neighbors.clear();
            const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
            const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
            for (Size p = begin; p < end; ++p) {
                const Index col = matrix.col_indices[p];
                if (col == row) continue;
                if (!visited[static_cast<Size>(col)]) {
                    visited[static_cast<Size>(col)] = 1;
                    neighbors.push_back(col);
                }
            }
            std::sort(neighbors.begin(), neighbors.end(), [&](Index a, Index b) {
                if (degree[static_cast<Size>(a)] != degree[static_cast<Size>(b)]) {
                    return degree[static_cast<Size>(a)] < degree[static_cast<Size>(b)];
                }
                return a < b;
            });
            for (Index col : neighbors) q.push(col);
        }
    }
    std::reverse(order.begin(), order.end());

    std::vector<Index> old_to_new(n, 0);
    for (Size new_index = 0; new_index < order.size(); ++new_index) {
        old_to_new[static_cast<Size>(order[new_index])] = static_cast<Index>(new_index);
    }
    return old_to_new;
}

void write_svg_raster(const std::filesystem::path& path,
                      const CsrMatrix& matrix,
                      const std::vector<Index>* old_to_new,
                      int requested_bins,
                      const std::string& title,
                      const std::string& subtitle) {
    const int n = matrix.n_rows;
    const int bins = std::min(std::max(16, requested_bins), n);
    std::vector<unsigned char> image(static_cast<Size>(bins) * static_cast<Size>(bins), 0);
    Size occupied = 0;
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const Index display_row = old_to_new ? (*old_to_new)[static_cast<Size>(row)] : row;
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index display_col = old_to_new ? (*old_to_new)[static_cast<Size>(matrix.col_indices[p])] : matrix.col_indices[p];
            const int rb = std::min(bins - 1, static_cast<int>((static_cast<long long>(display_row) * bins) / std::max(1, n)));
            const int cb = std::min(bins - 1, static_cast<int>((static_cast<long long>(display_col) * bins) / std::max(1, n)));
            auto& pixel = image[static_cast<Size>(rb) * static_cast<Size>(bins) + static_cast<Size>(cb)];
            if (!pixel) {
                pixel = 1;
                ++occupied;
            }
        }
    }

    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write SVG raster: " + path.string());
    constexpr double canvas = 900.0;
    constexpr double margin_left = 92.0;
    constexpr double margin_top = 92.0;
    constexpr double plot = 760.0;
    const double cell = plot / static_cast<double>(bins);
    out << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << canvas << "\" height=\"" << canvas
        << "\" viewBox=\"0 0 " << canvas << ' ' << canvas << "\">\n";
    out << "<rect x=\"0\" y=\"0\" width=\"" << canvas << "\" height=\"" << canvas << "\" fill=\"white\"/>\n";
    out << "<text x=\"24\" y=\"34\" font-family=\"Arial, sans-serif\" font-size=\"24\" font-weight=\"700\" fill=\"#111827\">"
        << json_escape(title) << "</text>\n";
    out << "<text x=\"24\" y=\"58\" font-family=\"Arial, sans-serif\" font-size=\"14\" fill=\"#64748b\">"
        << json_escape(subtitle) << "</text>\n";
    out << "<rect x=\"" << margin_left << "\" y=\"" << margin_top << "\" width=\"" << plot << "\" height=\"" << plot
        << "\" fill=\"white\" stroke=\"#334155\" stroke-width=\"1.5\"/>\n";
    out << "<g fill=\"#111827\">\n";
    for (int r = 0; r < bins; ++r) {
        for (int c = 0; c < bins; ++c) {
            if (!image[static_cast<Size>(r) * static_cast<Size>(bins) + static_cast<Size>(c)]) continue;
            out << "<rect x=\"" << (margin_left + c * cell) << "\" y=\"" << (margin_top + r * cell)
                << "\" width=\"" << std::max(0.35, cell) << "\" height=\"" << std::max(0.35, cell) << "\"/>\n";
        }
    }
    out << "</g>\n";
    out << "<text x=\"" << margin_left << "\" y=\"874\" font-family=\"Arial, sans-serif\" font-size=\"13\" fill=\"#64748b\">"
        << "n=" << matrix.n_rows << ", nnz=" << matrix.nnz() << ", raster=" << bins << "x" << bins
        << ", occupied bins=" << occupied << "</text>\n";
    out << "</svg>\n";
}

void write_exact_window_csv(const std::filesystem::path& path,
                            const CsrMatrix& matrix,
                            int row_start,
                            int col_start,
                            int window_size) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write exact window CSV: " + path.string());
    const Index first_row = std::min<Index>(static_cast<Index>(row_start), matrix.n_rows);
    const Index last_row = std::min<Index>(matrix.n_rows, first_row + static_cast<Index>(window_size));
    const Index first_col = std::min<Index>(static_cast<Index>(col_start), matrix.n_cols);
    const Index last_col = std::min<Index>(matrix.n_cols, first_col + static_cast<Index>(window_size));
    out << "row,col\n";
    for (Index row = first_row; row < last_row; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index col = matrix.col_indices[p];
            if (col >= first_col && col < last_col) out << row << ',' << col << '\n';
        }
    }
}

void write_exact_window_svg(const std::filesystem::path& path,
                            const CsrMatrix& matrix,
                            int row_start,
                            int col_start,
                            int window_size,
                            const std::string& title) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write exact window SVG: " + path.string());
    const Index first_row = std::min<Index>(static_cast<Index>(row_start), matrix.n_rows);
    const Index last_row = std::min<Index>(matrix.n_rows, first_row + static_cast<Index>(window_size));
    const Index first_col = std::min<Index>(static_cast<Index>(col_start), matrix.n_cols);
    const Index last_col = std::min<Index>(matrix.n_cols, first_col + static_cast<Index>(window_size));
    const double rows = std::max<Index>(1, last_row - first_row);
    const double cols = std::max<Index>(1, last_col - first_col);
    constexpr double canvas = 900.0;
    constexpr double margin_left = 92.0;
    constexpr double margin_top = 92.0;
    constexpr double plot = 760.0;
    const double cell_x = plot / cols;
    const double cell_y = plot / rows;
    Size window_nnz = 0;

    out << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" << canvas << "\" height=\"" << canvas
        << "\" viewBox=\"0 0 " << canvas << ' ' << canvas << "\">\n";
    out << "<rect x=\"0\" y=\"0\" width=\"" << canvas << "\" height=\"" << canvas << "\" fill=\"white\"/>\n";
    out << "<text x=\"24\" y=\"34\" font-family=\"Arial, sans-serif\" font-size=\"24\" font-weight=\"700\" fill=\"#111827\">"
        << json_escape(title) << "</text>\n";
    out << "<text x=\"24\" y=\"58\" font-family=\"Arial, sans-serif\" font-size=\"14\" fill=\"#64748b\">"
        << "rows [" << first_row << "," << last_row << "), cols [" << first_col << "," << last_col
        << "), no binning</text>\n";
    out << "<rect x=\"" << margin_left << "\" y=\"" << margin_top << "\" width=\"" << plot << "\" height=\"" << plot
        << "\" fill=\"white\" stroke=\"#334155\" stroke-width=\"1.5\"/>\n";
    out << "<g fill=\"#111827\">\n";
    for (Index row = first_row; row < last_row; ++row) {
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const Index col = matrix.col_indices[p];
            if (col < first_col || col >= last_col) continue;
            ++window_nnz;
            out << "<rect x=\"" << (margin_left + static_cast<double>(col - first_col) * cell_x)
                << "\" y=\"" << (margin_top + static_cast<double>(row - first_row) * cell_y)
                << "\" width=\"" << std::max(0.75, cell_x)
                << "\" height=\"" << std::max(0.75, cell_y) << "\"/>\n";
        }
    }
    out << "</g>\n";
    out << "<text x=\"" << margin_left << "\" y=\"874\" font-family=\"Arial, sans-serif\" font-size=\"13\" fill=\"#64748b\">"
        << "window nnz=" << window_nnz << ", exact coordinates, no raster aggregation</text>\n";
    out << "</svg>\n";
}

int choose_dense_diagonal_window(const CsrMatrix& matrix, int window_size) {
    const int n = matrix.n_rows;
    const int width = std::max(1, window_size);
    const int blocks = (n + width - 1) / width;
    std::vector<Size> counts(static_cast<Size>(blocks), 0);
    for (Index row = 0; row < matrix.n_rows; ++row) {
        const int row_block = static_cast<int>(row) / width;
        const Size begin = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(matrix.row_offsets[static_cast<Size>(row) + 1]);
        for (Size p = begin; p < end; ++p) {
            const int col_block = static_cast<int>(matrix.col_indices[p]) / width;
            if (row_block == col_block) ++counts[static_cast<Size>(row_block)];
        }
    }
    Size best_count = 0;
    int best_block = 0;
    for (int b = 0; b < blocks; ++b) {
        if (counts[static_cast<Size>(b)] > best_count) {
            best_count = counts[static_cast<Size>(b)];
            best_block = b;
        }
    }
    return best_block * width;
}

void write_window_summary(const std::filesystem::path& path,
                          int row_start,
                          int col_start,
                          int window_size,
                          const std::string& note) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write exact window summary: " + path.string());
    out << "# Exact Sparse Window\n\n";
    out << "- Row window: `[" << row_start << ", " << row_start + window_size << ")`\n";
    out << "- Column window: `[" << col_start << ", " << col_start + window_size << ")`\n";
    out << "- Binning: `none`\n";
    out << "- Note: " << note << "\n";
}

void write_metadata(const std::filesystem::path& path,
                    const Config& cfg,
                    const Mesh& mesh,
                    const CsrMatrix& serial,
                    const CsrMatrix& parallel,
                    const MatrixError& error,
                    const VisualizationStats& visualization) {
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
        << "  },\n"
        << "  \"visualization\": {\n"
        << "    \"permutation_algorithm\": \"reverse_cuthill_mckee\",\n"
        << "    \"permutation_scope\": \"visualization_only\",\n"
        << "    \"original_bandwidth\": " << visualization.original_bandwidth << ",\n"
        << "    \"rcm_bandwidth\": " << visualization.rcm_bandwidth << ",\n"
        << "    \"rcm_nnz\": " << visualization.rcm_nnz << ",\n"
        << "    \"visualization_bins\": " << visualization.visualization_bins << ",\n"
        << "    \"exact_window\": {\n"
        << "      \"row_start\": " << visualization.exact_window_row_start << ",\n"
        << "      \"col_start\": " << visualization.exact_window_col_start << ",\n"
        << "      \"size\": " << visualization.exact_window_size << "\n"
        << "    },\n"
        << "    \"exact_window_auto\": {\n"
        << "      \"row_start\": " << visualization.exact_window_auto_row_start << ",\n"
        << "      \"col_start\": " << visualization.exact_window_auto_col_start << ",\n"
        << "      \"size\": " << visualization.exact_window_size << "\n"
        << "    }\n"
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
        if (!cfg.skip_full_patterns) {
            write_csv_pattern(out_dir / (cfg.prefix + "_serial_pattern.csv"), serial);
            write_csv_pattern(out_dir / (cfg.prefix + "_parallel_pattern.csv"), parallel);
            write_matrix_market_pattern(out_dir / (cfg.prefix + "_serial_pattern.mtx"), serial);
            write_matrix_market_pattern(out_dir / (cfg.prefix + "_parallel_pattern.mtx"), parallel);
        }
        write_csr_window(out_dir / (cfg.prefix + "_serial_csr_window.csv"),
                         serial,
                         cfg.csr_window_start,
                         cfg.csr_window_rows);
        write_csr_window(out_dir / (cfg.prefix + "_parallel_csr_window.csv"),
                         parallel,
                         cfg.csr_window_start,
                         cfg.csr_window_rows);
        write_csr_window_summary(out_dir / (cfg.prefix + "_serial_csr_window_summary.md"),
                                 serial,
                                 cfg.csr_window_start,
                                 cfg.csr_window_rows);
        const auto old_to_new = reverse_cuthill_mckee(serial);
        VisualizationStats visualization;
        visualization.original_bandwidth = matrix_bandwidth(serial);
        visualization.rcm_bandwidth = permuted_bandwidth(serial, old_to_new);
        visualization.rcm_nnz = serial.nnz();
        visualization.visualization_bins = std::min(std::max(16, cfg.visualization_bins), serial.n_rows);
        visualization.exact_window_row_start = cfg.exact_window_row_start;
        visualization.exact_window_col_start = cfg.exact_window_col_start;
        visualization.exact_window_size = cfg.exact_window_size;
        const int auto_window_start = choose_dense_diagonal_window(serial, cfg.exact_window_size);
        visualization.exact_window_auto_row_start = auto_window_start;
        visualization.exact_window_auto_col_start = auto_window_start;
        write_svg_raster(out_dir / (cfg.prefix + "_spy_original_raster.svg"),
                         serial,
                         nullptr,
                         cfg.visualization_bins,
                         "Original CSR sparse pattern",
                         "raw .inp node order; raster occupancy");
        write_svg_raster(out_dir / (cfg.prefix + "_spy_rcm_raster.svg"),
                         serial,
                         &old_to_new,
                         cfg.visualization_bins,
                         "RCM-reordered sparse pattern K(p,p)",
                         "reverse Cuthill-McKee; visualization only");
        write_exact_window_csv(out_dir / (cfg.prefix + "_exact_window_serial.csv"),
                               serial,
                               cfg.exact_window_row_start,
                               cfg.exact_window_col_start,
                               cfg.exact_window_size);
        write_exact_window_svg(out_dir / (cfg.prefix + "_exact_window_serial.svg"),
                               serial,
                               cfg.exact_window_row_start,
                               cfg.exact_window_col_start,
                               cfg.exact_window_size,
                               "Exact local sparse window");
        write_window_summary(out_dir / (cfg.prefix + "_exact_window_serial_summary.md"),
                             cfg.exact_window_row_start,
                             cfg.exact_window_col_start,
                             cfg.exact_window_size,
                             "Manual/global-coordinate window; each mark is a true nonzero coordinate.");
        write_exact_window_csv(out_dir / (cfg.prefix + "_exact_window_auto_serial.csv"),
                               serial,
                               auto_window_start,
                               auto_window_start,
                               cfg.exact_window_size);
        write_exact_window_svg(out_dir / (cfg.prefix + "_exact_window_auto_serial.svg"),
                               serial,
                               auto_window_start,
                               auto_window_start,
                               cfg.exact_window_size,
                               "Auto-selected exact sparse window");
        write_window_summary(out_dir / (cfg.prefix + "_exact_window_auto_serial_summary.md"),
                             auto_window_start,
                             auto_window_start,
                             cfg.exact_window_size,
                             "Auto-selected diagonal window with the densest in-window nonzero count.");
        write_metadata(out_dir / (cfg.prefix + "_metadata.json"), cfg, mesh, serial, parallel, error, visualization);

        std::cout << "pattern export complete: " << out_dir << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 1;
    }
}
