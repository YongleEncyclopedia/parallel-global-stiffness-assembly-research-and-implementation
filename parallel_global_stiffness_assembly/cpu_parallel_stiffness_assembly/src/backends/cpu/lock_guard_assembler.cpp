#include "backends/cpu/lock_guard_assembler.h"

#include <chrono>

namespace fem::cpu {

LockGuardAssembler::LockGuardAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void LockGuardAssembler::prepare() {
    ensure_ready();
    const auto t0 = std::chrono::steady_clock::now();
    entry_mutex_count_ = structure_->nnz();
    entry_mutexes_ = std::make_unique<std::mutex[]>(entry_mutex_count_);
    stats_.extra_memory_bytes = entry_mutex_count_ * sizeof(std::mutex);
    const auto t1 = std::chrono::steady_clock::now();
    stats_.prepare_allocate_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.preprocess_time_ms = stats_.prepare_allocate_ms;
    stats_.diagnostics = "std::lock_guard<std::mutex>; granularity=per_entry";
}

void LockGuardAssembler::assemble() {
    ensure_ready();
    if (!entry_mutexes_) prepare();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    const Size ne = mesh_->num_elements();
    const int nth = threads();

#ifdef _OPENMP
#pragma omp parallel num_threads(nth)
#endif
    {
        std::vector<Real> ke;
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
                    const Size p = static_cast<Size>(scatter[i * edofs + j]);
                    const Real v = ke[static_cast<Size>(i) * edofs + j];
                    std::lock_guard<std::mutex> guard(entry_mutexes_[p]);
                    result_.values[p] += v;
                }
            }
        }
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_numeric_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.assembly_time_ms = stats_.assembly_numeric_ms;
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
    stats_.diagnostics = "std::lock_guard<std::mutex>; granularity=per_entry";
}

void LockGuardAssembler::cleanup() {
    entry_mutexes_.reset();
    entry_mutex_count_ = 0;
}

} // namespace fem::cpu
