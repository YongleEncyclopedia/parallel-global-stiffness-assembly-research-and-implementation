#include "csc3_demo/assembly_helper.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace csc3_demo {
namespace {

constexpr double kSymmetryTolerance = 1.0e-10;

std::vector<ElementId> sorted_element_ids(const DofCodingInfo& info) {
    std::vector<ElementId> ids;
    ids.reserve(info.elems.size());
    for (const auto& item : info.elems) ids.push_back(item.first);
    std::sort(ids.begin(), ids.end());
    return ids;
}

std::vector<Index> collect_checked_global_dofs(const DofCodingInfo& info) {
    std::vector<Index> dofs;
    for (const auto& item : info.node_dofs) {
        if (item.second.empty()) {
            throw std::invalid_argument("node_dofs contains an empty DOF list");
        }
        dofs.insert(dofs.end(), item.second.begin(), item.second.end());
    }
    for (Index dof : dofs) {
        if (dof < 0) throw std::invalid_argument("global DOF id must be non-negative");
    }
    std::sort(dofs.begin(), dofs.end());
    if (std::adjacent_find(dofs.begin(), dofs.end()) != dofs.end()) {
        throw std::invalid_argument("global DOF ids must be unique across node_dofs");
    }
    if (dofs.empty()) throw std::invalid_argument("node_dofs must contain at least one DOF");
    for (std::size_t i = 0; i < dofs.size(); ++i) {
        if (dofs[i] != static_cast<Index>(i)) {
            throw std::invalid_argument("global DOF ids must be contiguous 0..n-1");
        }
    }
    return dofs;
}

Index checked_index_size(std::size_t value, const char* label) {
    if (value > static_cast<std::size_t>(std::numeric_limits<Index>::max())) {
        throw std::overflow_error(std::string(label) + " exceeds 32-bit Index capacity");
    }
    return static_cast<Index>(value);
}

void validate_local_unique(const std::vector<Index>& dofs, ElementId elem_id) {
    std::vector<Index> sorted = dofs;
    std::sort(sorted.begin(), sorted.end());
    if (std::adjacent_find(sorted.begin(), sorted.end()) != sorted.end()) {
        throw std::invalid_argument("element " + std::to_string(elem_id) +
                                    " has duplicate local/global DOF ids");
    }
}

Index find_upper_position(const Csc3Matrix& matrix, Index a, Index b) {
    const Index row = std::min(a, b);
    const Index col = std::max(a, b);
    if (row < 0 || col < 0 || row >= matrix.n || col >= matrix.n) {
        throw std::out_of_range("CSC3 entry is out of matrix range");
    }
    const auto begin_index = matrix.col_ptr[static_cast<std::size_t>(col)];
    const auto end_index = matrix.col_ptr[static_cast<std::size_t>(col) + 1];
    const auto begin = matrix.row_idx.begin() + begin_index;
    const auto end = matrix.row_idx.begin() + end_index;
    const auto it = std::lower_bound(begin, end, row);
    if (it == end || *it != row) {
        throw std::runtime_error("CSC3 structure does not contain requested upper entry");
    }
    return static_cast<Index>(std::distance(matrix.row_idx.begin(), it));
}

std::size_t element_dof_count(const HelpInfo& help, std::size_t ordinal) {
    return static_cast<std::size_t>(help.element_dof_offsets[ordinal + 1] -
                                   help.element_dof_offsets[ordinal]);
}

void validate_local_matrix(const HelpInfo& help,
                           std::size_t ordinal,
                           const double* ke_row_major,
                           std::size_t size) {
    if (!ke_row_major) throw std::invalid_argument("local stiffness matrix pointer is null");
    const std::size_t edofs = element_dof_count(help, ordinal);
    if (size != edofs * edofs) {
        throw std::invalid_argument("local stiffness matrix size must be edofs * edofs");
    }
    for (std::size_t p = 0; p < size; ++p) {
        if (!std::isfinite(ke_row_major[p])) {
            throw std::invalid_argument("local stiffness matrix contains non-finite value");
        }
    }
    for (std::size_t r = 0; r < edofs; ++r) {
        for (std::size_t c = r + 1; c < edofs; ++c) {
            const double a = ke_row_major[r * edofs + c];
            const double b = ke_row_major[c * edofs + r];
            if (std::abs(a - b) > kSymmetryTolerance) {
                throw std::invalid_argument("local stiffness matrix must be symmetric");
            }
        }
    }
}

std::string vector_to_string(const std::vector<Index>& values) {
    std::ostringstream os;
    os << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) os << ", ";
        os << values[i];
    }
    os << ']';
    return os.str();
}

