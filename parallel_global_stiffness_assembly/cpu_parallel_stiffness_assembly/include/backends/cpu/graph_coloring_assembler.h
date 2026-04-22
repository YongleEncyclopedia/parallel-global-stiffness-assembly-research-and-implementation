#pragma once
#include "backends/cpu/cpu_assembler_base.h"

#include <vector>

namespace fem::cpu {
class GraphColoringAssembler final : public CpuAssemblerBase {
public:
    explicit GraphColoringAssembler(AssemblyOptions options);
    void prepare() override;
    void assemble() override;
    void cleanup() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_graph_coloring"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuGraphColoring; }
private:
    std::vector<int> element_colors_;
    std::vector<std::vector<Index>> color_groups_;
};
} // namespace fem::cpu
