// 这里构造 Tet4/Hex8 小型算例，也负责把 Abaqus 网格转成组装与验证使用的数据。
// 单元刚度按三维各向同性线弹性模型计算。
#include "csc3_demo_tools/evidence.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace csc3_demo::evidence {
namespace {

constexpr std::size_t kDofsPerNode = 3;
// 固定总载荷 $1000\,\mathrm{N}$ 均匀分配到 $x=1$ 端面节点，并沿 $-z$ 方向作用。
constexpr double kTotalLoadMagnitude = 1000.0;

using Matrix3 = std::array<std::array<double, 3>, 3>;
using ElasticityMatrix = std::array<std::array<double, 6>, 6>;

[[noreturn]] void throw_overflow(const char* label) {
    throw std::overflow_error(std::string(label) + " exceeds representable capacity");
}

std::size_t checked_multiply(std::size_t left, std::size_t right, const char* label) {
    if (left != 0 && right > std::numeric_limits<std::size_t>::max() / left) {
        throw_overflow(label);
    }
    return left * right;
}

Offset size_to_offset(std::size_t value, const char* label) {
    if constexpr (std::numeric_limits<std::size_t>::digits > std::numeric_limits<Offset>::digits) {
        if (value > static_cast<std::size_t>(std::numeric_limits<Offset>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<Offset>(value);
}

std::size_t offset_to_size(Offset value, const char* label) {
    if constexpr (std::numeric_limits<Offset>::digits > std::numeric_limits<std::size_t>::digits) {
        if (value > static_cast<Offset>(std::numeric_limits<std::size_t>::max())) {
            throw_overflow(label);
        }
    }
    return static_cast<std::size_t>(value);
}

GlobalDofIndex size_to_dof(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<GlobalDofIndex>::max())) {
        throw_overflow(label);
    }
    return static_cast<GlobalDofIndex>(value);
}

ElementId size_to_element_id(std::size_t value) {
    if (value > static_cast<std::size_t>(std::numeric_limits<ElementId>::max())) {
        throw_overflow("element identifier");
    }
    return static_cast<ElementId>(value);
}

double determinant(const Matrix3& matrix) {
    return matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1]) -
           matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0]) +
           matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0]);
}

double determinant_tolerance(const Matrix3& matrix) {
    // 容差随 Jacobian 最大分量的三次方缩放，与三维行列式的量纲一致；64 倍机器精度
    // 用于拒绝退化或翻转单元，而不是把几何误差静默带入刚度矩阵。
    double scale = 0.0;
    for (const auto& row : matrix) {
        for (const double value : row) {
            scale = std::max(scale, std::abs(value));
        }
    }
    return 64.0 * std::numeric_limits<double>::epsilon() * scale * scale * scale;
}

Matrix3 inverse(const Matrix3& matrix, double determinant_value) {
    Matrix3 result{};
    result[0][0] = (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1]) / determinant_value;
    result[0][1] = (matrix[0][2] * matrix[2][1] - matrix[0][1] * matrix[2][2]) / determinant_value;
    result[0][2] = (matrix[0][1] * matrix[1][2] - matrix[0][2] * matrix[1][1]) / determinant_value;
    result[1][0] = (matrix[1][2] * matrix[2][0] - matrix[1][0] * matrix[2][2]) / determinant_value;
    result[1][1] = (matrix[0][0] * matrix[2][2] - matrix[0][2] * matrix[2][0]) / determinant_value;
    result[1][2] = (matrix[0][2] * matrix[1][0] - matrix[0][0] * matrix[1][2]) / determinant_value;
    result[2][0] = (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0]) / determinant_value;
    result[2][1] = (matrix[0][1] * matrix[2][0] - matrix[0][0] * matrix[2][1]) / determinant_value;
    result[2][2] = (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) / determinant_value;
    return result;
}