std::string vector_to_string(const std::vector<double>& values) {
    std::ostringstream os;
    os << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i) os << ", ";
        os << values[i];
    }
    os << ']';
    return os.str();
}

} // namespace

void AssemblyHelper::symbolic(const DofCodingInfo& info) {
    if (info.elems.empty()) throw std::invalid_argument("elems must not be empty");
    if (info.node_dofs.empty()) throw std::invalid_argument("node_dofs must not be empty");

    const auto all_dofs = collect_checked_global_dofs(info);

    matrix_ = {};
    help_info_ = {};
    element_to_ordinal_.clear();
    matrix_.n = checked_index_size(all_dofs.size(), "matrix dimension");

    std::vector<std::vector<Index>> columns(static_cast<std::size_t>(matrix_.n));
    const auto elem_ids = sorted_element_ids(info);
    help_info_.element_dof_offsets.push_back(0);
    help_info_.entry_offsets.push_back(0);

    for (ElementId elem_id : elem_ids) {
        const auto elem_it = info.elems.find(elem_id);
        if (elem_it == info.elems.end() || elem_it->second.empty()) {
            throw std::invalid_argument("element has an empty node list");
        }

        std::vector<Index> edofs;
        for (NodeId node : elem_it->second) {
            const auto node_it = info.node_dofs.find(node);
            if (node_it == info.node_dofs.end()) {
                throw std::invalid_argument("element references a node missing from node_dofs");
            }
            edofs.insert(edofs.end(), node_it->second.begin(), node_it->second.end());
        }
        if (edofs.empty()) {
            throw std::invalid_argument("element has no local DOFs");
        }
        validate_local_unique(edofs, elem_id);

        const std::size_t ordinal = help_info_.element_ids.size();
        help_info_.element_ids.push_back(elem_id);
        element_to_ordinal_[elem_id] = ordinal;
        help_info_.element_dofs.insert(help_info_.element_dofs.end(), edofs.begin(), edofs.end());
        help_info_.element_dof_offsets.push_back(checked_index_size(help_info_.element_dofs.size(),
                                                                    "element DOF offset"));

        std::size_t entry_count = 0;
        for (std::size_t i = 0; i < edofs.size(); ++i) {
            for (std::size_t j = i; j < edofs.size(); ++j) {
                const Index row = std::min(edofs[i], edofs[j]);
                const Index col = std::max(edofs[i], edofs[j]);
                columns[static_cast<std::size_t>(col)].push_back(row);
                ++entry_count;
            }
        }
        const std::size_t next_entries =
            static_cast<std::size_t>(help_info_.entry_offsets.back()) + entry_count;
        help_info_.entry_offsets.push_back(checked_index_size(next_entries, "entry offset"));
    }

    matrix_.col_ptr.assign(static_cast<std::size_t>(matrix_.n) + 1, 0);
    for (Index col = 0; col < matrix_.n; ++col) {
        auto& rows = columns[static_cast<std::size_t>(col)];
        std::sort(rows.begin(), rows.end());
        rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
        matrix_.row_idx.insert(matrix_.row_idx.end(), rows.begin(), rows.end());
        matrix_.col_ptr[static_cast<std::size_t>(col) + 1] =
            checked_index_size(matrix_.row_idx.size(), "CSC3 nonzero count");
    }
    matrix_.values.assign(matrix_.row_idx.size(), 0.0);

    help_info_.scatter.reserve(static_cast<std::size_t>(help_info_.entry_offsets.back()));
    for (std::size_t ordinal = 0; ordinal < help_info_.element_ids.size(); ++ordinal) {
        const std::size_t begin = static_cast<std::size_t>(help_info_.element_dof_offsets[ordinal]);
        const std::size_t end = static_cast<std::size_t>(help_info_.element_dof_offsets[ordinal + 1]);
        for (std::size_t i = begin; i < end; ++i) {
            for (std::size_t j = i; j < end; ++j) {
                help_info_.scatter.push_back(find_upper_position(matrix_,
                                                                 help_info_.element_dofs[i],
                                                                 help_info_.element_dofs[j]));
            }
        }
    }
}

