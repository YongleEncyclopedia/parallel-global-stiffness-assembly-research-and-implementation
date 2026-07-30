#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo;

static_assert(std::is_same_v<GlobalDofIndex, std::int32_t>);
static_assert(std::is_same_v<ElementId, std::int32_t>);
static_assert(std::is_same_v<Offset, std::uint64_t>);
static_assert(noexcept(std::declval<const SymmetricCscAssembler&>().matrix()));
static_assert(noexcept(std::declval<const SymmetricCscAssembler&>().assembly_plan()));
static_assert(noexcept(std::declval<const SymmetricCscAssembler&>().symbolic_thread_count_used()));
static_assert(noexcept(std::declval<const SymmetricCscAssembler&>().numeric_thread_count_used()));
static_assert(noexcept(openmp_enabled()));
static_assert(noexcept(max_openmp_threads()));

struct ElementSpec {
    ElementId id = 0;
    std::vector<GlobalDofIndex> dofs;
};

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

void require_close(const std::vector<double>& actual, const std::vector<double>& expected,
                   const std::string& label, double absolute_tolerance = 1.0e-11,
                   double relative_tolerance = 1.0e-11) {
    require_equal(actual.size(), expected.size(), label + " size");
    for (std::size_t i = 0; i < actual.size(); ++i) {
        const double difference = std::abs(actual[i] - expected[i]);
        const double scale = std::max(std::abs(actual[i]), std::abs(expected[i]));
        if (!std::isfinite(actual[i]) ||
            difference > absolute_tolerance + relative_tolerance * scale) {
            throw std::runtime_error(label + " differs at index " + std::to_string(i));
        }
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

ElementDofMap make_element_dof_map(const std::vector<ElementSpec>& elements) {
    ElementDofMap result;
    result.element_dof_offsets.push_back(0);
    for (const auto& element : elements) {
        result.element_ids.push_back(element.id);
        result.global_dof_indices.insert(result.global_dof_indices.end(), element.dofs.begin(),
                                         element.dofs.end());
        result.element_dof_offsets.push_back(static_cast<Offset>(result.global_dof_indices.size()));
    }
    return result;
}

ElementDofMap chain_topology_unordered() {
    return make_element_dof_map({
        {20, {1, 2}},
        {10, {0, 1}},
    });
}

ElementDofMap chain_topology_ordered() {
    return make_element_dof_map({
        {10, {0, 1}},
        {20, {1, 2}},
    });
}

ElementMatrixBatch chain_matrices_canonical() {
    return ElementMatrixBatch{
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
}

Offset csc_position(const Csc3Matrix& matrix, GlobalDofIndex row, GlobalDofIndex column) {
    if (row > column) {
        std::swap(row, column);
    }
    const Offset begin = matrix.column_offsets[static_cast<std::size_t>(column)];
    const Offset end = matrix.column_offsets[static_cast<std::size_t>(column) + 1];
    const auto first = matrix.row_indices.begin() + static_cast<std::ptrdiff_t>(begin);
    const auto last = matrix.row_indices.begin() + static_cast<std::ptrdiff_t>(end);
    const auto found = std::lower_bound(first, last, row);
    if (found == last || *found != row) {
        throw std::runtime_error("expected CSC3 entry is missing");
    }
    return static_cast<Offset>(std::distance(matrix.row_indices.begin(), found));
}

std::vector<double> expand_csc3_to_dense(const Csc3Matrix& matrix) {
    const std::size_t dimension = static_cast<std::size_t>(matrix.dimension);
    std::vector<double> dense(dimension * dimension, 0.0);
    for (GlobalDofIndex column = 0; column < matrix.dimension; ++column) {
        const Offset begin = matrix.column_offsets[static_cast<std::size_t>(column)];
        const Offset end = matrix.column_offsets[static_cast<std::size_t>(column) + 1];
        for (Offset position = begin; position < end; ++position) {
            const auto row = matrix.row_indices[static_cast<std::size_t>(position)];
            const auto value = matrix.values[static_cast<std::size_t>(position)];
            dense[static_cast<std::size_t>(row) * dimension + static_cast<std::size_t>(column)] =
                value;
            dense[static_cast<std::size_t>(column) * dimension + static_cast<std::size_t>(row)] =
                value;
        }
    }
    return dense;
}

std::vector<double> assemble_dense_oracle(const AssemblyPlan& plan,
                                          const ElementMatrixBatch& batch) {
    GlobalDofIndex dimension = 0;
    for (const auto dof : plan.global_dof_indices) {
        dimension = std::max(dimension, static_cast<GlobalDofIndex>(dof + 1));
    }
    const std::size_t dense_dimension = static_cast<std::size_t>(dimension);
    std::vector<double> dense(dense_dimension * dense_dimension, 0.0);

    for (std::size_t element = 0; element < plan.element_ids.size(); ++element) {
        const Offset dof_begin = plan.element_dof_offsets[element];
        const Offset dof_end = plan.element_dof_offsets[element + 1];
        const std::size_t local_dimension = static_cast<std::size_t>(dof_end - dof_begin);
        const Offset value_begin = batch.element_value_offsets[element];
        for (std::size_t local_row = 0; local_row < local_dimension; ++local_row) {
            for (std::size_t local_column = local_row; local_column < local_dimension;
                 ++local_column) {
                const auto global_row =
                    plan.global_dof_indices[static_cast<std::size_t>(dof_begin) + local_row];
                const auto global_column =
                    plan.global_dof_indices[static_cast<std::size_t>(dof_begin) + local_column];
                const double value =
                    batch.values_row_major[static_cast<std::size_t>(value_begin) +
                                           local_row * local_dimension + local_column];
                dense[static_cast<std::size_t>(global_row) * dense_dimension +
                      static_cast<std::size_t>(global_column)] += value;
                if (global_row != global_column) {
                    dense[static_cast<std::size_t>(global_column) * dense_dimension +
                          static_cast<std::size_t>(global_row)] += value;
                }
            }
        }
    }
    return dense;
}

void require_same_symbolic_result(const SymmetricCscAssembler& actual,
                                  const SymmetricCscAssembler& expected, const std::string& label) {
    const auto& actual_matrix = actual.matrix();
    const auto& expected_matrix = expected.matrix();
    require_equal(actual_matrix.dimension, expected_matrix.dimension, label + " dimension");
    require_equal(actual_matrix.column_offsets, expected_matrix.column_offsets,
                  label + " column_offsets");
    require_equal(actual_matrix.row_indices, expected_matrix.row_indices, label + " row_indices");

    const auto& actual_plan = actual.assembly_plan();
    const auto& expected_plan = expected.assembly_plan();
    require_equal(actual_plan.element_ids, expected_plan.element_ids, label + " element_ids");
    require_equal(actual_plan.element_dof_offsets, expected_plan.element_dof_offsets,
                  label + " element_dof_offsets");
    require_equal(actual_plan.global_dof_indices, expected_plan.global_dof_indices,
                  label + " global_dof_indices");
    require_equal(actual_plan.element_scatter_offsets, expected_plan.element_scatter_offsets,
                  label + " element_scatter_offsets");
    require_equal(actual_plan.scatter_indices, expected_plan.scatter_indices,
                  label + " scatter_indices");
}

void test_two_element_chain_exact_structure_and_values() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 4);

    const auto& matrix = assembler.matrix();
    require_equal(matrix.dimension, GlobalDofIndex{3}, "chain dimension");
    require_equal(matrix.column_offsets, std::vector<Offset>{0, 1, 3, 5}, "chain column_offsets");
    require_equal(matrix.row_indices, std::vector<GlobalDofIndex>{0, 0, 1, 1, 2},
                  "chain row_indices");

    const auto& plan = assembler.assembly_plan();
    require_equal(plan.element_ids, std::vector<ElementId>{10, 20}, "chain element_ids");
    require_equal(plan.element_dof_offsets, std::vector<Offset>{0, 2, 4},
                  "chain element_dof_offsets");
    require_equal(plan.global_dof_indices, std::vector<GlobalDofIndex>{0, 1, 1, 2},
                  "chain global_dof_indices");
    require_equal(plan.element_scatter_offsets, std::vector<Offset>{0, 3, 6},
                  "chain element_scatter_offsets");
    require_equal(plan.scatter_indices, std::vector<Offset>{0, 1, 2, 2, 3, 4},
                  "chain scatter_indices");

    assembler.assemble_numeric_atomic(chain_matrices_canonical(), 4);
    require_close(matrix.values, std::vector<double>{2.0, -1.0, 5.0, -2.0, 3.0}, "chain values");
}

void test_canonical_sorting_of_unordered_element_ids() {
    const auto topology = make_element_dof_map({
        {42, {2, 3}},
        {7, {3, 0}},
        {20, {1, 2}},
    });
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(topology, 2);

    const auto& plan = assembler.assembly_plan();
    require_equal(plan.element_ids, std::vector<ElementId>{7, 20, 42}, "sorted IDs");
    require_equal(plan.element_dof_offsets, std::vector<Offset>{0, 2, 4, 6}, "sorted DOF offsets");
    require_equal(plan.global_dof_indices, std::vector<GlobalDofIndex>{3, 0, 1, 2, 2, 3},
                  "sorted element DOFs");
}

void test_ordered_topology_matches_canonicalized_topology() {
    SymmetricCscAssembler ordered;
    ordered.build_symbolic_parallel(chain_topology_ordered(), 2);

    SymmetricCscAssembler unordered;
    unordered.build_symbolic_parallel(chain_topology_unordered(), 2);

    require_same_symbolic_result(ordered, unordered, "ordered topology fast path");
    ordered.assemble_numeric_atomic(chain_matrices_canonical(), 2);
    unordered.assemble_numeric_atomic(chain_matrices_canonical(), 2);
    require_equal(ordered.matrix().values, unordered.matrix().values,
                  "ordered topology numeric values");
}

void test_symbolic_is_bitwise_deterministic_across_thread_counts() {
    const auto topology = make_element_dof_map({
        {40, {7, 1, 4}},
        {10, {0, 3}},
        {30, {2, 3, 5}},
        {20, {6, 0, 5}},
        {50, {7, 2}},
        {60, {1, 6, 4}},
    });

    SymmetricCscAssembler baseline;
    baseline.build_symbolic_parallel(topology, 1);
    for (const int threads : {2, 4, 8}) {
        SymmetricCscAssembler candidate;
        candidate.build_symbolic_parallel(topology, threads);
        require_same_symbolic_result(candidate, baseline,
                                     "symbolic threads=" + std::to_string(threads));
    }
}

ElementDofMap high_contention_topology(std::size_t element_count) {
    std::vector<ElementSpec> elements;
    elements.reserve(element_count);
    for (std::size_t element = 0; element < element_count; ++element) {
        elements.push_back(ElementSpec{static_cast<ElementId>(element), {0, 1}});
    }
    return make_element_dof_map(elements);
}

ElementMatrixBatch high_contention_matrices(std::size_t element_count) {
    ElementMatrixBatch batch;
    batch.element_value_offsets.reserve(element_count + 1);
    batch.values_row_major.reserve(element_count * 4);
    batch.element_value_offsets.push_back(0);
    for (std::size_t element = 0; element < element_count; ++element) {
        batch.values_row_major.insert(batch.values_row_major.end(), {1.0, 0.25, 0.25, 2.0});
        batch.element_value_offsets.push_back(static_cast<Offset>(batch.values_row_major.size()));
    }
    return batch;
}

void test_parallel_entry_points_record_real_team_sizes() {
    require_true(openmp_enabled(), "OpenMP must be enabled");
    require_true(max_openmp_threads() > 1, "test environment must expose multiple OpenMP threads");
    const int requested_threads = std::min(4, max_openmp_threads());

    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(high_contention_topology(256), requested_threads);
    require_true(assembler.symbolic_thread_count_used() > 1,
                 "parallel symbolic construction did not observe multiple threads");
    assembler.assemble_numeric_atomic(high_contention_matrices(256), requested_threads);
    require_true(assembler.numeric_thread_count_used() > 1,
                 "parallel numeric assembly did not observe multiple threads");
}

void test_high_contention_atomic_assembly() {
    constexpr std::size_t kElementCount = 2048;
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(high_contention_topology(kElementCount), 8);
    assembler.assemble_numeric_atomic(high_contention_matrices(kElementCount), 8);

    require_close(assembler.matrix().values, std::vector<double>{2048.0, 512.0, 4096.0},
                  "high-contention values");
}

struct RandomCase {
    ElementDofMap topology;
    ElementMatrixBatch matrices;
};

RandomCase make_random_case(std::mt19937& random, int trial) {
    const GlobalDofIndex dimension = static_cast<GlobalDofIndex>(5 + trial % 5);
    std::vector<ElementSpec> canonical_elements;
    const int element_count = static_cast<int>(dimension) + 3;
    canonical_elements.reserve(static_cast<std::size_t>(element_count));

    for (int element = 0; element < element_count; ++element) {
        std::vector<GlobalDofIndex> dofs(static_cast<std::size_t>(dimension));
        for (GlobalDofIndex dof = 0; dof < dimension; ++dof) {
            dofs[static_cast<std::size_t>(dof)] = dof;
        }
        if (element < dimension) {
            dofs = {
                static_cast<GlobalDofIndex>(element),
                static_cast<GlobalDofIndex>((element + 1) % dimension),
            };
        } else {
            std::shuffle(dofs.begin(), dofs.end(), random);
            const std::size_t local_dimension =
                2 + static_cast<std::size_t>(random() % static_cast<unsigned>(dimension - 1));
            dofs.resize(local_dimension);
        }
        canonical_elements.push_back(ElementSpec{
            static_cast<ElementId>(1000 + trial * 100 + element * 3),
            std::move(dofs),
        });
    }

    ElementMatrixBatch matrices;
    matrices.element_value_offsets.push_back(0);
    for (std::size_t element = 0; element < canonical_elements.size(); ++element) {
        const std::size_t local_dimension = canonical_elements[element].dofs.size();
        const std::size_t value_begin = matrices.values_row_major.size();
        matrices.values_row_major.resize(value_begin + local_dimension * local_dimension);
        for (std::size_t row = 0; row < local_dimension; ++row) {
            for (std::size_t column = row; column < local_dimension; ++column) {
                const double value =
                    row == column
                        ? static_cast<double>(20 + trial + static_cast<int>(element + row))
                        : static_cast<double>(1 + trial +
                                              static_cast<int>(element + row + column)) /
                              8.0;
                matrices.values_row_major[value_begin + row * local_dimension + column] = value;
                matrices.values_row_major[value_begin + column * local_dimension + row] = value;
            }
        }
        matrices.element_value_offsets.push_back(
            static_cast<Offset>(matrices.values_row_major.size()));
    }

    std::vector<ElementSpec> input_elements = canonical_elements;
    std::shuffle(input_elements.begin(), input_elements.end(), random);
    return RandomCase{make_element_dof_map(input_elements), std::move(matrices)};
}

void test_fixed_seed_random_topologies_against_dense_oracle() {
    std::mt19937 random(0x43C5C3U);
    for (int trial = 0; trial < 30; ++trial) {
        const auto input = make_random_case(random, trial);
        SymmetricCscAssembler assembler;
        const int threads = std::vector<int>{1, 2, 4, 8}[static_cast<std::size_t>(trial % 4)];
        assembler.build_symbolic_parallel(input.topology, threads);
        assembler.assemble_numeric_atomic(input.matrices, threads);
        require_close(expand_csc3_to_dense(assembler.matrix()),
                      assemble_dense_oracle(assembler.assembly_plan(), input.matrices),
                      "random dense oracle trial " + std::to_string(trial));
    }
}

void test_repeated_numeric_calls_overwrite_values() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 4);
    const auto batch = chain_matrices_canonical();
    assembler.assemble_numeric_atomic(batch, 4);
    const auto once = assembler.matrix().values;
    assembler.assemble_numeric_atomic(batch, 4);
    require_equal(assembler.matrix().values, once, "one-shot overwrite values");
}

