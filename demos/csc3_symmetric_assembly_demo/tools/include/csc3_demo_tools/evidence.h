#pragma once

#include "csc3_demo/assembly_helper.h"

#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

namespace csc3_demo::evidence {

/// Element formulations available to the internal generated evidence cases.
enum class ElementType {
    Tet4,
    Hex8,
};

struct Node {
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

/// Flat, compact, zero-based mesh parsed from an Abaqus input file.
struct ParsedMesh {
    std::string name;
    ElementType element_type = ElementType::Tet4;
    std::vector<Node> nodes;
    /// External Abaqus identifiers in input order.
    std::vector<ElementId> external_element_ids;
    /// Zero-based offsets into compact_node_indices, with one terminal offset.
    std::vector<Offset> element_node_offsets;
    /// Compact zero-based node indices in each element's local order.
    std::vector<std::size_t> compact_node_indices;
};

/// Internal fixture used to exercise assembly and a constrained displacement solve.
struct AssemblyCase {
    std::string name;
    ElementType element_type = ElementType::Tet4;
    std::vector<Node> nodes;
    ElementDofMap element_dof_map;
    ElementMatrixBatch element_matrices;
    std::vector<double> force;
    std::vector<GlobalDofIndex> constrained_dof_indices;
};

/// Independently assembled upper structure plus a complete dense matrix.
struct SerialAssemblyResult {
    GlobalDofIndex dimension = 0;
    std::vector<Offset> column_offsets;
    std::vector<GlobalDofIndex> row_indices;
    std::vector<double> dense_values;
};

struct MatrixComparison {
    bool structure_matches = false;
    double relative_frobenius_error = 0.0;
    double max_absolute_error = 0.0;
    double reference_max_absolute_value = 0.0;
    double max_absolute_tolerance = 0.0;
    bool passed = false;
};

struct DisplacementComparison {
    double relative_displacement_error = 0.0;
    double parallel_relative_residual = 0.0;
    double serial_relative_residual = 0.0;
    double parallel_displacement_norm = 0.0;
    double serial_displacement_norm = 0.0;
    bool passed = false;
};

struct ValidationResult {
    std::string case_name;
    ElementType element_type = ElementType::Tet4;
    std::size_t node_count = 0;
    std::size_t element_count = 0;
    std::size_t dof_count = 0;
    int thread_count = 0;
    MatrixComparison matrix;
    DisplacementComparison displacement;
    bool passed = false;
};

AssemblyCase make_cube_case(ElementType element_type,
                            int nx,
                            int ny,
                            int nz,
                            double young_modulus = 2.1e11,
                            double poisson_ratio = 0.3);

ParsedMesh parse_abaqus_inp(const std::filesystem::path& path);

AssemblyCase make_assembly_case(ParsedMesh parsed_mesh,
                                double young_modulus = 2.1e11,
                                double poisson_ratio = 0.3);

AssemblyCase load_abaqus_case(const std::filesystem::path& path,
                              double young_modulus = 2.1e11,
                              double poisson_ratio = 0.3);

SerialAssemblyResult assemble_serial_reference(const AssemblyCase& assembly_case);

MatrixComparison compare_matrices(const Csc3Matrix& candidate,
                                  const SerialAssemblyResult& reference);

ValidationResult validate_case(const AssemblyCase& assembly_case, int thread_count);

} // namespace csc3_demo::evidence
