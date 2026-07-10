/**
 * @file workqueue_assembler.cu
 * @brief 工作队列动态负载均衡组装器 CUDA 实现
 */

#include "backends/cuda/workqueue_assembler.h"
#include "backends/cuda/cuda_utils.cuh"
#include <cuda_runtime.h>

namespace fem {
namespace cuda {

/**
 * @brief 工作队列组装 Kernel
 *
 * 使用原子计数器动态分配任务给线程
 */
__global__ void assemble_hex8_workqueue_kernel(
    const double* __restrict__ node_x,
    const double* __restrict__ node_y,
    const double* __restrict__ node_z,
    const int* __restrict__ connectivity,
    const int* __restrict__ row_ptr,
    const int* __restrict__ col_ind,
    double* __restrict__ values,
    int* __restrict__ work_counter,
    int num_elements)
{
    while (true) {
        // 动态领取任务
        int elem_idx = atomicAdd(work_counter, 1);
        if (elem_idx >= num_elements) break;

        int nodes[8];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            nodes[i] = connectivity[elem_idx * 8 + i];
        }

        double coords[8][3];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            coords[i][0] = node_x[nodes[i]];
            coords[i][1] = node_y[nodes[i]];
            coords[i][2] = node_z[nodes[i]];
        }

        double Ke[24 * 24];
        compute_hex8_stiffness(coords, Ke);

        int global_dofs[24];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        for (int i = 0; i < 24; ++i) {
            int row = global_dofs[i];
            int row_start = row_ptr[row];
            int row_end = row_ptr[row + 1];

            for (int j = 0; j < 24; ++j) {
                int col = global_dofs[j];
                double val = Ke[i * 24 + j];

                int idx = binary_search_row(col_ind, row_start, row_end, col);
                if (idx >= 0) {
                    atomicAdd(&values[idx], val);
                }
            }
        }
    }
}

__global__ void assemble_tet4_workqueue_kernel(
    const double* __restrict__ node_x,
    const double* __restrict__ node_y,
    const double* __restrict__ node_z,
    const int* __restrict__ connectivity,
    const int* __restrict__ row_ptr,
    const int* __restrict__ col_ind,
    double* __restrict__ values,
    int* __restrict__ work_counter,
    int num_elements)
{
    while (true) {
        int elem_idx = atomicAdd(work_counter, 1);
        if (elem_idx >= num_elements) break;

        int nodes[4];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            nodes[i] = connectivity[elem_idx * 4 + i];
        }

        double coords[4][3];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            coords[i][0] = node_x[nodes[i]];
            coords[i][1] = node_y[nodes[i]];
            coords[i][2] = node_z[nodes[i]];
        }

        double Ke[12 * 12];
        compute_tet4_stiffness(coords, Ke);

        int global_dofs[12];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        for (int i = 0; i < 12; ++i) {
            int row = global_dofs[i];
            int row_start = row_ptr[row];
            int row_end = row_ptr[row + 1];

            for (int j = 0; j < 12; ++j) {
                int col = global_dofs[j];
                double val = Ke[i * 12 + j];

                int idx = binary_search_row(col_ind, row_start, row_end, col);
                if (idx >= 0) {
                    atomicAdd(&values[idx], val);
                }
            }
        }
    }
}

}  // namespace cuda

WorkQueueAssembler::WorkQueueAssembler(const AssemblyOptions& options)
    : options_(options) {}

WorkQueueAssembler::~WorkQueueAssembler() {
    cleanup();
}

void WorkQueueAssembler::set_mesh(const Mesh& mesh) {
    mesh_ = &mesh;
}

void WorkQueueAssembler::set_csr_structure(const CsrMatrix& csr) {
    host_result_ = csr;
}

void WorkQueueAssembler::prepare() {
    if (!mesh_) throw FemException("Mesh not set");

    d_nodes_.allocate_and_copy(mesh_->nodes);
    d_conn_.allocate_and_copy(mesh_->connectivity);
    d_csr_.allocate_structure(host_result_);

    // 分配工作计数器
    CUDA_CHECK(cudaMalloc(&d_work_counter_, sizeof(int)));

    stats_.num_dofs = mesh_->num_dofs();
    stats_.num_elements_processed = mesh_->num_elements();
    stats_.nnz = host_result_.nnz;
    stats_.memory_usage_bytes = d_nodes_.memory_usage_bytes() +
                                d_conn_.memory_usage_bytes() +
                                d_csr_.memory_usage_bytes() +
                                sizeof(int);
    prepared_ = true;
}

void WorkQueueAssembler::assemble() {
    if (!prepared_) prepare();

    d_csr_.zero_values();

    // 重置工作计数器
    int zero = 0;
    CUDA_CHECK(cudaMemcpy(d_work_counter_, &zero, sizeof(int), cudaMemcpyHostToDevice));

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));

    int num_elements = static_cast<int>(mesh_->num_elements());

    // 使用较小的网格，让线程动态领取任务
    int block_size = options_.block_size;
    int grid_size = 256;  // 固定网格大小

    if (mesh_->element_type == ElementType::Hex8) {
        cuda::assemble_hex8_workqueue_kernel<<<grid_size, block_size>>>(
            d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
            d_conn_.d_data,
            d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
            d_work_counter_,
            num_elements
        );
    } else {
        cuda::assemble_tet4_workqueue_kernel<<<grid_size, block_size>>>(
            d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
            d_conn_.d_data,
            d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
            d_work_counter_,
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

void WorkQueueAssembler::cleanup() {
    d_nodes_.free();
    d_conn_.free();
    d_csr_.free();
    if (d_work_counter_) {
        cudaFree(d_work_counter_);
        d_work_counter_ = nullptr;
    }
    prepared_ = false;
}

}  // namespace fem
