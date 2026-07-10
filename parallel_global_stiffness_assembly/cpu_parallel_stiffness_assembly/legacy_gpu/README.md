# GPU 历史归档目录

## 状态

本目录保存 GPU-first 阶段的历史 CUDA 源码、独立验证程序和 Windows 构建脚本。它仅用于来源追溯，**不是当前开发入口、不是受支持构建目标，也不保证能够独立编译或运行**。

当前 CPU 主线仍位于上级目录，默认 CMake、CTest、benchmark 和实验脚本不得引用本目录。

## 内容

- `MANIFEST.sha256`：Issue #28 迁移前生成的确定性清单，记录 21 个原路径、归档路径与迁移前 SHA256；迁移保持这些文件的工作树字节不变。
- `src/backends/cuda/`、`include/backends/cuda/`：早期 CUDA assembler 实现与声明。
- `include/core/device_soa.h`：从活动 `include/core/soa.h` 迁出的两个设备端 SoA 声明；此提取文件不属于字节不变的 `git mv` 清单。
- `standalone_cuda_verification/`：根目录原有的 3 个独立 `.cu` 验证程序。
- `scripts/`：根目录原有的 6 个 `.bat` 与 1 个 `.ps1` 历史脚本。
- `cmake/CudaConfig.cmake`：已退出活动 CMake 的 CUDA 历史配置。

正式 `results/` 内的历史 GPU 绘图脚本仍属于结果证据，没有移动到这里。

## 维护约束

- 不从默认构建或测试重新接入这里的文件。
- 不运行这里的旧构建脚本作为当前验证证据。
- 若重新启动 GPU 研究，应建立独立 Issue、分支和受支持构建设计，不能直接恢复本目录为主线。

Issue #28 同时证明活动 CMake 未引用 `cmake/CompilerFlags.cmake` 与 `cmake/Dependencies.cmake`，因此只删除了这两个未使用模块；`cmake/README.md` 随活动 `cmake/` 目录清空而有意删除。一次性启发式脚本 `scripts/archive_gpu_legacy.py` 也已删除，避免再次扩大迁移范围。

## 相关入口

- [CPU 主线目录](../README.md)
