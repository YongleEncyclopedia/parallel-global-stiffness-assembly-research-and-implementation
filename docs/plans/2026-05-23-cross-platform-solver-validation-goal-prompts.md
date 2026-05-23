# Cross-Platform Solver Validation Codex Goal Prompts

These prompts are intended to be copied into separate Codex sessions on the target machines. Each session should use Codex `/goal` so the run can continue across turns until the platform-specific validation package is complete.

Shared invariants for all three platforms:

- Use the current CPU mainline under `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly`.
- Treat `docs/context/current-knowledge-boundary.md`, the CPU README, and `docs/cpu/symbolic_numeric_assembly.md` as the first context files.
- Use `linear_elastic_solid` as the canonical stiffness model. Do not use `legacy_synthetic` for conclusions.
- Use the validation contract: C++ exports `K/F/BC/probes/metadata`, MATLAB solves the self-assembled matrix, and the platform solver exports displacement CSV for probe-level comparison.
- Do not assume solver equivalence just because the solver is mature. Confirm element type, integration rule, material constants, units, BCs, force normalization, node/probe mapping, and displacement components.
- No hard pass/fail threshold is required for external solver comparison. The required output is a traceable difference report with absolute difference, relative difference, maximum-difference location, and explanation status.
- Separate correctness validation from assembly performance. Solver runtime is not assembly runtime.
- Do not commit, push, delete historical assets, or rewrite long-term reports unless explicitly requested in that platform session.

## macOS + COMSOL Prompt

Copy the following into Codex on the macOS host:

````markdown
/goal
你是 macOS 平台上的 Codex 工程与研究助手。请在本机完成 `parallel-global-stiffness-assembly-research-and-implementation` 仓库的 macOS + COMSOL 求解级正确性验证包。macOS 这轮的核心角色是使用 COMSOL 作为成熟有限元求解软件参考，并与 MATLAB 对自研 C++ 导出的 `K/F/BC` 求解结果做 probe 位移对比；macOS 性能结果只作为 Apple Silicon 补充，不作为 Intel/AMD 主结论。

## Hard Boundaries

- 优先在当前工作树上做非破坏性探索；先运行 `git status --short --branch --untracked-files=all`。
- 不 commit，不 push，不重写 Beamer/历史报告，不删除文件。
- 如果工作树已有用户改动，必须读懂并避开；不要回退。
- 如果 COMSOL、MATLAB、CMake、OpenMP 或 Git LFS 不可用，先记录 blocker 和最小安装/路径需求；不要把环境失败伪装成验证失败。
- 不允许用 `legacy_synthetic` 做结论；所有正式 validation 使用 `--stiffness-model linear_elastic_solid`。

## First Context To Read

从仓库根目录开始，先读：

```bash
sed -n '1,140p' docs/context/current-knowledge-boundary.md
sed -n '1,180p' parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md
sed -n '1,180p' parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md
```

确认当前事实：`validation_export` 负责导出矩阵/载荷/约束/probes/metadata，MATLAB 负责求解自研矩阵，COMSOL 只作为独立位移参考。

## Environment Inventory

进入 CPU 子项目：

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
git status --short --branch --untracked-files=all
git lfs pull
python3 scripts/inspect_cpu_platform.py
which cmake || true
which matlab || true
which comsol || true
ls -d /Applications/COMSOL* 2>/dev/null || true
```

记录：

- macOS 版本、CPU 型号、物理核/逻辑核、是否 Apple Silicon。
- CMake、compiler、OpenMP/libomp、MATLAB、COMSOL 版本和实际可执行路径。
- COMSOL 是否支持 batch/no-GUI 自动求解；如果只能 GUI 操作，生成手动导出说明并把未自动化项标为 blocker。

## Build And Repository Verification

```bash
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
python3 tests/correctness/verify_validation_export.py build/cpu-release/bin/validation_export /tmp/pgsa_validation_export_verify
```

如果任何测试失败，先定位并修复；不要继续生成正式 COMSOL 对比结论。

## Validation Cases

固定运行以下四个 case：

- `cantilever_hex8_small`: 结构化 Hex8，对齐 COMSOL 8-node brick / full integration 等价设置。
- `cantilever_hex8_medium`: 中等规模 Hex8，用于检查 sparse pattern 和实际 probe 趋势。
- `cantilever_tet4_small`: Tet4/C3D4 路径，确认既有物理核不退化。
- `cantilever_tet4_medium`: 中等规模 Tet4，用于非结构化/四面体路径趋势。

固定参数：

- `L=1, W=0.2, T=0.1`
- `E=1, nu=0.3`
- `x=0` 面三向位移固定
- `x=L` 端面总量归一化向下力，`load_dof=2, total_load=-1`

先导出自研矩阵并用 MATLAB 求解：

```bash
RESULT_ROOT="results/validation-export/$(date +%F)-macos-comsol"
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-release/bin/validation_export \
  --out-root "$RESULT_ROOT" \
  --run-matlab \
  --matlab-bin matlab
