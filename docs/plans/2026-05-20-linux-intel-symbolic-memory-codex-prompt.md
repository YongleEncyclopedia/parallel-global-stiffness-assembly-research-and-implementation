# Linux Intel Symbolic Memory Codex Prompt

Copy the prompt below into the Linux Codex session. It is written for a Linux Intel host starting from a clean `main` worktree.

````markdown
你是 Linux 环境下的 Codex 工程与研究助手。请在当前仓库的干净 `main` 工作树上完成 Linux Intel full-host 符号组装并行化测试与报告包生成。

## Hard Boundaries

- 不新建分支。
- 不 commit。
- 不 push。
- 不更新长期文档、Beamer 或历史报告。
- 只允许在当前 `main` 工作树中留下可由 GitHub Desktop 审阅和提交的代码、脚本、测试、结果数据和报告包。
- 如果工作树一开始不干净，先运行 `git status --short --branch --untracked-files=all` 并停下来说明现有改动，不要覆盖或回退用户改动。
- 如果 `../../examples/3d-WindTurbineHub.inp` 是 Git LFS pointer，停止并提示需要先运行 `git lfs pull`，不要继续跑 benchmark。

## Goal

在 Linux + Intel CPU 上，只测试 full host 的 `1..physical_cores`，不做 P/E 核隔离，不扫逻辑核或超订阅。报告必须回答两个问题：

1. 在已经采用符号结构（CSR/scatter plan）的前提下，`cpu_atomic`、`cpu_private_csr`、`cpu_lock_guard` 哪个数值后端的 speedup/memory tradeoff 最合理。
2. 在同一数值后端、同一线程数下，`serial_symbolic_parallel_numeric` 与 `parallel_symbolic_reuse` 的总耗时、临时内存和 isolated RSS 对比，判断符号阶段本身是否值得并行化。

本轮保持 macOS 当前口径：符号扫描是一轮 full sweep，不改成多次重复取平均。若未来改 repeat=3，macOS 结果也必须重跑。

## Required Working Directory

先进入 CPU 子项目：

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
```

## Required Baseline Checks

```bash
git status --short --branch --untracked-files=all
test ! -f ../../examples/3d-WindTurbineHub.inp || ! head -n 1 ../../examples/3d-WindTurbineHub.inp | grep -q 'version https://git-lfs.github.com/spec/v1'
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
```

如果 `ctest` 失败，先修复测试或构建问题；不要继续正式实验。

## Smoke Test Before WindHub

先用小网格验证新增模式和 RSS runner：

```bash
build/cpu-release/bin/symbolic_numeric_eval \
  --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 \
  --kernel physics_tet4 \
  --assemblies-list 1 \
  --threads-list 1,2 \
  --backend-list atomic,lock_guard \
  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel \
  --csv /tmp/pgsa_symbolic_smoke.csv \
  --json /tmp/pgsa_symbolic_smoke.json \
  --summary-md /tmp/pgsa_symbolic_smoke.md

python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval \
  --out-root /tmp/pgsa_isolated_symbolic_smoke \
  --mesh cube --element tet4 --nx 1 --ny 1 --nz 1 \
  --kernel physics_tet4 \
  --assemblies-list 1 \
  --threads-list 1,2 \
  --backend-list atomic,lock_guard \
  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse
