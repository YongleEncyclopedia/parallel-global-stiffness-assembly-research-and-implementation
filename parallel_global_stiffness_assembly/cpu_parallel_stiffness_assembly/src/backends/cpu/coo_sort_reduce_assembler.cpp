#include "backends/cpu/coo_sort_reduce_assembler.h"

#include <algorithm>
#include <chrono>
#include <sstream>
#include <stdexcept>

namespace fem::cpu {
namespace {
struct CooContribution {
    Index csr_index = 0;
    Real value = 0.0;
};
} // namespace

CooSortReduceAssembler::CooSortReduceAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void CooSortReduceAssembler::prepare() {
    ensure_ready();
    Size entries = 0;
    for (const auto& elem : mesh_->elements) {
        const Size edofs = static_cast<Size>(elem.node_count * constants::DOFS_PER_NODE);
        entries += edofs * edofs;
    }
    const Size required = entries * sizeof(CooContribution);
    if (required > options_.max_transient_bytes) {
        std::ostringstream os;
        os << "cpu_coo_sort_reduce requires about " << memory_string(required)
           << " transient memory, above limit " << memory_string(options_.max_transient_bytes);
        throw std::runtime_error(os.str());
    }
    stats_.extra_memory_bytes = required;
    stats_.diagnostics = "Transient memory estimate only; vector is allocated during assemble()";
}

void CooSortReduceAssembler::assemble() {
    ensure_ready();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    const Size ne = mesh_->num_elements();
    const int nth = threads();
    std::vector<std::vector<CooContribution>> per_thread(static_cast<Size>(nth));

    Size total_entries = 0;
    for (const auto& elem : mesh_->elements) {
        const Size edofs = static_cast<Size>(elem.node_count * constants::DOFS_PER_NODE);
        total_entries += edofs * edofs;
    }
    const Size reserve_each = total_entries / static_cast<Size>(nth) + 1024;
    for (auto& v : per_thread) v.reserve(reserve_each);

#ifdef _OPENMP
#pragma omp parallel num_threads(nth)
#endif
    {
        std::vector<Real> ke;
        const int tid = current_thread_id();
        auto& local = per_thread[static_cast<Size>(tid)];
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
        for (std::int64_t ee = 0; ee < static_cast<std::int64_t>(ne); ++ee) {
            const Size e = static_cast<Size>(ee);
            compute_element_matrix(*mesh_, e, options_, ke);
            const int edofs = plan_->element_dof_count(e);
            const Index* scatter = plan_->element_scatter_ptr(e);
            for (int i = 0; i < edofs; ++i) {
                for (int j = 0; j < edofs; ++j) {
                    local.push_back(CooContribution{scatter[i * edofs + j], ke[static_cast<Size>(i) * edofs + j]});
                }
            }
        }
    }
    const auto t_generate = std::chrono::steady_clock::now();

    std::vector<CooContribution> all;
    all.reserve(total_entries);
    for (auto& v : per_thread) {
        all.insert(all.end(), std::make_move_iterator(v.begin()), std::make_move_iterator(v.end()));
        std::vector<CooContribution>().swap(v);
    }
    const auto t_merge = std::chrono::steady_clock::now();

    std::sort(all.begin(), all.end(), [](const auto& a, const auto& b) {
        return a.csr_index < b.csr_index;
    });
    const auto t_sort = std::chrono::steady_clock::now();

    Size p = 0;
    while (p < all.size()) {
        const Index idx = all[p].csr_index;
        Real sum = 0.0;
        do {
            sum += all[p].value;
            ++p;
        } while (p < all.size() && all[p].csr_index == idx);
        result_.values[static_cast<Size>(idx)] = sum;
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_generate_ms = std::chrono::duration<double, std::milli>(t_generate - t0).count();
    stats_.assembly_merge_ms = std::chrono::duration<double, std::milli>(t_merge - t_generate).count();
    stats_.assembly_sort_ms = std::chrono::duration<double, std::milli>(t_sort - t_merge).count();
    stats_.assembly_reduce_ms = std::chrono::duration<double, std::milli>(t1 - t_sort).count();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
    stats_.diagnostics = "Thread-local COO generation, global sort by CSR position, serial reduce";
}

} // namespace fem::cpu
