#include "assembly/assembly_options.h"
#include "assembly/element_kernels.h"
#include "core/mesh.h"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace fem;

namespace {

void require_close(const char* label, Real value, Real tolerance) {
    if (std::abs(value) > tolerance || !std::isfinite(value)) {
        throw std::runtime_error(std::string(label) + " = " + std::to_string(value));
    }
}

void verify_symmetric(const std::vector<Real>& matrix, int n) {
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            require_close("hex8 stiffness symmetry",
                          matrix[static_cast<Size>(i) * n + j] -
                              matrix[static_cast<Size>(j) * n + i],
                          1.0e-10);
        }
    }
}

void verify_rigid_translation_mode(const std::vector<Real>& matrix, int n, int component) {
    for (int row = 0; row < n; ++row) {
        Real sum = 0.0;
        for (int node = 0; node < n / constants::DOFS_PER_NODE; ++node) {
            sum += matrix[static_cast<Size>(row) * n + node * constants::DOFS_PER_NODE + component];
        }
        require_close("hex8 rigid translation residual", sum, 1.0e-10);
    }
}

} // namespace

int main() {
    try {
        Mesh hex = Mesh::make_cube_hex8(1, 1, 1);
        AssemblyOptions options;
        options.kernel = KernelType::PhysicsSolid;
        options.young_modulus = 1.0;
        options.poisson_ratio = 0.3;

        std::vector<Real> ke;
        compute_element_matrix(hex, 0, options, ke);
        if (ke.size() != 24 * 24) {
            throw std::runtime_error("Expected C3D8 stiffness matrix to have 24x24 entries");
        }

        verify_symmetric(ke, 24);
        verify_rigid_translation_mode(ke, 24, 0);
        verify_rigid_translation_mode(ke, 24, 1);
        verify_rigid_translation_mode(ke, 24, 2);

        Mesh tet = Mesh::make_cube_tet4(1, 1, 1);
        compute_element_matrix(tet, 0, options, ke);
        if (ke.size() != 12 * 12) {
            throw std::runtime_error("Expected physics_solid Tet4 matrix to reuse 12x12 physics Tet4 kernel");
        }
        std::vector<Real> solid_tet = ke;
        options.kernel = KernelType::PhysicsTet4;
        compute_element_matrix(tet, 0, options, ke);
        if (ke.size() != solid_tet.size()) {
            throw std::runtime_error("PhysicsSolid and PhysicsTet4 Tet4 matrix sizes differ");
        }
        for (Size i = 0; i < ke.size(); ++i) {
            require_close("physics_solid Tet4 compatibility", solid_tet[i] - ke[i], 1.0e-12);
        }

        std::cout << "verify_physics_solid_kernel passed\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "verify_physics_solid_kernel failed: " << ex.what() << "\n";
        return 1;
    }
}
