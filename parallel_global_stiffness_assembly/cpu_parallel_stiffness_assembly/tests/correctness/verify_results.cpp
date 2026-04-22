#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"

#include <iostream>
#include <stdexcept>

using namespace fem;

int main() {
    try {
        Mesh mesh = Mesh::make_cube_tet4(3, 3, 3);
        CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
        AssemblyPlan plan = build_assembly_plan(mesh, csr);

        AssemblyOptions options;
        options.threads = 4;
        options.kernel = KernelType::Simplified;

        auto serial = AssemblerFactory::create(AlgorithmType::CpuSerial, options);
        serial->set_problem(mesh, csr, plan);
        serial->prepare();
        serial->assemble();

        for (auto algo : AssemblerFactory::get_available_algorithms()) {
            auto assembler = AssemblerFactory::create(algo, options);
            assembler->set_problem(mesh, csr, plan);
            assembler->prepare();
            assembler->assemble();
            const auto error = compare_values(serial->get_result(), assembler->get_result());
            std::cout << algorithm_to_string(algo) << " rel_l2=" << error.relative_l2
                      << " max_abs=" << error.max_abs << "\n";
            if (!error.same_structure || error.relative_l2 > 1.0e-8) {
                throw std::runtime_error("Correctness check failed for " + algorithm_to_string(algo));
            }
        }
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_results failed: " << ex.what() << "\n";
        return 1;
    }
}
