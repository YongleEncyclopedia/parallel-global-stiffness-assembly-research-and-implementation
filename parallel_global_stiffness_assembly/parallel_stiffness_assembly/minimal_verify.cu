/**
 * @file minimal_verify.cu
 * @brief 最小化 Warp 聚合验证程序（独立编译）
 *
 * 编译: nvcc -O2 -o minimal_verify minimal_verify.cu
 */

#include <cuda_runtime.h>
#include <cstdio>
#include <cmath>

#define CUDA_CHECK(call) \
    do { \
        cudaError_t err = call; \
        if (err != cudaSuccess) { \
            printf("CUDA Error: %s at %d\n", cudaGetErrorString(err), __LINE__); \
            return 1; \
        } \
    } while(0)

constexpr int WARP_SIZE = 32;

// 修复后的 Warp 聚合函数
__device__ __forceinline__
void warp_aggregated_atomic_add_full(double* base_ptr, int idx, double value) {
    if (idx < 0) return;

    unsigned int active_mask = __activemask();
    unsigned int same_idx_mask = __match_any_sync(active_mask, idx);
    int active_count = __popc(same_idx_mask);
    int lane = threadIdx.x % WARP_SIZE;

    double sum = value;
    for (int offset = 1; offset < active_count; offset *= 2) {
        double other = __shfl_down_sync(same_idx_mask, sum, offset);
        sum += other;
    }

    int leader = __ffs(same_idx_mask) - 1;
    if (lane == leader) {
        atomicAdd(&base_ptr[idx], sum);
    }
}

// 测试 kernel
__global__ void test_kernel(double* result, int scenario) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    if (scenario == 1) {
        // 所有256个线程写入位置0
        warp_aggregated_atomic_add_full(result, 0, 1.0);
    } else if (scenario == 2) {
        // 偶数/奇数线程分别写入0/1
        int target = tid % 2;
        warp_aggregated_atomic_add_full(result, target, 1.0);
    } else if (scenario == 3) {
        // 每4个线程一组写入
        int target = tid / 4;
        warp_aggregated_atomic_add_full(result, target, 1.0);
    }
}

int main() {
    printf("==========================================\n");
    printf("Warp 聚合函数验证\n");
    printf("==========================================\n\n");

    // GPU 信息
    int device;
    CUDA_CHECK(cudaGetDevice(&device));
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, device));
    printf("GPU: %s\n", prop.name);
    printf("Compute Capability: %d.%d\n\n", prop.major, prop.minor);

    double* d_result;
    CUDA_CHECK(cudaMalloc(&d_result, 100 * sizeof(double)));

    const int threads = 256;
    const int blocks = 1;
    int passed = 0;
    int total = 0;

    // 测试1：所有线程写同一位置
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 1);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result;
        CUDA_CHECK(cudaMemcpy(&h_result, d_result, sizeof(double), cudaMemcpyDeviceToHost));

        double expected = 256.0;
        double error = fabs(h_result - expected) / expected;
        bool pass = error < 1e-10;

        printf("测试 1: 全线程聚合\n");
        printf("  期望值: %.1f\n", expected);
        printf("  实际值: %.1f\n", h_result);
        printf("  相对误差: %.2e\n", error);
        printf("  状态: %s\n\n", pass ? "✓ PASS" : "✗ FAIL");

        total++;
        if (pass) passed++;
    }

    // 测试2：偶数/奇数分组
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 2);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result[2];
        CUDA_CHECK(cudaMemcpy(h_result, d_result, 2 * sizeof(double), cudaMemcpyDeviceToHost));

        bool pass = true;
        printf("测试 2: 偶数/奇数分组\n");
        for (int i = 0; i < 2; i++) {
            double expected = 128.0;
            double error = fabs(h_result[i] - expected) / expected;
            bool p = error < 1e-10;
            printf("  位置 %d: %.1f (期望 %.1f) [%s]\n",
                   i, h_result[i], expected, p ? "✓" : "✗");
            pass = pass && p;
        }
        printf("  状态: %s\n\n", pass ? "✓ PASS" : "✗ FAIL");

        total++;
        if (pass) passed++;
    }

    // 测试3：每4个线程一组
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 3);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result[64];
        CUDA_CHECK(cudaMemcpy(h_result, d_result, 64 * sizeof(double), cudaMemcpyDeviceToHost));

        bool pass = true;
        printf("测试 3: 每4线程一组 (显示前5组)\n");
        for (int i = 0; i < 5; i++) {
            double expected = 4.0;
            double error = fabs(h_result[i] - expected) / expected;
            bool p = error < 1e-10;
            printf("  组 %d: %.1f (期望 %.1f) [%s]\n",
                   i, h_result[i], expected, p ? "✓" : "✗");
            pass = pass && p;
        }

        // 检查所有64组
        for (int i = 0; i < 64; i++) {
            double expected = 4.0;
            double error = fabs(h_result[i] - expected) / expected;
            if (error >= 1e-10) {
                pass = false;
                break;
            }
        }

        printf("  状态: %s\n\n", pass ? "✓ PASS" : "✗ FAIL");

        total++;
        if (pass) passed++;
    }

    printf("==========================================\n");
    printf("测试结果: %d/%d 通过\n", passed, total);
    printf("==========================================\n");

    if (passed == total) {
        printf("\n✅ 所有测试通过！\n");
        printf("   Warp 聚合函数修复成功，误差问题已解决。\n");
        printf("   可以继续编译完整项目。\n\n");
    } else {
        printf("\n❌ 部分测试失败！\n");
        printf("   需要进一步调试 Warp 聚合函数。\n\n");
    }

    cudaFree(d_result);
    return (passed == total) ? 0 : 1;
}
