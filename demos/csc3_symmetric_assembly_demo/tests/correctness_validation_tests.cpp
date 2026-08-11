#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo;
using namespace csc3_demo::evidence;

constexpr double kTotalLoadMagnitude = 1000.0;

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
void require_equal(const T& actual, const T& expected, const std::string& label) {
    if (actual != expected) {
        throw std::runtime_error(label + " mismatch");
    }
}

void require_close(double actual, double expected, double tolerance, const std::string& label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(label + " mismatch");
    }
}

template <typename Exception, typename Fn> void require_throws(Fn&& fn, const std::string& label) {
    try {
        std::forward<Fn>(fn)();
    } catch (const Exception&) {
        return;
    } catch (const std::exception& exception) {
        throw std::runtime_error(label + " threw the wrong exception: " + exception.what());
    } catch (...) {
        throw std::runtime_error(label + " threw a non-standard exception");
    }
    throw std::runtime_error(label + " did not throw");
}

AssemblyCase make_chain_case() {
    AssemblyCase result;
    result.name = "two_element_chain";
    result.element_type = ElementType::Tet4;
    result.element_dof_map = FlatDofTopology{
        {20, 10},
        {0, 2, 4},
        {1, 2, 0, 1},
    };
    result.element_matrices = ElementMatrixBatch{
        {0, 4, 8},
        {
            2.0,
            -1.0,
            -1.0,
            2.0,
            3.0,
            -2.0,
            -2.0,
            3.0,
        },
    };
    result.force = {0.0, 0.0, 0.0};
    return result;
}

Csc3Matrix assemble_candidate(const AssemblyCase& assembly_case) {
    const DofCodingInfo input{
        {{20, {1, 2}}, {10, {0, 1}}},
        {{0, {0}}, {1, {1}}, {2, {2}}},
    };
    AssemblyHelper helper;
    Csc3Matrix csc3;
    HelpInfo help_info;
    helper.Symbolic(csc3, help_info, input);
    helper.zero_values(csc3);
#pragma omp parallel for schedule(static) num_threads(2)
    for (int element = 0; element < 2; ++element) {
        const std::size_t ordinal = static_cast<std::size_t>(element);
        const std::size_t begin =
            static_cast<std::size_t>(assembly_case.element_matrices.element_value_offsets[ordinal]);
        const std::size_t end = static_cast<std::size_t>(
            assembly_case.element_matrices.element_value_offsets[ordinal + 1]);
        helper.add(csc3, help_info,
                   ElementStiffness{help_info.element_ids[ordinal],
                                    assembly_case.element_matrices.values_row_major.data() + begin,
                                    end - begin});
    }
    return csc3;
}

std::vector<GlobalDofIndex> node_dofs(const std::vector<int>& node_indices) {
    std::vector<GlobalDofIndex> result;
    result.reserve(node_indices.size() * 3);
    for (const int node : node_indices) {
        for (int component = 0; component < 3; ++component) {
            result.push_back(static_cast<GlobalDofIndex>(3 * node + component));
        }
    }
    return result;
}

