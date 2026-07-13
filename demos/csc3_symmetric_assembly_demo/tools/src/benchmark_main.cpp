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
