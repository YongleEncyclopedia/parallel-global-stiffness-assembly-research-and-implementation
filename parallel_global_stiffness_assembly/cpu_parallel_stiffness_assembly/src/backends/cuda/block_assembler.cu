/**
 * @file block_assembler.cu
 * @brief 线程块并行组装器 CUDA 实现
 */

#include "backends/cuda/block_assembler.h"
#include "backends/cuda/cuda_utils.cuh"
#include <cuda_runtime.h>

namespace fem {
namespace cuda {

/**
 * @brief 线程块并行组装 Kernel（Hex8）- 优化版
 *
 * 优化点：
 * 1. 移除未使用的共享内存（提升占用率）
 * 2. Grid-stride loop 提高利用率
 * 3. __ldg 缓存加速只读访问
 * 4. 按项计算减少寄存器压力
 * 5. Warp 聚合原子操作
 */
__global__ void assemble_hex8_block_kernel(
    const double* __restrict__ node_x,
    const double* __restrict__ node_y,
    const double* __restrict__ node_z,
    const int* __restrict__ connectivity,
    const int* __restrict__ row_ptr,
    const int* __restrict__ col_ind,
    double* __restrict__ values,
    int num_elements)
{
    // Grid-stride loop
    for (int elem_idx = blockIdx.x * blockDim.x + threadIdx.x;
         elem_idx < num_elements;
         elem_idx += blockDim.x * gridDim.x) {

        // 读取节点索引（__ldg 缓存）
        int nodes[8];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            nodes[i] = __ldg(&connectivity[elem_idx * 8 + i]);
        }

        // 读取坐标
        double coords[8][3];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            coords[i][0] = __ldg(&node_x[nodes[i]]);
            coords[i][1] = __ldg(&node_y[nodes[i]]);
            coords[i][2] = __ldg(&node_z[nodes[i]]);
        }

        // 计算刚度系数
        double stiffness = compute_hex8_stiffness_coeff(coords);

        // 计算全局自由度
        int global_dofs[24];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        // 组装（Warp 聚合原子）
        for (int i = 0; i < 24; ++i) {
            int row = global_dofs[i];
            int row_start = __ldg(&row_ptr[row]);
            int row_end = __ldg(&row_ptr[row + 1]);

            for (int j = 0; j < 24; ++j) {
                int col = global_dofs[j];
                double val = compute_hex8_entry(stiffness, i, j);

                if (fabs(val) < 1e-15) continue;

                int idx = binary_search_row(col_ind, row_start, row_end, col);
                warp_aggregated_atomic_add_full(values, idx, val);
            }
        }
    }
}

/**
 * @brief 线程块并行组装 Kernel（Tet4）- 优化版
 */
__global__ void assemble_tet4_block_kernel(
    const double* __restrict__ node_x,
    const double* __restrict__ node_y,
    const double* __restrict__ node_z,
    const int* __restrict__ connectivity,
    const int* __restrict__ row_ptr,
    const int* __restrict__ col_ind,
    double* __restrict__ values,
    int num_elements)
{
    // Grid-stride loop
    for (int elem_idx = blockIdx.x * blockDim.x + threadIdx.x;
         elem_idx < num_elements;
         elem_idx += blockDim.x * gridDim.x) {

        int nodes[4];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            nodes[i] = __ldg(&connectivity[elem_idx * 4 + i]);
        }

        double coords[4][3];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            coords[i][0] = __ldg(&node_x[nodes[i]]);
            coords[i][1] = __ldg(&node_y[nodes[i]]);
            coords[i][2] = __ldg(&node_z[nodes[i]]);
        }

        double stiffness = compute_tet4_stiffness_coeff(coords);

        int global_dofs[12];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        for (int i = 0; i < 12; ++i) {
            int row = global_dofs[i];
            int row_start = __ldg(&row_ptr[row]);
            int row_end = __ldg(&row_ptr[row + 1]);

            for (int j = 0; j < 12; ++j) {
                int col = global_dofs[j];
                double val = compute_tet4_entry(stiffness, i, j);

                if (fabs(val) < 1e-15) continue;

                int idx = binary_search_row(col_ind, row_start, row_end, col);
                warp_aggregated_atomic_add_full(values, idx, val);
            }
        }
    }
}

}  // namespace cuda

// ============================================================================
// BlockAssembler 实现
// ============================================================================

BlockAssembler::BlockAssembler(const AssemblyOptions& options)
    : options_(options) {}

BlockAssembler::~BlockAssembler() {
    cleanup();
}

void BlockAssembler::set_mesh(const Mesh& mesh) {
    mesh_ = &mesh;
}

void BlockAssembler::set_csr_structure(const CsrMatrix& csr) {
    host_result_ = csr;
}

void BlockAssembler::prepare() {
    if (!mesh_) throw FemException("Mesh not set");

    d_nodes_.allocate_and_copy(mesh_->nodes);
    d_conn_.allocate_and_copy(mesh_->connectivity);
    d_csr_.allocate_structure(host_result_);

    stats_.num_dofs = mesh_->num_dofs();
    stats_.num_elements_processed = mesh_->num_elements();
    stats_.nnz = host_result_.nnz;
    stats_.memory_usage_bytes = d_nodes_.memory_usage_bytes() +
                                d_conn_.memory_usage_bytes() +
                                d_csr_.memory_usage_bytes();
    prepared_ = true;
}

void BlockAssembler::assemble() {
    if (!prepared_) prepare();

    d_csr_.zero_values();

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));

    int num_elements = static_cast<int>(mesh_->num_elements());
    int block_size = options_.block_size;
    int grid_size = (num_elements + block_size - 1) / block_size;

    if (mesh_->element_type == ElementType::Hex8) {
        cuda::assemble_hex8_block_kernel<<<grid_size, block_size>>>(
            d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
            d_conn_.d_data,
            d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
            num_elements
        );
    } else {
        cuda::assemble_tet4_block_kernel<<<grid_size, block_size>>>(
            d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
            d_conn_.d_data,
            d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
            num_elements
        );
    }
    CUDA_CHECK_LAST();

    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float kernel_ms = 0;
    CUDA_CHECK(cudaEventElapsedTime(&kernel_ms, start, stop));
    stats_.kernel_time_ms = kernel_ms;
    stats_.assembly_time_ms = kernel_ms;

    d_csr_.copy_values_to_host(host_result_);
    stats_.total_time_ms = stats_.assembly_time_ms;

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
}

void BlockAssembler::cleanup() {
    d_nodes_.free();
    d_conn_.free();
    d_csr_.free();
    prepared_ = false;
}

}  // namespace fem
