/**
 * @file serial_assembler.h
 * @brief CPU 串行组装器
 *
 * 作为正确性验证和加速比计算的基准
 */

#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"
#include <chrono>

namespace fem {

/**
 * @brief CPU 串行组装器
 *
 * 使用简单的串行算法组装刚度矩阵，作为基准参考
 */
class SerialAssembler : public IAssembler {
public:
    SerialAssembler() = default;
    ~SerialAssembler() override = default;

    // ========================================================================
    // IAssembler 接口实现
    // ========================================================================

    void set_mesh(const Mesh& mesh) override {
        mesh_ = &mesh;
    }

    void set_csr_structure(const CsrMatrix& csr) override {
        // 复制 CSR 结构
        result_ = csr;
    }

    void prepare() override {
        // CPU 版本无需特殊准备
        if (!mesh_) {
            throw FemException("Mesh not set");
        }
        stats_.num_dofs = mesh_->num_dofs();
        stats_.num_elements_processed = mesh_->num_elements();
        stats_.nnz = result_.nnz;
        stats_.memory_usage_bytes = result_.memory_usage_bytes();
    }

    void assemble() override;

    void cleanup() override {
        // 无需清理
    }

    const CsrMatrix& get_result() const override {
        return result_;
    }

    CsrMatrix& get_result_mut() override {
        return result_;
    }

    AssemblyStats get_stats() const override {
        return stats_;
    }

    std::string get_name() const override {
        return "CPU_Serial";
    }

    AlgorithmType get_type() const override {
        return AlgorithmType::CpuSerial;
    }

    bool uses_gpu() const override {
        return false;
    }

private:
    const Mesh* mesh_ = nullptr;
    CsrMatrix result_;
    AssemblyStats stats_;

    /**
     * @brief 计算 Hex8 单元的局部刚度矩阵
     */
    void compute_element_stiffness_hex8(Size elem_idx, std::vector<Real>& Ke) const;

