# CSC3 Demo 正式交付验收清单

> 分发级别：**INTERNAL EVALUATION ONLY**
>
> `CSC3_ACCEPTANCE_CHECKLIST_STATUS=PENDING`
>
> 当前决定：`PENDING`
>
> 规则：任何必选项未完成时，最终状态只能是 `BLOCKED`；任一适用门槛未通过时，
> 最终状态必须是 `FAIL`。不得把空白清单当作验收记录。

本清单应与
[Linux 正式运行手册](LINUX_FORMAL_RUNBOOK.zh-CN.md)、
[机器可读验收记录](ACCEPTANCE_RECORD.schema.json)、规范 Markdown 测试报告和
[交付说明空白模板](DELIVERY_NOTE_TEMPLATE.zh-CN.md)一起使用。正式操作时先把本清单
复制到仓库外；完成全部核对并取得四方确认后，将上述机器状态标记改为
`CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS`。方括号内填写 `PASS`、`FAIL`、
`BLOCKED` 或 `N/A`；只有明确写明理由时才允许 `N/A`。

## A. 交付标识与授权

- [ ] 交付 ID：`REQUIRED BEFORE DELIVERY`
- [ ] Issue #44 URL：`REQUIRED BEFORE DELIVERY`
- [ ] Demo 版本：`REQUIRED BEFORE DELIVERY`
- [ ] 完整源码 SHA：`REQUIRED BEFORE DELIVERY`
- [ ] 候选源码 ZIP 文件名及 SHA-256：`REQUIRED BEFORE DELIVERY`
- [ ] 授权与接收方范围已由仓库所有者书面确认：`REQUIRED BEFORE DELIVERY`
- [ ] 接收组织及部门：`REQUIRED BEFORE DELIVERY`
- [ ] 指定接收人身份引用：`REQUIRED BEFORE DELIVERY`
- [ ] 分发标记逐字为 **INTERNAL EVALUATION ONLY**：`REQUIRED BEFORE DELIVERY`
- [ ] 已确认当前无公开许可证，不授予公开、转授权或再分发权：
  `REQUIRED BEFORE DELIVERY`

## B. 源码与 LFS 输入身份

- [ ] 完整、非 shallow、非 sparse checkout：`REQUIRED BEFORE DELIVERY`
- [ ] `git rev-parse HEAD` 与交付源码 SHA 完全相同：`REQUIRED BEFORE DELIVERY`
- [ ] 开始与结束时 `git status --porcelain=v1 --untracked-files=all` 均为空：
  `REQUIRED BEFORE DELIVERY`
- [ ] 输入路径严格为 `examples/3d-WindTurbineHub.inp`：
  `REQUIRED BEFORE DELIVERY`
- [ ] WindHub 输入已由 Git LFS 实体化，不是 pointer：`REQUIRED BEFORE DELIVERY`
- [ ] 实体文件字节数与 `HEAD` LFS pointer 的 `size` 相同：
  `REQUIRED BEFORE DELIVERY`
- [ ] 实体文件 SHA-256 与 `HEAD` LFS pointer 的 `oid sha256` 相同：
  `REQUIRED BEFORE DELIVERY`

## C. 受控主机与环境记录

- [ ] 受控主机 ID：`REQUIRED BEFORE DELIVERY`
- [ ] 物理 Linux `x86_64`/`amd64` Intel 主机：`REQUIRED BEFORE DELIVERY`
- [ ] `host-preflight.txt` 包含 UTC、hostname、OS/kernel、CPU、NUMA/cpuset、
  内存、工具链、OpenMP、governor/turbo/SMT：`REQUIRED BEFORE DELIVERY`
- [ ] GCC、CMake、Ninja、Python、Git、Git LFS 版本已记录：
  `REQUIRED BEFORE DELIVERY`
- [ ] `OMP_DYNAMIC=false`、`OMP_PROC_BIND=close`、`OMP_PLACES=cores`：
  `REQUIRED BEFORE DELIVERY`
