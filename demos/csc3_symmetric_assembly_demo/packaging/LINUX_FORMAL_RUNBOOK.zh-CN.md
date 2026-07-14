# CSC3 Demo：Linux Intel 正式验收运行手册

## 1. 用途与边界

本手册用于在登记过的物理 Linux `x86_64`/`amd64` Intel 主机上，从一个
**确定的完整提交**生成 WindHub 正式证据、规范测试报告和可复现源码候选包。
自动流程的成功终态只能是 `PACKAGE_CANDIDATE`；它不等于正式验收通过。只有
[正式验收清单](ACCEPTANCE_CHECKLIST.zh-CN.md)完成四方确认、机器可读记录通过
跨字段重算，且最终封包程序生成 `FINAL_SHA256SUMS` 后，产物才是可提交给研究院
求解器开发部门的内部正式交付档案。

以下内容不构成公开发布授权。所有产物均为 **INTERNAL EVALUATION ONLY**；
许可证仍未确定，不得公开、转授权或再分发。GitHub CI 计时只用于工程反馈，
**不得作为正式性能结论**。规范证据报告是由证据生成器写出的 Markdown；PDF
只能是后续展示派生件，不能替代、编辑或重新定义已通过 SHA-256 绑定的 Markdown。

状态语义：

- `PACKAGE_CANDIDATE`：自动门槛通过并形成候选源码包，但人工确认与最终封包尚未完成；
- `PASS`：全部自动门槛、跨字段重算、四方确认和最终封包均通过；
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
及其 `libgomp`。在开始规范命令前，用同一个 `python3` 执行
`python3 -m pip install -r demos/csc3_symmetric_assembly_demo/requirements-test.txt`；
正式流程会再次验证该依赖。正式线程扫描为
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

for variable in \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_DIR GIT_GRAFT_FILE \
  GIT_INDEX_FILE GIT_NAMESPACE GIT_OBJECT_DIRECTORY GIT_REPLACE_REF_BASE \
  GIT_WORK_TREE; do
  if [[ -n "${!variable-}" ]]; then
    echo "Git object interpretation override is forbidden: $variable" >&2
    exit 2
  fi
done
export GIT_NO_REPLACE_OBJECTS=1
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_ROOT="$(realpath -- "$REPO_ROOT")"
RUN_ROOT="$(realpath -m -- "$RUN_ROOT")"
case "$RUN_ROOT" in
  "$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "RUN_ROOT must be outside the repository" >&2
    exit 2
    ;;
esac
[[ ! -e "$RUN_ROOT" ]]
install -d -m 0700 "$RUN_ROOT"

RUNBOOK_LOG="$RUN_ROOT/runbook.log"
OUTCOME_RECORD="$RUN_ROOT/acceptance-outcome.json"
HOST_PREFLIGHT="$RUN_ROOT/host-preflight.txt"
RUNBOOK_STATUS=BLOCKED
RUNBOOK_REASON='formal acceptance preflight did not complete'
RUNBOOK_PHASE='bootstrap'
RUNBOOK_FAILED_COMMAND=''
RUNBOOK_CANDIDATE_COMPLETED_AT_UTC=''
RUNBOOK_TRAP_ENABLED=1
RUNBOOK_LOG_ACTIVE=0

json_escape() {
  local value=${1-}
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '%s' "$value"
}

write_outcome() {
  local exit_code=${1:-1}
  local status reason phase failed_command candidate_completed_at_utc temporary
  status="$(json_escape "$RUNBOOK_STATUS")"
  reason="$(json_escape "$RUNBOOK_REASON")"
  phase="$(json_escape "$RUNBOOK_PHASE")"
  failed_command="$(json_escape "$RUNBOOK_FAILED_COMMAND")"
  candidate_completed_at_utc=null
  if [[ "$RUNBOOK_STATUS" == PACKAGE_CANDIDATE ]]; then
    candidate_completed_at_utc="\"$(json_escape "$RUNBOOK_CANDIDATE_COMPLETED_AT_UTC")\""
  fi
  temporary="$OUTCOME_RECORD.tmp.$$"
  printf '{\n  "status": "%s",\n  "reason": "%s",\n  "phase": "%s",\n  "candidate_completed_at_utc": %s,\n  "failed_command": "%s",\n  "exit_code": %s\n}\n' \
    "$status" "$reason" "$phase" "$candidate_completed_at_utc" \
    "$failed_command" "$exit_code" > "$temporary"
  mv -f -- "$temporary" "$OUTCOME_RECORD"
}

