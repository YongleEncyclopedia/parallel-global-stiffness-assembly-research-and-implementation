cmake_minimum_required(VERSION 3.20)

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

if(NOT CSC3_DEMO_REQUIRE_OPENMP)
    message(FATAL_ERROR
        "CSC3_DEMO_REQUIRE_OPENMP=OFF is unsupported because this demo has no "
        "serial fallback. Install an OpenMP C++ runtime and configure with "
        "-DCSC3_DEMO_REQUIRE_OPENMP=ON."
    )
endif()

find_package(OpenMP REQUIRED COMPONENTS CXX)
include(CTest)

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
target_link_libraries(csc3_demo PUBLIC OpenMP::OpenMP_CXX)
csc3_demo_enable_warnings(csc3_demo)

add_executable(csc3_demo_app
    src/main.cpp
)
target_link_libraries(csc3_demo_app PRIVATE csc3_demo::csc3_demo)
csc3_demo_enable_warnings(csc3_demo_app)

if(BUILD_TESTING)
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

    add_test(NAME Csc3DemoTests COMMAND csc3_demo_tests)
    add_test(NAME Csc3DemoConsumer COMMAND csc3_demo_consumer)
    set_tests_properties(Csc3DemoTests Csc3DemoConsumer PROPERTIES
        LABELS ci
        TIMEOUT 180
    )
endif()
