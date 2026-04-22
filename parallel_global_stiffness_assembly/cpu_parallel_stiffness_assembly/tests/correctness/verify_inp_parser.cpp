#include "core/mesh.h"

#include <iostream>
#include <stdexcept>
#include <string>

int main() {
    try {
        const std::string path = std::string(PGSA_TEST_EXAMPLES_DIR) + "/tiny_c3d4_with_output_sections.inp";
        const fem::Mesh mesh = fem::Mesh::load_from_inp(path);
        if (mesh.num_nodes() != 4) {
            throw std::runtime_error("Expected 4 nodes, got " + std::to_string(mesh.num_nodes()));
        }
        if (mesh.num_elements() != 1) {
            throw std::runtime_error("Expected 1 element, got " + std::to_string(mesh.num_elements()));
        }
        if (mesh.elements.front().node_count != 4) {
            throw std::runtime_error("Expected Tet4 element");
        }
        std::cout << "verify_inp_parser passed\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_inp_parser failed: " << ex.what() << "\n";
        return 1;
    }
}
