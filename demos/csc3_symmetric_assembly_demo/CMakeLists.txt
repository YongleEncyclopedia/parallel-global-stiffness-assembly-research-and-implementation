cmake_minimum_required(VERSION 3.20)

project(Csc3SymmetricAssemblyDemo
    VERSION 0.1.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(OpenMP REQUIRED COMPONENTS CXX)

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
target_link_libraries(csc3_demo PUBLIC OpenMP::OpenMP_CXX)

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
