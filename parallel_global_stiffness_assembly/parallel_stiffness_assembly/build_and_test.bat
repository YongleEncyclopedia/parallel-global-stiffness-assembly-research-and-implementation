@echo off
REM 自动配置、编译和测试脚本

echo ========================================
echo GPU 并行刚度矩阵组装 - 自动构建测试
echo ========================================
echo.

REM 设置 Visual Studio 环境
echo [1/5] 配置 Visual Studio 环境...
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
if errorlevel 1 (
    echo 错误: 无法配置 VS 环境
    exit /b 1
)
echo ✓ VS 环境配置完成
echo.

REM 清理旧构建
echo [2/5] 清理旧构建目录...
if exist build rmdir /s /q build
mkdir build
cd build
echo ✓ 构建目录已准备
echo.

REM 配置 CMake
echo [3/5] 配置 CMake...
cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo 错误: CMake 配置失败
    cd ..
    exit /b 1
)
echo ✓ CMake 配置成功
echo.

REM 编译
echo [4/5] 编译项目...
nmake
if errorlevel 1 (
    echo 错误: 编译失败
    cd ..
    exit /b 1
)
echo ✓ 编译成功
echo.

REM 运行测试
echo [5/5] 运行基准测试...
echo 测试网格: 30x30x30 (约 48000 单元)
cd ..
if exist bin\benchmark.exe (
    bin\benchmark.exe 30 30 30
) else (
    .\build\benchmark.exe 30 30 30
)
echo.

REM 显示结果
echo ========================================
echo 测试结果汇总
echo ========================================
if exist benchmark_results.csv (
    type benchmark_results.csv
) else if exist build\benchmark_results.csv (
    type build\benchmark_results.csv
) else (
    echo 警告: 未找到结果文件
)
echo.
echo ========================================
echo 构建和测试完成！
echo ========================================
