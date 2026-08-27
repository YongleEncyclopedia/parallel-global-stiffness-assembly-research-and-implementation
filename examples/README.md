# WindHub 工程输入

这里保存跨模块共用的工程输入。WindHub 性能实验使用：

```text
examples/3d-WindTurbineHub.inp
```

这个文件由 Git LFS 管理，仓库中只保留一份。CSC3 Demo 的一键脚本会自动找到它，
不要把它复制到 Demo 目录。

本目录只保存输入文件，不是运行入口。请从
`demos/csc3_symmetric_assembly_demo/README.md` 开始编译和运行。

同目录的 `符号组装参考代码.zip` 只供人工对照，不参与编译或性能实验。

## Windows 首次下载

先安装 Git LFS，再从仓库根目录执行：

```powershell
git lfs install
git lfs pull --include="examples/3d-WindTurbineHub.inp"
```

可以用下面的命令查看文件大小：

```powershell
(Get-Item .\examples\3d-WindTurbineHub.inp).Length
```

当前实体文件应为 76,111,745 字节。如果文件只有几行以
`version https://git-lfs.github.com/spec/v1` 开头的文字，说明拿到的仍是 LFS 指针，
请重新执行 `git lfs pull`。

## 使用边界

- 小型解析测试会在运行时生成临时输入，不会读取完整 WindHub。
- `3d-WindTurbineHub.inp` 只提供节点和单元网格；Demo 不读取载荷或边界条件。
- 构建输出和实验结果写入 Demo 的 `build/`，不放在本目录。
- 删除或替换 Git LFS 文件前，要先检查引用路径和对象校验值。
