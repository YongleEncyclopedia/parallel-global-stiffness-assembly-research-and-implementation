# 跨平台策略

## 目标平台

项目预期按下面顺序演进：

1. 在 `Mac Studio` 的 `macOS` 环境中做第一轮验证和设计驱动实现。
2. 后续迁移到 `Intel U7 265KF` 的 `Windows` 环境中复现 benchmark。

因此，本项目从一开始就应被当作跨平台 CPU 项目维护，而不是单机原型。

## 实际约束

- `macOS Apple Silicon` 与 `Windows Intel x86_64` 的 CPU 架构不同。
- 编译器栈不同：macOS 侧以 `AppleClang/Clang` 为主，Windows 侧以 `MSVC` 为主。
- `OpenMP` 可用性和安装方式随平台变化。
- 路径处理、shell 行为和换行符规则不同。

## 设计规则

- 构建入口优先使用 `CMake`。
- C++ 代码优先遵守标准 `C++17`。
- 平台相关代码保持隔离，不要散落在通用逻辑中。
- 避免把流程硬编码成只适用于某个 shell 的形式。
- 小型自动化任务可以优先使用 Python。
- benchmark 输出必须记录编译器、操作系统、CPU 架构和线程后端。

## 当前开发倾向

第一阶段实现时：

- 在 macOS 上优先保证正确性和清晰抽象。
- 不引入会阻碍 Windows 迁移的捷径。
- 平台 workaround 必须作为显式兼容层存在，不能变成隐藏假设。

## 后续工作

完成初始 macOS 验证后：

- 确认 Windows 上的最小 CMake 构建流程。
- 复现相同 benchmark 输入和输出字段。
- 把算法行为和平台影响分开解释。

## Benchmark Schema 规则

跨平台 benchmark 结果必须使用版本化 package schema。当前规范见：

- [cross-platform-benchmark-schema.md](cross-platform-benchmark-schema.md)

在测试新的 CPU 平台之前，先运行 `scripts/inspect_cpu_platform.py`，并明确说明 CPU 是同质核心还是存在 performance/efficiency core 分类。如果平台可以可靠隔离 P/E core 资源，则收集 `full_host`、`performance_core_only` 和 `efficiency_core_only`；否则在 metadata 中用证据把不支持的 profile 标为 `not_applicable` 或 `missing`。
