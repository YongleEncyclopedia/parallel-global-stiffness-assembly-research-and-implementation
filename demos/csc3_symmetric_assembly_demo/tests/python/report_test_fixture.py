#!/usr/bin/env python3
"""Synthetic hash-bound evidence used by report-verifier contract tests."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Iterable


BENCHMARK_SCHEMA_V1 = "csc3-demo-benchmark-v1"
BENCHMARK_SCHEMA_V2 = "csc3-demo-benchmark-v2"

CSV_HEADER_V1 = (
    "schema_version", "case_name", "element_type", "nx", "ny", "nz",
    "node_count", "element_count", "dof_count", "nnz", "thread_count",
    "sample_index", "sample_kind", "input_prepare_ms", "serial_symbolic_ms",
    "serial_numeric_ms", "symbolic_pattern_ms", "symbolic_scatter_ms",
    "symbolic_total_ms", "numeric_reset_ms", "numeric_kernel_ms",
    "numeric_total_ms", "amortized_total_ms", "symbolic_speedup",
    "numeric_speedup", "relative_frobenius_error", "max_absolute_error",
    "matrix_correctness_status", "estimated_persistent_bytes",
    "performance_evidence_level",
)

CSV_HEADER = CSV_HEADER_V1 + (
    "symbolic_plan_matches_serial",
    "numeric_setup_plan_matches_serial",
)

JUNIT_NAMES = (
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

FIXTURE_WINDHUB_SIZE = 76111745
FIXTURE_WINDHUB_SHA256 = (
    "4f3066b7e388ff0abaccb41d9ff5ec5a668e8d6ed008ae0c1061951f836ae0c3"
)


def statistics(value: float, count: int) -> dict[str, object]:
    return {
        "sample_count": count,
        "mean_ms": value,
        "median_ms": value,
        "population_standard_deviation_ms": 0.0,
        "minimum_ms": value,
        "maximum_ms": value,
        "coefficient_of_variation": 0.0,
    }


def validation_case(element_type: str, thread_count: int) -> dict[str, object]:
    tet4 = element_type == "Tet4"
    return {
        "case_name": "cube_tet4_1x1x1" if tet4 else "cube_hex8_1x1x1",
        "element_type": element_type,
        "node_count": 8,
        "element_count": 6 if tet4 else 1,
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


class EvidenceFixture:
    """Materialize a small evidence bundle without invoking the benchmark."""

    def __init__(
        self,
        root: Path,
        *,
        evidence_level: str = "local-smoke",
        report_intent: str = "local-smoke",
        formal_gate_pass: bool = True,
        windhub: bool = False,
        schema_version: str = BENCHMARK_SCHEMA_V2,
    ) -> None:
        self.root = root
        self.evidence_level = evidence_level
        self.report_intent = report_intent
        self.formal_gate_pass = formal_gate_pass
        self.schema_version = schema_version
        self.formal = evidence_level == "formal"
        self.windhub = self.formal or windhub
        self.case = "windhub" if self.windhub else "generated-tet4"
        self.threads = [1, 2, 4, 8, 16] if self.formal else [1, 2]
        self.warmup = 2 if self.formal else 1
        self.repeat = 7 if self.formal else 2
        self.amortization = 1 if self.formal else 2
        self.rows = self._make_rows()
        self.summary = self._make_summary()
        self.manifest = self._make_manifest()
        self.write_all()

    @property
    def manifest_path(self) -> Path:
        return self.root / "run_manifest.json"

    def _candidate_values(self, thread: int) -> tuple[float, float, float, float, float]:
        eligible = thread > 1 and self.formal_gate_pass
        symbolic_total = 5.0 if eligible else 10.0
        numeric_reset = 1.0 if eligible else 2.0
        numeric_kernel = 3.0 if eligible else 6.0
        numeric_total = numeric_reset + numeric_kernel + 0.5
        symbolic_speedup = 10.0 / symbolic_total
        numeric_speedup = 8.0 / (numeric_reset + numeric_kernel)
        return (
            symbolic_total,
            numeric_reset,
            numeric_kernel,
            symbolic_speedup,
            numeric_speedup,
        )

    def _make_rows(self) -> list[dict[str, str]]:
        case_name = "3d-WindTurbineHub.inp" if self.windhub else "cube_tet4_1x1x1"
        rows: list[dict[str, str]] = []
        for thread in self.threads:
            symbolic_total, reset, kernel, symbolic_speedup, numeric_speedup = (
                self._candidate_values(thread)
            )
            numeric_total = reset + kernel + 0.5
            for sample_index in range(self.warmup + self.repeat):
                values = {
                    "schema_version": self.schema_version,
                    "case_name": case_name,
                    "element_type": "Tet4",
                    "nx": "0" if self.windhub else "1",
                    "ny": "0" if self.windhub else "1",
                    "nz": "0" if self.windhub else "1",
                    "node_count": "8",
                    "element_count": "6",
                    "dof_count": "24",
                    "nnz": "219",
                    "thread_count": str(thread),
                    "sample_index": str(sample_index),
                    "sample_kind": "warmup" if sample_index < self.warmup else "measured",
                    "input_prepare_ms": "0.5",
                    "serial_symbolic_ms": "10.0",
                    "serial_numeric_ms": "8.0",
                    "symbolic_pattern_ms": str(symbolic_total * 0.4),
                    "symbolic_scatter_ms": str(symbolic_total * 0.4),
                    "symbolic_total_ms": str(symbolic_total),
                    "numeric_reset_ms": str(reset),
                    "numeric_kernel_ms": str(kernel),
                    "numeric_total_ms": str(numeric_total),
                    "amortized_total_ms": str(
                        symbolic_total / self.amortization + numeric_total
                    ),
                    "symbolic_speedup": str(symbolic_speedup),
                    "numeric_speedup": str(numeric_speedup),
                    "relative_frobenius_error": "1e-15",
                    "max_absolute_error": "1e-14",
                    "matrix_correctness_status": "PASS",
                    "estimated_persistent_bytes": "123456",
                    "performance_evidence_level": self.evidence_level,
                }
                if self.schema_version == BENCHMARK_SCHEMA_V2:
                    values.update(
                        {
                            "symbolic_plan_matches_serial": "true",
                            "numeric_setup_plan_matches_serial": "true",
                        }
                    )
                rows.append(values)
        return rows

    def _make_summary(self) -> dict[str, object]:
        case_name = "3d-WindTurbineHub.inp" if self.windhub else "cube_tet4_1x1x1"
        per_thread = []
        for thread in self.threads:
            symbolic_total, reset, kernel, symbolic_speedup, numeric_speedup = (
                self._candidate_values(thread)
            )
            numeric_total = reset + kernel + 0.5
            row: dict[str, object] = {
                "thread_count": thread,
                "symbolic_thread_count_observed": thread,
                "numeric_thread_count_observed": thread,
                "symbolic_speedup": symbolic_speedup,
                "numeric_speedup": numeric_speedup,
                "symbolic_pattern_ms": statistics(symbolic_total * 0.4, self.repeat),
                "symbolic_scatter_ms": statistics(symbolic_total * 0.4, self.repeat),
                "symbolic_total_ms": statistics(symbolic_total, self.repeat),
                "numeric_reset_ms": statistics(reset, self.repeat),
                "numeric_kernel_ms": statistics(kernel, self.repeat),
                "numeric_algorithm_ms": statistics(reset + kernel, self.repeat),
                "numeric_total_ms": statistics(numeric_total, self.repeat),
                "amortized_total_ms": statistics(
                    symbolic_total / self.amortization + numeric_total,
                    self.repeat,
                ),
            }
            if self.schema_version == BENCHMARK_SCHEMA_V2:
                row.update(
                    {
                        "symbolic_plan_check_count": self.warmup + self.repeat,
                        "symbolic_plan_match_count": self.warmup + self.repeat,
                        "numeric_setup_plan_matches_serial": True,
                        "scatter_status": "PASS",
                    }
                )
            per_thread.append(row)

        if not self.windhub:
            gate = {
                "status": "NOT_APPLICABLE_GENERATED_CASE",
                "applicable": False,
                "performance_requirements_met": False,
                "numeric_requirement_met": False,
                "symbolic_requirement_met": False,
                "numeric_thread_count": 0,
                "symbolic_thread_count": 0,
            }
        else:
            requirements_met = self.formal and self.formal_gate_pass
            gate = {
                "status": (
                    ("PASS" if self.formal_gate_pass else "FAIL")
                    if self.formal
                    else (
                        "NON_FORMAL_CI_SMOKE"
                        if self.evidence_level == "ci-smoke"
                        else "NON_FORMAL_LOCAL_SMOKE"
                    )
                ),
                "applicable": True,
                "performance_requirements_met": requirements_met,
                "numeric_requirement_met": self.formal_gate_pass,
                "symbolic_requirement_met": self.formal_gate_pass,
                "numeric_thread_count": 2 if self.formal_gate_pass else 0,
                "symbolic_thread_count": 2 if self.formal_gate_pass else 0,
            }
        gate.update(
            {
                "numeric_speedup_threshold": 1.5,
                "symbolic_speedup_threshold": 1.0,
                "maximum_coefficient_of_variation": 0.05,
            }
        )
        if self.schema_version == BENCHMARK_SCHEMA_V2:
            gate.update(
                {
                    "serial_symbolic_cv_requirement_met": self.windhub,
                    "serial_numeric_cv_requirement_met": self.windhub,
                    "scatter_requirement_met": self.windhub,
                    "formal_requirements_met": (
                        self.formal and self.formal_gate_pass
                    ),
                }
            )
        selected_validation_thread = 2
        summary = {
            "schema_version": self.schema_version,
            "configuration": {
                "case": self.case,
                "nx": 0 if self.windhub else 1,
                "ny": 0 if self.windhub else 1,
                "nz": 0 if self.windhub else 1,
                "thread_counts": list(self.threads),
                "warmup_count": self.warmup,
                "repeat_count": self.repeat,
                "amortization_count": self.amortization,
                "performance_evidence_level": self.evidence_level,
            },
            "case_sizes": {
                "case_name": case_name,
                "element_type": "Tet4",
                "node_count": 8,
                "element_count": 6,
                "dof_count": 24,
                "nnz": 219,
            },
            "input_prepare_ms": 0.5,
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
                validation_case("Tet4", selected_validation_thread),
                validation_case("Hex8", selected_validation_thread),
            ],
            "serial_measured_statistics": {
                "symbolic_total_ms": statistics(10.0, self.repeat),
                "numeric_total_ms": statistics(8.0, self.repeat),
            },
            "per_thread_measured_statistics": per_thread,
            "estimated_persistent_bytes": 123456,
            "estimated_persistent_memory_kind": "owned_vector_payload_bytes_not_rss",
            "numeric_speedup_basis": "serial_reset_plus_kernel_over_atomic_reset_plus_kernel",
            "performance_evidence_level": self.evidence_level,
            "performance_gate": gate,
            "performance_gate_status": gate["status"],
        }
        if self.schema_version == BENCHMARK_SCHEMA_V2:
            summary.update(
                {
                    "raw_samples": [
                        {
                            "thread_count": int(row["thread_count"]),
                            "sample_index": int(row["sample_index"]),
                            "sample_kind": row["sample_kind"],
                            "symbolic_plan_matches_serial": True,
                            "numeric_setup_plan_matches_serial": True,
                        }
                        for row in self.rows
                    ],
                    "scatter_correctness": {
                        "symbolic_plan_check_count": len(self.rows),
                        "symbolic_plan_match_count": len(self.rows),
                        "numeric_setup_plan_check_count": len(self.threads),
                        "numeric_setup_plan_match_count": len(self.threads),
                        "status": "PASS",
                    },
                }
            )
        return summary

    def _make_manifest(self) -> dict[str, object]:
        if self.windhub:
            input_facts: dict[str, object] = {
                "case": "windhub",
                "path": "/controlled/input/3d-WindTurbineHub.inp",
                "size_bytes": FIXTURE_WINDHUB_SIZE,
                "sha256": FIXTURE_WINDHUB_SHA256,
                "materialized": True,
                "tracked": True,
                "matches_head_lfs": True,
                "repository_relative_path": "examples/3d-WindTurbineHub.inp",
                "head_lfs_oid_sha256": FIXTURE_WINDHUB_SHA256,
                "head_lfs_size_bytes": FIXTURE_WINDHUB_SIZE,
            }
        else:
            input_facts = {
                "case": "generated-tet4",
                "grid": {"nx": 1, "ny": 1, "nz": 1},
            }
        if self.formal and self.report_intent != "delivery":
            status = "BLOCKED"
        elif self.formal:
            status = "PASS" if self.formal_gate_pass else "FAIL"
        else:
            status = "BLOCKED" if self.report_intent == "delivery" else "LOCAL_SMOKE"
        # The synthetic manifest claims Darwin or Linux provenance, so its recorded
        # command paths must keep that POSIX flavour even when the contract tests run
        # on a Windows host.  Files used by the test itself still live under
        # ``self.root``; these paths are provenance values only and are never opened.
        provenance_root = PurePosixPath("/controlled/csc3-demo")
        source_directory = provenance_root / "source"
        build_directory = provenance_root / "build" / "delivery"
        python_executable = provenance_root / "venv" / "bin" / "python"
        commands = {
            "configure": [
                "cmake",
                "--preset",
                "delivery",
                "-B",
                str(build_directory),
                "-DPython3_EXECUTABLE:FILEPATH=" + str(python_executable),
            ],
            "build": [
                "cmake",
                "--build",
                str(build_directory),
                "--config",
                "Release",
            ],
            "ctest": [
                "ctest",
                "--test-dir",
                str(build_directory),
                "-C",
                "Release",
                "--label-regex",
                "ci",
                "--output-on-failure",
                "--no-tests=error",
                "--output-junit",
                str(provenance_root / "ctest.xml"),
            ],
            "benchmark": [
                str(build_directory / "bin" / "csc3_demo_benchmark"),
                "--case",
                self.case,
                "--threads-list",
                ",".join(str(value) for value in self.threads),
                "--warmup",
                str(self.warmup),
                "--repeat",
                str(self.repeat),
                "--amortization-count",
                str(self.amortization),
                "--evidence-level",
                self.evidence_level,
                "--samples-csv",
                str(provenance_root / "benchmark_samples.csv"),
                "--summary-json",
                str(provenance_root / "benchmark_summary.json"),
            ],
        }
        if self.windhub:
            commands["benchmark"].extend(["--input", str(input_facts["path"])])
        else:
            grid = input_facts["grid"]
            commands["benchmark"].extend(
                [
                    "--nx",
                    str(grid["nx"]),
                    "--ny",
                    str(grid["ny"]),
                    "--nz",
                    str(grid["nz"]),
                ]
            )
        binding_environment = {
            "OMP_DYNAMIC": "false",
            "OMP_PROC_BIND": "close",
            "OMP_PLACES": "cores",
        }
        tasks = [
            {
                "name": name,
                "command": list(commands[name]),
                "cwd": str(source_directory),
                "environment": dict(binding_environment),
                "status": "PASS",
                "returncode": 0,
                "exit_code": 0,
                "error": None,
            }
            for name in ("configure", "build", "ctest", "benchmark")
        ]
        if self.formal and not self.formal_gate_pass:
            tasks[-1].update(
                {
                    "status": "FAIL",
                    "returncode": 17,
                    "exit_code": 17,
                    "error": "formal performance gate failed",
                }
            )
        source_facts = {
            "commit_sha": "a" * 40,
            "branch": "codex/issue-44-csc3-evidence-report",
            "source_dirty_at_start": False,
            "demo_version": "0.2.0",
        }
        identity_checks = []
        if self.formal:
            identity_checks = [
                {
                    "phase": phase,
                    "status": "PASS",
                    "source": dict(source_facts),
                    "input": json.loads(json.dumps(input_facts)),
                    "errors": [],
                }
                for phase in ("after-build", "before-benchmark", "after-benchmark")
            ]
        return {
            "schema_version": "csc3-demo-benchmark-run-v1",
            "run_id": "run-20260713T000000Z-aaaaaaaaaaaa",
            "report_intent": self.report_intent,
            "status": status,
            "evidence_level": self.evidence_level,
            "source": source_facts,
            "environment": {
                "system": "Linux" if self.formal else "Darwin",
                "architecture": "x86_64" if self.formal else "arm64",
                "hostname": "controlled-host" if self.formal else "local-host",
                "cpu_vendor": "GenuineIntel" if self.formal else "Apple",
                "cpu_model": "Intel Xeon" if self.formal else "Apple M4",
                "physical_core_count": 16 if self.formal else 10,
                "logical_core_count": 32 if self.formal else 10,
                "total_memory_bytes": 64000000000,
                "python_version": "3.13.5",
                "controlled_host_id": "intel-linux-01" if self.formal else None,
            },
            "toolchain": {
                "cmake_version": "3.31.6",
                "compiler": "GNU 14.2.0",
                "compiler_id": "GNU",
                "compiler_version": "14.2.0",
                "build_directory": str(build_directory),
                "runner_python_executable": str(python_executable),
                "cmake_python_executable": str(python_executable),
                "openmp": {"found": True, "require_openmp": True, "flags": "-fopenmp"},
            },
            "input": input_facts,
            "benchmark": {
                "warmup_count": self.warmup,
                "repeat_count": self.repeat,
                "amortization_count": self.amortization,
                "requested_thread_counts": list(self.threads),
                "observed_thread_counts": list(self.threads),
            },
            "commands": commands,
            "binding_environment": binding_environment,
            "tasks": tasks,
            "identity_checks": identity_checks,
            "blockers": [] if status in {"PASS", "FAIL"} else ["formal evidence unavailable"],
            "artifacts": [],
            "started_at_utc": "2026-07-13T00:00:00Z",
            "ended_at_utc": "2026-07-13T00:00:01Z",
        }

    def write_all(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.write_csv()
        self.write_summary()
        self.write_junit()
        (self.root / "summary.md").write_text(
            "# fixture summary\n", encoding="utf-8", newline="\n"
        )
        self.refresh_artifacts()

    def write_csv(self, header: Iterable[str] | None = None) -> None:
        with (self.root / "benchmark_samples.csv").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.writer(stream, lineterminator="\n")
            columns = tuple(
                header
                if header is not None
                else (
                    CSV_HEADER
                    if self.schema_version == BENCHMARK_SCHEMA_V2
                    else CSV_HEADER_V1
                )
            )
            writer.writerow(columns)
            for row in self.rows:
                writer.writerow([row.get(column, "") for column in columns])

    def write_summary(self) -> None:
        (self.root / "benchmark_summary.json").write_text(
            json.dumps(self.summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def write_junit(
        self,
        *,
        names: Iterable[str] = JUNIT_NAMES,
        root_counts: dict[str, str] | None = None,
        testcase_attributes: dict[int, dict[str, str]] | None = None,
        testcase_children: dict[int, str] | None = None,
    ) -> None:
        names = tuple(names)
        counts = {
            "tests": str(len(names)),
            "failures": "0",
            "errors": "0",
            "skipped": "0",
            "disabled": "0",
        }
        counts.update(root_counts or {})
        attributes_text = " ".join(
            f'{key}="{value}"' for key, value in counts.items()
        )
        cases = []
        for index, name in enumerate(names):
            attributes = {"name": name}
            attributes.update((testcase_attributes or {}).get(index, {}))
            case_attributes = " ".join(
                f'{key}="{value}"' for key, value in attributes.items()
            )
            child = (testcase_children or {}).get(index)
            cases.append(
                f"<testcase {case_attributes}>{child}</testcase>"
                if child is not None
                else f"<testcase {case_attributes}/>"
            )
        (self.root / "ctest.xml").write_text(
            f"<testsuites {attributes_text}>" + "".join(cases) + "</testsuites>\n",
            encoding="utf-8",
            newline="\n",
        )

    def refresh_artifacts(self, paths: Iterable[str] | None = None) -> None:
        artifact_paths = tuple(paths or (
            "ctest.xml",
            "benchmark_samples.csv",
            "benchmark_summary.json",
            "summary.md",
        ))
        artifacts = []
        for relative in artifact_paths:
            path = self.root / relative
            content = path.read_bytes()
            artifacts.append(
                {
                    "path": relative,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
        self.manifest["artifacts"] = artifacts
        self.write_manifest()

    def write_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
