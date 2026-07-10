# 平台协议与兼容策略

## 用途

本目录保存跨平台角色、CPU profile、benchmark package schema、Linux Intel 正式实验口径和求解器 validation 契约。这里定义可复用规则，不保存某次实验的原始输出或仍在执行的计划。

## 文档索引

- [跨平台策略](cross-platform-strategy.md)：Linux Intel、macOS ARM64、Windows AMD 与三平台 CI 的职责和解释边界。
- [跨平台 CPU benchmark schema](cross-platform-benchmark-schema.md)：versioned package、run profile 与跨平台比较字段。
- [Linux Intel 正式实验协议](linux-intel-experiment-protocol.md)：物理核线程范围、重复口径、内存生命周期、manifest 和物理机验收规则。
- [跨平台求解器 validation 协议](cross-platform-validation-protocol.md)：四例导出、MATLAB 求解和独立求解器位移比较闭环。

## 证据归属

正式 benchmark 与求解器验证的原始 CSV/JSON、日志、manifest 和图表进入 CPU 子项目的 `results/` 或 `reports/`。GitHub Actions artifact 只保存自动检查产物；Issue 与 PR 只写摘要并链接稳定证据。

## 维护提示

- 平台策略负责说明“哪些结果可以比较”，不能代替原始结果证明“哪个实现更快”。
- 变更线程、重复、工具链、内存测量源或求解器契约时，应同步更新相应协议和自动契约测试。
- 历史证据保持其原始工具链与环境含义，不能用当前 CI 状态追溯性改写。

## 相关入口

- 上级目录：[docs](../README.md)
- CPU 主线：[cpu_parallel_stiffness_assembly](../../parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md)
