cmake_minimum_required(VERSION 3.21)

project(Csc3DemoExternalConsumer LANGUAGES CXX)

get_filename_component(
    CSC3_DEMO_SOURCE_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../.."
    ABSOLUTE
)
set(BUILD_TESTING OFF CACHE BOOL "Do not build the demo's internal tests" FORCE)
add_subdirectory(
    "${CSC3_DEMO_SOURCE_DIR}"
    "${CMAKE_BINARY_DIR}/csc3-demo"
    EXCLUDE_FROM_ALL
)

add_executable(csc3_demo_external_consumer main.cpp)
target_link_libraries(csc3_demo_external_consumer PRIVATE csc3_demo::csc3_demo)

enable_testing()
add_test(NAME Csc3DemoExternalConsumer COMMAND csc3_demo_external_consumer)
