/**
 * @file mesh.h
 * @brief 有限元网格数据结构
 *
 * 存储节点坐标、单元连接关系和网格拓扑信息
 */

#pragma once

#include "types.h"
#include "soa.h"
#include "dof_map.h"
#include "csr_matrix.h"
#include <string>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <set>

namespace fem {

/**
 * @brief 有限元网格类
 *
 * 存储网格的几何信息（节点坐标）和拓扑信息（单元连接）
 */
class Mesh {
public:
    NodeCoordinates nodes;       ///< 节点坐标（SoA布局）
    Connectivity connectivity;   ///< 单元连接表
    ElementType element_type;    ///< 单元类型
    DofMap dof_map;             ///< 自由度映射

    // ========================================================================
    // 构造与初始化
    // ========================================================================

    Mesh() : element_type(ElementType::Hex8) {}

    /**
     * @brief 从文件加载网格
     */
    void load_from_file(const std::string& filename);

    /**
     * @brief 保存网格到文件
     */
    void save_to_file(const std::string& filename) const;

    /**
     * @brief 生成结构化立方体网格（用于测试）
     *
     * @param nx x方向单元数
     * @param ny y方向单元数
     * @param nz z方向单元数
     * @param lx x方向长度
     * @param ly y方向长度
     * @param lz z方向长度
     * @param type 单元类型
     */
    void generate_cube_mesh(Size nx, Size ny, Size nz,
                           Real lx = 1.0, Real ly = 1.0, Real lz = 1.0,
                           ElementType type = ElementType::Hex8);

    // ========================================================================
    // 查询方法
    // ========================================================================

    Size num_nodes() const { return nodes.num_nodes(); }
    Size num_elements() const { return connectivity.num_elements; }
    Size num_dofs() const { return dof_map.num_dofs(); }
    int nodes_per_element() const { return fem::nodes_per_element(element_type); }
    int dofs_per_element() const { return fem::dofs_per_element(element_type); }

    /**
     * @brief 获取第 e 个单元的节点索引
     */
    const Index* element_nodes(Size e) const {
        return connectivity.element_nodes(e);
    }

    // ========================================================================
    // CSR 结构预计算
    // ========================================================================

    /**
     * @brief 预计算 CSR 矩阵结构（符号分析）
     *
     * 分析网格拓扑，确定刚度矩阵的稀疏模式
     * @return 初始化好结构的 CSR 矩阵（值为零）
     */
    CsrMatrix precompute_csr_structure() const;

private:
    /**
     * @brief 生成 Hex8 网格
     */
    void generate_hex8_mesh(Size nx, Size ny, Size nz, Real lx, Real ly, Real lz);

