# 求解级 validation 输入样例目录

## 用途

保存悬臂梁 Tet4/Hex8 小型 `.inp`，用于 validation_export 和 MATLAB/Abaqus 对比。

## 存放内容

- 直接文件：`README.md`、`cantilever_hex8_small.inp`、`cantilever_tet4_small.inp`
- 子目录：当前没有直接子目录。

## 不应存放

大规模 benchmark 网格或生成结果。

## 维护提示

样例变更会影响验证闭环，修改前同步 README 和相关测试。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/examples](../README.md)


## 原有说明

以下保留本文件原有的详细说明；本节之前的内容是统一补充的中文目录维护说明。

# Validation Fixtures

These small Abaqus `.inp` files mirror the generated cantilever validation
cases used by `validation_export`. They are intentionally tiny so they can be
checked into the repository, loaded by the C++ parser, and reused as Abaqus
model seeds.

- `cantilever_hex8_small.inp`: one C3D8 block with dimensions `1 x 0.2 x 0.1`.
- `cantilever_tet4_small.inp`: the same block decomposed into six C3D4
  tetrahedra.

The executable-generated cases remain the default for regression tests because
they include enough nodes to place the `free_tip_center` and `midspan_center`
probes exactly at mesh nodes.