void test_symbolic_input_validation() {
    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{}, 1);
        },
        "empty topology");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{{1, 2}, {0, 2}, {0, 1}}, 1);
        },
        "offset count");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{{1}, {1, 2}, {0, 1}}, 1);
        },
        "first offset");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{{1, 2}, {0, 2, 1}, {0}}, 1);
        },
        "nonmonotone offsets");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{{1}, {0, 1}, {0, 1}}, 1);
        },
        "final offset");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(ElementDofMap{{1}, {0, 0}, {}}, 1);
        },
        "empty element DOFs");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(make_element_dof_map({{1, {0}}, {1, {1}}}), 1);
        },
        "duplicate element IDs");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(make_element_dof_map({{1, {0, 0}}}), 1);
        },
        "duplicate local DOFs");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(make_element_dof_map({{1, {-1, 0}}}), 1);
        },
        "negative global DOF");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(make_element_dof_map({{1, {0, 2}}}), 1);
        },
        "noncompact global DOFs");

    require_throws<std::invalid_argument>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.build_symbolic_parallel(make_element_dof_map({{-1, {0}}}), 1);
        },
        "negative element ID");
}

void test_numeric_state_and_batch_validation() {
    require_throws<std::logic_error>(
        [] {
            SymmetricCscAssembler assembler;
            assembler.assemble_numeric_atomic(chain_matrices_canonical(), 1);
        },
        "numeric before symbolic");

    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 2);

    require_throws<std::invalid_argument>(
        [&] { assembler.assemble_numeric_atomic(ElementMatrixBatch{}, 2); },
        "missing matrix offsets");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.element_value_offsets = {0, 8};
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "matrix offset count");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.element_value_offsets = {1, 4, 8};
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "first matrix offset");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.element_value_offsets = {0, 5, 4};
            batch.values_row_major.resize(4);
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "nonmonotone matrix offsets");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.element_value_offsets = {0, 4, 7};
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "final matrix offset");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.element_value_offsets = {0, 3, 7};
            batch.values_row_major.resize(7, 1.0);
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "matrix segment size");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.values_row_major[1] = std::numeric_limits<double>::quiet_NaN();
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "NaN matrix value");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.values_row_major[1] = std::numeric_limits<double>::infinity();
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "infinite matrix value");

    require_throws<std::invalid_argument>(
        [&] {
            auto batch = chain_matrices_canonical();
            batch.values_row_major[1] = 1.0;
            batch.values_row_major[2] = 1.01;
            assembler.assemble_numeric_atomic(batch, 2);
        },
        "materially nonsymmetric matrix");
}

