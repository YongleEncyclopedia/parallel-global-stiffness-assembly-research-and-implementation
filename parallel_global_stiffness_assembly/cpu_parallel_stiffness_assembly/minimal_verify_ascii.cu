/**
 * @file minimal_verify_ascii.cu
 * @brief Minimal Warp aggregation verification program (ASCII only)
 *
 * Compile: nvcc -O2 -arch=sm_86 -o minimal_verify minimal_verify_ascii.cu
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

// Fixed warp aggregation function
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

// Test kernel
__global__ void test_kernel(double* result, int scenario) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    if (scenario == 1) {
        warp_aggregated_atomic_add_full(result, 0, 1.0);
    } else if (scenario == 2) {
        int target_idx = tid % 2;
        warp_aggregated_atomic_add_full(result, target_idx, 1.0);
    } else if (scenario == 3) {
        int target_idx = tid / 4;
        warp_aggregated_atomic_add_full(result, target_idx, 1.0);
    }
}

int main() {
    printf("==========================================\n");
    printf("Warp Aggregation Function Verification\n");
    printf("==========================================\n\n");

    // GPU info
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

    // Test 1: All threads write to same location
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 1);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result;
        CUDA_CHECK(cudaMemcpy(&h_result, d_result, sizeof(double), cudaMemcpyDeviceToHost));

        double expected = 256.0;
        double error = fabs(h_result - expected) / expected;
        bool pass = error < 1e-10;

        printf("Test 1: Full thread aggregation\n");
        printf("  Expected: %.1f\n", expected);
        printf("  Actual: %.1f\n", h_result);
        printf("  Relative error: %.2e\n", error);
        printf("  Status: %s\n\n", pass ? "[PASS]" : "[FAIL]");

        total++;
        if (pass) passed++;
    }

    // Test 2: Even/odd threads
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 2);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result[2];
        CUDA_CHECK(cudaMemcpy(h_result, d_result, 2 * sizeof(double), cudaMemcpyDeviceToHost));

        bool pass = true;
        printf("Test 2: Even/odd thread groups\n");
        for (int i = 0; i < 2; i++) {
            double expected = 128.0;
            double error = fabs(h_result[i] - expected) / expected;
            bool p = error < 1e-10;
            printf("  Location %d: %.1f (expected %.1f) [%s]\n",
                   i, h_result[i], expected, p ? "OK" : "FAIL");
            pass = pass && p;
        }
        printf("  Status: %s\n\n", pass ? "[PASS]" : "[FAIL]");

        total++;
        if (pass) passed++;
    }

    // Test 3: Groups of 4 threads
    {
        CUDA_CHECK(cudaMemset(d_result, 0, 100 * sizeof(double)));
        test_kernel<<<blocks, threads>>>(d_result, 3);
        CUDA_CHECK(cudaDeviceSynchronize());

        double h_result[64];
        CUDA_CHECK(cudaMemcpy(h_result, d_result, 64 * sizeof(double), cudaMemcpyDeviceToHost));

        bool pass = true;
        printf("Test 3: Groups of 4 threads (showing first 5 groups)\n");
        for (int i = 0; i < 5; i++) {
            double expected = 4.0;
            double error = fabs(h_result[i] - expected) / expected;
            bool p = error < 1e-10;
            printf("  Group %d: %.1f (expected %.1f) [%s]\n",
                   i, h_result[i], expected, p ? "OK" : "FAIL");
            pass = pass && p;
        }

        // Check all 64 groups
        for (int i = 0; i < 64; i++) {
            double expected = 4.0;
            double error = fabs(h_result[i] - expected) / expected;
            if (error >= 1e-10) {
                pass = false;
                break;
            }
        }

        printf("  Status: %s\n\n", pass ? "[PASS]" : "[FAIL]");

        total++;
        if (pass) passed++;
    }

    printf("==========================================\n");
    printf("Test Results: %d/%d passed\n", passed, total);
    printf("==========================================\n");

    if (passed == total) {
        printf("\n[SUCCESS] All tests passed!\n");
        printf("Warp aggregation function fix verified.\n");
        printf("The 0.647 error issue has been resolved.\n\n");
    } else {
        printf("\n[FAILURE] Some tests failed!\n");
        printf("Further debugging needed.\n\n");
    }

    cudaFree(d_result);
    return (passed == total) ? 0 : 1;
}
