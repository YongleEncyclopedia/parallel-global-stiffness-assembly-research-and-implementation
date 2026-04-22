#include "backends/cpu/private_csr_assembler.h"

#include <chrono>
#include <sstream>
#include <stdexcept>

namespace fem::cpu {

PrivateCsrAssembler::PrivateCsrAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void PrivateCsrAssembler::prepare() {
    ensure_ready();
    const auto t0 = std::chrono::steady_clock::now();
    const Size required = static_cast<Size>(threads()) * structure_->nnz() * sizeof(Real);
    if (required > options_.max_transient_bytes) {
        std::ostringstream os;
        os << "cpu_private_csr requires " << memory_string(required)
           << " transient memory, above limit " << memory_string(options_.max_transient_bytes);
        throw std::runtime_error(os.str());
    }
    private_values_.assign(static_cast<Size>(threads()) * structure_->nnz(), 0.0);
    stats_.extra_memory_bytes = required;
    const auto t1 = std::chrono::steady_clock::now();
    stats_.prepare_allocate_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.preprocess_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
}

void PrivateCsrAssembler::assemble() {
    ensure_ready();
    if (private_values_.empty()) prepare();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    std::fill(private_values_.begin(), private_values_.end(), 0.0);
    const auto t_zero = std::chrono::steady_clock::now();
    const Size ne = mesh_->num_elements();
    const Size nnz = structure_->nnz();
    const int nth = threads();

#ifdef _OPENMP
#pragma omp parallel num_threads(nth)
#endif
    {
        std::vector<Real> ke;
        const int tid = current_thread_id();
        Real* local = private_values_.data() + static_cast<Size>(tid) * nnz;
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
                    local[static_cast<Size>(scatter[i * edofs + j])] += ke[static_cast<Size>(i) * edofs + j];
                }
            }
        }
    }
    const auto t_numeric = std::chrono::steady_clock::now();

#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t pp = 0; pp < static_cast<std::int64_t>(nnz); ++pp) {
        const Size p = static_cast<Size>(pp);
        Real v = 0.0;
        for (int t = 0; t < nth; ++t) v += private_values_[static_cast<Size>(t) * nnz + p];
        result_.values[p] = v;
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_zero_ms = std::chrono::duration<double, std::milli>(t_zero - t0).count();
    stats_.assembly_numeric_ms = std::chrono::duration<double, std::milli>(t_numeric - t_zero).count();
    stats_.assembly_reduce_ms = std::chrono::duration<double, std::milli>(t1 - t_numeric).count();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
    stats_.diagnostics = "Thread-private CSR arrays followed by deterministic nnz-wise reduction";
}

void PrivateCsrAssembler::cleanup() {
    std::vector<Real>().swap(private_values_);
}

} // namespace fem::cpu
