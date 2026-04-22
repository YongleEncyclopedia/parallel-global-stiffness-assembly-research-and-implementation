@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================================
echo   GPU Parallel Stiffness Assembly - Quick Build
echo ========================================================
echo.

REM Try VS 2026 first
set "VS_PATH=C:\Program Files\Microsoft Visual Studio\18\Community"
if not exist "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" (
    REM Try VS 2022
    set "VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community"
    if not exist "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" (
        set "VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\Enterprise"
        if not exist "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" (
            echo ERROR: Visual Studio not found
            exit /b 1
        )
    )
)

echo [1/4] Setting up Visual Studio environment...
call "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to setup VS environment
    exit /b 1
)
echo       Done.

REM Setup CUDA
set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
set "PATH=%CUDA_PATH%\bin;%PATH%"

echo [2/4] Verifying tools...
where cl >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: MSVC cl.exe not found
    exit /b 1
)
echo       - cl.exe: OK

where nvcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: NVCC not found
    exit /b 1
)
echo       - nvcc: OK

where cmake >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: CMake not found
    exit /b 1
)
echo       - cmake: OK

echo.
echo [3/4] Building minimal verification test...
cd /d "%~dp0"

REM Compile minimal verify
nvcc -O2 -arch=sm_120 -allow-unsupported-compiler -o minimal_verify_build.exe minimal_verify_ascii.cu
if %ERRORLEVEL% neq 0 (
    nvcc -O2 -arch=sm_86 -allow-unsupported-compiler -o minimal_verify_build.exe minimal_verify_ascii.cu
    if %ERRORLEVEL% neq 0 (
        echo WARNING: minimal_verify compilation failed
    )
)

if exist minimal_verify_build.exe (
    echo.
    echo Running minimal verification...
    minimal_verify_build.exe
    echo.
)

echo [4/4] Building main project with CMake...
if exist build rmdir /s /q build
mkdir build
cd build

cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl
if %ERRORLEVEL% neq 0 (
    echo CMake configuration failed!
    cd ..
    exit /b 1
)

nmake
if %ERRORLEVEL% neq 0 (
    echo Build failed!
    cd ..
    exit /b 1
)

echo.
echo ========================================================
echo   Build completed!
echo ========================================================
echo.

cd ..

REM Find and run benchmark
if exist build\bin\benchmark_assembly.exe (
    set "BENCH=build\bin\benchmark_assembly.exe"
) else if exist build\benchmark_assembly.exe (
    set "BENCH=build\benchmark_assembly.exe"
) else (
    echo Executable not found
    dir /s /b build\*.exe
    exit /b 1
)

echo Running benchmarks...
echo.
echo Test 1: Small (10x10x10 = 1000 elements)
%BENCH% 10 10 10 hex8

echo.
echo Test 2: Medium (20x20x20 = 8000 elements)
%BENCH% 20 20 20 hex8

echo.
echo Test 3: Large (40x40x40 = 64000 elements)
%BENCH% 40 40 40 hex8

echo.
echo ========================================================
echo   Tests completed! Check benchmark_results.csv
echo ========================================================

pause
