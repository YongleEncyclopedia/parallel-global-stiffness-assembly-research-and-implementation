cmake_minimum_required(VERSION 3.20)

project(CpuParallelStiffnessAssembly
    VERSION 2.0.0
    LANGUAGES CXX
    DESCRIPTION "CPU parallel global stiffness matrix assembly benchmark"
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_TESTS "Build tests" ON)
option(BUILD_BENCHMARKS "Build benchmark executable" ON)
option(PGSA_ENABLE_OPENMP "Enable OpenMP CPU parallel backends" ON)
option(PGSA_WARNINGS_AS_ERRORS "Treat warnings as errors" OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

add_library(fem_core STATIC
    src/core/mesh.cpp
    src/core/csr_matrix.cpp
    src/core/dof_map.cpp
    src/core/platform.cpp
)

target_include_directories(fem_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

add_library(fem_assembly STATIC
    src/assembly/assembly_options.cpp
    src/assembly/assembly_plan.cpp
    src/assembly/element_kernels.cpp
    src/assembly/symbolic_numeric_eval.cpp
    src/assembly/assembler_factory.cpp
    src/backends/cpu/cpu_assembler_base.cpp
    src/backends/cpu/serial_assembler.cpp
    src/backends/cpu/atomic_assembler.cpp
    src/backends/cpu/private_csr_assembler.cpp
    src/backends/cpu/coo_sort_reduce_assembler.cpp
    src/backends/cpu/graph_coloring_assembler.cpp
    src/backends/cpu/row_owner_assembler.cpp
)

target_include_directories(fem_assembly PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(fem_assembly PUBLIC fem_core)

if(PGSA_ENABLE_OPENMP)
    if(APPLE AND NOT DEFINED OpenMP_ROOT)
        foreach(_pgsa_openmp_root IN ITEMS /opt/homebrew/opt/libomp /usr/local/opt/libomp)
            if(EXISTS "${_pgsa_openmp_root}")
                set(OpenMP_ROOT "${_pgsa_openmp_root}" CACHE PATH
                    "Preferred OpenMP runtime location for AppleClang" FORCE)
                break()
            endif()
        endforeach()
    endif()

    find_package(OpenMP QUIET COMPONENTS CXX)
    if(OpenMP_CXX_FOUND)
        target_link_libraries(fem_core PUBLIC OpenMP::OpenMP_CXX)
        target_link_libraries(fem_assembly PUBLIC OpenMP::OpenMP_CXX)
        message(STATUS "OpenMP enabled for CPU assembly backends")
    else()
        message(WARNING "OpenMP requested but not found; CPU parallel backends will run as single-thread fallback")
    endif()
endif()

if(MSVC)
    target_compile_options(fem_core PRIVATE /W4)
    target_compile_options(fem_assembly PRIVATE /W4)
    if(PGSA_WARNINGS_AS_ERRORS)
        target_compile_options(fem_core PRIVATE /WX)
        target_compile_options(fem_assembly PRIVATE /WX)
    endif()
else()
    target_compile_options(fem_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(fem_assembly PRIVATE -Wall -Wextra -Wpedantic)
    if(PGSA_WARNINGS_AS_ERRORS)
        target_compile_options(fem_core PRIVATE -Werror)
        target_compile_options(fem_assembly PRIVATE -Werror)
    endif()
endif()

if(BUILD_BENCHMARKS)
    add_executable(benchmark_assembly apps/benchmark/main.cpp)
    target_link_libraries(benchmark_assembly PRIVATE fem_assembly)

    add_executable(symbolic_numeric_eval apps/symbolic_eval/main.cpp)
    target_link_libraries(symbolic_numeric_eval PRIVATE fem_assembly)
endif()

if(BUILD_TESTS)
    enable_testing()
    find_package(Python3 QUIET COMPONENTS Interpreter)
    add_executable(verify_results tests/correctness/verify_results.cpp)
    target_compile_definitions(verify_results PRIVATE
        PGSA_TEST_EXAMPLES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/examples")
    target_link_libraries(verify_results PRIVATE fem_assembly)
    add_test(NAME VerifyCpuAssemblers COMMAND verify_results)

    add_executable(verify_inp_parser tests/correctness/verify_inp_parser.cpp)
    target_compile_definitions(verify_inp_parser PRIVATE
        PGSA_TEST_EXAMPLES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/examples")
    target_link_libraries(verify_inp_parser PRIVATE fem_assembly)
    add_test(NAME VerifyInpParser COMMAND verify_inp_parser)

    add_executable(verify_symbolic_numeric_eval tests/correctness/verify_symbolic_numeric_eval.cpp)
    target_link_libraries(verify_symbolic_numeric_eval PRIVATE fem_assembly)
    add_test(NAME VerifySymbolicNumericEval COMMAND verify_symbolic_numeric_eval)

    add_executable(verify_thread_region tests/correctness/verify_thread_region.cpp)
    target_link_libraries(verify_thread_region PRIVATE fem_core)
    add_test(NAME VerifyThreadRegion COMMAND verify_thread_region)

    if(Python3_Interpreter_FOUND AND BUILD_BENCHMARKS)
        add_test(
            NAME VerifyBenchmarkSchema
            COMMAND
                ${Python3_EXECUTABLE}
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/correctness/verify_benchmark_schema.py
                $<TARGET_FILE:benchmark_assembly>
                ${CMAKE_CURRENT_BINARY_DIR}/schema-smoke
        )
        add_test(
            NAME VerifyCrossPlatformSchemaScripts
            COMMAND
                ${Python3_EXECUTABLE}
                -m unittest discover -s ${CMAKE_CURRENT_SOURCE_DIR}/tests/python -v
        )
    endif()
endif()

install(TARGETS fem_core fem_assembly
    EXPORT CpuParallelStiffnessAssemblyTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)

message(STATUS "")
message(STATUS "========== CPU Assembly Configuration ==========")
message(STATUS "Project: ${PROJECT_NAME} v${PROJECT_VERSION}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Build tests: ${BUILD_TESTS}")
message(STATUS "Build benchmarks: ${BUILD_BENCHMARKS}")
message(STATUS "OpenMP requested: ${PGSA_ENABLE_OPENMP}")
message(STATUS "===============================================")
message(STATUS "")
