/**
 * @file atomic_assembler.h
 * @brief 原子操作 + Warp 聚合组装器
 *
 * 算法1：基于原子操作的并行累加，结合 Warp 聚合优化
 */

#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"
#include "core/soa.h"

namespace fem {

/**
 * @brief 原子操作组装器（GPU）
 *
 * 核心思想：每个线程处理一个单元，计算局部刚度矩阵后
 * 通过原子操作累加到全局 CSR 矩阵。结合 Warp 聚合减少原子冲突。
 */
class AtomicAssembler : public IAssembler {
public:
    explicit AtomicAssembler(const AssemblyOptions& options = AssemblyOptions());
    ~AtomicAssembler() override;

    // IAssembler 接口
    void set_mesh(const Mesh& mesh) override;
    void set_csr_structure(const CsrMatrix& csr) override;
    void prepare() override;
    void assemble() override;
    void cleanup() override;

    const CsrMatrix& get_result() const override { return host_result_; }
    CsrMatrix& get_result_mut() override { return host_result_; }
    AssemblyStats get_stats() const override { return stats_; }

    std::string get_name() const override { return "Atomic_WarpAgg"; }
    AlgorithmType get_type() const override { return AlgorithmType::Atomic; }
    bool uses_gpu() const override { return true; }

private:
    AssemblyOptions options_;
    const Mesh* mesh_ = nullptr;
    CsrMatrix host_result_;
    AssemblyStats stats_;

    // 设备端数据
    DeviceNodeCoordinates d_nodes_;
    DeviceConnectivity d_conn_;
    DeviceCsrMatrix d_csr_;

    bool prepared_ = false;

    void launch_hex8_kernel();
    void launch_tet4_kernel();
};

}  // namespace fem
