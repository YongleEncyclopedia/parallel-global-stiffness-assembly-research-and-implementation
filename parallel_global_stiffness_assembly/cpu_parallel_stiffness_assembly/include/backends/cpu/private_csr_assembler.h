#pragma once
#include "backends/cpu/cpu_assembler_base.h"

namespace fem::cpu {
class PrivateCsrAssembler final : public CpuAssemblerBase {
public:
    explicit PrivateCsrAssembler(AssemblyOptions options);
    void prepare() override;
    void assemble() override;
    void cleanup() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_private_csr"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuPrivateCsr; }
private:
    std::vector<Real> private_values_;
};
} // namespace fem::cpu
