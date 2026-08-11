cmake_minimum_required(VERSION 3.21)

# 这个小工程放在 Demo 的主构建之外，模拟研发把源码作为子目录接入自己的项目。
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
# 接入库时不能悄悄修改上层工程的 BUILD_TESTING，也不应编译 Demo 自己的测试程序。
if(NOT BUILD_TESTING STREQUAL csc3_demo_parent_build_testing)
    message(FATAL_ERROR "The demo subproject changed parent BUILD_TESTING")
endif()
if(TARGET csc3_demo_tests OR TARGET csc3_demo_benchmark_engine_tests)
    message(FATAL_ERROR "The demo subproject unexpectedly enabled internal tests")
endif()

add_executable(csc3_demo_external_consumer main.cpp)
# 接收方只依赖这个带命名空间的 target，不需要知道库内部文件列表。
target_link_libraries(csc3_demo_external_consumer PRIVATE csc3_demo::csc3_demo)

if(BUILD_TESTING)
    add_test(NAME Csc3DemoExternalConsumer COMMAND csc3_demo_external_consumer)
endif()
