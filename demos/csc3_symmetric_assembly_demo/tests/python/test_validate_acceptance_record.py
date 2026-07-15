#!/usr/bin/env python3
"""Contract tests for the formal acceptance-record validator."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


DEMO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
VALIDATOR_SCRIPT = DEMO_ROOT / "scripts" / "validate_acceptance_record.py"
FINALIZER_SCRIPT = DEMO_ROOT / "scripts" / "finalize_delivery.py"
PUBLICATION_SCRIPT = DEMO_ROOT / "scripts" / "acceptance_publication.py"
PACKAGER_SCRIPT = DEMO_ROOT / "scripts" / "create_delivery_package.py"
REPORTER_SCRIPT = DEMO_ROOT / "scripts" / "generate_test_report.py"
VERIFIER_SCRIPT = DEMO_ROOT / "scripts" / "verify_delivery_package.py"
DELIVERY_TEST_SCRIPT = TEST_ROOT / "test_delivery_package.py"
EXPECTED_TESTS = (
    "Csc3DemoTests",
    "Csc3DemoConsumer",
    "Csc3DemoCorrectness",
    "Csc3DemoBenchmarkTiming",
    "Csc3DemoBenchmarkEngine",
    "Csc3DemoBenchmarkIo",
    "Csc3DemoInpCase",
    "Csc3DemoWindHubBenchmark",
    "Csc3DemoBenchmarkRunner",
    "Csc3DemoAtomicContention",
)
PASS_ARTIFACT_PATHS = {
    "run_manifest": "evidence/run_manifest.json",
    "ctest_junit": "evidence/ctest.xml",
    "benchmark_samples": "evidence/benchmark_samples.csv",
    "benchmark_summary": "evidence/benchmark_summary.json",
    "evidence_summary": "evidence/summary.md",
    "canonical_markdown_report": "csc3-test-report.zh-CN.md",
    "host_preflight": "host-preflight.txt",
    "runbook_log": "runbook.log",
    "outcome_record": "acceptance-outcome.json",
    "source_commit_file": "SOURCE_COMMIT",
    "sha256sums_file": "SHA256SUMS",
    "deterministic_package_record": "deterministic-package.txt",
    "manifest_only_verifier_output": "manifest-only-verification.json",
    "clean_room_verifier_log": "clean-room-verification.log",
}

if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from report_test_fixture import EvidenceFixture  # noqa: E402


def load_script(path: Path, module_name: str):
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


PUBLICATION = load_script(
    PUBLICATION_SCRIPT, "csc3_acceptance_publication_test_capability"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    return {
        "path": relative,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def party(identity: str) -> dict[str, str]:
    return {
        "organization": "Example Institute",
        "department": "Solver Development",
        "identity_reference": identity,
    }


def acknowledged(identity: str) -> dict[str, str]:
    return {
        "identity_reference": identity,
        "acknowledgement": "ACKNOWLEDGED",
        "acknowledged_at_utc": "2026-07-13T12:00:00Z",
        "approval_record_reference": f"issue-44/{identity}",
    }


def pending(identity: str) -> dict[str, str]:
    return {"identity_reference": identity, "acknowledgement": "PENDING"}


class AcceptanceRecordValidatorModuleTests(unittest.TestCase):
    def test_validator_script_exists(self) -> None:
        self.assertTrue(VALIDATOR_SCRIPT.is_file())


class FormalAcceptanceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="csc3-acceptance-base-")
        cls.base = Path(cls.temporary.name)
        cls.run_root = cls.base / "run-root"
        cls.run_root.mkdir()

        cls.delivery_fixtures = load_script(
            DELIVERY_TEST_SCRIPT,
            "csc3_acceptance_delivery_fixtures",
        )
        cls.packager = load_script(PACKAGER_SCRIPT, "csc3_acceptance_packager")
        cls.reporter = load_script(REPORTER_SCRIPT, "csc3_acceptance_reporter")
        cls.verifier = load_script(VERIFIER_SCRIPT, "csc3_acceptance_verifier")
        cls.validator = load_script(VALIDATOR_SCRIPT, "csc3_acceptance_validator")

        git_fixture = cls.delivery_fixtures.GitDemoFixture(cls.base / "package-fixture")
        cls.source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_fixture.repository,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()

        evidence = EvidenceFixture(
            cls.run_root / "evidence",
            evidence_level="formal",
            report_intent="delivery",
        )
        evidence.amortization = 1
        evidence.rows = evidence._make_rows()
        evidence.summary = evidence._make_summary()
        evidence.manifest = evidence._make_manifest()
        evidence.manifest["source"]["commit_sha"] = cls.source_commit
        for identity_check in evidence.manifest["identity_checks"]:
            identity_check["source"]["commit_sha"] = cls.source_commit
        evidence.write_all()
        cls.bundle = cls.reporter.validate_evidence_bundle(evidence.manifest_path)
        cls.report_path = cls.run_root / "csc3-test-report.zh-CN.md"
        cls.report_path.write_text(
            cls.reporter.render_report(cls.bundle),
            encoding="utf-8",
            newline="\n",
        )
        cls.archive_path = cls.packager.create_external_formal_package(
            git_fixture.demo,
            evidence.root,
            cls.report_path,
            "linux-intel-formal",
            cls.run_root / "dist-a",
        )
        archive_relative = cls.archive_path.resolve().relative_to(
            cls.run_root.resolve()
        ).as_posix()
        archive_b_relative = "dist-b/" + cls.archive_path.name
        archive_b = cls.run_root / archive_b_relative
        archive_b.parent.mkdir()
        shutil.copy2(cls.archive_path, archive_b)
        verification = cls.verifier.verify_delivery_package(
            cls.archive_path,
            run_clean_room=False,
        )

        def quiet_checked(command: list[str], cwd: Path) -> None:
            subprocess.run(
                command,
                cwd=cwd,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        clean_room_verification = cls.verifier.verify_delivery_package(
            cls.archive_path,
            run_clean_room=True,
            command_runner=quiet_checked,
        )
        environment = cls.bundle.manifest["environment"]
        toolchain = cls.bundle.manifest["toolchain"]
        auxiliary_contents = {
            "host-preflight.txt": (
                "## observed CPU vendor\nGenuineIntel\n"
                f"## compiler\ng++ (GCC) {toolchain['compiler_version']}\n"
                f"## CMake\ncmake version {toolchain['cmake_version']}\n"
                "## Ninja\n1.12.0\n"
                f"## Python\nPython {environment['python_version']}\n"
                "## Git\ngit version 2.50.0\n"
                "## Git LFS\ngit-lfs/3.7.0 (GitHub; linux amd64; go 1.24)\n"
            ),
            "runbook.log": "formal run completed\n",
            "acceptance-outcome.json": json.dumps(
                {
                    "status": "PACKAGE_CANDIDATE",
                    "reason": "all automated gates passed; approvals remain pending",
                    "phase": "automated-candidate-complete",
                    "candidate_completed_at_utc": "2026-07-13T11:00:00Z",
                    "failed_command": "",
                    "exit_code": 0,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            "SOURCE_COMMIT": cls.source_commit + "\n",
            "deterministic-package.txt": (
                "status=PASS\n"
                f"zip_a={archive_relative}\n"
                f"zip_b={archive_b_relative}\n"
                f"sha256={sha256(cls.archive_path)}\n"
            ),
            "manifest-only-verification.json": (
                json.dumps(verification, indent=2, sort_keys=True) + "\n"
            ),
            "clean-room-verification.log": (
                "real clean-room verification completed\n"
                + json.dumps(clean_room_verification, indent=2, sort_keys=True)
                + "\n"
            ),
        }
        for relative, content in auxiliary_contents.items():
            (cls.run_root / relative).write_text(content, encoding="utf-8", newline="\n")
        pass_artifact_paths = {
            **PASS_ARTIFACT_PATHS,
            "delivery_zip": archive_relative,
        }
        checksum_lines = [
            f"{sha256(cls.run_root / relative)}  {relative}\n"
            for name, relative in pass_artifact_paths.items()
            if name != "sha256sums_file"
        ]
        (cls.run_root / "SHA256SUMS").write_text(
            "".join(checksum_lines), encoding="utf-8", newline="\n"
        )
        cls.base_record = cls.make_record(archive_relative)
        cls.record_path = cls.run_root / "acceptance-record.json"
        cls.write_record(cls.record_path, cls.base_record)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def write_record(cls, path: Path, record: dict[str, object]) -> None:
        path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    @classmethod
    def make_record(cls, archive_relative: str) -> dict[str, object]:
        summary = cls.bundle.benchmark_summary
        manifest = cls.bundle.manifest
        validation_by_type = {
            case["element_type"].lower(): case for case in summary["validation_cases"]
        }

        def correctness_case(element_type: str) -> dict[str, object]:
            case = validation_by_type[element_type]
            matrix = case["matrix"]
            displacement = case["displacement"]
            return {
                "status": "PASS",
                "structure_equal": matrix["structure_matches"],
                "values_finite": True,
                "scatter_indices_valid": True,
                "frobenius_relative_error": matrix["relative_frobenius_error"],
                "maximum_absolute_error": matrix["max_absolute_error"],
                "maximum_absolute_serial_entry": matrix[
                    "reference_max_absolute_value"
                ],
                "maximum_absolute_error_tolerance": matrix[
                    "max_absolute_tolerance"
                ],
                "maximum_absolute_error_within_tolerance": True,
                "displacement_relative_error": displacement[
                    "relative_displacement_error"
                ],
                "relative_residual": displacement["parallel_relative_residual"],
                "evidence_reference": "evidence/benchmark_summary.json",
            }

        per_thread = {
            row["thread_count"]: row
            for row in cls.bundle.recomputed_statistics["per_thread"]
        }
        gate = cls.bundle.recomputed_gate
        numeric_row = per_thread[gate["numeric_thread_count"]]
        symbolic_row = per_thread[gate["symbolic_thread_count"]]
        evidence = manifest["input"]
        environment = manifest["environment"]
        toolchain = manifest["toolchain"]
        benchmark = manifest["benchmark"]
        artifact_paths = {**PASS_ARTIFACT_PATHS, "delivery_zip": archive_relative}
        verification = {
            "status": "PASS",
            "evidence_reference": "evidence/run_manifest.json",
        }
        delivery_id = "linux-formal-pass"
        delivery_binding = artifact(cls.run_root, archive_relative)
        machine_facts_sha256 = "a" * 64

        def bound_acknowledgement(identity: str) -> dict[str, str]:
            return {
                **acknowledged(identity),
                "delivery_id": delivery_id,
                "source_commit": cls.source_commit,
                "archive_filename": Path(archive_relative).name,
                "archive_sha256": str(delivery_binding["sha256"]),
                "candidate_status": "PACKAGE_CANDIDATE",
                "clean_room_status": "PASS",
                "machine_facts_sha256": machine_facts_sha256,
                "sender": {
                    "organization": "Example Institute",
                    "department": "Solver Development",
                },
                "recipient": party("recipient-id"),
                "deviations": [],
                "statement": f"{identity} approved this exact candidate",
            }

        return {
            "schema_version": "csc3-demo-formal-acceptance-v2",
            "acceptance_inputs": {
                "machine_facts": {
                    "path": "acceptance-machine-facts.json",
                    "size_bytes": 1,
                    "sha256": machine_facts_sha256,
                },
                "decision": {
                    "path": "acceptance-decision.json",
                    "size_bytes": 1,
                    "sha256": "b" * 64,
                },
            },
            "delivery_id": delivery_id,
            "issue_url": "https://github.com/example/repository/issues/44",
            "source_commit": cls.source_commit,
            "distribution": "INTERNAL EVALUATION ONLY",
            "recipient": party("recipient-id"),
            "operator": party("operator-id"),
            "technical_reviewer": party("reviewer-id"),
            "controlled_host": {
                "controlled_host_id": environment["controlled_host_id"],
                "system": environment["system"],
                "architecture": environment["architecture"],
                "hostname": environment["hostname"],
                "cpu_vendor": "GenuineIntel",
                "cpu_model": environment["cpu_model"],
                "physical_core_count": environment["physical_core_count"],
                "logical_core_count": environment["logical_core_count"],
                "total_memory_bytes": environment["total_memory_bytes"],
                "preflight_sha256": artifact(
                    cls.run_root, "host-preflight.txt"
                )["sha256"],
            },
            "toolchain": {
                "compiler": toolchain["compiler_id"],
                "compiler_version": toolchain["compiler_version"],
                "cmake_version": toolchain["cmake_version"],
                "ninja_version": "1.12.0",
                "python_version": environment["python_version"],
                "git_version": "2.50.0",
                "git_lfs_version": "3.7.0",
                "openmp_found": toolchain["openmp"]["found"],
                "openmp_required": toolchain["openmp"]["require_openmp"],
            },
            "input": {
                "case": "windhub",
                "repository_relative_path": evidence["repository_relative_path"],
                "size_bytes": evidence["size_bytes"],
                "sha256": evidence["sha256"],
                "tracked": evidence["tracked"],
                "materialized": evidence["materialized"],
                "matches_head_lfs": evidence["matches_head_lfs"],
                "head_lfs_oid_sha256": evidence["head_lfs_oid_sha256"],
                "head_lfs_size_bytes": evidence["head_lfs_size_bytes"],
            },
            "execution": {
                "status": "PASS",
                "evidence_level": "formal",
                "report_intent": "delivery",
                "preset": "delivery",
                "warmup_count": benchmark["warmup_count"],
                "repeat_count": benchmark["repeat_count"],
                "amortization_count": benchmark["amortization_count"],
                "requested_thread_counts": benchmark["requested_thread_counts"],
                "physical_core_thread_included": True,
                "omp_dynamic": "false",
                "omp_proc_bind": "close",
                "omp_places": "cores",
                "started_at_utc": manifest["started_at_utc"],
                "ended_at_utc": manifest["ended_at_utc"],
            },
            "correctness": {
                "status": "PASS",
                "thresholds": {
                    "frobenius_relative_error_maximum": 1e-8,
                    "maximum_absolute_error": {
                        "absolute_term": 1e-10,
                        "scale_term": 1e-8,
                        "scale_quantity": "max_abs_serial_matrix_entry",
                    },
                    "displacement_relative_error_maximum": 1e-8,
                    "relative_residual_maximum": 1e-10,
                },
                "tet4": correctness_case("tet4"),
                "hex8": correctness_case("hex8"),
            },
            "performance": {
                "status": "PASS",
                "thresholds": {
                    "numeric_speedup_minimum": 1.5,
                    "symbolic_speedup_exclusive_minimum": 1.0,
                    "maximum_coefficient_of_variation": 0.05,
                    "thread_count_exclusive_minimum": 1,
                },
                "numeric_thread_count": gate["numeric_thread_count"],
                "numeric_speedup": numeric_row["numeric_speedup"],
                "numeric_coefficient_of_variation": numeric_row[
                    "numeric_algorithm_ms"
                ]["coefficient_of_variation"],
                "symbolic_thread_count": gate["symbolic_thread_count"],
                "symbolic_speedup": symbolic_row["symbolic_speedup"],
                "symbolic_coefficient_of_variation": symbolic_row[
                    "symbolic_total_ms"
                ]["coefficient_of_variation"],
                "raw_sample_count": len(cls.bundle.csv_rows),
                "samples_sha256": artifact(
                    cls.run_root, "evidence/benchmark_samples.csv"
                )["sha256"],
                "summary_sha256": artifact(
                    cls.run_root, "evidence/benchmark_summary.json"
                )["sha256"],
            },
            "artifacts": {
                name: artifact(cls.run_root, relative)
                for name, relative in artifact_paths.items()
            },
            "verifications": {
                "status": "PASS",
                "source_and_input_identity": copy.deepcopy(verification),
                "ctest": {
                    "status": "PASS",
                    "test_count": 10,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "not_run_count": 0,
                    "test_names": list(EXPECTED_TESTS),
                    "evidence_reference": "evidence/ctest.xml",
                },
                "report_recomputation": copy.deepcopy(verification),
                "deterministic_package": copy.deepcopy(verification),
                "manifest_only": copy.deepcopy(verification),
                "clean_room": copy.deepcopy(verification),
            },
            "deviations": [],
            "approvals": {
                "operator": bound_acknowledgement("operator-id"),
                "technical_reviewer": bound_acknowledgement("reviewer-id"),
                "delivery_approver": bound_acknowledgement("approver-id"),
                "recipient_acknowledgement": bound_acknowledgement("recipient-id"),
            },
            "status": "PASS",
        }

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-acceptance-test-")
        self.root = Path(self.temporary.name) / "run-root"
        shutil.copytree(self.run_root, self.root, symlinks=True)
        self.record = copy.deepcopy(self.base_record)
        self.current_record_path = self.root / "acceptance-record.json"
        self.archive = self.root / self.record["artifacts"]["delivery_zip"]["path"]
        self.write_current_record()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_current_record(self) -> None:
        self.write_record(self.current_record_path, self.record)

    def validate(self, archive: Path | None = None) -> dict[str, object]:
        self.write_current_record()
        return self.validator.validate_acceptance_record(
            self.current_record_path,
            self.root,
            archive or self.archive,
        )

    def assert_invalid(self, pattern: str, archive: Path | None = None) -> str:
        with self.assertRaisesRegex(self.validator.AcceptanceRecordError, pattern) as caught:
            self.validate(archive)
        return str(caught.exception)

    def refresh_artifact(self, name: str) -> None:
        relative = self.record["artifacts"][name]["path"]
        self.record["artifacts"][name] = artifact(self.root, relative)

    def rewrite_sha256sums(self, lines: list[str]) -> None:
        (self.root / "SHA256SUMS").write_text(
            "".join(lines), encoding="utf-8", newline="\n"
        )
        self.refresh_artifact("sha256sums_file")

    def refresh_artifact_and_sha256sums(self, name: str) -> None:
        self.refresh_artifact(name)
        relative = self.record["artifacts"][name]["path"]
        replacement = f"{self.record['artifacts'][name]['sha256']}  {relative}\n"
        lines = (self.root / "SHA256SUMS").read_text(encoding="utf-8").splitlines(
            keepends=True
        )
        matches = [index for index, line in enumerate(lines) if line.endswith(f"  {relative}\n")]
        self.assertEqual(len(matches), 1, relative)
        lines[matches[0]] = replacement
        self.rewrite_sha256sums(lines)

    def make_nonpass(self, status: str) -> None:
        outcome_path = self.root / "acceptance-outcome.json"
        outcome_path.write_text(
            json.dumps(
                {
                    "status": status,
                    "reason": "formal processing did not complete",
                    "phase": "independent-evidence-verification",
                    "candidate_completed_at_utc": None,
                    "failed_command": "run_benchmark exit=1; report exit=1",
                    "exit_code": 1,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.record["status"] = status
        self.record["delivery_id"] = f"linux-formal-{status.lower()}"
        self.record["execution"]["status"] = status
        self.record["correctness"] = {"status": "NOT_RUN"}
        self.record["performance"] = {"status": "NOT_RUN"}
        self.record["artifacts"] = {
            name: self.record["artifacts"][name]
            for name in ("runbook_log", "outcome_record")
        }
        self.refresh_artifact("outcome_record")
        self.record["verifications"] = {"status": status}
        self.record["deviations"] = [
            {
                "identifier": "RUN-001",
                "description": "Formal processing did not complete.",
                "impact": "No delivery archive was accepted.",
                "disposition": "OPEN_BLOCKER" if status == "BLOCKED" else "REJECTED",
            }
        ]
        self.record["approvals"] = {
            "operator": pending("operator-id"),
            "technical_reviewer": pending("reviewer-id"),
            "delivery_approver": pending("approver-id"),
            "recipient_acknowledgement": pending("recipient-id"),
        }

    def test_valid_pass_record_succeeds(self) -> None:
        result = self.validate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_commit"], self.source_commit)
        self.assertEqual(result["ctest_count"], 10)
        self.assertEqual(result["artifact_count"], len(self.record["artifacts"]))

    def test_validated_snapshot_exposes_exact_immutable_candidate_checksum_tree(
        self,
    ) -> None:
        self.write_current_record()
        checksum_lines = (self.root / "SHA256SUMS").read_text(
            encoding="utf-8"
        ).splitlines()
        listed = {line.split("  ", 1)[1] for line in checksum_lines}
        zip_b_relative = next(
            line.removeprefix("zip_b=")
            for line in (self.root / "deterministic-package.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith("zip_b=")
        )
        expected = listed | {zip_b_relative}

        with self.validator.validated_acceptance_snapshot(
            self.current_record_path,
            self.root,
            self.archive,
        ) as snapshot:
            self.assertEqual(expected, set(snapshot.candidate_checksum_contents))
            for relative in expected:
                self.assertEqual(
                    (self.root / relative).read_bytes(),
                    snapshot.candidate_checksum_contents[relative],
                )
            (self.root / "runbook.log").write_bytes(b"changed after snapshot\n")
            self.assertNotEqual(
                (self.root / "runbook.log").read_bytes(),
                snapshot.candidate_checksum_contents["runbook.log"],
            )
            with self.assertRaises(TypeError):
                snapshot.candidate_checksum_contents["runbook.log"] = b"forged\n"

    def test_snapshot_falls_back_when_directory_descriptors_are_unavailable(
        self,
    ) -> None:
        self.write_current_record()
        real_open = os.open
        canonical_root = Path(os.path.abspath(os.fspath(self.root)))

        def windows_like_open(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            if (
                dir_fd is None
                and Path(os.path.abspath(os.fspath(path))) == canonical_root
            ):
                raise PermissionError(13, "directory handles are unavailable", path)
            if dir_fd is None:
                return real_open(path, flags, mode)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(os, "supports_dir_fd", set()), mock.patch.object(
            os, "open", side_effect=windows_like_open
        ):
            with self.validator._capture_acceptance_snapshot(
                self.current_record_path,
                self.root,
                self.archive,
            ) as snapshot:
                self.assertEqual(snapshot.capture_errors, ())
                self.assertIn(
                    "evidence/run_manifest.json", snapshot.relative_contents
                )

    def test_render_rejects_v1_pass_record_semantics(self) -> None:
        self.record["schema_version"] = "csc3-demo-formal-acceptance-v1"
        self.assert_invalid("schema_version|formal-acceptance-v2")

    @unittest.skipUnless(
        PUBLICATION.SECURE_DIRECTORY_PUBLICATION_SUPPORTED,
        "secure acceptance-directory publication is unsupported",
    )
    def test_real_validator_finalizes_complete_evidence_bound_delivery(self) -> None:
        self.write_current_record()
        archive_sha256 = sha256(self.archive)
        completion = (
            f"PASS; delivery_id={self.record['delivery_id']}; "
            f"source_commit={self.record['source_commit']}; "
            f"archive={self.archive.name}; archive_sha256={archive_sha256}"
        )
        demo_version_match = re.fullmatch(
            r"csc3-symmetric-assembly-demo-v(\d+\.\d+\.\d+)\+[0-9a-f]{12}\.zip",
            self.archive.name,
        )
        self.assertIsNotNone(demo_version_match)
        demo_version = demo_version_match.group(1)
        approvals = self.record["approvals"]
        delivery_date_utc = max(
            approval["acknowledged_at_utc"] for approval in approvals.values()
        )[:10]

        def number(value: object) -> str:
            return format(float(value), ".15g")

        correctness = self.record["correctness"]
        correctness_thresholds = correctness["thresholds"]
        maximum_absolute = correctness_thresholds["maximum_absolute_error"]
        correctness_summary = (
            f"status={correctness['status']}；Tet4={correctness['tet4']['status']}；"
            f"Hex8={correctness['hex8']['status']}；"
            f"$e_F \\le {number(correctness_thresholds['frobenius_relative_error_maximum'])}$；"
            f"$e_{{\\max}} \\le {number(maximum_absolute['absolute_term'])} + "
            f"{number(maximum_absolute['scale_term'])}\\max |K_s|$；"
            f"$e_u \\le {number(correctness_thresholds['displacement_relative_error_maximum'])}$；"
            "$r_{\\mathrm{rel}} \\le "
            f"{number(correctness_thresholds['relative_residual_maximum'])}$"
        )
        performance = self.record["performance"]
        performance_thresholds = performance["thresholds"]
        maximum_cv = number(
            performance_thresholds["maximum_coefficient_of_variation"]
        )
        performance_summary = (
            f"status={performance['status']}；"
            f"$S_{{\\mathrm{{numeric}}}}({performance['numeric_thread_count']})="
            f"{number(performance['numeric_speedup'])} \\ge "
            f"{number(performance_thresholds['numeric_speedup_minimum'])}$，"
            f"$CV={number(performance['numeric_coefficient_of_variation'])} "
            f"\\le {maximum_cv}$；"
            f"$S_{{\\mathrm{{symbolic}}}}({performance['symbolic_thread_count']})="
            f"{number(performance['symbolic_speedup'])} > "
            f"{number(performance_thresholds['symbolic_speedup_exclusive_minimum'])}$，"
            f"$CV={number(performance['symbolic_coefficient_of_variation'])} "
            f"\\le {maximum_cv}$；原始样本数 $N={performance['raw_sample_count']}$"
        )
        verification_parts = []
        for verification_name, artifact_name in (
            ("deterministic_package", "deterministic_package_record"),
            ("manifest_only", "manifest_only_verifier_output"),
            ("clean_room", "clean_room_verifier_log"),
        ):
            binding = self.record["artifacts"][artifact_name]
            verification_parts.append(
                f"{verification_name}="
                f"{self.record['verifications'][verification_name]['status']}"
                f"（{binding['path']}；SHA-256 {binding['sha256']}）"
            )
        verification_summary = "；".join(verification_parts)
        deviation_summary = "无（验收记录 deviations 为空）"

        previous_validator_module = sys.modules.get("validate_acceptance_record")
        sys.modules["validate_acceptance_record"] = self.validator
        try:
            finalizer = load_script(
                FINALIZER_SCRIPT,
                "csc3_acceptance_real_finalizer_e2e",
            )
        finally:
            if previous_validator_module is None:
                sys.modules.pop("validate_acceptance_record", None)
            else:
                sys.modules["validate_acceptance_record"] = previous_validator_module

        checksum_content = (self.root / "SHA256SUMS").read_bytes()
        zip_b_relative = next(
            line.removeprefix("zip_b=")
            for line in (self.root / "deterministic-package.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith("zip_b=")
        )
        zip_b_content = (self.root / zip_b_relative).read_bytes()
        machine_facts = {
            "candidate": {"frozen_at_utc": "2026-07-13T12:00:30Z"},
            "artifacts": {
                "sha256sums_file": {
                    "path": "SHA256SUMS",
                    "size_bytes": len(checksum_content),
                    "sha256": hashlib.sha256(checksum_content).hexdigest(),
                },
                "deterministic_zip_b": {
                    "path": zip_b_relative,
                    "size_bytes": len(zip_b_content),
                    "sha256": hashlib.sha256(zip_b_content).hexdigest(),
                },
            },
        }
        decision: dict[str, object] = {}
        machine_facts_content = finalizer.acceptance_core.canonical_json_bytes(
            machine_facts
        )
        decision_content = finalizer.acceptance_core.canonical_json_bytes(decision)
        machine_facts_path = self.root / "acceptance-machine-facts.json"
        decision_path = self.root / "acceptance-decision.json"
        machine_facts_path.write_bytes(machine_facts_content)
        decision_path.write_bytes(decision_content)
        machine_facts_sha256 = hashlib.sha256(machine_facts_content).hexdigest()
        self.record["acceptance_inputs"] = {
            "machine_facts": {
                "path": machine_facts_path.name,
                "size_bytes": len(machine_facts_content),
                "sha256": machine_facts_sha256,
            },
            "decision": {
                "path": decision_path.name,
                "size_bytes": len(decision_content),
                "sha256": hashlib.sha256(decision_content).hexdigest(),
            },
        }
        for approval in self.record["approvals"].values():
            approval["machine_facts_sha256"] = machine_facts_sha256
        self.write_current_record()

        def completed_template(filename: str, marker: str) -> Path:
            template = DEMO_ROOT / "packaging" / filename
            text = template.read_text(encoding="utf-8")
            text = text.replace(
                "{{CSC3_CHECKLIST_STATUS_MARKER}}", "PASS"
            ).replace(
                "{{CSC3_CHECKLIST_DECISION}}", "PASS"
            ).replace(
                "{{CSC3_DELIVERY_NOTE_STATUS_MARKER}}", "PASS"
            )
            text = text.replace("- [ ]", "- [x]")
            operator = self.record["operator"]
            recipient = self.record["recipient"]
            approvals = self.record["approvals"]
            if filename == "ACCEPTANCE_CHECKLIST.zh-CN.md":
                objective_artifacts = {
                    name: (binding["path"], binding["sha256"])
                    for name, binding in self.record["artifacts"].items()
                }
                objective_values = (
                    finalizer.acceptance_rendering.canonical_objective_checklist_values(
                        self.record,
                        archive_name=self.archive.name,
                        archive_sha256=archive_sha256,
                        record_relative=self.current_record_path.name,
                        record_sha256=sha256(self.current_record_path),
                        objective_artifacts=objective_artifacts,
                        validation_status="PASS",
                    )
                )
                lines = text.splitlines(keepends=True)
                for field, value in objective_values.items():
                    token = finalizer.acceptance_rendering.CHECKLIST_OBJECTIVE_TOKENS[
                        field
                    ]
                    matches: list[tuple[int, int]] = []
                    index = 0
                    while index < len(lines):
                        if not lines[index].startswith("- [x] "):
                            index += 1
                            continue
                        end = index + 1
                        while end < len(lines) and lines[end].startswith("  "):
                            end += 1
                        if token in "".join(lines[index:end]):
                            matches.append((index, end))
                        index = end
                    self.assertEqual(len(matches), 1, field)
                    start, end = matches[0]
                    block = "".join(lines[start:end])
                    self.assertEqual(block.count("REQUIRED BEFORE DELIVERY"), 1)
                    lines[start:end] = [
                        block.replace("REQUIRED BEFORE DELIVERY", value, 1).replace(
                            f" <!-- {token} -->", "", 1
                        )
                    ]
                text = "".join(lines)
            text = re.sub(r" <!-- \{\{CSC3_[A-Z0-9_]+\}\} -->", "", text)
            if filename == "ACCEPTANCE_CHECKLIST.zh-CN.md":
                text = text.replace(
                    "- [x] 交付 ID：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] 交付 ID：`{self.record['delivery_id']}`",
                ).replace(
                    "- [x] Issue #44 URL：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] Issue #44 URL：`{self.record['issue_url']}`",
                ).replace(
                    "- [x] Demo 版本：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] Demo 版本：`{demo_version}`",
                ).replace(
                    "- [x] 完整源码 SHA：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] 完整源码 SHA：`{self.record['source_commit']}`",
                ).replace(
                    "- [x] 候选源码 ZIP 文件名及 SHA-256：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] 候选源码 ZIP 文件名及 SHA-256：`{self.archive.name}` "
                    f"`{archive_sha256}`",
                ).replace(
                    "- [x] 接收组织及部门：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] 接收组织及部门：`{recipient['organization']}` / "
                    f"`{recipient['department']}`",
                ).replace(
                    "- [x] 指定接收人身份引用：`REQUIRED BEFORE DELIVERY`",
                    f"- [x] 指定接收人身份引用：`{recipient['identity_reference']}`",
                )
                for label, approval_name in (
                    ("操作员", "operator"),
                    ("技术复核人", "technical_reviewer"),
                    ("交付批准人", "delivery_approver"),
                    ("接收方确认", "recipient_acknowledgement"),
                ):
                    approval = approvals[approval_name]
                    pattern = (
                        rf"- \[x\] {re.escape(label)}：身份引用 "
                        r"`REQUIRED BEFORE DELIVERY`；UTC\s+"
                        r"`REQUIRED BEFORE DELIVERY`；\s*记录号 "
                        "`REQUIRED BEFORE DELIVERY`"
                    )
                    replacement = (
                        f"- [x] {label}：身份引用 `{approval['identity_reference']}`；UTC "
                        f"`{approval['acknowledged_at_utc']}`；记录号 "
                        f"`{approval['approval_record_reference']}`"
                    )
                    text, count = re.subn(pattern, replacement, text)
                    self.assertEqual(count, 1, label)
                text = text.replace(
                    "最终状态：`REQUIRED BEFORE DELIVERY`", "最终状态：`PASS`"
                ).replace(
                    "最终验收记录文件：`REQUIRED BEFORE DELIVERY`",
                    f"最终验收记录文件：`{self.current_record_path.name}` "
                    f"`{sha256(self.current_record_path)}`",
                ).replace(
                    "最终 ZIP SHA-256：`REQUIRED BEFORE DELIVERY`",
                    f"最终 ZIP SHA-256：`{archive_sha256}`",
                )
            else:
                text = text.replace(
                    "| 交付 ID | **REQUIRED BEFORE DELIVERY** |",
                    f"| 交付 ID | **{self.record['delivery_id']}** |",
                ).replace(
                    "| 交付日期（UTC） | **REQUIRED BEFORE DELIVERY** |",
                    f"| 交付日期（UTC） | **{delivery_date_utc}** |",
                ).replace(
                    "| Demo 版本 | **REQUIRED BEFORE DELIVERY** |",
                    f"| Demo 版本 | **{demo_version}** |",
                ).replace(
                    "| 完整源码 SHA | **REQUIRED BEFORE DELIVERY** |",
                    f"| 完整源码 SHA | **{self.record['source_commit']}** |",
                ).replace(
                    "| Issue #44 URL | **REQUIRED BEFORE DELIVERY** |",
                    f"| Issue #44 URL | **{self.record['issue_url']}** |",
                ).replace(
                    "| 发送组织/部门 | **REQUIRED BEFORE DELIVERY** |",
                    f"| 发送组织/部门 | **{operator['organization']} / "
                    f"{operator['department']}** |",
                ).replace(
                    "| 接收组织/部门 | **REQUIRED BEFORE DELIVERY** |",
                    f"| 接收组织/部门 | **{recipient['organization']} / "
                    f"{recipient['department']}** |",
                ).replace(
                    "| 指定接收人身份引用 | **REQUIRED BEFORE DELIVERY** |",
                    f"| 指定接收人身份引用 | **{recipient['identity_reference']}** |",
                ).replace(
                    "| 正式源码 ZIP | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                    f"| 正式源码 ZIP | **{self.record['artifacts']['delivery_zip']['path']}** | "
                    f"**{archive_sha256}** |",
                )
                artifact_rows = {
                    "原始证据目录/manifest": "run_manifest",
                    "规范 Markdown 报告": "canonical_markdown_report",
                    "`host-preflight.txt`": "host_preflight",
                    "`SOURCE_COMMIT`": "source_commit_file",
                    "`SHA256SUMS`": "sha256sums_file",
                    "`deterministic-package.txt`": "deterministic_package_record",
                    "manifest-only verifier 输出": "manifest_only_verifier_output",
                    "`clean-room-verification.log`": "clean_room_verifier_log",
                }
                for label, artifact_name in artifact_rows.items():
                    binding = self.record["artifacts"][artifact_name]
                    text = text.replace(
                        f"| {label} | **REQUIRED BEFORE DELIVERY** | "
                        "**REQUIRED BEFORE DELIVERY** |",
                        f"| {label} | **{binding['path']}** | "
                        f"**{binding['sha256']}** |",
                    )
                checklist_path = self.root / "completed-ACCEPTANCE_CHECKLIST.zh-CN.md"
                text = text.replace(
                    "| 机器可读验收记录 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                    f"| 机器可读验收记录 | **{self.current_record_path.name}** | "
                    f"**{sha256(self.current_record_path)}** |",
                ).replace(
                    "| 完成版验收清单 | **REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** |",
                    f"| 完成版验收清单 | **{checklist_path.name}** | "
                    f"**{sha256(checklist_path)}** |",
                ).replace(
                    "证据 SHA-256：**REQUIRED BEFORE DELIVERY**",
                    "证据 SHA-256：**"
                    + self.record["artifacts"]["run_manifest"]["sha256"]
                    + "**",
                ).replace(
                    "报告 SHA-256：**REQUIRED BEFORE DELIVERY**",
                    "报告 SHA-256：**"
                    + self.record["artifacts"]["canonical_markdown_report"]["sha256"]
                    + "**",
                ).replace(
                    "ZIP SHA-256：**REQUIRED BEFORE DELIVERY**",
                    f"ZIP SHA-256：**{archive_sha256}**",
                ).replace(
                    "机器可读验收记录路径：**REQUIRED BEFORE DELIVERY**",
                    f"机器可读验收记录路径：**{self.current_record_path.name}**",
                ).replace(
                    "复现所需完整源码 SHA：**REQUIRED BEFORE DELIVERY**",
                    f"复现所需完整源码 SHA：**{self.record['source_commit']}**",
                ).replace(
                    "受控主机 ID：**REQUIRED BEFORE DELIVERY**",
                    "受控主机 ID：**"
                    + self.record["controlled_host"]["controlled_host_id"]
                    + "**",
                ).replace(
                    "输入 SHA-256 与字节数：**REQUIRED BEFORE DELIVERY**",
                    f"输入 SHA-256 与字节数：**{self.record['input']['sha256']}** / "
                    f"**{self.record['input']['size_bytes']} bytes**",
                ).replace(
                    "完整复现命令/记录位置：**REQUIRED BEFORE DELIVERY**",
                    "完整复现命令/记录位置：**"
                    + self.record["artifacts"]["runbook_log"]["path"]
                    + "** / **"
                    + self.record["artifacts"]["runbook_log"]["sha256"]
                    + "**",
                ).replace(
                    "可选 PDF 路径及 SHA-256：**REQUIRED BEFORE DELIVERY**",
                    "可选 PDF 路径及 SHA-256：**"
                    + finalizer.acceptance_rendering.canonical_presentation_pdf_binding(
                        self.record
                    )
                    + "**",
                )
                for label, approval_name in (
                    ("操作员", "operator"),
                    ("技术复核人", "technical_reviewer"),
                    ("发送方批准/交付批准人", "delivery_approver"),
                    ("接收方确认", "recipient_acknowledgement"),
                ):
                    approval = approvals[approval_name]
                    text = text.replace(
                        f"| {label} | **REQUIRED BEFORE DELIVERY** | "
                        "**REQUIRED BEFORE DELIVERY** | **REQUIRED BEFORE DELIVERY** | "
                        "**REQUIRED BEFORE DELIVERY** |",
                        f"| {label} | **{approval['identity_reference']}** | "
                        f"**{approval['acknowledged_at_utc']}** | "
                        f"**{approval['approval_record_reference']}** | "
                        f"**{approval['acknowledgement']}** |",
                    )
                text = text.replace(
                    "正式验收状态（只能为 `PASS`）：**REQUIRED BEFORE DELIVERY**",
                    "正式验收状态（只能为 `PASS`）：**PASS**",
                ).replace(
                    "正确性门槛摘要：**REQUIRED BEFORE DELIVERY**",
                    f"正确性门槛摘要：**{correctness_summary}**",
                ).replace(
                    "性能门槛摘要：**REQUIRED BEFORE DELIVERY**",
                    f"性能门槛摘要：**{performance_summary}**",
                ).replace(
                    "确定性打包与 clean-room 结果：**REQUIRED BEFORE DELIVERY**",
                    "确定性打包与 clean-room 结果："
                    f"**{verification_summary}**",
                ).replace(
                    "偏差及批准引用（无偏差也必须填写“无”）："
                    "**REQUIRED BEFORE DELIVERY**",
                    "偏差及批准引用（无偏差也必须填写“无”）："
                    f"**{deviation_summary}**",
                )
            text = text.replace("REQUIRED BEFORE DELIVERY", completion)
            self.assertIn(marker, text)
            self.assertNotIn("REQUIRED BEFORE DELIVERY", text)
            self.assertNotIn("- [ ]", text)
            completed = self.root / f"completed-{filename}"
            completed.write_text(text, encoding="utf-8", newline="\n")
            return completed.resolve()

        checklist = completed_template(
            "ACCEPTANCE_CHECKLIST.zh-CN.md",
            "CSC3_ACCEPTANCE_CHECKLIST_STATUS=PASS",
        )
        delivery_note = completed_template(
            "DELIVERY_NOTE_TEMPLATE.zh-CN.md",
            "CSC3_DELIVERY_NOTE_STATUS=PASS",
        )

        canonical_root = self.root.resolve()
        output_directory = canonical_root / "final-delivery-e2e"
        checksum_relatives = {
            line.split("  ", 1)[1]
            for line in checksum_content.decode("utf-8").splitlines()
        }
        candidate_snapshot = mock.Mock(
            machine_facts_content=machine_facts_content,
            machine_facts=machine_facts,
            archive_content=self.archive.read_bytes(),
            relative_contents={
                relative: (self.root / relative).read_bytes()
                for relative in checksum_relatives
            },
            artifact_contents={
                "sha256sums_file": checksum_content,
                "deterministic_zip_b": zip_b_content,
            },
        )
        candidate_context = mock.MagicMock()
        candidate_context.__enter__.return_value = candidate_snapshot
        rendered = mock.Mock(
            record_content=self.current_record_path.read_bytes(),
            checklist_content=checklist.read_bytes(),
            delivery_note_content=delivery_note.read_bytes(),
        )
        with mock.patch.object(
            finalizer,
            "validated_candidate_snapshot",
            return_value=candidate_context,
        ), mock.patch.object(
            finalizer.acceptance_rendering,
            "render_acceptance_bytes",
            return_value=rendered,
        ):
            result = finalizer.finalize_delivery(
                machine_facts_path.resolve(),
                decision_path.resolve(),
                self.current_record_path.resolve(),
                canonical_root,
                self.archive.resolve(),
                checklist,
                delivery_note,
                output_directory,
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_commit"], self.source_commit)
        self.assertEqual(result["archive_sha256"], archive_sha256)
        self.assertEqual(
            (output_directory / "ACCEPTANCE_RECORD.json").read_bytes(),
            self.current_record_path.read_bytes(),
        )
        self.assertEqual(
            (output_directory / self.archive.name).read_bytes(),
            self.archive.read_bytes(),
        )

        checksum_lines = (output_directory / "FINAL_SHA256SUMS").read_text(
            encoding="utf-8"
        ).splitlines()
        checksum_paths: set[str] = set()
        for line in checksum_lines:
            self.assertRegex(line, r"^[0-9a-f]{64}  [^\n]+$")
            expected_digest, relative = line.split("  ", 1)
            self.assertNotIn(relative, checksum_paths)
            checksum_paths.add(relative)
            self.assertEqual(sha256(output_directory / relative), expected_digest)

        expected_evidence_paths: set[str] = set()
        for name, binding in self.record["artifacts"].items():
            if name == "delivery_zip":
                continue
            relative = str(binding["path"])
            suffix = Path(relative).suffix
            if re.fullmatch(r"(?:\.[A-Za-z0-9_-]+)?", suffix) is None:
                suffix = ".bin"
            bundled_relative = f"ACCEPTANCE_EVIDENCE/{name}{suffix}"
            expected_evidence_paths.add(bundled_relative)
            bundled = output_directory / bundled_relative
            self.assertTrue(bundled.is_file(), bundled_relative)
            self.assertEqual(bundled.read_bytes(), (canonical_root / relative).read_bytes())

        self.assertTrue(expected_evidence_paths)
        self.assertTrue(expected_evidence_paths.issubset(checksum_paths))
        candidate_root = output_directory / "ACCEPTANCE_EVIDENCE" / "candidate"
        expected_candidate_paths = {
            "SHA256SUMS",
            zip_b_relative,
            *checksum_relatives,
        }
        actual_candidate_paths = {
            path.relative_to(candidate_root).as_posix()
            for path in candidate_root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(expected_candidate_paths, actual_candidate_paths)
        for relative in checksum_relatives | {zip_b_relative}:
            self.assertEqual(
                (canonical_root / relative).read_bytes(),
                (candidate_root / relative).read_bytes(),
            )
        for line in (candidate_root / "SHA256SUMS").read_text(
            encoding="utf-8"
        ).splitlines():
            expected_digest, relative = line.split("  ", 1)
            self.assertEqual(sha256(candidate_root / relative), expected_digest)
        self.assertTrue(
            {
                f"ACCEPTANCE_EVIDENCE/candidate/{relative}"
                for relative in expected_candidate_paths
            }.issubset(checksum_paths)
        )
        self.assertEqual(
            {
                path.relative_to(output_directory).as_posix()
                for path in (output_directory / "ACCEPTANCE_EVIDENCE").iterdir()
            },
            expected_evidence_paths | {"ACCEPTANCE_EVIDENCE/candidate"},
        )

    def test_cli_emits_machine_readable_success(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "--record",
                str(self.current_record_path),
                "--run-root",
                str(self.root),
                "--archive",
                str(self.archive),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_record_rejects_non_finite_json_constants(self) -> None:
        text = json.dumps(self.record, sort_keys=True).replace(
            '"numeric_speedup": 2.0',
            '"numeric_speedup": NaN',
        )
        self.current_record_path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(
            self.validator.AcceptanceRecordError,
            r"non-finite JSON constant.*NaN",
        ):
            self.validator.validate_acceptance_record(
                self.current_record_path, self.root, self.archive
            )

    def test_record_rejects_duplicate_json_keys(self) -> None:
        text = '{"status":"FAIL",' + json.dumps(self.record, sort_keys=True)[1:]
        self.current_record_path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(
            self.validator.AcceptanceRecordError,
            r"duplicate JSON object key.*status",
        ):
            self.validator.validate_acceptance_record(
                self.current_record_path, self.root, self.archive
            )

    def test_schema_format_checker_rejects_invalid_timestamp(self) -> None:
        self.record["approvals"]["operator"]["acknowledged_at_utc"] = "not-a-date"
        self.assert_invalid(r"schema.*approvals\.operator\.acknowledged_at_utc.*date-time")

    def test_schema_format_checker_requires_rfc3339_utc(self) -> None:
        attacks = ("2026-W29-1T12:00:00Z", "2026-07-13T14:00:00+02:00")
        for timestamp in attacks:
            with self.subTest(timestamp=timestamp):
                self.record = copy.deepcopy(self.base_record)
                self.record["approvals"]["operator"]["acknowledged_at_utc"] = timestamp
                self.assert_invalid(r"schema.*acknowledged_at_utc.*date-time")

    def test_pass_requires_exact_genuineintel_vendor(self) -> None:
        self.record["controlled_host"]["cpu_vendor"] = "Intel Corporation"
        self.assert_invalid(r"controlled_host\.cpu_vendor.*exactly 'GenuineIntel'")

    def test_toolchain_fields_are_bound_to_run_manifest(self) -> None:
        self.record["toolchain"]["compiler_version"] = "99.0.0"
        self.assert_invalid(r"toolchain\.compiler_version.*run_manifest")

    def test_recorded_tool_versions_are_bound_to_host_preflight(self) -> None:
        for field in ("ninja_version", "git_version", "git_lfs_version"):
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                self.record["toolchain"][field] = "FAKE"
                self.assert_invalid(rf"toolchain\.{field}.*host-preflight")

    def test_gcc_label_is_accepted_for_gnu_compiler_id(self) -> None:
        self.record["toolchain"]["compiler"] = "GCC"
        try:
            result = self.validate()
        except self.validator.AcceptanceRecordError as error:
            self.fail(f"GCC is the expected human label for GNU: {error}")
        self.assertEqual(result["status"], "PASS")

    def test_pass_rejects_lfs_digest_mismatch(self) -> None:
        self.record["input"]["head_lfs_oid_sha256"] = "f" * 64
        self.assert_invalid(r"input SHA-256.*HEAD LFS")

    def test_pass_rejects_lfs_size_mismatch(self) -> None:
        self.record["input"]["head_lfs_size_bytes"] += 1
        self.assert_invalid(r"input size.*HEAD LFS")

    def test_pass_rejects_incorrect_scale_aware_tolerance(self) -> None:
        self.record["correctness"]["tet4"]["maximum_absolute_error_tolerance"] = 1.0
        self.assert_invalid(r"correctness\.tet4.*tolerance.*1e-10 \+ 1e-8")

    def test_pass_rejects_error_above_recomputed_tolerance(self) -> None:
        case = self.record["correctness"]["tet4"]
        case["maximum_absolute_error"] = case["maximum_absolute_error_tolerance"] * 2
        case["maximum_absolute_error_within_tolerance"] = True
        self.assert_invalid(r"correctness\.tet4.*maximum_absolute_error.*exceeds")

    def test_artifact_paths_are_confined_to_run_root(self) -> None:
        self.record["artifacts"]["runbook_log"]["path"] = "../outside.log"
        self.assert_invalid(r"artifacts\.runbook_log\.path.*unsafe|schema.*runbook_log")

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_artifact_validation_does_not_follow_symbolic_links(self) -> None:
        outside = Path(self.temporary.name) / "outside.log"
        outside.write_text("formal run completed\n", encoding="utf-8")
        claimed = self.root / "runbook.log"
        claimed.unlink()
        claimed.symlink_to(outside)
        self.assert_invalid(r"artifacts\.runbook_log.*symbolic link")

    def test_artifact_size_and_hash_are_recomputed(self) -> None:
        (self.root / "runbook.log").write_text("tampered\n", encoding="utf-8")
        message = self.assert_invalid(r"artifacts\.runbook_log.*(?:size|SHA-256)")
        self.assertIn("artifacts.runbook_log", message)

    def test_concurrent_artifact_exchange_cannot_mix_hash_and_json(self) -> None:
        target = self.root / "acceptance-outcome.json"
        valid_content = target.read_bytes()
        invalid_document = json.loads(valid_content.decode("utf-8"))
        invalid_document["status"] = "PASS"
        invalid_content = (
            json.dumps(invalid_document, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        target.write_bytes(invalid_content)
        self.refresh_artifact_and_sha256sums("outcome_record")

        real_sha256 = self.validator._sha256

        def exchange_after_hash(path: Path) -> str:
            candidate = Path(path)
            if candidate.resolve() != target.resolve():
                return real_sha256(candidate)
            target.write_bytes(invalid_content)
            digest = real_sha256(target)
            replacement = target.with_name(target.name + ".replacement")
            replacement.write_bytes(valid_content)
            os.replace(replacement, target)
            return digest

        with mock.patch.object(
            self.validator, "_sha256", side_effect=exchange_after_hash
        ):
            with self.assertRaisesRegex(
                self.validator.AcceptanceRecordError,
                r"outcome_record\.status.*acceptance record|SHA-256 mismatch",
            ):
                self.validate()

    def test_duplicate_artifact_bindings_are_rejected(self) -> None:
        self.record["artifacts"]["outcome_record"] = copy.deepcopy(
            self.record["artifacts"]["runbook_log"]
        )
        self.assert_invalid(r"duplicate artifact path.*runbook\.log")

    def test_archive_argument_must_equal_delivery_zip_artifact(self) -> None:
        other = self.root / "other.zip"
        shutil.copy2(self.archive, other)
        self.assert_invalid(r"--archive.*artifacts\.delivery_zip", other)

    def test_archive_manifest_is_verified(self) -> None:
        content = bytearray(self.archive.read_bytes())
        content[len(content) // 2] ^= 0x01
        self.archive.write_bytes(content)
        self.refresh_artifact("delivery_zip")
        self.assert_invalid(
            r"delivery archive.*(?:CRC|SHA-256|invalid|Bad ZIP|member)",
            self.archive,
        )

    def test_archive_source_and_evidence_identity_match_record(self) -> None:
        self.record["source_commit"] = "c" * 40
        self.assert_invalid(r"delivery archive.*source commit|run_manifest.*source commit")

    def test_archive_build_info_rejects_numeric_overflow(self) -> None:
        with zipfile.ZipFile(self.archive) as source:
            infos = source.infolist()
            contents = {info.filename: source.read(info) for info in infos}
        build_info_name = next(
            name for name in contents if name.endswith("/BUILD_INFO.json")
        )
        manifest_name = next(
            name for name in contents if name.endswith("/MANIFEST.sha256")
        )
        contents[build_info_name] = contents[build_info_name].replace(
            b"{\n", b'{\n  "numeric_overflow": 1e999,\n', 1
        )
        build_info_relative = build_info_name.split("/", 1)[1]
        manifest_lines = contents[manifest_name].decode("utf-8").splitlines()
        contents[manifest_name] = (
            "\n".join(
                (
                    f"{hashlib.sha256(contents[build_info_name]).hexdigest()}  "
                    f"{build_info_relative}"
                    if line.endswith(f"  {build_info_relative}")
                    else line
                )
                for line in manifest_lines
            )
            + "\n"
        ).encode("utf-8")
        replacement = self.root / "overflow.zip"
        with zipfile.ZipFile(replacement, "w") as destination:
            for info in infos:
                destination.writestr(info, contents[info.filename])
        replacement.replace(self.archive)
        shutil.copy2(
            self.archive,
            self.root / "dist-b" / self.archive.name,
        )

        archive_digest = sha256(self.archive)
        deterministic = self.root / "deterministic-package.txt"
        deterministic.write_text(
            re.sub(
                r"(?m)^sha256=[0-9a-f]{64}$",
                f"sha256={archive_digest}",
                deterministic.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )
        manifest_result = json.loads(
            (self.root / "manifest-only-verification.json").read_text(
                encoding="utf-8"
            )
        )
        manifest_result["archive_sha256"] = archive_digest
        (self.root / "manifest-only-verification.json").write_text(
            json.dumps(manifest_result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        clean_result = dict(manifest_result)
        clean_result["clean_room_executed"] = True
        (self.root / "clean-room-verification.log").write_text(
            "recorded clean-room transcript\n"
            + json.dumps(clean_result, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        for name in self.record["artifacts"]:
            if name != "sha256sums_file":
                self.refresh_artifact(name)
        checksum_lines = [
            f"{binding['sha256']}  {binding['path']}\n"
            for name, binding in self.record["artifacts"].items()
            if name != "sha256sums_file"
        ]
        self.rewrite_sha256sums(checksum_lines)
        self.assert_invalid(r"BUILD_INFO.*non-finite JSON number")

    def test_candidate_outcome_is_bound_to_automated_success_state(self) -> None:
        attacks = (
            ("status", "PASS", r"outcome_record\.status.*PACKAGE_CANDIDATE"),
            ("phase", "packaging", r"outcome_record\.phase.*automated-candidate-complete"),
            ("exit_code", 1, r"outcome_record\.exit_code.*zero"),
        )
        for field, value, pattern in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                outcome_path = self.root / "acceptance-outcome.json"
                outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
                outcome[field] = value
                outcome_path.write_text(
                    json.dumps(outcome, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_artifact_and_sha256sums("outcome_record")
                self.assert_invalid(pattern)

    def test_candidate_completion_and_approval_order_are_enforced(self) -> None:
        attacks = (
            (None, r"candidate_completed_at_utc.*valid UTC"),
            ("not-a-date", r"candidate_completed_at_utc.*valid UTC"),
            ("2000-01-01T00:00:00Z", r"candidate_completed_at_utc.*execution"),
            ("2026-07-13T12:01:00Z", r"acknowledged_at_utc.*candidate"),
        )
        for timestamp, pattern in attacks:
            with self.subTest(timestamp=timestamp):
                self.record = copy.deepcopy(self.base_record)
                outcome_path = self.root / "acceptance-outcome.json"
                outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
                outcome["candidate_completed_at_utc"] = timestamp
                outcome_path.write_text(
                    json.dumps(outcome, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_artifact_and_sha256sums("outcome_record")
                self.assert_invalid(pattern)

    def test_approval_at_candidate_completion_time_is_rejected(self) -> None:
        candidate_completed = json.loads(
            (self.root / "acceptance-outcome.json").read_text(encoding="utf-8")
        )["candidate_completed_at_utc"]
        self.record["approvals"]["operator"][
            "acknowledged_at_utc"
        ] = candidate_completed
        self.assert_invalid(r"acknowledged_at_utc.*strictly later.*candidate")

    def test_pass_deviations_require_internal_acceptance_and_reference(self) -> None:
        accepted = {
            "identifier": "DEV-001",
            "description": "An internally accepted limitation.",
            "impact": "Restricted to internal evaluation.",
            "disposition": "ACCEPTED_INTERNAL_ONLY",
            "approval_reference": "issue-44/deviation-approval-001",
        }
        self.record["deviations"] = [copy.deepcopy(accepted)]
        for approval in self.record["approvals"].values():
            approval["deviations"] = [copy.deepcopy(accepted)]
        self.assertEqual(self.validate()["status"], "PASS")

        attacks = (
            (
                "missing approval",
                {
                    key: value
                    for key, value in accepted.items()
                    if key != "approval_reference"
                },
            ),
            ("blank approval", {**accepted, "approval_reference": " "}),
            ("rejected", {**accepted, "disposition": "REJECTED"}),
            ("open blocker", {**accepted, "disposition": "OPEN_BLOCKER"}),
        )
        for name, deviation in attacks:
            with self.subTest(name=name):
                self.record = copy.deepcopy(self.base_record)
                self.record["deviations"] = [deviation]
                self.assert_invalid(r"deviations|disposition|approval_reference|schema")

    def test_approval_structured_bindings_match_the_candidate(self) -> None:
        attacks = (
            ("delivery_id", "another-delivery"),
            ("source_commit", "c" * 40),
            ("archive_filename", "csc3-symmetric-assembly-demo-v0.2.0+cccccccccccc.zip"),
            ("archive_sha256", "c" * 64),
            ("candidate_status", "PASS"),
            ("clean_room_status", "FAIL"),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                self.record["approvals"]["operator"][field] = value
                self.assert_invalid(rf"approvals\.operator\.{field}.*candidate|schema")

        cross_bindings = (
            ("machine_facts_sha256", "c" * 64),
            (
                "sender",
                {"organization": "Other Institute", "department": "Delivery"},
            ),
            ("recipient", party("different-recipient")),
            (
                "deviations",
                [
                    {
                        "identifier": "DEV-X",
                        "description": "Unbound deviation.",
                        "impact": "Unknown.",
                        "disposition": "ACCEPTED_INTERNAL_ONLY",
                        "approval_reference": "issue-44/DEV-X",
                    }
                ],
            ),
        )
        for field, value in cross_bindings:
            with self.subTest(cross_binding=field):
                self.record = copy.deepcopy(self.base_record)
                self.record["approvals"]["operator"][field] = value
                self.assert_invalid(
                    rf"approvals\.operator\.{field}.*"
                    r"(?:candidate|machine|sender|recipient|deviations)"
                )

    def test_artifact_json_rejects_duplicate_object_keys(self) -> None:
        attacks = (
            (
                "outcome_record",
                "acceptance-outcome.json",
                r"duplicate JSON object key.*status",
            ),
            (
                "manifest_only_verifier_output",
                "manifest-only-verification.json",
                r"duplicate JSON object key.*status",
            ),
        )
        for artifact_name, relative, pattern in attacks:
            with self.subTest(artifact=artifact_name):
                self.record = copy.deepcopy(self.base_record)
                path = self.root / relative
                text = path.read_text(encoding="utf-8")
                path.write_text('{"status":"FAIL",' + text.lstrip()[1:], encoding="utf-8")
                self.refresh_artifact_and_sha256sums(artifact_name)
                self.assert_invalid(pattern)

    def test_sha256sums_requires_canonical_unique_confined_entries(self) -> None:
        original = (self.root / "SHA256SUMS").read_text(encoding="utf-8").splitlines(
            keepends=True
        )
        attacks = (
            (
                "duplicate",
                original + [original[0]],
                r"SHA256SUMS.*duplicate.*" + re.escape(original[0].split("  ", 1)[1].strip()),
            ),
            (
                "escape",
                original + [f"{'a' * 64}  ../outside\n"],
                r"SHA256SUMS.*unsafe.*\.\./outside",
            ),
            (
                "noncanonical",
                [original[0].replace("  ", " ", 1), *original[1:]],
                r"SHA256SUMS.*canonical",
            ),
        )
        for _name, lines, pattern in attacks:
            with self.subTest(name=_name):
                self.record = copy.deepcopy(self.base_record)
                self.rewrite_sha256sums(list(lines))
                self.assert_invalid(pattern)

    def test_sha256sums_recomputes_entries_and_covers_every_candidate_artifact(self) -> None:
        original = (self.root / "SHA256SUMS").read_text(encoding="utf-8").splitlines(
            keepends=True
        )
        runbook_path = self.record["artifacts"]["runbook_log"]["path"]
        missing = [line for line in original if not line.endswith(f"  {runbook_path}\n")]
        self.rewrite_sha256sums(missing)
        self.assert_invalid(r"SHA256SUMS.*missing.*artifacts\.runbook_log")

        self.record = copy.deepcopy(self.base_record)
        corrupted = list(original)
        index = next(
            position
            for position, line in enumerate(corrupted)
            if line.endswith(f"  {runbook_path}\n")
        )
        corrupted[index] = f"{'f' * 64}  {runbook_path}\n"
        self.rewrite_sha256sums(corrupted)
        self.assert_invalid(r"SHA256SUMS.*runbook\.log.*SHA-256 mismatch")

    def test_manifest_only_verifier_output_is_cross_checked(self) -> None:
        attacks = (
            ("status", "FAIL", r"manifest-only.*status.*PASS"),
            ("clean_room_executed", True, r"manifest-only.*clean_room_executed.*false"),
            ("archive_sha256", "f" * 64, r"manifest-only.*archive_sha256.*delivery ZIP"),
            ("source_commit", "f" * 40, r"manifest-only.*source_commit.*record"),
        )
        for field, value, pattern in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                path = self.root / "manifest-only-verification.json"
                document = json.loads(path.read_text(encoding="utf-8"))
                document[field] = value
                path.write_text(
                    json.dumps(document, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_artifact_and_sha256sums(
                    "manifest_only_verifier_output"
                )
                self.assert_invalid(pattern)

    def test_clean_room_verifier_tail_json_is_cross_checked(self) -> None:
        attacks = (
            ("status", "FAIL", r"clean-room.*status.*PASS"),
            ("clean_room_executed", False, r"clean-room.*clean_room_executed.*true"),
            ("archive_sha256", "f" * 64, r"clean-room.*archive_sha256.*delivery ZIP"),
            ("source_commit", "f" * 40, r"clean-room.*source_commit.*record"),
        )
        base_document = json.loads(
            (self.root / "manifest-only-verification.json").read_text(encoding="utf-8")
        )
        base_document["clean_room_executed"] = True
        for field, value, pattern in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                document = dict(base_document)
                document[field] = value
                (self.root / "clean-room-verification.log").write_text(
                    "clean-room command transcript\n"
                    + json.dumps(document, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )
                self.refresh_artifact_and_sha256sums("clean_room_verifier_log")
                self.assert_invalid(pattern)

    def test_clean_room_tail_rejects_duplicate_json_keys(self) -> None:
        document = json.loads(
            (self.root / "manifest-only-verification.json").read_text(encoding="utf-8")
        )
        document["clean_room_executed"] = True
        duplicated = '{"status":"FAIL",' + json.dumps(document, sort_keys=True)[1:]
        (self.root / "clean-room-verification.log").write_text(
            "clean-room transcript\n" + duplicated + "\n",
            encoding="utf-8",
        )
        self.refresh_artifact_and_sha256sums("clean_room_verifier_log")
        self.assert_invalid(r"clean-room.*(?:duplicate JSON object key|valid JSON object)")

    def test_pass_reexecutes_real_clean_room_verification(self) -> None:
        verifier = self.validator._load_sibling(
            "verify_delivery_package.py", "csc3_acceptance_package_verifier"
        )
        real_verify = verifier.verify_delivery_package
        observed: list[bool] = []

        def traced_verify(archive: Path, **options: object) -> dict[str, object]:
            observed.append(bool(options.get("run_clean_room")))
            return real_verify(archive, **options)

        with mock.patch.object(verifier, "verify_delivery_package", traced_verify):
            self.validate()
        self.assertIn(True, observed)

    def test_fabricated_clean_room_log_cannot_replace_reexecution(self) -> None:
        verifier = self.validator._load_sibling(
            "verify_delivery_package.py", "csc3_acceptance_package_verifier"
        )
        real_verify = verifier.verify_delivery_package

        def reject_clean_room(archive: Path, **options: object) -> dict[str, object]:
            if options.get("run_clean_room") is True:
                raise RuntimeError("simulated independent clean-room failure")
            return real_verify(archive, **options)

        with mock.patch.object(verifier, "verify_delivery_package", reject_clean_room):
            self.assert_invalid(r"independent clean-room verification failed")

    def test_deterministic_package_record_binds_both_zip_paths_and_digest(self) -> None:
        attacks = (
            ("status", "FAIL", r"deterministic-package.*status.*PASS"),
            ("zip_a", "dist-b/missing.zip", r"deterministic-package.*zip_a.*delivery ZIP"),
            ("zip_b", "dist-b/missing.zip", r"deterministic-package.*zip_b.*does not exist"),
            ("sha256", "f" * 64, r"deterministic-package.*sha256.*delivery ZIP"),
        )
        for field, value, pattern in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                path = self.root / "deterministic-package.txt"
                lines = path.read_text(encoding="utf-8").splitlines()
                updated = [
                    f"{field}={value}" if line.startswith(f"{field}=") else line
                    for line in lines
                ]
                path.write_text("\n".join(updated) + "\n", encoding="utf-8")
                self.refresh_artifact_and_sha256sums("deterministic_package_record")
                self.assert_invalid(pattern)

    def test_run_manifest_source_commit_matches_record(self) -> None:
        manifest_path = self.root / "evidence/run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source"]["commit_sha"] = "c" * 40
        for identity_check in manifest["identity_checks"]:
            identity_check["source"]["commit_sha"] = "c" * 40
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.refresh_artifact("run_manifest")
        self.assert_invalid(r"run_manifest.*source commit")

    def test_canonical_report_is_recomputed_from_evidence(self) -> None:
        self.report_path = self.root / "csc3-test-report.zh-CN.md"
        self.report_path.write_text("# fabricated report\n", encoding="utf-8")
        self.refresh_artifact("canonical_markdown_report")
        self.assert_invalid(r"canonical Markdown report.*recomputed.*evidence")

    def test_performance_sample_and_summary_hashes_match_artifacts(self) -> None:
        for field in ("samples_sha256", "summary_sha256"):
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                self.record["performance"][field] = "f" * 64
                self.assert_invalid(rf"performance\.{field}.*artifact")

    def test_performance_raw_sample_count_matches_csv_rows(self) -> None:
        self.record["performance"]["raw_sample_count"] += 1
        self.assert_invalid(r"performance\.raw_sample_count.*CSV row count")

    def test_correctness_values_match_benchmark_summary(self) -> None:
        self.record["correctness"]["hex8"]["frobenius_relative_error"] = 1e-9
        self.assert_invalid(r"correctness\.hex8\.frobenius_relative_error.*summary")

    def test_performance_values_match_recomputed_samples(self) -> None:
        self.record["performance"]["numeric_speedup"] = 9.0
        self.assert_invalid(r"performance\.numeric_speedup.*recomputed samples")

    def test_ctest_record_requires_exact_ten_names_and_counts(self) -> None:
        attacks = (
            ("test_count", 9),
            ("failed_count", 1),
            ("skipped_count", 1),
            ("not_run_count", 1),
            ("test_names", list(reversed(EXPECTED_TESTS))),
        )
        for field, value in attacks:
            with self.subTest(field=field):
                self.record = copy.deepcopy(self.base_record)
                self.record["verifications"]["ctest"][field] = value
                self.assert_invalid(r"verifications\.ctest|schema")

    def test_pass_requires_all_four_acknowledged_approvals(self) -> None:
        approval = self.record["approvals"]["recipient_acknowledgement"]
        approval.clear()
        approval.update(pending("recipient-id"))
        self.assert_invalid(r"approvals\.recipient_acknowledgement|schema")

    def test_pass_rejects_whitespace_only_party_and_approval_identity(self) -> None:
        self.record["operator"]["organization"] = " "
        self.record["approvals"]["delivery_approver"][
            "approval_record_reference"
        ] = " "
        self.assert_invalid(r"operator\.organization.*nonblank|delivery_approver.*nonblank")

    def test_pass_rejects_approval_before_execution_completed(self) -> None:
        for approval in self.record["approvals"].values():
            approval["acknowledged_at_utc"] = "2000-01-01T00:00:00Z"
        self.assert_invalid(r"acknowledged_at_utc.*before execution\.ended_at_utc")

    def test_pass_rejects_future_or_unbound_approval(self) -> None:
        self.record["approvals"]["delivery_approver"][
            "acknowledged_at_utc"
        ] = "2999-01-01T00:00:00Z"
        self.record["approvals"]["operator"][
            "approval_record_reference"
        ] = "issue-44/unrelated"
        message = self.assert_invalid(r"acknowledged_at_utc.*future|does not bind")
        self.assertIn("does not bind", message)

    def test_named_approvals_are_bound_to_party_identity_references(self) -> None:
        self.record["approvals"]["operator"]["identity_reference"] = "someone-else"
        self.assert_invalid(r"approvals\.operator\.identity_reference.*operator")

    def test_artifact_and_cross_field_errors_are_aggregated(self) -> None:
        self.record["controlled_host"]["cpu_vendor"] = "Intel Corporation"
        self.record["input"]["head_lfs_oid_sha256"] = "f" * 64
        (self.root / "runbook.log").write_text("tampered\n", encoding="utf-8")
        message = self.assert_invalid(r"acceptance record validation failed")
        self.assertIn("controlled_host.cpu_vendor", message)
        self.assertIn("HEAD LFS", message)
        self.assertIn("artifacts.runbook_log", message)

    def test_fail_record_only_checks_artifacts_it_claims(self) -> None:
        self.make_nonpass("FAIL")
        result = self.validate(self.root / "archive-was-not-created.zip")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["artifact_count"], 2)

    def test_blocked_record_only_checks_artifacts_it_claims(self) -> None:
        self.make_nonpass("BLOCKED")
        result = self.validate(self.root / "archive-was-not-created.zip")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["artifact_count"], 2)

    def test_rejected_and_open_blocker_deviations_map_to_overall_status(self) -> None:
        self.make_nonpass("FAIL")
        self.record["deviations"][0]["disposition"] = "OPEN_BLOCKER"
        self.assert_invalid(r"OPEN_BLOCKER.*BLOCKED|deviations|schema")

        self.record = copy.deepcopy(self.base_record)
        self.make_nonpass("BLOCKED")
        self.record["deviations"][0]["disposition"] = "REJECTED"
        self.assert_invalid(r"REJECTED.*FAIL|deviations|schema")

    def test_nonpass_record_requires_matching_valid_outcome(self) -> None:
        for record_status, outcome_status in (
            ("FAIL", "PACKAGE_CANDIDATE"),
            ("BLOCKED", "FAIL"),
        ):
            with self.subTest(record_status=record_status):
                self.record = copy.deepcopy(self.base_record)
                self.make_nonpass(record_status)
                outcome_path = self.root / "acceptance-outcome.json"
                outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
                outcome["status"] = outcome_status
                outcome_path.write_text(
                    json.dumps(outcome, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.refresh_artifact("outcome_record")
                self.assert_invalid(r"outcome_record\.status.*acceptance record")

    def test_nonpass_record_rejects_non_json_outcome(self) -> None:
        self.make_nonpass("FAIL")
        (self.root / "acceptance-outcome.json").write_text("not json\n", encoding="utf-8")
        self.refresh_artifact("outcome_record")
        self.assert_invalid(r"outcome_record is not strict UTF-8 JSON")

    def test_nonpass_record_cannot_claim_candidate_completion(self) -> None:
        self.make_nonpass("BLOCKED")
        outcome_path = self.root / "acceptance-outcome.json"
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        outcome["candidate_completed_at_utc"] = "2026-07-13T11:00:00Z"
        outcome_path.write_text(
            json.dumps(outcome, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.refresh_artifact("outcome_record")
        self.assert_invalid(r"non-PASS.*candidate_completed_at_utc.*null")

    def test_nonpass_record_rejects_a_missing_claimed_artifact(self) -> None:
        self.make_nonpass("BLOCKED")
        (self.root / "runbook.log").unlink()
        self.assert_invalid(
            r"artifacts\.runbook_log.*does not exist",
            self.root / "archive-was-not-created.zip",
        )

    def test_cli_aggregates_errors_and_returns_nonzero(self) -> None:
        self.record["controlled_host"]["cpu_vendor"] = "Intel Corporation"
        self.record["input"]["head_lfs_oid_sha256"] = "f" * 64
        self.write_current_record()
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "--record",
                str(self.current_record_path),
                "--run-root",
                str(self.root),
                "--archive",
                str(self.archive),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("controlled_host.cpu_vendor", result.stderr)
        self.assertIn("HEAD LFS", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
