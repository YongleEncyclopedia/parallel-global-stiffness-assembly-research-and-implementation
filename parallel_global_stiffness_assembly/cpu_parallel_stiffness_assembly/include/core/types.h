#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <algorithm>
#include <cctype>

namespace fem {

using Real = double;
using Index = std::int32_t;
using Size = std::size_t;

namespace constants {
constexpr int DOFS_PER_NODE = 3;
constexpr int HEX8_NODES_PER_ELEMENT = 8;
constexpr int TET4_NODES_PER_ELEMENT = 4;
constexpr Real DEFAULT_YOUNG_MODULUS = 210.0e9;
constexpr Real DEFAULT_POISSON_RATIO = 0.30;
constexpr Real TOLERANCE = 1.0e-10;
} // namespace constants

enum class ElementType {
    Hex8,
    Tet4
};

enum class KernelType {
    Simplified,
    PhysicsTet4
};

enum class AlgorithmType {
    CpuSerial,
    CpuAtomic,
    CpuPrivateCsr,
    CpuCooSortReduce,
    CpuGraphColoring,
    CpuRowOwner
};

inline std::string to_lower_ascii(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

inline std::string element_type_to_string(ElementType type) {
    switch (type) {
    case ElementType::Hex8: return "Hex8";
    case ElementType::Tet4: return "Tet4";
    }
    return "Unknown";
}

inline ElementType parse_element_type(const std::string& text) {
    const auto s = to_lower_ascii(text);
    if (s == "tet4" || s == "c3d4") return ElementType::Tet4;
    if (s == "hex8" || s == "c3d8") return ElementType::Hex8;
    throw std::invalid_argument("Unsupported element type: " + text);
}

inline int nodes_per_element(ElementType type) {
    switch (type) {
    case ElementType::Hex8: return constants::HEX8_NODES_PER_ELEMENT;
    case ElementType::Tet4: return constants::TET4_NODES_PER_ELEMENT;
    }
    throw std::invalid_argument("Unknown element type");
}

inline int dofs_per_element(ElementType type) {
    return nodes_per_element(type) * constants::DOFS_PER_NODE;
}

inline std::string kernel_type_to_string(KernelType type) {
    switch (type) {
    case KernelType::Simplified: return "simplified";
    case KernelType::PhysicsTet4: return "physics_tet4";
    }
    return "unknown";
}

inline KernelType parse_kernel_type(const std::string& text) {
    const auto s = to_lower_ascii(text);
    if (s == "simplified" || s == "simple" || s == "synthetic") return KernelType::Simplified;
    if (s == "physics_tet4" || s == "physics-tet4" || s == "tet4" || s == "c3d4") return KernelType::PhysicsTet4;
    throw std::invalid_argument("Unsupported kernel type: " + text);
}

inline std::string algorithm_to_string(AlgorithmType type) {
    switch (type) {
    case AlgorithmType::CpuSerial: return "cpu_serial";
    case AlgorithmType::CpuAtomic: return "cpu_atomic";
    case AlgorithmType::CpuPrivateCsr: return "cpu_private_csr";
    case AlgorithmType::CpuCooSortReduce: return "cpu_coo_sort_reduce";
    case AlgorithmType::CpuGraphColoring: return "cpu_graph_coloring";
    case AlgorithmType::CpuRowOwner: return "cpu_row_owner";
    }
    return "unknown";
}

inline AlgorithmType parse_algorithm_type(const std::string& text) {
    const auto s = to_lower_ascii(text);
    if (s == "serial" || s == "cpu_serial" || s == "cpu-serial") return AlgorithmType::CpuSerial;
    if (s == "atomic" || s == "addto" || s == "cpu_atomic" || s == "cpu-atomic") return AlgorithmType::CpuAtomic;
    if (s == "private" || s == "private_csr" || s == "cpu_private_csr" || s == "thread_private_csr") return AlgorithmType::CpuPrivateCsr;
    if (s == "coo" || s == "coo_sort" || s == "coo_sort_reduce" || s == "cpu_coo_sort_reduce") return AlgorithmType::CpuCooSortReduce;
    if (s == "coloring" || s == "graph_coloring" || s == "cpu_graph_coloring" || s == "color") return AlgorithmType::CpuGraphColoring;
    if (s == "row_owner" || s == "owner" || s == "owner_computes" || s == "cpu_row_owner") return AlgorithmType::CpuRowOwner;
    throw std::invalid_argument("Unsupported algorithm: " + text);
}

class FemException : public std::runtime_error {
public:
    explicit FemException(const std::string& msg) : std::runtime_error(msg) {}
};

} // namespace fem
