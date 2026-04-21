/**
 * @file block_assembler.h
 * @brief 线程块并行组装器
 *
 * 算法2：基于线程块的并行组装，利用共享内存累加
 */

#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"
#include "core/soa.h"

namespace fem {

/**
 * @brief 线程块并行组装器（GPU）
 *
 * 核心思想：每个线程块负责一批单元，利用共享内存进行块内累加，
 * 减少全局内存原子操作
 */
class BlockAssembler : public IAssembler {
public:
    explicit BlockAssembler(const AssemblyOptions& options = AssemblyOptions());
    ~BlockAssembler() override;

    void set_mesh(const Mesh& mesh) override;
    void set_csr_structure(const CsrMatrix& csr) override;
    void prepare() override;
    void assemble() override;
    void cleanup() override;

    const CsrMatrix& get_result() const override { return host_result_; }
    CsrMatrix& get_result_mut() override { return host_result_; }
    AssemblyStats get_stats() const override { return stats_; }

    std::string get_name() const override { return "Block_Parallel"; }
    AlgorithmType get_type() const override { return AlgorithmType::Block; }
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
