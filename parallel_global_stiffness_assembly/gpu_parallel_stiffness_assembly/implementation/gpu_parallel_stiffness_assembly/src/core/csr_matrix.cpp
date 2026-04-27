/**
 * @file csr_matrix.cpp
 * @brief CSR 矩阵的非内联实现和 CUDA 内存操作
 */

#include "core/csr_matrix.h"
#include <cuda_runtime.h>
#include <cstring>
#include <stdexcept>

namespace fem {

// ============================================================================
// CUDA 错误检查宏
// ============================================================================

#define CUDA_CHECK(call)                                                      \
    do {                                                                       \
        cudaError_t err = call;                                                \
        if (err != cudaSuccess) {                                              \
            throw CudaException(std::string(cudaGetErrorString(err)) +         \
                                " at " + __FILE__ + ":" + std::to_string(__LINE__)); \
        }                                                                      \
    } while (0)

// ============================================================================
// DeviceCsrMatrix 实现
// ============================================================================

void DeviceCsrMatrix::allocate_structure(const CsrMatrix& host_matrix) {
    free();  // 释放已有内存

    num_rows = host_matrix.num_rows;
    num_cols = host_matrix.num_cols;
    nnz = host_matrix.nnz;

    // 分配设备内存
    CUDA_CHECK(cudaMalloc(&d_row_ptr, (num_rows + 1) * sizeof(Index)));
    CUDA_CHECK(cudaMalloc(&d_col_ind, nnz * sizeof(Index)));
    CUDA_CHECK(cudaMalloc(&d_values, nnz * sizeof(Real)));

    // 复制结构（row_ptr 和 col_ind）
    CUDA_CHECK(cudaMemcpy(d_row_ptr, host_matrix.row_ptr.data(),
                          (num_rows + 1) * sizeof(Index), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_col_ind, host_matrix.col_ind.data(),
                          nnz * sizeof(Index), cudaMemcpyHostToDevice));

    // 初始化值为零
    CUDA_CHECK(cudaMemset(d_values, 0, nnz * sizeof(Real)));
}

void DeviceCsrMatrix::allocate_and_copy(const CsrMatrix& host_matrix) {
    allocate_structure(host_matrix);

    // 复制值
    CUDA_CHECK(cudaMemcpy(d_values, host_matrix.values.data(),
                          nnz * sizeof(Real), cudaMemcpyHostToDevice));
}

void DeviceCsrMatrix::copy_values_to_host(CsrMatrix& host_matrix) const {
    if (host_matrix.values.size() != nnz) {
        host_matrix.values.resize(nnz);
    }
    CUDA_CHECK(cudaMemcpy(host_matrix.values.data(), d_values,
                          nnz * sizeof(Real), cudaMemcpyDeviceToHost));
}

void DeviceCsrMatrix::zero_values() {
    if (d_values && nnz > 0) {
        CUDA_CHECK(cudaMemset(d_values, 0, nnz * sizeof(Real)));
    }
}

void DeviceCsrMatrix::free() {
    if (d_row_ptr) {
        cudaFree(d_row_ptr);
        d_row_ptr = nullptr;
    }
    if (d_col_ind) {
        cudaFree(d_col_ind);
        d_col_ind = nullptr;
    }
    if (d_values) {
        cudaFree(d_values);
        d_values = nullptr;
    }
    num_rows = 0;
    num_cols = 0;
    nnz = 0;
}

}  // namespace fem
