#include "csc3_demo/assembly_helper.h"

int main() {
    const csc3_demo::ElementDofMap topology{
        {20, 10},
        {0, 2, 4},
        {1, 2, 0, 1},
    };
    const csc3_demo::ElementMatrixBatch element_matrices{
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

    csc3_demo::SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(topology, 2);
    assembler.assemble_numeric_atomic(element_matrices, 2);

    const auto& matrix = assembler.matrix();
    const bool result_is_correct =
        matrix.dimension == 3 &&
        matrix.column_offsets == std::vector<csc3_demo::Offset>{0, 1, 3, 5} &&
        matrix.row_indices == std::vector<csc3_demo::GlobalDofIndex>{0, 0, 1, 1, 2} &&
        matrix.values == std::vector<double>{2.0, -1.0, 5.0, -2.0, 3.0};
    return result_is_correct ? 0 : 1;
}
