#include "csc3_demo/assembly_helper.h"

#include <cmath>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef _OPENMP
#error "The contention test requires OpenMP"
#endif

#include <omp.h>

namespace {

using namespace csc3_demo;

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_close(double actual, double expected, const std::string& label) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1.0e-10) {
        throw std::runtime_error(label + " mismatch");
    }
}

} // namespace

int main() {
    try {
        constexpr int kElementCount = 8192;
        constexpr int kThreadCount = 2;
        DofCodingInfo input;
        input.node_dofs = {{0, {0}}, {1, {1}}};
        for (int element = 0; element < kElementCount; ++element) {
            input.elems.emplace(element, std::vector<NodeId>{0, 1});
        }

        require_true(openmp_enabled() && max_openmp_threads() >= kThreadCount,
                     "two OpenMP threads are required");
        omp_set_dynamic(0);
        omp_set_num_threads(kThreadCount);
        AssemblyHelper helper;
        Csc3Matrix csc3;
        HelpInfo help_info;
        helper.Symbolic(csc3, help_info, input);
        require_true(helper.symbolic_thread_count_used() == kThreadCount,
                     "symbolic assembly used the wrong team size");

        helper.zero_values(csc3);
        const std::vector<double> stiffness{1.0, 0.25, 0.25, 2.0};
        int observed_threads = 0;
#pragma omp parallel num_threads(kThreadCount)
        {
#pragma omp single
            {
                observed_threads = omp_get_num_threads();
            }
#pragma omp for schedule(static)
            for (int element = 0; element < kElementCount; ++element) {
                helper.add(csc3, help_info,
                           ElementStiffness{element, stiffness.data(), stiffness.size()});
            }
        }
        require_true(observed_threads == kThreadCount, "numeric assembly used the wrong team size");
        require_true(csc3.values.size() == 3, "unexpected CSC3 value count");
        require_close(csc3.values[0], static_cast<double>(kElementCount), "diagonal (0,0)");
        require_close(csc3.values[1], 0.25 * static_cast<double>(kElementCount), "entry (0,1)");
        require_close(csc3.values[2], 2.0 * static_cast<double>(kElementCount), "diagonal (1,1)");
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