```

检查 `validation_export_manifest.json`、每个 case 的 `K.mtx`、`force.csv`、`bc.csv`、`probes.csv`、`metadata.json`、`*_matlab_displacements.csv`、`*_matlab_probe_summary.csv` 是否存在。

## COMSOL Reference Workflow

优先自动化。如果仓库已有 COMSOL runner/importer，复用它；否则创建最小可追溯 workflow，放在本次 `RESULT_ROOT` 或一个明确的 reusable script 中，并说明为什么放那里。

COMSOL 模型必须与 C++/MATLAB case 等价：

- 几何尺寸与坐标系相同。
- 材料是 small-strain isotropic linear elasticity，`E=1, nu=0.3`。
- `x=0` 面完全固定。
- `x=L` 端面总力为 `-1`，方向对应 C++ 的 `load_dof=2`；如果 COMSOL 使用面载荷，需要证明积分后的总力是 `-1`。
- Hex8 case 必须使用与 C3D8/full-integration 等价或最接近的设置；如果 COMSOL 只能以不同单元/积分规则求解，报告中必须标为 formulation mismatch。
- Tet4 case 必须记录一阶四面体/线性位移场设置；如果使用二阶单元或自动高阶，不能直接称为等价。
- 输出所有 probe 节点或最近点的 `ux, uy, uz`，写成 `*_comsol_displacements.csv`，字段至少包括 `case,node_id_or_probe_id,x,y,z,ux,uy,uz,source`.

如果 COMSOL probe 点与 C++ 节点无法一一对应，必须输出 nearest-node/nearest-point 距离并在报告中说明这会影响差异解释。

## Comparison Report

对每个 case 运行或补齐比较脚本：

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab "$CASE_DIR/${PREFIX}_matlab_displacements.csv" \
  --abaqus "$CASE_DIR/${PREFIX}_comsol_displacements.csv" \
  --probes "$CASE_DIR/${PREFIX}_probes.csv" \
  --out-csv "$CASE_DIR/${PREFIX}_comsol_compare.csv" \
  --out-md "$CASE_DIR/${PREFIX}_comsol_compare.md"
```

如果脚本参数名仍叫 `--abaqus`，可以暂时复用，但报告必须清楚说明 reference solver 是 COMSOL。必要时做一个向后兼容的小改动，让脚本接受 `--reference-solver comsol` 或把列名泛化；改动后补测试。

最终写：

```text
$RESULT_ROOT/macos_comsol_validation_report.md
```

报告必须包含：

- Git branch/commit/dirty status。
- macOS/CPU/MATLAB/COMSOL/CMake/OpenMP 环境。
- 实际命令和结果文件路径。
- 四个 case 的 MATLAB 求解状态。
- 四个 case 的 COMSOL 参考状态。
- 每个 case 的 probe 差异摘要：最大绝对差异、最大相对差异、位置、解释状态。
- 等价性检查表：element formulation、integration、BC、load、units、probe mapping。
- 未自动化或需要人工 COMSOL 导出的步骤。

## Optional macOS Performance Supplement

如果正确性验证完成且时间允许，只跑补充性能，不作为主结论：

```bash
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-release/bin/validation_export \
  --out-root "$RESULT_ROOT/performance-linked-validation" \
  --run-matlab \
  --matlab-bin matlab

python3 scripts/run_symbolic_numeric_eval.py
```

