/**
 * @file assembler_interface.h
 * @brief 组装器抽象接口
 *
 * 定义所有组装器必须实现的统一接口
 */

#pragma once

#include "core/types.h"
#include "core/mesh.h"
#include "core/csr_matrix.h"
#include <string>
#include <memory>

namespace fem {

/**
 * @brief 组装结果统计
 */
struct AssemblyStats {
    double assembly_time_ms = 0.0;      ///< 组装时间（毫秒）
    double total_time_ms = 0.0;         ///< 总时间（含数据传输）
    Size memory_usage_bytes = 0;        ///< 内存使用量
    Size num_elements_processed = 0;    ///< 处理的单元数
    Size num_dofs = 0;                  ///< 自由度数
    Size nnz = 0;                       ///< 非零元数量

    // GPU 特定统计
    double h2d_transfer_time_ms = 0.0;  ///< 主机到设备传输时间
    double d2h_transfer_time_ms = 0.0;  ///< 设备到主机传输时间
    double kernel_time_ms = 0.0;        ///< CUDA kernel 执行时间
};

/**
 * @brief 组装器抽象接口
 *
 * 所有组装算法必须实现此接口
 */
class IAssembler {
public:
    virtual ~IAssembler() = default;

    // ========================================================================
    // 配置
    // ========================================================================

    /**
     * @brief 设置网格数据
     */
    virtual void set_mesh(const Mesh& mesh) = 0;

    /**
     * @brief 设置 CSR 矩阵结构
     *
     * CSR 结构必须预先计算好，组装器只负责填充值
     */
    virtual void set_csr_structure(const CsrMatrix& csr) = 0;

    // ========================================================================
    // 核心操作
    // ========================================================================

    /**
     * @brief 准备组装（分配内存等）
     */
    virtual void prepare() = 0;

    /**
     * @brief 执行组装
     *
     * 核心组装操作，填充 CSR 矩阵的值
     */
    virtual void assemble() = 0;

    /**
     * @brief 清理资源
     */
    virtual void cleanup() = 0;

    // ========================================================================
    // 结果获取
    // ========================================================================

    /**
     * @brief 获取组装结果矩阵
     */
    virtual const CsrMatrix& get_result() const = 0;

    /**
     * @brief 获取可修改的结果矩阵引用
     */
    virtual CsrMatrix& get_result_mut() = 0;

    /**
     * @brief 获取组装统计信息
     */
    virtual AssemblyStats get_stats() const = 0;

    // ========================================================================
    // 算法信息
    // ========================================================================

    /**
     * @brief 获取算法名称
     */
    virtual std::string get_name() const = 0;

    /**
     * @brief 获取算法类型
     */
    virtual AlgorithmType get_type() const = 0;

    /**
     * @brief 是否使用 GPU
     */
    virtual bool uses_gpu() const = 0;
};

/**
 * @brief 组装器智能指针类型
 */
using AssemblerPtr = std::unique_ptr<IAssembler>;

}  // namespace fem
