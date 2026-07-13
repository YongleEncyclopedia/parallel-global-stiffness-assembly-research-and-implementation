#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <exception>
#include <iostream>

int main() {
    try {
        const csc3_demo::ElementDofMap topology{
            {20, 10},
            {0, 2, 4},
            {1, 2, 0, 1},
        };
        const csc3_demo::ElementMatrixBatch matrices{
            {0, 4, 8},
            {
                2.0,
                -1.0,
                -1.0,
                2.0,
                3.0,
                -2.0,
                -2.0,
                3.0,
            },
        };

        const int thread_count = std::max(1, std::min(4, csc3_demo::max_openmp_threads()));
        csc3_demo::SymmetricCscAssembler assembler;
        assembler.build_symbolic_parallel(topology, thread_count);
        assembler.assemble_numeric_atomic(matrices, thread_count);

        const auto& matrix = assembler.matrix();
        std::cout << "dimension=" << matrix.dimension << " values=";
        for (std::size_t index = 0; index < matrix.values.size(); ++index) {
            if (index != 0) {
                std::cout << ',';
            }
            std::cout << matrix.values[index];
        }
        std::cout << '\n';
        return 0;
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
}
