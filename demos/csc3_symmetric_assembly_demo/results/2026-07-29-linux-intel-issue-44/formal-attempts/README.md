# Formal 失败尝试审计

本目录故意保留失败证据。四次失败都不参与正式性能统计；前三次发生在
benchmark 之前，第四次发生在 benchmark 门禁已通过后的报告生成阶段。

## r1：CMake Python 选择错误

- 源码 SHA：`94cd0d00f1d6725a6af67c8364b4bd07643f1e43`。
- 归档的 `cmake-cache.txt` 记录
  `_Python3_EXECUTABLE=/home/haohua/.local/bin/python3.11`。
- 该解释器缺少 `jsonschema`，configure `FAIL`。
- 修复：formal runner 将实际 `sys.executable` 显式传给 CMake，并在 manifest
  中记录 runner 与 CMake 两个路径；formal gate 要求原字符串完全一致。

## r2：Git replace 攻击测试夹具受 formal 防护影响

- 显式 PATH 临时探针让 CMake 选中 venv，configure/build `PASS`。
- CTest `FAIL`：runbook 的 `GIT_NO_REPLACE_OBJECTS=1` 正确地阻止 Git 测试
  夹具解释 replace ref，导致攻击夹具在调用被测打包器前就没有构造成功。
- 修复：保留 formal 子进程的 Git 防护，仅在测试内部构造恶意 fixture 的 Git
  命令中局部移除该变量；新增测试确认 sanitizer 继续保留安全变量。

## r3：clean-room 二次 CMake 未绑定 venv

- 源码 SHA：`f5aaf46154556c32ec6880845e10ef7f024194d5`。
- 顶层 configure/build 和 Python 绑定 `PASS`。
- CTest 的 delivery-package clean-room 在临时解包目录再次运行 CMake，误选用户
  Python；因缺少 `jsonschema`，CTest `FAIL`。
- 修复：clean-room configure 显式传入当前 `sys.executable`，保留未解析的 venv
  路径，并新增精确命令回归测试。

## r4：report generator 仍使用旧 configure 契约

- 源码 SHA：`29bbcb8b65b1455f7a4ded9233f4451986b8a3b8`。
- runner 的 configure、build、10 项 CTest、WindHub 正确性、scatter 和性能门禁
  均为 `PASS`。
- 报告生成器仍硬编码旧的 5-token configure 命令，未接受新增的显式 Python
  参数，因此规范报告生成 `FAIL`。
- 修复：报告校验要求 configure 第 6 个参数与
  `runner_python_executable`、`cmake_python_executable` 三方逐字节一致。

后续 r5 在新干净 detached worktree 上通过 runner 全链与规范报告生成；其证据
位于 `../formal-bound-control/`。
