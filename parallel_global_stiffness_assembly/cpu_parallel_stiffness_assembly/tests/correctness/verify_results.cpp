#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"

#include <iostream>
#include <string>
#include <stdexcept>

using namespace fem;

namespace {

void verify_algorithms(const Mesh& mesh, KernelType kernel, int threads) {
    CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
    AssemblyPlan plan = build_assembly_plan(mesh, csr);

    AssemblyOptions options;
    options.threads = threads;
    options.kernel = kernel;

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
        std::cout << mesh.name << " " << algorithm_to_string(algo)
                  << " rel_l2=" << error.relative_l2
                  << " max_abs=" << error.max_abs << "\n";
        if (!error.same_structure || error.relative_l2 > 1.0e-8) {
            throw std::runtime_error("Correctness check failed for " + algorithm_to_string(algo));
        }
    }
}

} // namespace

int main() {
    try {
        Mesh generated_mesh = Mesh::make_cube_tet4(3, 3, 3);
        verify_algorithms(generated_mesh, KernelType::Simplified, 4);

        const std::string gap_labels_path =
            std::string(PGSA_TEST_EXAMPLES_DIR) + "/small_c3d4_gap_labels.inp";
        Mesh gap_labels_mesh = Mesh::load_from_inp(gap_labels_path);
        if (gap_labels_mesh.num_nodes() != 5 || gap_labels_mesh.num_elements() != 2) {
            throw std::runtime_error("Gap-label .inp sample did not parse as expected");
        }
        verify_algorithms(gap_labels_mesh, KernelType::PhysicsTet4, 3);
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_results failed: " << ex.what() << "\n";
        return 1;
    }
}
