/**
 * @file quick_verify.cu
 * @brief 快速验证修复后的 Warp 聚合函数
 *
 * 编译：nvcc -arch=sm_86 -o quick_verify quick_verify.cu
 * 运行：./quick_verify
 */

#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cstdio>
#include <cmath>

namespace cg = cooperative_groups;

constexpr int WARP_SIZE = 32;

// ============================================================================
// 修复后的 Warp 聚合函数
// ============================================================================

__device__ __forceinline__
void warp_aggregated_atomic_add_full(double* base_ptr, int idx, double value) {
    // 早退: 无效索引直接返回
    if (idx < 0) return;

    // 获取活动线程掩码
    unsigned int active_mask = __activemask();

    // 找出写入同一索引的线程
    unsigned int same_idx_mask = __match_any_sync(active_mask, idx);

    // 计算相同索引的线程数量
    int active_count = __popc(same_idx_mask);

    // 获取当前 lane
    int lane = threadIdx.x % WARP_SIZE;

    // 在具有相同索引的线程中进行树状规约（修复：从小到大）
    double sum = value;

    // 标准树状规约：从 offset=1 开始，逐渐翻倍
    for (int offset = 1; offset < active_count; offset *= 2) {
        double other = __shfl_down_sync(same_idx_mask, sum, offset);
        sum += other;
    }

    // 计算 leader（最低 lane）执行原子操作
    int leader = __ffs(same_idx_mask) - 1;
    if (lane == leader) {
        atomicAdd(&base_ptr[idx], sum);
    }
}

// ============================================================================
// 测试 Kernel
// ============================================================================

__global__ void test_warp_aggregation(double* result, int num_threads) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_threads) return;

    // 测试场景 1：所有线程写入同一个位置，期望结果 = num_threads * 1.0
    warp_aggregated_atomic_add_full(result, 0, 1.0);

    // 测试场景 2：每个 warp 写入不同位置
    int warp_id = tid / WARP_SIZE;
    warp_aggregated_atomic_add_full(result, 1 + warp_id, 1.0);
}

__global__ void test_mixed_writes(double* result, int num_threads) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_threads) return;

    // 混合写入：偶数线程写入位置 0，奇数线程写入位置 1
    int target = tid % 2;
    warp_aggregated_atomic_add_full(result, target, 2.0);
}

// ============================================================================
// 主程序
// ============================================================================

bool check_result(const char* test_name, double actual, double expected, double tolerance = 1e-6) {
    double error = fabs(actual - expected) / fmax(fabs(expected), 1e-15);
    bool passed = error < tolerance;

    printf("%s: ", test_name);
    if (passed) {
        printf("✓ PASS (actual=%.6f, expected=%.6f, error=%.2e)\n", actual, expected, error);
    } else {
        printf("✗ FAIL (actual=%.6f, expected=%.6f, error=%.2e)\n", actual, expected, error);
    }

    return passed;
}

int main() {
    printf("========================================\n");
    printf("Warp 聚合函数修复验证\n");
    printf("========================================\n\n");

    const int num_threads = 256;
    const int block_size = 256;
    const int grid_size = (num_threads + block_size - 1) / block_size;

    // 分配设备内存
    double* d_result1;
    double* d_result2;
    cudaMalloc(&d_result1, 100 * sizeof(double));
    cudaMalloc(&d_result2, 100 * sizeof(double));

    int all_pass = 1;

    // ========================================================================
    // 测试 1：基本聚合测试
    // ========================================================================
    printf("测试 1：基本 Warp 聚合\n");
    printf("--------------------\n");

    cudaMemset(d_result1, 0, 100 * sizeof(double));
    test_warp_aggregation<<<grid_size, block_size>>>(d_result1, num_threads);
    cudaDeviceSynchronize();

    double h_result1[100];
    cudaMemcpy(h_result1, d_result1, 100 * sizeof(double), cudaMemcpyDeviceToHost);

    // 验证：所有线程写入位置 0，期望 = 256.0
    all_pass &= check_result("  场景1 (所有线程->位置0)", h_result1[0], 256.0);

    // 验证：每个 warp 写入不同位置 (8 个 warp，每个 32 个线程)
    int num_warps = (num_threads + 31) / 32;
    for (int i = 0; i < num_warps; ++i) {
        int expected_threads = (i == num_warps - 1) ?
                               (num_threads - i * 32) : 32;
        char test_name[100];
        snprintf(test_name, sizeof(test_name), "  场景2 (warp %d->位置%d)", i, i + 1);
        all_pass &= check_result(test_name, h_result1[1 + i], (double)expected_threads);
    }

    printf("\n");

    // ========================================================================
    // 测试 2：混合写入测试
    // ========================================================================
    printf("测试 2：混合写入模式\n");
    printf("--------------------\n");

    cudaMemset(d_result2, 0, 100 * sizeof(double));
    test_mixed_writes<<<grid_size, block_size>>>(d_result2, num_threads);
    cudaDeviceSynchronize();

    double h_result2[100];
    cudaMemcpy(h_result2, d_result2, 100 * sizeof(double), cudaMemcpyDeviceToHost);

    // 128 个偶数线程写入位置 0，每个写入 2.0
    all_pass &= check_result("  偶数线程->位置0", h_result2[0], 256.0);
    // 128 个奇数线程写入位置 1，每个写入 2.0
    all_pass &= check_result("  奇数线程->位置1", h_result2[1], 256.0);

    printf("\n");

    // ========================================================================
    // 总结
    // ========================================================================
    printf("========================================\n");
    if (all_pass) {
        printf("✅ 所有测试通过！Warp 聚合函数修复成功。\n");
        printf("   可以继续编译完整项目。\n");
    } else {
        printf("❌ 部分测试失败，需要进一步调试。\n");
    }
    printf("========================================\n");

    // 清理
    cudaFree(d_result1);
    cudaFree(d_result2);

    return all_pass ? 0 : 1;
}
