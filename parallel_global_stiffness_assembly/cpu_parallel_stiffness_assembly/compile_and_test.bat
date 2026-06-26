@echo off
REM 中文维护说明：
REM 本脚本用于独立编译并运行根部 CUDA 验证程序 `minimal_verify.cu`，
REM 因此和该独立验证源码一起保留在 CPU 主线根部。它属于历史 GPU/CUDA
REM 验证资产，不是当前 CPU 主线构建入口。
setlocal

REM 设置 MSVC 环境
set "VSINSTALLDIR=C:\Program Files\Microsoft Visual Studio\18\Community"
set "VCINSTALLDIR=%VSINSTALLDIR%\VC"
set "MSVC_VER=14.50.35717"
set "MSVC_BIN=%VCINSTALLDIR%\Tools\MSVC\%MSVC_VER%\bin\Hostx64\x64"

REM 添加到 PATH
set "PATH=%MSVC_BIN%;%PATH%"
set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin;%PATH%"

REM 设置 include 和 lib
set "INCLUDE=%VCINSTALLDIR%\Tools\MSVC\%MSVC_VER%\include;%INCLUDE%"
set "LIB=%VCINSTALLDIR%\Tools\MSVC\%MSVC_VER%\lib\x64;%LIB%"

echo Compiling minimal_verify.cu...
nvcc -O2 -arch=sm_86 -o minimal_verify.exe minimal_verify.cu

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Compilation successful! Running test...
    echo.
    minimal_verify.exe
) else (
    echo Compilation failed!
    exit /b 1
)
