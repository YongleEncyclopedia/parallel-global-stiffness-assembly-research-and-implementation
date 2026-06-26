#include "csc3_demo/assembly_helper.h"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--report") {
            std::ofstream out(argv[2]);
            if (!out) {
                std::cerr << "Cannot open report path: " << argv[2] << '\n';
                return 2;
            }
            out << csc3_demo::generate_demo_report();
            return 0;
        }

        std::cout << csc3_demo::generate_demo_report();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << '\n';
        return 1;
    }
}
