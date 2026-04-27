cmake_minimum_required(VERSION 3.25)

# ============================================================
# 修复 MSVC + NVCC 的 PDB/Debug Information 问题
# CMP0141 控制 MSVC 调试信息格式，设为 NEW 允许我们覆盖
# 必须在 project() 之前设置
# ============================================================
if(POLICY CMP0141)
    cmake_policy(SET CMP0141 NEW)
endif()

# 禁用 MSVC 调试信息格式（避免向 NVCC 传递 -Xcompiler=-Fd...,-FS）
set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "" CACHE STRING "" FORCE)

# 在 project() 之前设置 CUDA 主机编译器（Windows MinGW 支持）
if(WIN32)
    # 检查是否使用 MinGW
    if(CMAKE_CXX_COMPILER)
        get_filename_component(CXX_COMPILER_NAME "${CMAKE_CXX_COMPILER}" NAME)
        if(CXX_COMPILER_NAME MATCHES "g\\+\\+")
            set(CMAKE_CUDA_HOST_COMPILER "${CMAKE_CXX_COMPILER}" CACHE FILEPATH "CUDA host compiler")
            message(STATUS "Pre-project: Using ${CMAKE_CXX_COMPILER} as CUDA host compiler")
        endif()
    endif()
endif()

# 允许使用不受官方支持的编译器（VS 2026 等）
# CUDA 13.1 官方仅支持 VS 2019-2022，但较新版本通常兼容
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -allow-unsupported-compiler" CACHE STRING "CUDA flags" FORCE)

# 项目定义
project(ParallelStiffnessAssembly
    VERSION 1.0.0
    LANGUAGES CXX CUDA
    DESCRIPTION "GPU Parallel Stiffness Matrix Assembly Benchmark"
)

# C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CUDA 标准
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)

# 设置 CUDA 架构 - RTX 5080 Blackwell (Compute 12.0)
# 同时支持较老架构以便测试
set(CMAKE_CUDA_ARCHITECTURES "86;89;120")

# 选项
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_BENCHMARKS "Build benchmark executables" ON)
option(USE_VCPKG "Use vcpkg for dependency management" OFF)
option(ENABLE_CUDA_DEBUG "Enable CUDA debug information" OFF)

# 输出目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# 包含自定义 CMake 模块
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# CUDA 配置
include(cmake/CudaConfig.cmake)

# 编译器选项
include(cmake/CompilerFlags.cmake)

# 依赖
include(cmake/Dependencies.cmake)

# ========== 核心库 ==========
add_library(fem_core STATIC
    src/core/mesh.cpp
    src/core/csr_matrix.cpp
    src/core/dof_map.cpp
)

target_include_directories(fem_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
    ${CUDAToolkit_INCLUDE_DIRS}
)

target_link_libraries(fem_core PUBLIC
    CUDA::cudart
)

# ========== 组装器库 (CUDA) ==========
add_library(fem_assembly STATIC
    src/assembly/assembler_factory.cpp
    src/assembly/assembly_options.cpp
    src/backends/cpu/serial_assembler.cpp
    src/backends/cuda/atomic_assembler.cu
    src/backends/cuda/block_assembler.cu
    src/backends/cuda/scan_assembler.cu
    src/backends/cuda/workqueue_assembler.cu
)

target_include_directories(fem_assembly PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(fem_assembly PUBLIC
    fem_core
    CUDA::cudart
    CUDA::cuda_driver
)

# CUDA 编译选项
target_compile_options(fem_assembly PRIVATE
    $<$<COMPILE_LANGUAGE:CUDA>:
        --expt-relaxed-constexpr
        --extended-lambda
        -lineinfo
        $<$<BOOL:${ENABLE_CUDA_DEBUG}>:-G>
    >
)

# ========== 基准测试程序 ==========
if(BUILD_BENCHMARKS)
    add_executable(benchmark_assembly
        apps/benchmark/main.cpp
    )

    target_link_libraries(benchmark_assembly PRIVATE
        fem_core
        fem_assembly
    )
endif()

# ========== 单元测试 ==========
if(BUILD_TESTS)
    enable_testing()

    # 如果找到 GTest
    find_package(GTest QUIET)
    if(GTest_FOUND)
        add_executable(test_mesh tests/unit/test_mesh.cpp)
        target_link_libraries(test_mesh PRIVATE fem_core GTest::gtest_main)
        add_test(NAME MeshTests COMMAND test_mesh)

        add_executable(test_csr tests/unit/test_csr.cpp)
        target_link_libraries(test_csr PRIVATE fem_core GTest::gtest_main)
        add_test(NAME CsrTests COMMAND test_csr)

        add_executable(test_assemblers tests/unit/test_assemblers.cpp)
        target_link_libraries(test_assemblers PRIVATE fem_assembly GTest::gtest_main)
        add_test(NAME AssemblerTests COMMAND test_assemblers)
    else()
        message(STATUS "GTest not found, unit tests will not be built")
    endif()

    # 正确性验证程序（不依赖 GTest）
    add_executable(verify_results tests/correctness/verify_results.cpp)
    target_link_libraries(verify_results PRIVATE fem_assembly)
endif()

# ========== 安装规则 ==========
install(TARGETS fem_core fem_assembly
    EXPORT ParallelStiffnessAssemblyTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)

install(DIRECTORY include/ DESTINATION include)

# 打印配置摘要
message(STATUS "")
message(STATUS "========== Configuration Summary ==========")
message(STATUS "Project: ${PROJECT_NAME} v${PROJECT_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CUDA architectures: ${CMAKE_CUDA_ARCHITECTURES}")
message(STATUS "Build tests: ${BUILD_TESTS}")
message(STATUS "Build benchmarks: ${BUILD_BENCHMARKS}")
message(STATUS "============================================")
message(STATUS "")
