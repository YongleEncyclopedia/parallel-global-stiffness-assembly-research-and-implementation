#include "assembly/element_kernels.h"

#include <array>
#include <cmath>
#include <stdexcept>

namespace fem {
namespace {

void simplified_kernel(Size element_id, int edofs, std::vector<Real>& ke) {
    ke.assign(static_cast<Size>(edofs) * edofs, 0.0);
    const Real scale = 1.0 + static_cast<Real>((element_id * 17) % 97) * 1.0e-4;
    for (int i = 0; i < edofs; ++i) {
        for (int j = 0; j < edofs; ++j) {
            Real v = 0.0;
            if (i == j) {
                v = 2.0 * scale + 0.01 * (i % 3);
            } else {
                v = 0.02 * scale / static_cast<Real>(1 + std::abs(i - j));
            }
            ke[static_cast<Size>(i) * edofs + j] = v;
        }
    }
}

Real det3(const std::array<std::array<Real, 3>, 3>& a) {
    return a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) -
           a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) +
           a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
}

bool invert4x4(std::array<std::array<Real, 4>, 4> a,
               std::array<std::array<Real, 4>, 4>& inv) {
    for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) inv[i][j] = (i == j) ? 1.0 : 0.0;
    }
    for (int col = 0; col < 4; ++col) {
        int pivot = col;
        Real best = std::abs(a[col][col]);
        for (int r = col + 1; r < 4; ++r) {
            const Real candidate = std::abs(a[r][col]);
            if (candidate > best) {
                best = candidate;
                pivot = r;
            }
        }
        if (best < 1.0e-30) return false;
        if (pivot != col) {
            std::swap(a[pivot], a[col]);
            std::swap(inv[pivot], inv[col]);
        }
        const Real diag = a[col][col];
        for (int j = 0; j < 4; ++j) {
            a[col][j] /= diag;
            inv[col][j] /= diag;
        }
        for (int r = 0; r < 4; ++r) {
            if (r == col) continue;
            const Real factor = a[r][col];
            if (factor == 0.0) continue;
            for (int j = 0; j < 4; ++j) {
                a[r][j] -= factor * a[col][j];
                inv[r][j] -= factor * inv[col][j];
            }
        }
    }
    return true;
}

void physics_tet4_kernel(const Mesh& mesh, Size element_id, const AssemblyOptions& options, std::vector<Real>& ke) {
    const auto& elem = mesh.elements[element_id];
    if (elem.type != ElementType::Tet4 || elem.node_count != 4) {
        simplified_kernel(element_id, elem.node_count * constants::DOFS_PER_NODE, ke);
        return;
    }

    std::array<Node, 4> p{};
    for (int i = 0; i < 4; ++i) p[i] = mesh.nodes[static_cast<Size>(elem.nodes[i])];

    std::array<std::array<Real, 3>, 3> jac{{
        {{p[1].x - p[0].x, p[1].y - p[0].y, p[1].z - p[0].z}},
        {{p[2].x - p[0].x, p[2].y - p[0].y, p[2].z - p[0].z}},
        {{p[3].x - p[0].x, p[3].y - p[0].y, p[3].z - p[0].z}}
    }};
    const Real volume = std::abs(det3(jac)) / 6.0;
    if (!(volume > 1.0e-30)) {
        simplified_kernel(element_id, constants::TET4_NODES_PER_ELEMENT * constants::DOFS_PER_NODE, ke);
        return;
    }

    std::array<std::array<Real, 4>, 4> m{{
        {{1.0, p[0].x, p[0].y, p[0].z}},
        {{1.0, p[1].x, p[1].y, p[1].z}},
        {{1.0, p[2].x, p[2].y, p[2].z}},
        {{1.0, p[3].x, p[3].y, p[3].z}}
    }};
    std::array<std::array<Real, 4>, 4> inv{};
    if (!invert4x4(m, inv)) {
        simplified_kernel(element_id, constants::TET4_NODES_PER_ELEMENT * constants::DOFS_PER_NODE, ke);
        return;
    }

    // Column i of inv stores [a_i, b_i, c_i, d_i]^T for N_i = a_i + b_i x + c_i y + d_i z.
    std::array<std::array<Real, 12>, 6> b{};
    for (int node = 0; node < 4; ++node) {
        const Real dx = inv[1][node];
        const Real dy = inv[2][node];
        const Real dz = inv[3][node];
        const int c = 3 * node;
        b[0][c + 0] = dx;
        b[1][c + 1] = dy;
        b[2][c + 2] = dz;
        b[3][c + 0] = dy;
        b[3][c + 1] = dx;
        b[4][c + 1] = dz;
        b[4][c + 2] = dy;
        b[5][c + 0] = dz;
        b[5][c + 2] = dx;
    }

    const Real e = options.young_modulus;
    const Real nu = options.poisson_ratio;
    const Real lambda = e * nu / ((1.0 + nu) * (1.0 - 2.0 * nu));
    const Real mu = e / (2.0 * (1.0 + nu));
    std::array<std::array<Real, 6>, 6> d{};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) d[i][j] = lambda;
        d[i][i] = lambda + 2.0 * mu;
    }
    d[3][3] = mu;
    d[4][4] = mu;
    d[5][5] = mu;

    ke.assign(12 * 12, 0.0);
    for (int i = 0; i < 12; ++i) {
        for (int j = 0; j < 12; ++j) {
            Real v = 0.0;
            for (int a = 0; a < 6; ++a) {
                for (int c = 0; c < 6; ++c) v += b[a][i] * d[a][c] * b[c][j];
            }
            ke[static_cast<Size>(i) * 12 + j] = volume * v;
        }
    }
}

} // namespace

void compute_element_matrix(const Mesh& mesh,
                            Size element_id,
                            const AssemblyOptions& options,
                            std::vector<Real>& ke) {
    const auto& elem = mesh.elements[element_id];
    const int edofs = elem.node_count * constants::DOFS_PER_NODE;
    if (options.kernel == KernelType::PhysicsTet4) {
        physics_tet4_kernel(mesh, element_id, options, ke);
    } else {
        simplified_kernel(element_id, edofs, ke);
    }
}

} // namespace fem
