# CSC3 对称稀疏组装 Demo 内部交付说明空白模板

> **INTERNAL EVALUATION ONLY**
>
> `CSC3_DELIVERY_NOTE_STATUS=PENDING`
>
> 源码包内包含本模板是预期行为；它只是可复制的空白模板，不是已经批准的
> 交付说明。操作员必须在仓库外复制并填写，随后将状态标记改为
> `CSC3_DELIVERY_NOTE_STATUS=PASS`。未填写完所有 `REQUIRED BEFORE DELIVERY`
> 字段、正式验收状态不是 `PASS`、或缺少批准记录时，完成版不得随最终交付档案
> 发出，也不得被称为正式交付说明。

## 1. 交付标识

| 字段 | 必填值 |
|---|---|
| 交付 ID | **REQUIRED BEFORE DELIVERY** |
| 交付日期（UTC） | **REQUIRED BEFORE DELIVERY** |
| Demo 版本 | **REQUIRED BEFORE DELIVERY** |
| 完整源码 SHA | **REQUIRED BEFORE DELIVERY** |
| Issue #44 URL | **REQUIRED BEFORE DELIVERY** |
| 发送组织/部门 | **REQUIRED BEFORE DELIVERY** |
| 接收组织/部门 | **REQUIRED BEFORE DELIVERY** |
| 指定接收人身份引用 | **REQUIRED BEFORE DELIVERY** |

## 2. 交付范围与算法

本交付是一个独立、可集成的 C++17 源码 Demo，用于 CSC3 对称上三角整体刚度
矩阵组装。候选算法仅包括：

1. 确定性的 OpenMP **并行符号组装**，生成 `column_offsets`、
   `row_indices` 与 `scatter_indices`；
2. 使用 OpenMP atomic 的**并行原子累加数值组装**，每次调用先清零再完成一轮
   全量组装。

串行实现只作为正确性和性能基线，不是对外候选算法，也没有无 OpenMP 的串行
fallback。

交付目的与允许使用范围：**REQUIRED BEFORE DELIVERY**

授权文件或内部审批引用：**REQUIRED BEFORE DELIVERY**

## 3. 包含项

- 白名单内的源码、公共头文件、CMake preset、测试与 benchmark 工具；
- 英文 README、API 与命名契约、迁移说明；
- 规范 Markdown 中文测试报告；
- `run_manifest.json`、`ctest.xml`、`benchmark_samples.csv`、
  `benchmark_summary.json`、`summary.md`；
- `BUILD_INFO.json`、`MANIFEST.sha256`、第三方依赖说明及内部评估声明。

最终包含项核对：**REQUIRED BEFORE DELIVERY**

## 4. 排除项与不作出的声明

- 不包含预编译二进制、商业求解器、许可证服务器或商业求解器输入/结果包；
- 不包含 MATLAB、Abaqus、CalculiX 或 COMSOL 的独立验证结论；
- 正确性中的位移与残差测试只证明组装结果可进入 $K u = f$ 求解流程，**不声称
  完成商业求解器验证**；
- 不把 GitHub CI runner 的计时用作正式性能结论；
- 不授予公开发布、再分发、转授权、销售或并入另一个对外产品的权利。

最终排除项核对：**REQUIRED BEFORE DELIVERY**

## 5. 证据与哈希

| 产物 | 路径或标识 | SHA-256 |
|---|---|---|
| 原始证据目录/manifest | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 规范 Markdown 报告 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 正式源码 ZIP | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| `host-preflight.txt` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| `SOURCE_COMMIT` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| `SHA256SUMS` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| `deterministic-package.txt` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| manifest-only verifier 输出 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| `clean-room-verification.log` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 机器可读验收记录 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 完成版验收清单 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |

`FINALIZATION.json` 与 `FINAL_SHA256SUMS` 不在本表中预填路径或哈希：本交付说明
自身是 finalizer 的输入，预填这两个派生文件会形成自引用。四方批准本说明后，
finalizer 才原子生成它们；操作员必须在最终目录外执行
`sha256sum -c FINAL_SHA256SUMS`，并把命令结果记录在 Issue #44 的 finish comment。

证据 SHA-256：**REQUIRED BEFORE DELIVERY**

报告 SHA-256：**REQUIRED BEFORE DELIVERY**

ZIP SHA-256：**REQUIRED BEFORE DELIVERY**

Markdown 是唯一权威测试报告。若另附 PDF，其用途仅为排版展示；PDF 必须记录
独立 SHA-256，不得替代或修改 Markdown 中的结论、数值、命令和证据绑定。

可选 PDF 路径及 SHA-256：**REQUIRED BEFORE DELIVERY** 或明确填写“不提供”。

## 6. 验收状态、已知限制与偏差

机器可读验收记录路径：**REQUIRED BEFORE DELIVERY**

正式验收状态（只能为 `PASS`）：**REQUIRED BEFORE DELIVERY**

正确性门槛摘要：**REQUIRED BEFORE DELIVERY**

性能门槛摘要：**REQUIRED BEFORE DELIVERY**

确定性打包与 clean-room 结果：**REQUIRED BEFORE DELIVERY**

已知限制：**REQUIRED BEFORE DELIVERY**

偏差及批准引用（无偏差也必须填写“无”）：**REQUIRED BEFORE DELIVERY**

未解决风险（无风险也必须填写“无”）：**REQUIRED BEFORE DELIVERY**

许可证和正式 release policy 尚未决定。因此本包只允许在已书面授权的发送方与
研究院指定求解器开发部门之间内部评估；接收方不得再分发，且不得把本文件理解为
公共或商业许可。

## 7. 回滚与复现

复现入口为
[`LINUX_FORMAL_RUNBOOK.zh-CN.md`](LINUX_FORMAL_RUNBOOK.zh-CN.md)，验收核对入口为
[`ACCEPTANCE_CHECKLIST.zh-CN.md`](ACCEPTANCE_CHECKLIST.zh-CN.md)，记录结构由
[`ACCEPTANCE_RECORD.schema.json`](ACCEPTANCE_RECORD.schema.json)定义。

复现所需完整源码 SHA：**REQUIRED BEFORE DELIVERY**

受控主机 ID：**REQUIRED BEFORE DELIVERY**

输入 SHA-256 与字节数：**REQUIRED BEFORE DELIVERY**

完整复现命令/记录位置：**REQUIRED BEFORE DELIVERY**

如发现交付错误，应暂停使用并按完整源码 SHA、ZIP SHA-256 和交付 ID 撤回该包；
不得覆盖原产物。修复后应使用新的唯一交付 ID 和新的仓库外运行目录，从头执行
正式流程并重新批准。

回滚负责人及联系引用：**REQUIRED BEFORE DELIVERY**

撤回/替换流程引用：**REQUIRED BEFORE DELIVERY**

## 8. 必需批准与接收确认

以下内容是组织审批引用，不是由本模板生成或伪造的签名。

| 角色 | 身份引用 | UTC 时间 | 审批/确认记录号 | 决定 |
|---|---|---|---|---|
| 操作员 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 技术复核人 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 发送方批准/交付批准人 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |
| 接收方确认 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |

发送方批准声明：**REQUIRED BEFORE DELIVERY**

接收方确认声明：**REQUIRED BEFORE DELIVERY**