ElasticityMatrix make_elasticity_matrix(double young_modulus, double poisson_ratio) {
    if (!std::isfinite(young_modulus) || young_modulus <= 0.0) {
        throw std::invalid_argument("young_modulus must be finite and positive");
    }
    if (!std::isfinite(poisson_ratio) || poisson_ratio <= -1.0 || poisson_ratio >= 0.5) {
        throw std::invalid_argument(
            "poisson_ratio must be finite and lie strictly between -1 and 0.5");
    }

    // 三维各向同性线弹性本构，采用工程剪应变 Voigt 次序
    // $(\varepsilon_{xx},\varepsilon_{yy},\varepsilon_{zz},\gamma_{xy},\gamma_{yz},\gamma_{xz})$。
    // Lamé 常数为 $\lambda=E\nu/((1+\nu)(1-2\nu))$、$\mu=E/(2(1+\nu))$。
    const double lambda =
        young_modulus * poisson_ratio / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio));
    const double mu = young_modulus / (2.0 * (1.0 + poisson_ratio));
    if (!std::isfinite(lambda) || !std::isfinite(mu)) {
        throw std::invalid_argument("material constants must remain finite");
    }

    ElasticityMatrix result{};
    for (std::size_t row = 0; row < 3; ++row) {
        for (std::size_t column = 0; column < 3; ++column) {
            result[row][column] = lambda;
        }
        result[row][row] = lambda + 2.0 * mu;
    }
    result[3][3] = mu;
    result[4][4] = mu;
    result[5][5] = mu;
    return result;
}

template <std::size_t NodeCount> using Gradients = std::array<std::array<double, 3>, NodeCount>;

template <std::size_t NodeCount>
using StrainDisplacementMatrix = std::array<std::array<double, kDofsPerNode * NodeCount>, 6>;

template <std::size_t NodeCount>
StrainDisplacementMatrix<NodeCount>
make_strain_displacement_matrix(const Gradients<NodeCount>& gradients) {
    // 由物理坐标下的形函数梯度构造 $B$ 矩阵；每个节点的三列依次对应
    // $(u_x,u_y,u_z)$，行次序必须与 make_elasticity_matrix() 的 Voigt 约定一致。
    StrainDisplacementMatrix<NodeCount> result{};
    for (std::size_t node = 0; node < NodeCount; ++node) {
        const double dx = gradients[node][0];
        const double dy = gradients[node][1];
        const double dz = gradients[node][2];
        const std::size_t column = kDofsPerNode * node;
        result[0][column] = dx;
        result[1][column + 1] = dy;
        result[2][column + 2] = dz;
        result[3][column] = dy;
        result[3][column + 1] = dx;
        result[4][column + 1] = dz;
        result[4][column + 2] = dy;
        result[5][column] = dz;
        result[5][column + 2] = dx;
    }
    return result;
}

template <std::size_t NodeCount>
void accumulate_stiffness(const StrainDisplacementMatrix<NodeCount>& b,
                          const ElasticityMatrix& elasticity, double integration_weight,
                          std::vector<double>& stiffness) {
    // 在当前积分点累加 $K_e \mathrel{+}= B^T D B\,w$。只计算局部上三角，再显式镜像
    // 到下三角，使输出满足数值组装接口要求的完整、对称、行主序矩阵契约。
    constexpr std::size_t local_dimension = kDofsPerNode * NodeCount;
    for (std::size_t row = 0; row < local_dimension; ++row) {
        for (std::size_t column = row; column < local_dimension; ++column) {
            double value = 0.0;
            for (std::size_t strain_row = 0; strain_row < 6; ++strain_row) {
                for (std::size_t strain_column = 0; strain_column < 6; ++strain_column) {
                    value += b[strain_row][row] * elasticity[strain_row][strain_column] *
                             b[strain_column][column];
                }
            }
            value *= integration_weight;
            if (!std::isfinite(value)) {
                throw std::invalid_argument("element stiffness contains a nonfinite value");
            }
            stiffness[row * local_dimension + column] += value;
            if (row != column) {
                stiffness[column * local_dimension + row] += value;
            }
        }
    }
}