void require_generated_layout(const AssemblyCase& assembly_case, std::size_t expected_element_count,
                              std::size_t expected_local_dimension) {
    require_equal(assembly_case.nodes.size(), std::size_t{8}, "generated node count");
    require_equal(assembly_case.element_dof_map.element_ids.size(), expected_element_count,
                  "generated element count");
    require_equal(assembly_case.force.size(), std::size_t{24}, "generated force size");
    require_equal(assembly_case.constrained_dof_indices,
                  std::vector<GlobalDofIndex>{
                      0,
                      1,
                      2,
                      6,
                      7,
                      8,
                      12,
                      13,
                      14,
                      18,
                      19,
                      20,
                  },
                  "generated constraints");

    require_true(std::is_sorted(assembly_case.constrained_dof_indices.begin(),
                                assembly_case.constrained_dof_indices.end()),
                 "generated constraints are not sorted");
    require_true(std::adjacent_find(assembly_case.constrained_dof_indices.begin(),
                                    assembly_case.constrained_dof_indices.end()) ==
                     assembly_case.constrained_dof_indices.end(),
                 "generated constraints are not unique");

    double total_z_load = 0.0;
    for (std::size_t dof = 2; dof < assembly_case.force.size(); dof += 3) {
        total_z_load += assembly_case.force[dof];
    }
    require_close(total_z_load, -kTotalLoadMagnitude, 1.0e-12, "generated total z load");
    for (std::size_t dof = 0; dof < assembly_case.force.size(); ++dof) {
        if (dof % 3 != 2) {
            require_close(assembly_case.force[dof], 0.0, 0.0, "generated lateral load");
        }
    }

    const auto& dof_offsets = assembly_case.element_dof_map.element_dof_offsets;
    const auto& matrix_offsets = assembly_case.element_matrices.element_value_offsets;
    require_equal(dof_offsets.size(), expected_element_count + 1, "generated DOF offsets");
    require_equal(matrix_offsets.size(), expected_element_count + 1, "generated matrix offsets");
    for (std::size_t element = 0; element < expected_element_count; ++element) {
        require_equal(dof_offsets[element + 1] - dof_offsets[element],
                      static_cast<Offset>(expected_local_dimension), "generated local dimension");
        require_equal(matrix_offsets[element + 1] - matrix_offsets[element],
                      static_cast<Offset>(expected_local_dimension * expected_local_dimension),
                      "generated local matrix size");

        const std::size_t begin = static_cast<std::size_t>(matrix_offsets[element]);
        for (std::size_t row = 0; row < expected_local_dimension; ++row) {
            for (std::size_t column = 0; column < expected_local_dimension; ++column) {
                const double value =
                    assembly_case.element_matrices
                        .values_row_major[begin + row * expected_local_dimension + column];
                const double transpose =
                    assembly_case.element_matrices
                        .values_row_major[begin + column * expected_local_dimension + row];
                require_true(std::isfinite(value), "generated matrix contains nonfinite value");
                require_close(value, transpose, 1.0e-6, "generated local matrix symmetry");
            }
        }
    }
}

void require_validation_pass(const ValidationResult& result, const std::string& expected_name) {
    require_equal(result.case_name, expected_name, "validation case name");
    require_true(result.matrix.structure_matches, "candidate/reference structures do not match");
    require_true(result.matrix.passed, "matrix comparison did not pass");
    require_true(result.matrix.relative_frobenius_error <= 1.0e-8,
                 "matrix relative Frobenius error exceeds threshold");
    require_true(result.matrix.max_absolute_error <= result.matrix.max_absolute_tolerance,
                 "matrix maximum absolute error exceeds threshold");
    require_true(result.displacement.passed, "displacement comparison did not pass");
    require_true(result.displacement.relative_displacement_error <= 1.0e-8,
                 "relative displacement error exceeds threshold");
    require_true(result.displacement.parallel_relative_residual <= 1.0e-10,
                 "parallel relative residual exceeds threshold");
    require_true(result.displacement.serial_relative_residual <= 1.0e-10,
                 "serial relative residual exceeds threshold");
    require_true(std::isfinite(result.displacement.parallel_displacement_norm) &&
                     result.displacement.parallel_displacement_norm > 0.0,
                 "parallel displacement norm is not finite and nonzero");
    require_true(std::isfinite(result.displacement.serial_displacement_norm) &&
                     result.displacement.serial_displacement_norm > 0.0,
                 "serial displacement norm is not finite and nonzero");
    require_true(result.passed, "overall validation did not pass");
}

