@echo off
REM build_now.bat - 在 VS 开发者环境中构建项目

echo ========================================================
echo   GPU Parallel Stiffness Assembly - Build Script
echo ========================================================

REM 设置 VS 2026 环境
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if %ERRORLEVEL% neq 0 (
    REM 尝试 VS 2022
    call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Cannot find Visual Studio environment
        exit /b 1
    )
)

REM 设置 CUDA
set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
set "PATH=%CUDA_PATH%\bin;%PATH%"

echo.
echo Checking tools...
where cl >nul 2>&1 && echo   - MSVC cl.exe: OK
where nvcc >nul 2>&1 && echo   - NVCC: OK
where cmake >nul 2>&1 && echo   - CMake: OK

echo.
echo Configuring CMake...
cd /d "%~dp0"
if exist build rmdir /s /q build
mkdir build
cd build

cmake .. -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl
if %ERRORLEVEL% neq 0 (
    echo CMake configuration failed!
    exit /b 1
)

echo.
echo Building...
cmake --build . --config Release --parallel
if %ERRORLEVEL% neq 0 (
    echo Build failed!
    exit /b 1
)

echo.
echo ========================================================
echo   Build completed successfully!
echo ========================================================

REM 运行测试
echo.
echo Running benchmark test...
cd ..
if exist build\bin\benchmark_assembly.exe (
    build\bin\benchmark_assembly.exe 10 10 10 hex8
    build\bin\benchmark_assembly.exe 20 20 20 hex8
    build\bin\benchmark_assembly.exe 40 40 40 hex8
) else (
    echo Executable not found at expected location
    dir /s build\*.exe 2>nul
)

pause