性能说明必须写清 Apple QoS / P/E 控制与 Linux Intel `taskset` 不等价。

## Final Response

最后只汇报：

- 修改或新增了哪些文件。
- 结果目录和核心产物。
- 构建、测试、MATLAB、COMSOL、比较脚本的验证状态。
- 哪些差异可解释，哪些仍是 blocker。
- 不要 commit，不要 push。
````

## Linux Intel + CalculiX Prompt

Copy the following into Codex on the Intel Linux host:

````markdown
/goal
你是 Intel Linux 平台上的 Codex 工程与研究助手。请在本机完成 Linux + CalculiX 的求解级正确性验证包，并保留 Intel 作为 CPU 并行组装主线平台的性能与内存证据。Linux 这轮使用开源 CalculiX 替代商业求解器，和 MATLAB 对自研 C++ `K/F/BC` 的求解结果做 probe 位移对比。

## Hard Boundaries

- 不 commit，不 push，不删除历史结果，不重写 Beamer。
- 开始前运行 `git status --short --branch --untracked-files=all`；若不干净，先说明并避开用户改动。
- 如果 `../../examples/3d-WindTurbineHub.inp` 是 Git LFS pointer，先运行 `git lfs pull`；如果仍是 pointer，停止。
- 如果 CalculiX (`ccx`) 不可用，不要伪造 solver 结果；记录 blocker 或给出最小安装命令。
- 正式 validation 和 benchmark 只能使用 `linear_elastic_solid`，不能用 `legacy_synthetic` 做结论。

## First Context To Read

```bash
sed -n '1,140p' docs/context/current-knowledge-boundary.md
sed -n '1,220p' parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md
sed -n '1,220p' parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md
sed -n '1,230p' docs/plans/2026-05-20-linux-intel-symbolic-memory-codex-prompt.md
```

明确两件事：

1. Solver validation: `validation_export` -> MATLAB solve -> CalculiX displacement CSV -> comparison report。
2. Intel performance: full-host CPU assembly timing/memory is主线证据；核心字段要区分 CSR/AssemblyPlan persistent memory、symbolic temporary、direct/no-symbolic transient、backend extra memory、isolated RSS。

## Environment Inventory

```bash
cd parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly
git status --short --branch --untracked-files=all
git lfs pull
lscpu
python3 scripts/inspect_cpu_platform.py
which cmake || true
which matlab || true
which ccx || true
ccx -v || true
```

记录 Intel CPU model、physical/logical cores、是否 hybrid P/E、NUMA、OpenMP runtime、MATLAB、CalculiX 版本。

## Build And Tests

```bash
cmake -S . -B build/cpu-release -DCMAKE_BUILD_TYPE=Release -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build/cpu-release --parallel
ctest --test-dir build/cpu-release --output-on-failure
python3 tests/correctness/verify_validation_export.py build/cpu-release/bin/validation_export /tmp/pgsa_validation_export_verify
python3 tests/correctness/verify_symbolic_parallel_cli.py build/cpu-release/bin/symbolic_numeric_eval /tmp/pgsa_symbolic_parallel_verify
```

失败先修复，不要继续正式结果。

## Validation Export + MATLAB

```bash
RESULT_ROOT="results/validation-export/$(date +%F)-linux-intel-calculix"
python3 scripts/run_validation_export.py \
  --validation-export build/cpu-release/bin/validation_export \
  --out-root "$RESULT_ROOT" \
  --run-matlab \
  --matlab-bin matlab
```

必须生成并检查四个 case：

- `cantilever_hex8_small`
- `cantilever_hex8_medium`
- `cantilever_tet4_small`
- `cantilever_tet4_medium`

固定参数：`L=1, W=0.2, T=0.1, E=1, nu=0.3`，`x=0` 固定，`x=L` 端面总力 `-1` 向下。

## CalculiX Reference Workflow

优先自动化：为每个 validation case 生成 CalculiX `.inp`，运行 `ccx`，解析 `.frd` 或 `.dat` 中的位移，导出 `*_calculix_displacements.csv`。

要求：

