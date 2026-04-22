#include "backends/cpu/graph_coloring_assembler.h"

#include <algorithm>
#include <chrono>
#include <sstream>

namespace fem::cpu {

GraphColoringAssembler::GraphColoringAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void GraphColoringAssembler::prepare() {
    ensure_ready();
    const auto t0 = std::chrono::steady_clock::now();
    const Size ne = mesh_->num_elements();
    std::vector<std::vector<Index>> node_to_elements(mesh_->num_nodes());
    for (Size e = 0; e < ne; ++e) {
        const auto& elem = mesh_->elements[e];
        for (int i = 0; i < elem.node_count; ++i) {
            node_to_elements[static_cast<Size>(elem.nodes[i])].push_back(static_cast<Index>(e));
        }
    }

    element_colors_.assign(ne, -1);
    std::vector<int> color_stamp;
    int stamp = 0;
    int color_count = 0;
    for (Size e = 0; e < ne; ++e) {
        ++stamp;
        const auto& elem = mesh_->elements[e];
        for (int i = 0; i < elem.node_count; ++i) {
            for (Index adj : node_to_elements[static_cast<Size>(elem.nodes[i])]) {
                if (adj < static_cast<Index>(e)) {
                    const int c = element_colors_[static_cast<Size>(adj)];
                    if (c >= 0) {
                        if (static_cast<Size>(c) >= color_stamp.size()) color_stamp.resize(static_cast<Size>(c) + 1, 0);
                        color_stamp[static_cast<Size>(c)] = stamp;
                    }
                }
            }
        }
        int chosen = 0;
        while (chosen < static_cast<int>(color_stamp.size()) && color_stamp[static_cast<Size>(chosen)] == stamp) ++chosen;
        element_colors_[e] = chosen;
        color_count = std::max(color_count, chosen + 1);
    }

    color_groups_.assign(static_cast<Size>(color_count), {});
    for (Size e = 0; e < ne; ++e) {
        color_groups_[static_cast<Size>(element_colors_[e])].push_back(static_cast<Index>(e));
    }
    stats_.colors = color_count;
    stats_.color_sizes.clear();
    stats_.color_sizes.reserve(color_groups_.size());
    for (const auto& group : color_groups_) stats_.color_sizes.push_back(group.size());
    stats_.extra_memory_bytes = element_colors_.size() * sizeof(int);
    for (const auto& group : color_groups_) stats_.extra_memory_bytes += group.size() * sizeof(Index);

    const auto t1 = std::chrono::steady_clock::now();
    stats_.prepare_coloring_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.preprocess_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::ostringstream os;
    os << "Greedy first-fit element coloring, colors=" << color_count;
    stats_.diagnostics = os.str();
}

void GraphColoringAssembler::assemble() {
    ensure_ready();
    if (color_groups_.empty()) prepare();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    const int nth = threads();

    for (const auto& group : color_groups_) {
        const Size group_size = group.size();
#ifdef _OPENMP
#pragma omp parallel num_threads(nth)
#endif
        {
            std::vector<Real> ke;
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
            for (std::int64_t ii = 0; ii < static_cast<std::int64_t>(group_size); ++ii) {
                const Size e = static_cast<Size>(group[static_cast<Size>(ii)]);
                compute_element_matrix(*mesh_, e, options_, ke);
                const int edofs = plan_->element_dof_count(e);
                const Index* scatter = plan_->element_scatter_ptr(e);
                for (int i = 0; i < edofs; ++i) {
                    for (int j = 0; j < edofs; ++j) {
                        result_.values[static_cast<Size>(scatter[i * edofs + j])] += ke[static_cast<Size>(i) * edofs + j];
                    }
                }
            }
        }
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_numeric_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
}

void GraphColoringAssembler::cleanup() {
    std::vector<int>().swap(element_colors_);
    std::vector<std::vector<Index>>().swap(color_groups_);
}

} // namespace fem::cpu