void AssemblyHelper::zero_values() {
    std::fill(matrix_.values.begin(), matrix_.values.end(), 0.0);
}

void AssemblyHelper::add(ElementId elem_id, const double* ke_row_major, std::size_t size) {
    const auto ordinal_it = element_to_ordinal_.find(elem_id);
    if (ordinal_it == element_to_ordinal_.end()) {
        throw std::invalid_argument("element id is not present in symbolic HelpInfo");
    }
    const std::size_t ordinal = ordinal_it->second;
    validate_local_matrix(help_info_, ordinal, ke_row_major, size);

    const std::size_t edofs = element_dof_count(help_info_, ordinal);
    std::size_t scatter_pos = static_cast<std::size_t>(help_info_.entry_offsets[ordinal]);
    for (std::size_t i = 0; i < edofs; ++i) {
        for (std::size_t j = i; j < edofs; ++j) {
            const std::size_t value_index = static_cast<std::size_t>(help_info_.scatter[scatter_pos++]);
            matrix_.values[value_index] += ke_row_major[i * edofs + j];
        }
    }
}

void AssemblyHelper::add(ElementId elem_id, const std::vector<double>& ke_row_major) {
    add(elem_id, ke_row_major.data(), ke_row_major.size());
}

void AssemblyHelper::add_parallel(const std::unordered_map<ElementId, std::vector<double>>& element_matrices,
                                  int threads) {
    struct WorkItem {
        std::size_t ordinal = 0;
        const std::vector<double>* matrix = nullptr;
    };

    if (element_matrices.size() != help_info_.element_ids.size()) {
        throw std::invalid_argument("add_parallel requires one local matrix for every symbolic element");
    }
    for (const auto& item : element_matrices) {
        if (element_to_ordinal_.find(item.first) == element_to_ordinal_.end()) {
            throw std::invalid_argument("element id is not present in symbolic HelpInfo");
        }
    }

    std::vector<WorkItem> work;
    work.reserve(help_info_.element_ids.size());
    for (ElementId elem_id : help_info_.element_ids) {
        const auto ordinal_it = element_to_ordinal_.find(elem_id);
        const auto matrix_it = element_matrices.find(elem_id);
        if (matrix_it == element_matrices.end()) {
            throw std::invalid_argument("add_parallel is missing a local matrix for a symbolic element");
        }
        validate_local_matrix(help_info_,
                              ordinal_it->second,
                              matrix_it->second.data(),
                              matrix_it->second.size());
        work.push_back(WorkItem{ordinal_it->second, &matrix_it->second});
    }

    const int nth = std::max(1, threads);
#if !(defined(CSC3_DEMO_HAS_OPENMP) && defined(_OPENMP))
    (void)nth;
#endif
#if defined(CSC3_DEMO_HAS_OPENMP) && defined(_OPENMP)
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t ww = 0; ww < static_cast<std::int64_t>(work.size()); ++ww) {
        const auto& item = work[static_cast<std::size_t>(ww)];
        const std::size_t edofs = element_dof_count(help_info_, item.ordinal);
        std::size_t scatter_pos = static_cast<std::size_t>(help_info_.entry_offsets[item.ordinal]);
        const double* ke = item.matrix->data();
        for (std::size_t i = 0; i < edofs; ++i) {
            for (std::size_t j = i; j < edofs; ++j) {
                const std::size_t value_index =
                    static_cast<std::size_t>(help_info_.scatter[scatter_pos++]);
                const double value = ke[i * edofs + j];
#if defined(CSC3_DEMO_HAS_OPENMP) && defined(_OPENMP)
#pragma omp atomic update
#endif
                matrix_.values[value_index] += value;
            }
        }
    }
}

