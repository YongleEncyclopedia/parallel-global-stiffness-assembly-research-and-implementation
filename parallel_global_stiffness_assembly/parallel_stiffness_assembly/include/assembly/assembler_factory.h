/**
 * @file assembler_factory.h
 * @brief 组装器工厂类
 */

#pragma once

#include "assembler_interface.h"
#include "assembly_options.h"

namespace fem {

/**
 * @brief 组装器工厂
 *
 * 根据算法类型创建对应的组装器实例
 */
class AssemblerFactory {
public:
    /**
     * @brief 创建组装器
     *
     * @param algorithm 算法类型
     * @param options 组装选项
     * @return 组装器实例
     */
    static AssemblerPtr create(AlgorithmType algorithm,
                               const AssemblyOptions& options = AssemblyOptions());

    /**
     * @brief 创建 CPU 串行组装器
     */
    static AssemblerPtr create_serial();

    /**
     * @brief 创建原子操作组装器（GPU）
     */
    static AssemblerPtr create_atomic(const AssemblyOptions& options = AssemblyOptions());

    /**
     * @brief 创建线程块并行组装器（GPU）
     */
    static AssemblerPtr create_block(const AssemblyOptions& options = AssemblyOptions());

    /**
     * @brief 创建前缀和组装器（GPU）
     */
    static AssemblerPtr create_scan(const AssemblyOptions& options = AssemblyOptions());

    /**
     * @brief 创建工作队列组装器（GPU）
     */
    static AssemblerPtr create_workqueue(const AssemblyOptions& options = AssemblyOptions());

    /**
     * @brief 获取所有可用的算法类型
     */
    static std::vector<AlgorithmType> get_available_algorithms();
};

}  // namespace fem
