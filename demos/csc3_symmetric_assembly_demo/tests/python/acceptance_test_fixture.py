#!/usr/bin/env python3
"""Shared real-package fixture for the two-stage acceptance workflow."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
PACKAGER_SCRIPT = DEMO_ROOT / "scripts" / "create_delivery_package.py"
REPORTER_SCRIPT = DEMO_ROOT / "scripts" / "generate_test_report.py"
VERIFIER_SCRIPT = DEMO_ROOT / "scripts" / "verify_delivery_package.py"

if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from report_test_fixture import EvidenceFixture  # noqa: E402
from test_delivery_package import GitDemoFixture  # noqa: E402


CHECKSUM_ONLY_RELATIVE = "auxiliary/checksum-only.txt"
CHECKSUM_ONLY_CONTENT = b"candidate closure member without a record artifact key\n"


@dataclass
class AcceptanceCandidateFixture:
    """Paths and source identity for one real formal package candidate."""

    run_root: Path
    archive_path: Path
    source_commit: str


def _load_script(path: Path, module_name: str):
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _quiet_checked(command: list[str], cwd: Path) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def build_acceptance_candidate_fixture(root: Path) -> AcceptanceCandidateFixture:
    """生成真实 formal evidence、双 ZIP、规范 SHA256SUMS 和 verifier 输出。"""
    root = Path(root).resolve()
    run_root = root / "run-root"
    run_root.mkdir(parents=True)

    packager = _load_script(
        PACKAGER_SCRIPT,
        f"csc3_acceptance_fixture_packager_{id(root)}",
    )
    reporter = _load_script(
        REPORTER_SCRIPT,
        f"csc3_acceptance_fixture_reporter_{id(root)}",
    )
    verifier = _load_script(
        VERIFIER_SCRIPT,
        f"csc3_acceptance_fixture_verifier_{id(root)}",
    )

    git_fixture = GitDemoFixture(root / "package-fixture")
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_fixture.repository,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()

    evidence = EvidenceFixture(
        run_root / "evidence",
        evidence_level="formal",
        report_intent="delivery",
    )
    evidence.amortization = 1
    evidence.rows = evidence._make_rows()
    evidence.summary = evidence._make_summary()
    evidence.manifest = evidence._make_manifest()
    evidence.manifest["source"]["commit_sha"] = source_commit
    evidence.manifest["toolchain"]["compiler_path"] = "/usr/bin/g++"
    for identity_check in evidence.manifest["identity_checks"]:
        identity_check["source"]["commit_sha"] = source_commit
    evidence.write_all()

    bundle = reporter.validate_evidence_bundle(evidence.manifest_path)
    report_path = run_root / "linux-intel-formal-test-report.zh-CN.md"
    report_path.write_text(
        reporter.render_report(bundle),
        encoding="utf-8",
        newline="\n",
    )

    archive_a = packager.create_external_formal_package(
        git_fixture.demo,
        evidence.root,
        report_path,
        "linux-intel-formal",
        run_root / "dist-a",
    )
    archive_b = packager.create_external_formal_package(
        git_fixture.demo,
        evidence.root,
        report_path,
        "linux-intel-formal",
        run_root / "dist-b",
    )
    archive_a_content = archive_a.read_bytes()
    archive_b_content = archive_b.read_bytes()
    if archive_a_content != archive_b_content:
        raise AssertionError("formal fixture archives are not byte-identical")

    manifest_only = verifier.verify_delivery_package(
        archive_a,
        run_clean_room=False,
    )
    clean_room = verifier.verify_delivery_package(
        archive_a,
        run_clean_room=True,
        command_runner=_quiet_checked,
    )

    archive_a_relative = archive_a.relative_to(run_root).as_posix()
    archive_b_relative = archive_b.relative_to(run_root).as_posix()
    host_preflight = """## UTC
