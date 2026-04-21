@echo off
REM configure_and_build.bat - 使用 VS 2026 + CUDA 13.1 编译项目

echo ========================================================
echo   GPU Parallel Stiffness Matrix Assembly
echo   Configure and Build Script (VS 2026 + CUDA 13.1)
echo ========================================================
echo.

REM 设置 Visual Studio 环境
echo [Step 1/4] Setting up Visual Studio 2026 environment...
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to set up Visual Studio environment
    exit /b 1
)

REM 添加 CUDA 到 PATH
set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin;%PATH%"
set "PATH=C:\Program Files\CMake\bin;%PATH%"

REM 验证工具
echo.
echo [Step 2/4] Verifying tools...
cl 2>&1 | findstr "Microsoft" > nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: MSVC compiler not found
    exit /b 1
)
echo   - MSVC: OK

nvcc --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: NVCC not found
    exit /b 1
)
echo   - NVCC: OK

cmake --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: CMake not found
    exit /b 1
)
echo   - CMake: OK

REM 创建 build 目录
echo.
echo [Step 3/4] Configuring CMake...
if not exist build mkdir build
cd build

cmake .. -G "Visual Studio 18 2026" -A x64 -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo ERROR: CMake configuration failed
    cd ..
    exit /b 1
)

REM 编译
echo.
echo [Step 4/4] Building project...
cmake --build . --config Release --parallel
if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed
    cd ..
    exit /b 1
)

cd ..

echo.
echo ========================================================
echo   Build completed successfully!
echo   Executables: build\bin\Release\
echo ========================================================
echo.