void test_serial_reference_has_exact_chain_structure_and_dense_values() {
    const SerialAssemblyResult reference = assemble_serial_reference(make_chain_case());
    require_equal(reference.dimension, GlobalDofIndex{3}, "serial chain dimension");
    require_equal(reference.column_offsets, std::vector<Offset>{0, 1, 3, 5},
                  "serial chain column offsets");
    require_equal(reference.row_indices, std::vector<GlobalDofIndex>{0, 0, 1, 1, 2},
                  "serial chain row indices");
    require_equal(reference.dense_values,
                  std::vector<double>{
                      2.0,
                      -1.0,
                      0.0,
                      -1.0,
                      5.0,
                      -2.0,
                      0.0,
                      -2.0,
                      3.0,
                  },
                  "serial chain dense values");
}

void test_exact_matrix_comparison_passes() {
    const AssemblyCase assembly_case = make_chain_case();
    const SerialAssemblyResult reference = assemble_serial_reference(assembly_case);
    const Csc3Matrix candidate = assemble_candidate(assembly_case);
    const MatrixComparison comparison = compare_matrices(candidate, reference);

    require_equal(candidate.n, reference.dimension, "chain structure dimension");
    require_true(candidate.col_ptr.size() == reference.column_offsets.size() &&
                     std::equal(candidate.col_ptr.begin(), candidate.col_ptr.end(),
                                reference.column_offsets.begin()),
                 "chain structure column offsets mismatch");
    require_equal(candidate.row_idx, reference.row_indices, "chain structure row indices");
    require_true(comparison.structure_matches, "exact comparison structure mismatch");
    require_close(comparison.relative_frobenius_error, 0.0, 0.0, "exact relative Frobenius error");
    require_close(comparison.max_absolute_error, 0.0, 0.0, "exact maximum absolute error");
    require_close(comparison.reference_max_absolute_value, 5.0, 0.0,
                  "independent reference maximum absolute value");
    require_close(comparison.max_absolute_tolerance, 1.0e-10 + 5.0e-8, 1.0e-20,
                  "scaled maximum absolute tolerance");
    require_true(comparison.passed, "exact matrix comparison did not pass");
}

void test_controlled_matrix_perturbation_fails_thresholds() {
    const AssemblyCase assembly_case = make_chain_case();
    const SerialAssemblyResult reference = assemble_serial_reference(assembly_case);
    Csc3Matrix candidate = assemble_candidate(assembly_case);
    candidate.values.front() += 1.0e-4;

    const MatrixComparison comparison = compare_matrices(candidate, reference);
    require_true(comparison.structure_matches, "value perturbation unexpectedly changed structure");
    require_true(comparison.max_absolute_error > comparison.max_absolute_tolerance,
                 "controlled perturbation did not cross maximum absolute threshold");
    require_true(!comparison.passed,
                 "controlled perturbation unexpectedly passed matrix comparison");
}

void test_structure_mismatch_returns_a_failed_comparison() {
    const AssemblyCase assembly_case = make_chain_case();
    const SerialAssemblyResult reference = assemble_serial_reference(assembly_case);
    Csc3Matrix candidate = assemble_candidate(assembly_case);
    candidate.n = 2;
    candidate.col_ptr = {0, 1, 3};
    candidate.row_idx.resize(3);
    candidate.values.resize(3);

    const MatrixComparison comparison = compare_matrices(candidate, reference);
    require_true(!comparison.structure_matches,
                 "dimension mismatch unexpectedly matched structure");
    require_equal(comparison.relative_frobenius_error, std::numeric_limits<double>::max(),
                  "structure mismatch relative error sentinel");
    require_equal(comparison.max_absolute_error, std::numeric_limits<double>::max(),
                  "structure mismatch absolute error sentinel");
    require_true(!comparison.passed, "structure mismatch unexpectedly passed matrix comparison");
}

