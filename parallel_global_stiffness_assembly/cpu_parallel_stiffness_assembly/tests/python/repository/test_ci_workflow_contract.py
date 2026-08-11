from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
CPU_PATH = "parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly"
DEMO_PATH = "demos/csc3_symmetric_assembly_demo"
DEMO_ROOT = REPOSITORY_ROOT / DEMO_PATH
JOB_IDS = ("ubuntu", "macos", "windows")
DEMO_REQUIREMENTS_PATH = f"{DEMO_PATH}/requirements-test.txt"
DEMO_INSTALL_COMMAND = "python -m pip install -r requirements-test.txt"
DEMO_INSTALL_COMMAND_PATTERN = (
    rf"(?m)^        run: {re.escape(DEMO_INSTALL_COMMAND)}$"
)
DEMO_INSTALL_DIRECTORY_PATTERN = (
    rf"(?m)^        working-directory: {re.escape(DEMO_PATH)}$"
)
DEMO_CACHE_PATH_PATTERN = (
    r"(?m)^          cache-dependency-path: \|\n"
    r"(?:            \S.*\n)*"
    rf"            {re.escape(DEMO_REQUIREMENTS_PATH)}$"
)


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


def job_steps(workflow: str, job_id: str) -> list[str]:
    return re.split(r"(?m)(?=^      - )", job_block(workflow, job_id))[1:]


