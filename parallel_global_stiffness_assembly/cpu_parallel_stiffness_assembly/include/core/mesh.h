#pragma once

#include "core/types.h"

#include <array>
#include <string>
#include <vector>

namespace fem {

struct Node {
    Real x = 0.0;
    Real y = 0.0;
    Real z = 0.0;
};

struct Element {
    ElementType type = ElementType::Tet4;
    std::array<Index, constants::HEX8_NODES_PER_ELEMENT> nodes{};
    int node_count = constants::TET4_NODES_PER_ELEMENT;
};

class Mesh {
public:
    std::vector<Node> nodes;
    std::vector<Element> elements;
    std::string name = "mesh";

    [[nodiscard]] Size num_nodes() const noexcept { return nodes.size(); }
    [[nodiscard]] Size num_elements() const noexcept { return elements.size(); }
    [[nodiscard]] Size num_dofs() const noexcept { return nodes.size() * constants::DOFS_PER_NODE; }
    [[nodiscard]] bool empty() const noexcept { return nodes.empty() || elements.empty(); }
    [[nodiscard]] ElementType dominant_element_type() const;

    static Mesh make_cube_tet4(int nx, int ny, int nz,
                               Real lx = 1.0, Real ly = 1.0, Real lz = 1.0);
    static Mesh make_cube_hex8(int nx, int ny, int nz,
                               Real lx = 1.0, Real ly = 1.0, Real lz = 1.0);
    static Mesh load_from_inp(const std::string& path);
};

std::vector<Index> element_dofs(const Element& element);
std::string mesh_summary(const Mesh& mesh);

} // namespace fem