void test_nonfinite_candidate_returns_a_finite_failed_comparison() {
    const AssemblyCase assembly_case = make_chain_case();
    const SerialAssemblyResult reference = assemble_serial_reference(assembly_case);
    Csc3Matrix candidate = assemble_candidate(assembly_case);
    candidate.values.front() = std::numeric_limits<double>::infinity();

    const MatrixComparison comparison = compare_matrices(candidate, reference);
    require_true(comparison.structure_matches,
                 "nonfinite value unexpectedly changed matrix structure");
    require_equal(comparison.relative_frobenius_error, std::numeric_limits<double>::max(),
                  "nonfinite candidate relative error sentinel");
    require_equal(comparison.max_absolute_error, std::numeric_limits<double>::max(),
                  "nonfinite candidate absolute error sentinel");
    require_true(!comparison.passed, "nonfinite candidate unexpectedly passed comparison");
}

void test_large_finite_matrix_comparison_uses_scaled_norms() {
    const double reference_value = 1.0e200;
    const SerialAssemblyResult reference{
        1,
        {0, 1},
        {0},
        {reference_value},
    };
    const Csc3Matrix candidate{
        1,
        {0, 1},
        {0},
        {reference_value * (1.0 + 1.0e-9)},
    };

    const MatrixComparison comparison = compare_matrices(candidate, reference);
    require_true(std::isfinite(comparison.relative_frobenius_error),
                 "large finite matrix produced a nonfinite relative error");
    require_true(comparison.relative_frobenius_error <= 1.0e-8,
                 "large finite matrix exceeded the relative threshold");
    require_true(comparison.max_absolute_error <= comparison.max_absolute_tolerance,
                 "large finite matrix exceeded the maximum absolute threshold");
    require_true(comparison.passed, "large finite matrix unexpectedly failed comparison");
}

void test_tiny_nonzero_displacement_norm_does_not_underflow() {
    AssemblyCase assembly_case;
    assembly_case.name = "tiny_nonzero_displacement";
    assembly_case.element_type = ElementType::Tet4;
    assembly_case.nodes = {{0.0, 0.0, 0.0}};
    assembly_case.element_dof_map = FlatDofTopology{{0}, {0, 1}, {0}};
    assembly_case.element_matrices = ElementMatrixBatch{{0, 1}, {1.0e200}};
    assembly_case.force = {1.0};

    const ValidationResult result = validate_case(assembly_case, 1);
    require_true(result.passed, "large-stiffness scalar case unexpectedly failed validation");
    require_true(std::isfinite(result.displacement.parallel_displacement_norm) &&
                     result.displacement.parallel_displacement_norm > 0.0,
                 "parallel displacement norm underflowed to zero");
    require_true(std::isfinite(result.displacement.serial_displacement_norm) &&
                     result.displacement.serial_displacement_norm > 0.0,
                 "serial displacement norm underflowed to zero");
}

void test_generated_tet4_case_uses_six_tetrahedra_and_physical_data() {
    const AssemblyCase assembly_case = make_cube_case(ElementType::Tet4, 1, 1, 1);
    require_equal(assembly_case.element_type, ElementType::Tet4, "Tet4 element type");
    require_generated_layout(assembly_case, 6, 12);
    require_equal(
        assembly_case.element_dof_map.global_dof_indices,
        node_dofs({0, 1, 3, 7, 0, 3, 2, 7, 0, 2, 6, 7, 0, 6, 4, 7, 0, 4, 5, 7, 0, 5, 1, 7}),
        "Tet4 six-tetrahedron split");
}

void test_generated_hex8_case_uses_standard_node_order_and_physical_data() {
    const AssemblyCase assembly_case = make_cube_case(ElementType::Hex8, 1, 1, 1);
    require_equal(assembly_case.element_type, ElementType::Hex8, "Hex8 element type");
    require_generated_layout(assembly_case, 1, 24);
    require_equal(assembly_case.element_dof_map.global_dof_indices,
                  node_dofs({0, 1, 3, 2, 4, 5, 7, 6}), "Hex8 node order");
}

