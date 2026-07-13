# CSC3 Demo：Linux Intel 正式验收运行手册

## 1. 用途与边界

本手册用于在登记过的物理 Linux `x86_64`/`amd64` Intel 主机上，从一个
**确定的完整提交**生成 WindHub 正式证据、规范测试报告和可复现源码包。只有
整段流程为 `PASS`，且
[正式验收清单](ACCEPTANCE_CHECKLIST.zh-CN.md)完成四方确认后，产物才可以作为
研究院求解器开发部门的内部验收候选。

以下内容不构成公开发布授权。所有产物均为 **INTERNAL EVALUATION ONLY**；
许可证仍未确定，不得公开、转授权或再分发。GitHub CI 计时只用于工程反馈，
**不得作为正式性能结论**。规范证据报告是由证据生成器写出的 Markdown；PDF
只能是后续展示派生件，不能替代、编辑或重新定义已通过 SHA-256 绑定的 Markdown。

状态语义：

- `PASS`：全部自动门槛和人工核对项通过；
- `FAIL`：流程完整执行，但一个或多个正确性、性能或验证门槛未通过；
- `BLOCKED`：主机、输入、工具链、身份或授权前置条件不足，不能形成有效验收结论；
- `PENDING`：尚未执行或尚未完成复核，不能对外声称验收通过。

## 2. 操作员必须先取得的信息

开始前由仓库维护者提供并登记：

1. 待验收的完整 40 位小写 `EXPECTED_SOURCE_SHA`；该提交必须已经合入待交付主线；
2. 受控物理主机的 `CONTROLLED_HOST_ID`；虚拟机和 GitHub runner 不适用；
3. 本次唯一的 `BUNDLE_ID`，格式为小写字母或数字开头，其余仅可含小写字母、
   数字、点、下划线和连字符；
