#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "assembly/symbolic_numeric_eval.h"
#include "backends/cpu/atomic_assembler.h"
#include "backends/cpu/coo_sort_reduce_assembler.h"
#include "backends/cpu/graph_coloring_assembler.h"
#include "backends/cpu/lock_guard_assembler.h"
#include "backends/cpu/private_csr_assembler.h"
#include "backends/cpu/row_owner_assembler.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"
#include "core/platform.h"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require_region(const char* label,
                    int threads,
                    const fem::CpuTopologyInfo& cpu,
                    const std::string& expected) {
    const std::string actual = fem::classify_thread_region(threads, cpu);
    std::cout << label << " threads=" << threads << " region=" << actual << "\n";
    if (actual != expected) {
        throw std::runtime_error(std::string(label) + " expected " + expected + ", got " + actual);
    }
}

template <class Callable>
void require_openmp_failure(const std::string& label,
                            const std::string& feature,
                            Callable&& callable) {
    try {
        callable();
    } catch (const std::exception& ex) {
        const std::string message = ex.what();
        if (message.find("OpenMP") == std::string::npos ||
            message.find(feature) == std::string::npos) {
            throw std::runtime_error(label + " returned an unclear capability error: " + message);
        }
        return;
    }
    throw std::runtime_error(label + " did not reject a build without OpenMP");
}

void verify_factory_algorithms(std::size_t expected_count) {
    const auto algorithms = fem::AssemblerFactory::get_available_algorithms();
    if (algorithms.size() != expected_count ||
        algorithms.empty() ||
        algorithms.front() != fem::AlgorithmType::CpuSerial) {
        throw std::runtime_error("assembler availability does not match the compiled OpenMP capability");
    }
}

template <class Backend>
void require_direct_backend_failure(const std::string& feature,
                                    const fem::Mesh& mesh,
                                    const fem::CsrMatrix& csr,
                                    const fem::AssemblyPlan& plan,
                                    const fem::AssemblyOptions& options,
                                    bool prepare_first) {
    require_openmp_failure("direct " + feature, feature, [&] {
        Backend assembler(options);
        assembler.set_problem(mesh, csr, plan);
        if (prepare_first) assembler.prepare();
        assembler.assemble();
    });
}

