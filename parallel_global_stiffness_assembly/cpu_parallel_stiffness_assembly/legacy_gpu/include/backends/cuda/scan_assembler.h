/**
 * @file scan_assembler.h
 * @brief 前缀和分配组装器
 *
 * 算法3：基于前缀和的并行分配，两阶段策略减少冲突
 */

#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"
#include "core/soa.h"

namespace fem {

/**
 * @brief 前缀和组装器（GPU）
 *
 * 核心思想：两阶段策略
 * 1. 计数阶段：统计每单元对CSR的写入量
 * 2. 分配阶段：前缀和确定写入位置，无冲突填值
 */
class ScanAssembler : public IAssembler {
public:
    explicit ScanAssembler(const AssemblyOptions& options = AssemblyOptions());
    ~ScanAssembler() override;

    void set_mesh(const Mesh& mesh) override;
    void set_csr_structure(const CsrMatrix& csr) override;
    void prepare() override;
    void assemble() override;
    void cleanup() override;

    const CsrMatrix& get_result() const override { return host_result_; }
    CsrMatrix& get_result_mut() override { return host_result_; }
    AssemblyStats get_stats() const override { return stats_; }

    std::string get_name() const override { return "Prefix_Scan"; }
    AlgorithmType get_type() const override { return AlgorithmType::PrefixScan; }
    bool uses_gpu() const override { return true; }

private:
    AssemblyOptions options_;
    const Mesh* mesh_ = nullptr;
    CsrMatrix host_result_;
    AssemblyStats stats_;

    DeviceNodeCoordinates d_nodes_;
    DeviceConnectivity d_conn_;
    DeviceCsrMatrix d_csr_;

    bool prepared_ = false;
};

}  // namespace fem
