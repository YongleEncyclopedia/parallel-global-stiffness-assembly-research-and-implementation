/**
 * @file atomic_assembler.cu
 * @brief 原子操作 + Warp 聚合组装器 CUDA 实现
 */

#include "backends/cuda/atomic_assembler.h"
#include "backends/cuda/cuda_utils.cuh"
#include <cuda_runtime.h>

namespace fem {
namespace cuda {

// ============================================================================
// CUDA Kernels
// ============================================================================

/**
 * @brief Hex8 单元组装 Kernel（优化版：Warp 聚合 + Grid-stride + 按项计算）
 *
 * 优化点：
 * 1. Grid-stride loop 提高 SM 利用率
 * 2. 使用 warp_aggregated_atomic_add_full 减少原子冲突
 * 3. 使用 __ldg 加速只读全局内存访问
 * 4. 按项计算 Ke 减少寄存器压力
 */
__global__ void assemble_hex8_atomic_kernel(
    const double* __restrict__ node_x,
    const double* __restrict__ node_y,
    const double* __restrict__ node_z,
    const int* __restrict__ connectivity,
    const int* __restrict__ row_ptr,
    const int* __restrict__ col_ind,
    double* __restrict__ values,
    int num_elements)
{
    // Grid-stride loop: 提高大规模/小规模网格的 SM 利用率
    for (int elem_idx = blockIdx.x * blockDim.x + threadIdx.x;
         elem_idx < num_elements;
         elem_idx += blockDim.x * gridDim.x) {

        // 读取单元节点索引（使用 __ldg 缓存）
        int nodes[8];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            nodes[i] = __ldg(&connectivity[elem_idx * 8 + i]);
        }

        // 读取节点坐标（使用 __ldg 缓存）
        double coords[8][3];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            coords[i][0] = __ldg(&node_x[nodes[i]]);
            coords[i][1] = __ldg(&node_y[nodes[i]]);
            coords[i][2] = __ldg(&node_z[nodes[i]]);
        }

        // 计算刚度系数（避免完整 Ke 矩阵）
        double stiffness = compute_hex8_stiffness_coeff(coords);

        // 计算全局自由度索引
        int global_dofs[24];
        #pragma unroll
        for (int i = 0; i < 8; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        // 组装到全局矩阵（使用 Warp 聚合原子操作）
        for (int i = 0; i < 24; ++i) {
            int row = global_dofs[i];
            int row_start = __ldg(&row_ptr[row]);
            int row_end = __ldg(&row_ptr[row + 1]);

            for (int j = 0; j < 24; ++j) {
                int col = global_dofs[j];

                // 按项计算 Ke(i,j)，避免大矩阵分配
                double val = compute_hex8_entry(stiffness, i, j);

                // 跳过零值
                if (fabs(val) < 1e-15) continue;

                // 行内二分查找
                int idx = binary_search_row(col_ind, row_start, row_end, col);

                // Warp 聚合原子累加
                warp_aggregated_atomic_add_full(values, idx, val);
            }
        }
    }
}

/**
 * @brief Tet4 单元组装 Kernel（优化版：Warp 聚合 + Grid-stride + 按项计算）
 */
__global__ void assemble_tet4_atomic_kernel(
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

        // 读取单元节点索引（使用 __ldg 缓存）
        int nodes[4];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            nodes[i] = __ldg(&connectivity[elem_idx * 4 + i]);
        }

        // 读取节点坐标（使用 __ldg 缓存）
        double coords[4][3];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            coords[i][0] = __ldg(&node_x[nodes[i]]);
            coords[i][1] = __ldg(&node_y[nodes[i]]);
            coords[i][2] = __ldg(&node_z[nodes[i]]);
        }

        // 计算刚度系数
        double stiffness = compute_tet4_stiffness_coeff(coords);

        // 计算全局自由度索引
        int global_dofs[12];
        #pragma unroll
        for (int i = 0; i < 4; ++i) {
            global_dofs[i * 3 + 0] = nodes[i] * 3 + 0;
            global_dofs[i * 3 + 1] = nodes[i] * 3 + 1;
            global_dofs[i * 3 + 2] = nodes[i] * 3 + 2;
        }

        // 组装到全局矩阵（使用 Warp 聚合原子操作）
        for (int i = 0; i < 12; ++i) {
            int row = global_dofs[i];
            int row_start = __ldg(&row_ptr[row]);
            int row_end = __ldg(&row_ptr[row + 1]);

            for (int j = 0; j < 12; ++j) {
                int col = global_dofs[j];

                // 按项计算 Ke(i,j)
                double val = compute_tet4_entry(stiffness, i, j);

                // 跳过零值
                if (fabs(val) < 1e-15) continue;

                int idx = binary_search_row(col_ind, row_start, row_end, col);

                // Warp 聚合原子累加
                warp_aggregated_atomic_add_full(values, idx, val);
            }
        }
    }
}

}  // namespace cuda

// ============================================================================
// AtomicAssembler 实现
// ============================================================================

AtomicAssembler::AtomicAssembler(const AssemblyOptions& options)
    : options_(options) {}

AtomicAssembler::~AtomicAssembler() {
    cleanup();
}

void AtomicAssembler::set_mesh(const Mesh& mesh) {
    mesh_ = &mesh;
}

void AtomicAssembler::set_csr_structure(const CsrMatrix& csr) {
    host_result_ = csr;
}

