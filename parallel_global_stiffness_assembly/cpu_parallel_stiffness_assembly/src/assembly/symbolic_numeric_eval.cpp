#include "assembly/symbolic_numeric_eval.h"

#include "assembly/assembler_factory.h"
#include "assembly/element_kernels.h"
#include "core/platform.h"

#include <algorithm>
#include <chrono>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace fem {
namespace {

struct DirectContribution {
    Index row = 0;
    Index col = 0;
    Real value = 0.0;
};

double ms_since(const std::chrono::steady_clock::time_point& begin,
                const std::chrono::steady_clock::time_point& end) {
    return std::chrono::duration<double, std::milli>(end - begin).count();
}

Size count_element_entries(const Mesh& mesh) {
    Size entries = 0;
    for (const auto& elem : mesh.elements) {
        const Size edofs = static_cast<Size>(elem.node_count * constants::DOFS_PER_NODE);
        const Size elem_entries = edofs * edofs;
        if (entries > std::numeric_limits<Size>::max() - elem_entries) {
            throw std::runtime_error("Direct no-symbolic contribution count overflows Size");
        }
        entries += elem_entries;
    }
    return entries;
}

void ensure_direct_memory_allowed(const Mesh& mesh, const AssemblyOptions& options) {
    const Size entries = count_element_entries(mesh);
    if (entries > std::numeric_limits<Size>::max() / sizeof(DirectContribution)) {
        throw std::runtime_error("Direct no-symbolic contribution memory estimate overflows Size");
    }
    const Size required = entries * sizeof(DirectContribution);
    if (required > options.max_transient_bytes) {
        std::ostringstream os;
        os << "direct_no_symbolic requires about " << memory_string(required)
           << " transient memory, above limit " << memory_string(options.max_transient_bytes);
        throw std::runtime_error(os.str());
    }
}

CsrMatrix reduce_direct_contributions(std::vector<DirectContribution>& contributions, Index ndofs) {
    std::sort(contributions.begin(), contributions.end(), [](const auto& a, const auto& b) {
        if (a.row != b.row) return a.row < b.row;
        return a.col < b.col;
    });

    std::vector<Index> row_offsets(static_cast<Size>(ndofs) + 1, 0);
    std::vector<Index> col_indices;
    std::vector<Real> values;
    col_indices.reserve(contributions.size());
    values.reserve(contributions.size());

    Index current_row = 0;
    Size p = 0;
    while (p < contributions.size()) {
        const Index row = contributions[p].row;
        const Index col = contributions[p].col;
        if (row < 0 || row >= ndofs || col < 0 || col >= ndofs) {
            throw std::runtime_error("Direct no-symbolic contribution index out of range");
        }
        while (current_row <= row) {
            row_offsets[static_cast<Size>(current_row)] = static_cast<Index>(col_indices.size());
            ++current_row;
        }
        Real sum = 0.0;
        do {
            sum += contributions[p].value;
            ++p;
        } while (p < contributions.size() && contributions[p].row == row && contributions[p].col == col);
        col_indices.push_back(col);
        values.push_back(sum);
        if (col_indices.size() > static_cast<Size>(std::numeric_limits<Index>::max())) {
            throw std::runtime_error("Direct no-symbolic result exceeds 32-bit Index capacity");
        }
    }

    while (current_row <= ndofs) {
        row_offsets[static_cast<Size>(current_row)] = static_cast<Index>(col_indices.size());
        ++current_row;
    }

    CsrMatrix matrix(ndofs, ndofs, std::move(row_offsets), std::move(col_indices));
    matrix.values = std::move(values);
    return matrix;
}

void populate_common_record(SymbolicEvaluationRecord& record,
                            const SymbolicArtifacts& artifacts,
                            int assemblies_per_symbolic) {
    record.assemblies_per_symbolic = assemblies_per_symbolic;
    record.threads = artifacts.threads;
    record.symbolic_csr_ms = artifacts.csr_ms;
    record.symbolic_plan_ms = artifacts.plan_ms;
    record.symbolic_total_ms = artifacts.total_ms();
    record.symbolic_temporary_bytes = artifacts.temporary_bytes;
    record.csr_bytes = artifacts.csr.bytes();
    record.plan_bytes = artifacts.plan.bytes();
}

} // namespace

