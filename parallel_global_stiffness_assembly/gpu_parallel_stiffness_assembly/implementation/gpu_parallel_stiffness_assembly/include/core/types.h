/**
 * @file types.h
 * @brief 基础类型定义
 *
 * 定义项目中使用的基本数据类型和常量
 */

#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <string>
#include <memory>
#include <stdexcept>

namespace fem {

// ============================================================================
// 基本数值类型
// ============================================================================

using Real = double;        // 默认使用双精度
using Index = int32_t;      // 索引类型（与CUDA兼容）
using Size = size_t;        // 大小类型

// ============================================================================
// 常量定义
// ============================================================================

namespace constants {
    // 每个节点的自由度数（3D问题：x, y, z位移）
    constexpr int DOFS_PER_NODE = 3;

    // Hex8 单元参数
    constexpr int HEX8_NODES_PER_ELEMENT = 8;
    constexpr int HEX8_DOFS_PER_ELEMENT = HEX8_NODES_PER_ELEMENT * DOFS_PER_NODE;  // 24

    // Tet4 单元参数
    constexpr int TET4_NODES_PER_ELEMENT = 4;
    constexpr int TET4_DOFS_PER_ELEMENT = TET4_NODES_PER_ELEMENT * DOFS_PER_NODE;  // 12

    // 数值容差
    constexpr Real TOLERANCE = 1e-10;
}

// ============================================================================
// 枚举类型
// ============================================================================

/**
 * @brief 单元类型枚举
 */
enum class ElementType {
    Hex8,   // 8节点六面体单元
    Tet4    // 4节点四面体单元
};

/**
 * @brief 将单元类型转换为字符串
 */
inline std::string element_type_to_string(ElementType type) {
    switch (type) {
        case ElementType::Hex8: return "Hex8";
        case ElementType::Tet4: return "Tet4";
        default: return "Unknown";
    }
}

/**
 * @brief 获取单元的节点数
 */
inline int nodes_per_element(ElementType type) {
    switch (type) {
        case ElementType::Hex8: return constants::HEX8_NODES_PER_ELEMENT;
        case ElementType::Tet4: return constants::TET4_NODES_PER_ELEMENT;
        default: throw std::invalid_argument("Unknown element type");
    }
}

/**
 * @brief 获取单元的自由度数
 */
inline int dofs_per_element(ElementType type) {
    return nodes_per_element(type) * constants::DOFS_PER_NODE;
}

/**
 * @brief 算法类型枚举
 */
enum class AlgorithmType {
    CpuSerial,      // CPU 串行基线
    Atomic,         // 原子操作 + Warp 聚合
    Block,          // 线程块并行
    PrefixScan,     // 前缀和分配
    WorkQueue       // 工作队列动态负载均衡
};

/**
 * @brief 将算法类型转换为字符串
 */
inline std::string algorithm_to_string(AlgorithmType type) {
    switch (type) {
        case AlgorithmType::CpuSerial:  return "CPU_Serial";
        case AlgorithmType::Atomic:     return "Atomic_WarpAgg";
        case AlgorithmType::Block:      return "Block_Parallel";
        case AlgorithmType::PrefixScan: return "Prefix_Scan";
        case AlgorithmType::WorkQueue:  return "Work_Queue";
        default: return "Unknown";
    }
}

// ============================================================================
// 异常类型
// ============================================================================

/**
 * @brief FEM 异常基类
 */
class FemException : public std::runtime_error {
public:
    explicit FemException(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief CUDA 错误异常
 */
class CudaException : public FemException {
public:
    explicit CudaException(const std::string& msg) : FemException("CUDA Error: " + msg) {}
};

}  // namespace fem
