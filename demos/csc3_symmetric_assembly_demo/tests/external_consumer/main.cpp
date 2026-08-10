#include "csc3_demo/assembly_helper.h"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    try {
        using namespace csc3_demo;
        const DofCodingInfo dof_coding_info{{{0, {0, 1}}}, {{0, {0}}, {1, {1}}}};
        const std::vector<double> element_stiffness{2.0, -1.0, -1.0, 2.0};

        AssemblyHelper helper;
        Csc3Matrix csc3;
        HelpInfo help_info;
        helper.Symbolic(csc3, help_info, dof_coding_info);
        helper.zero_values(csc3);
#pragma omp parallel for schedule(static) num_threads(2)
        for (int element = 0; element < 1; ++element) {
            helper.add(csc3, help_info,
                       ElementStiffness{help_info.element_ids[static_cast<std::size_t>(element)],
                                        element_stiffness.data(), element_stiffness.size()});
        }

        if (!openmp_enabled() || csc3.values != std::vector<double>{2.0, -1.0, 2.0}) {
            throw std::runtime_error("external consumer integration failed");
        }
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
