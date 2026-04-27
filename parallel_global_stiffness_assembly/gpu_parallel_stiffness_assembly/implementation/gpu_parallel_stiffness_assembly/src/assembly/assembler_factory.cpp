/**
 * @file assembler_factory.cpp
 * @brief 组装器工厂实现
 */

#include "assembly/assembler_factory.h"
#include "backends/cpu/serial_assembler.h"
#include "backends/cuda/atomic_assembler.h"
#include "backends/cuda/block_assembler.h"
#include "backends/cuda/scan_assembler.h"
#include "backends/cuda/workqueue_assembler.h"

namespace fem {

AssemblerPtr AssemblerFactory::create(AlgorithmType algorithm,
                                      const AssemblyOptions& options) {
    switch (algorithm) {
        case AlgorithmType::CpuSerial:
            return create_serial();
        case AlgorithmType::Atomic:
            return create_atomic(options);
        case AlgorithmType::Block:
            return create_block(options);
        case AlgorithmType::PrefixScan:
            return create_scan(options);
        case AlgorithmType::WorkQueue:
            return create_workqueue(options);
        default:
            throw FemException("Unknown algorithm type");
    }
}

AssemblerPtr AssemblerFactory::create_serial() {
    return std::make_unique<SerialAssembler>();
}

AssemblerPtr AssemblerFactory::create_atomic(const AssemblyOptions& options) {
    return std::make_unique<AtomicAssembler>(options);
}

AssemblerPtr AssemblerFactory::create_block(const AssemblyOptions& options) {
    return std::make_unique<BlockAssembler>(options);
}

AssemblerPtr AssemblerFactory::create_scan(const AssemblyOptions& options) {
    return std::make_unique<ScanAssembler>(options);
}

AssemblerPtr AssemblerFactory::create_workqueue(const AssemblyOptions& options) {
    return std::make_unique<WorkQueueAssembler>(options);
}

std::vector<AlgorithmType> AssemblerFactory::get_available_algorithms() {
    return {
        AlgorithmType::CpuSerial,
        AlgorithmType::Atomic,
        AlgorithmType::Block,
        // AlgorithmType::PrefixScan,  // DISABLED: incomplete two-phase implementation
        AlgorithmType::WorkQueue
    };
}

}  // namespace fem
