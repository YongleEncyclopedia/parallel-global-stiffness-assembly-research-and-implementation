// benchmark 和正确性测试共用的算例数据放在这里。
// 这些类型属于测试工具。
#pragma once

#include "csc3_demo/assembly_helper.h"

#include <cstddef>
#include <filesystem>
#include <limits>
#include <string>
#include <vector>

namespace csc3_demo::evidence {

// 测试工具使用的紧凑数组。它们不属于交付给研发调用的公共接口。
using GlobalDofIndex = Index;
using Offset = std::uint64_t;

struct FlatDofTopology {
    // 三个数组共同表示“单元 -> 全局自由度”。第 e 个单元使用
    // [element_dof_offsets[e], element_dof_offsets[e + 1]) 这一段自由度。
    std::vector<ElementId> element_ids;
    std::vector<Offset> element_dof_offsets;
    std::vector<GlobalDofIndex> global_dof_indices;
};

struct ElementMatrixBatch {
    // 单元矩阵按 element_ids 的顺序连续存放，每个矩阵采用行优先布局。
    // offsets 同样带末端偏移，因此可以直接取得任意一个单元矩阵的范围。
    std::vector<Offset> element_value_offsets;
    std::vector<double> values_row_major;
};

/// 比较无法计算时写入 JSON/CSV 的有限哨兵值，避免输出非标准 `NaN`/`Infinity`。
inline constexpr double kComparisonFailureError = std::numeric_limits<double>::max();
/// 正式性能证据的固定预热次数 $W$。
inline constexpr int kFormalWarmupCount = 2;
/// 正式性能证据的固定测量重复次数 $R$。
inline constexpr int kFormalRepeatCount = 7;
/// 正式口径中符号成本的摊销次数 $m$。
inline constexpr int kFormalAmortizationCount = 1;

/// 内部生成证据算例可使用的单元形式。
enum class ElementType {
    Tet4,
    Hex8,
};

struct Node {
    /// 物理坐标，生成式夹具使用 SI 长度单位。
    double x = 0.0;
    double y = 0.0;
    double z = 0.0;
};

/// 从 Abaqus 输入文件解析得到的扁平、紧凑、零基网格。
struct ParsedMesh {
    std::string name;
    ElementType element_type = ElementType::Tet4;
    std::vector<Node> nodes;
    /// 按输入次序保存的外部 Abaqus 编号。
    std::vector<ElementId> external_element_ids;
    /// 指向 compact_node_indices 的零基偏移，并包含一个末端偏移。
    std::vector<Offset> element_node_offsets;
    /// 按各单元局部次序保存的紧凑零基节点索引。
    std::vector<std::size_t> compact_node_indices;
};

/// 用于矩阵组装和约束位移求解的内部有限元夹具。
///
/// 每个节点具有三个平移自由度，编号顺序为 $(u_x,u_y,u_z)$。`force` 与全局自由度
/// 一一对应，`constrained_dof_indices` 必须升序且无重复；当前夹具施加零位移约束。
struct AssemblyCase {
    std::string name;
    ElementType element_type = ElementType::Tet4;
    std::vector<Node> nodes;
    // 拓扑和单元矩阵必须采用相同的单元顺序。
    FlatDofTopology element_dof_map;
    ElementMatrixBatch element_matrices;
    // force 的长度等于全局自由度数；当前只支持零位移约束。
    std::vector<double> force;
    std::vector<GlobalDofIndex> constrained_dof_indices;
};

/// 独立串行参考结果：上三角结构用于严格结构比较，完整稠密矩阵用于误差与求解。
/// 该结果不复用候选 `HelpInfo` 或 scatter 数据，避免同源错误相互抵消。
struct SerialAssemblyResult {
    GlobalDofIndex dimension = 0;
    std::vector<Offset> column_offsets;
    std::vector<GlobalDofIndex> row_indices;
    std::vector<double> dense_values;
};

struct MatrixComparison {
    // 先比较 CSC3 的列偏移和行号，再比较对应的数值。
    bool structure_matches = false;
    /// $e_F=\lVert K_p-K_s\rVert_F/\max(\lVert K_s\rVert_F,10^{-30})$。
    double relative_frobenius_error = 0.0;
    /// $e_{max}=\max_{i,j}|(K_p-K_s)_{ij}|$。
    double max_absolute_error = 0.0;
    double reference_max_absolute_value = 0.0;
    double max_absolute_tolerance = 0.0;
    bool passed = false;
};

struct DisplacementComparison {
    /// $e_u=\lVert u_p-u_s\rVert_2/\max(\lVert u_s\rVert_2,10^{-30})$。
    double relative_displacement_error = 0.0;
    /// 并行矩阵对应自由系统的相对残差。
    double parallel_relative_residual = 0.0;
    /// 串行参考矩阵对应自由系统的相对残差。
    double serial_relative_residual = 0.0;
    // 两个范数保留下来，便于检查相对误差是否受接近零的参考量影响。
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

/// 生成单位立方体 Tet4/Hex8 夹具：$x=0$ 面固支，$x=1$ 面施加总计 $-1000\,\mathrm{N}$ 的 $z$
/// 向载荷。
AssemblyCase make_cube_case(ElementType element_type, int nx, int ny, int nz,
                            double young_modulus = 2.1e11, double poisson_ratio = 0.3);

ParsedMesh parse_abaqus_inp(const std::filesystem::path& path);

AssemblyCase make_assembly_case(ParsedMesh parsed_mesh, double young_modulus = 2.1e11,
                                double poisson_ratio = 0.3);

AssemblyCase load_abaqus_case(const std::filesystem::path& path, double young_modulus = 2.1e11,
                              double poisson_ratio = 0.3);

// 将测试工具的紧凑拓扑还原为研发接口要求的“单元—节点—自由度”两级映射。
DofCodingInfo make_dof_coding_info(const AssemblyCase& assembly_case);

/// 使用独立拓扑搜索和稠密累加构造串行参考，不调用候选组装器。
SerialAssemblyResult assemble_serial_reference(const AssemblyCase& assembly_case);

/// 比较结构、$e_F$ 与 $e_{max}$；完整对称矩阵的上下三角均计入 Frobenius 范数。
MatrixComparison compare_matrices(const Csc3Matrix& candidate,
                                  const SerialAssemblyResult& reference);

/// 完成候选/串行组装、约束系统求解、位移误差和双方残差检查。
ValidationResult validate_case(const AssemblyCase& assembly_case, int thread_count);

} // namespace csc3_demo::evidence
