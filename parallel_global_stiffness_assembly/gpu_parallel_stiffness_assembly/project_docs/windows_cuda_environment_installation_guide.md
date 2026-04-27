# GPU并行刚度矩阵组装项目 - 环境安装指南

**系统**: Windows
**GPU**: NVIDIA RTX 5080 (Driver 591.86, 支持 CUDA 13.1)

---

## 1. 必需组件安装清单

| 组件 | 当前状态 | 要求版本 | 安装方式 |
|------|---------|---------|---------|
| CUDA Toolkit | ❌ 未安装 | 13.1+ | 官方安装包 |
| CMake | ❌ 未安装 | 3.25+ | winget 或官网 |
| Python | ⚠️ Store版本 | 3.8+ | 推荐官网版本 |
| Visual Studio | 待确认 | 2022 | 社区版免费 |

---

## 2. CUDA Toolkit 13.1 安装

### 步骤1: 下载CUDA Toolkit

**下载地址**: https://developer.nvidia.com/cuda-13-1-0-download-archive

选择:
- Operating System: Windows
- Architecture: x86_64
- Version: 11 (或您的Windows版本)
- Installer Type: exe (local) [推荐]

### 步骤2: 安装CUDA

1. 运行下载的安装程序
2. 选择 **Custom Installation**
3. 确保勾选以下组件:
   - [x] CUDA Runtime
   - [x] CUDA Development
   - [x] CUDA Documentation
   - [x] CUDA Visual Studio Integration
   - [x] Nsight Compute (性能分析工具)
4. 完成安装

### 步骤3: 验证安装

打开新的命令行窗口，执行:
```cmd
nvcc --version
```

预期输出:
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2024 NVIDIA Corporation
Built on ...
Cuda compilation tools, release 13.1, V13.1.xxx
```

### 步骤4: 配置环境变量（通常自动配置）

确认以下路径已添加到 PATH:
- `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin`
- `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\libnvvp`

---

## 3. CMake 安装

### 方式1: 使用 winget（推荐）

```cmd
winget install Kitware.CMake
```

### 方式2: 官网下载

**下载地址**: https://cmake.org/download/

选择 **Windows x64 Installer (.msi)**

安装时勾选 **Add CMake to the system PATH for all users**

### 验证安装

```cmd
cmake --version
```

预期输出: `cmake version 3.28.x` 或更高

---

## 4. Visual Studio 2022 安装

### 下载地址

https://visualstudio.microsoft.com/downloads/

选择 **Community** 版本（免费）

### 安装组件

在安装程序中选择:
- [x] **Desktop development with C++**
  - [x] MSVC v143 - VS 2022 C++ x64/x86 build tools
  - [x] Windows 11 SDK
  - [x] C++ CMake tools for Windows

---

## 5. Python 环境配置

### 方式1: 使用现有 Python（如果已安装 Anaconda/Miniconda）

```cmd
# 检查conda
conda --version

# 创建项目环境
conda create -n fem_gpu python=3.10
conda activate fem_gpu

# 安装依赖
pip install numpy matplotlib pandas scipy
```

### 方式2: 安装官方 Python

**下载地址**: https://www.python.org/downloads/

安装时勾选 **Add Python to PATH**

然后安装依赖:
```cmd
pip install numpy matplotlib pandas scipy
```

### 验证 Python 环境

```cmd
python -c "import numpy; import matplotlib; import pandas; import scipy; print('All packages OK')"
```

---

## 6. 可选: vcpkg 包管理器

vcpkg 可以方便地安装 C++ 依赖（Eigen3, fmt, spdlog, gtest）

### 安装 vcpkg

```cmd
cd C:\
git clone https://github.com/microsoft/vcpkg
cd vcpkg
.\bootstrap-vcpkg.bat
```

### 安装项目依赖

```cmd
.\vcpkg install eigen3:x64-windows fmt:x64-windows spdlog:x64-windows gtest:x64-windows
```

### 配置环境变量

```cmd
setx VCPKG_ROOT "C:\vcpkg"
```

---

## 7. 环境验证脚本

安装完成后，运行以下命令验证所有组件:

```cmd
@echo off
echo === 环境检查 ===
echo.
echo [CUDA Toolkit]
nvcc --version 2>nul || echo CUDA NOT FOUND
echo.
echo [CMake]
cmake --version 2>nul || echo CMake NOT FOUND
echo.
echo [Visual Studio]
where cl 2>nul || echo MSVC NOT FOUND (请从Developer Command Prompt运行)
echo.
echo [Python]
python --version 2>nul || echo Python NOT FOUND
echo.
echo [Python Packages]
python -c "import numpy, matplotlib, pandas, scipy; print('All packages OK')" 2>nul || echo Python packages missing
echo.
echo [GPU]
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>nul || echo GPU NOT FOUND
echo.
echo === 检查完成 ===
pause
```

将以上内容保存为 `check_env.bat` 并运行

---

## 8. 安装后操作

环境安装完成后，请回复 **"环境已安装"**，我将继续执行项目框架搭建。

---

## 常见问题

### Q: nvcc 找不到

**A**: 重启命令行窗口，或手动添加 CUDA bin 目录到 PATH

### Q: CMake 找不到 CUDA

**A**: 确保使用 **x64 Native Tools Command Prompt for VS 2022** 或设置 `CMAKE_CUDA_COMPILER` 变量

### Q: Python 包安装失败

**A**: 尝试使用国内镜像:
```cmd
pip install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
```