```

检查 smoke CSV 必须包含：

- `strategy_label`
- `serial_symbolic_parallel_numeric`
- `parallel_symbolic_reuse`
- `symbolic_temporary_bytes`
- `symbolic_persistent_bytes`
- `numeric_backend_extra_bytes`
- `estimated_peak_bytes`
- `delta_vs_serial_symbolic_serial_numeric_bytes`
- `isolated_peak_rss_mb`
- `rel_l2` 和 `max_abs`

## Full Linux Intel Run

结果根目录必须使用当天日期：

```bash
RESULT_ROOT="results/$(date +%F)-linux-intel-symbolic-memory-full-host"
mkdir -p "$RESULT_ROOT"
PHYSICAL_CORES="$(python3 - <<'PY'
import os
print(os.cpu_count() or 1)
PY
)"
```

如果仓库工具能更准确识别 physical cores，使用仓库工具输出覆盖 `PHYSICAL_CORES`；否则用 `os.cpu_count()` 并在报告里说明。

运行数值后端 full-host 对照：

```bash
build/cpu-release/bin/benchmark_assembly \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --kernel physics_tet4 \
  --algo atomic,private_csr,lock_guard \
  --threads-range "1:${PHYSICAL_CORES}" \
  --repeat 1 \
  --check \
  --schema-version pgsa-cross-platform-v2-raw \
  --platform-id linux-intel-full-host \
  --run-profile full_host \
  --env-group linux_intel_symbolic_memory \
  --max-memory-gb 32 \
  --csv "$RESULT_ROOT/windhub_backend_tradeoff.csv" \
  --json "$RESULT_ROOT/windhub_backend_tradeoff.json" \
  --summary-md "$RESULT_ROOT/windhub_backend_tradeoff.md"
```

运行逐进程 isolated RSS 符号/数值对照：

```bash
python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval \
  --out-root "$RESULT_ROOT/isolated_symbolic_memory" \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --kernel physics_tet4 \
  --assemblies-list 1 \
  --threads-range "1:${PHYSICAL_CORES}" \
  --backend-list atomic,private_csr,lock_guard \
  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel \
  --max-memory-gb 32
```

生成 v2 package/report：

```bash
python3 scripts/package_cross_platform_results_v2.py \
  --out-dir "$RESULT_ROOT/cross-platform-v2" \
  --platform-id linux-intel-full-host \
  --thread-scaling-csv "$RESULT_ROOT/windhub_backend_tradeoff.csv" \
  --symbolic-csv "$RESULT_ROOT/isolated_symbolic_memory/isolated_symbolic_memory.csv" \
  --lock-benchmark-csv "$RESULT_ROOT/windhub_backend_tradeoff.csv"

python3 scripts/validate_benchmark_package_v2.py "$RESULT_ROOT/cross-platform-v2"
```

如果需要关键图表且仓库没有现成 plotting helper，可在 `RESULT_ROOT` 下生成一次性图表脚本或 notebook 输出，不要写入长期源码目录。至少生成：

- 后端 `amortized_total_ms` 或 `assembly_ms` vs threads。
- 后端 extra memory / estimated peak memory vs threads。
- 同 backend 下 serial symbolic vs parallel symbolic 的 total time、estimated peak、isolated RSS 对比。

## Report Requirements

最终报告必须写入：

```text
$RESULT_ROOT/linux_intel_symbolic_memory_report.md
```

报告必须包含：

- Git commit hash、branch、dirty status。
- CPU model、physical cores、logical cores、OpenMP 环境、`OMP_DYNAMIC`/`OMP_PROC_BIND`/`OMP_PLACES`。
- 所有实际运行命令。
- full host `1..physical_cores` 范围说明，明确没有 P/E 核隔离、没有逻辑核/超订阅。
- 正确性：`rel_l2`、`max_abs`、`status`。
- 内存生命周期分层：persistent symbolic artifacts、parallel symbolic temporary bytes、numeric backend extra bytes、direct/no-symbolic transient bytes、estimated peak bytes、isolated peak RSS。
- 两个主问题的结论：
  - 哪个数值后端的速度/内存权衡最合理。
  - 符号阶段本身并行化是否值得。
- 明确说明本轮不是多次重复取平均，而是与当前 macOS 结果一致的一轮 full sweep。
- 如果 RSS 不可测，标为 blocker；不能用 estimated bytes 冒充 RSS。

## Final Response Format

完成后只汇报：

- 改了哪些文件。
- 生成了哪些结果目录和核心产物。
- 验证命令和结果。
- GitHub Desktop 提交说明建议。
- 未验证项或风险。

不要 commit，不要 push，不要问是否继续。
````
