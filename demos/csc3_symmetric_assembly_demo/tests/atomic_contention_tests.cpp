#include "csc3_demo/assembly_helper.h"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace csc3_demo;

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

ElementDofMap make_high_contention_topology(std::size_t element_count) {
    ElementDofMap topology;
    topology.element_ids.reserve(element_count);
    topology.element_dof_offsets.reserve(element_count + 1);
    topology.global_dof_indices.reserve(element_count * 2);
    topology.element_dof_offsets.push_back(0);
    for (std::size_t element = 0; element < element_count; ++element) {
        topology.element_ids.push_back(static_cast<ElementId>(element));
        topology.global_dof_indices.insert(topology.global_dof_indices.end(), {0, 1});
        topology.element_dof_offsets.push_back(
            static_cast<Offset>(topology.global_dof_indices.size()));
    }
    return topology;
}

ElementMatrixBatch make_high_contention_matrices(std::size_t element_count) {
    ElementMatrixBatch matrices;
    matrices.element_value_offsets.reserve(element_count + 1);
    matrices.values_row_major.reserve(element_count * 4);
    matrices.element_value_offsets.push_back(0);
    for (std::size_t element = 0; element < element_count; ++element) {
        matrices.values_row_major.insert(matrices.values_row_major.end(), {1.0, 0.25, 0.25, 2.0});
        matrices.element_value_offsets.push_back(
            static_cast<Offset>(matrices.values_row_major.size()));
    }
    return matrices;
}

void require_close(double actual, double expected, const std::string& label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1.0e-10) {
        throw std::runtime_error(label + " mismatch");
    }
}

} // namespace

int main() {
    try {
        constexpr std::size_t kElementCount = 8192;
        constexpr int kThreadCount = 2;
        require_true(openmp_enabled(), "OpenMP is not enabled");
        require_true(max_openmp_threads() > 1,
                     "the test environment does not expose multiple OpenMP threads");

        SymmetricCscAssembler assembler;
        assembler.build_symbolic_parallel(make_high_contention_topology(kElementCount),
                                          kThreadCount);
        require_true(assembler.symbolic_thread_count_used() == kThreadCount,
                     "symbolic assembly did not observe the requested team");
        assembler.assemble_numeric_atomic(make_high_contention_matrices(kElementCount),
                                          kThreadCount);
        require_true(assembler.numeric_thread_count_used() == kThreadCount,
                     "numeric assembly did not observe the requested team");

        const auto& values = assembler.matrix().values;
        require_true(values.size() == 3, "unexpected CSC3 value count");
        require_close(values[0], static_cast<double>(kElementCount), "diagonal (0,0)");
        require_close(values[1], 0.25 * static_cast<double>(kElementCount), "entry (0,1)");
        require_close(values[2], 2.0 * static_cast<double>(kElementCount), "diagonal (1,1)");
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
