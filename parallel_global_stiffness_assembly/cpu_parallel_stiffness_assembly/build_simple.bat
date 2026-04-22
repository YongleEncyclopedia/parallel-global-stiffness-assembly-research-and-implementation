@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================================
echo   GPU Parallel Stiffness Assembly - Simple Build
echo ========================================================
echo.

cd /d "%~dp0"

REM Check if already in VS environment
where cl >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Please run this script from VS Developer Command Prompt
    echo        Search for "x64 Native Tools Command Prompt for VS 2022"
    pause
    exit /b 1
)
echo [OK] cl.exe found

where nvcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] nvcc not in PATH, adding CUDA...
    set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
    set "PATH=!CUDA_PATH!\bin;!PATH!"
    where nvcc >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo ERROR: NVCC not found. Please install CUDA Toolkit.
        pause
        exit /b 1
    )
)
echo [OK] nvcc found

where cmake >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: CMake not found. Please install CMake.
    pause
    exit /b 1
)
echo [OK] cmake found

echo.
echo [1/2] Configuring with CMake...
if exist build rmdir /s /q build
mkdir build
cd build

cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: CMake configuration failed!
    cd ..
    pause
    exit /b 1
)

echo.
echo [2/2] Building with NMake...
nmake
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Build failed!
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================================
echo   Build completed successfully!
echo ========================================================
echo.

if exist build\bin\benchmark_assembly.exe (
    echo Executable: build\bin\benchmark_assembly.exe
) else (
    echo Searching for executable...
    dir /s /b build\*.exe 2>nul
)

echo.
pause