SymbolicArtifacts build_symbolic_artifacts(const Mesh& mesh) {
    const auto csr0 = std::chrono::steady_clock::now();
    CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
    const auto csr1 = std::chrono::steady_clock::now();
    AssemblyPlan plan = build_assembly_plan(mesh, csr);
    const auto plan1 = std::chrono::steady_clock::now();

    SymbolicArtifacts artifacts;
    artifacts.csr = std::move(csr);
    artifacts.plan = std::move(plan);
    artifacts.mode = "serial";
    artifacts.threads = 1;
    artifacts.csr_ms = ms_since(csr0, csr1);
    artifacts.plan_ms = ms_since(csr1, plan1);
    return artifacts;
}

SymbolicArtifacts build_symbolic_artifacts_parallel(const Mesh& mesh, int threads) {
    const int nth = std::max(1, effective_thread_count(threads));
    Size temporary_bytes = 0;
    const auto csr0 = std::chrono::steady_clock::now();
    CsrMatrix csr = CsrMatrix::build_sparsity_parallel(mesh, nth, &temporary_bytes);
    const auto csr1 = std::chrono::steady_clock::now();
    AssemblyPlan plan = build_assembly_plan_parallel(mesh, csr, nth);
    const auto plan1 = std::chrono::steady_clock::now();

    SymbolicArtifacts artifacts;
    artifacts.csr = std::move(csr);
    artifacts.plan = std::move(plan);
    artifacts.mode = "parallel";
    artifacts.threads = nth;
    artifacts.csr_ms = ms_since(csr0, csr1);
    artifacts.plan_ms = ms_since(csr1, plan1);
    artifacts.temporary_bytes = temporary_bytes;
    return artifacts;
}

SymbolicSerialResult assemble_symbolic_serial_once(const Mesh& mesh,
                                                   const SymbolicArtifacts& artifacts,
                                                   const AssemblyOptions& options) {
    auto assembler = AssemblerFactory::create(AlgorithmType::CpuSerial, options);
    assembler->set_problem(mesh, artifacts.csr, artifacts.plan);
    assembler->prepare();
    assembler->assemble();

    SymbolicSerialResult result;
    result.matrix = assembler->get_result();
    result.numeric_ms = assembler->get_stats().assembly_time_ms;
    return result;
}

DirectNoSymbolicResult assemble_direct_no_symbolic_once(const Mesh& mesh,
                                                        const AssemblyOptions& options) {
    const Size entries = count_element_entries(mesh);
    ensure_direct_memory_allowed(mesh, options);
    std::vector<DirectContribution> contributions;
    contributions.reserve(entries);
    std::vector<Real> ke;

    const auto t0 = std::chrono::steady_clock::now();
    for (Size e = 0; e < mesh.num_elements(); ++e) {
        const auto dofs = element_dofs(mesh.elements[e]);
        compute_element_matrix(mesh, e, options, ke);
        const int edofs = static_cast<int>(dofs.size());
        for (int i = 0; i < edofs; ++i) {
            for (int j = 0; j < edofs; ++j) {
                contributions.push_back(DirectContribution{
                    dofs[static_cast<Size>(i)],
                    dofs[static_cast<Size>(j)],
                    ke[static_cast<Size>(i) * edofs + j]});
            }
        }
    }
    const auto t_generate = std::chrono::steady_clock::now();

    if (mesh.num_dofs() > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Too many DOFs for 32-bit Index in direct no-symbolic assembly");
    }
    CsrMatrix matrix = reduce_direct_contributions(contributions, static_cast<Index>(mesh.num_dofs()));
    const auto t1 = std::chrono::steady_clock::now();

    DirectNoSymbolicResult result;
    result.matrix = std::move(matrix);
    result.generate_ms = ms_since(t0, t_generate);
    result.sort_reduce_ms = ms_since(t_generate, t1);
    result.total_ms = ms_since(t0, t1);
    result.transient_bytes = entries * sizeof(DirectContribution);
    return result;
}