def demo_requirements_contract_violations(
    workflow: str,
    job_id: str,
) -> list[str]:
    steps = job_steps(workflow, job_id)
    setup_steps = [
        step for step in steps if "uses: actions/setup-python@v6" in step
    ]
    install_steps = [
        step
        for step in steps
        if re.search(DEMO_INSTALL_COMMAND_PATTERN, step) is not None
    ]
    violations = []

    if (
        len(setup_steps) != 1
        or "          cache: pip\n" not in setup_steps[0]
        or re.search(DEMO_CACHE_PATH_PATTERN, setup_steps[0]) is None
    ):
        violations.append("cache")
    if (
        len(install_steps) != 1
        or re.search(DEMO_INSTALL_DIRECTORY_PATTERN, install_steps[0]) is None
    ):
        violations.append("install")
    return violations


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
        self.assertIn("group: ${{ github.workflow }}-${{ github.ref }}", workflow)
        self.assertNotIn("github.head_ref", workflow)
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
        self.assertEqual(actions.count("actions/upload-artifact@v6"), 4)
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
        for job_id in JOB_IDS:
            setup_steps = [
                step
                for step in job_steps(workflow, job_id)
                if "uses: actions/setup-python@v6" in step
            ]
            self.assertEqual(len(setup_steps), 1)
            self.assertIn(f"{CPU_PATH}/requirements.txt", setup_steps[0])

    def test_every_platform_caches_and_installs_demo_test_requirements(self) -> None:
        workflow = read_workflow()

        for job_id in JOB_IDS:
            with self.subTest(job_id=job_id):
                self.assertEqual(
                    demo_requirements_contract_violations(workflow, job_id),
                    [],
                )

    def test_demo_install_command_and_working_directory_must_share_step(self) -> None:
        workflow = read_workflow()
        original_install_step = f"""\
      - name: Install CSC3 Python test dependencies
        working-directory: {DEMO_PATH}
        run: {DEMO_INSTALL_COMMAND}
"""
        split_install_steps = f"""\
      - name: Enter CSC3 Python test directory
        working-directory: {DEMO_PATH}
        run: python -c "pass"
      - id: install-csc3-python-test-dependencies
        run: {DEMO_INSTALL_COMMAND}
"""

        for job_id in JOB_IDS:
            block = job_block(workflow, job_id)
            mutated_block = block.replace(
                original_install_step,
                split_install_steps,
                1,
            )
            self.assertNotEqual(mutated_block, block)
            mutated_workflow = workflow.replace(block, mutated_block, 1)

            with self.subTest(job_id=job_id):
                self.assertEqual(
                    demo_requirements_contract_violations(
                        mutated_workflow,
                        job_id,
                    ),
                    ["install"],
                )

    def test_demo_ci_contract_is_self_contained_in_bound_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="csc3-demo-ci-contract-"
        ) as temporary:
            temporary_root = Path(temporary)
            unrelated_root = temporary_root / "unrelated"
            unrelated_root.mkdir()
            copied_demo = unrelated_root / "standalone-demo"
            shutil.copytree(
                DEMO_ROOT,
                copied_demo,
                ignore=shutil.ignore_patterns(
                    "build",
                    "build-*",
                    "dist",
                    "__pycache__",
                    "*.pyc",
                ),
            )
            (copied_demo / "BUILD_INFO.json").write_text(
                json.dumps(
                    {
                        "schema_version": "csc3-demo-build-info-v1",
                        "archive_root": copied_demo.name,
                    }
                ),
                encoding="utf-8",
            )

            self.assertFalse((temporary_root / ".github").exists())
            self.assertFalse((copied_demo / "build").exists())
            completed = subprocess.run(
                [sys.executable, "tests/python/test_ci_contract.py", "-v"],
                cwd=copied_demo,
                check=False,
                capture_output=True,
                text=True,
            )

            output = completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, output)
            self.assertIn("Ran 12 tests", output)
            self.assertIn("OK", output)
            self.assertNotIn("skipped", output)

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
            f"{DEMO_PATH}/",
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
        for job_id in JOB_IDS:
            block = job_block(workflow, job_id)
            self.assertIn(f"working-directory: {CPU_PATH}", block)
            self.assertIn("python -m pip install ninja -r requirements.txt", block)

        preset_commands = (
            "cmake --preset cpu-ci",
            "cmake --build --preset cpu-ci --parallel",
            "python scripts/check_ctest_inventory.py --build-dir build/cpu-ci --expected tests/ctest/expected-ci-tests.txt --label ci",
            "ctest --preset cpu-ci --output-on-failure --output-junit ctest.xml",
            "python scripts/check_ctest_junit.py --junit build/cpu-ci/ctest.xml --expected-tests 14",
        )
        for job_id in ("ubuntu", "macos"):
            block = job_block(workflow, job_id)
            for command in preset_commands:
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
        ):
            self.assertIn(token, build_step)

    def test_windows_uses_short_runner_temp_build_directory(self) -> None:
        windows = job_block(read_workflow(), "windows")
        build_step = windows.split(
            "- name: Enter Visual Studio x64 shell, configure, build, and test\n",
            maxsplit=1,
        )[1].split("- name: Upload failure logs\n", maxsplit=1)[0]
        commands = (
            '$buildDir = "$env:RUNNER_TEMP\\pgsa-cpu-ci"',
            "cmake --preset cpu-ci -B $buildDir",
            "cmake --build $buildDir --parallel",
            "python scripts/check_ctest_inventory.py --build-dir $buildDir --expected tests/ctest/expected-ci-tests.txt --label ci",
            "ctest --test-dir $buildDir -L ci --output-on-failure --output-junit ctest.xml",
            "python scripts/check_ctest_junit.py --junit $buildDir/ctest.xml --expected-tests 14",
        )

        for command in commands:
            self.assertIn(command, build_step)
        for stale_command in (
            "cmake --build --preset cpu-ci",
            "--build-dir build/cpu-ci",
            "ctest --preset cpu-ci",
            "--junit build/cpu-ci/ctest.xml",
        ):
            self.assertNotIn(stale_command, build_step)
        self.assertIn("${{ runner.temp }}/pgsa-cpu-ci/", windows)
        for smoke_output in (
            "isolated-backend-thread-sweep-smoke/",
            "isolated-symbolic-memory-smoke/",
        ):
            self.assertIn(f"${{{{ runner.temp }}}}/pgsa-cpu-ci/{smoke_output}", windows)
        self.assertNotIn(f"{CPU_PATH}/build/cpu-ci/", windows)

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

    def test_ubuntu_runs_repository_contract(self) -> None:
        ubuntu = job_block(read_workflow(), "ubuntu")

        self.assertIn(
            "ctest --test-dir build/cpu-ci -L repository --output-on-failure --output-junit repository.xml",
            ubuntu,
        )
        self.assertIn(
            "python scripts/check_ctest_junit.py --junit build/cpu-ci/repository.xml --expected-tests 1",
            ubuntu,
        )
    def test_every_platform_runs_strict_csc3_openmp_contract(self) -> None:
        workflow = read_workflow()
        for job_id in JOB_IDS:
            block = job_block(workflow, job_id)
            for token in (
                f"working-directory: {DEMO_PATH}",
                "OMP_NUM_THREADS: '2'",
                "OMP_THREAD_LIMIT: '2'",
                "OMP_DYNAMIC: 'false'",
                "cmake --preset delivery",
                "cmake --build",
                "scripts/check_ctest_inventory.py",
                "tests/ctest/expected-ci-tests.txt",
                "--label ci",
                "--output-junit",
                "scripts/check_ctest_junit.py",
                "--expected-tests 10",
                "tests/external_consumer",
                "Csc3DemoExternalConsumer",
            ):
                self.assertIn(token, block)
            for forbidden in (
                "CSC3_DEMO_ENABLE_OPENMP=OFF",
                "continue-on-error",
                "|| true",
            ):
                self.assertNotIn(forbidden, block)

    def test_ubuntu_runs_demo_hardening_checks(self) -> None:
        ubuntu = job_block(read_workflow(), "ubuntu")
        for token in (
            "python -m pip install clang-format==22.1.8",
            "csc3_demo_format_check",
            "--repeat until-fail:20",
            "ci-sanitizers",
            "CMAKE_DISABLE_FIND_PACKAGE_OpenMP=ON",
            "OpenMP negative configuration unexpectedly succeeded",
        ):
            self.assertIn(token, ubuntu)

    def test_ubuntu_verifies_internal_package_and_uploads_minimal_source(self) -> None:
        ubuntu = job_block(read_workflow(), "ubuntu")
        internal_step = ubuntu.split(
            "- name: Verify reproducible CSC3 internal package\n", maxsplit=1
        )[1].split(
            "- name: Build reproducible minimal CSC3 source package\n",
            maxsplit=1,
        )[0]
        source_step = ubuntu.split(
            "- name: Build reproducible minimal CSC3 source package\n", maxsplit=1
        )[1].split(
            "- name: Upload minimal CSC3 source package\n",
            maxsplit=1,
        )[0]
        upload_step = ubuntu.split(
            "- name: Upload minimal CSC3 source package\n",
            maxsplit=1,
        )[1].split("- name: Upload failure logs\n", maxsplit=1)[0]

        for token in (
            f"working-directory: {DEMO_PATH}",
            "OMP_NUM_THREADS: '2'",
            "OMP_THREAD_LIMIT: '2'",
            "OMP_DYNAMIC: 'false'",
            "dist/internal-first",
            "dist/internal-second",
            "results/2026-07-13-macos-arm64-local-smoke",
            "reports/2026-07-13-csc3-demo-macos-local-smoke-test-report.zh-CN.md",
            "scripts/create_delivery_package.py",
            "shopt -s nullglob",
            "first_archives=(dist/internal-first/*.zip)",
            "second_archives=(dist/internal-second/*.zip)",
            '${#first_archives[@]} -ne 1',
            '${#second_archives[@]} -ne 1',
            'basename -- "${first_archive}"',
            'basename -- "${second_archive}"',
            "cmp --",
            'python scripts/verify_delivery_package.py "${first_archive}"',
        ):
            self.assertIn(token, internal_step)
        self.assertEqual(internal_step.count("scripts/create_delivery_package.py"), 2)
        self.assertNotIn("git rev-parse --short=12", internal_step)
        self.assertNotIn("csc3-symmetric-assembly-demo-v0.2.0+", internal_step)
        self.assertNotIn("--manifest-only", internal_step)

        create_positions = [
            match.start()
            for match in re.finditer("scripts/create_delivery_package.py", internal_step)
        ]
        cmp_position = internal_step.index('cmp -- "${first_archive}" "${second_archive}"')
        verify_position = internal_step.index(
            'python scripts/verify_delivery_package.py "${first_archive}"'
        )
        self.assertLess(create_positions[0], create_positions[1])
        self.assertLess(create_positions[1], cmp_position)
        self.assertLess(cmp_position, verify_position)

        for token in (
            f"working-directory: {DEMO_PATH}",
            'source_commit="$(git rev-parse HEAD)"',
            'source_name="CSC3对称稀疏组装Demo_源码.zip"',
            "scripts/create_windows_delivery.py create-source",
            "--repository-root ../..",
            '--source-commit "${source_commit}"',
            "dist/source-first",
            "dist/source-second",
            'cmp -- "dist/source-first/${source_name}" "dist/source-second/${source_name}"',
            "scripts/create_windows_delivery.py verify-source",
            "dist/artifact",
        ):
            self.assertIn(token, source_step)
        self.assertEqual(
            source_step.count("scripts/create_windows_delivery.py create-source"),
            2,
        )
        self.assertLess(
            source_step.index("scripts/create_windows_delivery.py verify-source"),
            source_step.index('cp -- "dist/source-first/${source_name}"'),
        )

        for token in (
            "uses: actions/upload-artifact@v6",
            "name: csc3-demo-minimal-source-package",
            f"{DEMO_PATH}/dist/artifact/CSC3对称稀疏组装Demo_源码.zip",
            "if-no-files-found: error",
            "overwrite: true",
        ):
            self.assertIn(token, upload_step)
        self.assertNotIn("if: failure()", upload_step)

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
