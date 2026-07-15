cmake_minimum_required(VERSION 3.21)

project(Csc3DemoExternalConsumer LANGUAGES CXX)

include(CTest)
set(csc3_demo_parent_build_testing "${BUILD_TESTING}")

get_filename_component(
    CSC3_DEMO_SOURCE_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../.."
    ABSOLUTE
)
add_subdirectory(
    "${CSC3_DEMO_SOURCE_DIR}"
    "${CMAKE_BINARY_DIR}/csc3-demo"
    EXCLUDE_FROM_ALL
)
if(NOT BUILD_TESTING STREQUAL csc3_demo_parent_build_testing)
    message(FATAL_ERROR "The demo subproject changed parent BUILD_TESTING")
endif()
if(TARGET csc3_demo_tests OR TARGET csc3_demo_benchmark_engine_tests)
    message(FATAL_ERROR "The demo subproject unexpectedly enabled internal tests")
endif()

add_executable(csc3_demo_external_consumer main.cpp)
target_link_libraries(csc3_demo_external_consumer PRIVATE csc3_demo::csc3_demo)

if(BUILD_TESTING)
    add_test(NAME Csc3DemoExternalConsumer COMMAND csc3_demo_external_consumer)
endif()