- Hex8 使用 CalculiX 线性 brick，与 C3D8/full integration 等价或明确记录差异。
- Tet4 使用 CalculiX 线性 tetra，与 C3D4 路径等价或明确记录差异。
- 材料、载荷、约束、单位、坐标、probe 节点必须与 `metadata.json` / `probes.csv` 对齐。
- 如果 CalculiX 对某种单元有 locking、reduced/full integration 或 formulation 差异，报告中必须列为解释项。
- 如果需要新增脚本，优先写 reusable 脚本，例如 `scripts/run_calculix_validation.py` 和 `scripts/extract_calculix_displacements.py`，并给出 smoke test 或最小自检。

CSV 字段至少包括：

```text
case,node_id,x,y,z,ux,uy,uz,source
```

## Probe Comparison

对每个 case 生成：

```bash
python3 scripts/compare_validation_displacements.py \
  --matlab "$CASE_DIR/${PREFIX}_matlab_displacements.csv" \
  --abaqus "$CASE_DIR/${PREFIX}_calculix_displacements.csv" \
  --probes "$CASE_DIR/${PREFIX}_probes.csv" \
  --out-csv "$CASE_DIR/${PREFIX}_calculix_compare.csv" \
  --out-md "$CASE_DIR/${PREFIX}_calculix_compare.md"
```

如果比较脚本列名仍写 Abaqus，可做向后兼容泛化；不要破坏已有 Abaqus 用法。比较报告不设硬阈值，但必须输出绝对差异、相对差异、最大差异位置和解释状态。

## Intel Performance And Memory Run

Linux Intel 仍是主线 CPU 平台，必须补一组 full-host 结果。先确定 physical core 范围；如果是 hybrid CPU，记录但本轮先 full-host，不把 P/E 隔离和 full-host 混称。

运行矩阵：

- `serial symbolic + serial numeric`
- `parallel symbolic + cpu_atomic`
- `direct/no-symbolic parallel`
- 可附录 `cpu_private_csr` / `cpu_lock_guard`，但主结论固定 `cpu_atomic`。

建议命令：

```bash
PERF_ROOT="results/$(date +%F)-linux-intel-calculix-validation-performance"
mkdir -p "$PERF_ROOT"

python3 scripts/run_isolated_symbolic_memory_eval.py \
  --symbolic-exe build/cpu-release/bin/symbolic_numeric_eval \
  --out-root "$PERF_ROOT/isolated_symbolic_memory" \
  --mesh inp \
  --inp ../../examples/3d-WindTurbineHub.inp \
  --case-name 3d-WindTurbineHub \
  --stiffness-model linear_elastic_solid \
  --assemblies-list 1 \
  --threads-range "1:$(nproc)" \
  --backend-list atomic \
  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel \
  --max-memory-gb 32
```

如果 `--stiffness-model` 不被某脚本接受，先检查当前 CLI，使用等价 canonical 参数；不要退回 `physics_tet4`，除非文档和结果里明确它只是旧字段 alias 且实际模型是 `linear_elastic_solid`。

## Final Report

写入：

```text
$RESULT_ROOT/linux_intel_calculix_validation_report.md
$PERF_ROOT/linux_intel_calculix_performance_report.md
```

必须包含：

- Git commit、branch、dirty status。
- Intel CPU / OS / compiler / OpenMP / MATLAB / CalculiX 环境。
- CalculiX 等价性检查表。
- 四个 validation case 的 MATLAB 和 CalculiX 状态。
- Probe 差异表和解释。
- Intel full-host 性能/内存摘要，明确 solver runtime 不纳入 assembly runtime。
- 所有实际命令。
- 未验证项和 blocker。

## Final Response

最后只汇报文件、结果目录、验证命令、通过/失败状态和风险；不要 commit，不要 push。
````

## Windows AMD + Abaqus Prompt

Copy the following into Codex on the AMD Windows host:

````markdown
/goal
你是 AMD Windows 平台上的 Codex 工程与研究助手。请在 Windows 原生环境完成 Abaqus 求解级正确性验证，并顺带采集 AMD CPU 平台上的并行组装耗时与内存占用。Windows 这轮的核心角色是利用 Abaqus/Standard 的原生 Windows 支持作为商业求解器参考，同时补充 AMD x86_64 CPU 平台性能证据。