void verify_serial_only_contract() {
    verify_factory_algorithms(1);

#if defined(PGSA_HAS_OPENMP)
    static_assert(PGSA_HAS_OPENMP == 0 || PGSA_HAS_OPENMP == 1,
                  "PGSA_HAS_OPENMP must be a public 0/1 compile capability");
    if (fem::openmp_available()) {
        throw std::runtime_error("openmp_available reported true in a serial-only build");
    }
    require_openmp_failure("OpenMP throwing guard", "thread-region capability test", [] {
        fem::require_openmp("thread-region capability test");
    });
#else
    throw std::runtime_error("PGSA_HAS_OPENMP public compile capability is undefined");
#endif

    if (fem::max_thread_count() != 1 ||
        fem::effective_thread_count(0) != 1 ||
        fem::effective_thread_count(8) != 1) {
        throw std::runtime_error("thread-count helpers report parallel capacity in a serial-only build");
    }

    fem::AssemblyOptions options;
    options.threads = 2;

    const fem::Mesh mesh = fem::Mesh::make_cube_tet4(1, 1, 1);
    const fem::CsrMatrix csr = fem::CsrMatrix::build_sparsity(mesh);
    const fem::AssemblyPlan plan = fem::build_assembly_plan(mesh, csr);

    require_direct_backend_failure<fem::cpu::AtomicAssembler>(
        "assembler backend cpu_atomic", mesh, csr, plan, options, false);
    require_direct_backend_failure<fem::cpu::LockGuardAssembler>(
        "assembler backend cpu_lock_guard", mesh, csr, plan, options, true);
    require_direct_backend_failure<fem::cpu::PrivateCsrAssembler>(
        "assembler backend cpu_private_csr", mesh, csr, plan, options, true);
    require_direct_backend_failure<fem::cpu::CooSortReduceAssembler>(
        "assembler backend cpu_coo_sort_reduce", mesh, csr, plan, options, true);
    require_direct_backend_failure<fem::cpu::GraphColoringAssembler>(
        "assembler backend cpu_graph_coloring", mesh, csr, plan, options, true);
    require_direct_backend_failure<fem::cpu::RowOwnerAssembler>(
        "assembler backend cpu_row_owner", mesh, csr, plan, options, true);

    const std::string atomic_feature = "assembler backend cpu_atomic";
    require_openmp_failure(atomic_feature, atomic_feature, [&] {
        (void)fem::AssemblerFactory::create(fem::AlgorithmType::CpuAtomic, options);
    });
    require_openmp_failure("create_atomic", atomic_feature, [&] {
        (void)fem::AssemblerFactory::create_atomic(options);
    });
    require_openmp_failure("create_lock_guard", "assembler backend cpu_lock_guard", [&] {
        (void)fem::AssemblerFactory::create_lock_guard(options);
    });
    require_openmp_failure("create_private_csr", "assembler backend cpu_private_csr", [&] {
        (void)fem::AssemblerFactory::create_private_csr(options);
    });
    require_openmp_failure("create_coo_sort_reduce", "assembler backend cpu_coo_sort_reduce", [&] {
        (void)fem::AssemblerFactory::create_coo_sort_reduce(options);
    });
    require_openmp_failure("create_graph_coloring", "assembler backend cpu_graph_coloring", [&] {
        (void)fem::AssemblerFactory::create_graph_coloring(options);
    });
    require_openmp_failure("create_row_owner", "assembler backend cpu_row_owner", [&] {
        (void)fem::AssemblerFactory::create_row_owner(options);
    });

    require_openmp_failure("parallel sparsity", "parallel sparsity construction", [&] {
        (void)fem::CsrMatrix::build_sparsity_parallel(mesh, 2);
    });
    require_openmp_failure("parallel assembly plan", "parallel assembly-plan construction", [&] {
        (void)fem::build_assembly_plan_parallel(mesh, csr, 2);
    });
    require_openmp_failure("parallel symbolic evaluation", "parallel symbolic-reuse evaluation", [&] {
        (void)fem::evaluate_parallel_symbolic_reuse(
            mesh, options, 1, fem::AlgorithmType::CpuAtomic);
    });
    require_openmp_failure("direct parallel evaluation", "direct no-symbolic parallel evaluation", [&] {
        (void)fem::evaluate_direct_no_symbolic_parallel(mesh, options, 1);
    });
}

void verify_openmp_contract() {
    verify_factory_algorithms(7);
#if defined(PGSA_HAS_OPENMP)
    static_assert(PGSA_HAS_OPENMP == 0 || PGSA_HAS_OPENMP == 1,
                  "PGSA_HAS_OPENMP must be a public 0/1 compile capability");
    if (!fem::openmp_available()) {
        throw std::runtime_error("openmp_available reported false in an OpenMP build");
    }
    fem::require_openmp("thread-region capability test");
#else
    throw std::runtime_error("PGSA_HAS_OPENMP public compile capability is undefined");
#endif
}

} // namespace

int main() {
    try {
        fem::CpuTopologyInfo smt_cpu;
        smt_cpu.model = "synthetic SMT CPU";
        smt_cpu.physical_cores = 8;
        smt_cpu.logical_cores = 16;
        require_region("physical lower bound", 1, smt_cpu, "physical_core_region");
        require_region("physical upper bound", 8, smt_cpu, "physical_core_region");
        require_region("logical lower bound", 9, smt_cpu, "logical_core_region");
        require_region("logical upper bound", 16, smt_cpu, "logical_core_region");
        require_region("oversubscribed", 17, smt_cpu, "oversubscription_region");

        fem::CpuTopologyInfo no_smt_cpu;
        no_smt_cpu.model = "synthetic no SMT CPU";
        no_smt_cpu.physical_cores = 14;
        no_smt_cpu.logical_cores = 14;
        require_region("no smt physical", 14, no_smt_cpu, "physical_core_region");
        require_region("no smt oversubscribed", 15, no_smt_cpu, "oversubscription_region");

        fem::CpuTopologyInfo unknown_cpu;
        unknown_cpu.model = "unknown topology CPU";
        unknown_cpu.physical_cores = 0;
        unknown_cpu.logical_cores = 4;
        require_region("unknown physical fallback", 4, unknown_cpu, "physical_core_region");
        require_region("unknown oversubscribed", 5, unknown_cpu, "oversubscription_region");

#if PGSA_HAS_OPENMP
        verify_openmp_contract();
#else
        verify_serial_only_contract();
#endif
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_thread_region failed: " << ex.what() << "\n";
        return 1;
    }
}
