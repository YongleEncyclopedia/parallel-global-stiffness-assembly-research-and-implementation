# CSC3 对称稀疏组装 Demo 的构建入口。
#
# 在本目录执行 `cmake --preset submission` 时，CMake 会读取本文件，
# 建立核心类库、示例程序、性能测试程序和测试用例。日常编译通常不需要修改本文件。
#
# 四条常用命令：
#   add_library(...)          定义一个库；
#   add_executable(...)       定义一个可执行程序；
#   target_link_libraries(...) 声明目标依赖的库；
#   add_test(...)             把程序登记为可由 CTest 运行的测试。

# 一、项目和 C++ 标准
cmake_minimum_required(VERSION 3.21)

project(Csc3SymmetricAssemblyDemo
    VERSION 0.2.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 所有生成物放到固定位置，避免不同编译器把程序散落到不同目录。
# Visual Studio 等多配置生成器还会产生 Debug、Release 等配置，下面的循环
# 让这些配置同样使用 build/<preset>/bin 和 build/<preset>/lib。
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

# 二、构建开关和依赖
# option(...) 定义可由命令行或 CMake preset 设置的 ON/OFF 开关。
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

# 核心类只提供 OpenMP 并行组装路径，没有静默退回串行的实现。
# 因此关闭 OpenMP 属于不受支持的配置，缺少 OpenMP 时也应在配置阶段报错。
if(NOT CSC3_DEMO_REQUIRE_OPENMP)
    message(FATAL_ERROR
        "CSC3_DEMO_REQUIRE_OPENMP=OFF is unsupported because this demo has no "
        "serial fallback. Install an OpenMP C++ runtime and configure with "
        "-DCSC3_DEMO_REQUIRE_OPENMP=ON."
    )
endif()

find_package(OpenMP REQUIRED COMPONENTS CXX)

# Demo 单独构建时启用 CTest；被其他工程通过 add_subdirectory(...) 引用时，
# 不主动改变上层工程的测试设置。
if(PROJECT_IS_TOP_LEVEL)
    include(CTest)
endif()

# 单独构建 Demo 时默认编译 C++ 测试；作为子目录使用时默认关闭，
# 避免把 Demo 自身的测试程序带进接收方工程。
set(csc3_demo_build_cpp_tests_default OFF)
if(PROJECT_IS_TOP_LEVEL AND BUILD_TESTING)
    set(csc3_demo_build_cpp_tests_default ON)
endif()
option(CSC3_DEMO_BUILD_CPP_TESTS
    "Build the standalone C++ test executables"
    ${csc3_demo_build_cpp_tests_default}
)
option(CSC3_DEMO_BUILD_PYTHON_TESTS
    "Run the Python tests for experiment scripts and report generation"
    OFF
)
if((CSC3_DEMO_BUILD_CPP_TESTS OR CSC3_DEMO_BUILD_PYTHON_TESTS) AND
   NOT BUILD_TESTING)
    message(FATAL_ERROR
        "CSC3_DEMO_BUILD_CPP_TESTS and CSC3_DEMO_BUILD_PYTHON_TESTS "
        "require BUILD_TESTING=ON."
    )
endif()

# Sanitizer 用于开发阶段检查越界访问和未定义行为。目前只在 Linux/macOS
# 的 GCC 或 Clang 环境中启用，Windows 的 MSVC 构建不走这条路径。
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

# 需要检查代码格式时，只检查这份明确的源码清单，不扫描构建目录或证据文件。
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

# 为各个目标统一设置编译器警告。MSVC 与 GCC/Clang 使用不同参数，
# CSC3_DEMO_WARNINGS_AS_ERRORS=ON 时再把警告提升为错误。
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

# 三、库和可执行程序
# csc3_demo 是交付给接收方使用的核心静态库，完整类实现在
# src/assembly_helper.cpp，公共接口在 include/csc3_demo/assembly_helper.h。
add_library(csc3_demo STATIC
    src/assembly_helper.cpp
)
add_library(csc3_demo::csc3_demo ALIAS csc3_demo)

# PUBLIC 表示使用 csc3_demo 的工程也会继承这些头文件路径、编译要求和依赖。
target_include_directories(csc3_demo PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_compile_features(csc3_demo PUBLIC cxx_std_17)
# 中文公共头文件必须在 Windows 默认代码页下可解析；设为 PUBLIC 后，
# 直接编译该头文件的外部 consumer 也会继承 /utf-8。
target_compile_options(csc3_demo PUBLIC
    "$<$<CXX_COMPILER_ID:MSVC>:/utf-8>"
)
target_link_libraries(csc3_demo PUBLIC OpenMP::OpenMP_CXX)
csc3_demo_enable_warnings(csc3_demo)

# 最小示例程序：演示公共接口的基本调用顺序。
add_executable(csc3_demo_app
    src/main.cpp
)
target_link_libraries(csc3_demo_app PRIVATE csc3_demo::csc3_demo)
csc3_demo_enable_warnings(csc3_demo_app)

# 性能和正确性验证所共用的辅助库，不属于接收方必须调用的公共接口。
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

# 命令行性能测试程序：读取算例、运行线程扫描并输出原始证据。
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

# 四、Python 脚本测试
# 这组测试检查实验脚本、证据复算和报告生成。普通源码编译不依赖 Python。
if(CSC3_DEMO_BUILD_PYTHON_TESTS)
    find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
endif()

# 五、C++ 测试程序
# 本节先把每项测试编译成可执行程序；下一节再用 add_test(...) 登记给 CTest。
if(CSC3_DEMO_BUILD_CPP_TESTS)
    # 核心类测试：输入校验、符号组装、数值组装和异常行为。
    add_executable(csc3_demo_tests
        tests/assembly_helper_tests.cpp
    )
    target_link_libraries(csc3_demo_tests PRIVATE csc3_demo::csc3_demo)
    csc3_demo_enable_warnings(csc3_demo_tests)

    # 接口使用测试：像外部调用方一样只通过公共头文件使用核心库。
    add_executable(csc3_demo_consumer
        tests/consumer/csc3_demo_consumer.cpp
    )
    target_link_libraries(csc3_demo_consumer PRIVATE csc3_demo::csc3_demo)
    csc3_demo_enable_warnings(csc3_demo_consumer)

    # 正确性测试：比较串行参考矩阵与并行组装矩阵的结构和数值。
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

    # 计时口径测试：确认各阶段耗时和总耗时字段的定义一致。
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
        csc3_demo_evidence
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_benchmark_timing_tests)

    # 性能测试引擎测试：检查线程、预热、重复测量和样本调度。
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

    # 证据读写测试：检查 CSV、JSON 和 manifest 的字段与数据。
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

    # 工程网格读取测试：检查 Abaqus INP 节点和 Tet4 单元解析。
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

    # WindHub 测试：检查工程网格性能命令的参数和结果约束。
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

    # 原子累加冲突测试：让多个线程反复写入相同矩阵位置，检查并发安全。
    add_executable(csc3_demo_atomic_contention_tests
        tests/atomic_contention_tests.cpp
    )
    target_link_libraries(csc3_demo_atomic_contention_tests PRIVATE
        csc3_demo::csc3_demo
    )
    csc3_demo_enable_warnings(csc3_demo_atomic_contention_tests)
endif()

# 六、登记 CTest 测试
# add_test(...) 后，使用者才能通过 `ctest --preset submission` 统一运行测试。
if(CSC3_DEMO_BUILD_CPP_TESTS)
    add_test(NAME Csc3DemoTests COMMAND csc3_demo_tests)
    add_test(NAME Csc3DemoConsumer COMMAND csc3_demo_consumer)
    add_test(NAME Csc3DemoCorrectness COMMAND csc3_demo_correctness_tests)
    add_test(NAME Csc3DemoBenchmarkTiming COMMAND csc3_demo_benchmark_timing_tests)
    add_test(NAME Csc3DemoBenchmarkEngine COMMAND csc3_demo_benchmark_engine_tests)
    add_test(NAME Csc3DemoBenchmarkIo COMMAND csc3_demo_benchmark_io_tests)
    add_test(NAME Csc3DemoInpCase COMMAND csc3_demo_inp_case_tests)
    add_test(NAME Csc3DemoWindHubBenchmark COMMAND csc3_demo_windhub_benchmark_tests)

    # 核心测试固定使用 2 个 OpenMP 线程，单项超过 180 秒即判为失败。
    set_tests_properties(
        Csc3DemoTests
        Csc3DemoConsumer
        Csc3DemoCorrectness
        Csc3DemoBenchmarkTiming
        Csc3DemoBenchmarkEngine
        Csc3DemoBenchmarkIo
        Csc3DemoInpCase
        Csc3DemoWindHubBenchmark
        PROPERTIES
        LABELS ci
        ENVIRONMENT "OMP_DYNAMIC=false;OMP_NUM_THREADS=2;OMP_THREAD_LIMIT=2"
        TIMEOUT 180
    )
endif()

# Python 测试检查实验 runner、报告输入和结果文件，运行时间上限为 600 秒。
if(CSC3_DEMO_BUILD_PYTHON_TESTS)
    add_test(
        NAME Csc3DemoPythonTests
        COMMAND
            ${Python3_EXECUTABLE} -m unittest discover
            -s ${CMAKE_CURRENT_SOURCE_DIR}/tests/python
            -p test_*.py
            -v
    )
    set_tests_properties(Csc3DemoPythonTests PROPERTIES
        LABELS ci
        ENVIRONMENT "OMP_DYNAMIC=false;OMP_NUM_THREADS=2;OMP_THREAD_LIMIT=2"
        TIMEOUT 600
    )
endif()

# 高冲突测试单独登记标签，CI 可以按标签重复运行它。
if(CSC3_DEMO_BUILD_CPP_TESTS)
    add_test(NAME Csc3DemoAtomicContention COMMAND csc3_demo_atomic_contention_tests)
    set_tests_properties(Csc3DemoAtomicContention PROPERTIES
        LABELS "ci;atomic-contention"
        ENVIRONMENT "OMP_DYNAMIC=false;OMP_NUM_THREADS=2;OMP_THREAD_LIMIT=2"
        TIMEOUT 180
    )
endif()