#ifdef CSC3_DEMO_HAS_EIGEN
void AssemblyHelper::add(ElementId elem_id, const Eigen::Ref<const Eigen::MatrixXd>& ke) {
    const auto ordinal_it = element_to_ordinal_.find(elem_id);
    if (ordinal_it == element_to_ordinal_.end()) {
        throw std::invalid_argument("element id is not present in symbolic HelpInfo");
    }
    const std::size_t edofs = element_dof_count(help_info_, ordinal_it->second);
    if (ke.rows() != ke.cols()) {
        throw std::invalid_argument("Eigen local stiffness matrix must be square");
    }
    if (ke.rows() != static_cast<Eigen::Index>(edofs)) {
        throw std::invalid_argument("Eigen local stiffness matrix dimension must match element DOF count");
    }
    std::vector<double> row_major(static_cast<std::size_t>(ke.rows() * ke.cols()));
    for (Eigen::Index r = 0; r < ke.rows(); ++r) {
        for (Eigen::Index c = 0; c < ke.cols(); ++c) {
            row_major[static_cast<std::size_t>(r * ke.cols() + c)] = ke(r, c);
        }
    }
    add(elem_id, row_major);
}
#endif

const Csc3Matrix& AssemblyHelper::matrix() const {
    return matrix_;
}

const HelpInfo& AssemblyHelper::help_info() const {
    return help_info_;
}

std::vector<double> expand_upper_csc_to_dense(const Csc3Matrix& matrix) {
    if (matrix.col_ptr.size() != static_cast<std::size_t>(matrix.n) + 1) {
        throw std::invalid_argument("invalid CSC3 col_ptr length");
    }
    std::vector<double> dense(static_cast<std::size_t>(matrix.n) *
                                  static_cast<std::size_t>(matrix.n),
                              0.0);
    for (Index col = 0; col < matrix.n; ++col) {
        const Index begin = matrix.col_ptr[static_cast<std::size_t>(col)];
        const Index end = matrix.col_ptr[static_cast<std::size_t>(col) + 1];
        for (Index p = begin; p < end; ++p) {
            const Index row = matrix.row_idx[static_cast<std::size_t>(p)];
            const double value = matrix.values[static_cast<std::size_t>(p)];
            dense[static_cast<std::size_t>(row) * matrix.n + col] = value;
            dense[static_cast<std::size_t>(col) * matrix.n + row] = value;
        }
    }
    return dense;
}

