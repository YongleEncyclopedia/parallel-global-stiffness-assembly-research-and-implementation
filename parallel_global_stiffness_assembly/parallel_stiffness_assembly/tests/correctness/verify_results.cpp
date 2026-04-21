/**
 * @file verify_results.cpp
 * @brief 正确性验证程序
 *
 * 验证 GPU 算法结果与 CPU 基线的一致性
 */

#include <iostream>
#include <iomanip>
#include <cmath>

#include "core/mesh.h"
#include "core/csr_matrix.h"
#include "assembly/assembler_factory.h"

using namespace fem;

double compute_relative_error(const CsrMatrix& ref, const CsrMatrix& test) {
    if (ref.nnz != test.nnz) {
        return -1.0;
    }

    double ref_norm = ref.frobenius_norm();
    if (ref_norm < 1e-15) {
        return 0.0;
    }

    double diff_sq = 0.0;
    for (Size i = 0; i < ref.nnz; ++i) {
        double d = ref.values[i] - test.values[i];
        diff_sq += d * d;
    }

    return std::sqrt(diff_sq) / ref_norm;
}

int main() {
    std::cout << "Correctness Verification\n";
    std::cout << "========================\n\n";

    // 生成测试网格
    Mesh mesh;
    mesh.generate_cube_mesh(10, 10, 10, 1.0, 1.0, 1.0, ElementType::Hex8);

    std::cout << "Test mesh:\n";
    std::cout << "  Elements: " << mesh.num_elements() << "\n";
    std::cout << "  DOFs: " << mesh.num_dofs() << "\n\n";

    // 预计算 CSR 结构
    CsrMatrix csr = mesh.precompute_csr_structure();

    // 运行 CPU 基线
    std::cout << "Running CPU baseline...\n";
    auto cpu_assembler = AssemblerFactory::create_serial();
    cpu_assembler->set_mesh(mesh);
    cpu_assembler->set_csr_structure(csr);
    cpu_assembler->prepare();
    cpu_assembler->assemble();
    const auto& cpu_result = cpu_assembler->get_result();

    std::cout << "CPU baseline norm: " << cpu_result.frobenius_norm() << "\n\n";

    // 测试所有 GPU 算法
    std::vector<AlgorithmType> gpu_algorithms = {
        AlgorithmType::Atomic,
        AlgorithmType::Block,
        AlgorithmType::PrefixScan,
        AlgorithmType::WorkQueue
    };

    std::cout << std::setw(20) << "Algorithm"
              << std::setw(15) << "Error"
              << std::setw(10) << "Status" << "\n";
    std::cout << std::string(45, '-') << "\n";

    bool all_passed = true;
    const double tolerance = 1e-6;

    for (auto algo : gpu_algorithms) {
        auto assembler = AssemblerFactory::create(algo);
        assembler->set_mesh(mesh);
        assembler->set_csr_structure(csr);

        assembler->prepare();
        assembler->assemble();

        double error = compute_relative_error(cpu_result, assembler->get_result());
        bool passed = (error >= 0 && error < tolerance);

        std::cout << std::setw(20) << assembler->get_name()
                  << std::setw(15) << std::scientific << std::setprecision(2) << error
                  << std::setw(10) << (passed ? "PASS" : "FAIL") << "\n";

        if (!passed) all_passed = false;

        assembler->cleanup();
    }

    std::cout << "\n";
    if (all_passed) {
        std::cout << "All tests PASSED!\n";
        return 0;
    } else {
        std::cout << "Some tests FAILED!\n";
        return 1;
    }
}
