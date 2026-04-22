#include "backends/cpu/atomic_assembler.h"

#include <chrono>

namespace fem::cpu {

AtomicAssembler::AtomicAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void AtomicAssembler::assemble() {
    ensure_ready();
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
#ifdef _OPENMP
#pragma omp atomic update
#endif
                    result_.values[p] += v;
                }
            }
        }
    }

    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_numeric_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
    stats_.diagnostics = "OpenMP atomic AddTo over precomputed CSR scatter addresses";
}

} // namespace fem::cpu