void test_tet4_fixture_passes_matrix_and_displacement_validation() {
    const AssemblyCase assembly_case = make_cube_case(ElementType::Tet4, 1, 1, 1);
    const ValidationResult result = validate_case(assembly_case, 2);
    require_validation_pass(result, assembly_case.name);
    require_equal(result.element_type, ElementType::Tet4, "Tet4 validation element type");
    require_equal(result.node_count, std::size_t{8}, "Tet4 validation node count");
    require_equal(result.element_count, std::size_t{6}, "Tet4 validation element count");
    require_equal(result.dof_count, std::size_t{24}, "Tet4 validation DOF count");
    require_equal(result.thread_count, 2, "Tet4 validation thread count");
}

void test_hex8_fixture_passes_matrix_and_displacement_validation() {
    const AssemblyCase assembly_case = make_cube_case(ElementType::Hex8, 1, 1, 1);
    const ValidationResult result = validate_case(assembly_case, 2);
    require_validation_pass(result, assembly_case.name);
    require_equal(result.element_type, ElementType::Hex8, "Hex8 validation element type");
    require_equal(result.node_count, std::size_t{8}, "Hex8 validation node count");
    require_equal(result.element_count, std::size_t{1}, "Hex8 validation element count");
    require_equal(result.dof_count, std::size_t{24}, "Hex8 validation DOF count");
    require_equal(result.thread_count, 2, "Hex8 validation thread count");
}

void test_invalid_grid_dimensions_are_rejected() {
    for (const ElementType element_type : {ElementType::Tet4, ElementType::Hex8}) {
        require_throws<std::invalid_argument>(
            [element_type] { static_cast<void>(make_cube_case(element_type, 0, 1, 1)); },
            "zero nx");
        require_throws<std::invalid_argument>(
            [element_type] { static_cast<void>(make_cube_case(element_type, 1, -1, 1)); },
            "negative ny");
        require_throws<std::invalid_argument>(
            [element_type] { static_cast<void>(make_cube_case(element_type, 1, 1, 0)); },
            "zero nz");
    }
}

void test_invalid_material_values_are_rejected() {
    for (const double young_modulus : {
             0.0,
             -1.0,
             std::numeric_limits<double>::infinity(),
             std::numeric_limits<double>::quiet_NaN(),
         }) {
        require_throws<std::invalid_argument>(
            [young_modulus] {
                static_cast<void>(make_cube_case(ElementType::Tet4, 1, 1, 1, young_modulus, 0.3));
            },
            "invalid Young modulus");
    }

    for (const double poisson_ratio : {
             -1.0,
             0.5,
             std::numeric_limits<double>::infinity(),
             std::numeric_limits<double>::quiet_NaN(),
         }) {
        require_throws<std::invalid_argument>(
            [poisson_ratio] {
                static_cast<void>(
                    make_cube_case(ElementType::Hex8, 1, 1, 1, 2.1e11, poisson_ratio));
            },
            "invalid Poisson ratio");
    }
}

void test_malformed_serial_topology_is_rejected() {
    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_dof_map.element_dof_offsets.pop_back();
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "missing topology terminal offset");

    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_dof_map.global_dof_indices = {1, 1, 0, 2};
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "duplicate local DOF");

    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_dof_map.global_dof_indices = {2, 4, 0, 1};
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "noncompact global DOFs");
}

void test_malformed_serial_matrix_batch_is_rejected() {
    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_matrices.element_value_offsets.pop_back();
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "missing matrix terminal offset");

    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_matrices.element_value_offsets = {0, 3, 8};
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "wrong local matrix size");
}

void test_nonfinite_reference_input_is_rejected() {
    require_throws<std::invalid_argument>(
        [] {
            AssemblyCase malformed = make_chain_case();
            malformed.element_matrices.values_row_major.front() =
                std::numeric_limits<double>::quiet_NaN();
            static_cast<void>(assemble_serial_reference(malformed));
        },
        "nonfinite reference matrix");
}

