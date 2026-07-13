# macOS ARM64 本地冒烟证据

本目录归档状态为 `LOCAL_SMOKE`，证据源提交为 `18f2474107bcfb4321d35bcabb4995d0c9f2f79f`。

这些文件是在 Apple M5/macOS ARM64 环境生成的 Tet4 证据，仅用于本地冒烟验证，不属于正式性能证据，也不构成交付验收。

本次参数为 $W=1$、$R=2$、$p\in\{1,2\}$ 与 $m=2$。

原始文件：

- [ctest.xml](./ctest.xml)
- [benchmark_samples.csv](./benchmark_samples.csv)
- [benchmark_summary.json](./benchmark_summary.json)
- [run_manifest.json](./run_manifest.json)
- [summary.md](./summary.md)

测试报告见 [macOS 本地冒烟测试报告](../../reports/2026-07-13-csc3-demo-macos-local-smoke-test-report.zh-CN.md)。

正式 WindHub 运行仍须在受控 Linux Intel 主机上执行。
