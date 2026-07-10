# Linux Intel symbolic-parallel backend raw data

This package reruns the original isolated symbolic-memory experiment style used by the monthly-report figure.

Measurement scope:
- Baseline: serial symbolic assembly + serial numeric assembly.
- Parallel rows: parallel symbolic assembly + parallel numeric assembly.
- Direct no-symbolic assembly is intentionally excluded.
- Five numeric backends are included: atomic, private_csr, lock_guard, coloring, row_owner.
- Thread range: 1..20.
- Repetition policy: one quick isolated run per row.
- Memory: isolated subprocess peak RSS.
- Timing: symbolic_total_ms + numeric_ms = amortized_total_ms.

Linux side only generates raw data. Plotting is done later on the Mac side.

## 历史 tar 清理来源

Issue #28 删除了源码树根部的归档 `linux_intel_symbolic_parallel_backends_raw_2026-06-26.tar.gz`。删除前记录：

- tar SHA256：`71910e33e0b8a1c3dbe564fba407e44599c3fb752126c0d059f79c8299209bf8`
- 比较结论：归档与清理前基线 `eca50af` 的展开目录共同文件中，`isolated_symbolic_memory/isolated_symbolic_memory.csv` 仅有 CRLF/LF 差异，统一为 LF 后逐字节一致；其余共同文件原始字节一致。
- 唯一成员：归档只多出 `run.log`，已从该精确成员恢复到本目录，未覆盖其他文件。
- `run.log` SHA256：`48d7034d7ce565b68708216e89d24583c1380e1374c6b901431dd12705681310`
- `run.log` 字节数：`97470`
- 成员：`README_raw_data.md`
- 成员：`platform_info.txt`
- 成员：`run.log`
- 成员：`run_commands.sh`
- 成员：`isolated_symbolic_memory/isolated_symbolic_memory.csv`
- 成员：`isolated_symbolic_memory/isolated_symbolic_memory.json`
- 成员：`isolated_symbolic_memory/isolated_symbolic_memory.md`

本节记录 tar 的原始哈希、成员与唯一日志来源；后续不得用重新打包的 tar 替代这些来源证据。

机器可读逐成员哈希见 [`../2026-06-26-archive-provenance.tsv`](../2026-06-26-archive-provenance.tsv)；其中 `working_tree_sha256` 对共同文件记录清理前基线 `eca50af`，对 `run.log` 记录恢复后的文件。
