#include "backends/cpu/cpu_assembler_base.h"

namespace fem::cpu {

CpuAssemblerBase::CpuAssemblerBase(AssemblyOptions options) : options_(options) {
    options_.threads = effective_thread_count(options_.threads);
}

void CpuAssemblerBase::set_problem(const Mesh& mesh, const CsrMatrix& csr_structure, const AssemblyPlan& plan) {
    mesh_ = &mesh;
    structure_ = &csr_structure;
    plan_ = &plan;
    result_ = csr_structure;
    result_.zero_values();
    stats_ = {};
    stats_.num_elements_processed = mesh.num_elements();
    stats_.num_dofs = mesh.num_dofs();
    stats_.nnz = csr_structure.nnz();
    stats_.memory_usage_bytes = csr_structure.bytes() + plan.bytes();
}

void CpuAssemblerBase::prepare() {}

void CpuAssemblerBase::cleanup() {}

const CsrMatrix& CpuAssemblerBase::get_result() const { return result_; }
CsrMatrix& CpuAssemblerBase::get_result_mut() { return result_; }
AssemblyStats CpuAssemblerBase::get_stats() const { return stats_; }

void CpuAssemblerBase::ensure_ready() const {
    if (!mesh_ || !structure_ || !plan_) {
        throw std::runtime_error("Assembler problem is not initialized");
    }
}

void CpuAssemblerBase::reset_result() {
    result_ = *structure_;
    result_.zero_values();
}

void CpuAssemblerBase::add_element_to_result(Size elem_id, const std::vector<Real>& ke) {
    const int edofs = plan_->element_dof_count(elem_id);
    const Index* scatter = plan_->element_scatter_ptr(elem_id);
    for (int i = 0; i < edofs; ++i) {
        for (int j = 0; j < edofs; ++j) {
            result_.values[static_cast<Size>(scatter[i * edofs + j])] += ke[static_cast<Size>(i) * edofs + j];
        }
    }
}

int CpuAssemblerBase::threads() const { return effective_thread_count(options_.threads); }

} // namespace fem::cpu