close_runbook_log() {
  if (( RUNBOOK_LOG_ACTIVE == 1 )); then
    exec 1>&3 2>&4
    wait "$RUNBOOK_TEE_PID"
    RUNBOOK_LOG_ACTIVE=0
  fi
}

on_runbook_error() {
  local exit_code=$1 line_number=$2 failed_command=$3
  if (( RUNBOOK_TRAP_ENABLED == 0 )); then
    return 0
  fi
  if [[ "$RUNBOOK_STATUS" == PACKAGE_CANDIDATE ]]; then
    RUNBOOK_STATUS=BLOCKED
  fi
  RUNBOOK_FAILED_COMMAND="line $line_number: $failed_command"
  RUNBOOK_REASON="command failed during $RUNBOOK_PHASE"
  write_outcome "$exit_code"
}

on_runbook_exit() {
  local exit_code=$1
  trap - ERR EXIT
  if (( exit_code == 0 )) && [[ "$RUNBOOK_STATUS" != PACKAGE_CANDIDATE ]]; then
    exit_code=1
    RUNBOOK_STATUS=BLOCKED
    RUNBOOK_REASON='runbook exited before the PACKAGE_CANDIDATE state'
  elif (( exit_code != 0 )) && [[ "$RUNBOOK_STATUS" == PACKAGE_CANDIDATE ]]; then
    RUNBOOK_STATUS=BLOCKED
    RUNBOOK_REASON='candidate evidence binding failed after provisional success'
  fi
  write_outcome "$exit_code"
  close_runbook_log
  if (( exit_code != 0 )); then
    exit "$exit_code"
  fi
}

trap 'on_runbook_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
trap 'on_runbook_exit "$?"' EXIT
exec 3>&1 4>&2
exec > >(tee -a "$RUNBOOK_LOG") 2>&1
RUNBOOK_TEE_PID=$!
RUNBOOK_LOG_ACTIVE=1
: > "$HOST_PREFLIGHT"
write_outcome 1

RUNBOOK_PHASE='source-and-toolchain-preflight'
[[ -x "$CC" && -x "$CXX" ]]
for command in git python3 cmake ninja sha256sum stat cmp tee mv; do
  command -v "$command" >/dev/null
done
git lfs version >/dev/null