DirectNoSymbolicResult assemble_direct_no_symbolic_parallel(const Mesh& mesh,
                                                            const AssemblyOptions& options) {
    const Size entries = count_element_entries(mesh);
    ensure_direct_memory_allowed(mesh, options);
    if (mesh.num_dofs() > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Too many DOFs for 32-bit Index in direct no-symbolic assembly");
    }
    const Index ndofs = static_cast<Index>(mesh.num_dofs());
    const int nth = std::max(1, effective_thread_count(options.threads));
    std::vector<std::vector<DirectContribution>> per_thread(static_cast<Size>(nth));
    const Size reserve_each = entries / static_cast<Size>(nth) + 1024;
    for (auto& local : per_thread) local.reserve(reserve_each);

    const auto t0 = std::chrono::steady_clock::now();
#ifdef _OPENMP
#pragma omp parallel num_threads(nth)
#endif
    {
        std::vector<Real> ke;
        const int tid = current_thread_id();
        auto& local = per_thread[static_cast<Size>(tid)];
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
        for (std::int64_t ee = 0; ee < static_cast<std::int64_t>(mesh.num_elements()); ++ee) {
            const Size e = static_cast<Size>(ee);
            const auto dofs = element_dofs(mesh.elements[e]);
            compute_element_matrix(mesh, e, options, ke);
            const int edofs = static_cast<int>(dofs.size());
            for (int i = 0; i < edofs; ++i) {
                for (int j = 0; j < edofs; ++j) {
                    local.push_back(DirectContribution{
                        dofs[static_cast<Size>(i)],
                        dofs[static_cast<Size>(j)],
                        ke[static_cast<Size>(i) * edofs + j]});
                }
            }
        }
    }
    const auto t_generate = std::chrono::steady_clock::now();

    std::vector<std::vector<DirectContribution>> buckets(static_cast<Size>(nth));
    const Size reserve_bucket = entries / static_cast<Size>(nth) + 1024;
    for (auto& bucket : buckets) bucket.reserve(reserve_bucket);
    for (auto& local : per_thread) {
        for (auto& contribution : local) {
            if (contribution.row < 0 || contribution.row >= ndofs ||
                contribution.col < 0 || contribution.col >= ndofs) {
                throw std::runtime_error("Direct no-symbolic contribution index out of range");
            }
            const Size bucket_id = std::min(static_cast<Size>(nth - 1),
                                            static_cast<Size>(contribution.row) * static_cast<Size>(nth) /
                                                static_cast<Size>(ndofs));
            buckets[bucket_id].push_back(contribution);
        }
        std::vector<DirectContribution>().swap(local);
    }
    const auto t_bucket = std::chrono::steady_clock::now();

    std::vector<std::vector<DirectContribution>> reduced(static_cast<Size>(nth));
    std::vector<Index> row_counts(static_cast<Size>(ndofs), 0);
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t bb = 0; bb < static_cast<std::int64_t>(nth); ++bb) {
        auto& bucket = buckets[static_cast<Size>(bb)];
        std::sort(bucket.begin(), bucket.end(), [](const auto& a, const auto& b) {
            if (a.row != b.row) return a.row < b.row;
            return a.col < b.col;
        });
        auto& out = reduced[static_cast<Size>(bb)];
        out.reserve(bucket.size());
        Size p = 0;
        while (p < bucket.size()) {
            const Index row = bucket[p].row;
            const Index col = bucket[p].col;
            Real sum = 0.0;
            do {
                sum += bucket[p].value;
                ++p;
            } while (p < bucket.size() && bucket[p].row == row && bucket[p].col == col);
            out.push_back(DirectContribution{row, col, sum});
            ++row_counts[static_cast<Size>(row)];
        }
        std::vector<DirectContribution>().swap(bucket);
    }

    std::vector<Index> row_offsets(static_cast<Size>(ndofs) + 1, 0);
    Size nnz = 0;
    for (Index row = 0; row < ndofs; ++row) {
        nnz += static_cast<Size>(row_counts[static_cast<Size>(row)]);
        if (nnz > static_cast<Size>(std::numeric_limits<Index>::max())) {
            throw std::runtime_error("Direct no-symbolic result exceeds 32-bit Index capacity");
        }
        row_offsets[static_cast<Size>(row) + 1] = static_cast<Index>(nnz);
    }

    std::vector<Index> col_indices(nnz);
    std::vector<Real> values(nnz, 0.0);
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t bb = 0; bb < static_cast<std::int64_t>(nth); ++bb) {
        Index current_row = -1;
        Index row_slot = 0;
        for (const auto& contribution : reduced[static_cast<Size>(bb)]) {
            if (contribution.row != current_row) {
                current_row = contribution.row;
                row_slot = 0;
            }
            const Size pos = static_cast<Size>(row_offsets[static_cast<Size>(contribution.row)] + row_slot);
            col_indices[pos] = contribution.col;
            values[pos] = contribution.value;
            ++row_slot;
        }
    }
    const auto t1 = std::chrono::steady_clock::now();

    CsrMatrix matrix(ndofs, ndofs, std::move(row_offsets), std::move(col_indices));
    matrix.values = std::move(values);

    DirectNoSymbolicResult result;
    result.matrix = std::move(matrix);
    result.generate_ms = ms_since(t0, t_generate);
    result.bucket_merge_ms = ms_since(t_generate, t_bucket);
    result.sort_reduce_ms = ms_since(t_bucket, t1);
    result.total_ms = ms_since(t0, t1);
    result.transient_bytes = entries * sizeof(DirectContribution);
    return result;
}

