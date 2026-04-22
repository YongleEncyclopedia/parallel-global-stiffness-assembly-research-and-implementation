#pragma once
#include "backends/cpu/cpu_assembler_base.h"

#include <cstdint>
#include <vector>

namespace fem::cpu {

struct RowOwnerTask {
    Index element = 0;
    std::uint8_t local_i = 0;
    std::uint8_t local_j = 0;
    Index csr_index = 0;
};

class RowOwnerAssembler final : public CpuAssemblerBase {
public:
    explicit RowOwnerAssembler(AssemblyOptions options);
    void prepare() override;
    void assemble() override;
    void cleanup() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_row_owner"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuRowOwner; }
private:
    std::vector<std::vector<RowOwnerTask>> tasks_by_owner_;
};
} // namespace fem::cpu
