/**
 * @file device_soa.h
 * @brief GPU-first 阶段的设备端 SoA 历史声明
 *
 * 本文件从当前 CPU 主线的 include/core/soa.h 迁出，仅供历史追溯。
 * legacy_gpu 不属于受支持构建目标，本文件不承诺可独立编译。
 */

#pragma once

#include "core/soa.h"

namespace fem {

/**
 * @brief 节点坐标的 SoA 布局（设备端）
 */
struct DeviceNodeCoordinates {
    Real* d_x = nullptr;  ///< 设备端 x 坐标指针
    Real* d_y = nullptr;  ///< 设备端 y 坐标指针
    Real* d_z = nullptr;  ///< 设备端 z 坐标指针
    Size count = 0;       ///< 节点数量

    void allocate_and_copy(const NodeCoordinates& host_data);
    void free();

    Size memory_usage_bytes() const {
        return count * sizeof(Real) * 3;
    }
};

/**
 * @brief 单元连接表的设备端存储
 */
struct DeviceConnectivity {
    Index* d_data = nullptr;
    Size num_elements = 0;
    int nodes_per_element = 0;

    void allocate_and_copy(const Connectivity& host_data);
    void free();

    Size memory_usage_bytes() const {
        return num_elements * nodes_per_element * sizeof(Index);
    }
};

}  // namespace fem
