/**
 * @file dof_map.h
 * @brief 自由度映射
 *
 * 处理节点-自由度的映射关系
 */

#pragma once

#include "types.h"
#include <vector>

namespace fem {

/**
 * @brief 自由度映射器
 *
 * 将节点索引映射到全局自由度索引
 * 对于3D问题，每个节点有3个自由度 (x, y, z 位移)
 */
class DofMap {
public:
    /**
     * @brief 构造函数
     * @param num_nodes 节点总数
     * @param dofs_per_node 每个节点的自由度数（默认3）
     */
    DofMap(Size num_nodes = 0, int dofs_per_node = constants::DOFS_PER_NODE)
        : num_nodes_(num_nodes), dofs_per_node_(dofs_per_node) {}

    /**
     * @brief 设置节点数
     */
    void set_num_nodes(Size n) {
        num_nodes_ = n;
    }

    /**
     * @brief 获取节点数
     */
    Size num_nodes() const { return num_nodes_; }

    /**
     * @brief 获取总自由度数
     */
    Size num_dofs() const { return num_nodes_ * dofs_per_node_; }

    /**
     * @brief 获取每个节点的自由度数
     */
    int dofs_per_node() const { return dofs_per_node_; }

    /**
     * @brief 将节点索引和局部自由度索引转换为全局自由度索引
     *
     * @param node_idx 节点索引
     * @param local_dof 局部自由度索引 (0, 1, 2 对应 x, y, z)
     * @return 全局自由度索引
     */
    Index node_dof_to_global(Index node_idx, int local_dof) const {
        return node_idx * dofs_per_node_ + local_dof;
    }

    /**
     * @brief 将全局自由度索引转换为节点索引
     */
    Index global_to_node(Index global_dof) const {
        return global_dof / dofs_per_node_;
    }

    /**
     * @brief 将全局自由度索引转换为局部自由度索引
     */
    int global_to_local_dof(Index global_dof) const {
        return global_dof % dofs_per_node_;
    }

    /**
     * @brief 获取单元的全局自由度索引数组
     *
     * @param element_nodes 单元节点索引数组
     * @param num_nodes 单元节点数
     * @param[out] element_dofs 输出的全局自由度索引数组
     */
    void get_element_dofs(const Index* element_nodes, int num_nodes,
                          std::vector<Index>& element_dofs) const {
        element_dofs.resize(num_nodes * dofs_per_node_);
        for (int i = 0; i < num_nodes; ++i) {
            for (int d = 0; d < dofs_per_node_; ++d) {
                element_dofs[i * dofs_per_node_ + d] =
                    node_dof_to_global(element_nodes[i], d);
            }
        }
    }

    /**
     * @brief 获取单元局部自由度对应的全局自由度
     *
     * @param element_nodes 单元节点索引数组
     * @param local_dof_idx 单元内局部自由度索引 (0 到 num_nodes*dofs_per_node-1)
     * @return 全局自由度索引
     */
    Index local_to_global_dof(const Index* element_nodes, int local_dof_idx) const {
        int node_local = local_dof_idx / dofs_per_node_;
        int dof_local = local_dof_idx % dofs_per_node_;
        return node_dof_to_global(element_nodes[node_local], dof_local);
    }

private:
    Size num_nodes_ = 0;
    int dofs_per_node_ = constants::DOFS_PER_NODE;
};

}  // namespace fem