## Hard Boundaries

- 使用 Windows 原生环境优先；不要把 Abaqus 参考求解放进 WSL 里完成。
- 不 commit，不 push，不删除历史文件，不重写长期报告。
- 开始前运行 `git status --short --branch --untracked-files=all`。
- 如果工作树不干净，先说明已有改动并避开；不要回退。
- 如果 Abaqus、MATLAB、MSVC/CMake/OpenMP 或 Git LFS 不可用，记录 blocker，不要伪造结果。
- 正式结论只使用 `linear_elastic_solid`；禁止用 `legacy_synthetic` 支撑结论。
- Solver runtime 和自研 assembly runtime 分开记录，不能混合。

## First Context To Read

在仓库根目录运行：

```powershell
Get-Content docs/context/current-knowledge-boundary.md -TotalCount 160
Get-Content parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md -TotalCount 220
Get-Content parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md -TotalCount 220
```

确认：

- `validation_export` 导出 `K/F/BC/probes/metadata`。
- MATLAB 求解自研 C++ 矩阵。
- Abaqus 导出位移 CSV，进入同一 probe 差异表。
- AMD 性能只比较自研 assembly，不比较 Abaqus 求解耗时。

## Environment Inventory

```powershell
cd parallel_global_stiffness_assembly\cpu_parallel_stiffness_assembly
git status --short --branch --untracked-files=all
git lfs pull
python scripts\inspect_cpu_platform.py
Get-CimInstance Win32_Processor | Format-List Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
where cmake
where python
where matlab
where abaqus
abaqus information=system
```

记录 Windows 版本、AMD CPU 型号、物理核/逻辑核、内存、compiler generator、OpenMP runtime、MATLAB、Abaqus 版本。

## Build And Tests

优先用 Visual Studio 生成器；如果本机标准是 Ninja/MSYS2，也可以用现有可工作的方式，但必须记录。

```powershell
cmake -S . -B build\cpu-release -G "Visual Studio 17 2022" -A x64 -DPGSA_ENABLE_OPENMP=ON -DBUILD_TESTS=ON -DBUILD_BENCHMARKS=ON
cmake --build build\cpu-release --config Release --parallel
ctest --test-dir build\cpu-release -C Release --output-on-failure
```

定位实际 exe：

```powershell
Get-ChildItem build\cpu-release -Recurse -Filter validation_export.exe
Get-ChildItem build\cpu-release -Recurse -Filter symbolic_numeric_eval.exe
```

再运行 validation export 自检；按实际 exe 路径替换：

```powershell
python tests\correctness\verify_validation_export.py build\cpu-release\bin\Release\validation_export.exe $env:TEMP\pgsa_validation_export_verify
python tests\correctness\verify_symbolic_parallel_cli.py build\cpu-release\bin\Release\symbolic_numeric_eval.exe $env:TEMP\pgsa_symbolic_parallel_verify
```

失败先修复，不要继续正式结果。

## Validation Export + MATLAB

```powershell
$Date = Get-Date -Format "yyyy-MM-dd"
$ResultRoot = "results\validation-export\$Date-windows-amd-abaqus"

python scripts\run_validation_export.py `
  --validation-export build\cpu-release\bin\Release\validation_export.exe `
  --out-root $ResultRoot `
  --run-matlab `
  --matlab-bin matlab
```

必须覆盖：

- `cantilever_hex8_small`
- `cantilever_hex8_medium`
- `cantilever_tet4_small`
- `cantilever_tet4_medium`

固定参数：`L=1, W=0.2, T=0.1, E=1, nu=0.3`，`x=0` 固定，`x=L` 总力 `-1` 向下。

## Abaqus Reference Workflow

优先自动化；如仓库已有 Abaqus runner/exporter，复用并补足 Windows 路径。若没有，新增最小脚本并保持可追溯：

- 生成 Abaqus `.inp`：C3D8 对应 Hex8/full integration，C3D4 对应 Tet4。
- 调用 Abaqus/Standard：`abaqus job=<case> input=<case>.inp interactive`。
- 用 Abaqus Python 从 `.odb` 提取节点位移：`abaqus python extract_abaqus_displacements.py --odb <case>.odb --probes <case>_probes.csv --out <case>_abaqus_displacements.csv`。

