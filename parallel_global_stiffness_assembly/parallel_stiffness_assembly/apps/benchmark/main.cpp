/**
 * @file main.cpp
 * @brief 性能基准测试主程序
 *
 * 执行所有算法的性能测试并输出结果
 */

#include <iostream>
#include <iomanip>
#include <fstream>
#include <chrono>
#include <vector>
#include <string>

#include "core/types.h"
#include "core/mesh.h"
#include "core/csr_matrix.h"
#include "assembly/assembler_factory.h"
#include "assembly/assembly_options.h"

using namespace fem;

// ============================================================================
// 工具函数
// ============================================================================

/**
 * @brief 计算两个 CSR 矩阵的相对误差
 */
double compute_relative_error(const CsrMatrix& ref, const CsrMatrix& test) {
    if (ref.nnz != test.nnz) {
        return -1.0;  // 结构不匹配
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

/**
 * @brief 打印测试结果表头
 */
void print_header() {
    std::cout << std::setw(20) << "Algorithm"
              << std::setw(15) << "Elements"
              << std::setw(15) << "DOFs"
              << std::setw(15) << "Time (ms)"
              << std::setw(15) << "Speedup"
              << std::setw(15) << "Error"
              << std::setw(15) << "Status"
              << std::endl;
    std::cout << std::string(105, '-') << std::endl;
}

/**
 * @brief 打印单行结果
 */
void print_result(const std::string& name, Size elements, Size dofs,
                  double time_ms, double speedup, double error, bool passed) {
    std::cout << std::setw(20) << name
              << std::setw(15) << elements
              << std::setw(15) << dofs
              << std::setw(15) << std::fixed << std::setprecision(3) << time_ms
              << std::setw(15) << std::fixed << std::setprecision(2) << speedup
              << std::setw(15) << std::scientific << std::setprecision(2) << error
              << std::setw(15) << (passed ? "PASS" : "FAIL")
              << std::endl;
}

// ============================================================================
// 主程序
// ============================================================================

int main(int argc, char** argv) {
    std::cout << "========================================================" << std::endl;
    std::cout << "  GPU Parallel Stiffness Matrix Assembly Benchmark" << std::endl;
    std::cout << "========================================================" << std::endl;
    std::cout << std::endl;

    // 默认参数
    Size nx = 20, ny = 20, nz = 20;  // 约 8000 单元
    ElementType elem_type = ElementType::Hex8;

    // 解析命令行参数
    if (argc >= 4) {
        nx = std::stoull(argv[1]);
        ny = std::stoull(argv[2]);
        nz = std::stoull(argv[3]);
    }
    if (argc >= 5) {
        std::string type_str = argv[4];
        if (type_str == "tet4" || type_str == "Tet4") {
            elem_type = ElementType::Tet4;
        }
    }

    // 生成网格
    std::cout << "Generating mesh..." << std::endl;
    Mesh mesh;
    mesh.generate_cube_mesh(nx, ny, nz, 1.0, 1.0, 1.0, elem_type);

    std::cout << "  Element type: " << element_type_to_string(elem_type) << std::endl;
    std::cout << "  Nodes: " << mesh.num_nodes() << std::endl;
    std::cout << "  Elements: " << mesh.num_elements() << std::endl;
    std::cout << "  DOFs: " << mesh.num_dofs() << std::endl;
    std::cout << std::endl;

    // 预计算 CSR 结构
    std::cout << "Precomputing CSR structure..." << std::endl;
    CsrMatrix csr = mesh.precompute_csr_structure();
    std::cout << "  NNZ: " << csr.nnz << std::endl;
    std::cout << "  Memory: " << csr.memory_usage_bytes() / (1024.0 * 1024.0) << " MB" << std::endl;
    std::cout << std::endl;

    // 配置选项
    AssemblyOptions options;
    options.block_size = 256;
    options.warmup_runs = 2;
    options.benchmark_runs = 5;

    // 获取所有算法
    auto algorithms = AssemblerFactory::get_available_algorithms();

    // 存储结果
    struct BenchmarkResult {
        std::string name;
        double time_ms;
        double error;
        bool passed;
    };
    std::vector<BenchmarkResult> results;

    // CPU 基线时间
    double cpu_time_ms = 0.0;
    CsrMatrix cpu_result;

    // 运行所有算法
    std::cout << "Running benchmarks..." << std::endl;
    print_header();

    for (auto algo : algorithms) {
        auto assembler = AssemblerFactory::create(algo, options);

        assembler->set_mesh(mesh);
        assembler->set_csr_structure(csr);

        // 预热
        for (int i = 0; i < options.warmup_runs; ++i) {
            assembler->prepare();
            assembler->assemble();
        }

        // 基准测试
        double total_time = 0.0;
        for (int i = 0; i < options.benchmark_runs; ++i) {
            assembler->prepare();
            assembler->assemble();
            total_time += assembler->get_stats().assembly_time_ms;
        }
        double avg_time = total_time / options.benchmark_runs;

        // 保存 CPU 结果作为参考
        if (algo == AlgorithmType::CpuSerial) {
            cpu_time_ms = avg_time;
            cpu_result = assembler->get_result();
        }

        // 计算误差和加速比
        double error = (algo == AlgorithmType::CpuSerial) ? 0.0 :
                       compute_relative_error(cpu_result, assembler->get_result());
        double speedup = (cpu_time_ms > 0) ? cpu_time_ms / avg_time : 1.0;
        bool passed = (error < 1e-6);

        print_result(assembler->get_name(), mesh.num_elements(), mesh.num_dofs(),
                     avg_time, speedup, error, passed);

        results.push_back({assembler->get_name(), avg_time, error, passed});

        assembler->cleanup();
    }

    std::cout << std::endl;
    std::cout << "Benchmark completed." << std::endl;

    // 输出 CSV 格式结果（可选）
    std::ofstream csv("benchmark_results.csv");
    if (csv.is_open()) {
        csv << "Algorithm,Elements,DOFs,Time_ms,Speedup,Error,Status\n";
        for (const auto& r : results) {
            double speedup = (cpu_time_ms > 0) ? cpu_time_ms / r.time_ms : 1.0;
            csv << r.name << ","
                << mesh.num_elements() << ","
                << mesh.num_dofs() << ","
                << r.time_ms << ","
                << speedup << ","
                << r.error << ","
                << (r.passed ? "PASS" : "FAIL") << "\n";
        }
        csv.close();
        std::cout << "Results saved to benchmark_results.csv" << std::endl;
    }

    return 0;
}