template <std::size_t NodeCount>
Gradients<NodeCount>
transform_gradients(const std::array<std::array<double, 3>, NodeCount>& natural_gradients,
                    const Matrix3& inverse_jacobian) {
    // 将自然坐标梯度映射到物理坐标。这里的 Jacobian 存储约定与下方 Tet4/Hex8
    // 构造保持一致，调用方必须传入同一约定下的逆矩阵。
    Gradients<NodeCount> result{};
    for (std::size_t node = 0; node < NodeCount; ++node) {
        for (std::size_t physical = 0; physical < 3; ++physical) {
            for (std::size_t natural = 0; natural < 3; ++natural) {
                result[node][physical] +=
                    inverse_jacobian[physical][natural] * natural_gradients[node][natural];
            }
        }
    }
    return result;
}

std::vector<double> tet4_stiffness(const std::array<Node, 4>& nodes,
                                   const ElasticityMatrix& elasticity) {
    // 线性四面体的形函数梯度在单元内为常量，因此单点解析积分即可：
    // $K_e=B^T D B\,V$，其中 $V=\det(J)/6$。正行列式同时固定节点方向。
    Matrix3 jacobian{{
        {{nodes[1].x - nodes[0].x, nodes[1].y - nodes[0].y, nodes[1].z - nodes[0].z}},
        {{nodes[2].x - nodes[0].x, nodes[2].y - nodes[0].y, nodes[2].z - nodes[0].z}},
        {{nodes[3].x - nodes[0].x, nodes[3].y - nodes[0].y, nodes[3].z - nodes[0].z}},
    }};
    const double determinant_value = determinant(jacobian);
    if (!std::isfinite(determinant_value) || determinant_value <= determinant_tolerance(jacobian)) {
        throw std::invalid_argument("Tet4 geometry is degenerate or inverted");
    }

    static constexpr std::array<std::array<double, 3>, 4> natural_gradients{{
        {{-1.0, -1.0, -1.0}},
        {{1.0, 0.0, 0.0}},
        {{0.0, 1.0, 0.0}},
        {{0.0, 0.0, 1.0}},
    }};
    const Gradients<4> gradients =
        transform_gradients(natural_gradients, inverse(jacobian, determinant_value));
    const auto b = make_strain_displacement_matrix(gradients);
    std::vector<double> stiffness(12 * 12, 0.0);
    accumulate_stiffness<4>(b, elasticity, determinant_value / 6.0, stiffness);
    return stiffness;
}

std::vector<double> hex8_stiffness(const std::array<Node, 8>& nodes,
                                   const ElasticityMatrix& elasticity) {
    // 三线性 Hex8 使用 $2\times2\times2$ Gauss 积分，八个积分点的权重均为 1。
    // 每个积分点重新计算 $J$、$\det(J)$、物理梯度与 $B$，随后累加
    // $K_e \mathrel{+}= B^T D B\det(J)$。
    static constexpr std::array<std::array<double, 3>, 8> natural_nodes{{
        {{-1.0, -1.0, -1.0}},
        {{1.0, -1.0, -1.0}},
        {{1.0, 1.0, -1.0}},
        {{-1.0, 1.0, -1.0}},
        {{-1.0, -1.0, 1.0}},
        {{1.0, -1.0, 1.0}},
        {{1.0, 1.0, 1.0}},
        {{-1.0, 1.0, 1.0}},
    }};
    const double gauss_coordinate = 1.0 / std::sqrt(3.0);
    const std::array<double, 2> gauss_points{{
        -gauss_coordinate,
        gauss_coordinate,
    }};

    std::vector<double> stiffness(24 * 24, 0.0);
    for (const double xi : gauss_points) {
        for (const double eta : gauss_points) {
            for (const double zeta : gauss_points) {
                std::array<std::array<double, 3>, 8> natural_gradients{};
                for (std::size_t node = 0; node < natural_nodes.size(); ++node) {
                    const double sign_x = natural_nodes[node][0];
                    const double sign_y = natural_nodes[node][1];
                    const double sign_z = natural_nodes[node][2];
                    natural_gradients[node][0] =
                        0.125 * sign_x * (1.0 + sign_y * eta) * (1.0 + sign_z * zeta);
                    natural_gradients[node][1] =
                        0.125 * sign_y * (1.0 + sign_x * xi) * (1.0 + sign_z * zeta);
                    natural_gradients[node][2] =
                        0.125 * sign_z * (1.0 + sign_x * xi) * (1.0 + sign_y * eta);
                }

                Matrix3 jacobian{};
                for (std::size_t node = 0; node < nodes.size(); ++node) {
                    const std::array<double, 3> coordinates{{
                        nodes[node].x,
                        nodes[node].y,
                        nodes[node].z,
                    }};
                    for (std::size_t natural = 0; natural < 3; ++natural) {
                        for (std::size_t physical = 0; physical < 3; ++physical) {
                            jacobian[natural][physical] +=
                                natural_gradients[node][natural] * coordinates[physical];
                        }
                    }
                }

                const double determinant_value = determinant(jacobian);
                if (!std::isfinite(determinant_value) ||
                    determinant_value <= determinant_tolerance(jacobian)) {
                    throw std::invalid_argument("Hex8 geometry is degenerate or inverted");
                }
                const Gradients<8> gradients =
                    transform_gradients(natural_gradients, inverse(jacobian, determinant_value));
                const auto b = make_strain_displacement_matrix(gradients);
                accumulate_stiffness<8>(b, elasticity, determinant_value, stiffness);
            }
        }
    }
    return stiffness;
}

