# 整体刚度矩阵研究代码根目录

## 用途

保存当前 CPU 主线项目和相关模块入口。

## 存放内容

- 直接文件：`README.md`
- 子目录：`cpu_parallel_stiffness_assembly/`

## 不应存放

仓库级计划、外部课程资料或无关实验。

## 维护提示

当前有效开发入口是 `cpu_parallel_stiffness_assembly/`。

## 相关入口

- 子目录：[`cpu_parallel_stiffness_assembly/`](cpu_parallel_stiffness_assembly/README.md)


## 原有说明

以下保留本文件原有的详细说明；本节之前的内容是统一补充的中文目录维护说明。

# parallel_global_stiffness_assembly

本目录当前只维护一个有效主入口：

```text
cpu_parallel_stiffness_assembly/
```

该子项目是当前仓库的 CPU-first / CPU-only 并行整体刚度矩阵组装 benchmark 平台。默认构建、默认实验和用户可见文档都围绕 CPU OpenMP 算法展开。

## 如何进入主线

```bash
cd cpu_parallel_stiffness_assembly
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
```

更完整的 benchmark、实验调度和绘图说明见：

- `cpu_parallel_stiffness_assembly/README.md`
- `../docs/requirements/cpu-parallel-stiffness-assembly-design.md`
- `../docs/plans/2026-04-22-chatgpt-pro-handoff.md`

## 关于 GPU 历史内容

GPU / CUDA 历史资产不是当前主线。如果后续需要把这些内容系统归档，请统一放入：

```text
cpu_parallel_stiffness_assembly/legacy_gpu/
```

当前推荐的说明文档与工具是：

- `cpu_parallel_stiffness_assembly/legacy_gpu/README.md`
- `cpu_parallel_stiffness_assembly/scripts/archive_gpu_legacy.py`

不要把 CUDA 构建、GPU 验证脚本或旧绘图脚本重新当成默认入口。
