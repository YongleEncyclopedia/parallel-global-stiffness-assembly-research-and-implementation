#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace csc3_demo::evidence {
namespace {

constexpr double kRelativeFrobeniusTolerance = 1.0e-8;
constexpr double kMaximumAbsoluteBaseTolerance = 1.0e-10;
constexpr double kMaximumAbsoluteScaleTolerance = 1.0e-8;
constexpr double kRelativeDisplacementTolerance = 1.0e-8;
constexpr double kRelativeResidualTolerance = 1.0e-10;
constexpr double kSymmetryAbsoluteTolerance = 1.0e-12;
constexpr double kSymmetryRelativeTolerance = 1.0e-10;

[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

std::size_t checked_add(std::size_t left,
                        std::size_t right,
                        const char* label) {
    if (right > std::numeric_limits<std::size_t>::max() - left) {
        throw_overflow(label);
    }
    return left + right;
}

std::size_t checked_multiply(std::size_t left,
                             std::size_t right,
                             const char* label) {
    if (left != 0 && right > std::numeric_limits<std::size_t>::max() / left) {
        throw_overflow(label);
    }
    return left * right;
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

Offset size_to_offset(std::size_t value, const char* label) {
    if constexpr (std::numeric_limits<std::size_t>::digits >
                  std::numeric_limits<Offset>::digits) {
        if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<Offset>(value);
}

GlobalDofIndex size_to_dimension(std::size_t value) {
    if (value > static_cast<std::size_t>(
                    std::numeric_limits<GlobalDofIndex>::max())) {
        throw_overflow("matrix dimension");
    }
    return static_cast<GlobalDofIndex>(value);
}

bool materially_nonsymmetric(double upper, double lower) {
    const double difference = std::abs(upper - lower);
    const double scale = std::max(std::abs(upper), std::abs(lower));
    return difference > kSymmetryAbsoluteTolerance &&
           difference > kSymmetryRelativeTolerance * scale;
}

struct ValidatedCase {
    GlobalDofIndex dimension = 0;
    std::vector<std::size_t> canonical_ordinals;
    std::vector<std::size_t> local_dimensions;
};

ValidatedCase validate_reference_input(const AssemblyCase& assembly_case) {
    for (const Node& node : assembly_case.nodes) {
        if (!std::isfinite(node.x) || !std::isfinite(node.y) ||
            !std::isfinite(node.z)) {
            throw std::invalid_argument("nodes must contain only finite coordinates");
        }
    }

    const ElementDofMap& topology = assembly_case.element_dof_map;
    const std::size_t element_count = topology.element_ids.size();
    if (element_count == 0) {
        throw std::invalid_argument("element_dof_map must contain at least one element");
    }
    const std::size_t expected_offset_count =
        checked_add(element_count, 1, "element offset count");
    if (topology.element_dof_offsets.size() != expected_offset_count) {
        throw std::invalid_argument(
            "element_dof_offsets must contain one entry per element plus one");
    }
    if (topology.element_dof_offsets.front() != 0) {
        throw std::invalid_argument("element_dof_offsets must start at zero");
    }
    for (std::size_t index = 1; index < topology.element_dof_offsets.size(); ++index) {
        if (topology.element_dof_offsets[index] <
            topology.element_dof_offsets[index - 1]) {
            throw std::invalid_argument("element_dof_offsets must be monotone");
        }
    }
    if (topology.element_dof_offsets.back() !=
        size_to_offset(topology.global_dof_indices.size(),
                       "global DOF array size")) {
        throw std::invalid_argument(
            "the final element DOF offset must equal global_dof_indices.size()");
    }

    ValidatedCase validated;
    validated.canonical_ordinals.resize(element_count);
    std::iota(validated.canonical_ordinals.begin(),
              validated.canonical_ordinals.end(),
              std::size_t{0});
    for (const ElementId element_id : topology.element_ids) {
        if (element_id < 0) {
            throw std::invalid_argument("element IDs must be nonnegative");
        }
    }
    std::sort(validated.canonical_ordinals.begin(),
              validated.canonical_ordinals.end(),
              [&topology](std::size_t left, std::size_t right) {
                  return topology.element_ids[left] < topology.element_ids[right];
              });
    for (std::size_t index = 1;
         index < validated.canonical_ordinals.size();
         ++index) {
        if (topology.element_ids[validated.canonical_ordinals[index - 1]] ==
            topology.element_ids[validated.canonical_ordinals[index]]) {
            throw std::invalid_argument("element IDs must be unique");
        }
    }

    std::set<GlobalDofIndex> unique_global_dofs;
    std::vector<std::size_t> input_local_dimensions(element_count, 0);
    for (std::size_t element = 0; element < element_count; ++element) {
        const std::size_t begin = offset_to_size(
            topology.element_dof_offsets[element], "element DOF offset");
        const std::size_t end = offset_to_size(
            topology.element_dof_offsets[element + 1], "element DOF offset");
        if (begin == end) {
            throw std::invalid_argument("each element must contain at least one DOF");
        }
        input_local_dimensions[element] = end - begin;
        std::set<GlobalDofIndex> local_dofs;
        for (std::size_t position = begin; position < end; ++position) {
            const GlobalDofIndex dof = topology.global_dof_indices[position];
            if (dof < 0) {
                throw std::invalid_argument("global DOF indices must be nonnegative");
            }
            if (!local_dofs.insert(dof).second) {
                throw std::invalid_argument("an element contains duplicate local DOFs");
            }
            unique_global_dofs.insert(dof);
        }
    }
    if (unique_global_dofs.empty()) {
        throw std::invalid_argument("topology must contain at least one global DOF");
    }
    std::size_t expected_dof = 0;
    for (const GlobalDofIndex dof : unique_global_dofs) {
        if (static_cast<std::size_t>(dof) != expected_dof) {
            throw std::invalid_argument(
                "global DOF indices must form compact numbering 0..dimension-1");
        }
        ++expected_dof;
    }
    validated.dimension = size_to_dimension(unique_global_dofs.size());

    const ElementMatrixBatch& matrices = assembly_case.element_matrices;
    if (matrices.element_value_offsets.size() != expected_offset_count) {
        throw std::invalid_argument(
            "element_value_offsets must contain one entry per canonical element plus one");
    }
    if (matrices.element_value_offsets.front() != 0) {
        throw std::invalid_argument("element_value_offsets must start at zero");
    }
    for (std::size_t index = 1;
         index < matrices.element_value_offsets.size();
         ++index) {
        if (matrices.element_value_offsets[index] <
            matrices.element_value_offsets[index - 1]) {
            throw std::invalid_argument("element_value_offsets must be monotone");
        }
    }
    if (matrices.element_value_offsets.back() !=
        size_to_offset(matrices.values_row_major.size(),
                       "element matrix value array size")) {
        throw std::invalid_argument(
            "the final element value offset must equal values_row_major.size()");
    }

    validated.local_dimensions.reserve(element_count);
    for (std::size_t canonical = 0; canonical < element_count; ++canonical) {
        const std::size_t input_ordinal = validated.canonical_ordinals[canonical];
        const std::size_t local_dimension =
            input_local_dimensions[input_ordinal];
        validated.local_dimensions.push_back(local_dimension);
        const std::size_t expected_matrix_size = checked_multiply(
            local_dimension, local_dimension, "local matrix size");
        const Offset segment_size =
            matrices.element_value_offsets[canonical + 1] -
            matrices.element_value_offsets[canonical];
        if (offset_to_size(segment_size, "local matrix size") !=
            expected_matrix_size) {
            throw std::invalid_argument(
                "each matrix segment must contain local_dimension squared values");
        }
        const std::size_t matrix_begin = offset_to_size(
            matrices.element_value_offsets[canonical],
            "element matrix value offset");
        for (std::size_t row = 0; row < local_dimension; ++row) {
            for (std::size_t column = 0; column < local_dimension; ++column) {
                const double value = matrices.values_row_major[
                    matrix_begin + row * local_dimension + column];
                if (!std::isfinite(value)) {
                    throw std::invalid_argument(
                        "element matrices must contain only finite values");
                }
            }
        }
        for (std::size_t row = 0; row < local_dimension; ++row) {
            for (std::size_t column = row + 1;
                 column < local_dimension;
                 ++column) {
                const double upper = matrices.values_row_major[
                    matrix_begin + row * local_dimension + column];
                const double lower = matrices.values_row_major[
                    matrix_begin + column * local_dimension + row];
                if (materially_nonsymmetric(upper, lower)) {
                    throw std::invalid_argument("element matrices must be symmetric");
                }
            }
        }
    }
    return validated;
}

void validate_reference_result(const SerialAssemblyResult& reference) {
    if (reference.dimension < 0) {
        throw std::invalid_argument("reference dimension must be nonnegative");
    }
    const std::size_t dimension = static_cast<std::size_t>(reference.dimension);
    if (reference.column_offsets.size() !=
        checked_add(dimension, 1, "reference column offset count")) {
        throw std::invalid_argument("reference column_offsets has the wrong size");
    }
    if (reference.column_offsets.front() != 0 ||
        reference.column_offsets.back() !=
            size_to_offset(reference.row_indices.size(),
                           "reference row index count")) {
        throw std::invalid_argument("reference column_offsets is inconsistent");
    }
    for (std::size_t column = 0; column < dimension; ++column) {
        const std::size_t begin = offset_to_size(
            reference.column_offsets[column], "reference column offset");
        const std::size_t end = offset_to_size(
            reference.column_offsets[column + 1], "reference column offset");
        if (end < begin || end > reference.row_indices.size()) {
            throw std::invalid_argument("reference column offsets must be monotone");
        }
        GlobalDofIndex prior = -1;
        for (std::size_t position = begin; position < end; ++position) {
            const GlobalDofIndex row = reference.row_indices[position];
            if (row < 0 || row > static_cast<GlobalDofIndex>(column) ||
                row <= prior) {
                throw std::invalid_argument(
                    "reference rows must be strictly increasing upper entries");
            }
            prior = row;
        }
    }
    const std::size_t dense_size =
        checked_multiply(dimension, dimension, "reference dense matrix size");
    if (reference.dense_values.size() != dense_size) {
        throw std::invalid_argument("reference dense matrix has the wrong size");
    }
    if (!std::all_of(reference.dense_values.begin(),
                     reference.dense_values.end(),
                     [](double value) { return std::isfinite(value); })) {
        throw std::invalid_argument("reference dense matrix must be finite");
    }
}

bool validate_candidate_structure(const Csc3Matrix& candidate) {
    if (candidate.dimension < 0) {
        throw std::invalid_argument("candidate dimension must be nonnegative");
    }
    const std::size_t dimension = static_cast<std::size_t>(candidate.dimension);
    if (candidate.column_offsets.size() !=
        checked_add(dimension, 1, "candidate column offset count")) {
        throw std::invalid_argument("candidate column_offsets has the wrong size");
    }
    if (candidate.column_offsets.front() != 0 ||
        candidate.column_offsets.back() !=
            size_to_offset(candidate.row_indices.size(),
                           "candidate row index count") ||
        candidate.values.size() != candidate.row_indices.size()) {
        throw std::invalid_argument("candidate CSC3 arrays are inconsistent");
    }
    for (std::size_t column = 0; column < dimension; ++column) {
        const std::size_t begin = offset_to_size(
            candidate.column_offsets[column], "candidate column offset");
        const std::size_t end = offset_to_size(
            candidate.column_offsets[column + 1], "candidate column offset");
        if (end < begin || end > candidate.row_indices.size()) {
            throw std::invalid_argument("candidate column offsets must be monotone");
        }
        GlobalDofIndex prior = -1;
        for (std::size_t position = begin; position < end; ++position) {
            const GlobalDofIndex row = candidate.row_indices[position];
            if (row < 0 || row > static_cast<GlobalDofIndex>(column) ||
                row <= prior) {
                throw std::invalid_argument(
                    "candidate rows must be strictly increasing upper entries");
            }
            prior = row;
        }
    }
    return std::all_of(candidate.values.begin(),
                       candidate.values.end(),
                       [](double value) { return std::isfinite(value); });
}

class ScaledNorm {
public:
    void add(double value) {
        const double magnitude = std::abs(value);
        if (!std::isfinite(magnitude)) {
            finite_ = false;
            return;
        }
        if (magnitude == 0.0) {
            return;
        }
        if (scale_ < magnitude) {
            const double ratio = scale_ / magnitude;
            scaled_square_sum_ =
                1.0 + scaled_square_sum_ * ratio * ratio;
            scale_ = magnitude;
        } else {
            const double ratio = magnitude / scale_;
            scaled_square_sum_ += ratio * ratio;
        }
    }

    [[nodiscard]] bool finite() const noexcept {
        return finite_;
    }

    [[nodiscard]] bool zero() const noexcept {
        return scale_ == 0.0;
    }

    [[nodiscard]] double value() const {
        if (!finite_) {
            return std::numeric_limits<double>::infinity();
        }
        return scale_ * std::sqrt(scaled_square_sum_);
    }

    [[nodiscard]] double relative_to(const ScaledNorm& reference,
                                     double reference_floor) const {
        if (!finite_ || !reference.finite_) {
            return std::numeric_limits<double>::infinity();
        }
        if (zero()) {
            return 0.0;
        }
        if (reference.value() < reference_floor) {
            return value() / reference_floor;
        }
        return (scale_ / reference.scale_) *
               std::sqrt(scaled_square_sum_ /
                         reference.scaled_square_sum_);
    }

private:
    double scale_ = 0.0;
    double scaled_square_sum_ = 1.0;
    bool finite_ = true;
};

std::vector<double> expand_candidate_dense(const Csc3Matrix& candidate) {
    static_cast<void>(validate_candidate_structure(candidate));
    const std::size_t dimension = static_cast<std::size_t>(candidate.dimension);
    std::vector<double> dense(
        checked_multiply(dimension, dimension, "candidate dense matrix size"),
        0.0);
    for (std::size_t column = 0; column < dimension; ++column) {
        const std::size_t begin = static_cast<std::size_t>(
            candidate.column_offsets[column]);
        const std::size_t end = static_cast<std::size_t>(
            candidate.column_offsets[column + 1]);
        for (std::size_t position = begin; position < end; ++position) {
            const std::size_t row =
                static_cast<std::size_t>(candidate.row_indices[position]);
            const double value = candidate.values[position];
            dense[row * dimension + column] = value;
            dense[column * dimension + row] = value;
        }
    }
    return dense;
}

double vector_norm(const std::vector<double>& values) {
    ScaledNorm norm;
    for (const double value : values) {
        norm.add(value);
    }
    return norm.value();
}

std::vector<double> solve_dense_system(std::vector<double> matrix,
                                       std::vector<double> right_hand_side) {
    const std::size_t dimension = right_hand_side.size();
    if (matrix.size() !=
        checked_multiply(dimension, dimension, "free matrix size")) {
        throw std::invalid_argument("free matrix and force dimensions do not match");
    }
    if (dimension == 0) {
        return {};
    }
    if (!std::all_of(matrix.begin(), matrix.end(), [](double value) {
            return std::isfinite(value);
        }) ||
        !std::all_of(right_hand_side.begin(),
                     right_hand_side.end(),
                     [](double value) { return std::isfinite(value); })) {
        throw std::invalid_argument("free system must contain only finite values");
    }

    double matrix_scale = 0.0;
    for (const double value : matrix) {
        matrix_scale = std::max(matrix_scale, std::abs(value));
    }
    if (matrix_scale == 0.0) {
        throw std::runtime_error("free stiffness matrix is singular");
    }
    const double pivot_tolerance =
        128.0 * std::numeric_limits<double>::epsilon() *
        static_cast<double>(dimension) * matrix_scale;

    for (std::size_t column = 0; column < dimension; ++column) {
        std::size_t pivot_row = column;
        double pivot_magnitude =
            std::abs(matrix[column * dimension + column]);
        for (std::size_t row = column + 1; row < dimension; ++row) {
            const double candidate = std::abs(matrix[row * dimension + column]);
            if (candidate > pivot_magnitude) {
                pivot_magnitude = candidate;
                pivot_row = row;
            }
        }
        if (!std::isfinite(pivot_magnitude) ||
            pivot_magnitude <= pivot_tolerance) {
            throw std::runtime_error("free stiffness matrix is singular");
        }
        if (pivot_row != column) {
            for (std::size_t entry = column; entry < dimension; ++entry) {
                std::swap(matrix[column * dimension + entry],
                          matrix[pivot_row * dimension + entry]);
            }
            std::swap(right_hand_side[column], right_hand_side[pivot_row]);
        }

        const double pivot = matrix[column * dimension + column];
        for (std::size_t row = column + 1; row < dimension; ++row) {
            const double factor = matrix[row * dimension + column] / pivot;
            if (!std::isfinite(factor)) {
                throw std::runtime_error("free-system elimination became nonfinite");
            }
            matrix[row * dimension + column] = 0.0;
            for (std::size_t entry = column + 1; entry < dimension; ++entry) {
                matrix[row * dimension + entry] -=
                    factor * matrix[column * dimension + entry];
            }
            right_hand_side[row] -= factor * right_hand_side[column];
        }
    }

    std::vector<double> solution(dimension, 0.0);
    for (std::size_t reverse = 0; reverse < dimension; ++reverse) {
        const std::size_t row = dimension - reverse - 1;
        double value = right_hand_side[row];
        for (std::size_t column = row + 1; column < dimension; ++column) {
            value -= matrix[row * dimension + column] * solution[column];
        }
        const double pivot = matrix[row * dimension + row];
        if (!std::isfinite(pivot) || std::abs(pivot) <= pivot_tolerance) {
            throw std::runtime_error("free stiffness matrix is singular");
        }
        solution[row] = value / pivot;
        if (!std::isfinite(solution[row])) {
            throw std::runtime_error("free-system solution became nonfinite");
        }
    }
    return solution;
}

struct FreeSystem {
    std::vector<std::size_t> global_indices;
    std::vector<double> matrix;
    std::vector<double> force;
};

FreeSystem extract_free_system(const std::vector<double>& dense_matrix,
                               GlobalDofIndex dimension_value,
                               const std::vector<double>& force,
                               const std::vector<GlobalDofIndex>& constraints) {
    if (dimension_value < 0) {
        throw std::invalid_argument("global dimension must be nonnegative");
    }
    const std::size_t dimension = static_cast<std::size_t>(dimension_value);
    if (dense_matrix.size() !=
        checked_multiply(dimension, dimension, "global dense matrix size")) {
        throw std::invalid_argument(
            "dense matrix size must equal global_dimension squared");
    }
    if (force.size() != dimension) {
        throw std::invalid_argument("force size must equal the global dimension");
    }
    if (!std::all_of(force.begin(), force.end(), [](double value) {
            return std::isfinite(value);
        })) {
        throw std::invalid_argument("force must contain only finite values");
    }
    if (!std::is_sorted(constraints.begin(), constraints.end()) ||
        std::adjacent_find(constraints.begin(), constraints.end()) !=
            constraints.end()) {
        throw std::invalid_argument("constrained DOFs must be sorted and unique");
    }
    std::vector<bool> constrained(dimension, false);
    for (const GlobalDofIndex dof : constraints) {
        if (dof < 0 || dof >= dimension_value) {
            throw std::invalid_argument("constrained DOF is out of range");
        }
        constrained[static_cast<std::size_t>(dof)] = true;
    }

    FreeSystem result;
    for (std::size_t dof = 0; dof < dimension; ++dof) {
        if (!constrained[dof]) {
            result.global_indices.push_back(dof);
        }
    }
    const std::size_t free_dimension = result.global_indices.size();
    result.matrix.assign(
        checked_multiply(free_dimension, free_dimension, "free matrix size"),
        0.0);
    result.force.resize(free_dimension);
    for (std::size_t free_row = 0; free_row < free_dimension; ++free_row) {
        const std::size_t global_row = result.global_indices[free_row];
        result.force[free_row] = force[global_row];
        for (std::size_t free_column = 0;
             free_column < free_dimension;
             ++free_column) {
            const std::size_t global_column = result.global_indices[free_column];
            result.matrix[free_row * free_dimension + free_column] =
                dense_matrix[global_row * dimension + global_column];
        }
    }
    return result;
}

std::vector<double> reconstruct_displacement(
    std::size_t global_dimension,
    const FreeSystem& free_system,
    const std::vector<double>& free_displacement) {
    if (free_system.global_indices.size() != free_displacement.size()) {
        throw std::logic_error("free displacement has the wrong size");
    }
    std::vector<double> result(global_dimension, 0.0);
    for (std::size_t index = 0; index < free_displacement.size(); ++index) {
        result[free_system.global_indices[index]] = free_displacement[index];
    }
    return result;
}

double relative_residual(const FreeSystem& system,
                         const std::vector<double>& displacement) {
    const std::size_t dimension = displacement.size();
    std::vector<double> residual(dimension, 0.0);
    for (std::size_t row = 0; row < dimension; ++row) {
        double value = -system.force[row];
        for (std::size_t column = 0; column < dimension; ++column) {
            value += system.matrix[row * dimension + column] *
                     displacement[column];
        }
        residual[row] = value;
    }
    return vector_norm(residual) / std::max(vector_norm(system.force), 1.0e-30);
}

double relative_displacement_error(const std::vector<double>& candidate,
                                   const std::vector<double>& reference) {
    if (candidate.size() != reference.size()) {
        throw std::logic_error("displacement vectors have different sizes");
    }
    std::vector<double> difference(candidate.size(), 0.0);
    for (std::size_t index = 0; index < candidate.size(); ++index) {
        difference[index] = candidate[index] - reference[index];
    }
    return vector_norm(difference) / std::max(vector_norm(reference), 1.0e-30);
}

} // namespace

SerialAssemblyResult assemble_serial_reference(const AssemblyCase& assembly_case) {
    const ValidatedCase validated = validate_reference_input(assembly_case);
    const std::size_t dimension = static_cast<std::size_t>(validated.dimension);
    SerialAssemblyResult result;
    result.dimension = validated.dimension;
    result.dense_values.assign(
        checked_multiply(dimension, dimension, "reference dense matrix size"),
        0.0);

    // Ordered column sets are built only from topology and do not use the
    // candidate assembler, its AssemblyPlan, or its numeric scatter indices.
    std::vector<std::set<GlobalDofIndex>> column_rows(dimension);
    const ElementDofMap& topology = assembly_case.element_dof_map;
    const ElementMatrixBatch& matrices = assembly_case.element_matrices;
    for (std::size_t canonical = 0;
         canonical < validated.canonical_ordinals.size();
         ++canonical) {
        const std::size_t input_ordinal = validated.canonical_ordinals[canonical];
        const std::size_t dof_begin = static_cast<std::size_t>(
            topology.element_dof_offsets[input_ordinal]);
        const std::size_t local_dimension = validated.local_dimensions[canonical];
        const std::size_t matrix_begin = static_cast<std::size_t>(
            matrices.element_value_offsets[canonical]);
        for (std::size_t local_row = 0;
             local_row < local_dimension;
             ++local_row) {
            const GlobalDofIndex global_row =
                topology.global_dof_indices[dof_begin + local_row];
            for (std::size_t local_column = 0;
                 local_column < local_dimension;
                 ++local_column) {
                const GlobalDofIndex global_column =
                    topology.global_dof_indices[dof_begin + local_column];
                const double local_value = matrices.values_row_major[
                    matrix_begin + local_row * local_dimension + local_column];
                double& global_value = result.dense_values[
                    static_cast<std::size_t>(global_row) * dimension +
                    static_cast<std::size_t>(global_column)];
                global_value += local_value;
                if (!std::isfinite(global_value)) {
                    throw std::overflow_error(
                        "serial reference accumulation became nonfinite");
                }

                const GlobalDofIndex row = std::min(global_row, global_column);
                const GlobalDofIndex column = std::max(global_row, global_column);
                column_rows[static_cast<std::size_t>(column)].insert(row);
            }
        }
    }

    result.column_offsets.reserve(dimension + 1);
    result.column_offsets.push_back(0);
    for (const auto& rows : column_rows) {
        result.row_indices.insert(result.row_indices.end(), rows.begin(), rows.end());
        result.column_offsets.push_back(
            size_to_offset(result.row_indices.size(), "reference nonzero count"));
    }
    return result;
}

MatrixComparison compare_matrices(const Csc3Matrix& candidate,
                                  const SerialAssemblyResult& reference) {
    validate_reference_result(reference);
    const bool candidate_values_are_finite =
        validate_candidate_structure(candidate);

    MatrixComparison result;
    result.structure_matches =
        candidate.dimension == reference.dimension &&
        candidate.column_offsets == reference.column_offsets &&
        candidate.row_indices == reference.row_indices;

    double reference_maximum = 0.0;
    for (const double value : reference.dense_values) {
        reference_maximum = std::max(reference_maximum, std::abs(value));
    }
    result.reference_max_absolute_value = reference_maximum;
    result.max_absolute_tolerance =
        kMaximumAbsoluteBaseTolerance +
        kMaximumAbsoluteScaleTolerance * result.reference_max_absolute_value;

    if (!result.structure_matches || !candidate_values_are_finite) {
        result.relative_frobenius_error =
            std::numeric_limits<double>::infinity();
        result.max_absolute_error = std::numeric_limits<double>::infinity();
        return result;
    }

    const std::vector<double> candidate_dense = expand_candidate_dense(candidate);
    ScaledNorm difference_norm;
    ScaledNorm reference_norm;
    for (std::size_t index = 0; index < reference.dense_values.size(); ++index) {
        const double difference =
            candidate_dense[index] - reference.dense_values[index];
        difference_norm.add(difference);
        reference_norm.add(reference.dense_values[index]);
        result.max_absolute_error =
            std::max(result.max_absolute_error, std::abs(difference));
    }
    result.relative_frobenius_error =
        difference_norm.relative_to(reference_norm, 1.0e-30);
    result.passed = std::isfinite(result.relative_frobenius_error) &&
                    std::isfinite(result.max_absolute_error) &&
                    result.relative_frobenius_error <=
                        kRelativeFrobeniusTolerance &&
                    result.max_absolute_error <=
                        result.max_absolute_tolerance;
    return result;
}

ValidationResult validate_case(const AssemblyCase& assembly_case,
                               int thread_count) {
    if (thread_count <= 0) {
        throw std::invalid_argument("thread_count must be positive");
    }

    const SerialAssemblyResult reference =
        assemble_serial_reference(assembly_case);
    const std::size_t dimension = static_cast<std::size_t>(reference.dimension);
    if (assembly_case.force.size() != dimension) {
        throw std::invalid_argument("force size must equal the global dimension");
    }
    if (!std::all_of(assembly_case.force.begin(),
                     assembly_case.force.end(),
                     [](double value) { return std::isfinite(value); })) {
        throw std::invalid_argument("force must contain only finite values");
    }
    if (!std::is_sorted(assembly_case.constrained_dof_indices.begin(),
                        assembly_case.constrained_dof_indices.end()) ||
        std::adjacent_find(assembly_case.constrained_dof_indices.begin(),
                           assembly_case.constrained_dof_indices.end()) !=
            assembly_case.constrained_dof_indices.end()) {
        throw std::invalid_argument("constrained DOFs must be sorted and unique");
    }
    for (const GlobalDofIndex dof : assembly_case.constrained_dof_indices) {
        if (dof < 0 || dof >= reference.dimension) {
            throw std::invalid_argument("constrained DOF is out of range");
        }
    }

    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(assembly_case.element_dof_map, thread_count);
    assembler.assemble_numeric_atomic(assembly_case.element_matrices, thread_count);
    const Csc3Matrix& candidate = assembler.matrix();

    ValidationResult result;
    result.case_name = assembly_case.name;
    result.element_type = assembly_case.element_type;
    result.node_count = assembly_case.nodes.size();
    result.element_count = assembly_case.element_dof_map.element_ids.size();
    result.dof_count = static_cast<std::size_t>(candidate.dimension);
    result.thread_count = thread_count;
    result.matrix = compare_matrices(candidate, reference);
    if (!result.matrix.structure_matches) {
        return result;
    }

    const std::vector<double> candidate_dense = expand_candidate_dense(candidate);
    const FreeSystem candidate_free = extract_free_system(
        candidate_dense,
        reference.dimension,
        assembly_case.force,
        assembly_case.constrained_dof_indices);
    const FreeSystem reference_free = extract_free_system(
        reference.dense_values,
        reference.dimension,
        assembly_case.force,
        assembly_case.constrained_dof_indices);
    const std::vector<double> candidate_free_displacement =
        solve_dense_system(candidate_free.matrix, candidate_free.force);
    const std::vector<double> reference_free_displacement =
        solve_dense_system(reference_free.matrix, reference_free.force);
    const std::vector<double> candidate_displacement = reconstruct_displacement(
        dimension, candidate_free, candidate_free_displacement);
    const std::vector<double> reference_displacement = reconstruct_displacement(
        dimension, reference_free, reference_free_displacement);

    result.displacement.relative_displacement_error =
        relative_displacement_error(candidate_displacement,
                                    reference_displacement);
    result.displacement.parallel_relative_residual =
        relative_residual(candidate_free, candidate_free_displacement);
    result.displacement.serial_relative_residual =
        relative_residual(reference_free, reference_free_displacement);
    result.displacement.parallel_displacement_norm =
        vector_norm(candidate_displacement);
    result.displacement.serial_displacement_norm =
        vector_norm(reference_displacement);
    result.displacement.passed =
        std::isfinite(result.displacement.relative_displacement_error) &&
        std::isfinite(result.displacement.parallel_relative_residual) &&
        std::isfinite(result.displacement.serial_relative_residual) &&
        std::isfinite(result.displacement.parallel_displacement_norm) &&
        std::isfinite(result.displacement.serial_displacement_norm) &&
        result.displacement.relative_displacement_error <=
            kRelativeDisplacementTolerance &&
        result.displacement.parallel_relative_residual <=
            kRelativeResidualTolerance &&
        result.displacement.serial_relative_residual <=
            kRelativeResidualTolerance;
    result.passed = result.matrix.passed && result.displacement.passed;
    return result;
}

} // namespace csc3_demo::evidence
