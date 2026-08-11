#include "csc3_demo/assembly_helper.h"

// 这是组装类的最小使用示例，不负责读取网格或计算单元刚度。程序先准备两个
// 二自由度单元，再按研发接口依次完成符号组装、清零和并行数值组装。

#include <algorithm>
#include <cstdint>
#include <exception>
#include <iostream>
#include <unordered_map>
#include <vector>

int main() {
    try {
        using namespace csc3_demo;

        // DofCodingInfo 包含两级映射：
        //   elems      ：单元编号 → 该单元包含的节点；
        //   node_dofs  ：节点编号 → 该节点拥有的全局自由度。
        // 本例用节点 0、1、2 组成一条两单元链。单元 10 连接节点 0、1，单元 20
        // 连接节点 1、2，因此两个单元会共同向自由度 1 对应的矩阵条目累加。
        const DofCodingInfo dof_coding_info{
            {{20, {1, 2}}, {10, {0, 1}}},
            {{0, {0}}, {1, {1}}, {2, {2}}},
        };

        // 每个局部刚度矩阵按行连续存放。本例中的矩阵都是二阶对称矩阵，数值只为
        // 演示组装关系，不代表某种具体材料或单元。
        const std::unordered_map<ElementId, std::vector<double>> element_stiffness{
            {20, {2.0, -1.0, -1.0, 2.0}},
            {10, {3.0, -2.0, -2.0, 3.0}},
        };

        // Symbolic() 只根据拓扑生成 CSC3 上三角结构和 HelpInfo 中的散射位置，
        // 此时矩阵还没有刚度值。zero_values() 是每轮数值组装前的统一清零入口。
        AssemblyHelper helper;
        Csc3Matrix csc3;
        HelpInfo help_info;
        helper.Symbolic(csc3, help_info, dof_coding_info);
        helper.zero_values(csc3);

        // 示例最多使用 4 个线程，但不会超过当前 OpenMP 运行时允许的线程数。
        // 外层循环由调用方并行化；每次 add() 负责一个单元，并通过 atomic 把该
        // 单元的上三角刚度条目累加到共享的 csc3.values。
        const int thread_count = std::max(1, std::min(4, max_openmp_threads()));
        const std::int64_t element_count = static_cast<std::int64_t>(help_info.element_ids.size());
#pragma omp parallel for schedule(static) num_threads(thread_count)
        for (std::int64_t element = 0; element < element_count; ++element) {
            const ElementId elem_id = help_info.element_ids[static_cast<std::size_t>(element)];
            const auto& values = element_stiffness.at(elem_id);
            helper.add(csc3, help_info, ElementStiffness{elem_id, values.data(), values.size()});
        }

        // 组装后的三阶矩阵上三角依次为 3、-2、5、-1、2，因此本例应输出：
        // n=3 values=3,-2,5,-1,2
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
        // 输入、内存或结构检查失败时输出原因，并用非零退出码通知调用脚本。
        std::cerr << exception.what() << '\n';
        return 1;
    }
}
