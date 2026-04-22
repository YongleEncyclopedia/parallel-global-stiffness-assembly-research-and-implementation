#pragma once
#include "backends/cpu/cpu_assembler_base.h"

namespace fem::cpu {
class SerialAssembler final : public CpuAssemblerBase {
public:
    explicit SerialAssembler(AssemblyOptions options);
    void assemble() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_serial"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuSerial; }
};
} // namespace fem::cpu