2026-07-13T10:59:00Z
## hostname
controlled-host
## kernel
Linux controlled-host 6.8.0-fixture #1 SMP x86_64 GNU/Linux
## OS
NAME=Fixture Linux
## CPU
Architecture:                         x86_64
CPU(s):                               32
On-line CPU(s) list:                  0-31
Vendor ID:                            GenuineIntel
Model name:                           Intel Xeon
Thread(s) per core:                   2
Core(s) per socket:                   16
Socket(s):                            1
NUMA node(s):                         1
NUMA node0 CPU(s):                    0-31
## NUMA
available: 1 nodes (0)
node 0 cpus: 0-31
## cpuset
cpuset_cpus: 0-31
cpuset_mems: 0
## process affinity
0-31
## memory
MemTotal:       62500000 kB
## compiler
g++ (GCC) 14.2.0
## CMake
cmake version 3.31.6
## Ninja
1.12.0
## Python
Python 3.13.5
## Git
git version 2.50.0
## Git LFS
git-lfs/3.7.0 (GitHub; linux amd64; go 1.24)
## OpenMP environment
OMP_DYNAMIC=false
OMP_PLACES=cores
OMP_PROC_BIND=close
## tool paths
compiler=/usr/bin/g++
cmake=/usr/bin/cmake
ninja=/usr/bin/ninja
python=/usr/bin/python3
git=/usr/bin/git
git_lfs=/usr/bin/git-lfs
## OpenMP version
201511
## OpenMP path
/usr/lib/x86_64-linux-gnu/libgomp.so.1
## CPU governor
performance
## Intel turbo
0
## generic boost
1
## SMT
1
## source
{source_commit}
## expected source
{source_commit}
## controlled host ID
intel-linux-01
## mainline identity
branch={source_branch}; is_mainline=false
## status
## WindHub SHA-256
{windhub_sha}  /controlled/input/3d-WindTurbineHub.inp
## WindHub bytes
76111745
""".format(
        source_commit=source_commit,
        source_branch=bundle.manifest["source"]["branch"],
        windhub_sha=bundle.manifest["input"]["sha256"],
    )

    auxiliary_contents: dict[str, bytes] = {
        "host-preflight.txt": host_preflight.encode("utf-8"),
        "runbook.log": b"formal run completed\n",
        "acceptance-outcome.json": _canonical_json(
            {
                "status": "PACKAGE_CANDIDATE",
                "reason": (
                    "all automated evidence, packaging, and clean-room gates passed; "
                    "approvals remain pending"
                ),
                "phase": "automated-candidate-complete",
                "candidate_completed_at_utc": "2026-07-13T11:00:00Z",
                "failed_command": "",
                "exit_code": 0,
            }
        ),
        "SOURCE_COMMIT": (source_commit + "\n").encode("utf-8"),
        "deterministic-package.txt": (
            "status=PASS\n"
            f"zip_a={archive_a_relative}\n"
            f"zip_b={archive_b_relative}\n"
            f"sha256={_sha256(archive_a_content)}\n"
        ).encode("utf-8"),
        "manifest-only-verification.json": _canonical_json(manifest_only),
        "clean-room-verification.log": (
            b"real clean-room verification completed\n"
            + _canonical_json(clean_room)
        ),
        CHECKSUM_ONLY_RELATIVE: CHECKSUM_ONLY_CONTENT,
    }
    for relative, content in auxiliary_contents.items():
        path = run_root.joinpath(*Path(relative).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    checksum_relatives = {
        "SOURCE_COMMIT",
        "host-preflight.txt",
        "runbook.log",
        "acceptance-outcome.json",
        "deterministic-package.txt",
        "evidence/run_manifest.json",
        "evidence/ctest.xml",
        "evidence/benchmark_samples.csv",
        "evidence/benchmark_summary.json",
        "evidence/summary.md",
        report_path.relative_to(run_root).as_posix(),
        archive_a_relative,
        "manifest-only-verification.json",
        "clean-room-verification.log",
        CHECKSUM_ONLY_RELATIVE,
    }
    checksum_content = "".join(
        f"{_sha256(run_root.joinpath(*Path(relative).parts).read_bytes())}  {relative}\n"
        for relative in sorted(checksum_relatives)
    ).encode("utf-8")
    (run_root / "SHA256SUMS").write_bytes(checksum_content)

    return AcceptanceCandidateFixture(
        run_root=run_root,
        archive_path=archive_a,
        source_commit=source_commit,
    )