void test_combined_absolute_relative_symmetry_tolerance() {
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(make_element_dof_map({{1, {0, 1}}}), 2);
    assembler.assemble_numeric_atomic(ElementMatrixBatch{{0, 4}, {2.0, 1.0e12 + 50.0, 1.0e12, 3.0}},
                                      2);
    require_close(assembler.matrix().values, std::vector<double>{2.0, 1.0e12 + 50.0, 3.0},
                  "relative symmetry tolerance");

    assembler.assemble_numeric_atomic(ElementMatrixBatch{{0, 4}, {2.0, 1.0e-13, 0.0, 3.0}}, 2);
    require_close(assembler.matrix().values, std::vector<double>{2.0, 1.0e-13, 3.0},
                  "absolute symmetry tolerance");
}

void test_nonpositive_thread_counts_are_rejected() {
    for (const int threads : {0, -1}) {
        require_throws<std::invalid_argument>(
            [threads] {
                SymmetricCscAssembler assembler;
                assembler.build_symbolic_parallel(chain_topology_unordered(), threads);
            },
            "nonpositive symbolic thread count");
    }

    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(chain_topology_unordered(), 1);
    for (const int threads : {0, -2}) {
        require_throws<std::invalid_argument>(
            [&assembler, threads] {
                assembler.assemble_numeric_atomic(chain_matrices_canonical(), threads);
            },
            "nonpositive numeric thread count");
    }
}

