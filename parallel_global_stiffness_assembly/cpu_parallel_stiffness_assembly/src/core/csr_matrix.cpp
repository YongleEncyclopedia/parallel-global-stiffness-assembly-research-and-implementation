#include "core/csr_matrix.h"

#include "core/platform.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace fem {

CsrMatrix::CsrMatrix(Index rows, Index cols, std::vector<Index> rowptr, std::vector<Index> cols_idx)
    : n_rows(rows), n_cols(cols), row_offsets(std::move(rowptr)), col_indices(std::move(cols_idx)) {
    values.assign(col_indices.size(), Real{0});
}

Size CsrMatrix::bytes() const noexcept {
    return row_offsets.size() * sizeof(Index) +
           col_indices.size() * sizeof(Index) +
           values.size() * sizeof(Real);
}

void CsrMatrix::zero_values() {
    std::fill(values.begin(), values.end(), Real{0});
}

Index CsrMatrix::find_position(Index row, Index col) const {
    if (row < 0 || row >= n_rows) throw std::out_of_range("CSR row out of range");
    const auto begin = col_indices.begin() + row_offsets[static_cast<Size>(row)];
    const auto end = col_indices.begin() + row_offsets[static_cast<Size>(row) + 1];
    const auto it = std::lower_bound(begin, end, col);
    if (it == end || *it != col) {
        throw std::runtime_error("CSR structure does not contain requested entry");
    }
    return static_cast<Index>(std::distance(col_indices.begin(), it));
}

bool CsrMatrix::same_structure(const CsrMatrix& other) const {
    return n_rows == other.n_rows && n_cols == other.n_cols &&
           row_offsets == other.row_offsets && col_indices == other.col_indices;
}

CsrMatrix CsrMatrix::build_sparsity(const Mesh& mesh) {
    const Size ndofs_size = mesh.num_dofs();
    if (ndofs_size > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Too many DOFs for 32-bit Index; switch Index to int64_t");
    }
    const Index ndofs = static_cast<Index>(ndofs_size);
    std::vector<std::vector<Index>> rows(static_cast<Size>(ndofs));

    for (const auto& elem : mesh.elements) {
        const auto dofs = element_dofs(elem);
        for (Index r : dofs) {
            auto& row = rows[static_cast<Size>(r)];
            row.insert(row.end(), dofs.begin(), dofs.end());
        }
    }

    std::vector<Index> row_offsets(static_cast<Size>(ndofs) + 1, 0);
    std::vector<Index> col_indices;
    Size nnz = 0;
    for (Index r = 0; r < ndofs; ++r) {
        auto& row = rows[static_cast<Size>(r)];
        std::sort(row.begin(), row.end());
        row.erase(std::unique(row.begin(), row.end()), row.end());
        nnz += row.size();
        if (nnz > static_cast<Size>(std::numeric_limits<Index>::max())) {
            throw std::runtime_error("Too many nonzeros for 32-bit Index; switch Index to int64_t");
        }
        row_offsets[static_cast<Size>(r) + 1] = static_cast<Index>(nnz);
    }
    col_indices.reserve(nnz);
    for (auto& row : rows) {
        col_indices.insert(col_indices.end(), row.begin(), row.end());
        std::vector<Index>().swap(row);
    }
    return CsrMatrix(ndofs, ndofs, std::move(row_offsets), std::move(col_indices));
}

