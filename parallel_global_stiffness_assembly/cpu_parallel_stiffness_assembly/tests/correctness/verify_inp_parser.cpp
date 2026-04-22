#include "core/mesh.h"

#include <iostream>
#include <stdexcept>
#include <string>

int main() {
    try {
        const std::string output_sections_path =
            std::string(PGSA_TEST_EXAMPLES_DIR) + "/tiny_c3d4_with_output_sections.inp";
        const fem::Mesh output_sections_mesh = fem::Mesh::load_from_inp(output_sections_path);
        if (output_sections_mesh.num_nodes() != 4) {
            throw std::runtime_error("Expected 4 nodes, got " + std::to_string(output_sections_mesh.num_nodes()));
        }
        if (output_sections_mesh.num_elements() != 1) {
            throw std::runtime_error("Expected 1 element, got " + std::to_string(output_sections_mesh.num_elements()));
        }
        if (output_sections_mesh.elements.front().node_count != 4) {
            throw std::runtime_error("Expected Tet4 element");
        }

        const std::string gap_labels_path =
            std::string(PGSA_TEST_EXAMPLES_DIR) + "/small_c3d4_gap_labels.inp";
        const fem::Mesh gap_labels_mesh = fem::Mesh::load_from_inp(gap_labels_path);
        if (gap_labels_mesh.num_nodes() != 5) {
            throw std::runtime_error("Expected 5 nodes in gap-label sample, got " +
                                     std::to_string(gap_labels_mesh.num_nodes()));
        }
        if (gap_labels_mesh.num_elements() != 2) {
            throw std::runtime_error("Expected 2 elements in gap-label sample, got " +
                                     std::to_string(gap_labels_mesh.num_elements()));
        }
        if (gap_labels_mesh.elements[0].node_count != 4 || gap_labels_mesh.elements[1].node_count != 4) {
            throw std::runtime_error("Gap-label sample should contain Tet4 elements only");
        }
        const auto& first = gap_labels_mesh.elements[0].nodes;
        const auto& second = gap_labels_mesh.elements[1].nodes;
        if (!(first[0] == 0 && first[1] == 1 && first[2] == 2 && first[3] == 3)) {
            throw std::runtime_error("First gap-label element was not remapped to contiguous internal node ids");
        }
        if (!(second[0] == 1 && second[1] == 2 && second[2] == 3 && second[3] == 4)) {
            throw std::runtime_error("Second gap-label element was not remapped to contiguous internal node ids");
        }

        std::cout << "verify_inp_parser passed\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_inp_parser failed: " << ex.what() << "\n";
        return 1;
    }
}
