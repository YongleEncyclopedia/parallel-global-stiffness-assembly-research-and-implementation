# 跨平台结果包：intel-u7-265kf

## 用途

保存指定硬件或运行 profile 下的跨平台 benchmark package。

## 存放内容

- 直接文件：当前没有直接文件，主要通过子目录承载内容。
- 子目录：`efficiency_core_only/`、`full_host/`、`performance_core_only/`

## 不应存放

其他硬件的结果或未打包原始实验。

## 维护提示

Intel taskset profile 与 Apple QoS profile 不能当作完全等价机制。

## 相关入口

- 上级目录：[parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/packages](../README.md)
- 子目录：[`efficiency_core_only/`](efficiency_core_only/README.md)
- 子目录：[`full_host/`](full_host/README.md)
- 子目录：[`performance_core_only/`](performance_core_only/README.md)
