# CSC3 对称稀疏组装 Demo 内部交付说明空白模板

> **INTERNAL EVALUATION ONLY**
>
> `CSC3_DELIVERY_NOTE_STATUS={{CSC3_DELIVERY_NOTE_STATUS_MARKER}}`
>
> 源码包内包含本模板是预期行为；它只是可复制的空白模板，不是已经批准的
> 交付说明。操作员必须在仓库外复制并填写，随后将状态标记改为
> `CSC3_DELIVERY_NOTE_STATUS=PASS`。未填写完所有必填占位字段、正式验收状态不是
> `PASS`、或缺少批准记录时，完成版不得随最终交付档案
> 发出，也不得被称为正式交付说明。

## 1. 交付标识

| 字段 | 必填值 |
|---|---|
| 交付 ID | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_DELIVERY_ID_ROW}} -->
| 交付日期（UTC） | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_DELIVERY_DATE_ROW}} -->
| Demo 版本 | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_DEMO_VERSION_ROW}} -->
| 完整源码 SHA | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_SOURCE_COMMIT_ROW}} -->
| Issue #44 URL | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_ISSUE_URL_ROW}} -->
| 发送组织/部门 | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_SENDER_ROW}} -->
| 接收组织/部门 | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_RECIPIENT_ROW}} -->
| 指定接收人身份引用 | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_RECIPIENT_IDENTITY_ROW}} -->

“交付日期（UTC）”固定为四条 `approvals.*.acknowledged_at_utc` 中最晚时刻转换为
UTC 后的日历日期，格式为 `YYYY-MM-DD`。它表示四方确认完成的 UTC 日期，不是 benchmark
开始时间、候选包生成时间或 finalizer 本机时间。Demo 版本必须从验收记录所绑定的候选
ZIP 文件名 `csc3-symmetric-assembly-demo-v<version>+<short-sha>.zip` 提取。

## 2. 交付范围与算法

本交付是一个独立、可集成的 C++17 源码 Demo，用于 CSC3 对称上三角整体刚度
矩阵组装。候选算法仅包括：

1. 确定性的 OpenMP **并行符号组装**，生成 `column_offsets`、
   `row_indices` 与 `scatter_indices`；
2. 使用 OpenMP atomic 的**并行原子累加数值组装**，每次调用先清零再完成一轮
   全量组装。

串行实现只作为正确性和性能基线，不是对外候选算法，也没有无 OpenMP 的串行
fallback。

交付目的与允许使用范围：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_PURPOSE_LINE}} -->

授权文件或内部审批引用：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_AUTHORIZATION_LINE}} -->

## 3. 包含项

- 白名单内的源码、公共头文件、CMake preset、测试与 benchmark 工具；
- 英文 README、API 与命名契约、迁移说明；
- 规范 Markdown 中文测试报告；
- `run_manifest.json`、`ctest.xml`、`benchmark_samples.csv`、
  `benchmark_summary.json`、`summary.md`；
- `BUILD_INFO.json`、`MANIFEST.sha256`、第三方依赖说明及内部评估声明。

最终包含项核对：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_INCLUDED_ITEMS_LINE}} -->

## 4. 排除项与不作出的声明

- 不包含预编译二进制、商业求解器、许可证服务器或商业求解器输入/结果包；
- 不包含 MATLAB、Abaqus、CalculiX 或 COMSOL 的独立验证结论；
- 正确性中的位移与残差测试只证明组装结果可进入 $K u = f$ 求解流程，**不声称
  完成商业求解器验证**；
- 不把 GitHub CI runner 的计时用作正式性能结论；
- 不授予公开发布、再分发、转授权、销售或并入另一个对外产品的权利。

最终排除项核对：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_EXCLUDED_ITEMS_LINE}} -->

## 5. 证据与哈希

| 产物 | 路径或标识 | SHA-256 |
|---|---|---|
| 原始证据目录/manifest | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_RUN_MANIFEST_ROW}} -->
| 规范 Markdown 报告 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_REPORT_ROW}} -->
| 正式源码 ZIP | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_ARCHIVE_ROW}} -->
| `host-preflight.txt` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_HOST_PREFLIGHT_ROW}} -->
| `SOURCE_COMMIT` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_SOURCE_COMMIT_FILE_ROW}} -->
| `SHA256SUMS` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_SHA256SUMS_ROW}} -->
| `deterministic-package.txt` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_DETERMINISTIC_PACKAGE_ROW}} -->
| manifest-only verifier 输出 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_MANIFEST_ONLY_ROW}} -->
| `clean-room-verification.log` | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_CLEAN_ROOM_ROW}} -->
| 机器可读验收记录 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_ACCEPTANCE_RECORD_ROW}} -->
| 完成版验收清单 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_ACCEPTANCE_CHECKLIST_ROW}} -->

以上每一行必须填写验收记录或 finalizer 输入快照中的实际相对路径与 SHA-256；
“已完成”、`PASS` 等泛化文字不能代替路径或哈希。机器可读验收记录的哈希以
finalizer 读取的不可变 `record_content` 为准，完成版验收清单的哈希以同一次
finalizer 调用读取的 `checklist_content` 为准，因此不形成自引用。