cd "$REPO_ROOT"
[[ "$(git rev-parse --is-inside-work-tree)" == true ]]
[[ "$(git rev-parse --is-shallow-repository)" == false ]]
[[ "$(git config --bool core.sparseCheckout || true)" != true ]]
[[ -z "$(git replace -l)" ]]
[[ ! -s "$(git rev-parse --git-path info/grafts)" ]]
[[ ! -s "$(git rev-parse --git-path objects/info/alternates)" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
git fetch --prune origin \
  '+refs/heads/main:refs/remotes/origin/main'
git show-ref --verify --quiet refs/remotes/origin/main
git merge-base --is-ancestor "$EXPECTED_SOURCE_SHA" refs/remotes/origin/main
git cat-file -e "${EXPECTED_SOURCE_SHA}^{commit}"
git checkout --detach "$EXPECTED_SOURCE_SHA"
[[ "$(git rev-parse HEAD)" == "$EXPECTED_SOURCE_SHA" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]

RUNBOOK_PHASE='host-identity-preflight'
ARCH="$(uname -m)"
CPU_VENDOR="$(awk -F: '/^vendor_id[[:space:]]*:/ { value=$2; sub(/^[[:space:]]+/, "", value); print value; exit }' /proc/cpuinfo)"
{
  echo '## initial UTC'; date -u '+%Y-%m-%dT%H:%M:%SZ'
  echo '## initial hostname'; hostname
  echo '## initial kernel'; uname -a
  printf '## observed architecture\n%s\n' "$ARCH"
  printf '## observed CPU vendor\n%s\n' "$CPU_VENDOR"
} >> "$HOST_PREFLIGHT"
[[ "$ARCH" =~ ^(x86_64|amd64)$ ]]
[[ "$CPU_VENDOR" == GenuineIntel ]]

GCC_VERSION="$("$CXX" -dumpfullversion -dumpversion)"
GCC_MAJOR="${GCC_VERSION%%.*}"
[[ "$GCC_MAJOR" =~ ^[0-9]+$ ]]
if (( GCC_MAJOR < 9 )); then
  echo "GCC 9 or newer is required; observed $GCC_VERSION" >&2
  exit 2
fi

python3 - <<'PY'
from importlib.metadata import PackageNotFoundError, version
import re
import subprocess
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required")

cmake_output = subprocess.check_output(["cmake", "--version"], text=True)
match = re.search(r"cmake version (\d+)\.(\d+)", cmake_output)
if match is None or tuple(map(int, match.groups())) < (3, 21):
    raise SystemExit("CMake 3.21 or newer is required")

try:
    jsonschema_version = tuple(
        int(part) for part in version("jsonschema").split(".")[:2]
    )
except (PackageNotFoundError, ValueError) as error:
    raise SystemExit(
        "install the declared test dependency with: "
        "python3 -m pip install -r "
        "demos/csc3_symmetric_assembly_demo/requirements-test.txt"
    ) from error
if not (jsonschema_version >= (4, 23) and jsonschema_version < (5, 0)):
    raise SystemExit("jsonschema>=4.23,<5 is required")
PY

RUNBOOK_PHASE='lfs-input-preflight'
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
  echo '## compiler'; "$CXX" --version
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
} >> "$HOST_PREFLIGHT"

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

RUNBOOK_PHASE='formal-benchmark-and-report'
RUNBOOK_TRAP_ENABLED=0
trap - ERR
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
trap 'on_runbook_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
RUNBOOK_TRAP_ENABLED=1
if (( RUN_RC != 0 || REPORT_RC != 0 )); then
  MANIFEST_STATUS=''
  if [[ -f "$EVIDENCE/run_manifest.json" ]]; then
    MANIFEST_STATUS="$(python3 - "$EVIDENCE/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("status", ""))
except (OSError, ValueError):
    print("")
PY
)"
  fi
  if [[ "$MANIFEST_STATUS" == FAIL ]]; then
    RUNBOOK_STATUS=FAIL
    RUNBOOK_REASON='formal evidence completed but at least one acceptance gate failed'
  else
    RUNBOOK_STATUS=BLOCKED
    RUNBOOK_REASON='formal benchmark or report could not complete valid evidence'
  fi
  RUNBOOK_FAILED_COMMAND="run_benchmark exit=$RUN_RC; report exit=$REPORT_RC"
  write_outcome 1
  echo 'Formal run is FAIL or BLOCKED; retain evidence/report and do not package.' >&2
  exit 1
fi

RUNBOOK_PHASE='independent-evidence-verification'
RUNBOOK_STATUS=FAIL
RUNBOOK_REASON='independent evidence assertions have not all passed'
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

RUNBOOK_PHASE='deterministic-packaging-and-clean-room-verification'
RUNBOOK_STATUS=BLOCKED
RUNBOOK_REASON='packaging or clean-room verification has not completed'
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