void test_invalid_force_and_constraint_contracts_are_rejected() {
    const AssemblyCase valid = make_cube_case(ElementType::Tet4, 1, 1, 1);

    require_throws<std::invalid_argument>(
        [valid] {
            AssemblyCase malformed = valid;
            malformed.force.pop_back();
            static_cast<void>(validate_case(malformed, 1));
        },
        "force size mismatch");

    require_throws<std::invalid_argument>(
        [valid] {
            AssemblyCase malformed = valid;
            malformed.force.front() = std::numeric_limits<double>::infinity();
            static_cast<void>(validate_case(malformed, 1));
        },
        "nonfinite force");

    require_throws<std::invalid_argument>(
        [valid] {
            AssemblyCase malformed = valid;
            malformed.constrained_dof_indices.push_back(malformed.constrained_dof_indices.back());
            static_cast<void>(validate_case(malformed, 1));
        },
        "duplicate constraint");

    require_throws<std::invalid_argument>(
        [valid] {
            AssemblyCase malformed = valid;
            std::swap(malformed.constrained_dof_indices[0], malformed.constrained_dof_indices[1]);
            static_cast<void>(validate_case(malformed, 1));
        },
        "unsorted constraints");
}

void test_singular_free_system_is_rejected() {
    AssemblyCase singular;
    singular.name = "singular_free_system";
    singular.element_type = ElementType::Tet4;
    singular.nodes = {{0.0, 0.0, 0.0}};
    singular.element_dof_map = FlatDofTopology{{0}, {0, 3}, {0, 1, 2}};
    singular.element_matrices = ElementMatrixBatch{{0, 9}, std::vector<double>(9, 0.0)};
    singular.force = {1.0, 0.0, 0.0};
    singular.constrained_dof_indices = {1, 2};

    require_throws<std::runtime_error>(
        [&singular] { static_cast<void>(validate_case(singular, 1)); }, "singular free system");
}

void test_invalid_validation_thread_count_is_rejected() {
    const AssemblyCase assembly_case = make_cube_case(ElementType::Hex8, 1, 1, 1);
    for (const int thread_count : {0, -1}) {
        require_throws<std::invalid_argument>(
            [&assembly_case, thread_count] {
                static_cast<void>(validate_case(assembly_case, thread_count));
            },
            "invalid validation thread count");
    }
}

} // namespace

int main() {
    try {
        test_serial_reference_has_exact_chain_structure_and_dense_values();
        test_exact_matrix_comparison_passes();
        test_controlled_matrix_perturbation_fails_thresholds();
        test_structure_mismatch_returns_a_failed_comparison();
        test_nonfinite_candidate_returns_a_finite_failed_comparison();
        test_large_finite_matrix_comparison_uses_scaled_norms();
        test_tiny_nonzero_displacement_norm_does_not_underflow();
        test_generated_tet4_case_uses_six_tetrahedra_and_physical_data();
        test_generated_hex8_case_uses_standard_node_order_and_physical_data();
        test_tet4_fixture_passes_matrix_and_displacement_validation();
        test_hex8_fixture_passes_matrix_and_displacement_validation();
        test_invalid_grid_dimensions_are_rejected();
        test_invalid_material_values_are_rejected();
        test_malformed_serial_topology_is_rejected();
        test_malformed_serial_matrix_batch_is_rejected();
        test_nonfinite_reference_input_is_rejected();
        test_invalid_force_and_constraint_contracts_are_rejected();
        test_singular_free_system_is_rejected();
        test_invalid_validation_thread_count_is_rejected();
    } catch (const std::exception& exception) {
        std::cerr << "Csc3DemoCorrectness failed: " << exception.what() << '\n';
        return 1;
    }
    std::cout << "Csc3DemoCorrectness passed\n";
    return 0;
}
