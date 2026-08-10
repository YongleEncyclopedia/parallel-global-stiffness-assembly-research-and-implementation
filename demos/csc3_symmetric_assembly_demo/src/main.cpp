#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <cstdint>
#include <exception>
#include <iostream>
#include <unordered_map>
#include <vector>

int main() {
    try {
        using namespace csc3_demo;

        const DofCodingInfo dof_coding_info{
            {{20, {1, 2}}, {10, {0, 1}}},
            {{0, {0}}, {1, {1}}, {2, {2}}},
        };
        const std::unordered_map<ElementId, std::vector<double>> element_stiffness{
            {20, {2.0, -1.0, -1.0, 2.0}},
            {10, {3.0, -2.0, -2.0, 3.0}},
        };

        AssemblyHelper helper;
        Csc3Matrix csc3;
        HelpInfo help_info;
        helper.Symbolic(csc3, help_info, dof_coding_info);
        helper.zero_values(csc3);

        const int thread_count = std::max(1, std::min(4, max_openmp_threads()));
        const std::int64_t element_count = static_cast<std::int64_t>(help_info.element_ids.size());
#pragma omp parallel for schedule(static) num_threads(thread_count)
        for (std::int64_t element = 0; element < element_count; ++element) {
            const ElementId elem_id = help_info.element_ids[static_cast<std::size_t>(element)];
            const auto& values = element_stiffness.at(elem_id);
            helper.add(csc3, help_info, ElementStiffness{elem_id, values.data(), values.size()});
        }

        std::cout << "n=" << csc3.n << " values=";
        for (std::size_t i = 0; i < csc3.values.size(); ++i) {
            if (i != 0) {
                std::cout << ',';
            }
            std::cout << csc3.values[i];
        }
        std::cout << '\n';
        return 0;
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
}
