#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace csc3_demo;
using namespace csc3_demo::evidence;

void require_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
void require_equal(const T& actual, const T& expected, const std::string& label) {
    if (actual != expected) {
        throw std::runtime_error(label + " mismatch");
    }
}

class TemporaryInput {
public:
    explicit TemporaryInput(const std::string& contents) {
        static std::size_t sequence = 0;
        const auto tick = std::chrono::steady_clock::now()
                              .time_since_epoch()
                              .count();
        path_ = std::filesystem::temp_directory_path() /
                ("csc3-inp-case-" + std::to_string(tick) + "-" +
                 std::to_string(sequence++) + ".inp");
        std::ofstream output(path_, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw std::runtime_error("could not create temporary input");
        }
        output << contents;
        if (!output) {
            throw std::runtime_error("could not write temporary input");
        }
    }

    TemporaryInput(const TemporaryInput&) = delete;
    TemporaryInput& operator=(const TemporaryInput&) = delete;

    ~TemporaryInput() {
        std::error_code error;
        std::filesystem::remove(path_, error);
    }

    const std::filesystem::path& path() const noexcept {
        return path_;
    }

private:
    std::filesystem::path path_;
};

template <typename Fn>
void require_parse_failure(const std::string& contents,
                           const std::string& expected_fragment,
                           Fn&& operation) {
    const TemporaryInput input(contents);
    try {
        std::forward<Fn>(operation)(input.path());
    } catch (const std::exception& exception) {
        const std::string message = exception.what();
        require_true(message.find("line ") != std::string::npos,
                     "parse failure omitted a line number: " + message);
        require_true(message.find(expected_fragment) != std::string::npos,
                     "parse failure omitted expected context: " + message);
        return;
    }
    throw std::runtime_error("invalid input unexpectedly parsed successfully");
}

void require_finite_symmetric_segments(const AssemblyCase& assembly_case) {
    const auto& offsets = assembly_case.element_matrices.element_value_offsets;
    const auto& values = assembly_case.element_matrices.values_row_major;
    require_equal(offsets.size(),
                  assembly_case.element_dof_map.element_ids.size() + 1,
                  "element matrix offset count");
    for (std::size_t element = 0;
         element < assembly_case.element_dof_map.element_ids.size();
         ++element) {
        const std::size_t begin = static_cast<std::size_t>(offsets[element]);
        const std::size_t end = static_cast<std::size_t>(offsets[element + 1]);
        const std::size_t value_count = end - begin;
        const std::size_t dimension =
            assembly_case.element_type == ElementType::Tet4 ? 12 : 24;
        require_equal(value_count, dimension * dimension, "local matrix size");
        for (std::size_t row = 0; row < dimension; ++row) {
            for (std::size_t column = 0; column < dimension; ++column) {
                const double value = values[begin + row * dimension + column];
                require_true(std::isfinite(value),
                             "local matrix contains a nonfinite value");
                require_true(value == values[begin + column * dimension + row],
                             "local matrix is not exactly symmetric");
            }
        }
    }
}