std::size_t structured_node_id(int i, int j, int k, int nx, int ny) {
    return (static_cast<std::size_t>(k) * (static_cast<std::size_t>(ny) + 1) +
            static_cast<std::size_t>(j)) *
               (static_cast<std::size_t>(nx) + 1) +
           static_cast<std::size_t>(i);
}

template <std::size_t NodeCount>
void append_element(AssemblyCase& assembly_case,
                    const std::array<std::size_t, NodeCount>& node_indices,
                    const ElasticityMatrix& elasticity, ElementId element_id) {
    // 全局自由度采用节点主序：node 的三个分量映射为
    // $(3\,node,3\,node+1,3\,node+2)$。拓扑与矩阵偏移同步追加，保证第 $e$ 个矩阵
    // 分段对应规范次序中的第 $e$ 个单元。
    assembly_case.element_dof_map.element_ids.push_back(element_id);
    for (const std::size_t node : node_indices) {
        for (std::size_t component = 0; component < kDofsPerNode; ++component) {
            assembly_case.element_dof_map.global_dof_indices.push_back(
                size_to_dof(kDofsPerNode * node + component, "global DOF index"));
        }
    }
    assembly_case.element_dof_map.element_dof_offsets.push_back(size_to_offset(
        assembly_case.element_dof_map.global_dof_indices.size(), "element DOF offset"));

    std::array<Node, NodeCount> element_nodes{};
    for (std::size_t local_node = 0; local_node < NodeCount; ++local_node) {
        element_nodes[local_node] = assembly_case.nodes[node_indices[local_node]];
    }
    std::vector<double> stiffness;
    if constexpr (NodeCount == 4) {
        stiffness = tet4_stiffness(element_nodes, elasticity);
    } else {
        static_assert(NodeCount == 8, "only Tet4 and Hex8 are supported");
        stiffness = hex8_stiffness(element_nodes, elasticity);
    }
    assembly_case.element_matrices.values_row_major.insert(
        assembly_case.element_matrices.values_row_major.end(), stiffness.begin(), stiffness.end());
    assembly_case.element_matrices.element_value_offsets.push_back(size_to_offset(
        assembly_case.element_matrices.values_row_major.size(), "element matrix offset"));
}

template <std::size_t NodeCount>
void append_generated_element(AssemblyCase& assembly_case,
                              const std::array<std::size_t, NodeCount>& node_indices,
                              const ElasticityMatrix& elasticity) {
    const std::size_t element_ordinal = assembly_case.element_dof_map.element_ids.size();
    append_element(assembly_case, node_indices, elasticity, size_to_element_id(element_ordinal));
}

} // namespace

