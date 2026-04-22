# Dependencies.cmake
# 依赖管理配置

# 如果使用 vcpkg
if(USE_VCPKG AND DEFINED ENV{VCPKG_ROOT})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        CACHE STRING "Vcpkg toolchain file")
    message(STATUS "Using vcpkg from: $ENV{VCPKG_ROOT}")
endif()

# Eigen3（可选，用于矩阵运算验证）
find_package(Eigen3 QUIET)
if(Eigen3_FOUND)
    message(STATUS "Eigen3 found: ${Eigen3_VERSION}")
else()
    message(STATUS "Eigen3 not found, will use internal matrix operations")
endif()

# fmt（可选，用于格式化输出）
find_package(fmt QUIET)
if(fmt_FOUND)
    message(STATUS "fmt found")
else()
    message(STATUS "fmt not found, will use iostream")
endif()

# spdlog（可选，用于日志）
find_package(spdlog QUIET)
if(spdlog_FOUND)
    message(STATUS "spdlog found")
else()
    message(STATUS "spdlog not found, will use basic logging")
endif()