    /**
     * @brief 生成 Tet4 网格（通过分解 Hex8）
     */
    void generate_tet4_mesh(Size nx, Size ny, Size nz, Real lx, Real ly, Real lz);
};

// ============================================================================
// 内联实现
// ============================================================================

inline void Mesh::generate_cube_mesh(Size nx, Size ny, Size nz,
                                     Real lx, Real ly, Real lz,
                                     ElementType type) {
    element_type = type;

    if (type == ElementType::Hex8) {
        generate_hex8_mesh(nx, ny, nz, lx, ly, lz);
    } else {
        generate_tet4_mesh(nx, ny, nz, lx, ly, lz);
    }

    // 更新自由度映射
    dof_map.set_num_nodes(nodes.num_nodes());
}

inline void Mesh::generate_hex8_mesh(Size nx, Size ny, Size nz,
                                     Real lx, Real ly, Real lz) {
    // 节点数: (nx+1) * (ny+1) * (nz+1)
    Size num_nodes_x = nx + 1;
    Size num_nodes_y = ny + 1;
    Size num_nodes_z = nz + 1;
    Size total_nodes = num_nodes_x * num_nodes_y * num_nodes_z;

    // 生成节点
    nodes.clear();
    nodes.reserve(total_nodes);

    Real dx = lx / nx;
    Real dy = ly / ny;
    Real dz = lz / nz;

    for (Size k = 0; k < num_nodes_z; ++k) {
        for (Size j = 0; j < num_nodes_y; ++j) {
            for (Size i = 0; i < num_nodes_x; ++i) {
                nodes.add_node(i * dx, j * dy, k * dz);
            }
        }
    }

    // 单元数: nx * ny * nz
    Size total_elements = nx * ny * nz;
    connectivity.resize(total_elements, constants::HEX8_NODES_PER_ELEMENT);

    // 节点编号辅助函数
    auto node_index = [=](Size i, Size j, Size k) -> Index {
        return static_cast<Index>(i + j * num_nodes_x + k * num_nodes_x * num_nodes_y);
    };

    // 生成单元连接
    Size elem_idx = 0;
    for (Size k = 0; k < nz; ++k) {
        for (Size j = 0; j < ny; ++j) {
            for (Size i = 0; i < nx; ++i) {
                // Hex8 单元的8个节点（按标准编号）
                //     7-------6
                //    /|      /|
                //   4-------5 |
                //   | 3-----|-2
                //   |/      |/
                //   0-------1
                connectivity.set_node(elem_idx, 0, node_index(i,     j,     k    ));
                connectivity.set_node(elem_idx, 1, node_index(i + 1, j,     k    ));
                connectivity.set_node(elem_idx, 2, node_index(i + 1, j + 1, k    ));
                connectivity.set_node(elem_idx, 3, node_index(i,     j + 1, k    ));
                connectivity.set_node(elem_idx, 4, node_index(i,     j,     k + 1));
                connectivity.set_node(elem_idx, 5, node_index(i + 1, j,     k + 1));
                connectivity.set_node(elem_idx, 6, node_index(i + 1, j + 1, k + 1));
                connectivity.set_node(elem_idx, 7, node_index(i,     j + 1, k + 1));
                ++elem_idx;
            }
        }
    }
}

inline void Mesh::generate_tet4_mesh(Size nx, Size ny, Size nz,
                                     Real lx, Real ly, Real lz) {
    // 先生成 Hex8 网格的节点
    Size num_nodes_x = nx + 1;
    Size num_nodes_y = ny + 1;
    Size num_nodes_z = nz + 1;
    Size total_nodes = num_nodes_x * num_nodes_y * num_nodes_z;

    nodes.clear();
    nodes.reserve(total_nodes);

    Real dx = lx / nx;
    Real dy = ly / ny;
    Real dz = lz / nz;

    for (Size k = 0; k < num_nodes_z; ++k) {
        for (Size j = 0; j < num_nodes_y; ++j) {
            for (Size i = 0; i < num_nodes_x; ++i) {
                nodes.add_node(i * dx, j * dy, k * dz);
            }
        }
    }

    // 每个 Hex8 分解为 6 个 Tet4
    Size total_elements = nx * ny * nz * 6;
    connectivity.resize(total_elements, constants::TET4_NODES_PER_ELEMENT);

    auto node_index = [=](Size i, Size j, Size k) -> Index {
        return static_cast<Index>(i + j * num_nodes_x + k * num_nodes_x * num_nodes_y);
    };

    Size elem_idx = 0;
    for (Size k = 0; k < nz; ++k) {
        for (Size j = 0; j < ny; ++j) {
            for (Size i = 0; i < nx; ++i) {
                // Hex8 的 8 个节点
                Index n0 = node_index(i,     j,     k    );
                Index n1 = node_index(i + 1, j,     k    );
                Index n2 = node_index(i + 1, j + 1, k    );
                Index n3 = node_index(i,     j + 1, k    );
                Index n4 = node_index(i,     j,     k + 1);
                Index n5 = node_index(i + 1, j,     k + 1);
                Index n6 = node_index(i + 1, j + 1, k + 1);
                Index n7 = node_index(i,     j + 1, k + 1);

                // 分解为 6 个四面体（标准分解方案）
                // Tet 1: 0-1-3-4
                connectivity.set_node(elem_idx, 0, n0);
                connectivity.set_node(elem_idx, 1, n1);
                connectivity.set_node(elem_idx, 2, n3);
                connectivity.set_node(elem_idx, 3, n4);
                ++elem_idx;

                // Tet 2: 1-2-3-6
                connectivity.set_node(elem_idx, 0, n1);
                connectivity.set_node(elem_idx, 1, n2);
                connectivity.set_node(elem_idx, 2, n3);
                connectivity.set_node(elem_idx, 3, n6);
                ++elem_idx;

                // Tet 3: 1-4-5-6
                connectivity.set_node(elem_idx, 0, n1);
                connectivity.set_node(elem_idx, 1, n4);
                connectivity.set_node(elem_idx, 2, n5);
                connectivity.set_node(elem_idx, 3, n6);
                ++elem_idx;

                // Tet 4: 3-4-6-7
                connectivity.set_node(elem_idx, 0, n3);
                connectivity.set_node(elem_idx, 1, n4);
                connectivity.set_node(elem_idx, 2, n6);
                connectivity.set_node(elem_idx, 3, n7);
                ++elem_idx;

                // Tet 5: 1-3-4-6
                connectivity.set_node(elem_idx, 0, n1);
                connectivity.set_node(elem_idx, 1, n3);
                connectivity.set_node(elem_idx, 2, n4);
                connectivity.set_node(elem_idx, 3, n6);
                ++elem_idx;

                // Tet 6: (补充分解 - 确保完整覆盖)
                // 使用对角分解
                connectivity.set_node(elem_idx, 0, n0);
                connectivity.set_node(elem_idx, 1, n1);
                connectivity.set_node(elem_idx, 2, n4);
                connectivity.set_node(elem_idx, 3, n5);
                ++elem_idx;
            }
        }
    }
}

inline void Mesh::load_from_file(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw FemException("Cannot open mesh file: " + filename);
    }

