#pragma once

#include <cstdint>
#include <vector>

namespace csc3_demo {

namespace evidence {
struct BenchmarkAccess;
}

/// Signed type for a zero-based global degree-of-freedom index.
using GlobalDofIndex = std::int32_t;
/// Signed type for a nonnegative, unique element identifier.
using ElementId = std::int32_t;
/// Unsigned type for a zero-based offset into an owned flattened array.
using Offset = std::uint64_t;

/// Owning flattened element-to-global-DOF topology input.
struct ElementDofMap {
    /// Element identifiers, one per offset segment; ownership stays with this object.
    std::vector<ElementId> element_ids;
    /// Zero-based offsets into global_dof_indices, with one terminal offset.
    std::vector<Offset> element_dof_offsets;
    /// Owned zero-based global DOF indices in each element's local order.
    std::vector<GlobalDofIndex> global_dof_indices;
};

/// Owning batch of complete dense element matrices in canonical element order.
struct ElementMatrixBatch {
    /// Zero-based offsets into values_row_major, with one terminal offset.
    std::vector<Offset> element_value_offsets;
    /// Owned finite matrix values, one full row-major square matrix per segment.
    std::vector<double> values_row_major;
};

/// Owning zero-based CSC3 representation of a symmetric matrix's upper triangle.
struct Csc3Matrix {
    /// Number of matrix rows and columns.
    GlobalDofIndex dimension = 0;
    /// Zero-based offsets into row_indices and values, with one terminal offset.
    std::vector<Offset> column_offsets;
    /// Owned zero-based row indices, strictly increasing within each column.
    std::vector<GlobalDofIndex> row_indices;
    /// Owned stored values corresponding one-to-one with row_indices.
    std::vector<double> values;
};

/// Owning canonical topology and zero-based numeric scatter plan.
struct AssemblyPlan {
    /// Element identifiers in strictly increasing canonical order.
    std::vector<ElementId> element_ids;
    /// Zero-based offsets into global_dof_indices, with one terminal offset.
    std::vector<Offset> element_dof_offsets;
    /// Owned zero-based global DOF indices in preserved local order.
    std::vector<GlobalDofIndex> global_dof_indices;
    /// Zero-based offsets into scatter_indices, with one terminal offset.
    std::vector<Offset> element_scatter_offsets;
    /// Owned zero-based target offsets into Csc3Matrix::values.
    std::vector<Offset> scatter_indices;
};

/// Owns a CSC3 matrix and plan; concurrent access to one instance is unsupported.
class SymmetricCscAssembler {
  public:
    /// Copies the topology and owns a canonical plan, replacing prior state on success.
    /// @throws std::invalid_argument for invalid topology or a nonpositive thread count.
    void build_symbolic_parallel(const ElementDofMap& element_dof_map, int thread_count);
    /// Reads without retaining one complete batch and overwrites all stored values.
    /// @throws std::logic_error if no symbolic plan exists.
    /// @throws std::invalid_argument for invalid values, layout, or thread count.
    void assemble_numeric_atomic(const ElementMatrixBatch& element_matrices, int thread_count);
    /// Returns assembler-owned matrix state for this assembler's lifetime.
    /// Mutating calls may replace the referenced object's vector contents.
    [[nodiscard]] const Csc3Matrix& matrix() const noexcept;
    /// Returns the assembler-owned plan for this assembler's lifetime.
    /// Symbolic mutation may replace the referenced object's vector contents.
    [[nodiscard]] const AssemblyPlan& assembly_plan() const noexcept;
    /// Returns the largest team size observed by the last successful symbolic call.
    [[nodiscard]] int symbolic_thread_count_used() const noexcept;
    /// Returns the team size observed by the last successful numeric call.
    [[nodiscard]] int numeric_thread_count_used() const noexcept;

  private:
    struct BenchmarkTimings {
        double symbolic_pattern_ms = 0.0;
        double symbolic_scatter_ms = 0.0;
        double symbolic_total_ms = 0.0;
        double numeric_reset_ms = 0.0;
        double numeric_kernel_ms = 0.0;
        double numeric_total_ms = 0.0;
    };

    friend struct evidence::BenchmarkAccess;

    Csc3Matrix matrix_;
    AssemblyPlan assembly_plan_;
    BenchmarkTimings benchmark_timings_;
    int symbolic_thread_count_used_ = 0;
    int numeric_thread_count_used_ = 0;
    bool symbolic_used_requested_team_in_all_regions_ = false;
    bool numeric_used_requested_team_ = false;
    bool symbolic_ready_ = false;
};

/// Reports whether this build includes the required OpenMP execution path.
[[nodiscard]] bool openmp_enabled() noexcept;
/// Returns the calling thread's current OpenMP maximum team-size setting.
[[nodiscard]] int max_openmp_threads() noexcept;

} // namespace csc3_demo