- [ ] 正式线程集合包含 $p \in \{1,2,4,8,16\}$ 及物理核心数，且实际线程团队
  均与请求相同：`REQUIRED BEFORE DELIVERY`
- [ ] 预热 $W = 2$、正式重复 $R = 7$、摊销次数 $m = 1$：
  `REQUIRED BEFORE DELIVERY`
- [ ] 测试期间主机负载和频率策略满足本单位受控实验规则，偏差已记录：
  `REQUIRED BEFORE DELIVERY`

## D. 自动测试与正确性

- [ ] CTest 精确执行以下十项且全部 `PASS`，无 skip/not-run：
  `REQUIRED BEFORE DELIVERY`

  1. `Csc3DemoTests`
  2. `Csc3DemoConsumer`
  3. `Csc3DemoCorrectness`
  4. `Csc3DemoBenchmarkTiming`
  5. `Csc3DemoBenchmarkEngine`
  6. `Csc3DemoBenchmarkIo`
  7. `Csc3DemoInpCase`
  8. `Csc3DemoWindHubBenchmark`
  9. `Csc3DemoBenchmarkRunner`
  10. `Csc3DemoAtomicContention`

- [ ] Tet4 与 Hex8 的 CSC3 结构逐项一致、scatter 合法、所有数值有限：
  `REQUIRED BEFORE DELIVERY`
- [ ] 矩阵 Frobenius 相对误差满足 $e_F \le 10^{-8}$：
  `REQUIRED BEFORE DELIVERY`
- [ ] 矩阵最大绝对误差满足
  $e_{\max} \le 10^{-10} + 10^{-8}\max |K_s|$：
  `REQUIRED BEFORE DELIVERY`
- [ ] Tet4 与 Hex8 位移相对误差满足 $e_u \le 10^{-8}$：
  `REQUIRED BEFORE DELIVERY`
- [ ] Tet4 与 Hex8 自由度方程相对残差满足
  $r_{\mathrm{rel}} \le 10^{-10}$：`REQUIRED BEFORE DELIVERY`
- [ ] 复核人理解：位移测试证明组装结果能进入求解流程，但不等于独立商业求解器
  验证：`REQUIRED BEFORE DELIVERY`

## E. 原始样本与性能门槛

- [ ] `benchmark_samples.csv` 保留每个线程、每次正式重复的原始样本：
  `REQUIRED BEFORE DELIVERY`
- [ ] `benchmark_summary.json` 的统计量由原始样本重新计算且与报告一致：
  `REQUIRED BEFORE DELIVERY`
- [ ] 至少一个 $p > 1$ 的配置满足
  $S_{\mathrm{numeric}}(p) \ge 1.5$：`REQUIRED BEFORE DELIVERY`
- [ ] 至少一个 $p > 1$ 的配置满足
  $S_{\mathrm{symbolic}}(p) > 1$：`REQUIRED BEFORE DELIVERY`
- [ ] 上述两个用于结论的配置均满足 $CV \le 0.05$：
  `REQUIRED BEFORE DELIVERY`
- [ ] symbolic、numeric、端到端和摊销时间均完整报告，没有选择性删除慢样本：
  `REQUIRED BEFORE DELIVERY`
- [ ] CI runner 计时没有被用作正式性能结论：`REQUIRED BEFORE DELIVERY`

## F. 报告、身份绑定与可复现包

- [ ] `run_manifest.json` 的状态为 `PASS`、证据级别为 `formal`、报告意图为
  `delivery`：`REQUIRED BEFORE DELIVERY`
- [ ] `after-build`、`before-benchmark`、`after-benchmark` 三阶段源码和输入身份
  检查全部 `PASS`：`REQUIRED BEFORE DELIVERY`
- [ ] 规范 Markdown 报告由当前提交的 `generate_test_report.py` 从五个原始证据
  生成，未人工改写：`REQUIRED BEFORE DELIVERY`
