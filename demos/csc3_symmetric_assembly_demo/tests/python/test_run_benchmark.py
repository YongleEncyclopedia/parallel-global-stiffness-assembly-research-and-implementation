#!/usr/bin/env python3
"""Contract tests for the reproducible CSC3 demo benchmark runner."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_benchmark.py"
SPEC = importlib.util.spec_from_file_location("csc3_run_benchmark", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load runner: {SCRIPT}")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def timing_statistics(value: float = 1.0, sample_count: int = 1) -> dict[str, object]:
    return {
        "sample_count": sample_count,
        "mean_ms": value,
        "median_ms": value,
        "population_standard_deviation_ms": 0.0,
        "minimum_ms": value,
        "maximum_ms": value,
        "coefficient_of_variation": 0.0,
    }


def thread_statistics(
    thread: int,
    sample_count: int,
    symbolic_speedup: float = 1.0,
    numeric_speedup: float = 1.0,
) -> dict[str, object]:
    row = {
        "thread_count": thread,
        "symbolic_thread_count_observed": thread,
        "numeric_thread_count_observed": thread,
        "symbolic_speedup": symbolic_speedup,
        "numeric_speedup": numeric_speedup,
    }
    for key in (
        "symbolic_pattern_ms", "symbolic_scatter_ms", "symbolic_total_ms",
        "numeric_reset_ms", "numeric_kernel_ms", "numeric_algorithm_ms",
        "numeric_total_ms", "amortized_total_ms",
    ):
        row[key] = timing_statistics(sample_count=sample_count)
    row["symbolic_total_ms"] = timing_statistics(
        value=1.0 / symbolic_speedup, sample_count=sample_count
    )
    row["numeric_algorithm_ms"] = timing_statistics(
        value=1.0 / numeric_speedup, sample_count=sample_count
    )
    return row


class TemporaryDirectory(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="csc3-runner-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()


class InputAndOutputContractTests(TemporaryDirectory):
    def test_lfs_pointer_is_rejected_without_creating_output(self) -> None:
        pointer = self.root / "hub.inp"
        pointer.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:" + "a" * 64 + "\n"
            "size 76111745\n",
            encoding="utf-8",
        )
        output = self.root / "evidence"
        with self.assertRaisesRegex(RuntimeError, "Git LFS pointer"):
            RUNNER.run_workflow(
                [
                    "--case", "windhub", "--input", str(pointer),
                    "--out-root", str(output), "--dry-run",
                ]
            )
        self.assertFalse(output.exists())

    def test_missing_windhub_input_is_rejected_before_output(self) -> None:
        output = self.root / "evidence"
        with self.assertRaisesRegex(FileNotFoundError, "input"):
            RUNNER.run_workflow(
                [
                    "--case", "windhub", "--input", str(self.root / "missing.inp"),
                    "--out-root", str(output), "--dry-run",
                ]
            )
        self.assertFalse(output.exists())

    def test_overwrite_removes_only_owned_files(self) -> None:
        output = self.root / "evidence"
        output.mkdir()
        keep = output / "keep.txt"
        keep.write_text("keep", encoding="utf-8")
        for name in RUNNER.OWNED_OUTPUT_NAMES:
            (output / name).write_text("old", encoding="utf-8")
        RUNNER.prepare_output_root(output, overwrite=True, source_root=self.root / "source")
        self.assertTrue(keep.is_file())
        self.assertEqual(keep.read_text(encoding="utf-8"), "keep")
        self.assertTrue(output.is_dir())
        for name in RUNNER.OWNED_OUTPUT_NAMES:
            self.assertFalse((output / name).exists())

    def test_existing_output_requires_overwrite(self) -> None:
        output = self.root / "evidence"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            RUNNER.prepare_output_root(output, overwrite=False, source_root=self.root / "source")

    def test_protected_output_roots_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "protected"):
            RUNNER.prepare_output_root(Path.cwd(), overwrite=True, source_root=self.root)
        with self.assertRaisesRegex(ValueError, "protected"):
            RUNNER.prepare_output_root(Path.home(), overwrite=True, source_root=self.root)
        with self.assertRaisesRegex(ValueError, "protected"):
            RUNNER.prepare_output_root(Path(tempfile.gettempdir()), overwrite=True, source_root=self.root)
        with self.assertRaisesRegex(ValueError, "protected"):
            RUNNER.prepare_output_root(Path(Path.cwd().anchor), overwrite=True, source_root=self.root)

    def test_source_parent_is_also_a_protected_output_root(self) -> None:
        source = self.root / "checkout" / "demo"
        source.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "protected"):
            RUNNER.prepare_output_root(
                source.parent, overwrite=True, source_root=source
            )

    def test_windows_multi_config_executable_is_resolved(self) -> None:
        executable = self.root / "build" / "bin" / "Release" / "csc3_demo_benchmark.exe"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"exe")
        self.assertEqual(
            RUNNER.resolve_executable(self.root / "build", "csc3_demo_benchmark"),
            executable.resolve(),
        )


class FormalPreflightContractTests(unittest.TestCase):
    def valid_context(self) -> dict[str, object]:
        return {
            "evidence_level": "formal",
            "case": "windhub",
            "report_intent": "delivery",
            "system": "Linux",
            "architecture": "x86_64",
            "cpu_vendor": "GenuineIntel",
            "cpu_model": "Intel Xeon Gold",
            "controlled_host_id": "solver-linux-intel-01",
            "source_dirty_at_start": False,
            "commit_sha": "a" * 40,
            "input_is_materialized": True,
            "input_is_tracked": True,
            "input_repository_relative_path": RUNNER.CANONICAL_WINDHUB_REPOSITORY_PATH,
            "input_matches_head_lfs": True,
            "input_sha256": "b" * 64,
            "input_size_bytes": 76111745,
            "warmup_count": 2,
            "repeat_count": 7,
            "requested_thread_counts": [1, 2, 4, 8, 16, 32],
            "physical_core_count": 32,
            "binding_environment": dict(RUNNER.REQUIRED_OPENMP_ENV),
            "openmp_found": True,
            "openmp_required": True,
        }

    def test_valid_formal_context_has_no_blockers(self) -> None:
        self.assertEqual(RUNNER.formal_preflight_blockers(self.valid_context()), [])

    def test_generated_case_can_never_be_formal(self) -> None:
        context = self.valid_context()
        context["case"] = "generated-tet4"
        self.assertTrue(any("WindHub" in item for item in RUNNER.formal_preflight_blockers(context)))

    def test_platform_host_and_dirty_gates(self) -> None:
        variants = [
            ("system", "Darwin", "Linux"),
            ("architecture", "arm64", "x86_64"),
            ("cpu_vendor", "Apple", "Intel"),
            ("controlled_host_id", "", "controlled host"),
            ("source_dirty_at_start", True, "clean Git"),
            ("commit_sha", "short", "full commit"),
        ]
        for key, value, message in variants:
            with self.subTest(key=key):
                context = self.valid_context()
                context[key] = value
                self.assertTrue(any(message in item for item in RUNNER.formal_preflight_blockers(context)))

    def test_input_warmup_repeat_thread_and_binding_gates(self) -> None:
        variants = [
            ("input_is_materialized", False, "materialized"),
            ("input_is_tracked", False, "tracked"),
            ("input_matches_head_lfs", False, "HEAD LFS"),
            ("warmup_count", 1, "warmups"),
            ("repeat_count", 6, "repeats"),
            ("requested_thread_counts", [1, 2, 4, 8, 32], "thread"),
            ("requested_thread_counts", [1, 2, 4, 8, 16], "physical-core"),
            ("binding_environment", {"OMP_DYNAMIC": "true"}, "binding"),
            ("openmp_found", False, "OpenMP"),
            ("openmp_required", False, "OpenMP"),
        ]
        for key, value, message in variants:
            with self.subTest(key=key, value=value):
                context = self.valid_context()
                context[key] = value
                self.assertTrue(any(message in item for item in RUNNER.formal_preflight_blockers(context)))


class EvidenceValidationTests(TemporaryDirectory):
    def test_junit_requires_actual_testcases_matching_declared_count(self) -> None:
        empty = self.root / "empty-suite.xml"
        empty.write_text('<testsuite tests="1" failures="0"/>', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "testcase"):
            RUNNER.validate_ctest_junit(empty)

    def test_junit_failure_and_skip_are_rejected(self) -> None:
        for body, expected in (
            ('<testsuite tests="1" failures="1"><testcase><failure/></testcase></testsuite>', "failures=1"),
            ('<testsuite tests="1" skipped="1"><testcase><skipped/></testcase></testsuite>', "skipped=1"),
        ):
            with self.subTest(expected=expected):
                path = self.root / f"{expected}.xml"
                path.write_text(body, encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, expected):
                    RUNNER.validate_ctest_junit(path)

    def test_materialized_tracked_input_must_match_head_lfs_pointer(self) -> None:
        repository = self.root / "repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repository, check=True)
        input_path = repository / "hub.inp"
        input_path.write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{'b' * 64}\nsize 4\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "hub.inp"], cwd=repository, check=True)
        subprocess.run(["git", "commit", "-qm", "pointer"], cwd=repository, check=True)
        input_path.write_bytes(b"data")
        options = RUNNER.build_argument_parser().parse_args(
            ["--case", "windhub", "--input", str(input_path), "--out-root", str(self.root / "out")]
        )
        facts = RUNNER._input_provenance(options, repository)
        self.assertTrue(facts["tracked"])
        self.assertFalse(facts["matches_head_lfs"])
        self.assertEqual(facts["head_lfs_oid_sha256"], "b" * 64)
        self.assertEqual(facts["head_lfs_size_bytes"], 4)


class ManifestAndSummaryContractTests(TemporaryDirectory):
    def setUp(self) -> None:
        super().setUp()
        self.csv_path = self.root / "benchmark_samples.csv"
        self.csv_path.write_text("schema_version,thread_count\nv1,1\n", encoding="utf-8")
        self.summary_json_path = self.root / "benchmark_summary.json"
        self.summary_data = {
            "schema_version": "csc3-demo-benchmark-v1",
            "configuration": {
                "case": "generated-tet4", "nx": 1, "ny": 1, "nz": 1,
                "thread_counts": [1, 2], "warmup_count": 2,
                "repeat_count": 7, "amortization_count": 1,
                "performance_evidence_level": "local-smoke",
            },
            "case_sizes": {
                "case_name": "generated-tet4-1x1x1",
                "element_type": "Tet4",
                "node_count": 8,
                "element_count": 6,
                "dof_count": 24,
                "nnz": 300,
            },
            "correctness": {
                "structure_matches": True,
                "relative_frobenius_error": 1.0e-15,
                "max_absolute_error": 1.0e-14,
                "max_absolute_tolerance": 1.0e-8,
                "status": "PASS",
            },
            "serial_measured_statistics": {
                "symbolic_total_ms": timing_statistics(sample_count=7),
                "numeric_total_ms": timing_statistics(sample_count=7),
            },
            "per_thread_measured_statistics": [
                thread_statistics(1, 7),
                thread_statistics(2, 7, symbolic_speedup=1.3, numeric_speedup=1.5),
            ],
            "estimated_persistent_bytes": 12345,
            "estimated_persistent_memory_kind": "owned_vector_payload_bytes_not_rss",
            "performance_evidence_level": "local-smoke",
            "performance_gate": {
                "status": "NOT_APPLICABLE_GENERATED_CASE",
                "applicable": False,
                "performance_requirements_met": False,
                "numeric_requirement_met": False,
                "symbolic_requirement_met": False,
                "numeric_thread_count": 0,
                "symbolic_thread_count": 0,
                "numeric_speedup_threshold": 1.5,
                "symbolic_speedup_threshold": 1.0,
                "maximum_coefficient_of_variation": 0.05,
            },
            "performance_gate_status": "NOT_APPLICABLE_GENERATED_CASE",
        }
        self.summary_json_path.write_text(json.dumps(self.summary_data), encoding="utf-8")

    def manifest_basis(self, evidence_level: str = "local-smoke") -> dict[str, object]:
        return {
            "schema_version": RUNNER.MANIFEST_SCHEMA_VERSION,
            "run_id": "run-20260713T000000Z-aaaaaaaaaaaa",
            "report_intent": "local-smoke",
            "status": "LOCAL_SMOKE",
            "evidence_level": evidence_level,
            "source": {"commit_sha": "a" * 40, "branch": "test", "source_dirty_at_start": False},
            "environment": {
                "system": "Darwin", "architecture": "arm64", "hostname": "host",
                "cpu_vendor": "Apple", "cpu_model": "M4", "physical_core_count": 10,
                "logical_core_count": 10, "total_memory_bytes": 32000000000,
                "python_version": platform.python_version(), "controlled_host_id": None,
            },
            "toolchain": {"cmake_version": "3.30", "compiler": "AppleClang 16", "openmp": {"found": True}},
            "input": {"case": "generated-tet4", "grid": {"nx": 1, "ny": 1, "nz": 1}},
            "benchmark": {
                "warmup_count": 2, "repeat_count": 7, "amortization_count": 1,
                "requested_thread_counts": [1, 2], "observed_thread_counts": [1, 2],
            },
            "commands": {"configure": ["cmake", "--preset", "delivery"], "build": ["cmake", "--build"], "ctest": ["ctest"], "benchmark": ["csc3_demo_benchmark"]},
            "binding_environment": dict(RUNNER.REQUIRED_OPENMP_ENV),
            "tasks": [{"name": "benchmark", "status": "PASS", "exit_code": 0, "error": None}],
            "blockers": ["formal controlled-host evidence was not requested"],
            "started_at_utc": "2026-07-13T00:00:00Z",
            "ended_at_utc": "2026-07-13T00:00:01Z",
        }

    def test_nonformal_summary_has_fixed_warning_twice_and_relative_links(self) -> None:
        markdown = RUNNER.render_markdown_summary(
            self.manifest_basis(), self.summary_data, self.csv_path
        )
        warning = RUNNER.NON_FORMAL_WARNING
        self.assertGreaterEqual(markdown.count(warning), 2)
        self.assertIn("[benchmark_samples.csv](benchmark_samples.csv)", markdown)
        self.assertIn("[benchmark_summary.json](benchmark_summary.json)", markdown)
        self.assertNotIn(str(self.root), markdown)
        self.assertIn("estimated persistent bytes", markdown)
        self.assertIn("not RSS", markdown)

    def test_artifact_records_are_relative_and_hash_bound(self) -> None:
        records = RUNNER.artifact_records(
            self.root, [self.csv_path, self.summary_json_path]
        )
        self.assertEqual([item["path"] for item in records], ["benchmark_samples.csv", "benchmark_summary.json"])
        for record in records:
            self.assertEqual(len(record["sha256"]), 64)
            self.assertGreater(record["size_bytes"], 0)

    def test_observed_teams_must_match_requested(self) -> None:
        observed = RUNNER.validate_observed_teams(self.summary_data, [1, 2])
        self.assertEqual(observed, [1, 2])
        bad = json.loads(json.dumps(self.summary_data))
        bad["per_thread_measured_statistics"][1]["numeric_thread_count_observed"] = 1
        with self.assertRaisesRegex(RuntimeError, "observed"):
            RUNNER.validate_observed_teams(bad, [1, 2])

    def test_summary_validation_rejects_evidence_gate_and_memory_drift(self) -> None:
        variants = [
            ("performance_evidence_level", "ci-smoke", "evidence_level"),
            ("estimated_persistent_memory_kind", "rss", "persistent-memory"),
            ("performance_gate_status", "PASS", "status fields disagree"),
        ]
        for key, value, message in variants:
            with self.subTest(key=key):
                bad = json.loads(json.dumps(self.summary_data))
                bad[key] = value
                path = self.root / f"bad-{key}.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, message):
                    RUNNER.validate_benchmark_summary(path, [1, 2], "local-smoke")

    def test_summary_validation_binds_configuration_and_recomputes_formal_gate(self) -> None:
        bad_configuration = json.loads(json.dumps(self.summary_data))
        bad_configuration["configuration"]["repeat_count"] = 999
        configuration_path = self.root / "bad-configuration.json"
        configuration_path.write_text(json.dumps(bad_configuration), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "repeat_count"):
            RUNNER.validate_benchmark_summary(
                configuration_path,
                [1, 2],
                "local-smoke",
                {
                    "case": "generated-tet4", "nx": 1, "ny": 1, "nz": 1,
                    "thread_counts": [1, 2], "warmup_count": 2,
                    "repeat_count": 7, "amortization_count": 1,
                    "performance_evidence_level": "local-smoke",
                },
            )

        forged = json.loads(json.dumps(self.summary_data))
        forged["configuration"]["case"] = "windhub"
        forged["configuration"]["nx"] = 0
        forged["configuration"]["ny"] = 0
        forged["configuration"]["nz"] = 0
        forged["configuration"]["performance_evidence_level"] = "formal"
        forged["performance_evidence_level"] = "formal"
        forged["performance_gate"]["status"] = "PASS"
        forged["performance_gate"]["applicable"] = False
        forged["performance_gate"]["performance_requirements_met"] = True
        forged["performance_gate_status"] = "PASS"
        forged_path = self.root / "forged-formal-gate.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "performance gate field"):
            RUNNER.validate_benchmark_summary(forged_path, [1, 2], "formal")

        forged_speedup = json.loads(json.dumps(self.summary_data))
        forged_speedup["per_thread_measured_statistics"][1]["numeric_speedup"] = 99.0
        forged_speedup_path = self.root / "forged-speedup.json"
        forged_speedup_path.write_text(json.dumps(forged_speedup), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "numeric_speedup"):
            RUNNER.validate_benchmark_summary(
                forged_speedup_path, [1, 2], "local-smoke"
            )

        overflow_speedup = json.loads(json.dumps(self.summary_data))
        overflow_speedup["serial_measured_statistics"]["symbolic_total_ms"] = (
            timing_statistics(value=1.0e308, sample_count=7)
        )
        overflow_speedup["per_thread_measured_statistics"][0]["symbolic_total_ms"] = (
            timing_statistics(value=5.0e-324, sample_count=7)
        )
        overflow_speedup["per_thread_measured_statistics"][1]["symbolic_total_ms"] = (
            timing_statistics(value=1.0e308 / 1.3, sample_count=7)
        )
        overflow_speedup_path = self.root / "overflow-speedup.json"
        overflow_speedup_path.write_text(
            json.dumps(overflow_speedup), encoding="utf-8"
        )
        with self.assertRaisesRegex(RuntimeError, "finite"):
            RUNNER.validate_benchmark_summary(
                overflow_speedup_path, [1, 2], "local-smoke"
            )

    def test_requested_teams_reject_bool_and_string_coercion(self) -> None:
        with self.assertRaises(ValueError):
            RUNNER.validate_observed_teams(self.summary_data, [True, 2])
        with self.assertRaises(ValueError):
            RUNNER.validate_observed_teams(self.summary_data, ["1", 2])

    def test_summary_covers_environment_commands_gates_and_blockers(self) -> None:
        manifest = self.manifest_basis()
        markdown = RUNNER.render_markdown_summary(
            manifest, self.summary_data, self.csv_path
        )
        self.assertIn("## Environment", markdown)
        self.assertIn("Darwin", markdown)
        self.assertIn("## Input", markdown)
        self.assertIn("generated-tet4", markdown)
        self.assertIn("## Commands", markdown)
        self.assertIn("cmake --preset delivery", markdown)
        self.assertIn("CV", markdown)
        self.assertIn("## Performance gate", markdown)
        self.assertIn("NOT_APPLICABLE_GENERATED_CASE", markdown)
        self.assertIn("## Limits and blockers", markdown)
        self.assertIn("formal controlled-host evidence was not requested", markdown)
        self.assertIn("[ctest.xml](ctest.xml)", markdown)

    def test_local_evidence_can_never_produce_pass(self) -> None:
        status, blockers = RUNNER.derive_run_status(
            evidence_level="local-smoke",
            report_intent="local-smoke",
            benchmark_summary=self.summary_data,
            command_failed=False,
        )
        self.assertEqual(status, "LOCAL_SMOKE")
        self.assertNotEqual(status, "PASS")
        self.assertTrue(blockers)

    def test_delivery_intent_without_formal_evidence_is_blocked(self) -> None:
        status, blockers = RUNNER.derive_run_status(
            evidence_level="local-smoke",
            report_intent="delivery",
            benchmark_summary=self.summary_data,
            command_failed=False,
        )
        self.assertEqual(status, "BLOCKED")
        self.assertTrue(any("formal" in item.lower() for item in blockers))


class WorkflowOrchestrationTests(TemporaryDirectory):
    def make_fake_source(self) -> tuple[Path, Path]:
        source = self.root / "source"
        (source / "scripts").mkdir(parents=True)
        (source / "CMakePresets.json").write_text("{}", encoding="utf-8")
        build = source / "build" / "delivery"
        (build / "bin").mkdir(parents=True)
        executable = build / "bin" / "csc3_demo_benchmark"
        executable.write_text("fake", encoding="utf-8")
        return source, build

    def fake_facts(self, source: Path, build: Path) -> dict[str, object]:
        return {
            "source": {"commit_sha": "a" * 40, "branch": "test", "source_dirty_at_start": False},
            "environment": {
                "system": "Linux", "architecture": "x86_64", "hostname": "test-host",
                "cpu_vendor": "GenuineIntel", "cpu_model": "Intel Test CPU",
                "physical_core_count": 16, "logical_core_count": 32,
                "total_memory_bytes": 64000000000, "python_version": platform.python_version(),
                "controlled_host_id": None,
            },
            "toolchain": {
                "cmake_version": "3.30.0", "compiler": "Clang 18",
                "openmp": {"found": True, "require_openmp": True},
                "preset": "delivery", "build_directory": str(build),
            },
            "repository_root": str(source.parent),
        }

    def benchmark_summary(self) -> dict[str, object]:
        return {
            "schema_version": "csc3-demo-benchmark-v1",
            "configuration": {
                "case": "generated-tet4", "nx": 1, "ny": 1, "nz": 1,
                "thread_counts": [1, 2], "warmup_count": 0,
                "repeat_count": 1, "amortization_count": 1,
                "performance_evidence_level": "local-smoke",
            },
            "case_sizes": {"case_name": "generated-tet4-1x1x1", "element_type": "Tet4", "node_count": 8, "element_count": 6, "dof_count": 24, "nnz": 300},
            "correctness": {"structure_matches": True, "relative_frobenius_error": 0.0, "max_absolute_error": 0.0, "max_absolute_tolerance": 1e-8, "status": "PASS"},
            "serial_measured_statistics": {
                "symbolic_total_ms": timing_statistics(),
                "numeric_total_ms": timing_statistics(),
            },
            "per_thread_measured_statistics": [thread_statistics(thread, 1) for thread in (1, 2)],
            "estimated_persistent_bytes": 1000,
            "estimated_persistent_memory_kind": "owned_vector_payload_bytes_not_rss",
            "performance_evidence_level": "local-smoke",
            "performance_gate": {
                "status": "NOT_APPLICABLE_GENERATED_CASE", "applicable": False,
                "performance_requirements_met": False,
                "numeric_requirement_met": False, "symbolic_requirement_met": False,
                "numeric_thread_count": 0, "symbolic_thread_count": 0,
                "numeric_speedup_threshold": 1.5,
                "symbolic_speedup_threshold": 1.0,
                "maximum_coefficient_of_variation": 0.05,
            },
            "performance_gate_status": "NOT_APPLICABLE_GENERATED_CASE",
        }

    def successful_command_runner(self, summary: dict[str, object]):
        def run(command, cwd, environment):
            command = [str(part) for part in command]
            if command[0] == "ctest":
                junit = Path(command[command.index("--output-junit") + 1])
                junit.write_text(
                    '<testsuite tests="1" failures="0" errors="0" skipped="0">'
                    '<testcase name="runner-contract"/></testsuite>',
                    encoding="utf-8",
                )
            if "--summary-json" in command:
                csv_path = Path(command[command.index("--samples-csv") + 1])
                json_path = Path(command[command.index("--summary-json") + 1])
                csv_path.write_text("schema_version,thread_count\nv1,1\n", encoding="utf-8")
                payload = json.loads(json.dumps(summary))
                payload["configuration"] = {
                    "case": command[command.index("--case") + 1],
                    "nx": int(command[command.index("--nx") + 1]) if "--nx" in command else 0,
                    "ny": int(command[command.index("--ny") + 1]) if "--ny" in command else 0,
                    "nz": int(command[command.index("--nz") + 1]) if "--nz" in command else 0,
                    "thread_counts": [int(item) for item in command[command.index("--threads-list") + 1].split(",")],
                    "warmup_count": int(command[command.index("--warmup") + 1]),
                    "repeat_count": int(command[command.index("--repeat") + 1]),
                    "amortization_count": int(command[command.index("--amortization-count") + 1]),
                    "performance_evidence_level": command[command.index("--evidence-level") + 1],
                }
                repeat_count = payload["configuration"]["repeat_count"]
                for statistics in payload["serial_measured_statistics"].values():
                    statistics["sample_count"] = repeat_count
                for row in payload["per_thread_measured_statistics"]:
                    for key, statistics in row.items():
                        if isinstance(statistics, dict) and "sample_count" in statistics:
                            statistics["sample_count"] = repeat_count
                json_path.write_text(json.dumps(payload), encoding="utf-8")
            return RUNNER.CommandResult(command=command, returncode=0, stdout="ok", stderr="")
        return run

    def test_dry_run_is_cwd_independent_and_creates_no_files(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        runner = mock.Mock(side_effect=AssertionError("dry-run executed a command"))
        with mock.patch.object(RUNNER, "collect_provenance", return_value=self.fake_facts(source, build)):
            with mock.patch.object(RUNNER.Path, "cwd", return_value=self.root / "unrelated"):
                result = RUNNER.run_workflow(
                    ["--source-dir", str(source), "--build-dir", str(build), "--out-root", str(output), "--dry-run"],
                    command_runner=runner,
                )
        self.assertEqual(result, 0)
        self.assertFalse(output.exists())
        runner.assert_not_called()

    def test_success_writes_five_hash_bound_artifacts_and_local_status(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        summary = self.benchmark_summary()
        with mock.patch.object(RUNNER, "collect_provenance", return_value=self.fake_facts(source, build)):
            result = RUNNER.run_workflow(
                ["--source-dir", str(source), "--build-dir", str(build), "--out-root", str(output), "--skip-build", "--warmup", "0", "--repeat", "1"],
                command_runner=self.successful_command_runner(summary),
            )
        self.assertEqual(result, 0)
        for name in RUNNER.OWNED_OUTPUT_NAMES:
            self.assertTrue((output / name).is_file(), name)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], RUNNER.MANIFEST_SCHEMA_VERSION)
        self.assertEqual(manifest["status"], "LOCAL_SMOKE")
        self.assertEqual(manifest["benchmark"]["observed_thread_counts"], [1, 2])
        self.assertEqual({item["path"] for item in manifest["artifacts"]}, {
            "ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md"
        })
        for artifact in manifest["artifacts"]:
            path = output / artifact["path"]
            self.assertEqual(RUNNER.sha256_file(path), artifact["sha256"])
            self.assertEqual(path.stat().st_size, artifact["size_bytes"])

    def test_pending_manifest_is_valid_before_first_command(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        summary = self.benchmark_summary()
        delegate = self.successful_command_runner(summary)

        def inspect_then_run(command, cwd, environment):
            manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PENDING")
            return delegate(command, cwd, environment)

        with mock.patch.object(RUNNER, "collect_provenance", return_value=self.fake_facts(source, build)):
            result = RUNNER.run_workflow(
                ["--source-dir", str(source), "--build-dir", str(build), "--out-root", str(output), "--skip-build", "--warmup", "0", "--repeat", "1"],
                command_runner=inspect_then_run,
            )
        self.assertEqual(result, 0)
        self.assertFalse(list(output.glob(".run_manifest.json.*.tmp")))

    def test_post_build_toolchain_refresh_preserves_start_source_facts(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        summary = self.benchmark_summary()
        initial = self.fake_facts(source, build)
        refreshed = json.loads(json.dumps(initial))
        refreshed["source"]["source_dirty_at_start"] = True
        refreshed["source"]["commit_sha"] = "b" * 40
        refreshed["toolchain"]["compiler"] = "Clang 19"
        with mock.patch.object(RUNNER, "collect_provenance", side_effect=[initial, refreshed]):
            result = RUNNER.run_workflow(
                ["--source-dir", str(source), "--build-dir", str(build), "--out-root", str(output), "--warmup", "0", "--repeat", "1"],
                command_runner=self.successful_command_runner(summary),
            )
        self.assertEqual(result, 0)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["commit_sha"], "a" * 40)
        self.assertFalse(manifest["source"]["source_dirty_at_start"])
        self.assertEqual(manifest["toolchain"]["compiler"], "Clang 19")

    def test_subprocess_failure_is_propagated_and_manifest_is_preserved(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        def fail(command, cwd, environment):
            return RUNNER.CommandResult(command=[str(item) for item in command], returncode=23, stdout="", stderr="boom")
        with mock.patch.object(RUNNER, "collect_provenance", return_value=self.fake_facts(source, build)):
            result = RUNNER.run_workflow(
                ["--source-dir", str(source), "--build-dir", str(build), "--out-root", str(output), "--skip-build"],
                command_runner=fail,
            )
        self.assertEqual(result, 23)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "FAIL")
        self.assertEqual(manifest["tasks"][0]["exit_code"], 23)
        self.assertIn("boom", manifest["tasks"][0]["error"])

    def test_formal_gate_failure_keeps_valid_benchmark_artifacts_and_exit_code(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        summary = self.benchmark_summary()
        threads = [1, 2, 4, 8, 16]
        summary["performance_evidence_level"] = "formal"
        summary["per_thread_measured_statistics"] = [
            dict(summary["per_thread_measured_statistics"][0],
                 thread_count=thread,
                 symbolic_thread_count_observed=thread,
                 numeric_thread_count_observed=thread)
            for thread in threads
        ]
        summary["performance_gate"] = {
            "status": "FAIL",
            "applicable": True,
            "performance_requirements_met": False,
            "numeric_requirement_met": False,
            "symbolic_requirement_met": False,
            "numeric_thread_count": 0,
            "symbolic_thread_count": 0,
            "numeric_speedup_threshold": 1.5,
            "symbolic_speedup_threshold": 1.0,
            "maximum_coefficient_of_variation": 0.05,
        }
        summary["performance_gate_status"] = "FAIL"
        facts = self.fake_facts(source, build)
        facts["environment"]["controlled_host_id"] = "controlled-01"
        facts["environment"]["physical_core_count"] = 16
        input_facts = {
            "case": "windhub", "materialized": True, "tracked": True,
            "matches_head_lfs": True, "sha256": "b" * 64,
            "size_bytes": 76111745,
            "repository_relative_path": RUNNER.CANONICAL_WINDHUB_REPOSITORY_PATH,
        }

        def formal_gate_runner(command, cwd, environment):
            result = self.successful_command_runner(summary)(command, cwd, environment)
            if "--summary-json" in [str(item) for item in command]:
                result.returncode = 17
                result.stderr = "formal performance gate failed"
            return result

        with mock.patch.object(RUNNER, "collect_provenance", return_value=facts), \
             mock.patch.object(RUNNER, "_input_provenance", return_value=input_facts):
            result = RUNNER.run_workflow(
                ["--source-dir", str(source), "--build-dir", str(build),
                 "--out-root", str(output), "--skip-build", "--case", "windhub",
                 "--input", str(self.root / "hub.inp"), "--threads-list", "1,2,4,8,16",
                 "--evidence-level", "formal", "--report-intent", "delivery",
                 "--controlled-host-id", "controlled-01"],
                command_runner=formal_gate_runner,
            )
        self.assertEqual(result, 17)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "FAIL")
        self.assertTrue((output / "benchmark_samples.csv").is_file())
        self.assertTrue((output / "benchmark_summary.json").is_file())
        self.assertTrue((output / "summary.md").is_file())
        self.assertEqual(manifest["tasks"][-1]["exit_code"], 17)
        self.assertIn("formal performance gate failed", manifest["tasks"][-1]["error"])
        self.assertEqual(
            {item["path"] for item in manifest["artifacts"]},
            {"ctest.xml", "benchmark_samples.csv", "benchmark_summary.json", "summary.md"},
        )
        for artifact in manifest["artifacts"]:
            path = output / artifact["path"]
            self.assertEqual(RUNNER.sha256_file(path), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
