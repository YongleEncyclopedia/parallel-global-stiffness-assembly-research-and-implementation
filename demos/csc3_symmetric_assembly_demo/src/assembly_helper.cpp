#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#ifndef _OPENMP
#error "The CSC3 demo requires OpenMP"
#endif

#include <omp.h>

namespace csc3_demo {
namespace {

constexpr double kSymmetryAbsoluteTolerance = 1.0e-12;
constexpr double kSymmetryRelativeTolerance = 1.0e-10;

using SteadyClock = std::chrono::steady_clock;

static_assert(std::is_nothrow_move_assignable_v<Csc3Matrix>);
static_assert(std::is_nothrow_move_assignable_v<AssemblyPlan>);

double elapsed_milliseconds(SteadyClock::time_point start,
                            SteadyClock::time_point end) noexcept {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

std::size_t checked_size_add(std::size_t left,
                             std::size_t right,
                             const char* label) {
    if (right > std::numeric_limits<std::size_t>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

Offset checked_offset_add(Offset left, Offset right, const char* label) {
    if (right > std::numeric_limits<Offset>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

Offset checked_offset_multiply(Offset left, Offset right, const char* label) {
    if (left != 0 && right > std::numeric_limits<Offset>::max() / left) {
        throw_overflow(label);
    }
    return left * right;
}

Offset checked_triangular_count(Offset dimension) {
    const Offset successor = checked_offset_add(dimension, 1, "element scatter count");
    if (dimension % 2 == 0) {
        return checked_offset_multiply(dimension / 2,
                                       successor,
                                       "element scatter count");
    }
    return checked_offset_multiply(dimension,
                                   successor / 2,
                                   "element scatter count");
}

Offset size_to_offset(std::size_t value, const char* label) {
    if constexpr (std::numeric_limits<std::size_t>::digits >
                  std::numeric_limits<Offset>::digits) {
        if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<Offset>(value);
}

std::size_t offset_to_size(Offset value, const char* label) {
    if constexpr (std::numeric_limits<Offset>::digits >
                  std::numeric_limits<std::size_t>::digits) {
        if (value > static_cast<Offset>(std::numeric_limits<std::size_t>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<std::size_t>(value);
}

GlobalDofIndex size_to_dimension(std::size_t value) {
    if (value > static_cast<std::size_t>(std::numeric_limits<GlobalDofIndex>::max())) {
        throw_overflow("matrix dimension");
    }
    return static_cast<GlobalDofIndex>(value);
}

std::int64_t size_to_parallel_bound(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max())) {
        throw_overflow(label);
    }
    return static_cast<std::int64_t>(value);
}

template <typename T>
void ensure_vector_size(std::size_t count, const char* label) {
    const std::vector<T> probe;
    if (count > probe.max_size()) {
        throw_overflow(label);
    }
}

struct ValidatedTopology {
    AssemblyPlan plan;
    GlobalDofIndex dimension = 0;
};

ValidatedTopology validate_and_canonicalize(const ElementDofMap& input) {
    if (input.element_ids.empty()) {
        throw std::invalid_argument("element_dof_map must contain at least one element");
    }

    const std::size_t expected_offset_count =
        checked_size_add(input.element_ids.size(), 1, "element DOF offset count");
    if (input.element_dof_offsets.size() != expected_offset_count) {
        throw std::invalid_argument(
            "element_dof_offsets must contain one entry per element plus one");
    }
    if (input.element_dof_offsets.front() != 0) {
        throw std::invalid_argument("element_dof_offsets must start at zero");
    }
    for (std::size_t index = 1; index < input.element_dof_offsets.size(); ++index) {
        if (input.element_dof_offsets[index] < input.element_dof_offsets[index - 1]) {
            throw std::invalid_argument("element_dof_offsets must be monotone");
        }
    }
    if (input.element_dof_offsets.back() !=
        size_to_offset(input.global_dof_indices.size(), "global DOF array size")) {
        throw std::invalid_argument(
            "the final element DOF offset must equal global_dof_indices.size()");
    }

    ensure_vector_size<std::size_t>(input.element_ids.size(), "element ordinal array");
    std::vector<std::size_t> canonical_ordinals(input.element_ids.size());
    std::iota(canonical_ordinals.begin(), canonical_ordinals.end(), std::size_t{0});
    for (const ElementId element_id : input.element_ids) {
        if (element_id < 0) {
            throw std::invalid_argument("element IDs must be nonnegative");
        }
    }
    std::sort(canonical_ordinals.begin(),
              canonical_ordinals.end(),
              [&input](std::size_t left, std::size_t right) {
                  return input.element_ids[left] < input.element_ids[right];
              });
    for (std::size_t index = 1; index < canonical_ordinals.size(); ++index) {
        if (input.element_ids[canonical_ordinals[index - 1]] ==
            input.element_ids[canonical_ordinals[index]]) {
            throw std::invalid_argument("element IDs must be unique");
        }
    }

    for (const GlobalDofIndex dof : input.global_dof_indices) {
        if (dof < 0) {
            throw std::invalid_argument("global DOF indices must be nonnegative");
        }
    }

    ensure_vector_size<GlobalDofIndex>(input.global_dof_indices.size(),
                                       "global DOF validation array");
    std::vector<GlobalDofIndex> unique_dofs = input.global_dof_indices;
    std::sort(unique_dofs.begin(), unique_dofs.end());
    unique_dofs.erase(std::unique(unique_dofs.begin(), unique_dofs.end()),
                      unique_dofs.end());
    if (unique_dofs.empty()) {
        throw std::invalid_argument("elements must collectively own at least one global DOF");
    }
    const GlobalDofIndex dimension = size_to_dimension(unique_dofs.size());
    for (std::size_t index = 0; index < unique_dofs.size(); ++index) {
        if (unique_dofs[index] != static_cast<GlobalDofIndex>(index)) {
            throw std::invalid_argument(
                "global DOF indices must form compact numbering 0..dimension-1");
        }
    }

    for (std::size_t element = 0; element < input.element_ids.size(); ++element) {
        const Offset begin_offset = input.element_dof_offsets[element];
        const Offset end_offset = input.element_dof_offsets[element + 1];
        if (begin_offset == end_offset) {
            throw std::invalid_argument("each element must own at least one DOF");
        }
        const std::size_t begin = offset_to_size(begin_offset, "element DOF offset");
        const std::size_t end = offset_to_size(end_offset, "element DOF offset");
        const std::size_t local_dimension = end - begin;
        ensure_vector_size<GlobalDofIndex>(local_dimension,
                                           "local DOF validation array");
        std::vector<GlobalDofIndex> local_dofs(input.global_dof_indices.begin() +
                                                   static_cast<std::ptrdiff_t>(begin),
                                               input.global_dof_indices.begin() +
                                                   static_cast<std::ptrdiff_t>(end));
        std::sort(local_dofs.begin(), local_dofs.end());
        if (std::adjacent_find(local_dofs.begin(), local_dofs.end()) != local_dofs.end()) {
            throw std::invalid_argument("an element contains duplicate local DOFs");
        }
    }

    ValidatedTopology result;
    result.dimension = dimension;
    ensure_vector_size<ElementId>(input.element_ids.size(), "canonical element ID array");
    ensure_vector_size<Offset>(expected_offset_count, "canonical element offset array");
    ensure_vector_size<GlobalDofIndex>(input.global_dof_indices.size(),
                                       "canonical global DOF array");
    result.plan.element_ids.reserve(input.element_ids.size());
    result.plan.element_dof_offsets.reserve(expected_offset_count);
    result.plan.global_dof_indices.reserve(input.global_dof_indices.size());
    result.plan.element_dof_offsets.push_back(0);

    for (const std::size_t input_ordinal : canonical_ordinals) {
        const std::size_t begin = offset_to_size(
            input.element_dof_offsets[input_ordinal], "element DOF offset");
        const std::size_t end = offset_to_size(
            input.element_dof_offsets[input_ordinal + 1], "element DOF offset");
        result.plan.element_ids.push_back(input.element_ids[input_ordinal]);
        result.plan.global_dof_indices.insert(
            result.plan.global_dof_indices.end(),
            input.global_dof_indices.begin() + static_cast<std::ptrdiff_t>(begin),
            input.global_dof_indices.begin() + static_cast<std::ptrdiff_t>(end));
        result.plan.element_dof_offsets.push_back(
            size_to_offset(result.plan.global_dof_indices.size(),
                           "canonical element DOF offset"));
    }

    return result;
}

bool materially_nonsymmetric(double upper, double lower) noexcept {
    const double difference = std::abs(upper - lower);
    const double scale = std::max(std::abs(upper), std::abs(lower));
    return difference > kSymmetryAbsoluteTolerance &&
           difference > kSymmetryRelativeTolerance * scale;
}

} // namespace

void SymmetricCscAssembler::build_symbolic_parallel(
    const ElementDofMap& element_dof_map,
    int thread_count) {
    const SteadyClock::time_point symbolic_total_start = SteadyClock::now();
    BenchmarkTimings candidate_timings{};
    {
        if (thread_count <= 0) {
            throw std::invalid_argument("thread_count must be positive");
        }

        ValidatedTopology validated = validate_and_canonicalize(element_dof_map);
        AssemblyPlan new_plan = std::move(validated.plan);
        Csc3Matrix new_matrix;
        new_matrix.dimension = validated.dimension;

        const SteadyClock::time_point symbolic_pattern_start = SteadyClock::now();
        const std::size_t dimension = static_cast<std::size_t>(new_matrix.dimension);
        const std::size_t dimension_plus_one =
            checked_size_add(dimension, 1, "DOF adjacency offset count");
        ensure_vector_size<Offset>(dimension_plus_one, "DOF adjacency offsets");
        std::vector<Offset> dof_element_offsets(dimension_plus_one, 0);

        for (const GlobalDofIndex dof : new_plan.global_dof_indices) {
            const std::size_t next = static_cast<std::size_t>(dof) + 1;
            dof_element_offsets[next] =
                checked_offset_add(dof_element_offsets[next], 1, "DOF incidence count");
        }
        for (std::size_t dof = 0; dof < dimension; ++dof) {
            dof_element_offsets[dof + 1] = checked_offset_add(
                dof_element_offsets[dof], dof_element_offsets[dof + 1], "DOF adjacency prefix");
        }

        const std::size_t incidence_count = new_plan.global_dof_indices.size();
        if (dof_element_offsets.back() !=
            size_to_offset(incidence_count, "DOF incidence array size")) {
            throw std::logic_error("DOF adjacency count does not match the canonical plan");
        }
        ensure_vector_size<Offset>(incidence_count, "DOF adjacency array");
        std::vector<Offset> dof_elements(incidence_count, 0);
        std::vector<Offset> fill_positions = dof_element_offsets;
        for (std::size_t element = 0; element < new_plan.element_ids.size(); ++element) {
            const std::size_t begin = offset_to_size(new_plan.element_dof_offsets[element],
                                                     "canonical element DOF offset");
            const std::size_t end = offset_to_size(new_plan.element_dof_offsets[element + 1],
                                                   "canonical element DOF offset");
            const Offset element_offset = size_to_offset(element, "canonical element ordinal");
            for (std::size_t local = begin; local < end; ++local) {
                const std::size_t dof =
                    static_cast<std::size_t>(new_plan.global_dof_indices[local]);
                const std::size_t target =
                    offset_to_size(fill_positions[dof], "DOF adjacency fill position");
                dof_elements[target] = element_offset;
                fill_positions[dof] =
                    checked_offset_add(fill_positions[dof], 1, "DOF adjacency fill position");
            }
        }

        ensure_vector_size<std::vector<GlobalDofIndex>>(dimension, "CSC3 column work array");
        std::vector<std::vector<GlobalDofIndex>> column_rows(dimension);
        for (std::size_t column = 0; column < dimension; ++column) {
            std::size_t candidate_count = 0;
            for (Offset position = dof_element_offsets[column];
                 position < dof_element_offsets[column + 1]; ++position) {
                const std::size_t element =
                    offset_to_size(dof_elements[offset_to_size(position, "DOF adjacency position")],
                                   "canonical element ordinal");
                const Offset local_dimension = new_plan.element_dof_offsets[element + 1] -
                                               new_plan.element_dof_offsets[element];
                candidate_count = checked_size_add(
                    candidate_count, offset_to_size(local_dimension, "local element dimension"),
                    "CSC3 column candidate count");
            }
            ensure_vector_size<GlobalDofIndex>(candidate_count, "CSC3 column candidates");
            column_rows[column].reserve(candidate_count);
        }

        int column_team_size = 0;
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                column_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (GlobalDofIndex column = 0; column < new_matrix.dimension; ++column) {
                auto& rows = column_rows[static_cast<std::size_t>(column)];
                const std::size_t column_index = static_cast<std::size_t>(column);
                for (Offset position = dof_element_offsets[column_index];
                     position < dof_element_offsets[column_index + 1]; ++position) {
                    const std::size_t element =
                        static_cast<std::size_t>(dof_elements[static_cast<std::size_t>(position)]);
                    const std::size_t begin =
                        static_cast<std::size_t>(new_plan.element_dof_offsets[element]);
                    const std::size_t end =
                        static_cast<std::size_t>(new_plan.element_dof_offsets[element + 1]);
                    for (std::size_t local = begin; local < end; ++local) {
                        const GlobalDofIndex row = new_plan.global_dof_indices[local];
                        if (row <= column) {
                            rows.push_back(row);
                        }
                    }
                }
                std::sort(rows.begin(), rows.end());
                rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
            }
        }

        ensure_vector_size<Offset>(dimension_plus_one, "CSC3 column offsets");
        new_matrix.column_offsets.assign(dimension_plus_one, 0);
        for (std::size_t column = 0; column < dimension; ++column) {
            new_matrix.column_offsets[column + 1] =
                checked_offset_add(new_matrix.column_offsets[column],
                                   size_to_offset(column_rows[column].size(), "CSC3 column length"),
                                   "CSC3 nonzero count");
        }

        const std::size_t nonzero_count =
            offset_to_size(new_matrix.column_offsets.back(), "CSC3 nonzero count");
        ensure_vector_size<GlobalDofIndex>(nonzero_count, "CSC3 row indices");
        ensure_vector_size<double>(nonzero_count, "CSC3 values");
        new_matrix.row_indices.assign(nonzero_count, 0);
        new_matrix.values.assign(nonzero_count, 0.0);

        int row_fill_team_size = 0;
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                row_fill_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (GlobalDofIndex column = 0; column < new_matrix.dimension; ++column) {
                const std::size_t column_index = static_cast<std::size_t>(column);
                const std::size_t begin =
                    static_cast<std::size_t>(new_matrix.column_offsets[column_index]);
                const auto& rows = column_rows[column_index];
                for (std::size_t row = 0; row < rows.size(); ++row) {
                    new_matrix.row_indices[begin + row] = rows[row];
                }
            }
        }

        const SteadyClock::time_point symbolic_pattern_end = SteadyClock::now();
        candidate_timings.symbolic_pattern_ms =
            elapsed_milliseconds(symbolic_pattern_start, symbolic_pattern_end);

        const SteadyClock::time_point symbolic_scatter_start = SteadyClock::now();
        const std::size_t element_count = new_plan.element_ids.size();
        const std::size_t scatter_offset_count =
            checked_size_add(element_count, 1, "element scatter offset count");
        ensure_vector_size<Offset>(scatter_offset_count, "element scatter offsets");
        new_plan.element_scatter_offsets.assign(scatter_offset_count, 0);
        for (std::size_t element = 0; element < element_count; ++element) {
            const Offset local_dimension =
                new_plan.element_dof_offsets[element + 1] - new_plan.element_dof_offsets[element];
            const Offset local_scatter_count = checked_triangular_count(local_dimension);
            new_plan.element_scatter_offsets[element + 1] =
                checked_offset_add(new_plan.element_scatter_offsets[element], local_scatter_count,
                                   "total element scatter count");
        }

        const std::size_t scatter_count =
            offset_to_size(new_plan.element_scatter_offsets.back(), "total element scatter count");
        ensure_vector_size<Offset>(scatter_count, "element scatter indices");
        new_plan.scatter_indices.assign(scatter_count, 0);
        const std::int64_t parallel_element_count =
            size_to_parallel_bound(element_count, "parallel element count");
        std::atomic<bool> scatter_failure{false};
        int scatter_team_size = 0;
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                scatter_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (std::int64_t element_loop = 0; element_loop < parallel_element_count;
                 ++element_loop) {
                const std::size_t element = static_cast<std::size_t>(element_loop);
                const std::size_t dof_begin =
                    static_cast<std::size_t>(new_plan.element_dof_offsets[element]);
                const std::size_t dof_end =
                    static_cast<std::size_t>(new_plan.element_dof_offsets[element + 1]);
                std::size_t scatter_position =
                    static_cast<std::size_t>(new_plan.element_scatter_offsets[element]);

                for (std::size_t local_row = dof_begin; local_row < dof_end; ++local_row) {
                    for (std::size_t local_column = local_row; local_column < dof_end;
                         ++local_column) {
                        const GlobalDofIndex first_dof = new_plan.global_dof_indices[local_row];
                        const GlobalDofIndex second_dof = new_plan.global_dof_indices[local_column];
                        const GlobalDofIndex row = std::min(first_dof, second_dof);
                        const GlobalDofIndex column = std::max(first_dof, second_dof);
                        const std::size_t column_index = static_cast<std::size_t>(column);
                        const std::size_t column_begin =
                            static_cast<std::size_t>(new_matrix.column_offsets[column_index]);
                        const std::size_t column_end =
                            static_cast<std::size_t>(new_matrix.column_offsets[column_index + 1]);
                        const auto begin = new_matrix.row_indices.begin() +
                                           static_cast<std::ptrdiff_t>(column_begin);
                        const auto end = new_matrix.row_indices.begin() +
                                         static_cast<std::ptrdiff_t>(column_end);
                        const auto found = std::lower_bound(begin, end, row);
                        if (found == end || *found != row ||
                            scatter_position >= new_plan.scatter_indices.size()) {
                            scatter_failure.store(true, std::memory_order_relaxed);
                        } else {
                            const std::size_t local_position =
                                static_cast<std::size_t>(found - begin);
                            new_plan.scatter_indices[scatter_position] =
                                static_cast<Offset>(column_begin + local_position);
                        }
                        ++scatter_position;
                    }
                }
                if (scatter_position !=
                    static_cast<std::size_t>(new_plan.element_scatter_offsets[element + 1])) {
                    scatter_failure.store(true, std::memory_order_relaxed);
                }
            }
        }

        if (scatter_failure.load(std::memory_order_relaxed)) {
            throw std::logic_error("failed to locate an element entry in the CSC3 structure");
        }
        const SteadyClock::time_point symbolic_scatter_end = SteadyClock::now();
        candidate_timings.symbolic_scatter_ms =
            elapsed_milliseconds(symbolic_scatter_start, symbolic_scatter_end);

        matrix_ = std::move(new_matrix);
        assembly_plan_ = std::move(new_plan);
        symbolic_thread_count_used_ =
            std::max({column_team_size, row_fill_team_size, scatter_team_size});
        numeric_thread_count_used_ = 0;
        symbolic_used_requested_team_in_all_regions_ = column_team_size == thread_count &&
                                                       row_fill_team_size == thread_count &&
                                                       scatter_team_size == thread_count;
        numeric_used_requested_team_ = false;
        symbolic_ready_ = true;
    }
    candidate_timings.symbolic_total_ms =
        elapsed_milliseconds(symbolic_total_start, SteadyClock::now());
    benchmark_timings_ = candidate_timings;
}

void SymmetricCscAssembler::assemble_numeric_atomic(
    const ElementMatrixBatch& element_matrices,
    int thread_count) {
    const SteadyClock::time_point numeric_total_start = SteadyClock::now();
    BenchmarkTimings candidate_timings = benchmark_timings_;
    {
        if (thread_count <= 0) {
            throw std::invalid_argument("thread_count must be positive");
        }
        if (!symbolic_ready_) {
            throw std::logic_error("numeric assembly requires a completed symbolic plan");
        }

        const std::size_t element_count = assembly_plan_.element_ids.size();
        const std::size_t expected_offset_count =
            checked_size_add(element_count, 1, "element matrix offset count");
        if (element_matrices.element_value_offsets.size() != expected_offset_count) {
            throw std::invalid_argument("element_value_offsets must contain one "
                                        "entry per canonical element plus one");
        }
        if (element_matrices.element_value_offsets.front() != 0) {
            throw std::invalid_argument("element_value_offsets must start at zero");
        }
        for (std::size_t index = 1; index < element_matrices.element_value_offsets.size();
             ++index) {
            if (element_matrices.element_value_offsets[index] <
                element_matrices.element_value_offsets[index - 1]) {
                throw std::invalid_argument("element_value_offsets must be monotone");
            }
        }
        if (element_matrices.element_value_offsets.back() !=
            size_to_offset(element_matrices.values_row_major.size(),
                           "element matrix value array size")) {
            throw std::invalid_argument(
                "the final element value offset must equal values_row_major.size()");
        }

        ensure_vector_size<std::size_t>(element_count, "numeric local dimensions");
        std::vector<std::size_t> local_dimensions(element_count, 0);
        std::vector<std::size_t> value_begins(element_count, 0);
        std::vector<std::size_t> scatter_begins(element_count, 0);

        for (std::size_t element = 0; element < element_count; ++element) {
            const Offset local_dimension_offset = assembly_plan_.element_dof_offsets[element + 1] -
                                                  assembly_plan_.element_dof_offsets[element];
            const Offset expected_segment_size = checked_offset_multiply(
                local_dimension_offset, local_dimension_offset, "element matrix segment size");
            const Offset actual_segment_size = element_matrices.element_value_offsets[element + 1] -
                                               element_matrices.element_value_offsets[element];
            if (actual_segment_size != expected_segment_size) {
                throw std::invalid_argument("each element matrix segment must contain "
                                            "exactly local_dimension squared values");
            }

            const std::size_t local_dimension =
                offset_to_size(local_dimension_offset, "numeric local dimension");
            const std::size_t value_begin = offset_to_size(
                element_matrices.element_value_offsets[element], "element matrix value offset");
            local_dimensions[element] = local_dimension;
            value_begins[element] = value_begin;
            scatter_begins[element] = offset_to_size(
                assembly_plan_.element_scatter_offsets[element], "element scatter offset");

            for (std::size_t row = 0; row < local_dimension; ++row) {
                for (std::size_t column = 0; column < local_dimension; ++column) {
                    const double value =
                        element_matrices
                            .values_row_major[value_begin + row * local_dimension + column];
                    if (!std::isfinite(value)) {
                        throw std::invalid_argument(
                            "element matrices must contain only finite values");
                    }
                }
            }
            for (std::size_t row = 0; row < local_dimension; ++row) {
                for (std::size_t column = row + 1; column < local_dimension; ++column) {
                    const double upper =
                        element_matrices
                            .values_row_major[value_begin + row * local_dimension + column];
                    const double lower =
                        element_matrices
                            .values_row_major[value_begin + column * local_dimension + row];
                    if (materially_nonsymmetric(upper, lower)) {
                        throw std::invalid_argument(
                            "element matrices must be symmetric within combined tolerance");
                    }
                }
            }
        }

        const Offset matrix_value_count =
            size_to_offset(matrix_.values.size(), "CSC3 value array size");
        for (const Offset target : assembly_plan_.scatter_indices) {
            if (target >= matrix_value_count) {
                throw std::logic_error("assembly plan contains an out-of-range scatter index");
            }
        }

        const std::int64_t parallel_element_count =
            size_to_parallel_bound(element_count, "parallel element count");
        const SteadyClock::time_point numeric_reset_start = SteadyClock::now();
        std::fill(matrix_.values.begin(), matrix_.values.end(), 0.0);
        const SteadyClock::time_point numeric_reset_end = SteadyClock::now();
        candidate_timings.numeric_reset_ms =
            elapsed_milliseconds(numeric_reset_start, numeric_reset_end);

        int numeric_team_size = 0;
        const SteadyClock::time_point numeric_kernel_start = SteadyClock::now();
#pragma omp parallel num_threads(thread_count)
        {
#pragma omp single
            {
                numeric_team_size = omp_get_num_threads();
            }

#pragma omp for schedule(static)
            for (std::int64_t element_loop = 0; element_loop < parallel_element_count;
                 ++element_loop) {
                const std::size_t element = static_cast<std::size_t>(element_loop);
                const std::size_t local_dimension = local_dimensions[element];
                const std::size_t value_begin = value_begins[element];
                std::size_t scatter_position = scatter_begins[element];
                for (std::size_t row = 0; row < local_dimension; ++row) {
                    for (std::size_t column = row; column < local_dimension; ++column) {
                        const std::size_t target = static_cast<std::size_t>(
                            assembly_plan_.scatter_indices[scatter_position++]);
                        const double value =
                            element_matrices
                                .values_row_major[value_begin + row * local_dimension + column];
#pragma omp atomic
                        matrix_.values[target] += value;
                    }
                }
            }
        }
        const SteadyClock::time_point numeric_kernel_end = SteadyClock::now();
        candidate_timings.numeric_kernel_ms =
            elapsed_milliseconds(numeric_kernel_start, numeric_kernel_end);
        numeric_thread_count_used_ = numeric_team_size;
        numeric_used_requested_team_ = numeric_team_size == thread_count;
    }
    candidate_timings.numeric_total_ms =
        elapsed_milliseconds(numeric_total_start, SteadyClock::now());
    benchmark_timings_ = candidate_timings;
}

const Csc3Matrix& SymmetricCscAssembler::matrix() const noexcept {
    return matrix_;
}

const AssemblyPlan& SymmetricCscAssembler::assembly_plan() const noexcept {
    return assembly_plan_;
}

int SymmetricCscAssembler::symbolic_thread_count_used() const noexcept {
    return symbolic_thread_count_used_;
}

int SymmetricCscAssembler::numeric_thread_count_used() const noexcept {
    return numeric_thread_count_used_;
}

bool openmp_enabled() noexcept {
    return true;
}

int max_openmp_threads() noexcept {
    return omp_get_max_threads();
}

} // namespace csc3_demo
