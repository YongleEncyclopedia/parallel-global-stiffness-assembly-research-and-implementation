cmake_minimum_required(VERSION 3.20)

project(Csc3SymmetricAssemblyDemo
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(CSC3_DEMO_ENABLE_OPENMP "Enable OpenMP atomic numeric assembly" ON)
option(CSC3_DEMO_ENABLE_EIGEN "Enable optional Eigen adapter when Eigen3 is available" ON)

add_library(csc3_demo STATIC
    src/assembly_helper.cpp
)

target_include_directories(csc3_demo PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_compile_options(csc3_demo PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>
)

if(CSC3_DEMO_ENABLE_OPENMP)
    find_package(OpenMP QUIET COMPONENTS CXX)
    if(OpenMP_CXX_FOUND)
        target_link_libraries(csc3_demo PUBLIC OpenMP::OpenMP_CXX)
        target_compile_definitions(csc3_demo PUBLIC CSC3_DEMO_HAS_OPENMP=1)
    endif()
endif()

if(CSC3_DEMO_ENABLE_EIGEN)
    find_package(Eigen3 QUIET)
    if(Eigen3_FOUND)
        target_link_libraries(csc3_demo PUBLIC Eigen3::Eigen)
        target_compile_definitions(csc3_demo PUBLIC CSC3_DEMO_HAS_EIGEN=1)
    endif()
endif()

add_executable(csc3_demo_app
    src/main.cpp
)
target_link_libraries(csc3_demo_app PRIVATE csc3_demo)

add_executable(csc3_demo_tests
    tests/assembly_helper_tests.cpp
)
target_link_libraries(csc3_demo_tests PRIVATE csc3_demo)

enable_testing()
add_test(NAME Csc3DemoTests COMMAND csc3_demo_tests)
