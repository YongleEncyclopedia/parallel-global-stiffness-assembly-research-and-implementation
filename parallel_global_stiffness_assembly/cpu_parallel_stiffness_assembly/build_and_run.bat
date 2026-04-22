@echo off
REM build_and_run.bat - 一键构建和运行脚本

echo ========================================================
echo   GPU Parallel Stiffness Matrix Assembly
echo   Build and Run Script
echo ========================================================
echo.

REM 检查必要工具
where cmake >nul 2>&1 || (
    echo ERROR: CMake not found. Please install CMake 3.25+
    pause
    exit /b 1
)

where nvcc >nul 2>&1 || (
    echo ERROR: NVCC not found. Please install CUDA Toolkit 13.1+
    pause
    exit /b 1
)

echo [Step 1/4] Creating build directory...
if not exist build mkdir build
cd build

echo [Step 2/4] Configuring CMake...
cmake .. -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo CMake configuration failed!
    pause
    exit /b 1
)

echo [Step 3/4] Building project...
cmake --build . --config Release
if %ERRORLEVEL% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo [Step 4/4] Running benchmark...
echo.
cd ..
if exist build\bin\Release\benchmark_assembly.exe (
    build\bin\Release\benchmark_assembly.exe 20 20 20 hex8
) else if exist build\bin\benchmark_assembly.exe (
    build\bin\benchmark_assembly.exe 20 20 20 hex8
) else (
    echo Executable not found!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   Build and benchmark completed!
echo   Results saved to: benchmark_results.csv
echo ========================================================
pause
