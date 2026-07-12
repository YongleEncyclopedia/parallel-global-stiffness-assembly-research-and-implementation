#pragma once

#include <cstdint>
#include <vector>

namespace csc3_demo {

using GlobalDofIndex = std::int32_t;
using ElementId = std::int32_t;
using Offset = std::uint64_t;

struct ElementDofMap {
    std::vector<ElementId> element_ids;
    std::vector<Offset> element_dof_offsets;
    std::vector<GlobalDofIndex> global_dof_indices;
};

struct ElementMatrixBatch {
    std::vector<Offset> element_value_offsets;
    std::vector<double> values_row_major;
};

struct Csc3Matrix {
    GlobalDofIndex dimension = 0;
    std::vector<Offset> column_offsets;
    std::vector<GlobalDofIndex> row_indices;
    std::vector<double> values;
};

struct AssemblyPlan {
    std::vector<ElementId> element_ids;
    std::vector<Offset> element_dof_offsets;
    std::vector<GlobalDofIndex> global_dof_indices;
    std::vector<Offset> element_scatter_offsets;
    std::vector<Offset> scatter_indices;
};

class SymmetricCscAssembler {
public:
    void build_symbolic_parallel(const ElementDofMap& element_dof_map,
                                 int thread_count);
    void assemble_numeric_atomic(const ElementMatrixBatch& element_matrices,
                                 int thread_count);
    [[nodiscard]] const Csc3Matrix& matrix() const noexcept;
    [[nodiscard]] const AssemblyPlan& assembly_plan() const noexcept;
    [[nodiscard]] int symbolic_thread_count_used() const noexcept;
    [[nodiscard]] int numeric_thread_count_used() const noexcept;

private:
    Csc3Matrix matrix_;
    AssemblyPlan assembly_plan_;
    int symbolic_thread_count_used_ = 0;
    int numeric_thread_count_used_ = 0;
    bool symbolic_ready_ = false;
};

[[nodiscard]] bool openmp_enabled() noexcept;
[[nodiscard]] int max_openmp_threads() noexcept;

} // namespace csc3_demo
