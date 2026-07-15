#!/usr/bin/env python3
"""Contract tests for the reproducible CSC3 demo benchmark runner."""

from __future__ import annotations

import importlib.util
import csv
import json
import math
import os
import platform
import statistics
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest import mock


TEST_DIRECTORY = Path(__file__).resolve().parent
if str(TEST_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_DIRECTORY))

from report_test_fixture import (  # noqa: E402
    BENCHMARK_SCHEMA_V1,
    BENCHMARK_SCHEMA_V2,
    CSV_HEADER,
    EvidenceFixture,
)


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
    symbolic_total = 1.0 / symbolic_speedup
    numeric_algorithm = 1.0 / numeric_speedup
    symbolic_pattern = symbolic_total * 0.4
    symbolic_scatter = symbolic_total * 0.4
    numeric_reset = numeric_algorithm * 0.2
    numeric_kernel = numeric_algorithm * 0.8
    numeric_total = numeric_algorithm + 0.25
    row = {
        "thread_count": thread,
        "symbolic_thread_count_observed": thread,
        "numeric_thread_count_observed": thread,
        "symbolic_speedup": symbolic_speedup,
        "numeric_speedup": numeric_speedup,
    }
    values = {
        "symbolic_pattern_ms": symbolic_pattern,
        "symbolic_scatter_ms": symbolic_scatter,
        "symbolic_total_ms": symbolic_total,
        "numeric_reset_ms": numeric_reset,
        "numeric_kernel_ms": numeric_kernel,
        "numeric_algorithm_ms": numeric_algorithm,
        "numeric_total_ms": numeric_total,
        "amortized_total_ms": symbolic_total + numeric_total,
    }
    for key, value in values.items():
        row[key] = timing_statistics(value=value, sample_count=sample_count)
    return row


def validation_case(element_type: str, thread_count: int) -> dict[str, object]:
    is_tet4 = element_type == "Tet4"
    return {
        "case_name": "cube_tet4_1x1x1" if is_tet4 else "cube_hex8_1x1x1",
        "element_type": element_type,
        "node_count": 8,
        "element_count": 6 if is_tet4 else 1,
        "dof_count": 24,
        "thread_count": thread_count,
        "matrix": {
            "structure_matches": True,
            "relative_frobenius_error": 1.0e-15,
            "max_absolute_error": 1.0e-14,
            "reference_max_absolute_value": 0.99,
            "max_absolute_tolerance": 1.0e-8,
            "status": "PASS",
        },
        "displacement": {
            "relative_displacement_error": 1.0e-15,
            "parallel_relative_residual": 1.0e-15,
            "serial_relative_residual": 1.0e-15,
            "parallel_displacement_norm": 1.0e-6,
            "serial_displacement_norm": 1.0e-6,
            "status": "PASS",
        },
        "status": "PASS",
    }


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
            "cmake_version": "3.31.6",
        }

    def test_valid_formal_context_has_no_blockers(self) -> None:
        self.assertEqual(RUNNER.formal_preflight_blockers(self.valid_context()), [])

    def test_amd64_is_normalized_as_linux_x86_64(self) -> None:
        context = self.valid_context()
        context["architecture"] = "amd64"
        self.assertEqual(RUNNER.formal_preflight_blockers(context), [])

    def test_unknown_cmake_blocks_formal_evidence(self) -> None:
        context = self.valid_context()
        context["cmake_version"] = "unknown"
        self.assertTrue(
            any("CMake" in item for item in RUNNER.formal_preflight_blockers(context))
        )

    def test_prebuild_context_defers_openmp_checks_until_after_configuration(self) -> None:
        options = RUNNER.build_argument_parser().parse_args(
            [
                "--case", "windhub",
                "--input", "unused.inp",
                "--out-root", "unused-output",
                "--evidence-level", "formal",
                "--report-intent", "delivery",
                "--controlled-host-id", "controlled-01",
            ]
        )
        provenance = {
            "source": {
                "commit_sha": "a" * 40,
                "branch": "test",
                "source_dirty_at_start": False,
                "demo_version": "0.2.0",
            },
            "environment": {
                "system": "Linux",
                "architecture": "x86_64",
                "cpu_vendor": "GenuineIntel",
                "controlled_host_id": "controlled-01",
                "physical_core_count": 16,
            },
            "toolchain": {
                "cmake_version": "3.31.6",
                "openmp": {"found": False, "require_openmp": False},
            },
        }
        input_facts = {
            "case": "windhub",
            "materialized": True,
            "tracked": True,
            "matches_head_lfs": True,
            "repository_relative_path": RUNNER.CANONICAL_WINDHUB_REPOSITORY_PATH,
            "sha256": "b" * 64,
            "size_bytes": 123,
        }
        context = RUNNER._formal_context(
            options, provenance, input_facts, [1, 2, 4, 8, 16]
        )
        self.assertNotIn("openmp_found", context)
        self.assertNotIn("openmp_required", context)
        self.assertEqual(RUNNER.formal_preflight_blockers(context), [])

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