    /**
     * @brief 计算 Tet4 单元的局部刚度矩阵
     */
    void compute_element_stiffness_tet4(Size elem_idx, std::vector<Real>& Ke) const;
};

// ============================================================================
// 实现
// ============================================================================

inline void SerialAssembler::assemble() {
    using Clock = std::chrono::high_resolution_clock;

    // 清零矩阵值
    result_.zero_values();

    auto start = Clock::now();

    int dpe = mesh_->dofs_per_element();
    std::vector<Real> Ke(dpe * dpe);
    std::vector<Index> elem_dofs(dpe);

    for (Size e = 0; e < mesh_->num_elements(); ++e) {
        // 计算局部刚度矩阵
        if (mesh_->element_type == ElementType::Hex8) {
            compute_element_stiffness_hex8(e, Ke);
        } else {
            compute_element_stiffness_tet4(e, Ke);
        }

        // 获取单元全局自由度
        const Index* nodes = mesh_->element_nodes(e);
        mesh_->dof_map.get_element_dofs(nodes, mesh_->nodes_per_element(), elem_dofs);

        // 组装到全局矩阵
        for (int i = 0; i < dpe; ++i) {
            Index row = elem_dofs[i];
            for (int j = 0; j < dpe; ++j) {
                Index col = elem_dofs[j];
                Real val = Ke[i * dpe + j];

                // 在 CSR 中找到位置并累加
                Index idx = result_.find_col_index(row, col);
                if (idx >= 0) {
                    result_.add_by_index(idx, val);
                }
            }
        }
    }

    auto end = Clock::now();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(end - start).count();
    stats_.total_time_ms = stats_.assembly_time_ms;
}

inline void SerialAssembler::compute_element_stiffness_hex8(Size elem_idx,
                                                           std::vector<Real>& Ke) const {
    // 简化的刚度矩阵计算（用于测试）
    // 实际应用中需要完整的高斯积分
    constexpr int dpe = constants::HEX8_DOFS_PER_ELEMENT;

    // 获取单元节点坐标
    const Index* nodes = mesh_->element_nodes(elem_idx);
    Real coords[8][3];
    for (int n = 0; n < 8; ++n) {
        Index node = nodes[n];
        coords[n][0] = mesh_->nodes.x[node];
        coords[n][1] = mesh_->nodes.y[node];
        coords[n][2] = mesh_->nodes.z[node];
    }

    // 计算单元特征尺寸（用于简化刚度计算）
    Real dx = coords[1][0] - coords[0][0];
    Real dy = coords[3][1] - coords[0][1];
    Real dz = coords[4][2] - coords[0][2];
    Real vol = dx * dy * dz;

    // 简化的刚度矩阵：对角占优的对称正定矩阵
    // K_ii = 刚度系数 * 体积
    // K_ij = -刚度系数 * 体积 / (邻接数) （相邻自由度）
    Real E = 1.0;  // 弹性模量（归一化）
    Real stiffness = E / vol;

    // 初始化为零
    std::fill(Ke.begin(), Ke.end(), 0.0);

    // 填充简化的刚度矩阵
    // 对角线
    for (int i = 0; i < dpe; ++i) {
        Ke[i * dpe + i] = stiffness * 8.0;  // 对角项
    }

    // 非对角项（节点间耦合）
    // 对于 Hex8，每个节点与相邻节点有耦合
    for (int n1 = 0; n1 < 8; ++n1) {
        for (int n2 = 0; n2 < 8; ++n2) {
            if (n1 != n2) {
                // 简化：所有节点对之间有弱耦合
                Real coupling = -stiffness * 0.5;
                for (int d = 0; d < 3; ++d) {
                    int i = n1 * 3 + d;
                    int j = n2 * 3 + d;
                    Ke[i * dpe + j] = coupling;
                }
            }
        }
    }
}

inline void SerialAssembler::compute_element_stiffness_tet4(Size elem_idx,
                                                           std::vector<Real>& Ke) const {
    constexpr int dpe = constants::TET4_DOFS_PER_ELEMENT;

    // 获取单元节点坐标
    const Index* nodes = mesh_->element_nodes(elem_idx);
    Real coords[4][3];
    for (int n = 0; n < 4; ++n) {
        Index node = nodes[n];
        coords[n][0] = mesh_->nodes.x[node];
        coords[n][1] = mesh_->nodes.y[node];
        coords[n][2] = mesh_->nodes.z[node];
    }

    // 计算四面体体积
    Real x1 = coords[1][0] - coords[0][0];
    Real y1 = coords[1][1] - coords[0][1];
    Real z1 = coords[1][2] - coords[0][2];
    Real x2 = coords[2][0] - coords[0][0];
    Real y2 = coords[2][1] - coords[0][1];
    Real z2 = coords[2][2] - coords[0][2];
    Real x3 = coords[3][0] - coords[0][0];
    Real y3 = coords[3][1] - coords[0][1];
    Real z3 = coords[3][2] - coords[0][2];

    Real vol = std::abs(x1 * (y2 * z3 - y3 * z2) -
                        y1 * (x2 * z3 - x3 * z2) +
                        z1 * (x2 * y3 - x3 * y2)) / 6.0;

    vol = std::max(vol, 1e-10);  // 避免除零

    Real E = 1.0;
    Real stiffness = E / vol;

    // 初始化为零
    std::fill(Ke.begin(), Ke.end(), 0.0);

    // 填充简化的刚度矩阵
    for (int i = 0; i < dpe; ++i) {
        Ke[i * dpe + i] = stiffness * 4.0;
    }

    for (int n1 = 0; n1 < 4; ++n1) {
        for (int n2 = 0; n2 < 4; ++n2) {
            if (n1 != n2) {
                Real coupling = -stiffness * 0.5;
                for (int d = 0; d < 3; ++d) {
                    int i = n1 * 3 + d;
                    int j = n2 * 3 + d;
                    Ke[i * dpe + j] = coupling;
                }
            }
        }
    }
}

}  // namespace fem
