#include "assembly/assembler_factory.h"
#include "assembly/assembly_plan.h"
#include "core/csr_matrix.h"
#include "core/mesh.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace fem;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void verify_mesh_shape(const Mesh& mesh,
                       Size expected_nodes,
                       Size expected_elements,
                       ElementType expected_type,
                       int expected_nodes_per_element) {
    require(mesh.num_nodes() == expected_nodes, "mesh node count mismatch");
    require(mesh.num_elements() == expected_elements, "mesh element count mismatch");
    require(mesh.num_dofs() == expected_nodes * constants::DOFS_PER_NODE,
            "mesh DOF count mismatch");
    require(mesh.dominant_element_type() == expected_type, "mesh element type mismatch");
    for (const auto& element : mesh.elements) {
        require(element.type == expected_type, "mesh contains an unexpected element type");
        require(element.node_count == expected_nodes_per_element,
                "mesh element node count mismatch");
    }
}

void verify_csr_structure(const Mesh& mesh, const CsrMatrix& csr) {
    const auto expected_dimension = static_cast<Index>(mesh.num_dofs());
    require(csr.n_rows == expected_dimension, "CSR row count mismatch");
    require(csr.n_cols == expected_dimension, "CSR column count mismatch");
    require(csr.row_offsets.size() == static_cast<Size>(csr.n_rows) + 1,
            "CSR row-offset size mismatch");
    require(!csr.row_offsets.empty() && csr.row_offsets.front() == 0,
            "CSR row offsets must start at zero");
    require(static_cast<Size>(csr.row_offsets.back()) == csr.nnz(),
            "CSR final row offset must equal nnz");
    require(csr.values.size() == csr.nnz(), "CSR value storage must match nnz");

    for (Index row = 0; row < csr.n_rows; ++row) {
        const Size begin = static_cast<Size>(csr.row_offsets[static_cast<Size>(row)]);
        const Size end = static_cast<Size>(csr.row_offsets[static_cast<Size>(row) + 1]);
        require(begin <= end && end <= csr.col_indices.size(),
                "CSR row offsets are not monotone and bounded");
        require(std::is_sorted(csr.col_indices.begin() + static_cast<std::ptrdiff_t>(begin),
                               csr.col_indices.begin() + static_cast<std::ptrdiff_t>(end)),
                "CSR column indices are not sorted within a row");
        require(std::adjacent_find(
                    csr.col_indices.begin() + static_cast<std::ptrdiff_t>(begin),
                    csr.col_indices.begin() + static_cast<std::ptrdiff_t>(end)) ==
                    csr.col_indices.begin() + static_cast<std::ptrdiff_t>(end),
                "CSR row contains duplicate column indices");
        for (Size position = begin; position < end; ++position) {
            const Index column = csr.col_indices[position];
            require(column >= 0 && column < csr.n_cols, "CSR column index is out of range");
            require(csr.find_position(row, column) == static_cast<Index>(position),
                    "CSR find_position returned the wrong position");
        }
    }
}

void verify_plan(const Mesh& mesh, const CsrMatrix& csr, const AssemblyPlan& plan) {
    require(plan.num_elements() == mesh.num_elements(), "assembly-plan element count mismatch");
    require(plan.element_offsets.size() == mesh.num_elements() + 1,
            "assembly-plan offset size mismatch");
    require(!plan.element_offsets.empty() && plan.element_offsets.front() == 0,
            "assembly-plan offsets must start at zero");

    Size expected_scatter_size = 0;
    for (Size element = 0; element < mesh.num_elements(); ++element) {
        const int dof_count = mesh.elements[element].node_count * constants::DOFS_PER_NODE;
        require(plan.element_dof_count(element) == dof_count,
                "assembly-plan element DOF count mismatch");
        expected_scatter_size += static_cast<Size>(dof_count) * static_cast<Size>(dof_count);

        const Index* dofs = plan.element_dofs_ptr(element);
        const Index* scatter = plan.element_scatter_ptr(element);
        for (int row = 0; row < dof_count; ++row) {
            for (int column = 0; column < dof_count; ++column) {
                const Index position = scatter[row * dof_count + column];
                require(position == csr.find_position(dofs[row], dofs[column]),
                        "assembly-plan scatter entry does not match the CSR structure");
            }
        }
    }
    require(plan.dofs.size() == static_cast<Size>(plan.element_offsets.back()),
            "assembly-plan DOF storage mismatch");
    require(plan.scatter.size() == expected_scatter_size,
            "assembly-plan scatter storage mismatch");
}

void verify_current_assemblers(const Mesh& mesh,
                               const CsrMatrix& csr,
                               const AssemblyPlan& plan) {
    AssemblyOptions options;
    options.stiffness_model = StiffnessModel::LinearElasticSolid;
    options.threads = 2;

    auto reference = AssemblerFactory::create_serial(options);
    IAssembler& reference_interface = *reference;
    reference_interface.set_problem(mesh, csr, plan);
    reference_interface.prepare();
    reference_interface.assemble();
    require(std::any_of(reference_interface.get_result().values.begin(),
                        reference_interface.get_result().values.end(),
                        [](Real value) { return value != Real{0}; }),
            "physical serial assembly produced an all-zero matrix");

    for (AlgorithmType algorithm : AssemblerFactory::get_available_algorithms()) {
        auto candidate = AssemblerFactory::create(algorithm, options);
        IAssembler& candidate_interface = *candidate;
        candidate_interface.set_problem(mesh, csr, plan);
        require(candidate_interface.get_result().same_structure(csr),
                "IAssembler::set_problem did not preserve the CSR structure");
        candidate_interface.prepare();
        candidate_interface.assemble();

        const MatrixError error = compare_values(reference_interface.get_result(),
                                                 candidate_interface.get_result());
        require(error.same_structure, "assembler result structure differs from serial");
        require(std::isfinite(error.relative_l2) && error.relative_l2 <= 1.0e-8,
                "assembler values differ from serial");
    }

    CsrMatrix mismatched;
    const MatrixError mismatch = compare_values(reference_interface.get_result(), mismatched);
    require(!mismatch.same_structure, "compare_values did not reject a structural mismatch");
}

void verify_mesh(const Mesh& mesh) {
    const CsrMatrix csr = CsrMatrix::build_sparsity(mesh);
    verify_csr_structure(mesh, csr);
    const AssemblyPlan plan = build_assembly_plan(mesh, csr);
    verify_plan(mesh, csr, plan);
    verify_current_assemblers(mesh, csr, plan);
}

} // namespace

int main() {
    try {
        const Mesh hex8 = Mesh::make_cube_hex8(2, 1, 1);
        verify_mesh_shape(hex8, 12, 2, ElementType::Hex8, constants::HEX8_NODES_PER_ELEMENT);
        verify_mesh(hex8);

        const Mesh tet4 = Mesh::make_cube_tet4(1, 1, 1);
        verify_mesh_shape(tet4, 8, 6, ElementType::Tet4, constants::TET4_NODES_PER_ELEMENT);
        verify_mesh(tet4);
    } catch (const std::exception& ex) {
        std::cerr << "VerifyCoreStructures failed: " << ex.what() << '\n';
        return 1;
    }
    std::cout << "VerifyCoreStructures passed\n";
    return 0;
}
