#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/element_kernels.h"
#include "core/platform.h"

#include <chrono>
#include <stdexcept>
#include <vector>

namespace fem::cpu {

class CpuAssemblerBase : public IAssembler {
public:
    explicit CpuAssemblerBase(AssemblyOptions options);
    ~CpuAssemblerBase() override = default;

    void set_problem(const Mesh& mesh, const CsrMatrix& csr_structure, const AssemblyPlan& plan) override;
    void prepare() override;
    void cleanup() override;
    [[nodiscard]] const CsrMatrix& get_result() const override;
    [[nodiscard]] CsrMatrix& get_result_mut() override;
    [[nodiscard]] AssemblyStats get_stats() const override;
    [[nodiscard]] bool uses_gpu() const override { return false; }

protected:
    const Mesh* mesh_ = nullptr;
    const CsrMatrix* structure_ = nullptr;
    const AssemblyPlan* plan_ = nullptr;
    AssemblyOptions options_;
    CsrMatrix result_;
    AssemblyStats stats_;

    void ensure_ready() const;
    void reset_result();
    void add_element_to_result(Size elem_id, const std::vector<Real>& ke);
    int threads() const;
};

} // namespace fem::cpu