Abaqus 模型必须对齐：

- 同一坐标、尺寸、材料、单位。
- `x=0` 三向位移固定。
- `x=L` 总力归一化为 `-1`，方向对应 `load_dof=2`。
- C3D8 使用 full integration；如果使用 reduced integration 或默认不同，必须标出。
- C3D4 使用线性四面体。
- probe 节点 ID 和坐标必须能追溯到 `probes.csv`；如果 Abaqus 重新编号，输出映射表。

输出 CSV 字段至少：

```text
case,node_id,x,y,z,ux,uy,uz,source
```

## Probe Comparison

每个 case 生成：

```powershell
python scripts\compare_validation_displacements.py `
  --matlab "$CaseDir\${Prefix}_matlab_displacements.csv" `
  --abaqus "$CaseDir\${Prefix}_abaqus_displacements.csv" `
  --probes "$CaseDir\${Prefix}_probes.csv" `
  --out-csv "$CaseDir\${Prefix}_abaqus_compare.csv" `
  --out-md "$CaseDir\${Prefix}_abaqus_compare.md"
```

不设硬阈值；报告绝对差异、相对差异、最大差异位置、是否可解释。不能因为 Abaqus 是商业软件就直接宣布等价。

## AMD Assembly Performance And Memory

Windows AMD 需要补充 CPU 平台数据。运行前记录电源计划、后台负载、物理核/逻辑核。线程范围至少覆盖 `1..physical_cores`；可以补 logical cores，但不能把超订阅结果混入主结论。

主线矩阵：

- `serial symbolic + serial numeric`
- `parallel symbolic + cpu_atomic`
- `direct/no-symbolic parallel`

附录可跑 `private_csr` / `lock_guard`，但主结论固定 `cpu_atomic`。

建议：

```powershell
$PerfRoot = "results\$Date-windows-amd-abaqus-validation-performance"
New-Item -ItemType Directory -Force $PerfRoot | Out-Null

python scripts\run_isolated_symbolic_memory_eval.py `
  --symbolic-exe build\cpu-release\bin\Release\symbolic_numeric_eval.exe `
  --out-root "$PerfRoot\isolated_symbolic_memory" `
  --mesh inp `
  --inp ..\..\examples\3d-WindTurbineHub.inp `
  --case-name 3d-WindTurbineHub `
  --stiffness-model linear_elastic_solid `
  --assemblies-list 1 `
  --threads-range "1:<PHYSICAL_CORES>" `
  --backend-list atomic `
  --mode-list symbolic_reuse_serial,serial_symbolic_parallel_numeric,parallel_symbolic_reuse,direct_no_symbolic_parallel `
  --max-memory-gb 32
```

把 `<PHYSICAL_CORES>` 替换为 `Get-CimInstance Win32_Processor` 的物理核心数。若脚本无法在 Windows 正确测 isolated RSS，必须修复或明确记录 Windows memory metric fallback，例如 peak working set/private bytes；不能用 estimated bytes 冒充 OS peak RSS。

## Required Reports

写入：

```text
$ResultRoot\windows_amd_abaqus_validation_report.md
$PerfRoot\windows_amd_assembly_performance_report.md
```

报告必须包含：

- Git commit、branch、dirty status。
- Windows/AMD CPU/compiler/OpenMP/MATLAB/Abaqus 环境。
- Abaqus model equivalence checklist。
- 四个 case 的 MATLAB 与 Abaqus 状态。
- Probe comparison summary。
- AMD assembly timing/memory table：threads、mode、backend、amortized/total time、temporary/persistent/backend memory、OS peak memory。
- 明确说明 Abaqus solver runtime 不进入 assembly speedup。
- 所有命令、路径、未验证项、blocker。

## Final Response

最后只汇报：

- 新增/修改文件。
- 结果目录和核心产物。
- 构建、测试、MATLAB、Abaqus、性能 runner 的状态。
- 哪些结论可以带到总报告，哪些只是平台补充。
- 不要 commit，不要 push。
````