AssemblyCase make_cube_case(ElementType element_type, int nx, int ny, int nz, double young_modulus,
                            double poisson_ratio) {
    if (nx <= 0 || ny <= 0 || nz <= 0) {
        throw std::invalid_argument("cube grid dimensions must be positive");
    }
    const ElasticityMatrix elasticity = make_elasticity_matrix(young_modulus, poisson_ratio);

    const std::size_t node_count =
        checked_multiply(checked_multiply(static_cast<std::size_t>(nx) + 1,
                                          static_cast<std::size_t>(ny) + 1, "cube node count"),
                         static_cast<std::size_t>(nz) + 1, "cube node count");
    const std::size_t global_dimension =
        checked_multiply(node_count, kDofsPerNode, "global dimension");
    static_cast<void>(size_to_dof(global_dimension - 1, "global dimension"));

    const std::size_t cell_count =
        checked_multiply(checked_multiply(static_cast<std::size_t>(nx),
                                          static_cast<std::size_t>(ny), "cube cell count"),
                         static_cast<std::size_t>(nz), "cube cell count");
    const std::size_t element_count =
        element_type == ElementType::Tet4
            ? checked_multiply(cell_count, std::size_t{6}, "Tet4 element count")
            : cell_count;
    static_cast<void>(size_to_element_id(element_count - 1));

    AssemblyCase result;
    result.name = std::string("cube_") + (element_type == ElementType::Tet4 ? "tet4_" : "hex8_") +
                  std::to_string(nx) + "x" + std::to_string(ny) + "x" + std::to_string(nz);
    result.element_type = element_type;
    result.nodes.reserve(node_count);
    for (int k = 0; k <= nz; ++k) {
        for (int j = 0; j <= ny; ++j) {
            for (int i = 0; i <= nx; ++i) {
                result.nodes.push_back(Node{
                    static_cast<double>(i) / static_cast<double>(nx),
                    static_cast<double>(j) / static_cast<double>(ny),
                    static_cast<double>(k) / static_cast<double>(nz),
                });
            }
        }
    }

    result.element_dof_map.element_ids.reserve(element_count);
    result.element_dof_map.element_dof_offsets.reserve(element_count + 1);
    result.element_matrices.element_value_offsets.reserve(element_count + 1);
    result.element_dof_map.element_dof_offsets.push_back(0);
    result.element_matrices.element_value_offsets.push_back(0);

    // 结构化单元按 $k\rightarrow j\rightarrow i$ 的稳定次序生成。Tet4 路径把每个
    // 六面体胞元沿共同体对角线拆成六个非退化四面体；Hex8 路径保留一个八节点单元。
    for (int k = 0; k < nz; ++k) {
        for (int j = 0; j < ny; ++j) {
            for (int i = 0; i < nx; ++i) {
                const std::size_t n000 = structured_node_id(i, j, k, nx, ny);
                const std::size_t n100 = structured_node_id(i + 1, j, k, nx, ny);
                const std::size_t n010 = structured_node_id(i, j + 1, k, nx, ny);
                const std::size_t n110 = structured_node_id(i + 1, j + 1, k, nx, ny);
                const std::size_t n001 = structured_node_id(i, j, k + 1, nx, ny);
                const std::size_t n101 = structured_node_id(i + 1, j, k + 1, nx, ny);
                const std::size_t n011 = structured_node_id(i, j + 1, k + 1, nx, ny);
                const std::size_t n111 = structured_node_id(i + 1, j + 1, k + 1, nx, ny);

                if (element_type == ElementType::Tet4) {
                    // 与 CPU 主项目的立方体生成器采用同一组六四面体连接关系。
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n100, n110, n111}}, elasticity);
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n110, n010, n111}}, elasticity);
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n010, n011, n111}}, elasticity);
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n011, n001, n111}}, elasticity);
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n001, n101, n111}}, elasticity);
                    append_generated_element(
                        result, std::array<std::size_t, 4>{{n000, n101, n100, n111}}, elasticity);
                } else {
                    append_generated_element(result,
                                             std::array<std::size_t, 8>{{
                                                 n000,
                                                 n100,
                                                 n110,
                                                 n010,
                                                 n001,
                                                 n101,
                                                 n111,
                                                 n011,
                                             }},
                                             elasticity);
                }
            }
        }
    }

    // 构造悬臂式小型求解夹具：$x=0$ 面三个平移自由度全约束；$x=1$ 面节点
    // 平分总载荷，因而网格细化不会改变合力。约束最终排序去重以满足求解器前置条件。
    result.force.assign(global_dimension, 0.0);
    const std::size_t loaded_node_count =
        checked_multiply(static_cast<std::size_t>(ny) + 1, static_cast<std::size_t>(nz) + 1,
                         "loaded face node count");
    const double nodal_load = -kTotalLoadMagnitude / static_cast<double>(loaded_node_count);
    for (int k = 0; k <= nz; ++k) {
        for (int j = 0; j <= ny; ++j) {
            const std::size_t loaded_node = structured_node_id(nx, j, k, nx, ny);
            result.force[kDofsPerNode * loaded_node + 2] = nodal_load;

            const std::size_t constrained_node = structured_node_id(0, j, k, nx, ny);
            for (std::size_t component = 0; component < kDofsPerNode; ++component) {
                result.constrained_dof_indices.push_back(size_to_dof(
                    kDofsPerNode * constrained_node + component, "constrained DOF index"));
            }
        }
    }
    std::sort(result.constrained_dof_indices.begin(), result.constrained_dof_indices.end());
    result.constrained_dof_indices.erase(
        std::unique(result.constrained_dof_indices.begin(), result.constrained_dof_indices.end()),
        result.constrained_dof_indices.end());
    return result;
}