std::string generate_demo_report() {
    DofCodingInfo info{
        {{10, {0, 1}}, {20, {1, 2}}},
        {{0, {0}}, {1, {1}}, {2, {2}}}
    };

    AssemblyHelper helper;
    helper.symbolic(info);
    helper.add_parallel({
        {10, {2.0, -1.0, -1.0, 2.0}},
        {20, {3.0, -2.0, -2.0, 3.0}}
    }, 4);

    const auto& matrix = helper.matrix();
    std::ostringstream os;
    os << "# CSC3 对称刚度矩阵组装 Demo 测试报告\n\n";
    os << "## 算法介绍\n\n";
    os << "本 demo 将整体刚度矩阵组装拆成两个阶段：符号组装先根据 `DofCodingInfo` "
          "生成上三角 CSC3 稀疏结构和 `HelpInfo::scatter` 写入地址；数值组装对 symbolic 阶段所有元素的单刚完整并行装配，"
          "把显式给定的单元刚度矩阵通过 atomic add 累加到 `values` 数组。\n\n";
    os << "CSC3 采用 0-based 三数组：`col_ptr` 记录每列起止位置，`row_idx` 记录行号，"
          "`values` 记录数值。本 demo 只存上三角，因此所有结构项满足 `row <= col`。\n\n";
    os << "## 输入格式\n\n";
    os << "- `elems[element_id] = {node0, node1, ...}` 表示单元节点拓扑和局部节点顺序。\n";
    os << "- `node_dofs[node_id] = {global_dof0, ...}` 表示节点自由度到全局自由度编号的映射。\n";
    os << "- 全局自由度编号要求全局唯一且连续紧凑，即 `0..n-1`。\n";
    os << "- `add_parallel()` 要求提供 symbolic 阶段所有元素的单刚；缺失单刚、未知 element id、NaN/Inf 单刚和非对称单刚都会被拒绝。\n\n";
    os << "## 测试案例：二单元一维链\n\n";
    os << "- 单元 10 连接节点 0-1，单刚为 `[[2, -1], [-1, 2]]`。\n";
    os << "- 单元 20 连接节点 1-2，单刚为 `[[3, -2], [-2, 3]]`。\n";
    os << "- OpenMP atomic enabled: " << (openmp_enabled() ? "yes" : "no") << "\n\n";
    os << "输出 CSC3 数组：\n\n";
    os << "```text\n";
    os << "n       = " << matrix.n << "\n";
    os << "col_ptr = " << vector_to_string(matrix.col_ptr) << "\n";
    os << "row_idx = " << vector_to_string(matrix.row_idx) << "\n";
    os << "values  = " << vector_to_string(matrix.values) << "\n";
    os << "```\n\n";
    os << "验证结论：该结果对应完整对称矩阵 `[[2, -1, 0], [-1, 5, -2], [0, -2, 3]]`，"
          "与手算整体刚度矩阵一致。\n";
    os << "\n## 测试覆盖\n\n";
    os << "- `Chain1DUpperCsc3`：验证上三角 CSC3 的 `col_ptr / row_idx / values` 与手算结果一致。\n";
    os << "- `Triangle2DVariableDofs`：验证每节点可变 DOF 的 Lagrange 单元输入，并将上三角 CSC3 展开为完整 dense 矩阵核对。\n";
    os << "- `SharedElementsParallelAtomic`：验证串行 `add()` 与 OpenMP atomic `add_parallel()` 的结构和值一致。\n";
    os << "- `ScatterInvariant`：验证每个局部上三角 entry 的 scatter 下标都指向正确 CSC3 结构项。\n";
    os << "- `LocalDofOrderUsesLocalUpperEntry` / `UnorderedVariableDofsDenseOracle`：验证局部 DOF 顺序不是全局升序时仍按局部上三角单刚读取数值。\n";
    os << "- `HighContentionParallelAtomic`：验证 1000 个共享 DOF 单元在高冲突 atomic 写入下与串行结果一致。\n";
    os << "- `RandomDeterministicOracle`：使用固定 seed 小规模随机网格比较 CSC3 展开结果和直接 dense assembly。\n";
    os << "- `ValidationFailures`：验证缺失节点、全局重复 DOF、DOF 编号不连续、单元内重复 DOF、单刚尺寸错误、NaN/Inf 单刚、缺失单刚和单刚非对称都会被拒绝。\n";
    return os.str();
}

bool openmp_enabled() {
#ifdef CSC3_DEMO_HAS_OPENMP
    return true;
#else
    return false;
#endif
}

} // namespace csc3_demo