- [ ] 报告中的源码 SHA、证据 `source.commit_sha`、ZIP `BUILD_INFO.json` 的源码
  SHA 与待交付源码 SHA 完全相同：`REQUIRED BEFORE DELIVERY`
- [ ] 证据 SHA 与报告、manifest 和 `SHA256SUMS` 中的记录完全一致：
  `REQUIRED BEFORE DELIVERY`
- [ ] `SOURCE_COMMIT` 与上述源码 SHA 完全相同：`REQUIRED BEFORE DELIVERY`
- [ ] 自动阶段状态严格为 `PACKAGE_CANDIDATE`，没有提前声明正式 `PASS`：
  `REQUIRED BEFORE DELIVERY`
- [ ] 候选 `SHA256SUMS` 覆盖原始证据、报告、主机记录、verifier 输出与候选 ZIP，
  且 `sha256sum -c` 通过：`REQUIRED BEFORE DELIVERY`
- [ ] 确定性打包：同一输入连续打包两次，两个 ZIP 经 `cmp` 字节级相同：
  `REQUIRED BEFORE DELIVERY`
- [ ] manifest-only 验证 `PASS`：`REQUIRED BEFORE DELIVERY`
- [ ] 完整 clean-room 配置、构建、十项 CTest 与独立 consumer 验证 `PASS`：
  `REQUIRED BEFORE DELIVERY`
- [ ] `validate_acceptance_record.py` 已被指定为四方批准后的必经独立复验；若它
  不返回 `PASS`，则不得运行 finalizer：
  `REQUIRED BEFORE DELIVERY`
- [ ] `finalize_delivery.py` 的目标目录在运行前不存在；已确认只有本清单完成后才
  运行 finalizer，且其成功标准是原子生成最终目录，并由 `FINAL_SHA256SUMS`
  覆盖候选 ZIP、验收 JSON、完成版清单、完成版交付说明、验收证据副本与
  `FINALIZATION.json`：
  `REQUIRED BEFORE DELIVERY`
- [ ] Markdown 是权威报告；如提供 PDF，PDF 仅为展示派生件并有独立 SHA-256，
  没有替代或修改 Markdown：`REQUIRED BEFORE DELIVERY`

## G. 偏差、风险与决定

- [ ] 偏差清单（无偏差也必须写“无”并说明）：`REQUIRED BEFORE DELIVERY`
- [ ] 已知限制与非目标：`REQUIRED BEFORE DELIVERY`
- [ ] 未解决 blocker：`REQUIRED BEFORE DELIVERY`
- [ ] 回滚与复现路径：`REQUIRED BEFORE DELIVERY`
- [ ] 最终决定只能为 `PASS`、`FAIL` 或 `BLOCKED`：
  `REQUIRED BEFORE DELIVERY`
- [ ] 最终决定理由：`REQUIRED BEFORE DELIVERY`

## H. 人员确认

以下字段记录身份引用、UTC 时间和组织内审批记录号；不要伪造手写或数字签名。

- [ ] 操作员：身份引用 `REQUIRED BEFORE DELIVERY`；UTC `REQUIRED BEFORE DELIVERY`；
  记录号 `REQUIRED BEFORE DELIVERY`
- [ ] 技术复核人：身份引用 `REQUIRED BEFORE DELIVERY`；UTC
  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`
- [ ] 交付批准人：身份引用 `REQUIRED BEFORE DELIVERY`；UTC
  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`
- [ ] 接收方确认：身份引用 `REQUIRED BEFORE DELIVERY`；UTC
  `REQUIRED BEFORE DELIVERY`；记录号 `REQUIRED BEFORE DELIVERY`

最终状态：`REQUIRED BEFORE DELIVERY`

最终验收记录文件：`REQUIRED BEFORE DELIVERY`

最终 ZIP SHA-256：`REQUIRED BEFORE DELIVERY`