4. 仓库外、尚不存在的绝对目录 `RUN_ROOT`；
5. Issue
   [#44](https://github.com/YongleEncyclopedia/parallel-global-stiffness-assembly-research-and-implementation/issues/44)
   的本次 Linux 机器 start comment 已登记。

主机至少需要 Git、Git LFS、Python `3.11`、CMake `3.21`、Ninja、GCC `9`
及其 `libgomp`。正式线程扫描为
$p \in \{1,2,4,8,16,p_{\mathrm{physical}}\}$，去重并保留该顺序；预热次数为
$W = 2$，正式重复次数为 $R = 7$，摊销次数为 $m = 1$。

## 3. 唯一规范命令

在一个**完整、非 shallow、非 sparse** 的全仓库 checkout 根目录中执行下面整段
命令。只替换开头四个 `REQUIRED` 值；不要删减线程、样本或身份检查。`RUN_ROOT`
必须位于仓库之外且执行前不存在。

```bash
set -euo pipefail
export LC_ALL=C
export TZ=UTC
unset PYTHONOPTIMIZE PYTHONPATH PYTHONHOME
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
export OMP_DYNAMIC=false
export OMP_PROC_BIND=close
export OMP_PLACES=cores

export EXPECTED_SOURCE_SHA='REQUIRED-40-LOWERCASE-HEX-SOURCE-SHA'
export CONTROLLED_HOST_ID='REQUIRED-REGISTERED-CONTROLLED-HOST-ID'
export BUNDLE_ID='REQUIRED-LOWERCASE-BUNDLE-ID'
export RUN_ROOT='/absolute/repository-external/REQUIRED-RUN-ROOT'

: "${EXPECTED_SOURCE_SHA:?EXPECTED_SOURCE_SHA is required}"
: "${CONTROLLED_HOST_ID:?CONTROLLED_HOST_ID is required}"
: "${BUNDLE_ID:?BUNDLE_ID is required}"
: "${RUN_ROOT:?RUN_ROOT is required}"
[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
[[ "$BUNDLE_ID" =~ ^[a-z0-9][a-z0-9._-]{0,127}$ ]]
[[ "$RUN_ROOT" = /* ]]
[[ -x "$CC" && -x "$CXX" ]]

for command in git python3 cmake ninja sha256sum stat cmp; do
  command -v "$command" >/dev/null
done
git lfs version >/dev/null

REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_ROOT="$(realpath -- "$REPO_ROOT")"
cd "$REPO_ROOT"
[[ "$(git rev-parse --is-inside-work-tree)" == true ]]
[[ "$(git rev-parse --is-shallow-repository)" == false ]]
[[ "$(git config --bool core.sparseCheckout || true)" != true ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
git cat-file -e "${EXPECTED_SOURCE_SHA}^{commit}"
git checkout --detach "$EXPECTED_SOURCE_SHA"
[[ "$(git rev-parse HEAD)" == "$EXPECTED_SOURCE_SHA" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]

RUN_ROOT="$(realpath -m -- "$RUN_ROOT")"
case "$RUN_ROOT" in
  "$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "RUN_ROOT must be outside the repository" >&2
    exit 2
    ;;
esac
[[ ! -e "$RUN_ROOT" ]]
install -d -m 0700 "$RUN_ROOT"

ARCH="$(uname -m)"
[[ "$ARCH" =~ ^(x86_64|amd64)$ ]]
grep -q '^vendor_id[[:space:]]*:[[:space:]]*GenuineIntel$' /proc/cpuinfo

python3 - <<'PY'
import re
import subprocess

version = subprocess.check_output(["cmake", "--version"], text=True)
match = re.search(r"cmake version (\d+)\.(\d+)", version)
if match is None or tuple(map(int, match.groups())) < (3, 21):
    raise SystemExit("CMake 3.21 or newer is required")
PY

INPUT_REL='examples/3d-WindTurbineHub.inp'
INPUT="$REPO_ROOT/$INPUT_REL"
git lfs pull --include="examples/3d-WindTurbineHub.inp" --exclude=''
git ls-files --error-unmatch -- "$INPUT_REL" >/dev/null
LFS_POINTER="$(git show HEAD:examples/3d-WindTurbineHub.inp)"
LFS_OID="$(printf '%s\n' "$LFS_POINTER" | sed -n 's/^oid sha256:\([0-9a-f]\{64\}\)$/\1/p')"
LFS_SIZE="$(printf '%s\n' "$LFS_POINTER" | sed -n 's/^size \([0-9][0-9]*\)$/\1/p')"
[[ "$LFS_OID" =~ ^[0-9a-f]{64}$ ]]
[[ "$LFS_SIZE" =~ ^[0-9]+$ ]]
[[ -f "$INPUT" ]]
[[ "$(sha256sum "$INPUT" | awk '{print $1}')" == "$LFS_OID" ]]
[[ "$(stat -c %s "$INPUT")" == "$LFS_SIZE" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]

DEMO_ROOT="$REPO_ROOT/demos/csc3_symmetric_assembly_demo"
BUILD_DIR="$RUN_ROOT/build"
EVIDENCE="$RUN_ROOT/evidence"
REPORT="$RUN_ROOT/$BUNDLE_ID-test-report.zh-CN.md"

{
  echo '## UTC'; date -u '+%Y-%m-%dT%H:%M:%SZ'
  echo '## hostname'; hostname
  echo '## kernel'; uname -a
  echo '## OS'; test ! -r /etc/os-release || cat /etc/os-release
  echo '## CPU'; lscpu
  echo '## NUMA'; command -v numactl >/dev/null && numactl --hardware || true
  echo '## cpuset'; grep -E '^(Cpus_allowed_list|Mems_allowed_list):' /proc/self/status || true
  echo '## memory'; cat /proc/meminfo
  echo '## compiler'; g++ --version
  echo '## CMake'; cmake --version
  echo '## Ninja'; ninja --version
  echo '## Python'; python3 --version
  echo '## Git'; git --version
  echo '## Git LFS'; git lfs version
  echo '## OpenMP environment'
  env | grep -E '^(OMP_DYNAMIC|OMP_PROC_BIND|OMP_PLACES)=' | sort
  echo '## CPU governor'
  test ! -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor || \
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
  echo '## Intel turbo'
  test ! -r /sys/devices/system/cpu/intel_pstate/no_turbo || \
    cat /sys/devices/system/cpu/intel_pstate/no_turbo
  echo '## generic boost'
  test ! -r /sys/devices/system/cpu/cpufreq/boost || \
    cat /sys/devices/system/cpu/cpufreq/boost
  echo '## SMT'
  test ! -r /sys/devices/system/cpu/smt/active || \
    cat /sys/devices/system/cpu/smt/active
  echo '## source'; git rev-parse HEAD
  echo '## expected source'; printf '%s\n' "$EXPECTED_SOURCE_SHA"
  echo '## controlled host ID'; printf '%s\n' "$CONTROLLED_HOST_ID"
  echo '## status'; git status --porcelain=v1 --untracked-files=all
  echo '## WindHub SHA-256'; sha256sum "$INPUT"
  echo '## WindHub bytes'; stat -c %s "$INPUT"
} > "$RUN_ROOT/host-preflight.txt"

THREADS="$(python3 - "$DEMO_ROOT" "$BUILD_DIR" "$CONTROLLED_HOST_ID" <<'PY'
import importlib.util
import sys
from pathlib import Path

demo_root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "csc3_formal_runner", demo_root / "scripts" / "run_benchmark.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load run_benchmark.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
provenance = module.collect_provenance(demo_root, Path(sys.argv[2]), sys.argv[3])
physical_core_count = int(provenance["environment"]["physical_core_count"])
ordered = []
for value in [1, 2, 4, 8, 16, physical_core_count]:
    if value not in ordered:
        ordered.append(value)
print(",".join(map(str, ordered)))
PY
)"
[[ "$THREADS" =~ ^[1-9][0-9]*(,[1-9][0-9]*)*$ ]]
printf 'requested_threads=%s\n' "$THREADS" | tee -a "$RUN_ROOT/host-preflight.txt"

set +e
python3 "$DEMO_ROOT/scripts/run_benchmark.py" \
  --case windhub \
  --input "$INPUT" \
  --source-dir "$DEMO_ROOT" \
  --build-dir "$BUILD_DIR" \
  --out-root "$EVIDENCE" \
  --threads-list "$THREADS" \
  --warmup 2 \
  --repeat 7 \
  --amortization-count 1 \
  --evidence-level formal \
  --preset delivery \
  --report-intent delivery \
  --controlled-host-id "$CONTROLLED_HOST_ID" \
  2>&1 | tee "$RUN_ROOT/formal-run.log"
RUN_RC=${PIPESTATUS[0]}
set -e

REPORT_RC=2
if [[ -f "$EVIDENCE/run_manifest.json" ]]; then
  set +e
  python3 "$DEMO_ROOT/scripts/generate_test_report.py" \
    --manifest "$EVIDENCE/run_manifest.json" \
    --out-md "$REPORT" \
    2>&1 | tee "$RUN_ROOT/report-generation.log"
  REPORT_RC=${PIPESTATUS[0]}
  set -e
fi
if (( RUN_RC != 0 || REPORT_RC != 0 )); then
  echo 'Formal run is FAIL or BLOCKED; retain evidence/report and do not package.' >&2
  exit 1
fi

python3 - "$EVIDENCE/run_manifest.json" "$EXPECTED_SOURCE_SHA" \
  "$CONTROLLED_HOST_ID" "$INPUT_REL" \
  "$DEMO_ROOT/tests/ctest/expected-ci-tests.txt" "$EVIDENCE/ctest.xml" <<'PY'
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_sha, controlled_host_id, input_rel = sys.argv[2:5]
assert manifest["status"] == "PASS"
assert manifest["evidence_level"] == "formal"
assert manifest["report_intent"] == "delivery"
assert manifest["source"]["commit_sha"] == expected_sha
assert manifest["source"]["source_dirty_at_start"] is False
assert manifest["environment"]["controlled_host_id"] == controlled_host_id
assert manifest["input"]["repository_relative_path"] == input_rel
assert manifest["input"]["materialized"] is True
assert manifest["input"]["tracked"] is True
assert manifest["input"]["matches_head_lfs"] is True
assert manifest["input"]["sha256"] == manifest["input"]["head_lfs_oid_sha256"]
assert manifest["input"]["size_bytes"] == manifest["input"]["head_lfs_size_bytes"]
checks = manifest["identity_checks"]
assert [check["phase"] for check in checks] == [
    "after-build", "before-benchmark", "after-benchmark"
]
assert all(check["status"] == "PASS" and check["errors"] == [] for check in checks)

expected_tests = Path(sys.argv[5]).read_text(encoding="utf-8").splitlines()
assert len(expected_tests) == 10
root = ET.parse(sys.argv[6]).getroot()
for element in root.iter():
    tag = element.tag.rsplit("}", 1)[-1].lower()
    assert tag not in {"failure", "error", "skipped"}
    for attribute in ("failures", "errors", "skipped", "disabled", "notrun"):
        if attribute in element.attrib:
            assert int(element.attrib[attribute]) == 0
actual_tests = [
    element.attrib["name"]
    for element in root.iter()
    if element.tag.rsplit("}", 1)[-1] == "testcase"
]
assert actual_tests == expected_tests
PY

# Expected inventory: Csc3DemoTests, Csc3DemoConsumer, Csc3DemoCorrectness,
# Csc3DemoBenchmarkTiming, Csc3DemoBenchmarkEngine, Csc3DemoBenchmarkIo,
# Csc3DemoInpCase, Csc3DemoWindHubBenchmark, Csc3DemoBenchmarkRunner,
# Csc3DemoAtomicContention.

python3 "$DEMO_ROOT/scripts/create_delivery_package.py" \
  --external-evidence-dir "$EVIDENCE" \
  --external-report "$REPORT" \
  --bundle-id "$BUNDLE_ID" \
  --out-dir "$RUN_ROOT/dist-a" > "$RUN_ROOT/package-a.json"
python3 "$DEMO_ROOT/scripts/create_delivery_package.py" \
  --external-evidence-dir "$EVIDENCE" \
  --external-report "$REPORT" \
  --bundle-id "$BUNDLE_ID" \
  --out-dir "$RUN_ROOT/dist-b" > "$RUN_ROOT/package-b.json"

ZIP_A="$(python3 - "$RUN_ROOT/package-a.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["archive"])
PY
)"
ZIP_B="$(python3 - "$RUN_ROOT/package-b.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["archive"])
PY
)"
case "$ZIP_A" in "$RUN_ROOT/dist-a/"*) ;; *) exit 2 ;; esac
case "$ZIP_B" in "$RUN_ROOT/dist-b/"*) ;; *) exit 2 ;; esac
ZIP_A_REL="${ZIP_A#"$RUN_ROOT/"}"
ZIP_B_REL="${ZIP_B#"$RUN_ROOT/"}"
cmp --silent "$ZIP_A" "$ZIP_B"
ZIP_SHA256="$(sha256sum "$ZIP_A" | awk '{print $1}')"
{
  echo 'status=PASS'
  printf 'zip_a=%s\n' "$ZIP_A_REL"
  printf 'zip_b=%s\n' "$ZIP_B_REL"
  printf 'sha256=%s\n' "$ZIP_SHA256"
} > "$RUN_ROOT/deterministic-package.txt"

python3 "$DEMO_ROOT/scripts/verify_delivery_package.py" \
  "$ZIP_A" --manifest-only | tee "$RUN_ROOT/manifest-only-verification.json"
python3 "$DEMO_ROOT/scripts/verify_delivery_package.py" \
  "$ZIP_A" 2>&1 | tee "$RUN_ROOT/clean-room-verification.log"

printf '%s\n' "$EXPECTED_SOURCE_SHA" > "$RUN_ROOT/SOURCE_COMMIT"
REPORT_REL="${REPORT#"$RUN_ROOT/"}"
(
  cd "$RUN_ROOT"
  sha256sum \
    SOURCE_COMMIT \
    host-preflight.txt \
    formal-run.log \
    report-generation.log \
    package-a.json \
    package-b.json \
    deterministic-package.txt \
    evidence/run_manifest.json \
    evidence/ctest.xml \
    evidence/benchmark_samples.csv \
    evidence/benchmark_summary.json \
    evidence/summary.md \
    "$REPORT_REL" \
    "$ZIP_A_REL" \
    manifest-only-verification.json \
    clean-room-verification.log > SHA256SUMS
  sha256sum -c SHA256SUMS
)
printf 'formal_package=%s\n' "$ZIP_A"
printf 'formal_package_sha256=%s\n' "$ZIP_SHA256"
```

脚本会执行真正的 OpenMP 路径，并独立确认精确源码 SHA、干净状态、规范 LFS
输入、三阶段身份检查和严格十项 CTest（无 `skipped`、`disabled` 或 `notrun`）。
它随后用完全相同输入打包两次，以 `cmp` 证明字节级确定性，再分别执行
manifest-only 和完整 clean-room 验证。

## 4. 结果处理

成功时，不要只发送 ZIP。应把以下内容作为同一内部交付档案保存：

- `dist-a/csc3-symmetric-assembly-demo-v0.2.0+<short-sha>.zip`；
- `SOURCE_COMMIT` 与 `SHA256SUMS`；
- `host-preflight.txt`、`deterministic-package.txt`、manifest-only verifier JSON、
  完整 clean-room verifier 日志；
- `evidence/` 中五个原始证据文件；
- 规范 Markdown 测试报告；
- 按 [JSON Schema](ACCEPTANCE_RECORD.schema.json) 填写的验收记录；
- 完成签认的[正式验收清单](ACCEPTANCE_CHECKLIST.zh-CN.md)和
  [交付说明](DELIVERY_NOTE.zh-CN.md)。

如果流程产生有效 `FAIL` 或 `BLOCKED` 证据，应**保留**完整证据目录、报告、
日志和主机记录用于诊断；不得创建或提交验收 ZIP，不得选择性重跑、删除慢样本
或只保留有利结果。操作员应把完整命令、状态、阻塞原因和产物路径记录到
Issue #44。只有修复原因后，才能使用新的唯一 `RUN_ROOT` 与新的运行记录从头重跑。

完成 Linux 运行后，机器 finish comment 必须按根 `AGENTS.md` 记录 base/end
SHA、主机和工具链、分支或 detached SHA、命令、每项 `PASS`/`FAIL`、产物路径及
剩余 blocker。正式交付前还必须逐项执行下一份验收清单；自动 `PASS` 不会替代
授权人和接收方确认。