void AtomicAssembler::prepare() {
    if (!mesh_) {
        throw FemException("Mesh not set");
    }

    // 分配设备内存并复制数据
    d_nodes_.allocate_and_copy(mesh_->nodes);
    d_conn_.allocate_and_copy(mesh_->connectivity);
    d_csr_.allocate_structure(host_result_);

    // 记录统计
    stats_.num_dofs = mesh_->num_dofs();
    stats_.num_elements_processed = mesh_->num_elements();
    stats_.nnz = host_result_.nnz;
    stats_.memory_usage_bytes = d_nodes_.memory_usage_bytes() +
                                d_conn_.memory_usage_bytes() +
                                d_csr_.memory_usage_bytes();

    prepared_ = true;
}

void AtomicAssembler::assemble() {
    if (!prepared_) {
        prepare();
    }

    // 清零 CSR 值
    d_csr_.zero_values();

    // 创建 CUDA events 计时
    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));

    CUDA_CHECK(cudaEventRecord(start));

    // 启动 kernel
    if (mesh_->element_type == ElementType::Hex8) {
        launch_hex8_kernel();
    } else {
        launch_tet4_kernel();
    }

    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));

    float kernel_ms = 0;
    CUDA_CHECK(cudaEventElapsedTime(&kernel_ms, start, stop));
    stats_.kernel_time_ms = kernel_ms;
    stats_.assembly_time_ms = kernel_ms;

    // 复制结果回主机
    cudaEvent_t d2h_start, d2h_stop;
    CUDA_CHECK(cudaEventCreate(&d2h_start));
    CUDA_CHECK(cudaEventCreate(&d2h_stop));
    CUDA_CHECK(cudaEventRecord(d2h_start));

    d_csr_.copy_values_to_host(host_result_);

    CUDA_CHECK(cudaEventRecord(d2h_stop));
    CUDA_CHECK(cudaEventSynchronize(d2h_stop));

    float d2h_ms = 0;
    CUDA_CHECK(cudaEventElapsedTime(&d2h_ms, d2h_start, d2h_stop));
    stats_.d2h_transfer_time_ms = d2h_ms;
    stats_.total_time_ms = stats_.assembly_time_ms + stats_.d2h_transfer_time_ms;

    // 清理 events
    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    cudaEventDestroy(d2h_start);
    cudaEventDestroy(d2h_stop);
}

void AtomicAssembler::cleanup() {
    d_nodes_.free();
    d_conn_.free();
    d_csr_.free();
    prepared_ = false;
}

void AtomicAssembler::launch_hex8_kernel() {
    int num_elements = static_cast<int>(mesh_->num_elements());
    int block_size = options_.block_size;
    int grid_size = (num_elements + block_size - 1) / block_size;

    cuda::assemble_hex8_atomic_kernel<<<grid_size, block_size>>>(
        d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
        d_conn_.d_data,
        d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
        num_elements
    );

    CUDA_CHECK_LAST();
}

void AtomicAssembler::launch_tet4_kernel() {
    int num_elements = static_cast<int>(mesh_->num_elements());
    int block_size = options_.block_size;
    int grid_size = (num_elements + block_size - 1) / block_size;

    cuda::assemble_tet4_atomic_kernel<<<grid_size, block_size>>>(
        d_nodes_.d_x, d_nodes_.d_y, d_nodes_.d_z,
        d_conn_.d_data,
        d_csr_.d_row_ptr, d_csr_.d_col_ind, d_csr_.d_values,
        num_elements
    );

    CUDA_CHECK_LAST();
}

// ============================================================================
// DeviceNodeCoordinates 实现
// ============================================================================

void DeviceNodeCoordinates::allocate_and_copy(const NodeCoordinates& host_data) {
    free();
    count = host_data.num_nodes();

    CUDA_CHECK(cudaMalloc(&d_x, count * sizeof(Real)));
    CUDA_CHECK(cudaMalloc(&d_y, count * sizeof(Real)));
    CUDA_CHECK(cudaMalloc(&d_z, count * sizeof(Real)));

    CUDA_CHECK(cudaMemcpy(d_x, host_data.x.data(), count * sizeof(Real), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_y, host_data.y.data(), count * sizeof(Real), cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_z, host_data.z.data(), count * sizeof(Real), cudaMemcpyHostToDevice));
}

void DeviceNodeCoordinates::free() {
    if (d_x) { cudaFree(d_x); d_x = nullptr; }
    if (d_y) { cudaFree(d_y); d_y = nullptr; }
    if (d_z) { cudaFree(d_z); d_z = nullptr; }
    count = 0;
}

// ============================================================================
// DeviceConnectivity 实现
// ============================================================================

void DeviceConnectivity::allocate_and_copy(const Connectivity& host_data) {
    free();
    num_elements = host_data.num_elements;
    nodes_per_element = host_data.nodes_per_element;

    size_t size = num_elements * nodes_per_element * sizeof(Index);
    CUDA_CHECK(cudaMalloc(&d_data, size));
    CUDA_CHECK(cudaMemcpy(d_data, host_data.data.data(), size, cudaMemcpyHostToDevice));
}

void DeviceConnectivity::free() {
    if (d_data) { cudaFree(d_data); d_data = nullptr; }
    num_elements = 0;
    nodes_per_element = 0;
}

}  // namespace fem
