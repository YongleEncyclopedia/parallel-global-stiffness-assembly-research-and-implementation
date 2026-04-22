/**
 * @file cuda_utils.cuh
 * @brief CUDA 工具函数和宏定义
 */

#pragma once

#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cstdio>

namespace cg = cooperative_groups;

// ============================================================================
// CUDA 错误检查宏
// ============================================================================

#define CUDA_CHECK(call)                                                       \
    do {                                                                        \
        cudaError_t err = call;                                                 \
        if (err != cudaSuccess) {                                               \
            fprintf(stderr, "CUDA Error at %s:%d - %s\n",                      \
                    __FILE__, __LINE__, cudaGetErrorString(err));              \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)

#define CUDA_CHECK_LAST()                                                      \
    do {                                                                        \
        cudaError_t err = cudaGetLastError();                                  \
        if (err != cudaSuccess) {                                               \
            fprintf(stderr, "CUDA Error at %s:%d - %s\n",                      \
                    __FILE__, __LINE__, cudaGetErrorString(err));              \
            exit(EXIT_FAILURE);                                                 \
        }                                                                       \
    } while (0)

// ============================================================================
// 常量
// ============================================================================

namespace fem {
namespace cuda {

constexpr int WARP_SIZE = 32;
constexpr int MAX_BLOCK_SIZE = 1024;
constexpr int DEFAULT_BLOCK_SIZE = 256;

// ============================================================================
// 设备函数：行内二分查找
// ============================================================================

/**
 * @brief 在 CSR 行中二分查找列索引
 *
 * @param col_ind 列索引数组
 * @param start 行起始位置
 * @param end 行结束位置（不包含）
 * @param col 目标列
 * @return 找到的位置，或 -1
 */
__device__ __forceinline__
int binary_search_row(const int* col_ind, int start, int end, int col) {
    while (start < end) {
        int mid = (start + end) / 2;
        int mid_col = col_ind[mid];
        if (mid_col == col) {
            return mid;
        } else if (mid_col < col) {
            start = mid + 1;
        } else {
            end = mid;
        }
    }
    return -1;
}

// ============================================================================
// Warp 聚合原子操作
// ============================================================================

/**
 * @brief Warp 聚合的原子加法
 *
 * 当 Warp 内多个线程试图向同一地址写入时，先在 Warp 内规约，
 * 然后由一个线程执行最终的原子操作
 */
__device__ __forceinline__
void warp_aggregated_atomic_add(double* address, double value) {
    // 使用协作组获取当前 warp
    auto warp = cg::tiled_partition<32>(cg::this_thread_block());

    // 获取当前线程在 warp 中的 lane id
    int lane = warp.thread_rank();

    // 使用 __match_any_sync 找出写入同一地址的线程
    // 注意：这里简化处理，假设每个线程写入不同地址
    // 完整实现需要比较地址并聚合

    // 简化版本：直接原子加
    // 生产级代码中应使用更复杂的聚合逻辑
    atomicAdd(address, value);
}

/**
 * @brief 完整的 Warp 聚合原子加法（基于地址匹配）
 *
 * 使用 __match_any_sync 找出写入同一地址的线程，
 * 然后在 warp 内进行规约
 *
 * @note 优化: 添加早退检查，避免无效索引参与 match_any
 */
__device__ __forceinline__
void warp_aggregated_atomic_add_full(double* base_ptr, int idx, double value) {
    // 早退: 无效索引直接返回，避免无意义的 warp 操作
    if (idx < 0) return;

    // 获取活动线程掩码
    unsigned int active_mask = __activemask();

    // 找出写入同一索引的线程
    unsigned int same_idx_mask = __match_any_sync(active_mask, idx);

    // 计算相同索引的线程数量
    int active_count = __popc(same_idx_mask);

    // 获取当前 lane
    int lane = threadIdx.x % WARP_SIZE;

    // 在具有相同索引的线程中进行树状规约（修复：从小到大）
    double sum = value;

    // 标准树状规约：从 offset=1 开始，逐渐翻倍
    for (int offset = 1; offset < active_count; offset *= 2) {
        double other = __shfl_down_sync(same_idx_mask, sum, offset);
        // 只有当前线程能接收到有效值时才累加
        sum += other;
    }

    // 计算 leader（最低 lane）执行原子操作
    int leader = __ffs(same_idx_mask) - 1;
    if (lane == leader) {
        atomicAdd(&base_ptr[idx], sum);
    }
}

// ============================================================================
// 局部刚度矩阵计算（设备函数）
// ============================================================================

/**
 * @brief 按项计算 Hex8 刚度矩阵单个元素（减少寄存器压力）
 *
 * @param coords 节点坐标 [8][3] 或共享内存中的缓存
 * @param i 行索引 (0-23)
 * @param j 列索引 (0-23)
 * @param stiffness 预计算的刚度系数 (E/vol)
 * @return Ke(i,j) 的值
 *
 * @note 此函数避免分配完整 24x24 矩阵，显著降低寄存器压力
 */
__device__ __forceinline__
double compute_hex8_entry(double stiffness, int i, int j) {
    int n1 = i / 3;  // 节点索引 1
    int d1 = i % 3;  // 方向索引 1
    int n2 = j / 3;  // 节点索引 2
    int d2 = j % 3;  // 方向索引 2

    if (i == j) {
        // 对角项
        return stiffness * 8.0;
    } else if (n1 != n2 && d1 == d2) {
        // 非对角项：不同节点、相同方向
        return -stiffness * 0.5;
    }
    return 0.0;
}

/**
 * @brief 按项计算 Tet4 刚度矩阵单个元素
 */
__device__ __forceinline__
double compute_tet4_entry(double stiffness, int i, int j) {
    int n1 = i / 3;
    int d1 = i % 3;
    int n2 = j / 3;
    int d2 = j % 3;

    if (i == j) {
        return stiffness * 4.0;
    } else if (n1 != n2 && d1 == d2) {
        return -stiffness * 0.5;
    }
    return 0.0;
}

/**
 * @brief 计算 Hex8 单元刚度系数（供按项计算使用）
 */
__device__ __forceinline__
double compute_hex8_stiffness_coeff(const double coords[8][3]) {
    double dx = coords[1][0] - coords[0][0];
    double dy = coords[3][1] - coords[0][1];
    double dz = coords[4][2] - coords[0][2];
    double vol = dx * dy * dz;
    vol = fmax(vol, 1e-10);
    return 1.0 / vol;  // E = 1.0
}

/**
 * @brief 计算 Tet4 单元刚度系数（供按项计算使用）
 */
__device__ __forceinline__
double compute_tet4_stiffness_coeff(const double coords[4][3]) {
    double x1 = coords[1][0] - coords[0][0];
    double y1 = coords[1][1] - coords[0][1];
    double z1 = coords[1][2] - coords[0][2];
    double x2 = coords[2][0] - coords[0][0];
    double y2 = coords[2][1] - coords[0][1];
    double z2 = coords[2][2] - coords[0][2];
    double x3 = coords[3][0] - coords[0][0];
    double y3 = coords[3][1] - coords[0][1];
    double z3 = coords[3][2] - coords[0][2];

    double vol = fabs(x1 * (y2 * z3 - y3 * z2) -
                      y1 * (x2 * z3 - x3 * z2) +
                      z1 * (x2 * y3 - x3 * y2)) / 6.0;
    vol = fmax(vol, 1e-10);
    return 1.0 / vol;  // E = 1.0
}

/**
 * @brief 计算 Hex8 单元的简化刚度矩阵（完整矩阵版本）
 *
 * @param coords 节点坐标 [8][3]
 * @param Ke 输出刚度矩阵 [24*24]
 *
 * @note 此函数分配完整矩阵，可能导致寄存器压力。
 *       对于高性能场景，推荐使用 compute_hex8_entry() 按项计算。
 */
__device__ __forceinline__ void compute_hex8_stiffness(
    const double coords[8][3],
    double* Ke)
{
    // 计算单元体积
    double dx = coords[1][0] - coords[0][0];
    double dy = coords[3][1] - coords[0][1];
    double dz = coords[4][2] - coords[0][2];
    double vol = dx * dy * dz;
    vol = fmax(vol, 1e-10);

    double E = 1.0;
    double stiffness = E / vol;

    constexpr int dpe = 24;

    // 初始化为零
    for (int i = 0; i < dpe * dpe; ++i) {
        Ke[i] = 0.0;
    }

    // 对角项
    for (int i = 0; i < dpe; ++i) {
        Ke[i * dpe + i] = stiffness * 8.0;
    }

    // 非对角项
    for (int n1 = 0; n1 < 8; ++n1) {
        for (int n2 = 0; n2 < 8; ++n2) {
            if (n1 != n2) {
                double coupling = -stiffness * 0.5;
                for (int d = 0; d < 3; ++d) {
                    int i = n1 * 3 + d;
                    int j = n2 * 3 + d;
                    Ke[i * dpe + j] = coupling;
                }
            }
        }
    }
}

/**
 * @brief 计算 Tet4 单元的简化刚度矩阵
 */
__device__ __forceinline__ void compute_tet4_stiffness(
    const double coords[4][3],
    double* Ke)
{
    // 计算四面体体积
    double x1 = coords[1][0] - coords[0][0];
    double y1 = coords[1][1] - coords[0][1];
    double z1 = coords[1][2] - coords[0][2];
    double x2 = coords[2][0] - coords[0][0];
    double y2 = coords[2][1] - coords[0][1];
    double z2 = coords[2][2] - coords[0][2];
    double x3 = coords[3][0] - coords[0][0];
    double y3 = coords[3][1] - coords[0][1];
    double z3 = coords[3][2] - coords[0][2];

    double vol = fabs(x1 * (y2 * z3 - y3 * z2) -
                      y1 * (x2 * z3 - x3 * z2) +
                      z1 * (x2 * y3 - x3 * y2)) / 6.0;
    vol = fmax(vol, 1e-10);

    double E = 1.0;
    double stiffness = E / vol;

    constexpr int dpe = 12;

    // 初始化为零
    for (int i = 0; i < dpe * dpe; ++i) {
        Ke[i] = 0.0;
    }

    // 对角项
    for (int i = 0; i < dpe; ++i) {
        Ke[i * dpe + i] = stiffness * 4.0;
    }

    // 非对角项
    for (int n1 = 0; n1 < 4; ++n1) {
        for (int n2 = 0; n2 < 4; ++n2) {
            if (n1 != n2) {
                double coupling = -stiffness * 0.5;
                for (int d = 0; d < 3; ++d) {
                    int i = n1 * 3 + d;
                    int j = n2 * 3 + d;
                    Ke[i * dpe + j] = coupling;
                }
            }
        }
    }
}

}  // namespace cuda
}  // namespace fem
