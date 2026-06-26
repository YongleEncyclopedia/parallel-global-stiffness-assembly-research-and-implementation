#include "assembly/symbolic_numeric_eval.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"

#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace fem;

namespace {

void require_close(const char* label, const CsrMatrix& reference, const CsrMatrix& candidate) {
    const auto err = compare_values(reference, candidate);
    std::cout << label << " rel_l2=" << err.relative_l2
              << " max_abs=" << err.max_abs << "\n";
    if (!err.same_structure || err.relative_l2 > 1.0e-8 || !std::isfinite(err.relative_l2)) {
        throw std::runtime_error(std::string(label) + " does not match symbolic reference");
    }
}

void require_positive(const char* label, double value) {
    if (!(value >= 0.0) || !std::isfinite(value)) {
        throw std::runtime_error(std::string(label) + " is not a finite non-negative duration");
    }
}

void require_same_symbolic_artifacts(const SymbolicArtifacts& reference,
                                     const SymbolicArtifacts& candidate) {
    if (reference.csr.row_offsets != candidate.csr.row_offsets ||
        reference.csr.col_indices != candidate.csr.col_indices) {
        throw std::runtime_error("parallel symbolic CSR does not match serial CSR exactly");
    }
    if (reference.plan.element_offsets != candidate.plan.element_offsets ||
        reference.plan.dofs != candidate.plan.dofs ||
        reference.plan.scatter != candidate.plan.scatter) {
        throw std::runtime_error("parallel symbolic AssemblyPlan does not match serial plan exactly");
    }
}

} // namespace

int main() {
    try {
        Mesh mesh = Mesh::make_cube_tet4(2, 2, 2);
        AssemblyOptions options;
        options.stiffness_model = StiffnessModel::PhysicsTet4;

        auto artifacts = build_symbolic_artifacts(mesh);
        auto parallel_artifacts = build_symbolic_artifacts_parallel(mesh, 2);
        require_same_symbolic_artifacts(artifacts, parallel_artifacts);
        if (parallel_artifacts.threads != 2 || parallel_artifacts.mode != "parallel") {
            throw std::runtime_error("parallel symbolic metadata was not recorded");
        }
        if (parallel_artifacts.temporary_bytes == 0) {
            throw std::runtime_error("parallel symbolic temporary memory estimate was not recorded");
        }

        auto symbolic_once = assemble_symbolic_serial_once(mesh, artifacts, options);
        auto direct_once = assemble_direct_no_symbolic_once(mesh, options);
        options.threads = 2;
        auto direct_parallel_once = assemble_direct_no_symbolic_parallel(mesh, options);
        require_close("direct_no_symbolic", symbolic_once.matrix, direct_once.matrix);
        require_close("direct_no_symbolic_parallel", symbolic_once.matrix, direct_parallel_once.matrix);

        const int assemblies = 3;
        options.threads = 2;
        auto parallel_reuse = evaluate_parallel_symbolic_reuse(mesh, options, assemblies, AlgorithmType::CpuAtomic);
        auto direct_parallel = evaluate_direct_no_symbolic_parallel(mesh, options, assemblies);
        options.threads = 1;
        auto reuse = evaluate_symbolic_reuse_serial(mesh, options, assemblies);
        auto rebuild = evaluate_symbolic_rebuild_serial(mesh, options, assemblies);
        auto direct = evaluate_direct_no_symbolic_serial(mesh, options, assemblies);

        require_close("parallel_symbolic_reuse", symbolic_once.matrix, parallel_reuse.matrix);
        require_close("direct_no_symbolic_parallel_eval", symbolic_once.matrix, direct_parallel.matrix);
        require_close("symbolic_reuse_serial", symbolic_once.matrix, reuse.matrix);
        require_close("symbolic_rebuild_serial", symbolic_once.matrix, rebuild.matrix);
        require_close("direct_no_symbolic_serial", symbolic_once.matrix, direct.matrix);

        if (parallel_reuse.mode != "parallel_symbolic_reuse" ||
            direct_parallel.mode != "direct_no_symbolic_parallel" ||
            reuse.mode != "symbolic_reuse_serial" ||
            rebuild.mode != "symbolic_rebuild_serial" ||
            direct.mode != "direct_no_symbolic_serial") {
            throw std::runtime_error("Unexpected symbolic evaluation mode labels");
        }
        if (parallel_reuse.threads != 2 ||
            direct_parallel.threads != 2 ||
            reuse.assemblies_per_symbolic != assemblies ||
            rebuild.assemblies_per_symbolic != assemblies ||
            direct.assemblies_per_symbolic != assemblies) {
            throw std::runtime_error("Unexpected assemblies_per_symbolic values");
        }

        require_positive("parallel symbolic csr_ms", parallel_reuse.symbolic_csr_ms);
        require_positive("parallel symbolic plan_ms", parallel_reuse.symbolic_plan_ms);
        require_positive("parallel symbolic temporary bytes", static_cast<double>(parallel_reuse.symbolic_temporary_bytes));
        require_positive("direct parallel bucket_merge_ms", direct_parallel.direct_bucket_merge_ms);
        require_positive("direct parallel sort_reduce_ms", direct_parallel.direct_sort_reduce_ms);
        require_positive("reuse symbolic_total_ms", reuse.symbolic_total_ms);
        require_positive("reuse numeric_ms", reuse.numeric_ms);
        require_positive("reuse amortized_total_ms", reuse.amortized_total_ms);
        require_positive("direct generate_ms", direct.direct_generate_ms);
        require_positive("direct sort_reduce_ms", direct.direct_sort_reduce_ms);
        require_positive("direct amortized_total_ms", direct.amortized_total_ms);

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_symbolic_numeric_eval failed: " << ex.what() << "\n";
        return 1;
    }
}