AssemblyCase make_assembly_case(ParsedMesh parsed_mesh, double young_modulus,
                                double poisson_ratio) {
    const std::size_t nodes_per_element = parsed_mesh.element_type == ElementType::Tet4   ? 4
                                          : parsed_mesh.element_type == ElementType::Hex8 ? 8
                                                                                          : 0;
    if (nodes_per_element == 0) {
        throw std::invalid_argument("parsed mesh has an invalid element type");
    }
    if (parsed_mesh.nodes.empty() || parsed_mesh.external_element_ids.empty()) {
        throw std::invalid_argument("parsed mesh is empty");
    }
    if (parsed_mesh.element_node_offsets.size() != parsed_mesh.external_element_ids.size() + 1) {
        throw std::invalid_argument("parsed mesh element offsets are inconsistent");
    }
    if (parsed_mesh.element_node_offsets.front() != 0) {
        throw std::invalid_argument("parsed mesh element offsets must begin at zero");
    }
    const std::size_t global_dimension =
        checked_multiply(parsed_mesh.nodes.size(), kDofsPerNode, "global dimension");
    static_cast<void>(size_to_dof(global_dimension - 1, "global dimension"));
    for (const Node& node : parsed_mesh.nodes) {
        if (!std::isfinite(node.x) || !std::isfinite(node.y) || !std::isfinite(node.z)) {
            throw std::invalid_argument("parsed mesh contains a nonfinite coordinate");
        }
    }

    // 外部 Abaqus 单元编号可无序但必须为正且唯一。先验证 connectivity，再按外部编号
    // 升序构造交付 API 所需的规范单元次序；节点编号已由解析器压缩为零基连续索引。
    std::vector<std::size_t> canonical_order(parsed_mesh.external_element_ids.size());
    for (std::size_t index = 0; index < canonical_order.size(); ++index) {
        canonical_order[index] = index;
        if (parsed_mesh.external_element_ids[index] <= 0) {
            throw std::invalid_argument("parsed mesh element identifiers must be positive");
        }
        const std::size_t begin =
            offset_to_size(parsed_mesh.element_node_offsets[index], "element node offset");
        const std::size_t end =
            offset_to_size(parsed_mesh.element_node_offsets[index + 1], "element node offset");
        if (begin > end || end > parsed_mesh.compact_node_indices.size() ||
            end - begin != nodes_per_element) {
            throw std::invalid_argument("parsed mesh element connectivity is inconsistent");
        }
        for (std::size_t position = begin; position < end; ++position) {
            if (parsed_mesh.compact_node_indices[position] >= parsed_mesh.nodes.size()) {
                throw std::invalid_argument("parsed mesh element references an out-of-range node");
            }
        }
    }
    if (offset_to_size(parsed_mesh.element_node_offsets.back(), "element node offset") !=
        parsed_mesh.compact_node_indices.size()) {
        throw std::invalid_argument("parsed mesh terminal element offset is inconsistent");
    }
    std::sort(canonical_order.begin(), canonical_order.end(),
              [&parsed_mesh](std::size_t left, std::size_t right) {
                  return parsed_mesh.external_element_ids[left] <
                         parsed_mesh.external_element_ids[right];
              });
    for (std::size_t index = 1; index < canonical_order.size(); ++index) {
        if (parsed_mesh.external_element_ids[canonical_order[index - 1]] ==
            parsed_mesh.external_element_ids[canonical_order[index]]) {
            throw std::invalid_argument("parsed mesh contains duplicate element identifiers");
        }
    }

    const ElasticityMatrix elasticity = make_elasticity_matrix(young_modulus, poisson_ratio);
    const std::size_t local_dimension =
        checked_multiply(nodes_per_element, kDofsPerNode, "local element dimension");
    const std::size_t total_dof_entries =
        checked_multiply(canonical_order.size(), local_dimension, "element DOF entries");
    const std::size_t values_per_element =
        checked_multiply(local_dimension, local_dimension, "element matrix value count");
    const std::size_t total_matrix_values =
        checked_multiply(canonical_order.size(), values_per_element, "element matrix value count");
    static_cast<void>(size_to_offset(total_dof_entries, "element DOF offset"));
    static_cast<void>(size_to_offset(total_matrix_values, "element matrix offset"));
    AssemblyCase result;
    result.name = std::move(parsed_mesh.name);
    result.element_type = parsed_mesh.element_type;
    result.nodes = std::move(parsed_mesh.nodes);
    result.element_dof_map.element_ids.reserve(canonical_order.size());
    result.element_dof_map.element_dof_offsets.reserve(canonical_order.size() + 1);
    result.element_dof_map.global_dof_indices.reserve(total_dof_entries);
    result.element_matrices.element_value_offsets.reserve(canonical_order.size() + 1);
    result.element_matrices.values_row_major.reserve(total_matrix_values);
    result.element_dof_map.element_dof_offsets.push_back(0);
    result.element_matrices.element_value_offsets.push_back(0);

    for (const std::size_t original_index : canonical_order) {
        const std::size_t begin =
            offset_to_size(parsed_mesh.element_node_offsets[original_index], "element node offset");
        if (result.element_type == ElementType::Tet4) {
            std::array<std::size_t, 4> node_indices{};
            for (std::size_t local_node = 0; local_node < node_indices.size(); ++local_node) {
                node_indices[local_node] = parsed_mesh.compact_node_indices[begin + local_node];
            }
            append_element(result, node_indices, elasticity,
                           parsed_mesh.external_element_ids[original_index]);
        } else {
            std::array<std::size_t, 8> node_indices{};
            for (std::size_t local_node = 0; local_node < node_indices.size(); ++local_node) {
                node_indices[local_node] = parsed_mesh.compact_node_indices[begin + local_node];
            }
            append_element(result, node_indices, elasticity,
                           parsed_mesh.external_element_ids[original_index]);
        }
    }
    result.force.assign(global_dimension, 0.0);
    return result;
}

AssemblyCase load_abaqus_case(const std::filesystem::path& path, double young_modulus,
                              double poisson_ratio) {
    return make_assembly_case(parse_abaqus_inp(path), young_modulus, poisson_ratio);
}

} // namespace csc3_demo::evidence
