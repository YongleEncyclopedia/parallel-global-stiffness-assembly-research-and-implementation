# 组装路径示意图

本目录保存三张基于当前 C++ 实现的组装路径示意图：

- `assets/symbolic_assembly_schematic.*`：符号组装，展示 `CSR` 稀疏结构和 `AssemblyPlan::scatter` 地址预计算。
- `assets/numeric_assembly_schematic.*`：数值组装，展示复用符号阶段结果计算 `Ke` 并写入 `CSR values`。
- `assets/direct_no_symbolic_assembly_schematic.*`：无符号直接组装，展示 `DirectContribution` 列表、排序归并和最终 `CSR` 构造。

## Figure contract

- Core conclusion：项目把拓扑/地址构造、数值填充、直接贡献排序归并拆成三条不同组装语义。
- Archetype：schematic-led composite。
- Backend：Python。
- Output：每张图导出 `SVG`、`PDF`、`PNG`、`TIFF`；`SVG` 保留可编辑 `<text>` 节点。
- Statistics：无；这是代码语义示意图，不是 benchmark 数据图。
- Source data：当前文档和 C++ 实现。
- Reviewer risk：`direct_no_symbolic` 不能解释成 dense matrix 路径，应解释成 contribution list -> sort/reduce -> CSR。

## 复现

```bash
/Users/haohua_jiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/plot_assembly_schematics.py
```