void test_c3d4_gapped_nodes_and_unsorted_elements() {
    const TemporaryInput input(
        "*Heading\n"
        "** gapped labels and input-order compact numbering\n"
        "*nOdE\n"
        "30, 0, 1, 0\n"
        "10, 0, 0, 0\n"
        "99, 0, 0, 1\n"
        "20, 1, 0, 0\n"
        "*Nset, nset=ignored\n"
        "10, 20\n"
        "*ELEMENT, Elset=solid, TyPe = c3d4\n"
        "42, 10, 20, 30, 99\n"
        "7, 10, 30, 99, 20\n"
        "*Elset, elset=ignored\n"
        "7, 42\n");

    const ParsedMesh parsed = parse_abaqus_inp(input.path());
    require_equal(parsed.element_type, ElementType::Tet4, "parsed element type");
    require_equal(parsed.nodes.size(), std::size_t{4}, "parsed node count");
    require_equal(parsed.external_element_ids,
                  std::vector<ElementId>({42, 7}),
                  "input element order");
    require_equal(parsed.element_node_offsets,
                  std::vector<Offset>({0, 4, 8}),
                  "element node offsets");
    require_equal(parsed.compact_node_indices,
                  std::vector<std::size_t>({1, 3, 0, 2, 1, 0, 2, 3}),
                  "compact node mapping");

    AssemblyCase assembly_case = make_assembly_case(parsed);
    require_equal(assembly_case.element_dof_map.element_ids,
                  std::vector<ElementId>({7, 42}),
                  "canonical external element IDs");
    require_equal(assembly_case.element_dof_map.element_dof_offsets,
                  std::vector<Offset>({0, 12, 24}),
                  "Tet4 DOF offsets");
    require_equal(assembly_case.element_dof_map.global_dof_indices[0],
                  GlobalDofIndex{3},
                  "canonical first element first DOF");
    require_equal(assembly_case.element_dof_map.global_dof_indices[3],
                  GlobalDofIndex{0},
                  "canonical first element second-node DOF");
    require_finite_symmetric_segments(assembly_case);
}

void test_c3d8_case_insensitive_physical_matrix() {
    const TemporaryInput input(
        "*NODE\n"
        "101,0,0,0\n"
        "205,1,0,0\n"
        "309,1,1,0\n"
        "410,0,1,0\n"
        "511,0,0,1\n"
        "612,1,0,1\n"
        "713,1,1,1\n"
        "814,0,1,1\n"
        "*element, type = C3d8\n"
        "9,101,205,309,410,511,612,713,814\n");

    const AssemblyCase loaded = load_abaqus_case(input.path());
    require_equal(loaded.element_type, ElementType::Hex8, "Hex8 element type");
    require_equal(loaded.element_dof_map.element_ids,
                  std::vector<ElementId>({9}),
                  "Hex8 external element ID");
    require_finite_symmetric_segments(loaded);

    const AssemblyCase generated = make_cube_case(ElementType::Hex8, 1, 1, 1);
    require_equal(loaded.element_matrices.values_row_major,
                  generated.element_matrices.values_row_major,
                  "shared Hex8 physical stiffness");
}

void test_rejected_inputs_report_lines() {
    require_parse_failure(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789\nsize 123\n",
        "Git LFS pointer",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });

    const std::string nodes =
        "*Node\n1,0,0,0\n2,1,0,0\n3,0,1,0\n4,0,0,1\n";
    require_parse_failure(
        "*Node\n1,0,0,0\n1,1,0,0\n*Element,type=C3D4\n1,1,1,1,1\n",
        "duplicate node",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D4\n8,1,2,3,4\n8,1,2,3,4\n",
        "duplicate element",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D4\n8,1,2,3,999\n",
        "unknown node",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        "*Node\n1,not-a-number,0,0\n*Element,type=C3D4\n1,1,1,1,1\n",
        "coordinate",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        "*Node\n1,nan,0,0\n*Element,type=C3D4\n1,1,1,1,1\n",
        "nonfinite",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D4\n8,1,2,3\n",
        "element record",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D10\n",
        "unsupported element type",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D4\n1,1,2,3,4\n*Element,type=C3D8\n",
        "mixed element formulations",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        "*Heading\n** no mesh\n",
        "empty mesh",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
    require_parse_failure(
        nodes + "*Element,type=C3D4\n2147483648,1,2,3,4\n",
        "element identifier",
        [](const auto& path) { static_cast<void>(parse_abaqus_inp(path)); });
}

} // namespace

int main() {
    try {
        test_c3d4_gapped_nodes_and_unsorted_elements();
        test_c3d8_case_insensitive_physical_matrix();
        test_rejected_inputs_report_lines();
    } catch (const std::exception& exception) {
        std::cerr << exception.what() << '\n';
        return 1;
    }
    return 0;
}
