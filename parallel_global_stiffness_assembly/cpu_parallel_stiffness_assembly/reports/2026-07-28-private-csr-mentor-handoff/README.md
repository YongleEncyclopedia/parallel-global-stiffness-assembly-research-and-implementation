# 并行组装实验导师包

关联 Issue：[#58](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/58)

## 交付文件

```text
private_csr_experiment_2026-07-08.zip
```

- 大小：21,706,654 bytes
- SHA-256：`48077a9502f7e91c6889b28669633a2b938b6fefd0856b3e297e59586cefd285`
- 本地路径：`/Users/macbook_prom5/Desktop/private_csr_experiment_2026-07-08.zip`

压缩包不提交到仓库。包内含 WindHub 网格，仅用于课题组内部复现。

## 包内内容

压缩包共 64 个文件，根目录只有一份中文 README：

| 目录 | 内容 |
|---|---|
| `code` | CPU 源码、CMake、正确性测试和实验 runner |
| `scripts` | 固定线程横向对比和各后端线程趋势绘图脚本 |
| `data` | 2026-07-08 的原始记录、汇总表、平台信息和实际命令 |
| `figures` | 2026-07-10 的 6 张正式 PNG 及 8 份对应绘图数据 |
| `mesh` | WindHub Abaqus `.inp` 网格 |

材料覆盖原子累加、线程私有、互斥锁、图着色和按行分配五种并行后端，
不再把交付范围限定为线程私有算法。每个代码文件开头都增加了简短的中文
用途说明；README 给出 Windows 的源码路径、输出路径、接口位置和复现命令。

## 复核结果

- 从新 ZIP 解压到空目录后，63 个清单条目的 SHA-256 全部通过。
- 三个 Python 脚本通过语法检查。
- AppleClang 21.0 + OpenMP 5.1 下配置、编译成功。
- `VerifySymbolicNumericEval`：1/1 通过。
- 五种并行后端的 1、2 线程小网格 smoke 共 11 条记录，11 条均为 `PASS`。
- 两个绘图脚本从 `data/summary.csv` 重画出 6 张图；与包内 PNG 逐像素一致，
  8 份绘图 CSV 逐行一致。
- ZIP 只有一个顶层目录，路径全部为 ASCII，不含 `.DS_Store`、
  `__pycache__` 或 `.pyc`。

macOS 上已完成上述复核；本次没有在独立 Windows 主机上重新解压并编译，
因此不写成“Windows 实机复现已完成”。原数据采于 2026-07-08，图生成于
2026-07-10。
