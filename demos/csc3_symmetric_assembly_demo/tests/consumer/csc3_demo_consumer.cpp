#include "csc3_demo/assembly_helper.h"

// 按接收方的调用方式使用公共头文件，不接触库内部实现。测试构造两个首尾相接的
// 二自由度单元，并核对最终 CSC3 结构和数值。

#include <cstdint>
#include <unordered_map>
#include <vector>

int main() {
    using namespace csc3_demo;
    // 单元 10 使用自由度 0、1；单元 20 使用自由度 1、2。
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
    const std::int64_t element_count = static_cast<std::int64_t>(help_info.element_ids.size());
#pragma omp parallel for schedule(static) num_threads(2)
    for (std::int64_t element = 0; element < element_count; ++element) {
        const ElementId elem_id = help_info.element_ids[static_cast<std::size_t>(element)];
        const auto& values = element_stiffness.at(elem_id);
        helper.add(csc3, help_info, ElementStiffness{elem_id, values.data(), values.size()});
    }

    // 上三角 CSC3 的期望列偏移、行号和数值均在这里逐项核对。
    const bool correct = csc3.n == 3 && csc3.col_ptr == std::vector<Index>{0, 1, 3, 5} &&
                         csc3.row_idx == std::vector<Index>{0, 0, 1, 1, 2} &&
                         csc3.values == std::vector<double>{3.0, -2.0, 5.0, -1.0, 2.0};
    return correct ? 0 : 1;
}
