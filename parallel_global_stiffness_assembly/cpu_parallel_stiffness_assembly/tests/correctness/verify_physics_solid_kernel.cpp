#include "assembly/element_kernels.h"

#include "core/mesh.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace fem;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

Real max_abs_entry(const std::vector<Real>& values) {
    Real result = 0.0;
    for (Real value : values) result = std::max(result, std::abs(value));
    return result;
}

Mesh make_skew_hex8() {
    Mesh mesh;
    mesh.name = "skew_hex8_affine";
    mesh.nodes = {
        Node{0.00, 0.00, 0.00},
        Node{1.00, 0.00, 0.00},
        Node{1.25, 0.20, 0.00},
        Node{0.25, 0.20, 0.00},
        Node{0.10, 0.03, 0.10},
        Node{1.10, 0.03, 0.10},
        Node{1.35, 0.23, 0.10},
        Node{0.35, 0.23, 0.10},
    };
    Element e;
    e.type = ElementType::Hex8;
    e.node_count = constants::HEX8_NODES_PER_ELEMENT;
    e.nodes = {0, 1, 2, 3, 4, 5, 6, 7};
    mesh.elements.push_back(e);
    return mesh;
}

void verify_symmetric(const std::vector<Real>& ke, int n) {
    const Real scale = std::max<Real>(1.0, max_abs_entry(ke));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            const Real diff = std::abs(ke[static_cast<Size>(i) * n + j] -
                                       ke[static_cast<Size>(j) * n + i]);
            require(diff <= 1.0e-12 * scale, "Hex8/C3D8 local stiffness is not symmetric");
        }
    }
}

void verify_translation_rigid_mode(const std::vector<Real>& ke, int n, int component) {
    std::vector<Real> u(static_cast<Size>(n), 0.0);
    for (int node = 0; node < 8; ++node) u[static_cast<Size>(3 * node + component)] = 1.0;

    Real residual_norm = 0.0;
    Real matrix_norm = 0.0;
    for (int i = 0; i < n; ++i) {
        Real r = 0.0;
        for (int j = 0; j < n; ++j) {
            const Real kij = ke[static_cast<Size>(i) * n + j];
            r += kij * u[static_cast<Size>(j)];
            matrix_norm += kij * kij;
        }
        residual_norm += r * r;
    }
    residual_norm = std::sqrt(residual_norm);
    matrix_norm = std::sqrt(matrix_norm);
    require(residual_norm <= 1.0e-10 * std::max<Real>(1.0, matrix_norm),
            "Hex8/C3D8 local stiffness does not annihilate translation rigid mode");
}

Real quadratic_form(const std::vector<Real>& ke, const std::vector<Real>& u) {
    const int n = static_cast<int>(u.size());
    Real result = 0.0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            result += u[static_cast<Size>(i)] * ke[static_cast<Size>(i) * n + j] * u[static_cast<Size>(j)];
        }
    }
    return result;
}

void verify_hex8_c3d8_full_integration_kernel() {
    const Mesh mesh = Mesh::make_cube_hex8(1, 1, 1, 1.0, 0.2, 0.1);

    AssemblyOptions options;
    options.stiffness_model = StiffnessModel::LinearElasticSolid;
    options.young_modulus = 1.0;
    options.poisson_ratio = 0.3;

    std::vector<Real> ke;
    compute_element_matrix(mesh, 0, options, ke);

    constexpr int n = constants::HEX8_NODES_PER_ELEMENT * constants::DOFS_PER_NODE;
    require(static_cast<int>(ke.size()) == n * n, "Hex8/C3D8 local stiffness has wrong size");
    verify_symmetric(ke, n);
    verify_translation_rigid_mode(ke, n, 0);
    verify_translation_rigid_mode(ke, n, 1);
    verify_translation_rigid_mode(ke, n, 2);
}

void verify_skew_hex8_linear_patch_energy() {
    const Mesh mesh = make_skew_hex8();

    AssemblyOptions options;
    options.stiffness_model = StiffnessModel::LinearElasticSolid;
    options.young_modulus = 1.0;
    options.poisson_ratio = 0.25;

    std::vector<Real> ke;
    compute_element_matrix(mesh, 0, options, ke);

    constexpr int n = constants::HEX8_NODES_PER_ELEMENT * constants::DOFS_PER_NODE;
    std::vector<Real> u(static_cast<Size>(n), 0.0);
    for (int node = 0; node < 8; ++node) {
        u[static_cast<Size>(3 * node)] = mesh.nodes[static_cast<Size>(node)].x;
    }

    const Real lambda = options.young_modulus * options.poisson_ratio /
                        ((1.0 + options.poisson_ratio) * (1.0 - 2.0 * options.poisson_ratio));
    const Real mu = options.young_modulus / (2.0 * (1.0 + options.poisson_ratio));
    const Real expected = 0.02 * (lambda + 2.0 * mu);
    const Real actual = quadratic_form(ke, u);
    require(std::abs(actual - expected) <= 1.0e-11 * std::max<Real>(1.0, std::abs(expected)),
            "Skew Hex8/C3D8 linear patch energy does not match isotropic elasticity");
}

} // namespace

int main() {
    try {
        verify_hex8_c3d8_full_integration_kernel();
        verify_skew_hex8_linear_patch_energy();
    } catch (const std::exception& ex) {
        std::cerr << "VerifyPhysicsSolidKernel failed: " << ex.what() << '\n';
        return 1;
    }
    std::cout << "VerifyPhysicsSolidKernel passed\n";
    return 0;
}