RUNBOOK_PHASE='candidate-hash-binding'
RUNBOOK_STATUS=BLOCKED
RUNBOOK_REASON='candidate artifact hashes have not been verified'
printf '%s\n' "$EXPECTED_SOURCE_SHA" > "$RUN_ROOT/SOURCE_COMMIT"
REPORT_REL="${REPORT#"$RUN_ROOT/"}"
close_runbook_log
(
  cd "$RUN_ROOT"
  sha256sum \
    SOURCE_COMMIT \
    host-preflight.txt \
    runbook.log \
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
RUNBOOK_PHASE='automated-candidate-complete'
RUNBOOK_STATUS=PACKAGE_CANDIDATE
RUNBOOK_CANDIDATE_COMPLETED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
RUNBOOK_REASON='all automated evidence, packaging, and clean-room gates passed; approvals remain pending'
RUNBOOK_FAILED_COMMAND=''
write_outcome 0
(
  cd "$RUN_ROOT"
  sha256sum acceptance-outcome.json >> SHA256SUMS
  sha256sum -c SHA256SUMS
)
printf 'candidate_package=%s\n' "$ZIP_A"
printf 'candidate_package_sha256=%s\n' "$ZIP_SHA256"
```

脚本会执行真正的 OpenMP 路径，并独立确认精确源码 SHA、干净状态、规范 LFS
输入、三阶段身份检查和严格十项 CTest（无 `skipped`、`disabled` 或 `notrun`）。
它随后用完全相同输入打包两次，以 `cmp` 证明字节级确定性，再分别执行
manifest-only 和完整 clean-room 验证。

## 4. 自动阶段结果处理

自动阶段成功只会输出 `candidate_package`，并在 `acceptance-outcome.json` 中记录
`PACKAGE_CANDIDATE`。此时 `SHA256SUMS` 绑定原始证据、报告、主机记录、verifier
输出和候选 ZIP，但尚未绑定人工填写的验收记录、清单与交付说明，**不得**把它
改称正式验收 `PASS`，也不得向接收部门提交。

如果流程产生有效 `FAIL` 或 `BLOCKED` 证据，应**保留**完整证据目录、报告、
日志和主机记录用于诊断；不得创建或提交验收 ZIP，不得选择性重跑、删除慢样本
或只保留有利结果。操作员应把完整命令、状态、阻塞原因和产物路径记录到
Issue #44。只有修复原因后，才能使用新的唯一 `RUN_ROOT` 与新的运行记录从头重跑。

## 5. 四方确认与最终交付封包

候选阶段为 `PACKAGE_CANDIDATE` 后，先从仓库中的空白模板生成**仓库外**工作副本：

```bash
set -euo pipefail
export EXPECTED_SOURCE_SHA='REQUIRED-40-LOWERCASE-HEX-SOURCE-SHA'
[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
for variable in \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_DIR GIT_GRAFT_FILE \
  GIT_INDEX_FILE GIT_NAMESPACE GIT_OBJECT_DIRECTORY GIT_REPLACE_REF_BASE \
  GIT_WORK_TREE; do
  [[ -z "${!variable-}" ]]
done
export GIT_NO_REPLACE_OBJECTS=1
REPO_ROOT="$(realpath -- "$(git rev-parse --show-toplevel)")"
export REPO_ROOT
export DEMO_ROOT="$REPO_ROOT/demos/csc3_symmetric_assembly_demo"
export RUN_ROOT='/absolute/repository-external/REQUIRED-RUN-ROOT'
cd "$REPO_ROOT"
[[ -z "$(git replace -l)" ]]
[[ ! -s "$(git rev-parse --git-path info/grafts)" ]]
[[ ! -s "$(git rev-parse --git-path objects/info/alternates)" ]]
git checkout --detach "$EXPECTED_SOURCE_SHA"
[[ "$(git rev-parse HEAD)" == "$EXPECTED_SOURCE_SHA" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
cp -- "$DEMO_ROOT/packaging/ACCEPTANCE_CHECKLIST.zh-CN.md" \
  "$RUN_ROOT/completed-acceptance-checklist.zh-CN.md"
cp -- "$DEMO_ROOT/packaging/DELIVERY_NOTE_TEMPLATE.zh-CN.md" \
  "$RUN_ROOT/completed-delivery-note.zh-CN.md"
```

按 [JSON Schema](ACCEPTANCE_RECORD.schema.json) 创建
`$RUN_ROOT/acceptance-record.json`。四方分别是操作员、技术复核人、交付批准人和
接收方确认人；必须在查看候选包、机器可读记录及两份完成版 Markdown 后，使用
真实身份引用、UTC 时间和组织内审批记录号完成批准。两份 Markdown 中不得保留
`REQUIRED BEFORE DELIVERY` 或未勾选的 `- [ ]`，并分别把
状态标记改为 `CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS` 与
`CSC3_DELIVERY_NOTE_STATUS=PASS`。两份文件都必须逐字包含交付 ID、完整源码 SHA、
候选 ZIP 文件名及其 SHA-256。只能填写占位值和勾选状态，不得删除、改名或重排
模板的章节、验收项及表格行；最终封包会逐项核对这些结构。

`acceptance-outcome.json` 的 `candidate_completed_at_utc` 是候选完成边界。四条
`acknowledged_at_utc` 均必须严格晚于该时间；时间戳采用 RFC3339 秒精度，因此至少
填写候选完成后的下一秒。`FAIL` 或 `BLOCKED` 结果的该字段必须为 `null`。每条
`approvals.*` 还必须逐字绑定同一候选的 `delivery_id`、
`source_commit`、`archive_filename`、`archive_sha256`、
`candidate_status=PACKAGE_CANDIDATE` 与 `clean_room_status=PASS`，不得只在自由文本
审批说明中提及这些值。

完成版 Markdown 的关键字段采用模板既有格式填写，不能把正确值附加到文件末尾来
代替指定字段：验收清单中的 Issue URL、接收组织/部门、指定接收人、四条人员确认及
`最终状态：PASS`、最终验收记录的相对路径与 SHA-256、最终 ZIP SHA-256 必须与
验收 JSON 及输入快照一致；交付说明中的 Issue URL、发送与接收组织/部门、指定接收人、
四条批准表格行（决定均为 `ACKNOWLEDGED`）及正式验收状态也必须一致。交付说明的
证据表必须逐行填写验收记录所绑定的 `run_manifest`、规范报告、`host-preflight.txt`、
候选 ZIP、`SOURCE_COMMIT`、`SHA256SUMS`、确定性打包记录、两类 verifier 输出，
以及 finalizer 输入的验收记录和完成版清单的实际相对路径与 SHA-256。finalizer 从
不可变验证快照重算这些值并逐项匹配；`COMPLETED` 等泛化文字不是有效值。

偏差与总状态必须保持单向语义：`PASS` 只能无偏差，或只包含具有非空
`approval_reference` 的 `ACCEPTED_INTERNAL_ONLY` 偏差；`REJECTED` 偏差只能对应
`FAIL`；`OPEN_BLOCKER` 偏差只能对应 `BLOCKED`。

完成复核后执行以下命令；`final-delivery` 在执行前必须不存在：

```bash
set -euo pipefail
export EXPECTED_SOURCE_SHA='REQUIRED-40-LOWERCASE-HEX-SOURCE-SHA'
[[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
for variable in \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_DIR GIT_GRAFT_FILE \
  GIT_INDEX_FILE GIT_NAMESPACE GIT_OBJECT_DIRECTORY GIT_REPLACE_REF_BASE \
  GIT_WORK_TREE; do
  [[ -z "${!variable-}" ]]
done
export GIT_NO_REPLACE_OBJECTS=1
REPO_ROOT="$(realpath -- "$(git rev-parse --show-toplevel)")"
export REPO_ROOT
export DEMO_ROOT="$REPO_ROOT/demos/csc3_symmetric_assembly_demo"
export RUN_ROOT='/absolute/repository-external/REQUIRED-RUN-ROOT'
cd "$REPO_ROOT"
[[ -z "$(git replace -l)" ]]
[[ ! -s "$(git rev-parse --git-path info/grafts)" ]]
[[ ! -s "$(git rev-parse --git-path objects/info/alternates)" ]]
[[ "$(git rev-parse HEAD)" == "$EXPECTED_SOURCE_SHA" ]]
[[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
ZIP_A="$(python3 - "$RUN_ROOT/package-a.json" <<'PY'
import json
import sys

print(json.load(open(sys.argv[1], encoding="utf-8"))["archive"])
PY
)"

python3 "$DEMO_ROOT/scripts/validate_acceptance_record.py" \
  --record "$RUN_ROOT/acceptance-record.json" \
  --run-root "$RUN_ROOT" \
  --archive "$ZIP_A" | tee "$RUN_ROOT/acceptance-record-validation.json"

python3 "$DEMO_ROOT/scripts/finalize_delivery.py" \
  --record "$RUN_ROOT/acceptance-record.json" \
  --run-root "$RUN_ROOT" \
  --archive "$ZIP_A" \
  --checklist "$RUN_ROOT/completed-acceptance-checklist.zh-CN.md" \
  --delivery-note "$RUN_ROOT/completed-delivery-note.zh-CN.md" \
  --out-dir "$RUN_ROOT/final-delivery" | tee "$RUN_ROOT/finalization-result.json"

(
  cd "$RUN_ROOT/final-delivery"
  sha256sum -c FINAL_SHA256SUMS
)
```

验收记录预检会使用 JSON Schema Draft 2020-12 `FormatChecker`，并检查文件
大小与 SHA-256、WindHub LFS 身份、误差容差关系、十项 CTest、原始样本、源码/
报告/ZIP 绑定以及四方批准。最终封包程序还会独立重跑同一验证和完整 clean-room；
只有复验仍为 `PASS` 才会创建目录。
`FINAL_SHA256SUMS` 同时覆盖候选 ZIP、机器可读验收记录、完成版清单、完成版交付
说明、`FINALIZATION.json`，以及验收记录引用的主机、runbook、候选哈希清单和
verifier 等证据副本；后者保存在 `ACCEPTANCE_EVIDENCE/`。这一步成功后，
`final-delivery/` 才是正式状态 `PASS` 的内部交付档案。

完成 Linux 运行后，机器 finish comment 必须按根 `AGENTS.md` 记录 base/end
SHA、主机和工具链、detached SHA、命令、自动阶段的 `PACKAGE_CANDIDATE` 或
`FAIL`/`BLOCKED`、最终封包的 `PASS`/未完成状态、产物路径及剩余 blocker。