SymbolicEvaluationRecord evaluate_parallel_symbolic_reuse(const Mesh& mesh,
                                                          const AssemblyOptions& options,
                                                          int assemblies_per_symbolic,
                                                          AlgorithmType numeric_backend) {
    if (assemblies_per_symbolic <= 0) throw std::invalid_argument("assemblies_per_symbolic must be positive");

    SymbolicEvaluationRecord record;
    record.mode = "parallel_symbolic_reuse";
    record.numeric_backend = algorithm_to_string(numeric_backend);
    SymbolicArtifacts artifacts = build_symbolic_artifacts_parallel(mesh, options.threads);
    populate_common_record(record, artifacts, assemblies_per_symbolic);
    record.symbolic_builds = 1;

    auto assembler = AssemblerFactory::create(numeric_backend, options);
    assembler->set_problem(mesh, artifacts.csr, artifacts.plan);
    assembler->prepare();

    double numeric_sum = 0.0;
    for (int i = 0; i < assemblies_per_symbolic; ++i) {
        assembler->assemble();
        numeric_sum += assembler->get_stats().assembly_time_ms;
    }
    record.numeric_ms = numeric_sum / static_cast<double>(assemblies_per_symbolic);
    record.amortized_total_ms =
        (record.symbolic_total_ms + numeric_sum) / static_cast<double>(assemblies_per_symbolic);
    record.matrix = assembler->get_result();
    return record;
}

SymbolicEvaluationRecord evaluate_symbolic_reuse_serial(const Mesh& mesh,
                                                        const AssemblyOptions& options,
                                                        int assemblies_per_symbolic) {
    if (assemblies_per_symbolic <= 0) throw std::invalid_argument("assemblies_per_symbolic must be positive");

    SymbolicEvaluationRecord record;
    record.mode = "symbolic_reuse_serial";
    record.numeric_backend = "cpu_serial";
    SymbolicArtifacts artifacts = build_symbolic_artifacts(mesh);
    populate_common_record(record, artifacts, assemblies_per_symbolic);
    record.symbolic_builds = 1;

    auto assembler = AssemblerFactory::create(AlgorithmType::CpuSerial, options);
    assembler->set_problem(mesh, artifacts.csr, artifacts.plan);
    assembler->prepare();

    double numeric_sum = 0.0;
    for (int i = 0; i < assemblies_per_symbolic; ++i) {
        assembler->assemble();
        numeric_sum += assembler->get_stats().assembly_time_ms;
    }
    record.numeric_ms = numeric_sum / static_cast<double>(assemblies_per_symbolic);
    record.amortized_total_ms =
        (record.symbolic_total_ms + numeric_sum) / static_cast<double>(assemblies_per_symbolic);
    record.matrix = assembler->get_result();
    return record;
}

