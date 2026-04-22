/**
 * @file test_csr.cpp
 * @brief CSR 矩阵单元测试
 */

#include <gtest/gtest.h>
#include "core/csr_matrix.h"

using namespace fem;

TEST(CsrMatrixTest, BinarySearch) {
    CsrMatrix csr;
    csr.num_rows = 3;
    csr.num_cols = 3;
    csr.row_ptr = {0, 2, 4, 6};
    csr.col_ind = {0, 2, 0, 1, 1, 2};
    csr.values = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
    csr.nnz = 6;

    // 查找存在的元素
    EXPECT_EQ(csr.find_col_index(0, 0), 0);
    EXPECT_EQ(csr.find_col_index(0, 2), 1);
    EXPECT_EQ(csr.find_col_index(1, 0), 2);
    EXPECT_EQ(csr.find_col_index(1, 1), 3);

    // 查找不存在的元素
    EXPECT_EQ(csr.find_col_index(0, 1), -1);
    EXPECT_EQ(csr.find_col_index(2, 0), -1);
}

TEST(CsrMatrixTest, Validity) {
    CsrMatrix csr;
    csr.num_rows = 2;
    csr.num_cols = 2;
    csr.row_ptr = {0, 1, 2};
    csr.col_ind = {0, 1};
    csr.values = {1.0, 2.0};
    csr.nnz = 2;

    EXPECT_TRUE(csr.is_valid());
}

TEST(CsrMatrixTest, FrobeniusNorm) {
    CsrMatrix csr;
    csr.values = {3.0, 4.0};  // ||[3, 4]|| = 5
    csr.nnz = 2;

    EXPECT_DOUBLE_EQ(csr.frobenius_norm(), 5.0);
}
