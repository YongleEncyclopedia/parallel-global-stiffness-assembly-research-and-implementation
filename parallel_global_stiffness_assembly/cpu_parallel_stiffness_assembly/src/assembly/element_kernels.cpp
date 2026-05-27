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

bool invert3x3(const std::array<std::array<Real, 3>, 3>& a,
               std::array<std::array<Real, 3>, 3>& inv,
               Real& det) {
    det = det3(a);
    if (std::abs(det) < 1.0e-30) return false;

    inv[0][0] = (a[1][1] * a[2][2] - a[1][2] * a[2][1]) / det;
    inv[0][1] = (a[0][2] * a[2][1] - a[0][1] * a[2][2]) / det;
    inv[0][2] = (a[0][1] * a[1][2] - a[0][2] * a[1][1]) / det;
    inv[1][0] = (a[1][2] * a[2][0] - a[1][0] * a[2][2]) / det;
    inv[1][1] = (a[0][0] * a[2][2] - a[0][2] * a[2][0]) / det;
    inv[1][2] = (a[0][2] * a[1][0] - a[0][0] * a[1][2]) / det;
    inv[2][0] = (a[1][0] * a[2][1] - a[1][1] * a[2][0]) / det;
    inv[2][1] = (a[0][1] * a[2][0] - a[0][0] * a[2][1]) / det;
    inv[2][2] = (a[0][0] * a[1][1] - a[0][1] * a[1][0]) / det;
    return true;
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

std::array<std::array<Real, 6>, 6> elasticity_matrix(const AssemblyOptions& options) {
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
    return d;
}

void physics_tet4_kernel(const Mesh& mesh, Size element_id, const AssemblyOptions& options, std::vector<Real>& ke) {
    const auto& elem = mesh.elements[element_id];
    if (elem.type != ElementType::Tet4 || elem.node_count != 4) {
        throw std::invalid_argument("physics_tet4 stiffness model requires Tet4/C3D4 elements, got " +
                                    element_type_to_string(elem.type));
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
        throw std::invalid_argument("Degenerate Tet4/C3D4 element cannot use physical stiffness model");
    }

    std::array<std::array<Real, 4>, 4> m{{
        {{1.0, p[0].x, p[0].y, p[0].z}},
        {{1.0, p[1].x, p[1].y, p[1].z}},
        {{1.0, p[2].x, p[2].y, p[2].z}},
        {{1.0, p[3].x, p[3].y, p[3].z}}
    }};
    std::array<std::array<Real, 4>, 4> inv{};
    if (!invert4x4(m, inv)) {
        throw std::invalid_argument("Singular Tet4/C3D4 geometry cannot use physical stiffness model");
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

    const auto d = elasticity_matrix(options);

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

void physics_hex8_kernel(const Mesh& mesh, Size element_id, const AssemblyOptions& options, std::vector<Real>& ke) {
    const auto& elem = mesh.elements[element_id];
    if (elem.type != ElementType::Hex8 || elem.node_count != 8) {
        throw std::invalid_argument("linear_elastic_solid Hex8/C3D8 stiffness path requires Hex8/C3D8 elements, got " +
                                    element_type_to_string(elem.type));
    }

    static constexpr std::array<std::array<Real, 3>, 8> natural_nodes{{
        {{-1.0, -1.0, -1.0}},
        {{ 1.0, -1.0, -1.0}},
        {{ 1.0,  1.0, -1.0}},
        {{-1.0,  1.0, -1.0}},
        {{-1.0, -1.0,  1.0}},
        {{ 1.0, -1.0,  1.0}},
        {{ 1.0,  1.0,  1.0}},
        {{-1.0,  1.0,  1.0}},
    }};
    const Real g = 1.0 / std::sqrt(3.0);
    const std::array<Real, 2> gauss{{-g, g}};
    const auto d = elasticity_matrix(options);

    std::array<Node, 8> p{};
    for (int i = 0; i < 8; ++i) p[i] = mesh.nodes[static_cast<Size>(elem.nodes[i])];

    ke.assign(24 * 24, 0.0);
    for (Real xi : gauss) {
        for (Real eta : gauss) {
            for (Real zeta : gauss) {
                std::array<std::array<Real, 3>, 8> dnat{};
                for (int a = 0; a < 8; ++a) {
                    const Real sx = natural_nodes[a][0];
                    const Real sy = natural_nodes[a][1];
                    const Real sz = natural_nodes[a][2];
                    dnat[a][0] = 0.125 * sx * (1.0 + sy * eta) * (1.0 + sz * zeta);
                    dnat[a][1] = 0.125 * sy * (1.0 + sx * xi) * (1.0 + sz * zeta);
                    dnat[a][2] = 0.125 * sz * (1.0 + sx * xi) * (1.0 + sy * eta);
                }

                std::array<std::array<Real, 3>, 3> jac{};
                for (int a = 0; a < 8; ++a) {
                    const std::array<Real, 3> xyz{{p[a].x, p[a].y, p[a].z}};
                    for (int i = 0; i < 3; ++i) {
                        for (int j = 0; j < 3; ++j) jac[i][j] += dnat[a][i] * xyz[j];
                    }
                }

                std::array<std::array<Real, 3>, 3> inv_jac{};
                Real det_j = 0.0;
                if (!invert3x3(jac, inv_jac, det_j) || det_j <= 0.0) {
                    throw std::invalid_argument("Invalid Hex8/C3D8 geometry cannot use physical stiffness model");
                }

                std::array<std::array<Real, 24>, 6> b{};
                for (int a = 0; a < 8; ++a) {
                    std::array<Real, 3> grad{};
                    for (int j = 0; j < 3; ++j) {
                        for (int i = 0; i < 3; ++i) grad[j] += inv_jac[j][i] * dnat[a][i];
                    }
                    const int c = 3 * a;
                    b[0][c + 0] = grad[0];
                    b[1][c + 1] = grad[1];
                    b[2][c + 2] = grad[2];
                    b[3][c + 0] = grad[1];
                    b[3][c + 1] = grad[0];
                    b[4][c + 1] = grad[2];
                    b[4][c + 2] = grad[1];
                    b[5][c + 0] = grad[2];
                    b[5][c + 2] = grad[0];
                }

                for (int i = 0; i < 24; ++i) {
                    for (int j = 0; j < 24; ++j) {
                        Real v = 0.0;
                        for (int a = 0; a < 6; ++a) {
                            for (int c = 0; c < 6; ++c) v += b[a][i] * d[a][c] * b[c][j];
                        }
                        ke[static_cast<Size>(i) * 24 + j] += det_j * v;
                    }
                }
            }
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
    if (options.stiffness_model == StiffnessModel::LegacySynthetic) {
        simplified_kernel(element_id, edofs, ke);
    } else if (options.stiffness_model == StiffnessModel::PhysicsTet4) {
        physics_tet4_kernel(mesh, element_id, options, ke);
    } else if (options.stiffness_model == StiffnessModel::LinearElasticSolid && elem.type == ElementType::Hex8) {
        physics_hex8_kernel(mesh, element_id, options, ke);
    } else if (options.stiffness_model == StiffnessModel::LinearElasticSolid && elem.type == ElementType::Tet4) {
        physics_tet4_kernel(mesh, element_id, options, ke);
    } else {
        throw std::invalid_argument("Unsupported element type for stiffness model " +
                                    stiffness_model_to_string(options.stiffness_model));
    }
}

} // namespace fem