SymbolicEvaluationRecord evaluate_symbolic_rebuild_serial(const Mesh& mesh,
                                                          const AssemblyOptions& options,
                                                          int assemblies_per_symbolic) {
    if (assemblies_per_symbolic <= 0) throw std::invalid_argument("assemblies_per_symbolic must be positive");

    SymbolicEvaluationRecord record;
    record.mode = "symbolic_rebuild_serial";
    record.numeric_backend = "cpu_serial";
    record.assemblies_per_symbolic = assemblies_per_symbolic;
    record.symbolic_builds = assemblies_per_symbolic;

    double csr_sum = 0.0;
    double plan_sum = 0.0;
    double numeric_sum = 0.0;
    Size csr_bytes = 0;
    Size plan_bytes = 0;
    for (int i = 0; i < assemblies_per_symbolic; ++i) {
        SymbolicArtifacts artifacts = build_symbolic_artifacts(mesh);
        csr_sum += artifacts.csr_ms;
        plan_sum += artifacts.plan_ms;
        csr_bytes = artifacts.csr.bytes();
        plan_bytes = artifacts.plan.bytes();
        auto once = assemble_symbolic_serial_once(mesh, artifacts, options);
        numeric_sum += once.numeric_ms;
        record.matrix = std::move(once.matrix);
    }

    record.symbolic_csr_ms = csr_sum / static_cast<double>(assemblies_per_symbolic);
    record.symbolic_plan_ms = plan_sum / static_cast<double>(assemblies_per_symbolic);
    record.symbolic_total_ms = record.symbolic_csr_ms + record.symbolic_plan_ms;
    record.numeric_ms = numeric_sum / static_cast<double>(assemblies_per_symbolic);
    record.amortized_total_ms =
        (csr_sum + plan_sum + numeric_sum) / static_cast<double>(assemblies_per_symbolic);
    record.csr_bytes = csr_bytes;
    record.plan_bytes = plan_bytes;
    return record;
}

SymbolicEvaluationRecord evaluate_direct_no_symbolic_serial(const Mesh& mesh,
                                                            const AssemblyOptions& options,
                                                            int assemblies_per_symbolic) {
    if (assemblies_per_symbolic <= 0) throw std::invalid_argument("assemblies_per_symbolic must be positive");

    SymbolicEvaluationRecord record;
    record.mode = "direct_no_symbolic_serial";
    record.numeric_backend = "none";
    record.assemblies_per_symbolic = assemblies_per_symbolic;
    record.threads = 1;
    record.symbolic_builds = 0;

    double generate_sum = 0.0;
    double sort_reduce_sum = 0.0;
    double total_sum = 0.0;
    Size transient_bytes = 0;
    for (int i = 0; i < assemblies_per_symbolic; ++i) {
        auto once = assemble_direct_no_symbolic_once(mesh, options);
        generate_sum += once.generate_ms;
        record.direct_bucket_merge_ms = 0.0;
        sort_reduce_sum += once.sort_reduce_ms;
        total_sum += once.total_ms;
        transient_bytes = once.transient_bytes;
        record.matrix = std::move(once.matrix);
    }

    record.direct_generate_ms = generate_sum / static_cast<double>(assemblies_per_symbolic);
    record.direct_sort_reduce_ms = sort_reduce_sum / static_cast<double>(assemblies_per_symbolic);
    record.amortized_total_ms = total_sum / static_cast<double>(assemblies_per_symbolic);
    record.direct_transient_bytes = transient_bytes;
    return record;
}

SymbolicEvaluationRecord evaluate_direct_no_symbolic_parallel(const Mesh& mesh,
                                                              const AssemblyOptions& options,
                                                              int assemblies_per_symbolic) {
    if (assemblies_per_symbolic <= 0) throw std::invalid_argument("assemblies_per_symbolic must be positive");

    SymbolicEvaluationRecord record;
    record.mode = "direct_no_symbolic_parallel";
    record.numeric_backend = "none";
    record.assemblies_per_symbolic = assemblies_per_symbolic;
    record.threads = std::max(1, effective_thread_count(options.threads));
    record.symbolic_builds = 0;

    double generate_sum = 0.0;
    double bucket_sum = 0.0;
    double sort_reduce_sum = 0.0;
    double total_sum = 0.0;
    Size transient_bytes = 0;
    for (int i = 0; i < assemblies_per_symbolic; ++i) {
        auto once = assemble_direct_no_symbolic_parallel(mesh, options);
        generate_sum += once.generate_ms;
        bucket_sum += once.bucket_merge_ms;
        sort_reduce_sum += once.sort_reduce_ms;
        total_sum += once.total_ms;
        transient_bytes = once.transient_bytes;
        record.matrix = std::move(once.matrix);
    }

    record.direct_generate_ms = generate_sum / static_cast<double>(assemblies_per_symbolic);
    record.direct_bucket_merge_ms = bucket_sum / static_cast<double>(assemblies_per_symbolic);
    record.direct_sort_reduce_ms = sort_reduce_sum / static_cast<double>(assemblies_per_symbolic);
    record.amortized_total_ms = total_sum / static_cast<double>(assemblies_per_symbolic);
    record.direct_transient_bytes = transient_bytes;
    return record;
}

} // namespace fem
