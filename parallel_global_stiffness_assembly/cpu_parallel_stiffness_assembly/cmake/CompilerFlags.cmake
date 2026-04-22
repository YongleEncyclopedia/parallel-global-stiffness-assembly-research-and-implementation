# CompilerFlags.cmake
# 编译器选项配置

# 通用警告选项 - 仅用于 CXX，CUDA 单独处理
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wall -Wextra -Wpedantic>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-unknown-pragmas>)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    # 仅对 CXX 文件应用这些选项，避免影响 CUDA 编译
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/W4>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/permissive->)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/wd4100>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/wd4127>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/wd4244>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/wd4267>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/utf-8>)

    # 禁用 MSVC 的 PDB 生成相关标志（避免 NVCC 解析问题）
    # 这些标志中的逗号会导致 NVCC 错误解析命令行
    string(REPLACE "/Zi" "" CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG}")
    string(REPLACE "/ZI" "" CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG}")
    set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "")
endif()

# Release 优化 - 仅用于 CXX，CUDA 有自己的优化标志
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-O3 -DNDEBUG>)
        add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-march=native>)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
        # 仅对 CXX 文件应用 MSVC 优化标志
        add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/O2>)
        add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/DNDEBUG>)
        add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/arch:AVX2>)
    endif()
endif()

# OpenMP 支持（用于 CPU 基线的多线程版本）
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    message(STATUS "OpenMP found, CPU baseline will use OpenMP")
endif()
