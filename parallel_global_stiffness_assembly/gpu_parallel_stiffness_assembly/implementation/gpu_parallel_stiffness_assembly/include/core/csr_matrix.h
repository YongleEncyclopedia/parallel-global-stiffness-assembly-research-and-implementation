/**
 * @file csr_matrix.h
 * @brief CSR (Compressed Sparse Row) 稀疏矩阵
 *
 * 用于存储全局刚度矩阵的 CSR 格式
 */

#pragma once

#include "types.h"
#include <vector>
#include <algorithm>
#include <cassert>
#include <cmath>

namespace fem {

/**
 * @brief CSR 稀疏矩阵（主机端）
 *
 * 存储格式：
 * - row_ptr: 大小 [num_rows + 1]，row_ptr[i] 到 row_ptr[i+1] 指示第 i 行的非零元范围
 * - col_ind: 大小 [nnz]，列索引
 * - values:  大小 [nnz]，非零元值
 */
class CsrMatrix {
public:
    std::vector<Index> row_ptr;   ///< 行指针
    std::vector<Index> col_ind;   ///< 列索引
    std::vector<Real> values;     ///< 非零元值

    Size num_rows = 0;            ///< 行数
    Size num_cols = 0;            ///< 列数
    Size nnz = 0;                 ///< 非零元数量

    // ========================================================================
    // 构造与初始化
    // ========================================================================

    CsrMatrix() = default;

    /**
     * @brief 从维度初始化（仅分配 row_ptr）
     */
    void init(Size rows, Size cols) {
        num_rows = rows;
        num_cols = cols;
        row_ptr.assign(rows + 1, 0);
        col_ind.clear();
        values.clear();
        nnz = 0;
    }

    /**
     * @brief 从预计算的结构初始化（用于并行组装）
     *
     * @param rows 行数
     * @param cols 列数
     * @param row_counts 每行的非零元数量
     */
    void init_from_row_counts(Size rows, Size cols, const std::vector<Index>& row_counts) {
        num_rows = rows;
        num_cols = cols;

        // 构建 row_ptr（前缀和）
        row_ptr.resize(rows + 1);
        row_ptr[0] = 0;
        for (Size i = 0; i < rows; ++i) {
            row_ptr[i + 1] = row_ptr[i] + row_counts[i];
        }
        nnz = row_ptr[rows];

        // 分配列索引和值
        col_ind.resize(nnz);
        values.assign(nnz, 0.0);  // 初始化为零
    }

    // ========================================================================
    // 查询操作
    // ========================================================================

    /**
     * @brief 获取第 row 行的非零元起始位置
     */
    Index row_start(Index row) const {
        return row_ptr[row];
    }

    /**
     * @brief 获取第 row 行的非零元结束位置（不包含）
     */
    Index row_end(Index row) const {
        return row_ptr[row + 1];
    }

    /**
     * @brief 获取第 row 行的非零元数量
     */
    Index row_nnz(Index row) const {
        return row_ptr[row + 1] - row_ptr[row];
    }

    /**
     * @brief 在第 row 行中查找列索引 col 的位置（行内二分查找）
     *
     * @param row 行索引
     * @param col 列索引
     * @return 在 col_ind 中的位置，如果未找到返回 -1
     */
    Index find_col_index(Index row, Index col) const {
        Index start = row_ptr[row];
        Index end = row_ptr[row + 1];

        // 行内二分查找
        auto it = std::lower_bound(
            col_ind.begin() + start,
            col_ind.begin() + end,
            col
        );

        if (it != col_ind.begin() + end && *it == col) {
            return static_cast<Index>(it - col_ind.begin());
        }
        return -1;  // 未找到
    }

    /**
     * @brief 获取元素值（带查找）
     */
    Real get(Index row, Index col) const {
        Index idx = find_col_index(row, col);
        if (idx >= 0) {
            return values[idx];
        }
        return 0.0;  // 零元素
    }

    /**
     * @brief 设置元素值（假设位置已知）
     */
    void set_by_index(Index idx, Real value) {
        values[idx] = value;
    }

    /**
     * @brief 累加元素值（假设位置已知）
     */
    void add_by_index(Index idx, Real value) {
        values[idx] += value;
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

    /**
     * @brief 清零所有值（保留结构）
     */
    void zero_values() {
        std::fill(values.begin(), values.end(), 0.0);
    }

    /**
     * @brief 验证 CSR 结构的有效性
     */
    bool is_valid() const {
        if (row_ptr.size() != num_rows + 1) return false;
        if (col_ind.size() != nnz) return false;
        if (values.size() != nnz) return false;
        if (row_ptr[num_rows] != static_cast<Index>(nnz)) return false;

        // 检查每行的列索引是否有序
        for (Size i = 0; i < num_rows; ++i) {
            for (Index j = row_ptr[i]; j < row_ptr[i + 1] - 1; ++j) {
                if (col_ind[j] >= col_ind[j + 1]) return false;
            }
            // 检查列索引范围
            for (Index j = row_ptr[i]; j < row_ptr[i + 1]; ++j) {
                if (col_ind[j] < 0 || col_ind[j] >= static_cast<Index>(num_cols)) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * @brief 计算 Frobenius 范数
     */
    Real frobenius_norm() const {
        Real sum = 0.0;
        for (const auto& v : values) {
            sum += v * v;
        }
        return std::sqrt(sum);
    }

    /**
     * @brief 内存使用量（字节）
     */
    Size memory_usage_bytes() const {
        return row_ptr.size() * sizeof(Index) +
               col_ind.size() * sizeof(Index) +
               values.size() * sizeof(Real);
    }
};

/**
 * @brief CSR 矩阵的设备端存储
 */
struct DeviceCsrMatrix {
    Index* d_row_ptr = nullptr;
    Index* d_col_ind = nullptr;
    Real* d_values = nullptr;
    Size num_rows = 0;
    Size num_cols = 0;
    Size nnz = 0;

    /**
     * @brief 从主机数据分配并复制（仅结构，不复制值）
     */
    void allocate_structure(const CsrMatrix& host_matrix);

    /**
     * @brief 分配并复制完整数据
     */
    void allocate_and_copy(const CsrMatrix& host_matrix);

    /**
     * @brief 将值复制回主机
     */
    void copy_values_to_host(CsrMatrix& host_matrix) const;

    /**
     * @brief 清零值（在设备上）
     */
    void zero_values();

    /**
     * @brief 释放设备内存
     */
    void free();

    /**
     * @brief 内存使用量（字节）
     */
    Size memory_usage_bytes() const {
        return (num_rows + 1) * sizeof(Index) +
               nnz * sizeof(Index) +
               nnz * sizeof(Real);
    }
};

}  // namespace fem