    std::string line;

    // 读取头部
    std::getline(file, line);
    std::istringstream header(line);

    std::string type_str;
    Size num_nodes_in, num_elements_in;
    header >> type_str >> num_nodes_in >> num_elements_in;

    if (type_str == "Hex8") {
        element_type = ElementType::Hex8;
    } else if (type_str == "Tet4") {
        element_type = ElementType::Tet4;
    } else {
        throw FemException("Unknown element type: " + type_str);
    }

    // 读取节点
    nodes.resize(num_nodes_in);
    for (Size i = 0; i < num_nodes_in; ++i) {
        file >> nodes.x[i] >> nodes.y[i] >> nodes.z[i];
    }

    // 读取单元
    int npn = fem::nodes_per_element(element_type);
    connectivity.resize(num_elements_in, npn);
    for (Size e = 0; e < num_elements_in; ++e) {
        for (int n = 0; n < npn; ++n) {
            file >> connectivity.data[e * npn + n];
        }
    }

    dof_map.set_num_nodes(num_nodes_in);
}

inline void Mesh::save_to_file(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw FemException("Cannot create mesh file: " + filename);
    }

    // 写入头部
    file << element_type_to_string(element_type) << " "
         << num_nodes() << " " << num_elements() << "\n";

    // 写入节点
    file << std::scientific;
    for (Size i = 0; i < num_nodes(); ++i) {
        file << nodes.x[i] << " " << nodes.y[i] << " " << nodes.z[i] << "\n";
    }

    // 写入单元
    int npn = nodes_per_element();
    for (Size e = 0; e < num_elements(); ++e) {
        for (int n = 0; n < npn; ++n) {
            file << connectivity.data[e * npn + n];
            if (n < npn - 1) file << " ";
        }
        file << "\n";
    }
}

inline CsrMatrix Mesh::precompute_csr_structure() const {
    Size ndofs = num_dofs();
    CsrMatrix csr;

    // 使用 set 统计每行的非零列（去重）
    std::vector<std::set<Index>> row_cols(ndofs);

    int dpe = dofs_per_element();

    for (Size e = 0; e < num_elements(); ++e) {
        const Index* elem_nodes = element_nodes(e);

        // 获取该单元的所有全局自由度
        std::vector<Index> elem_dofs(dpe);
        for (int i = 0; i < nodes_per_element(); ++i) {
            for (int d = 0; d < constants::DOFS_PER_NODE; ++d) {
                elem_dofs[i * constants::DOFS_PER_NODE + d] =
                    dof_map.node_dof_to_global(elem_nodes[i], d);
            }
        }

        // 记录稀疏模式（行-列对）
        for (int i = 0; i < dpe; ++i) {
            Index row = elem_dofs[i];
            for (int j = 0; j < dpe; ++j) {
                Index col = elem_dofs[j];
                row_cols[row].insert(col);
            }
        }
    }

    // 构建 CSR 结构
    csr.num_rows = ndofs;
    csr.num_cols = ndofs;
    csr.row_ptr.resize(ndofs + 1);
    csr.row_ptr[0] = 0;

    for (Size i = 0; i < ndofs; ++i) {
        csr.row_ptr[i + 1] = csr.row_ptr[i] + static_cast<Index>(row_cols[i].size());
    }

    csr.nnz = csr.row_ptr[ndofs];
    csr.col_ind.resize(csr.nnz);
    csr.values.assign(csr.nnz, 0.0);

    // 填充列索引（已排序）
    for (Size i = 0; i < ndofs; ++i) {
        Index idx = csr.row_ptr[i];
        for (Index col : row_cols[i]) {
            csr.col_ind[idx++] = col;
        }
    }

    return csr;
}

}  // namespace fem

// 需要包含 set
#include <set>
