#include "backends/cpu/row_owner_assembler.h"

#include <algorithm>
#include <chrono>
#include <sstream>
#include <stdexcept>

namespace fem::cpu {

RowOwnerAssembler::RowOwnerAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void RowOwnerAssembler::prepare() {
    ensure_ready();
    const auto t0 = std::chrono::steady_clock::now();
    const int nth = threads();
    Size tasks = 0;
    for (const auto& elem : mesh_->elements) {
        const Size edofs = static_cast<Size>(elem.node_count * constants::DOFS_PER_NODE);
        tasks += edofs * edofs;
    }
    const Size required = tasks * sizeof(RowOwnerTask);
    if (required > options_.max_transient_bytes) {
        std::ostringstream os;
        os << "cpu_row_owner requires about " << memory_string(required)
           << " transient memory, above limit " << memory_string(options_.max_transient_bytes);
        throw std::runtime_error(os.str());
    }

    tasks_by_owner_.assign(static_cast<Size>(nth), {});
    for (auto& v : tasks_by_owner_) v.reserve(tasks / static_cast<Size>(nth) + 1024);
    const Index nrows = structure_->n_rows;
    for (Size e = 0; e < mesh_->num_elements(); ++e) {
        const int edofs = plan_->element_dof_count(e);
        const Index* dofs = plan_->element_dofs_ptr(e);
        const Index* scatter = plan_->element_scatter_ptr(e);
        for (int i = 0; i < edofs; ++i) {
            const int owner = std::min(nth - 1, static_cast<int>((static_cast<long long>(dofs[i]) * nth) / std::max<Index>(1, nrows)));
            auto& bucket = tasks_by_owner_[static_cast<Size>(owner)];
            for (int j = 0; j < edofs; ++j) {
                bucket.push_back(RowOwnerTask{static_cast<Index>(e),
                                              static_cast<std::uint8_t>(i),
                                              static_cast<std::uint8_t>(j),
                                              scatter[i * edofs + j]});
            }
        }
    }
    for (auto& bucket : tasks_by_owner_) {
        std::sort(bucket.begin(), bucket.end(), [](const auto& a, const auto& b) {
            if (a.element != b.element) return a.element < b.element;
            if (a.local_i != b.local_i) return a.local_i < b.local_i;
            return a.local_j < b.local_j;
        });
    }
    stats_.extra_memory_bytes = required;
    const auto t1 = std::chrono::steady_clock::now();
    stats_.prepare_owner_partition_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.preprocess_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.diagnostics = "Owner-computes by CSR row block; no atomics, but elements may be recomputed by multiple owners";
}

void RowOwnerAssembler::assemble() {
    ensure_ready();
    if (tasks_by_owner_.empty()) prepare();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    const int nth = threads();

#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (int owner = 0; owner < nth; ++owner) {
        const auto& tasks = tasks_by_owner_[static_cast<Size>(owner)];
        std::vector<Real> ke;
        Index current_element = -1;
        int current_edofs = 0;
        for (const auto& task : tasks) {
            if (task.element != current_element) {
                current_element = task.element;
                compute_element_matrix(*mesh_, static_cast<Size>(task.element), options_, ke);
                current_edofs = plan_->element_dof_count(static_cast<Size>(task.element));
            }
            result_.values[static_cast<Size>(task.csr_index)] +=
                ke[static_cast<Size>(task.local_i) * current_edofs + task.local_j];
        }
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_numeric_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
}

void RowOwnerAssembler::cleanup() {
    std::vector<std::vector<RowOwnerTask>>().swap(tasks_by_owner_);
}

} // namespace fem::cpu
