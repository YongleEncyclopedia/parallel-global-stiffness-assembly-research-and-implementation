#include "core/mesh.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace fem {
namespace {

std::string trim(std::string s) {
    auto not_space = [](unsigned char c) { return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
    s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
    return s;
}

std::string upper_ascii(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return s;
}

std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> out;
    std::string token;
    std::stringstream ss(line);
    while (std::getline(ss, token, ',')) out.push_back(trim(token));
    return out;
}

Index structured_node_id(int i, int j, int k, int nx, int ny) {
    return static_cast<Index>((k * (ny + 1) + j) * (nx + 1) + i);
}

Element make_tet(Index a, Index b, Index c, Index d) {
    Element e;
    e.type = ElementType::Tet4;
    e.node_count = constants::TET4_NODES_PER_ELEMENT;
    e.nodes = {a, b, c, d, 0, 0, 0, 0};
    return e;
}

Element make_hex(Index n0, Index n1, Index n2, Index n3,
                 Index n4, Index n5, Index n6, Index n7) {
    Element e;
    e.type = ElementType::Hex8;
    e.node_count = constants::HEX8_NODES_PER_ELEMENT;
    e.nodes = {n0, n1, n2, n3, n4, n5, n6, n7};
    return e;
}

bool contains_type(const std::string& header, const std::string& type) {
    return upper_ascii(header).find("TYPE=" + type) != std::string::npos;
}

std::string header_keyword(const std::string& header) {
    return trim(upper_ascii(header.substr(0, header.find(','))));
}

} // namespace

ElementType Mesh::dominant_element_type() const {
    if (elements.empty()) return ElementType::Tet4;
    Size tet = 0;
    Size hex = 0;
    for (const auto& e : elements) {
        if (e.type == ElementType::Tet4) ++tet;
        if (e.type == ElementType::Hex8) ++hex;
    }
    return hex > tet ? ElementType::Hex8 : ElementType::Tet4;
}

Mesh Mesh::make_cube_tet4(int nx, int ny, int nz, Real lx, Real ly, Real lz) {
    if (nx <= 0 || ny <= 0 || nz <= 0) {
        throw std::invalid_argument("Cube dimensions must be positive");
    }
    Mesh mesh;
    mesh.name = "cube_tet4_" + std::to_string(nx) + "x" + std::to_string(ny) + "x" + std::to_string(nz);
    mesh.nodes.reserve(static_cast<Size>(nx + 1) * static_cast<Size>(ny + 1) * static_cast<Size>(nz + 1));
    for (int k = 0; k <= nz; ++k) {
        for (int j = 0; j <= ny; ++j) {
            for (int i = 0; i <= nx; ++i) {
                mesh.nodes.push_back(Node{lx * i / nx, ly * j / ny, lz * k / nz});
            }
        }
    }
    mesh.elements.reserve(static_cast<Size>(nx) * ny * nz * 6);
    for (int k = 0; k < nz; ++k) {
        for (int j = 0; j < ny; ++j) {
            for (int i = 0; i < nx; ++i) {
                const Index n000 = structured_node_id(i, j, k, nx, ny);
                const Index n100 = structured_node_id(i + 1, j, k, nx, ny);
                const Index n010 = structured_node_id(i, j + 1, k, nx, ny);
                const Index n110 = structured_node_id(i + 1, j + 1, k, nx, ny);
                const Index n001 = structured_node_id(i, j, k + 1, nx, ny);
                const Index n101 = structured_node_id(i + 1, j, k + 1, nx, ny);
                const Index n011 = structured_node_id(i, j + 1, k + 1, nx, ny);
                const Index n111 = structured_node_id(i + 1, j + 1, k + 1, nx, ny);
                mesh.elements.push_back(make_tet(n000, n100, n110, n111));
                mesh.elements.push_back(make_tet(n000, n110, n010, n111));
                mesh.elements.push_back(make_tet(n000, n010, n011, n111));
                mesh.elements.push_back(make_tet(n000, n011, n001, n111));
                mesh.elements.push_back(make_tet(n000, n001, n101, n111));
                mesh.elements.push_back(make_tet(n000, n101, n100, n111));
            }
        }
    }
    return mesh;
}

