#pragma once

#include "assembly/assembler_interface.h"
#include "assembly/assembly_options.h"

#include <vector>

namespace fem {

class AssemblerFactory {
public:
    static AssemblerPtr create(AlgorithmType algorithm,
                               const AssemblyOptions& options = AssemblyOptions());

    static AssemblerPtr create_serial(const AssemblyOptions& options = AssemblyOptions());
    static AssemblerPtr create_atomic(const AssemblyOptions& options = AssemblyOptions());
    static AssemblerPtr create_private_csr(const AssemblyOptions& options = AssemblyOptions());
    static AssemblerPtr create_coo_sort_reduce(const AssemblyOptions& options = AssemblyOptions());
    static AssemblerPtr create_graph_coloring(const AssemblyOptions& options = AssemblyOptions());
    static AssemblerPtr create_row_owner(const AssemblyOptions& options = AssemblyOptions());

    static std::vector<AlgorithmType> get_available_algorithms();
};

} // namespace fem
