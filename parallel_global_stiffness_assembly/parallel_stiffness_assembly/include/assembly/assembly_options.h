/**
 * @file assembly_options.h
 * @brief 组装选项配置
 */

#pragma once

#include "core/types.h"

namespace fem {

/**
 * @brief 组装配置选项
 */
struct AssemblyOptions {
    // 算法选择
    AlgorithmType algorithm = AlgorithmType::Atomic;

    // CUDA 选项
    int cuda_device_id = 0;              ///< CUDA 设备 ID
    int block_size = 256;                ///< CUDA 线程块大小
    bool use_warp_aggregation = true;    ///< 是否使用 Warp 聚合

    // 前缀和算法选项
    bool use_thrust_scan = true;         ///< 使用 Thrust 进行前缀和

    // 工作队列选项
    int work_queue_chunk_size = 32;      ///< 工作队列任务粒度

    // 调试选项
    bool verbose = false;                ///< 详细输出
    bool verify_result = false;          ///< 是否验证结果

    // 计时选项
    int warmup_runs = 2;                 ///< 预热运行次数
    int benchmark_runs = 5;              ///< 基准测试运行次数
};

}  // namespace fem
