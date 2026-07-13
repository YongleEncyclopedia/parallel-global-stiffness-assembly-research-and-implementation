#include "csc3_demo/assembly_helper.h"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    try {
        using namespace csc3_demo;
        SymmetricCscAssembler assembler;
        assembler.build_symbolic_parallel(ElementDofMap{{0}, {0, 2}, {0, 1}}, 2);
        assembler.assemble_numeric_atomic(ElementMatrixBatch{{0, 4}, {2.0, -1.0, -1.0, 2.0}}, 2);

        if (!openmp_enabled() || assembler.symbolic_thread_count_used() != 2 ||
            assembler.numeric_thread_count_used() != 2 ||
            assembler.matrix().values != std::vector<double>{2.0, -1.0, 2.0}) {
            throw std::runtime_error("external consumer integration failed");
        }
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