class ProjectVersionTests(TemporaryDirectory):
    def test_demo_readme_requires_cmake_3_21_for_evidence_and_junit(self) -> None:
        readme = (SCRIPT.parent.parent / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())
        self.assertNotIn("CMake `3.20`", readme)
        self.assertIn("All platforms require CMake `3.21` or newer", normalized)
        self.assertIn(
            "The evidence and JUnit workflow requires CMake `3.21` or newer.",
            normalized,
        )

    def test_multiline_project_version_is_strictly_parsed(self) -> None:
        (self.root / "CMakeLists.txt").write_text(
            "project(Csc3SymmetricAssemblyDemo\n"
            "    VERSION 0.2.0\n"
            "    LANGUAGES CXX\n"
            ")\n",
            encoding="utf-8",
        )
        self.assertEqual(RUNNER._read_project_version(self.root), "0.2.0")

    def test_comments_and_parentheses_in_description_do_not_confuse_parser(self) -> None:
        (self.root / "CMakeLists.txt").write_text(
            "#[[ project(Csc3SymmetricAssemblyDemo VERSION 9.9.9) ]]\n"
            "# project(Csc3SymmetricAssemblyDemo VERSION 8.8.8)\n"
            "project(Csc3SymmetricAssemblyDemo\n"
            "    VERSION 0.2.0\n"
            "    DESCRIPTION \"CSC3 (demo)\"\n"
            "    LANGUAGES CXX\n"
            ")\n",
            encoding="utf-8",
        )
        self.assertEqual(RUNNER._read_project_version(self.root), "0.2.0")

    def test_quoted_and_bracket_arguments_do_not_create_project_declarations(self) -> None:
        (self.root / "CMakeLists.txt").write_text(
            'set(QUOTED "project(Csc3SymmetricAssemblyDemo VERSION 9.9.9)")\n'
            "set(BRACKET [=[project(Csc3SymmetricAssemblyDemo VERSION 8.8.8)]=])\n"
            "project(Csc3SymmetricAssemblyDemo VERSION 0.2.0 LANGUAGES CXX)\n",
            encoding="utf-8",
        )
        self.assertEqual(RUNNER._read_project_version(self.root), "0.2.0")

    def test_missing_non_semver_and_ambiguous_project_versions_are_rejected(self) -> None:
        variants = (
            "project(Csc3SymmetricAssemblyDemo LANGUAGES CXX)\n",
            "project(Csc3SymmetricAssemblyDemo VERSION 0.2 LANGUAGES CXX)\n",
            "project(Csc3SymmetricAssemblyDemo VERSION 0.2.0.1 LANGUAGES CXX)\n",
            "project(Csc3SymmetricAssemblyDemo VERSION ${DEMO_VERSION} LANGUAGES CXX)\n",
            "project(AnotherDemo VERSION 0.2.0 LANGUAGES CXX)\n",
            "project(Csc3SymmetricAssemblyDemo VERSION 1.0.0)\n"
            "project(Csc3SymmetricAssemblyDemo VERSION 2.0.0)\n",
        )
        for index, text in enumerate(variants):
            with self.subTest(text=text):
                source = self.root / str(index)
                source.mkdir()
                (source / "CMakeLists.txt").write_text(text, encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    RUNNER._read_project_version(source)


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
                "reference_max_absolute_value": 0.99,
                "max_absolute_tolerance": 1.0e-8,
                "status": "PASS",
            },
            "validation_cases_schema_version": "csc3-demo-validation-v1",
            "validation_thresholds": {
                "relative_frobenius_error_max": 1.0e-8,
                "relative_displacement_error_max": 1.0e-8,
                "relative_residual_max": 1.0e-10,
            },
            "validation_cases": [
                validation_case("Tet4", 2),
                validation_case("Hex8", 2),
            ],
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

    def test_summary_validation_accepts_structured_validation_evidence(self) -> None:
        parsed, observed = RUNNER.validate_benchmark_summary(
            self.summary_json_path, [1, 2], "local-smoke"
        )
        self.assertEqual(observed, [1, 2])
        self.assertEqual(
            [case["element_type"] for case in parsed["validation_cases"]],
            ["Tet4", "Hex8"],
        )

    def test_v2_summary_is_recomputed_from_exact_csv(self) -> None:
        fixture = EvidenceFixture(self.root / "v2")
        parsed, observed = RUNNER.validate_benchmark_summary(
            fixture.root / "benchmark_summary.json",
            fixture.threads,
            fixture.evidence_level,
            fixture.summary["configuration"],
            samples_csv_path=fixture.root / "benchmark_samples.csv",
            require_current_schema=True,
        )
        self.assertEqual(parsed["schema_version"], BENCHMARK_SCHEMA_V2)
        self.assertEqual(observed, fixture.threads)

    def test_v2_summary_accepts_an_immutable_csv_snapshot(self) -> None:
        fixture = EvidenceFixture(self.root / "v2-bytes")
        snapshot = (fixture.root / "benchmark_samples.csv").read_bytes()

        try:
            parsed, observed = RUNNER.validate_benchmark_summary(
                fixture.root / "benchmark_summary.json",
                fixture.threads,
                fixture.evidence_level,
                fixture.summary["configuration"],
                samples_csv_path=snapshot,
                require_current_schema=True,
            )
        except (RuntimeError, TypeError) as error:
            self.fail(f"v2 validation must accept immutable CSV bytes: {error}")

        self.assertEqual(parsed["schema_version"], BENCHMARK_SCHEMA_V2)
        self.assertEqual(observed, fixture.threads)

    def test_v2_csv_boolean_text_is_exact_and_summary_bound(self) -> None:
        for index, value in enumerate(("True", "FALSE", "1", "false")):
            with self.subTest(value=value):
                fixture = EvidenceFixture(self.root / f"bool-{index}")
                fixture.rows[0]["symbolic_plan_matches_serial"] = value
                fixture.write_csv()
                with self.assertRaises(RuntimeError):
                    RUNNER.validate_benchmark_summary(
                        fixture.root / "benchmark_summary.json",
                        fixture.threads,
                        fixture.evidence_level,
                        fixture.summary["configuration"],
                        samples_csv_path=fixture.root / "benchmark_samples.csv",
                        require_current_schema=True,
                    )

    def test_v2_raw_thread_and_root_scatter_tampering_is_rejected(self) -> None:
        mutations = (
            lambda summary: summary["raw_samples"][0].update(
                {"numeric_setup_plan_matches_serial": False}
            ),
            lambda summary: summary["per_thread_measured_statistics"][0].update(
                {"symbolic_plan_match_count": 0}
            ),
            lambda summary: summary["per_thread_measured_statistics"][0].update(
                {"scatter_status": "FAIL"}
            ),
            lambda summary: summary["scatter_correctness"].update(
                {"numeric_setup_plan_match_count": 0}
            ),
            lambda summary: summary["scatter_correctness"].update(
                {"status": "FAIL"}
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                fixture = EvidenceFixture(self.root / f"scatter-{index}")
                mutate(fixture.summary)
                fixture.write_summary()
                with self.assertRaises(RuntimeError):
                    RUNNER.validate_benchmark_summary(
                        fixture.root / "benchmark_summary.json",
                        fixture.threads,
                        fixture.evidence_level,
                        fixture.summary["configuration"],
                        samples_csv_path=fixture.root / "benchmark_samples.csv",
                        require_current_schema=True,
                    )

    def test_v2_serial_cv_cannot_be_forged_to_formal_pass(self) -> None:
        fixture = EvidenceFixture(
            self.root / "serial-cv",
            evidence_level="formal",
            report_intent="delivery",
        )
        measured = [5.0, 10.0, 10.0, 10.0, 10.0, 10.0, 15.0]
        for row in fixture.rows:
            sample_index = int(row["sample_index"])
            if sample_index >= fixture.warmup:
                row["serial_symbolic_ms"] = str(
                    measured[sample_index - fixture.warmup]
                )
        mean = statistics.fmean(measured)
        summary_statistics = {
            "sample_count": len(measured),
            "mean_ms": mean,
            "median_ms": statistics.median(measured),
            "population_standard_deviation_ms": statistics.pstdev(measured),
            "minimum_ms": min(measured),
            "maximum_ms": max(measured),
            "coefficient_of_variation": statistics.pstdev(measured) / mean,
        }
        fixture.summary["serial_measured_statistics"]["symbolic_total_ms"] = (
            summary_statistics
        )
        fixture.write_csv()
        fixture.write_summary()
        with self.assertRaises(RuntimeError):
            RUNNER.validate_benchmark_summary(
                fixture.root / "benchmark_summary.json",
                fixture.threads,
                fixture.evidence_level,
                fixture.summary["configuration"],
                samples_csv_path=fixture.root / "benchmark_samples.csv",
                require_current_schema=True,
            )

    def test_v2_consistent_correctness_validation_and_scatter_failures_are_evidence(self) -> None:
        fixtures = []

        correctness = EvidenceFixture(self.root / "valid-correctness-fail")
        correctness.summary["correctness"].update(
            {"relative_frobenius_error": 2.0e-8, "status": "FAIL"}
        )
        for row in correctness.rows:
            row.update(
                {
                    "relative_frobenius_error": "2e-8",
                    "matrix_correctness_status": "FAIL",
                }
            )
        fixtures.append(correctness)

        validation = EvidenceFixture(self.root / "valid-validation-fail")
        validation_case = validation.summary["validation_cases"][0]
        validation_case["displacement"].update(
            {"relative_displacement_error": 2.0e-8, "status": "FAIL"}
        )
        validation_case["status"] = "FAIL"
        fixtures.append(validation)

        scatter = EvidenceFixture(self.root / "valid-scatter-fail")
        scatter.rows[0]["symbolic_plan_matches_serial"] = "false"
        scatter.summary["raw_samples"][0]["symbolic_plan_matches_serial"] = False
        scatter.summary["per_thread_measured_statistics"][0].update(
            {
                "symbolic_plan_match_count": scatter.warmup + scatter.repeat - 1,
                "scatter_status": "FAIL",
            }
        )
        scatter.summary["scatter_correctness"].update(
            {
                "symbolic_plan_match_count": len(scatter.rows) - 1,
                "status": "FAIL",
            }
        )
        fixtures.append(scatter)

        for fixture in fixtures:
            with self.subTest(root=fixture.root.name):
                fixture.write_csv()
                fixture.write_summary()
                parsed, _ = RUNNER.validate_benchmark_summary(
                    fixture.root / "benchmark_summary.json",
                    fixture.threads,
                    fixture.evidence_level,
                    fixture.summary["configuration"],
                    samples_csv_path=fixture.root / "benchmark_samples.csv",
                    require_current_schema=True,
                )
                status, _ = RUNNER.derive_run_status(
                    evidence_level=fixture.evidence_level,
                    report_intent=fixture.report_intent,
                    benchmark_summary=parsed,
                    command_failed=True,
                )
                self.assertEqual(status, "FAIL")

    def test_v1_is_read_only_local_compatible_but_not_current_or_formal(self) -> None:
        local = EvidenceFixture(
            self.root / "legacy-local", schema_version=BENCHMARK_SCHEMA_V1
        )
        parsed, observed = RUNNER.validate_benchmark_summary(
            local.root / "benchmark_summary.json",
            local.threads,
            local.evidence_level,
            local.summary["configuration"],
            samples_csv_path=local.root / "benchmark_samples.csv",
        )
        self.assertEqual(parsed["schema_version"], BENCHMARK_SCHEMA_V1)
        self.assertEqual(observed, local.threads)

        with self.assertRaisesRegex(RuntimeError, "v1|legacy|current"):
            RUNNER.validate_benchmark_summary(
                local.root / "benchmark_summary.json",
                local.threads,
                local.evidence_level,
                local.summary["configuration"],
                samples_csv_path=local.root / "benchmark_samples.csv",
                require_current_schema=True,
            )

        formal = EvidenceFixture(
            self.root / "legacy-formal",
            evidence_level="formal",
            report_intent="delivery",
            schema_version=BENCHMARK_SCHEMA_V1,
        )
        with self.assertRaisesRegex(RuntimeError, "v1|legacy|formal"):
            RUNNER.validate_benchmark_summary(
                formal.root / "benchmark_summary.json",
                formal.threads,
                formal.evidence_level,
                formal.summary["configuration"],
                samples_csv_path=formal.root / "benchmark_samples.csv",
            )

    def test_summary_validation_allows_mean_roundoff_at_sample_range_boundaries(
        self,
    ) -> None:
        sample_value = 0.000208
        rounded_values = {
            "below-minimum": math.nextafter(sample_value, -math.inf),
            "above-maximum": math.nextafter(sample_value, math.inf),
        }
        for label, rounded_mean in rounded_values.items():
            with self.subTest(label=label):
                summary = json.loads(json.dumps(self.summary_data))
                statistics = summary["per_thread_measured_statistics"][1][
                    "numeric_reset_ms"
                ]
                statistics.update(
                    {
                        "mean_ms": rounded_mean,
                        "median_ms": sample_value,
                        "minimum_ms": sample_value,
                        "maximum_ms": sample_value,
                    }
                )
                path = self.root / f"roundoff-{label}.json"
                path.write_text(json.dumps(summary), encoding="utf-8")

                parsed, observed = RUNNER.validate_benchmark_summary(
                    path, [1, 2], "local-smoke"
                )

                self.assertEqual(observed, [1, 2])
                self.assertEqual(
                    parsed["per_thread_measured_statistics"][1][
                        "numeric_reset_ms"
                    ]["mean_ms"],
                    rounded_mean,
                )

    def test_summary_validation_rejects_materially_out_of_range_mean(self) -> None:
        sample_value = 0.000208
        for label, invalid_mean in {
            "below-minimum": sample_value - 1.0e-9,
            "above-maximum": sample_value + 1.0e-9,
        }.items():
            with self.subTest(label=label):
                summary = json.loads(json.dumps(self.summary_data))
                statistics = summary["per_thread_measured_statistics"][1][
                    "numeric_reset_ms"
                ]
                statistics.update(
                    {
                        "mean_ms": invalid_mean,
                        "median_ms": sample_value,
                        "minimum_ms": sample_value,
                        "maximum_ms": sample_value,
                    }
                )
                path = self.root / f"invalid-mean-{label}.json"
                path.write_text(json.dumps(summary), encoding="utf-8")

                with self.assertRaisesRegex(RuntimeError, "outside the sample range"):
                    RUNNER.validate_benchmark_summary(
                        path, [1, 2], "local-smoke"
                    )

    def test_summary_validation_recomputes_every_max_absolute_tolerance(self) -> None:
        targets = (
            ("root", lambda summary: summary["correctness"]),
            ("Tet4", lambda summary: summary["validation_cases"][0]["matrix"]),
            ("Hex8", lambda summary: summary["validation_cases"][1]["matrix"]),
        )
        mutations = (
            lambda matrix: matrix.update({"max_absolute_tolerance": 2.0e-8}),
            lambda matrix: matrix.update({"reference_max_absolute_value": 0.5}),
            lambda matrix: matrix.update(
                {"max_absolute_error": 1.0, "max_absolute_tolerance": 2.0}
            ),
        )
        for target_name, select in targets:
            for mutation_index, mutate in enumerate(mutations):
                with self.subTest(target=target_name, mutation=mutation_index):
                    bad = json.loads(json.dumps(self.summary_data))
                    mutate(select(bad))
                    path = self.root / f"bad-tolerance-{target_name}-{mutation_index}.json"
                    path.write_text(json.dumps(bad), encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, "tolerance|reference"):
                        RUNNER.validate_benchmark_summary(
                            path, [1, 2], "local-smoke"
                        )

    def test_summary_validation_translates_huge_json_numbers_to_domain_errors(self) -> None:
        huge = 10**400
        targets = (
            (
                "correctness",
                lambda summary: summary["correctness"].__setitem__(
                    "relative_frobenius_error", huge
                ),
            ),
            (
                "statistics",
                lambda summary: summary["serial_measured_statistics"][
                    "symbolic_total_ms"
                ].__setitem__("mean_ms", huge),
            ),
            (
                "gate-threshold",
                lambda summary: summary["performance_gate"].__setitem__(
                    "numeric_speedup_threshold", huge
                ),
            ),
            (
                "speedup",
                lambda summary: summary["per_thread_measured_statistics"][0].__setitem__(
                    "symbolic_speedup", huge
                ),
            ),
            (
                "validation-matrix",
                lambda summary: summary["validation_cases"][0]["matrix"].__setitem__(
                    "relative_frobenius_error", huge
                ),
            ),
            (
                "validation-displacement",
                lambda summary: summary["validation_cases"][0][
                    "displacement"
                ].__setitem__("parallel_relative_residual", huge),
            ),
        )
        for name, mutate in targets:
            with self.subTest(name=name):
                bad = json.loads(json.dumps(self.summary_data))
                mutate(bad)
                path = self.root / f"huge-{name}.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "numeric value"):
                    RUNNER.validate_benchmark_summary(
                        path, [1, 2], "local-smoke"
                    )

    def test_summary_validation_rejects_missing_or_corrupt_validation_case(self) -> None:
        missing = json.loads(json.dumps(self.summary_data))
        del missing["validation_cases"]
        missing_path = self.root / "missing-validation-cases.json"
        missing_path.write_text(json.dumps(missing), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "validation"):
            RUNNER.validate_benchmark_summary(
                missing_path, [1, 2], "local-smoke"
            )

        corrupt = json.loads(json.dumps(self.summary_data))
        corrupt["validation_cases"][1]["displacement"][
            "parallel_relative_residual"
        ] = 1.1e-10
        corrupt_path = self.root / "corrupt-validation-case.json"
        corrupt_path.write_text(json.dumps(corrupt), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "validation"):
            RUNNER.validate_benchmark_summary(
                corrupt_path, [1, 2], "local-smoke"
            )

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
        with self.assertRaisesRegex(RuntimeError, "performance gate field|legacy"):
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
        (source / "CMakeLists.txt").write_text(
            "project(Csc3SymmetricAssemblyDemo VERSION 0.2.0 LANGUAGES CXX)\n",
            encoding="utf-8",
        )
        build = source / "build" / "delivery"
        (build / "bin").mkdir(parents=True)
        executable = build / "bin" / "csc3_demo_benchmark"
        executable.write_text("fake", encoding="utf-8")
        return source, build

    def fake_facts(self, source: Path, build: Path) -> dict[str, object]:
        return {
            "source": {
                "commit_sha": "a" * 40,
                "branch": "test",
                "source_dirty_at_start": False,
                "demo_version": "0.2.0",
            },
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
        per_thread = [thread_statistics(thread, 1) for thread in (1, 2)]
        for row in per_thread:
            row.update(
                {
                    "symbolic_plan_check_count": 1,
                    "symbolic_plan_match_count": 1,
                    "numeric_setup_plan_matches_serial": True,
                    "scatter_status": "PASS",
                }
            )
        return {
            "schema_version": BENCHMARK_SCHEMA_V2,
            "configuration": {
                "case": "generated-tet4", "nx": 1, "ny": 1, "nz": 1,
                "thread_counts": [1, 2], "warmup_count": 0,
                "repeat_count": 1, "amortization_count": 1,
                "performance_evidence_level": "local-smoke",
            },
            "case_sizes": {"case_name": "generated-tet4-1x1x1", "element_type": "Tet4", "node_count": 8, "element_count": 6, "dof_count": 24, "nnz": 300},
            "correctness": {
                "structure_matches": True,
                "relative_frobenius_error": 0.0,
                "max_absolute_error": 0.0,
                "reference_max_absolute_value": 0.99,
                "max_absolute_tolerance": 1e-8,
                "status": "PASS",
            },
            "validation_cases_schema_version": "csc3-demo-validation-v1",
            "validation_thresholds": {
                "relative_frobenius_error_max": 1.0e-8,
                "relative_displacement_error_max": 1.0e-8,
                "relative_residual_max": 1.0e-10,
            },
            "validation_cases": [
                validation_case("Tet4", 2),
                validation_case("Hex8", 2),
            ],
            "serial_measured_statistics": {
                "symbolic_total_ms": timing_statistics(),
                "numeric_total_ms": timing_statistics(),
            },
            "per_thread_measured_statistics": per_thread,
            "estimated_persistent_bytes": 1000,
            "estimated_persistent_memory_kind": "owned_vector_payload_bytes_not_rss",
            "performance_evidence_level": "local-smoke",
            "performance_gate": {
                "status": "NOT_APPLICABLE_GENERATED_CASE", "applicable": False,
                "performance_requirements_met": False,
                "numeric_requirement_met": False, "symbolic_requirement_met": False,
                "serial_symbolic_cv_requirement_met": False,
                "serial_numeric_cv_requirement_met": False,
                "scatter_requirement_met": False,
                "formal_requirements_met": False,
                "numeric_thread_count": 0, "symbolic_thread_count": 0,
                "numeric_speedup_threshold": 1.5,
                "symbolic_speedup_threshold": 1.0,
                "maximum_coefficient_of_variation": 0.05,
            },
            "performance_gate_status": "NOT_APPLICABLE_GENERATED_CASE",
            "raw_samples": [
                {
                    "thread_count": thread,
                    "sample_index": 0,
                    "sample_kind": "measured",
                    "symbolic_plan_matches_serial": True,
                    "numeric_setup_plan_matches_serial": True,
                }
                for thread in (1, 2)
            ],
            "scatter_correctness": {
                "symbolic_plan_check_count": 2,
                "symbolic_plan_match_count": 2,
                "numeric_setup_plan_check_count": 2,
                "numeric_setup_plan_match_count": 2,
                "status": "PASS",
            },
        }

    def formal_facts(self, source: Path, build: Path) -> dict[str, object]:
        facts = self.fake_facts(source, build)
        facts["environment"]["controlled_host_id"] = "controlled-01"
        facts["environment"]["physical_core_count"] = 16
        return facts

    def formal_input_facts(self) -> dict[str, object]:
        return {
            "case": "windhub",
            "path": str((self.root / "hub.inp").resolve()),
            "materialized": True,
            "tracked": True,
            "matches_head_lfs": True,
            "sha256": "b" * 64,
            "size_bytes": 76111745,
            "repository_relative_path": RUNNER.CANONICAL_WINDHUB_REPOSITORY_PATH,
            "head_lfs_oid_sha256": "b" * 64,
            "head_lfs_size_bytes": 76111745,
        }

    def formal_summary(self) -> dict[str, object]:
        summary = self.benchmark_summary()
        threads = [1, 2, 4, 8, 16]
        summary["performance_evidence_level"] = "formal"
        summary["per_thread_measured_statistics"] = [
            dict(
                summary["per_thread_measured_statistics"][0],
                thread_count=thread,
                symbolic_thread_count_observed=thread,
                numeric_thread_count_observed=thread,
            )
            for thread in threads
        ]
        summary["performance_gate"] = {
            "status": "FAIL",
            "applicable": True,
            "performance_requirements_met": False,
            "numeric_requirement_met": False,
            "symbolic_requirement_met": False,
            "serial_symbolic_cv_requirement_met": True,
            "serial_numeric_cv_requirement_met": True,
            "scatter_requirement_met": True,
            "formal_requirements_met": False,
            "numeric_thread_count": 0,
            "symbolic_thread_count": 0,
            "numeric_speedup_threshold": 1.5,
            "symbolic_speedup_threshold": 1.0,
            "maximum_coefficient_of_variation": 0.05,
        }
        summary["performance_gate_status"] = "FAIL"
        return summary

    def formal_arguments(self, source: Path, build: Path, output: Path) -> list[str]:
        return [
            "--source-dir",
            str(source),
            "--build-dir",
            str(build),
            "--out-root",
            str(output),
            "--case",
            "windhub",
            "--input",
            str(self.root / "hub.inp"),
            "--threads-list",
            "1,2,4,8,16",
            "--evidence-level",
            "formal",
            "--report-intent",
            "delivery",
            "--controlled-host-id",
            "controlled-01",
        ]

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
                payload = json.loads(json.dumps(summary))
                case = command[command.index("--case") + 1]
                threads = [
                    int(item)
                    for item in command[
                        command.index("--threads-list") + 1
                    ].split(",")
                ]
                warmup_count = int(command[command.index("--warmup") + 1])
                repeat_count = int(command[command.index("--repeat") + 1])
                amortization_count = int(
                    command[command.index("--amortization-count") + 1]
                )
                evidence_level = command[command.index("--evidence-level") + 1]
                payload["schema_version"] = BENCHMARK_SCHEMA_V2
                payload["configuration"] = {
                    "case": case,
                    "nx": int(command[command.index("--nx") + 1]) if "--nx" in command else 0,
                    "ny": int(command[command.index("--ny") + 1]) if "--ny" in command else 0,
                    "nz": int(command[command.index("--nz") + 1]) if "--nz" in command else 0,
                    "thread_counts": threads,
                    "warmup_count": warmup_count,
                    "repeat_count": repeat_count,
                    "amortization_count": amortization_count,
                    "performance_evidence_level": evidence_level,
                }
                windhub = case == "windhub"
                case_name = (
                    "3d-WindTurbineHub.inp"
                    if windhub
                    else "generated-tet4-1x1x1"
                )
                payload["case_sizes"]["case_name"] = case_name
                payload["input_prepare_ms"] = 0.5
                payload["performance_evidence_level"] = evidence_level
                payload["numeric_speedup_basis"] = (
                    "serial_reset_plus_kernel_over_atomic_reset_plus_kernel"
                )
                serial_symbolic = 1.0
                serial_numeric = 1.0
                symbolic_total = 2.0 if windhub else 1.0
                symbolic_pattern = symbolic_total * 0.4
                symbolic_scatter = symbolic_total * 0.4
                numeric_reset = 0.2
                numeric_kernel = 0.8
                numeric_algorithm = numeric_reset + numeric_kernel
                numeric_total = numeric_algorithm + 0.25
                amortized_total = (
                    symbolic_total / amortization_count + numeric_total
                )
                symbolic_speedup = serial_symbolic / symbolic_total
                numeric_speedup = serial_numeric / numeric_algorithm

                payload["serial_measured_statistics"] = {
                    "symbolic_total_ms": timing_statistics(
                        serial_symbolic, repeat_count
                    ),
                    "numeric_total_ms": timing_statistics(
                        serial_numeric, repeat_count
                    ),
                }
                payload["per_thread_measured_statistics"] = []
                raw_samples = []
                csv_rows = []
                for thread in threads:
                    measured = thread_statistics(
                        thread,
                        repeat_count,
                        symbolic_speedup=symbolic_speedup,
                        numeric_speedup=numeric_speedup,
                    )
                    measured["amortized_total_ms"] = timing_statistics(
                        amortized_total, repeat_count
                    )
                    measured.update(
                        {
                            "symbolic_plan_check_count": warmup_count
                            + repeat_count,
                            "symbolic_plan_match_count": warmup_count
                            + repeat_count,
                            "numeric_setup_plan_matches_serial": True,
                            "scatter_status": "PASS",
                        }
                    )
                    payload["per_thread_measured_statistics"].append(measured)
                    for sample_index in range(warmup_count + repeat_count):
                        sample_kind = (
                            "warmup"
                            if sample_index < warmup_count
                            else "measured"
                        )
                        raw_samples.append(
                            {
                                "thread_count": thread,
                                "sample_index": sample_index,
                                "sample_kind": sample_kind,
                                "symbolic_plan_matches_serial": True,
                                "numeric_setup_plan_matches_serial": True,
                            }
                        )
                        csv_rows.append(
                            {
                                "schema_version": BENCHMARK_SCHEMA_V2,
                                "case_name": case_name,
                                "element_type": "Tet4",
                                "nx": payload["configuration"]["nx"],
                                "ny": payload["configuration"]["ny"],
                                "nz": payload["configuration"]["nz"],
                                "node_count": 8,
                                "element_count": 6,
                                "dof_count": 24,
                                "nnz": 300,
                                "thread_count": thread,
                                "sample_index": sample_index,
                                "sample_kind": sample_kind,
                                "input_prepare_ms": 0.5,
                                "serial_symbolic_ms": serial_symbolic,
                                "serial_numeric_ms": serial_numeric,
                                "symbolic_pattern_ms": symbolic_pattern,
                                "symbolic_scatter_ms": symbolic_scatter,
                                "symbolic_total_ms": symbolic_total,
                                "numeric_reset_ms": numeric_reset,
                                "numeric_kernel_ms": numeric_kernel,
                                "numeric_total_ms": numeric_total,
                                "amortized_total_ms": amortized_total,
                                "symbolic_speedup": symbolic_speedup,
                                "numeric_speedup": numeric_speedup,
                                "relative_frobenius_error": 0.0,
                                "max_absolute_error": 0.0,
                                "matrix_correctness_status": "PASS",
                                "estimated_persistent_bytes": 1000,
                                "performance_evidence_level": evidence_level,
                                "symbolic_plan_matches_serial": "true",
                                "numeric_setup_plan_matches_serial": "true",
                            }
                        )
                payload["raw_samples"] = raw_samples
                payload["scatter_correctness"] = {
                    "symbolic_plan_check_count": len(csv_rows),
                    "symbolic_plan_match_count": len(csv_rows),
                    "numeric_setup_plan_check_count": len(threads),
                    "numeric_setup_plan_match_count": len(threads),
                    "status": "PASS",
                }
                if windhub:
                    gate = {
                        "status": (
                            "FAIL"
                            if evidence_level == "formal"
                            else "NON_FORMAL_LOCAL_SMOKE"
                        ),
                        "applicable": True,
                        "performance_requirements_met": False,
                        "numeric_requirement_met": False,
                        "symbolic_requirement_met": False,
                        "serial_symbolic_cv_requirement_met": True,
                        "serial_numeric_cv_requirement_met": True,
                        "scatter_requirement_met": True,
                        "formal_requirements_met": False,
                        "numeric_thread_count": 0,
                        "symbolic_thread_count": 0,
                    }
                else:
                    gate = {
                        "status": "NOT_APPLICABLE_GENERATED_CASE",
                        "applicable": False,
                        "performance_requirements_met": False,
                        "numeric_requirement_met": False,
                        "symbolic_requirement_met": False,
                        "serial_symbolic_cv_requirement_met": False,
                        "serial_numeric_cv_requirement_met": False,
                        "scatter_requirement_met": False,
                        "formal_requirements_met": False,
                        "numeric_thread_count": 0,
                        "symbolic_thread_count": 0,
                    }
                gate.update(
                    {
                        "numeric_speedup_threshold": 1.5,
                        "symbolic_speedup_threshold": 1.0,
                        "maximum_coefficient_of_variation": 0.05,
                    }
                )
                payload["performance_gate"] = gate
                payload["performance_gate_status"] = gate["status"]
                with csv_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(
                        stream, fieldnames=CSV_HEADER, lineterminator="\n"
                    )
                    writer.writeheader()
                    writer.writerows(csv_rows)
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

    def test_formal_skip_build_is_rejected_before_output_creation(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        with self.assertRaisesRegex(ValueError, "formal.*skip-build"):
            RUNNER.run_workflow(
                [
                    "--source-dir", str(source),
                    "--build-dir", str(build),
                    "--out-root", str(output),
                    "--case", "windhub",
                    "--input", str(self.root / "not-read.inp"),
                    "--evidence-level", "formal",
                    "--report-intent", "delivery",
                    "--skip-build",
                ]
            )
        self.assertFalse(output.exists())

    def test_formal_non_delivery_preset_is_rejected_before_output_creation(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        with self.assertRaisesRegex(ValueError, "formal.*delivery.*preset"):
            RUNNER.run_workflow(
                [
                    "--source-dir",
                    str(source),
                    "--build-dir",
                    str(build),
                    "--out-root",
                    str(output),
                    "--case",
                    "windhub",
                    "--input",
                    str(self.root / "not-read.inp"),
                    "--evidence-level",
                    "formal",
                    "--report-intent",
                    "delivery",
                    "--preset",
                    "debug",
                ]
            )
        self.assertFalse(output.exists())

    def test_only_later_provenance_checks_exclude_the_owned_output_root(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        observations = []

        def collect(*args, **kwargs):
            observations.append(kwargs.get("owned_output_root"))
            return self.fake_facts(source, build)

        with mock.patch.object(RUNNER, "collect_provenance", side_effect=collect):
            result = RUNNER.run_workflow(
                [
                    "--source-dir",
                    str(source),
                    "--build-dir",
                    str(build),
                    "--out-root",
                    str(output),
                    "--warmup",
                    "0",
                    "--repeat",
                    "1",
                ],
                command_runner=self.successful_command_runner(
                    self.benchmark_summary()
                ),
            )
        self.assertEqual(result, 0)
        self.assertIsNone(observations[0])
        self.assertEqual(Path(observations[1]), output.resolve())

    def test_postbuild_unknown_cmake_fails_manifest_before_ctest(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        initial = self.fake_facts(source, build)
        initial["environment"]["controlled_host_id"] = "controlled-01"
        initial["environment"]["physical_core_count"] = 16
        refreshed = json.loads(json.dumps(initial))
        refreshed["toolchain"]["cmake_version"] = "unknown"
        input_facts = {
            "case": "windhub",
            "materialized": True,
            "tracked": True,
            "matches_head_lfs": True,
            "sha256": "b" * 64,
            "size_bytes": 123,
            "repository_relative_path": RUNNER.CANONICAL_WINDHUB_REPOSITORY_PATH,
        }
        with mock.patch.object(
            RUNNER, "collect_provenance", side_effect=[initial, refreshed]
        ), mock.patch.object(RUNNER, "_input_provenance", return_value=input_facts):
            result = RUNNER.run_workflow(
                [
                    "--source-dir", str(source),
                    "--build-dir", str(build),
                    "--out-root", str(output),
                    "--case", "windhub",
                    "--input", str(self.root / "unused.inp"),
                    "--threads-list", "1,2,4,8,16",
                    "--evidence-level", "formal",
                    "--report-intent", "delivery",
                    "--controlled-host-id", "controlled-01",
                ],
                command_runner=self.successful_command_runner(self.benchmark_summary()),
            )
        self.assertEqual(result, 1)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "FAIL")
        self.assertEqual([task["name"] for task in manifest["tasks"]], ["configure", "build"])
        self.assertIn("CMake", manifest["blockers"][0])
        self.assertIsNotNone(manifest["ended_at_utc"])
        self.assertFalse(list(output.glob(".run_manifest.json.*.tmp")))

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
        self.assertEqual(manifest["source"]["demo_version"], "0.2.0")
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

    def test_post_build_source_drift_fails_and_preserves_start_source_facts(self) -> None:
        source, build = self.make_fake_source()
        output = self.root / "evidence"
        initial = self.formal_facts(source, build)
        refreshed = json.loads(json.dumps(initial))
        refreshed["source"]["source_dirty_at_start"] = True
        refreshed["source"]["commit_sha"] = "b" * 40
        refreshed["source"]["demo_version"] = "9.9.9"
        refreshed["toolchain"]["compiler"] = "Clang 19"
        with mock.patch.object(
            RUNNER, "collect_provenance", side_effect=[initial, refreshed]
        ), mock.patch.object(
            RUNNER, "_input_provenance", return_value=self.formal_input_facts()
        ):
            result = RUNNER.run_workflow(
                self.formal_arguments(source, build, output),
                command_runner=self.successful_command_runner(self.formal_summary()),
            )
        self.assertEqual(result, 1)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["commit_sha"], "a" * 40)
        self.assertFalse(manifest["source"]["source_dirty_at_start"])
        self.assertEqual(manifest["source"]["demo_version"], "0.2.0")
        self.assertEqual(manifest["toolchain"]["compiler"], "Clang 19")
        self.assertEqual(manifest["status"], "FAIL")
        self.assertEqual(manifest["identity_checks"][0]["phase"], "after-build")
        self.assertEqual(manifest["identity_checks"][0]["status"], "FAIL")

    def test_formal_source_drift_fails_at_each_identity_phase(self) -> None:
        phase_names = ("after-build", "before-benchmark", "after-benchmark")
        for phase_index, phase_name in enumerate(phase_names, start=1):
            with self.subTest(phase=phase_name):
                case_root = self.root / phase_name
                case_root.mkdir()
                original_root = self.root
                self.root = case_root
                try:
                    source, build = self.make_fake_source()
                    output = self.root / "evidence"
                    initial = self.formal_facts(source, build)
                    observations = [json.loads(json.dumps(initial)) for _ in range(4)]
                    observations[phase_index]["source"]["branch"] = "drifted-branch"
                    with mock.patch.object(
                        RUNNER, "collect_provenance", side_effect=observations
                    ), mock.patch.object(
                        RUNNER,
                        "_input_provenance",
                        return_value=self.formal_input_facts(),
                    ):
                        result = RUNNER.run_workflow(
                            self.formal_arguments(source, build, output),
                            command_runner=self.successful_command_runner(
                                self.formal_summary()
                            ),
                        )
                    self.assertEqual(result, 1)
                    manifest = json.loads(
                        (output / "run_manifest.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(manifest["identity_checks"][-1]["phase"], phase_name)
                    self.assertEqual(manifest["identity_checks"][-1]["status"], "FAIL")
                finally:
                    self.root = original_root

    def test_formal_input_and_lfs_drift_fail_at_each_identity_phase(self) -> None:
        phase_names = ("after-build", "before-benchmark", "after-benchmark")
        drift_fields = (
            ("size_bytes", 76111746),
            ("sha256", "c" * 64),
            ("head_lfs_size_bytes", 76111746),
            ("head_lfs_oid_sha256", "c" * 64),
        )
        for phase_index, phase_name in enumerate(phase_names, start=1):
            for field, value in drift_fields:
                with self.subTest(phase=phase_name, field=field):
                    case_root = self.root / f"{phase_name}-{field}"
                    case_root.mkdir()
                    original_root = self.root
                    self.root = case_root
                    try:
                        source, build = self.make_fake_source()
                        output = self.root / "evidence"
                        initial_facts = self.formal_facts(source, build)
                        inputs = [self.formal_input_facts() for _ in range(4)]
                        inputs[phase_index][field] = value
                        with mock.patch.object(
                            RUNNER, "collect_provenance", return_value=initial_facts
                        ), mock.patch.object(
                            RUNNER, "_input_provenance", side_effect=inputs
                        ):
                            result = RUNNER.run_workflow(
                                self.formal_arguments(source, build, output),
                                command_runner=self.successful_command_runner(
                                    self.formal_summary()
                                ),
                            )
                        self.assertEqual(result, 1)
                        manifest = json.loads(
                            (output / "run_manifest.json").read_text(encoding="utf-8")
                        )
                        self.assertEqual(
                            manifest["identity_checks"][-1]["phase"], phase_name
                        )
                        self.assertEqual(
                            manifest["identity_checks"][-1]["status"], "FAIL"
                        )
                    finally:
                        self.root = original_root

    def test_repository_dirty_check_excludes_only_owned_output_root(self) -> None:
        repository = self.root / "repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        tracked = repository / "tracked.txt"
        tracked.write_text("tracked\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(repository), "add", "tracked.txt"], check=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "user.name=CSC3 Test",
                "-c",
                "user.email=csc3@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            check=True,
        )
        output = repository / "results" / "owned-[evidence]"
        output.mkdir(parents=True)
        (output / "run_manifest.json").write_text("{}\n", encoding="utf-8")

        self.assertEqual(RUNNER._repository_dirty_output(repository, output), "")

        unrelated = repository / "unrelated.txt"
        unrelated.write_text("drift\n", encoding="utf-8")
        dirty = RUNNER._repository_dirty_output(repository, output)
        self.assertIn("unrelated.txt", dirty)
        self.assertNotIn("owned-[evidence]", dirty)

        unrelated.unlink()
        tracked.write_text("tracked drift\n", encoding="utf-8")
        dirty = RUNNER._repository_dirty_output(repository, output)
        self.assertIn("tracked.txt", dirty)
        self.assertNotIn("owned-[evidence]", dirty)

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
                 "--out-root", str(output), "--case", "windhub",
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
