// benchmark 可执行程序只负责接收 argv。参数解释、运行和错误处理都在
// run_benchmark_cli() 中，单元测试也可以直接调用同一套入口。
#include "csc3_demo_tools/benchmark.h"

#include <iostream>
#include <string>
#include <vector>

int main(int argument_count, char** argument_values) {
    std::vector<std::string> arguments;
    if (argument_count > 1) {
        arguments.reserve(static_cast<std::size_t>(argument_count - 1));
    }
    for (int index = 1; index < argument_count; ++index) {
        arguments.emplace_back(argument_values[index]);
    }
    return csc3_demo::evidence::run_benchmark_cli(arguments, std::cout, std::cerr);
}