void test_scatter_indices_point_to_expected_entries() {
    const auto topology = make_element_dof_map({
        {9, {3, 1, 2}},
        {4, {2, 0}},
        {7, {1, 3}},
    });
    SymmetricCscAssembler assembler;
    assembler.build_symbolic_parallel(topology, 4);

    const auto& matrix = assembler.matrix();
    const auto& plan = assembler.assembly_plan();
    require_equal(plan.scatter_indices.size(),
                  static_cast<std::size_t>(plan.element_scatter_offsets.back()), "scatter size");
    for (const Offset position : plan.scatter_indices) {
        require_true(position < static_cast<Offset>(matrix.values.size()),
                     "scatter index is out of range");
    }

    for (std::size_t element = 0; element < plan.element_ids.size(); ++element) {
        const Offset begin = plan.element_dof_offsets[element];
        const Offset end = plan.element_dof_offsets[element + 1];
        Offset scatter_position = plan.element_scatter_offsets[element];
        for (Offset local_row = begin; local_row < end; ++local_row) {
            for (Offset local_column = local_row; local_column < end; ++local_column) {
                const auto global_row =
                    plan.global_dof_indices[static_cast<std::size_t>(local_row)];
                const auto global_column =
                    plan.global_dof_indices[static_cast<std::size_t>(local_column)];
                require_equal(plan.scatter_indices[static_cast<std::size_t>(scatter_position++)],
                              csc_position(matrix, global_row, global_column), "scatter target");
            }
        }
        require_equal(scatter_position, plan.element_scatter_offsets[element + 1],
                      "scatter segment length");
    }
}

} // namespace

int main() {
    try {
        test_two_element_chain_exact_structure_and_values();
        test_canonical_sorting_of_unordered_element_ids();
        test_ordered_topology_matches_canonicalized_topology();
        test_symbolic_is_bitwise_deterministic_across_thread_counts();
        test_parallel_entry_points_record_real_team_sizes();
        test_high_contention_atomic_assembly();
        test_fixed_seed_random_topologies_against_dense_oracle();
        test_repeated_numeric_calls_overwrite_values();
        test_symbolic_input_validation();
        test_numeric_state_and_batch_validation();
        test_combined_absolute_relative_symmetry_tolerance();
        test_nonpositive_thread_counts_are_rejected();
        test_scatter_indices_point_to_expected_entries();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
