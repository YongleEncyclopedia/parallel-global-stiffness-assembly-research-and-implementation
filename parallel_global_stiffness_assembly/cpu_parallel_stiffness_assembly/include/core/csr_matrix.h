// 定义全局稀疏刚度矩阵的 CSR 存储，以及结构构建、位置查找和数值比较接口。
#pragma once

#include "core/types.h"
#include "core/mesh.h"

#include <vector>
#include <string>

namespace fem {

class CsrMatrix {
public:
    Index n_rows = 0;
    Index n_cols = 0;
    std::vector<Index> row_offsets;
    std::vector<Index> col_indices;
    std::vector<Real> values;

    CsrMatrix() = default;
    CsrMatrix(Index rows, Index cols, std::vector<Index> rowptr, std::vector<Index> cols_idx);

    [[nodiscard]] Size nnz() const noexcept { return col_indices.size(); }
    [[nodiscard]] Size bytes() const noexcept;
    void zero_values();
    [[nodiscard]] Index find_position(Index row, Index col) const;
    [[nodiscard]] bool same_structure(const CsrMatrix& other) const;

    static CsrMatrix build_sparsity(const Mesh& mesh);
    static CsrMatrix build_sparsity_parallel(const Mesh& mesh,
                                             int threads,
                                             Size* temporary_bytes = nullptr);
};

struct MatrixError {
    Real relative_l2 = 0.0;
    Real max_abs = 0.0;
    bool same_structure = true;
};

MatrixError compare_values(const CsrMatrix& reference, const CsrMatrix& candidate);
std::string memory_string(Size bytes);

} // namespace fem
