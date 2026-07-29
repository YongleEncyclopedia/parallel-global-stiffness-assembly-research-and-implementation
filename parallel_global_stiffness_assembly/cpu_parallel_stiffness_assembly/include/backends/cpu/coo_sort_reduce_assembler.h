// COO 排序归并后端：先收集单元贡献，再按全局位置排序并合并。
#pragma once
#include "backends/cpu/cpu_assembler_base.h"

namespace fem::cpu {
class CooSortReduceAssembler final : public CpuAssemblerBase {
public:
    explicit CooSortReduceAssembler(AssemblyOptions options);
    void prepare() override;
    void assemble() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_coo_sort_reduce"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuCooSortReduce; }
};
} // namespace fem::cpu
