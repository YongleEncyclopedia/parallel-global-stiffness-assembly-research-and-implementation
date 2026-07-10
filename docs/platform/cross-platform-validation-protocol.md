# 跨平台求解器 validation 协议

## 目的与边界

本协议规定如何把 C++ 组装得到的整体刚度矩阵 $K$、载荷向量 $f$ 和位移边界条件交给 MATLAB 求解，再与 Abaqus、CalculiX、COMSOL 等独立有限元求解器的 probe 位移比较。它用于建立可追溯的求解级证据，不取代单元刚度、整体矩阵和性能测试。

普通 CI 只验证小网格物理路径、七文件导出 schema、runner 状态传播和合成位移比较。MATLAB 与商业求解器只能在具备相应软件或许可证的受控机器运行；未执行求解器时必须标记为 `export-only/SKIPPED`，不能宣称已完成求解器级验证。

## 固定算例与模型等价性

标准包包含四例：

| case | C++ 单元 | 参考求解器等价单元 | 默认网格 |
| --- | --- | --- | --- |
| `cantilever_hex8_small` | Hex8，$2\times2\times2$ Gauss 全积分 | Abaqus `C3D8` 或等价全积分单元 | $2\times2\times2$ |
| `cantilever_hex8_medium` | Hex8，$2\times2\times2$ Gauss 全积分 | Abaqus `C3D8` 或等价全积分单元 | $12\times4\times4$ |
| `cantilever_tet4_small` | 常应变 Tet4 | Abaqus `C3D4` 或等价线性四面体 | $2\times2\times2$ 结构化块的六四面体剖分 |
| `cantilever_tet4_medium` | 常应变 Tet4 | Abaqus `C3D4` 或等价线性四面体 | $12\times4\times4$ 结构化块的六四面体剖分 |

四例均必须显式使用 `--stiffness-model linear_elastic_solid`。默认悬臂块取长度 $L=1$、宽度 $W=0.2$、厚度 $T=0.1$、弹性模量 $E=1$、泊松比 $\nu=0.3$；在 $x=0$ 的端面约束三个位移自由度，在 $x=L$ 的端面向自由度 $2$ 施加总力 $-1$。参考模型必须保持相同节点坐标、连接顺序、材料、约束、等效节点载荷和单元积分方案。

## 七文件导出契约

每个 `<prefix>` 必须产生：

1. `<prefix>_K.mtx`
2. `<prefix>_force.csv`
3. `<prefix>_bc.csv`
4. `<prefix>_probes.csv`
5. `<prefix>_nodes.csv`
6. `<prefix>_elements.csv`
7. `<prefix>_metadata.json`

CSV 中的节点与自由度编号均从 $0$ 开始。Matrix Market 坐标从 $1$ 开始，header 必须为 `%%MatrixMarket matrix coordinate real symmetric`，且只保存下三角。metadata 必须记录 case、`linear_elastic_solid`、网格规模、材料、载荷、矩阵维度和六个数据文件名。

批量导出入口为：

```bash
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-serial \
  --out-root /tmp/pgsa-validation-export
```

默认导出全部四例，并写入 `validation_export_manifest.json`。输出目录已存在时默认失败；只有明确传入 `--overwrite` 才会替换该 runner 自己管理的 case 目录和 manifest。`--dry-run` 只打印命令，不创建输出。

## MATLAB 求解契约

MATLAB 入口为：

```matlab
addpath("scripts")
solve_validation_export_matlab("/tmp/pgsa-validation-export/cantilever_hex8_small", ...
    "cantilever_hex8_small")
```

该函数自带 Matrix Market `real symmetric` 下三角读取器，不依赖外部 `mmread`。CSV 的零基节点/自由度在 MATLAB 中转换为一基索引。对非零 Dirichlet 条件，必须先构造

$$
f_f' = f_f-K_{fc}u_c,
$$

再求解

$$
K_{ff}u_f=f_f'.
$$

输出包括 `<prefix>_matlab_displacements.csv`、`<prefix>_matlab_probe_summary.csv` 和 `<prefix>_matlab_solve_metadata.json`。metadata 必须记录矩阵规模、约束与未约束自由度数量，以及未约束自由度上的绝对和相对残差。

需要实际运行 MATLAB 时，在受控机器执行：

```bash
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-serial \
  --out-root results/validation-export/<platform> \
  --run-matlab \
  --matlab-bin matlab
```

## 通用位移比较契约

比较入口示例：

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab CASE_matlab_displacements.csv \
  --reference CASE_abaqus_displacements.csv \
  --reference-solver abaqus \
  --reference-index-base 1 \
  --probes CASE_probes.csv \
  --out-csv CASE_abaqus_compare.csv \
  --out-md CASE_abaqus_compare.md
```

参考 CSV 的节点映射列按以下优先级解释：`cpp_node`、`node_zero_based`、`node`、`node_label`。前两列始终按零基处理；后两列按 `--reference-index-base` 转换。若同一行同时出现多个映射列，转换后的节点必须一致，否则比较失败。`--abaqus` 暂时保留为 `--reference` 的兼容别名。

对于 probe 位移 $u_p$ 与参考位移 $u_r$，报告

$$
d_{\mathrm{abs}}=\lVert u_p-u_r\rVert_2,
$$

$$
d_{\mathrm{rel}}=
\frac{d_{\mathrm{abs}}}
{\max\!\left(\lVert u_r\rVert_2,10^{-30}\right)}.
$$

自由端挠度幅值的百分比差异为

$$
d_{\mathrm{tip},\%}=100\,
\frac{\left|\lVert u_p\rVert_2-\lVert u_r\rVert_2\right|}
{\max\!\left(\lVert u_r\rVert_2,10^{-30}\right)}.
$$

本阶段不人为设定物理 pass/fail 阈值；有效比较统一标记为 `REPORTED_NO_HARD_THRESHOLD`。缺失/重复节点、缺列、非有限数值、索引越界或映射冲突必须非零退出。

## 证据保存与人工检查

许可证主机完成四例后，应将命令、提交 SHA、平台、编译器、MATLAB/求解器版本、runner manifest、原始位移 CSV 和比较报告保存到 `results/validation-export/...`。Issue 或 PR 只写摘要并链接该证据，不粘贴整份原始数据。

若 Hex8 结果出现显著差异，依次核对节点顺序、积分方案、材料矩阵、单元刚度与应变能、边界条件、端面载荷等效化和求解器默认设置；在原因隔离前不得把差异解释为某一实现必然错误。
