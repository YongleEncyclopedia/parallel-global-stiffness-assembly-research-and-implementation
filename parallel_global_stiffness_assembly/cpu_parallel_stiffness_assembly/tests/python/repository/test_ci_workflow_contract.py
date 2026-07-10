from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
CPU_PATH = "parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly"
JOB_IDS = ("ubuntu", "macos", "windows")


def read_workflow() -> str:
    if not WORKFLOW_PATH.is_file():
        raise AssertionError(f"missing CI workflow: {WORKFLOW_PATH}")
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def job_block(workflow: str, job_id: str) -> str:
    marker = f"  {job_id}:\n"
    try:
        start = workflow.index(marker)
    except ValueError as error:
        raise AssertionError(f"missing CI job: {job_id}") from error
    sibling = re.search(r"(?m)^  [a-z0-9_-]+:\n", workflow[start + len(marker) :])
    if sibling is None:
        return workflow[start:]
    return workflow[start : start + len(marker) + sibling.start()]


class CiWorkflowContractTests(unittest.TestCase):
    def test_triggers_permissions_and_concurrency_are_safe(self) -> None:
        workflow = read_workflow()

        self.assertIn(
            """\
on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:
""",
            workflow,
        )
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertIn("group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        for forbidden in ("pull_request_target", "paths:", "paths-ignore:"):
            self.assertNotIn(forbidden, workflow)

    def test_jobs_have_exact_stable_names_and_limits(self) -> None:
        workflow = read_workflow()
        jobs_text = workflow.split("\njobs:\n", maxsplit=1)[1]

        self.assertEqual(
            re.findall(r"(?m)^  ([a-z0-9_-]+):$", jobs_text), list(JOB_IDS)
        )
        self.assertEqual(
            re.findall(r"(?m)^    name: (CI / .+)$", jobs_text),
            ["CI / Ubuntu", "CI / macOS", "CI / Windows"],
        )
        for job_id in JOB_IDS:
            self.assertIn("timeout-minutes: 30", job_block(workflow, job_id))
        self.assertNotIn("continue-on-error", workflow)

    def test_only_approved_action_majors_and_python_are_used(self) -> None:
        workflow = read_workflow()
        actions = re.findall(r"uses:\s+(\S+)", workflow)

        self.assertEqual(actions.count("actions/checkout@v6"), 3)
        self.assertEqual(actions.count("actions/setup-python@v6"), 3)
        self.assertEqual(actions.count("actions/upload-artifact@v6"), 3)
        self.assertEqual(
            set(actions),
            {
                "actions/checkout@v6",
                "actions/setup-python@v6",
                "actions/upload-artifact@v6",
            },
        )
        self.assertEqual(workflow.count("python-version: '3.11'"), 3)
        self.assertEqual(workflow.count("cache: pip"), 3)
        self.assertEqual(
            workflow.count(f"cache-dependency-path: {CPU_PATH}/requirements.txt"), 3
        )

    def test_linux_checkout_is_full_and_other_checkouts_are_sparse(self) -> None:
        workflow = read_workflow()
        ubuntu = job_block(workflow, "ubuntu")
        macos = job_block(workflow, "macos")
        windows = job_block(workflow, "windows")

        self.assertIn("fetch-depth: 0", ubuntu)
        self.assertIn("lfs: false", ubuntu)
        self.assertNotIn("sparse-checkout:", ubuntu)
        sparse_paths = (
            ".github/",
            f"{CPU_PATH}/CMakeLists.txt",
            f"{CPU_PATH}/CMakePresets.json",
            f"{CPU_PATH}/cmake/",
            f"{CPU_PATH}/requirements.txt",
            f"{CPU_PATH}/apps/",
            f"{CPU_PATH}/include/",
            f"{CPU_PATH}/src/",
            f"{CPU_PATH}/tests/",
            f"{CPU_PATH}/scripts/",
            f"{CPU_PATH}/examples/",
        )
        for sparse_job in (macos, windows):
            self.assertIn("sparse-checkout: |", sparse_job)
            self.assertIn("sparse-checkout-cone-mode: false", sparse_job)
            for path in sparse_paths:
                self.assertIn(path, sparse_job)

        self.assertEqual(workflow.count("lfs: false"), 1)
        for forbidden in (
            "git lfs pull",
            "lfs: true",
            f"{CPU_PATH}/results/",
            f"{CPU_PATH}/reports/",
            "WindHub",
            f"{CPU_PATH}/legacy_gpu/",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_every_platform_runs_the_common_cpu_contract(self) -> None:
        workflow = read_workflow()
        commands = (
            "python -m pip install ninja -r requirements.txt",
            "cmake --preset cpu-ci",
            "cmake --build --preset cpu-ci --parallel",
            "python scripts/check_ctest_inventory.py --build-dir build/cpu-ci --expected tests/ctest/expected-ci-tests.txt --label ci",
            "ctest --preset cpu-ci --output-on-failure --output-junit ctest.xml",
            "python scripts/check_ctest_junit.py --junit build/cpu-ci/ctest.xml --expected-tests 14",
        )
        for job_id in JOB_IDS:
            block = job_block(workflow, job_id)
            self.assertIn(f"working-directory: {CPU_PATH}", block)
            for command in commands:
                self.assertIn(command, block)

    def test_platform_specific_setup_is_present(self) -> None:
        workflow = read_workflow()
        ubuntu = job_block(workflow, "ubuntu")
        macos = job_block(workflow, "macos")
        windows = job_block(workflow, "windows")

        self.assertIn("runs-on: ubuntu-latest", ubuntu)
        self.assertNotIn("brew install libomp", ubuntu)
        self.assertIn("runs-on: macos-latest", macos)
        self.assertIn("brew install libomp", macos)
        self.assertIn('OpenMP_ROOT=$(brew --prefix libomp)', macos)
        self.assertIn("GITHUB_ENV", macos)

        self.assertIn("runs-on: windows-latest", windows)
        build_step = windows.split(
            "- name: Enter Visual Studio x64 shell, configure, build, and test\n",
            maxsplit=1,
        )[1].split("- name: Upload failure logs\n", maxsplit=1)[0]
        for token in (
            "shell: pwsh",
            "vswhere.exe",
            "Microsoft.VisualStudio.DevShell.dll",
            "Import-Module",
            "Enter-VsDevShell",
            "-arch=x64 -host_arch=x64",
            "cmake --preset cpu-ci",
            "cmake --build --preset cpu-ci --parallel",
            "check_ctest_inventory.py",
            "ctest --preset cpu-ci",
        ):
            self.assertIn(token, build_step)

    def test_windows_enables_git_long_paths_before_checkout(self) -> None:
        windows = job_block(read_workflow(), "windows")
        longpaths_step = """\
      - name: Enable Git long paths
        shell: pwsh
        working-directory: ${{ github.workspace }}
        run: git config --global core.longpaths true
"""
        checkout_action = "uses: actions/checkout@v6"

        self.assertIn(longpaths_step, windows)
        self.assertLess(windows.index(longpaths_step), windows.index(checkout_action))

    def test_ubuntu_runs_repository_contract_and_csc3_demo(self) -> None:
        ubuntu = job_block(read_workflow(), "ubuntu")

        self.assertIn(
            "ctest --test-dir build/cpu-ci -L repository --output-on-failure --output-junit repository.xml",
            ubuntu,
        )
        self.assertIn(
            "python scripts/check_ctest_junit.py --junit build/cpu-ci/repository.xml --expected-tests 1",
            ubuntu,
        )
        for token in (
            "../../demos/csc3_symmetric_assembly_demo",
            "-G Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCSC3_DEMO_ENABLE_OPENMP=OFF",
            "-DCSC3_DEMO_ENABLE_EIGEN=OFF",
            "cmake --build build/csc3-demo --parallel",
            "ctest --test-dir build/csc3-demo --output-on-failure",
        ):
            self.assertIn(token, ubuntu)

    def test_failure_artifacts_are_scoped_and_no_forbidden_inputs_exist(self) -> None:
        workflow = read_workflow()
        artifact_names = {
            "ubuntu": "ci-ubuntu-failure-logs",
            "macos": "ci-macos-failure-logs",
            "windows": "ci-windows-failure-logs",
        }

        for job_id, artifact_name in artifact_names.items():
            block = job_block(workflow, job_id)
            self.assertIn("if: failure()", block)
            self.assertIn("uses: actions/upload-artifact@v6", block)
            self.assertIn(f"name: {artifact_name}", block)
            self.assertIn("CMakeFiles/CMakeConfigureLog.yaml", block)
            self.assertIn("Testing/Temporary/", block)
            self.assertIn("ctest.xml", block)
            self.assertIn("if-no-files-found: ignore", block)

        for forbidden in (
            "secrets.",
            "${{ secrets",
            "performance-threshold",
            "timing-assertion",
            "solver-license",
        ):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
