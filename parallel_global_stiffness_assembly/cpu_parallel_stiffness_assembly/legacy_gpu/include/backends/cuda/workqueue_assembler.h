/**
 * @file workqueue_assembler.h
 * @brief 工作队列动态负载均衡组装器
 *
 * 算法4：基于工作队列的动态负载均衡
 */

#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"
#include "core/soa.h"

namespace fem {

/**
 * @brief 工作队列组装器（GPU）
 *
 * 核心思想：使用全局任务队列，线程动态领取任务，
 * 解决 Hex8/Tet4 混合网格的负载不均问题
 */
class WorkQueueAssembler : public IAssembler {
public:
    explicit WorkQueueAssembler(const AssemblyOptions& options = AssemblyOptions());
    ~WorkQueueAssembler() override;

    void set_mesh(const Mesh& mesh) override;
    void set_csr_structure(const CsrMatrix& csr) override;
    void prepare() override;
    void assemble() override;
    void cleanup() override;

    const CsrMatrix& get_result() const override { return host_result_; }
    CsrMatrix& get_result_mut() override { return host_result_; }
    AssemblyStats get_stats() const override { return stats_; }

    std::string get_name() const override { return "Work_Queue"; }
    AlgorithmType get_type() const override { return AlgorithmType::WorkQueue; }
    bool uses_gpu() const override { return true; }

private:
    AssemblyOptions options_;
    const Mesh* mesh_ = nullptr;
    CsrMatrix host_result_;
    AssemblyStats stats_;

    DeviceNodeCoordinates d_nodes_;
    DeviceConnectivity d_conn_;
    DeviceCsrMatrix d_csr_;

    // 工作队列相关
    int* d_work_counter_ = nullptr;

    bool prepared_ = false;
};

}  // namespace fem
