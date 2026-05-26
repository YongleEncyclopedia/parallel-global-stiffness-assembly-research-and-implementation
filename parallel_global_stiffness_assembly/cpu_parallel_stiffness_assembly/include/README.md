# 公共头文件目录

## 用途

保存 C++ 库对内部模块和应用暴露的公共接口。

## 存放内容

- 直接文件：当前没有直接文件，主要通过子目录承载内容。
- 子目录：`assembly/`、`backends/`、`core/`

## 不应存放

具体实现 `.cpp`、结果数据或报告。

## 维护提示

接口变更要同步 `src/` 实现、测试和文档。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly](../README.md)
- 子目录：[`assembly/`](assembly/README.md)
- 子目录：[`backends/`](backends/README.md)
- 子目录：[`core/`](core/README.md)
