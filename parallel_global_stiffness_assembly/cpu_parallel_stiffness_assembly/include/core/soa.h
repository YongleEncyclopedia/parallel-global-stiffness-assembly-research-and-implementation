/**
 * @file soa.h
 * @brief SoA (Structure of Arrays) 内存布局
 *
 * 提供节点坐标的 SoA 布局以优化 GPU 内存访问
 */

#pragma once

#include "types.h"
#include <vector>

// CUDA 运行时只在 CUDA 编译时包含
#ifdef __CUDACC__
#include <cuda_runtime.h>
#endif

namespace fem {

/**
 * @brief 节点坐标的 SoA 布局（主机端）
 *
 * 将 x, y, z 坐标分开存储以实现 GPU 上的合并内存访问
 */
struct NodeCoordinates {
    std::vector<Real> x;  ///< 所有节点的 x 坐标
    std::vector<Real> y;  ///< 所有节点的 y 坐标
    std::vector<Real> z;  ///< 所有节点的 z 坐标

    Size num_nodes() const { return x.size(); }

    /**
     * @brief 调整大小
     */
    void resize(Size n) {
        x.resize(n);
        y.resize(n);
        z.resize(n);
    }

    /**
     * @brief 清空
     */
    void clear() {
        x.clear();
        y.clear();
        z.clear();
    }

    /**
     * @brief 预留空间
     */
    void reserve(Size n) {
        x.reserve(n);
        y.reserve(n);
        z.reserve(n);
    }

    /**
     * @brief 添加一个节点
     */
    void add_node(Real px, Real py, Real pz) {
        x.push_back(px);
        y.push_back(py);
        z.push_back(pz);
    }
};

/**
 * @brief 节点坐标的 SoA 布局（设备端）
 *
 * GPU 内存中的节点坐标存储
 */
struct DeviceNodeCoordinates {
    Real* d_x = nullptr;  ///< 设备端 x 坐标指针
    Real* d_y = nullptr;  ///< 设备端 y 坐标指针
    Real* d_z = nullptr;  ///< 设备端 z 坐标指针
    Size count = 0;       ///< 节点数量

    /**
     * @brief 从主机数据分配并复制
     */
    void allocate_and_copy(const NodeCoordinates& host_data);

    /**
     * @brief 释放设备内存
     */
    void free();

    /**
     * @brief 获取内存使用量（字节）
     */
    Size memory_usage_bytes() const {
        return count * sizeof(Real) * 3;
    }
};

/**
 * @brief 单元连接表的 SoA 布局（主机端）
 */
struct Connectivity {
    std::vector<Index> data;  ///< 连接数据 [num_elements * nodes_per_element]
    Size num_elements = 0;
    int nodes_per_element = 0;

    /**
     * @brief 获取第 e 个单元的第 i 个节点索引
     */
    Index get_node(Size e, int i) const {
        return data[e * nodes_per_element + i];
    }

    /**
     * @brief 设置第 e 个单元的第 i 个节点索引
     */
    void set_node(Size e, int i, Index node_idx) {
        data[e * nodes_per_element + i] = node_idx;
    }

    /**
     * @brief 获取第 e 个单元的连接数组起始指针
     */
    const Index* element_nodes(Size e) const {
        return data.data() + e * nodes_per_element;
    }

    /**
     * @brief 调整大小
     */
    void resize(Size n_elements, int n_nodes_per_elem) {
        num_elements = n_elements;
        nodes_per_element = n_nodes_per_elem;
        data.resize(n_elements * n_nodes_per_elem);
    }
};

/**
 * @brief 单元连接表的设备端存储
 */
struct DeviceConnectivity {
    Index* d_data = nullptr;
    Size num_elements = 0;
    int nodes_per_element = 0;

    /**
     * @brief 从主机数据分配并复制
     */
    void allocate_and_copy(const Connectivity& host_data);

    /**
     * @brief 释放设备内存
     */
    void free();

    /**
     * @brief 获取内存使用量（字节）
     */
    Size memory_usage_bytes() const {
        return num_elements * nodes_per_element * sizeof(Index);
    }
};

}  // namespace fem
