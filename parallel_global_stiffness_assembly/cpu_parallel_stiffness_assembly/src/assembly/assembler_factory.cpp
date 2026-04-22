#include "assembly/assembler_factory.h"

#include "backends/cpu/atomic_assembler.h"
#include "backends/cpu/coo_sort_reduce_assembler.h"
#include "backends/cpu/graph_coloring_assembler.h"
#include "backends/cpu/private_csr_assembler.h"
#include "backends/cpu/row_owner_assembler.h"
#include "backends/cpu/serial_assembler.h"

#include <stdexcept>

namespace fem {

AssemblerPtr AssemblerFactory::create(AlgorithmType algorithm, const AssemblyOptions& options) {
    switch (algorithm) {
    case AlgorithmType::CpuSerial: return create_serial(options);
    case AlgorithmType::CpuAtomic: return create_atomic(options);
    case AlgorithmType::CpuPrivateCsr: return create_private_csr(options);
    case AlgorithmType::CpuCooSortReduce: return create_coo_sort_reduce(options);
    case AlgorithmType::CpuGraphColoring: return create_graph_coloring(options);
    case AlgorithmType::CpuRowOwner: return create_row_owner(options);
    }
    throw std::invalid_argument("Unsupported assembler type");
}

AssemblerPtr AssemblerFactory::create_serial(const AssemblyOptions& options) {
    return std::make_unique<cpu::SerialAssembler>(options);
}
AssemblerPtr AssemblerFactory::create_atomic(const AssemblyOptions& options) {
    return std::make_unique<cpu::AtomicAssembler>(options);
}
AssemblerPtr AssemblerFactory::create_private_csr(const AssemblyOptions& options) {
    return std::make_unique<cpu::PrivateCsrAssembler>(options);
}
AssemblerPtr AssemblerFactory::create_coo_sort_reduce(const AssemblyOptions& options) {
    return std::make_unique<cpu::CooSortReduceAssembler>(options);
}
AssemblerPtr AssemblerFactory::create_graph_coloring(const AssemblyOptions& options) {
    return std::make_unique<cpu::GraphColoringAssembler>(options);
}
AssemblerPtr AssemblerFactory::create_row_owner(const AssemblyOptions& options) {
    return std::make_unique<cpu::RowOwnerAssembler>(options);
}

std::vector<AlgorithmType> AssemblerFactory::get_available_algorithms() {
    return {AlgorithmType::CpuSerial,
            AlgorithmType::CpuAtomic,
            AlgorithmType::CpuPrivateCsr,
            AlgorithmType::CpuCooSortReduce,
            AlgorithmType::CpuGraphColoring,
            AlgorithmType::CpuRowOwner};
}

} // namespace fem
