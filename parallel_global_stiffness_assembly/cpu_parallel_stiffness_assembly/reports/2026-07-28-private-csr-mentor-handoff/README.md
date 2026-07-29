# 线程私有 CSR 实验导师包

关联 Issue：[#58](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/58)

## 最终文件

```text
private_csr_experiment_2026-07-08.zip
```

- 大小：20,146,230 bytes
- SHA-256：`38ce1b18af16fbfc68e57f7c9b7927aa703ff17575961c15fd0e7d70a8beb781`
- 本地路径：`/Users/macbook_prom5/Desktop/private_csr_experiment_2026-07-08.zip`

压缩包不提交到仓库。包内含 76 MB WindHub 网格，只用于课题组内部复现。

## 本次精简

旧包有 228 个文件和 22 份 README，阅读入口太多。新包改成 ASCII 路径，
只保留 51 个文件和根目录的一份中文 README：

| 目录 | 内容 |
|---|---|
| `code` | CPU 源码、精简 CMake 入口、一个正确性测试和实验 runner |
| `scripts` | 线程私有 CSR 绘图脚本 |
| `data` | 2026-07-08 原始 CSV、汇总 CSV、平台信息和原始命令 |
| `figures` | 2026-07-10 正式 PNG 和 20 个绘图点 |
| `mesh` | WindHub Abaqus `.inp` 网格 |

README 明确写出了 Windows 的 CMake 源码路径、生成的 `.exe` 路径、接口
位置、实验设置和不同线程数下的时间、内存与加速比。旧包已移到
`build/issue-58-mentor-handoff/superseded_verbose_package/`，没有删除。

## 核对结果

- Python 两个脚本通过语法检查。
- 从 ZIP 新目录配置和编译成功，OpenMP 5.1 被启用。
- `VerifySymbolicNumericEval`：1/1 通过。
- 小网格隔离进程测试产生 3 条记录，`run_status` 和矩阵正确性均为 `PASS`。
- 使用 Matplotlib 3.10.8 重画线程私有图，尺寸为
  \(3072\times1728\)，解码后像素逐点一致。
- ZIP 内部 50 个实质文件的 SHA-256 全部通过。
- ZIP 只有一个顶层目录，路径全部为 ASCII，不含 `.DS_Store`、
  `__pycache__` 或 `.pyc`。

macOS 上已经从 ZIP 做过完整复验；包内 C++ 源码也通过现有分支的 Windows
CI。此次没有在一台独立 Windows 主机上重新解压整个 19 MB 包，因此不把
当前检查写成“Windows 实机复现已完成”。

原数据采于 2026-07-08，图生成于 2026-07-10。仓库中没有
“2026-07-20”这一轮的原始日志，所以继续使用可追溯的真实日期。