CsrMatrix CsrMatrix::build_sparsity_parallel(const Mesh& mesh,
                                             int threads,
                                             Size* temporary_bytes) {
    const Size ndofs_size = mesh.num_dofs();
    if (ndofs_size > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Too many DOFs for 32-bit Index; switch Index to int64_t");
    }
    if (mesh.num_elements() > static_cast<Size>(std::numeric_limits<Index>::max())) {
        throw std::runtime_error("Too many elements for 32-bit Index adjacency");
    }

    const Index ndofs = static_cast<Index>(ndofs_size);
    const Size nnodes = mesh.num_nodes();
    const int nth = std::max(1, effective_thread_count(threads));

    std::vector<std::vector<Index>> node_to_elements(nnodes);
    Size incidence_count = 0;
    for (Size e = 0; e < mesh.elements.size(); ++e) {
        const auto& elem = mesh.elements[e];
        incidence_count += static_cast<Size>(elem.node_count);
        const Index elem_id = static_cast<Index>(e);
        for (int a = 0; a < elem.node_count; ++a) {
            const Index node = elem.nodes[a];
            if (node < 0 || static_cast<Size>(node) >= nnodes) {
                throw std::runtime_error("Element node index out of range during CSR build");
            }
            node_to_elements[static_cast<Size>(node)].push_back(elem_id);
        }
    }

    std::vector<std::vector<Index>> rows(static_cast<Size>(ndofs));

#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t rr = 0; rr < static_cast<std::int64_t>(ndofs); ++rr) {
        const Index row = static_cast<Index>(rr);
        const Index node = row / constants::DOFS_PER_NODE;
        auto& cols = rows[static_cast<Size>(row)];
        for (Index elem_id : node_to_elements[static_cast<Size>(node)]) {
            const auto dofs = element_dofs(mesh.elements[static_cast<Size>(elem_id)]);
            cols.insert(cols.end(), dofs.begin(), dofs.end());
        }
        std::sort(cols.begin(), cols.end());
        cols.erase(std::unique(cols.begin(), cols.end()), cols.end());
    }

    std::vector<Index> row_offsets(static_cast<Size>(ndofs) + 1, 0);
    Size nnz = 0;
    for (Index r = 0; r < ndofs; ++r) {
        nnz += rows[static_cast<Size>(r)].size();
        if (nnz > static_cast<Size>(std::numeric_limits<Index>::max())) {
            throw std::runtime_error("Too many nonzeros for 32-bit Index; switch Index to int64_t");
        }
        row_offsets[static_cast<Size>(r) + 1] = static_cast<Index>(nnz);
    }

    std::vector<Index> col_indices(nnz);
#ifdef _OPENMP
#pragma omp parallel for schedule(static) num_threads(nth)
#endif
    for (std::int64_t rr = 0; rr < static_cast<std::int64_t>(ndofs); ++rr) {
        const Size row = static_cast<Size>(rr);
        const auto& cols = rows[row];
        std::copy(cols.begin(), cols.end(), col_indices.begin() + row_offsets[row]);
    }

    if (temporary_bytes) {
        *temporary_bytes =
            node_to_elements.size() * sizeof(std::vector<Index>) +
            incidence_count * sizeof(Index) +
            rows.size() * sizeof(std::vector<Index>) +
            nnz * sizeof(Index);
    }
    return CsrMatrix(ndofs, ndofs, std::move(row_offsets), std::move(col_indices));
}

MatrixError compare_values(const CsrMatrix& reference, const CsrMatrix& candidate) {
    MatrixError err;
    err.same_structure = reference.same_structure(candidate);
    if (!err.same_structure) {
        err.relative_l2 = std::numeric_limits<Real>::infinity();
        err.max_abs = std::numeric_limits<Real>::infinity();
        return err;
    }
    long double diff2 = 0.0L;
    long double ref2 = 0.0L;
    Real max_abs = 0.0;
    for (Size i = 0; i < reference.values.size(); ++i) {
        const Real d = candidate.values[i] - reference.values[i];
        diff2 += static_cast<long double>(d) * d;
        ref2 += static_cast<long double>(reference.values[i]) * reference.values[i];
        max_abs = std::max(max_abs, std::abs(d));
    }
    err.max_abs = max_abs;
    if (ref2 <= 0.0L) {
        err.relative_l2 = std::sqrt(static_cast<Real>(diff2));
    } else {
        err.relative_l2 = std::sqrt(static_cast<Real>(diff2 / ref2));
    }
    return err;
}

std::string memory_string(Size bytes) {
    static constexpr const char* units[] = {"B", "KiB", "MiB", "GiB", "TiB"};
    double value = static_cast<double>(bytes);
    int unit = 0;
    while (value >= 1024.0 && unit < 4) {
        value /= 1024.0;
        ++unit;
    }
    std::ostringstream os;
    os << std::fixed << std::setprecision(unit == 0 ? 0 : 2) << value << " " << units[unit];
    return os.str();
}

} // namespace fem
