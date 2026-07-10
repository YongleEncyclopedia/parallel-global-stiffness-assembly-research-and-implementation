# CudaConfig.cmake
# CUDA 编译器和运行时配置

# 设置 NVCC 主机编译器（Windows 上使用 MinGW g++ 替代 cl.exe）
if(WIN32 AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    # 使用 g++ 作为 NVCC 主机编译器
    set(CMAKE_CUDA_HOST_COMPILER "${CMAKE_CXX_COMPILER}")
    message(STATUS "Using ${CMAKE_CXX_COMPILER} as CUDA host compiler")
endif()

# 允许使用不受官方支持的编译器（VS 2026 / MSVC 19.50+）
# CUDA 13.1 官方仅支持 VS 2019-2022，但 VS 2026 通常兼容
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -allow-unsupported-compiler")

# 查找 CUDA Toolkit
find_package(CUDAToolkit REQUIRED)

# 打印 CUDA 信息
message(STATUS "CUDA Toolkit version: ${CUDAToolkit_VERSION}")
message(STATUS "CUDA include dirs: ${CUDAToolkit_INCLUDE_DIRS}")

# 设置 CUDA 编译选项
set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} --use_fast_math")

# MSVC 主机编译器选项 - 添加 /utf-8 解决中文注释编码问题
if(MSVC)
    set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} -Xcompiler=/utf-8")
endif()

# Debug 模式下的 CUDA 选项
set(CMAKE_CUDA_FLAGS_DEBUG "${CMAKE_CUDA_FLAGS_DEBUG} -G -g")

# Release 模式下的 CUDA 选项
set(CMAKE_CUDA_FLAGS_RELEASE "${CMAKE_CUDA_FLAGS_RELEASE} -O3")

# 分离编译支持（用于大型项目）
set(CMAKE_CUDA_SEPARABLE_COMPILATION ON)

# ============================================================
# 修复 MSVC + NVCC 的 PDB 标志问题
# CMake 3.25+ 会自动传递 /Fd 和 /FS 给 NVCC -Xcompiler
# 逗号分隔的格式会导致 NVCC 解析失败
# ============================================================
if(MSVC)
    # 清除 CUDA 的调试信息格式，避免 /Fd 和 /FS 标志
    set(CMAKE_CUDA_FLAGS_DEBUG "${CMAKE_CUDA_FLAGS_DEBUG}" CACHE STRING "" FORCE)
    set(CMAKE_CUDA_FLAGS_RELEASE "${CMAKE_CUDA_FLAGS_RELEASE}" CACHE STRING "" FORCE)
    set(CMAKE_CUDA_FLAGS_RELWITHDEBINFO "${CMAKE_CUDA_FLAGS_RELWITHDEBINFO}" CACHE STRING "" FORCE)

    # 禁用 MSVC 调试信息格式对 CUDA 的影响
    # 这会阻止 CMake 向 NVCC 传递 -Xcompiler=-Fd...,-FS
    if(POLICY CMP0141)
        cmake_policy(SET CMP0141 NEW)
    endif()
    set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "" CACHE STRING "" FORCE)
endif()

# PTX 生成（用于调试和优化分析）
# set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} --keep --ptxas-options=-v")
