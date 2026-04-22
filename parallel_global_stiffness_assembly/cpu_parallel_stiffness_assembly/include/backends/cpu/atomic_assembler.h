#pragma once
#include "backends/cpu/cpu_assembler_base.h"

namespace fem::cpu {
class AtomicAssembler final : public CpuAssemblerBase {
public:
    explicit AtomicAssembler(AssemblyOptions options);
    void assemble() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_atomic"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuAtomic; }
};
} // namespace fem::cpu
