cmake_minimum_required(VERSION 3.21)

project(Csc3SymmetricAssemblyDemo
    VERSION 0.2.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
foreach(configuration IN LISTS CMAKE_CONFIGURATION_TYPES)
    string(TOUPPER "${configuration}" configuration_upper)
    set("CMAKE_RUNTIME_OUTPUT_DIRECTORY_${configuration_upper}"
        "${CMAKE_BINARY_DIR}/bin")
    set("CMAKE_LIBRARY_OUTPUT_DIRECTORY_${configuration_upper}"
        "${CMAKE_BINARY_DIR}/lib")
    set("CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${configuration_upper}"
        "${CMAKE_BINARY_DIR}/lib")
endforeach()

option(CSC3_DEMO_REQUIRE_OPENMP
    "Require OpenMP for the supported parallel-only implementation"
    ON
)
option(CSC3_DEMO_WARNINGS_AS_ERRORS
    "Treat compiler warnings as errors"
    OFF
)
option(CSC3_DEMO_ENABLE_SANITIZERS
    "Enable AddressSanitizer and UndefinedBehaviorSanitizer"
    OFF
)
option(CSC3_DEMO_ENABLE_FORMAT_CHECK
    "Add the clang-format verification target"
    OFF
)
set(CSC3_DEMO_CLANG_FORMAT_EXECUTABLE "" CACHE FILEPATH
    "Optional explicit path to clang-format"
)

if(NOT CSC3_DEMO_REQUIRE_OPENMP)
    message(FATAL_ERROR
        "CSC3_DEMO_REQUIRE_OPENMP=OFF is unsupported because this demo has no "
        "serial fallback. Install an OpenMP C++ runtime and configure with "
        "-DCSC3_DEMO_REQUIRE_OPENMP=ON."
    )
endif()

find_package(OpenMP REQUIRED COMPONENTS CXX)
include(CTest)

if(CSC3_DEMO_ENABLE_SANITIZERS)
    if(MSVC OR NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        message(FATAL_ERROR
            "CSC3_DEMO_ENABLE_SANITIZERS requires a GCC- or Clang-compatible "
            "compiler on Linux or macOS."
        )
    endif()
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
endif()

set(CSC3_DEMO_FORMAT_FILES
    include/csc3_demo/assembly_helper.h
    src/assembly_helper.cpp
    src/main.cpp
    tests/assembly_helper_tests.cpp
    tests/atomic_contention_tests.cpp
    tests/benchmark_engine_tests.cpp
    tests/benchmark_io_tests.cpp
    tests/benchmark_timing_tests.cpp
    tests/consumer/csc3_demo_consumer.cpp
    tests/correctness_validation_tests.cpp
    tests/external_consumer/main.cpp
    tests/inp_case_tests.cpp
    tests/windhub_benchmark_tests.cpp
    tools/include/csc3_demo_tools/benchmark.h
    tools/include/csc3_demo_tools/evidence.h
    tools/src/benchmark.cpp
    tools/src/benchmark_io.cpp
    tools/src/benchmark_main.cpp
    tools/src/generated_cases.cpp
    tools/src/inp_case.cpp
    tools/src/validation.cpp
)
list(TRANSFORM CSC3_DEMO_FORMAT_FILES PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/")

if(CSC3_DEMO_ENABLE_FORMAT_CHECK)
    if(CSC3_DEMO_CLANG_FORMAT_EXECUTABLE)
        set(csc3_demo_clang_format "${CSC3_DEMO_CLANG_FORMAT_EXECUTABLE}")
    else()
        find_program(csc3_demo_clang_format
            NAMES clang-format clang-format-18
            REQUIRED
        )
    endif()
    add_custom_target(csc3_demo_format_check
        COMMAND
            "${csc3_demo_clang_format}"
            --dry-run
            --Werror
            --style=file
            ${CSC3_DEMO_FORMAT_FILES}
        COMMENT "Checking CSC3 demo C++ formatting"
        VERBATIM
    )
endif()

function(csc3_demo_enable_warnings target_name)
    if(MSVC)
        target_compile_options(${target_name} PRIVATE /W4)
        if(CSC3_DEMO_WARNINGS_AS_ERRORS)
            target_compile_options(${target_name} PRIVATE /WX)
        endif()
    else()
        target_compile_options(${target_name} PRIVATE -Wall -Wextra -Wpedantic)
        if(CSC3_DEMO_WARNINGS_AS_ERRORS)
            target_compile_options(${target_name} PRIVATE -Werror)
        endif()
    endif()
endfunction()

add_library(csc3_demo STATIC
    src/assembly_helper.cpp
)
add_library(csc3_demo::csc3_demo ALIAS csc3_demo)

target_include_directories(csc3_demo PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_compile_features(csc3_demo PUBLIC cxx_std_17)
target_link_libraries(csc3_demo PUBLIC OpenMP::OpenMP_CXX)
csc3_demo_enable_warnings(csc3_demo)

add_executable(csc3_demo_app
    src/main.cpp
)
target_link_libraries(csc3_demo_app PRIVATE csc3_demo::csc3_demo)
csc3_demo_enable_warnings(csc3_demo_app)

add_library(csc3_demo_evidence STATIC
    tools/src/benchmark.cpp
    tools/src/benchmark_io.cpp
    tools/src/generated_cases.cpp
    tools/src/inp_case.cpp
    tools/src/validation.cpp
)
target_include_directories(csc3_demo_evidence PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
)
target_link_libraries(csc3_demo_evidence PRIVATE csc3_demo::csc3_demo)
target_compile_features(csc3_demo_evidence PRIVATE cxx_std_17)
csc3_demo_enable_warnings(csc3_demo_evidence)

add_executable(csc3_demo_benchmark
    tools/src/benchmark_main.cpp
)
target_include_directories(csc3_demo_benchmark PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
)
target_link_libraries(csc3_demo_benchmark PRIVATE
    csc3_demo_evidence
    csc3_demo::csc3_demo
)
target_compile_features(csc3_demo_benchmark PRIVATE cxx_std_17)
csc3_demo_enable_warnings(csc3_demo_benchmark)

if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    set(CSC3_DEMO_PYTHON_TEST_REQUIREMENTS
        "${CMAKE_CURRENT_SOURCE_DIR}/requirements-test.txt"
    )
    execute_process(
        COMMAND
            "${Python3_EXECUTABLE}" -c [=[
from importlib.metadata import version
from jsonschema import Draft202012Validator

raw_version = version("jsonschema")
major, minor = (int(part) for part in raw_version.split(".")[:2])
if not ((major, minor) >= (4, 23) and major < 5):
    raise RuntimeError(
        f"jsonschema {raw_version} does not satisfy jsonschema>=4.23,<5"
    )
assert Draft202012Validator.META_SCHEMA["$schema"]
]=]
        RESULT_VARIABLE csc3_demo_python_dependency_status
        ERROR_VARIABLE csc3_demo_python_dependency_error
    )
    if(NOT csc3_demo_python_dependency_status EQUAL 0)
        message(FATAL_ERROR
            "CSC3 demo tests require jsonschema>=4.23,<5 for Draft 2020-12 "
            "acceptance-record validation. Install the declared dependency "
            "with '${Python3_EXECUTABLE} -m pip install -r "
            "${CSC3_DEMO_PYTHON_TEST_REQUIREMENTS}'. Python reported:\n"
            "${csc3_demo_python_dependency_error}"
        )
    endif()

    add_executable(csc3_demo_tests
        tests/assembly_helper_tests.cpp
    )
    target_link_libraries(csc3_demo_tests PRIVATE csc3_demo::csc3_demo)
    csc3_demo_enable_warnings(csc3_demo_tests)

    add_executable(csc3_demo_consumer
        tests/consumer/csc3_demo_consumer.cpp
    )
    target_link_libraries(csc3_demo_consumer PRIVATE csc3_demo::csc3_demo)
    csc3_demo_enable_warnings(csc3_demo_consumer)

    add_executable(csc3_demo_correctness_tests
        tests/correctness_validation_tests.cpp
    )
    target_include_directories(csc3_demo_correctness_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_link_libraries(csc3_demo_correctness_tests PRIVATE
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_correctness_tests)

    add_executable(csc3_demo_benchmark_timing_tests
        tests/benchmark_timing_tests.cpp
    )
    target_include_directories(csc3_demo_benchmark_timing_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_compile_definitions(csc3_demo_benchmark_timing_tests PRIVATE
        "CSC3_DEMO_PUBLIC_HEADER_PATH=\"${CMAKE_CURRENT_SOURCE_DIR}/include/csc3_demo/assembly_helper.h\""
    )
    target_link_libraries(csc3_demo_benchmark_timing_tests PRIVATE
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_benchmark_timing_tests)

    add_executable(csc3_demo_benchmark_engine_tests
        tests/benchmark_engine_tests.cpp
    )
    target_include_directories(csc3_demo_benchmark_engine_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_compile_definitions(csc3_demo_benchmark_engine_tests PRIVATE
        "CSC3_DEMO_PUBLIC_HEADER_PATH=\"${CMAKE_CURRENT_SOURCE_DIR}/include/csc3_demo/assembly_helper.h\""
    )
    target_link_libraries(csc3_demo_benchmark_engine_tests PRIVATE
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_benchmark_engine_tests)

    add_executable(csc3_demo_benchmark_io_tests
        tests/benchmark_io_tests.cpp
    )
    target_include_directories(csc3_demo_benchmark_io_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_link_libraries(csc3_demo_benchmark_io_tests PRIVATE
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_benchmark_io_tests)

    add_executable(csc3_demo_inp_case_tests
        tests/inp_case_tests.cpp
    )
    target_include_directories(csc3_demo_inp_case_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_link_libraries(csc3_demo_inp_case_tests PRIVATE
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_inp_case_tests)

    add_executable(csc3_demo_windhub_benchmark_tests
        tests/windhub_benchmark_tests.cpp
    )
    target_include_directories(csc3_demo_windhub_benchmark_tests PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/tools/include
    )
    target_link_libraries(csc3_demo_windhub_benchmark_tests PRIVATE
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_windhub_benchmark_tests)

    add_executable(csc3_demo_atomic_contention_tests
        tests/atomic_contention_tests.cpp
    )
    target_link_libraries(csc3_demo_atomic_contention_tests PRIVATE
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_atomic_contention_tests)

    add_test(NAME Csc3DemoTests COMMAND csc3_demo_tests)
    add_test(NAME Csc3DemoConsumer COMMAND csc3_demo_consumer)
    add_test(NAME Csc3DemoCorrectness COMMAND csc3_demo_correctness_tests)
    add_test(NAME Csc3DemoBenchmarkTiming COMMAND csc3_demo_benchmark_timing_tests)
    add_test(NAME Csc3DemoBenchmarkEngine COMMAND csc3_demo_benchmark_engine_tests)
    add_test(NAME Csc3DemoBenchmarkIo COMMAND csc3_demo_benchmark_io_tests)
    add_test(NAME Csc3DemoInpCase COMMAND csc3_demo_inp_case_tests)
    add_test(NAME Csc3DemoWindHubBenchmark COMMAND csc3_demo_windhub_benchmark_tests)
    add_test(
        NAME Csc3DemoBenchmarkRunner
        COMMAND
            ${Python3_EXECUTABLE} -m unittest discover
            -s ${CMAKE_CURRENT_SOURCE_DIR}/tests/python
            -p test_*.py
            -v
    )
    add_test(NAME Csc3DemoAtomicContention COMMAND csc3_demo_atomic_contention_tests)
    set_tests_properties(
        Csc3DemoTests
        Csc3DemoConsumer
        Csc3DemoCorrectness
        Csc3DemoBenchmarkTiming
        Csc3DemoBenchmarkEngine
        Csc3DemoBenchmarkIo
        Csc3DemoInpCase
        Csc3DemoWindHubBenchmark
        Csc3DemoBenchmarkRunner
        PROPERTIES
        LABELS ci
        ENVIRONMENT "OMP_DYNAMIC=false;OMP_NUM_THREADS=2;OMP_THREAD_LIMIT=2"
        TIMEOUT 180
    )
    set_tests_properties(Csc3DemoAtomicContention PROPERTIES
        LABELS "ci;atomic-contention"
        ENVIRONMENT "OMP_DYNAMIC=false;OMP_NUM_THREADS=2;OMP_THREAD_LIMIT=2"
        TIMEOUT 180
    )
endif()