`FINALIZATION.json` 与 `FINAL_SHA256SUMS` 不在本表中预填路径或哈希：本交付说明
自身是 finalizer 的输入，预填这两个派生文件会形成自引用。四方批准本说明后，
finalizer 才原子生成它们；操作员必须在最终目录外执行
`sha256sum -c FINAL_SHA256SUMS`，并把命令结果记录在 Issue #44 的 finish comment。

证据 SHA-256：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_EVIDENCE_SHA256_LINE}} -->

报告 SHA-256：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_REPORT_SHA256_LINE}} -->

ZIP SHA-256：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_ARCHIVE_SHA256_LINE}} -->

Markdown 是唯一权威测试报告。若另附 PDF，其用途仅为排版展示；PDF 必须记录
独立 SHA-256，不得替代或修改 Markdown 中的结论、数值、命令和证据绑定。

可选 PDF 路径及 SHA-256：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_PRESENTATION_PDF_LINE}} -->

若验收记录不含 `artifacts.presentation_pdf`，本行必须逐字填写
`presentation_pdf=ABSENT`；若包含，则必须填写
`presentation_pdf=<record path>；PDF_SHA-256=<record sha256>`。finalizer 会与验收
记录精确比对，不能使用“不提供”、自由文本或未绑定的路径/哈希替代。

## 6. 验收状态、已知限制与偏差

机器可读验收记录路径：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_RECORD_PATH_LINE}} -->

正式验收状态（只能为 `PASS`）：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_ACCEPTANCE_STATUS_LINE}} -->

正确性门槛摘要：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_CORRECTNESS_SUMMARY_LINE}} -->

性能门槛摘要：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_PERFORMANCE_SUMMARY_LINE}} -->

确定性打包与 clean-room 结果：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_VERIFICATION_SUMMARY_LINE}} -->

已知限制：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_KNOWN_LIMITATIONS_LINE}} -->

偏差及批准引用（无偏差也必须填写“无”）：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_DEVIATION_SUMMARY_LINE}} -->

未解决风险（无风险也必须填写“无”）：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_UNRESOLVED_RISKS_LINE}} -->

许可证和正式 release policy 尚未决定。因此本包只允许在已书面授权的发送方与
研究院指定求解器开发部门之间内部评估；接收方不得再分发，且不得把本文件理解为
公共或商业许可。

本节的正确性摘要必须逐字绑定 `correctness.status`、Tet4/Hex8 状态和四项门槛；
性能摘要必须绑定 `performance.status`、用于结论的线程数、speedup、$CV$、门槛和
原始样本数；确定性/clean-room 摘要必须绑定 `verifications` 中三项状态以及对应
证据路径和 SHA-256；偏差摘要必须逐项列出标识、`disposition` 和
`approval_reference`。泛化的“已完成”或单独的 `PASS` 不能代替这些结构化事实。

## 7. 回滚与复现

复现入口为
[`LINUX_FORMAL_RUNBOOK.zh-CN.md`](LINUX_FORMAL_RUNBOOK.zh-CN.md)，验收核对入口为
[`ACCEPTANCE_CHECKLIST.zh-CN.md`](ACCEPTANCE_CHECKLIST.zh-CN.md)，记录结构由
[`ACCEPTANCE_RECORD.schema.json`](ACCEPTANCE_RECORD.schema.json)定义。

复现所需完整源码 SHA：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_REPRODUCTION_SOURCE_COMMIT_LINE}} -->

受控主机 ID：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_CONTROLLED_HOST_ID_LINE}} -->

输入 SHA-256 与字节数：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_INPUT_BINDING_LINE}} -->

完整复现命令/记录位置：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_REPRODUCTION_RECORD_LINE}} -->

如发现交付错误，应暂停使用并按完整源码 SHA、ZIP SHA-256 和交付 ID 撤回该包；
不得覆盖原产物。修复后应使用新的唯一交付 ID 和新的仓库外运行目录，从头执行
正式流程并重新批准。

回滚负责人及联系引用：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_ROLLBACK_OWNER_LINE}} -->

撤回/替换流程引用：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_WITHDRAWAL_LINE}} -->

## 8. 必需批准与接收确认

以下内容是组织审批引用，不是由本模板生成或伪造的签名。

| 角色 | 身份引用 | UTC 时间 | 审批/确认记录号 | 决定 |
|---|---|---|---|---|
| 操作员 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_OPERATOR_APPROVAL_ROW}} -->
| 技术复核人 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_REVIEWER_APPROVAL_ROW}} -->
| 发送方批准/交付批准人 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_APPROVER_APPROVAL_ROW}} -->
| 接收方确认 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | <!-- {{CSC3_DELIVERY_NOTE_RECIPIENT_APPROVAL_ROW}} -->

发送方批准声明：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_SENDER_STATEMENT_LINE}} -->

接收方确认声明：**REQUIRED BEFORE DELIVERY** <!-- {{CSC3_DELIVERY_NOTE_RECIPIENT_STATEMENT_LINE}} -->