Mesh Mesh::make_cube_hex8(int nx, int ny, int nz, Real lx, Real ly, Real lz) {
    if (nx <= 0 || ny <= 0 || nz <= 0) {
        throw std::invalid_argument("Cube dimensions must be positive");
    }
    Mesh mesh;
    mesh.name = "cube_hex8_" + std::to_string(nx) + "x" + std::to_string(ny) + "x" + std::to_string(nz);
    mesh.nodes.reserve(static_cast<Size>(nx + 1) * static_cast<Size>(ny + 1) * static_cast<Size>(nz + 1));
    for (int k = 0; k <= nz; ++k) {
        for (int j = 0; j <= ny; ++j) {
            for (int i = 0; i <= nx; ++i) {
                mesh.nodes.push_back(Node{lx * i / nx, ly * j / ny, lz * k / nz});
            }
        }
    }
    mesh.elements.reserve(static_cast<Size>(nx) * ny * nz);
    for (int k = 0; k < nz; ++k) {
        for (int j = 0; j < ny; ++j) {
            for (int i = 0; i < nx; ++i) {
                mesh.elements.push_back(make_hex(
                    structured_node_id(i, j, k, nx, ny),
                    structured_node_id(i + 1, j, k, nx, ny),
                    structured_node_id(i + 1, j + 1, k, nx, ny),
                    structured_node_id(i, j + 1, k, nx, ny),
                    structured_node_id(i, j, k + 1, nx, ny),
                    structured_node_id(i + 1, j, k + 1, nx, ny),
                    structured_node_id(i + 1, j + 1, k + 1, nx, ny),
                    structured_node_id(i, j + 1, k + 1, nx, ny)));
            }
        }
    }
    return mesh;
}

Mesh Mesh::load_from_inp(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Cannot open .inp file: " + path);

    Mesh mesh;
    mesh.name = path;
    std::unordered_map<long long, Index> node_id_to_index;

    enum class Section { None, Node, ElementTet4, ElementHex8, ElementUnsupported };
    Section section = Section::None;
    std::string line;
    Size line_no = 0;
    while (std::getline(in, line)) {
        ++line_no;
        line = trim(line);
        if (line.empty() || line.rfind("**", 0) == 0) continue;
        if (line[0] == '*') {
            const auto upper = upper_ascii(line);
            const auto keyword = header_keyword(line);
            if (keyword == "*NODE") {
                section = Section::Node;
            } else if (keyword == "*ELEMENT" && contains_type(upper, "C3D4")) {
                section = Section::ElementTet4;
            } else if (keyword == "*ELEMENT" && contains_type(upper, "C3D8")) {
                section = Section::ElementHex8;
            } else {
                section = Section::ElementUnsupported;
            }
            continue;
        }

        const auto fields = split_csv(line);
        if (section == Section::Node) {
            if (fields.size() < 4) throw std::runtime_error("Invalid *Node line " + std::to_string(line_no));
            const long long external_id = std::stoll(fields[0]);
            Node n{std::stod(fields[1]), std::stod(fields[2]), std::stod(fields[3])};
            const Index internal = static_cast<Index>(mesh.nodes.size());
            node_id_to_index[external_id] = internal;
            mesh.nodes.push_back(n);
        } else if (section == Section::ElementTet4 || section == Section::ElementHex8) {
            const int nnode = (section == Section::ElementTet4) ? 4 : 8;
            if (static_cast<int>(fields.size()) < nnode + 1) {
                throw std::runtime_error("Invalid *Element line " + std::to_string(line_no));
            }
            Element e;
            e.type = (section == Section::ElementTet4) ? ElementType::Tet4 : ElementType::Hex8;
            e.node_count = nnode;
            for (int i = 0; i < nnode; ++i) {
                const long long external_node = std::stoll(fields[1 + i]);
                auto it = node_id_to_index.find(external_node);
                if (it == node_id_to_index.end()) {
                    throw std::runtime_error("Element references unknown node " + std::to_string(external_node) +
                                             " at line " + std::to_string(line_no));
                }
                e.nodes[i] = it->second;
            }
            mesh.elements.push_back(e);
        }
    }
    if (mesh.empty()) throw std::runtime_error("No supported nodes/elements were parsed from " + path);
    return mesh;
}

std::vector<Index> element_dofs(const Element& element) {
    std::vector<Index> dofs;
    dofs.reserve(static_cast<Size>(element.node_count) * constants::DOFS_PER_NODE);
    for (int a = 0; a < element.node_count; ++a) {
        const Index node = element.nodes[a];
        for (int c = 0; c < constants::DOFS_PER_NODE; ++c) {
            dofs.push_back(node * constants::DOFS_PER_NODE + c);
        }
    }
    return dofs;
}

std::string mesh_summary(const Mesh& mesh) {
    std::ostringstream os;
    os << "name=" << mesh.name
       << ", nodes=" << mesh.num_nodes()
       << ", elements=" << mesh.num_elements()
       << ", dofs=" << mesh.num_dofs()
       << ", dominant_element=" << element_type_to_string(mesh.dominant_element_type());
    return os.str();
}

} // namespace fem
