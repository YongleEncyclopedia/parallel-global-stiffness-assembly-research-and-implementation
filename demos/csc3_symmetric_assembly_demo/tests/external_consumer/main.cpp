#include "csc3_demo/assembly_helper.h"

// 该程序由 tests/external_consumer 下的独立 CMake 工程编译，用来确认接收方只靠
// 公共头文件和 csc3_demo::csc3_demo target 就能完成接入。

#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    try {
        using namespace csc3_demo;
        // 一个二自由度单元对应二阶对称矩阵，上三角 CSC3 数值应为
        // [2, -1, 2]。
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
