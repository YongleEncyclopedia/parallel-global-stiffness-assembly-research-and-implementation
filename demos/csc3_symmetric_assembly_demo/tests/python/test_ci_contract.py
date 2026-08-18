from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from delivery_test_context import repository_workflow_text


DEMO_ROOT = Path(__file__).resolve().parents[2]
CMAKE_PATH = DEMO_ROOT / "CMakeLists.txt"
PRESETS_PATH = DEMO_ROOT / "CMakePresets.json"
README_PATH = DEMO_ROOT / "README.md"
TESTS_README_PATH = DEMO_ROOT / "tests" / "README.md"
REQUIREMENTS_PATH = DEMO_ROOT / "requirements-test.txt"
EXPECTED_TESTS_PATH = DEMO_ROOT / "tests" / "ctest" / "expected-ci-tests.txt"
EXPECTED_CPP_TESTS_PATH = DEMO_ROOT / "tests" / "ctest" / "expected-cpp-tests.txt"
EXTERNAL_CONSUMER_ROOT = DEMO_ROOT / "tests" / "external_consumer"

EXPECTED_CI_TESTS = [
    "Csc3DemoTests",
    "Csc3DemoConsumer",
    "Csc3DemoCorrectness",
    "Csc3DemoBenchmarkTiming",
    "Csc3DemoBenchmarkEngine",
    "Csc3DemoBenchmarkIo",
    "Csc3DemoInpCase",
    "Csc3DemoWindHubBenchmark",
    "Csc3DemoPythonTests",
    "Csc3DemoAtomicContention",
]
EXPECTED_CPP_TESTS = [
    name for name in EXPECTED_CI_TESTS if name != "Csc3DemoPythonTests"
]
README_QUICK_COMMANDS = [
    "cd demos/csc3_symmetric_assembly_demo",
    "mkdir build",
    "cd build",
    "cmake ..",
    "cmake --build .",
]
README_MINGW_COMMANDS = [
    '$env:Path = "C:\\msys64\\mingw64\\bin;$env:Path"',
    "cd demos/csc3_symmetric_assembly_demo",
    "mkdir build-mingw",
    "cd build-mingw",
    'cmake -G Ninja "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe" ..',
    "cmake --build .",
    ".\\bin\\csc3_demo_app.exe",
]
EXPECTED_DEMO_OUTPUT = "n=3 values=3,-2,5,-1,2"


def _markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
    )
    if match is None:
        raise AssertionError(f"missing Markdown section: {heading}")
    return match.group("body")


def _fenced_block(section: str, language: str, index: int = 0) -> list[str]:
    blocks = re.findall(
        rf"```{re.escape(language)}\s*\n(?P<body>.*?)```",
        section,
        re.DOTALL,
    )
    if len(blocks) <= index:
        raise AssertionError(f"missing {language} fenced block {index}")
    return [line.strip() for line in blocks[index].splitlines() if line.strip()]


def _workflow_step_block(workflow: str, step_name: str) -> str:
    match = re.search(
        rf"(?ms)^      - name: {re.escape(step_name)}\s*$\n"
        rf"(?P<body>.*?)(?=^      - name: |\Z)",
        workflow,
    )
    if match is None:
        raise AssertionError(f"missing workflow step: {step_name}")
    return match.group(0)


def _workflow_run_lines(step_block: str) -> list[str]:
    lines = step_block.splitlines()
    try:
        run_index = next(
            index for index, line in enumerate(lines) if line.strip() == "run: |"
        )
    except StopIteration as error:
        raise AssertionError("workflow step has no multiline run block") from error

    commands: list[str] = []
    for line in lines[run_index + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= 8:
            break
        if line.startswith("          ") and line.strip():
            commands.append(line[10:].rstrip())
    return commands


def _assert_contiguous_subsequence(
    testcase: unittest.TestCase,
    lines: list[str],
    expected: list[str],
) -> None:
    for index in range(len(lines) - len(expected) + 1):
        if lines[index : index + len(expected)] == expected:
            return
    testcase.fail(f"commands are not contiguous and ordered: {expected!r}")


class CiBuildContractTests(unittest.TestCase):
    def test_readme_quick_start_uses_out_of_source_build(self) -> None:
        text = README_PATH.read_text(encoding="utf-8")
        quick_start = _markdown_section(text, "## Windows 快速编译")
        self.assertEqual(_fenced_block(quick_start, "powershell", 0), README_QUICK_COMMANDS)
        self.assertEqual(
            _fenced_block(quick_start, "powershell", 1),
            [".\\bin\\csc3_demo_app.exe"],
        )
        self.assertEqual(_fenced_block(quick_start, "text"), [EXPECTED_DEMO_OUTPUT])
        for token in (
            "CMake 3.21",
            "Visual Studio 2022",
            "使用 C++ 的桌面开发",
            "普通 PowerShell",
            "C:\\src\\pgsa",
            "build/bin",
            "build/lib",
        ):
            with self.subTest(token=token):
                self.assertIn(token, quick_start)

        mingw = _markdown_section(text, "## MinGW-w64")
        self.assertEqual(_fenced_block(mingw, "powershell"), README_MINGW_COMMANDS)
        for package in (
            "mingw-w64-x86_64-gcc",
            "mingw-w64-x86_64-cmake",
            "mingw-w64-x86_64-ninja",
        ):
            with self.subTest(package=package):
                self.assertIn(package, mingw)

    def test_python_test_dependencies_use_the_shared_requirements(self) -> None:
        self.assertTrue(
            REQUIREMENTS_PATH.is_file(),
            "the demo must declare its Python test requirements",
        )
        requirements = [
            line.strip()
            for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(requirements, ["-r requirements-windows-delivery.txt"])

    def test_cmake_requires_python_only_for_python_tests(self) -> None:
        cmake = CMAKE_PATH.read_text(encoding="utf-8")

        self.assertIn("CSC3_DEMO_BUILD_CPP_TESTS", cmake)
        self.assertIn("CSC3_DEMO_BUILD_PYTHON_TESTS", cmake)
        python_guard = cmake.index("if(CSC3_DEMO_BUILD_PYTHON_TESTS)")
        python_lookup = cmake.index(
            "find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)"
        )
        self.assertLess(python_guard, python_lookup)

    def test_cmake_registers_strict_ci_targets(self) -> None:
        cmake = CMAKE_PATH.read_text(encoding="utf-8")

        for token in (
            "find_package(OpenMP REQUIRED COMPONENTS CXX)",
            "CSC3_DEMO_WARNINGS_AS_ERRORS",
            "CSC3_DEMO_ENABLE_SANITIZERS",
            "-fsanitize=address,undefined",
            "CSC3_DEMO_ENABLE_FORMAT_CHECK",
            "csc3_demo_format_check",
            "tests/atomic_contention_tests.cpp",
            "add_test(NAME Csc3DemoAtomicContention",
        ):
            self.assertIn(token, cmake)

        self.assertIn("LABELS \"ci;atomic-contention\"", cmake)
        self.assertIn("TIMEOUT 180", cmake)
        python_tests = re.search(
            r"set_tests_properties\(Csc3DemoPythonTests PROPERTIES(?P<body>.*?)\n\s*\)",
            cmake,
            re.DOTALL,
        )
        self.assertIsNotNone(python_tests)
        assert python_tests is not None
        self.assertIn("TIMEOUT 600", python_tests.group("body"))

    def test_submission_delivery_and_sanitizer_presets_are_strict(self) -> None:
        presets = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        configure = {preset["name"]: preset for preset in presets["configurePresets"]}

        submission = configure["submission"]["cacheVariables"]
        self.assertEqual(submission["CSC3_DEMO_REQUIRE_OPENMP"], "ON")
        self.assertEqual(submission["CSC3_DEMO_WARNINGS_AS_ERRORS"], "ON")
        self.assertEqual(submission["BUILD_TESTING"], "ON")
        self.assertEqual(submission["CSC3_DEMO_BUILD_CPP_TESTS"], "ON")
        self.assertEqual(submission["CSC3_DEMO_BUILD_PYTHON_TESTS"], "OFF")

        delivery = configure["delivery"]["cacheVariables"]
        self.assertEqual(delivery["CSC3_DEMO_REQUIRE_OPENMP"], "ON")
        self.assertEqual(delivery["CSC3_DEMO_WARNINGS_AS_ERRORS"], "ON")
        self.assertEqual(delivery["BUILD_TESTING"], "ON")
        self.assertEqual(delivery["CSC3_DEMO_BUILD_CPP_TESTS"], "ON")
        self.assertEqual(delivery["CSC3_DEMO_BUILD_PYTHON_TESTS"], "ON")

        sanitizers = configure["ci-sanitizers"]["cacheVariables"]
        self.assertEqual(sanitizers["CSC3_DEMO_REQUIRE_OPENMP"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_WARNINGS_AS_ERRORS"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_ENABLE_SANITIZERS"], "ON")
        self.assertEqual(sanitizers["BUILD_TESTING"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_BUILD_CPP_TESTS"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_BUILD_PYTHON_TESTS"], "OFF")

    def test_ci_inventory_is_exact_and_ordered(self) -> None:
        names = [
            line.strip()
            for line in EXPECTED_TESTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(names, EXPECTED_CI_TESTS)
        self.assertEqual(len(names), len(set(names)))

    def test_cpp_inventory_is_exact_and_excludes_python_tests(self) -> None:
        names = [
            line.strip()
            for line in EXPECTED_CPP_TESTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(names, EXPECTED_CPP_TESTS)
        self.assertNotIn("Csc3DemoPythonTests", names)
        self.assertEqual(len(names), len(set(names)))

    def test_cmake_registration_order_matches_ci_inventory(self) -> None:
        cmake = CMAKE_PATH.read_text(encoding="utf-8")
        registered_names = re.findall(
            r"add_test\s*\(\s*NAME\s+([A-Za-z0-9_]+)",
            cmake,
        )

        self.assertEqual(registered_names, EXPECTED_CI_TESTS)

    def test_sanitizer_ci_runs_the_exact_cpp_inventory(self) -> None:
        workflow = repository_workflow_text(DEMO_ROOT)
        if workflow is None:
            self.assertTrue((DEMO_ROOT / "BUILD_INFO.json").is_file())
            return

        self.assertIn(
            "--expected tests/ctest/expected-cpp-tests.txt --label ci",
            workflow,
        )
        self.assertNotIn("-E '^Csc3DemoPythonTests$'", workflow)

    def test_windows_ci_covers_msvc_and_mingw(self) -> None:
        workflow = repository_workflow_text(DEMO_ROOT)
        if workflow is None:
            self.assertTrue((DEMO_ROOT / "BUILD_INFO.json").is_file())
            return

        install_step = _workflow_step_block(
            workflow, "Install MinGW-w64 for CSC3 demo"
        )
        for package in (
            "mingw-w64-x86_64-gcc",
            "mingw-w64-x86_64-cmake",
            "mingw-w64-x86_64-ninja",
        ):
            with self.subTest(package=package):
                self.assertIn(package, install_step)

        mingw_quick_step = _workflow_step_block(
            workflow, "Run CSC3 README MinGW quick start in ordinary PowerShell"
        )
        self.assertIn(
            "working-directory: ${{ runner.temp }}/c3-readme-mingw",
            mingw_quick_step,
        )
        self.assertIn("-NoProfile", mingw_quick_step)
        self.assertNotIn("Enter-VsDevShell", mingw_quick_step)
        self.assertIn("The README PATH entry must not be preloaded", mingw_quick_step)
        mingw_quick_lines = _workflow_run_lines(mingw_quick_step)
        for cache_pattern in (
            '  "generator" = \'^CMAKE_GENERATOR:INTERNAL=Ninja$\'',
            '  "compiler" = \'^CMAKE_CXX_COMPILER:(?:FILEPATH|STRING)=C:/msys64/mingw64/bin/g\\+\\+\\.exe$\'',
            '  "build tool" = \'^CMAKE_MAKE_PROGRAM:FILEPATH=C:/msys64/mingw64/bin/ninja\\.exe$\'',
            '  "CMake" = \'^CMAKE_COMMAND:INTERNAL=C:/msys64/mingw64/bin/cmake\\.exe$\'',
        ):
            with self.subTest(cache_pattern=cache_pattern):
                self.assertIn(cache_pattern, mingw_quick_lines)
        _assert_contiguous_subsequence(
            self,
            mingw_quick_lines,
            README_MINGW_COMMANDS,
        )
        self.assertIn(
            "$demoOutput = .\\bin\\csc3_demo_app.exe",
            mingw_quick_lines,
        )
        self.assertIn(
            f'if (($demoOutput -join "`n").Trim() -cne "{EXPECTED_DEMO_OUTPUT}") {{',
            mingw_quick_lines,
        )
        self.assertIn(
            '  throw "Unexpected CSC3 demo output: $demoOutput"',
            mingw_quick_lines,
        )

        strict_step = _workflow_step_block(
            workflow, "Build and test CSC3 demo with MinGW-w64 and Ninja"
        )
        strict_lines = _workflow_run_lines(strict_step)
        self.assertLess(
            strict_lines.index('$env:Path = "C:\\msys64\\mingw64\\bin;$env:Path"'),
            strict_lines.index(
                'cmake --preset submission -B $buildDir "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe"'
            ),
        )
        self.assertIn("ctest --test-dir $buildDir", strict_step)
        self.assertIn("csc3-demo-mingw-consumer", strict_step)

    def test_windows_ci_executes_the_readme_quick_start(self) -> None:
        workflow = repository_workflow_text(DEMO_ROOT)
        if workflow is None:
            self.assertTrue((DEMO_ROOT / "BUILD_INFO.json").is_file())
            return

        prepare_step = _workflow_step_block(
            workflow, "Prepare clean CSC3 README source copies"
        )
        self.assertIn("git archive --format=zip", prepare_step)
        self.assertIn("c3-readme-msvc", prepare_step)
        self.assertIn("c3-readme-mingw", prepare_step)
        prepare_lines = _workflow_run_lines(prepare_step)
        for check_line in (
            '  $root = Join-Path $env:RUNNER_TEMP $rootName',
            '  if (Test-Path $root) {',
            '  if ((Test-Path (Join-Path $demo "build")) -or',
            '      (Test-Path (Join-Path $demo "build-mingw"))) {',
        ):
            with self.subTest(check_line=check_line):
                self.assertIn(check_line, prepare_lines)

        quick_step_name = "Run CSC3 README MSVC quick start in ordinary PowerShell"
        quick_step = _workflow_step_block(workflow, quick_step_name)
        self.assertIn(
            "working-directory: ${{ runner.temp }}/c3-readme-msvc",
            quick_step,
        )
        self.assertNotIn("working-directory: ${{ github.workspace }}", quick_step)
        self.assertIn("-NoProfile", quick_step)
        self.assertIn("Get-Command cl.exe -ErrorAction SilentlyContinue", quick_step)
        self.assertIn("Unexpected developer-shell variable", quick_step)
        self.assertNotIn("Enter-VsDevShell", quick_step)
        self.assertNotIn("continue-on-error", quick_step)
        self.assertNotRegex(quick_step, r"(?m)^\s*\$env:CMAKE_GENERATOR\s*=")
        self.assertNotRegex(quick_step, r"(?m)^\s*\$env:CMAKE_CXX_COMPILER\s*=")

        readme_quick_start = _markdown_section(
            README_PATH.read_text(encoding="utf-8"),
            "## Windows 快速编译",
        )
        readme_commands = _fenced_block(readme_quick_start, "powershell", 0)
        readme_run_command = _fenced_block(readme_quick_start, "powershell", 1)
        self.assertEqual(len(readme_run_command), 1)
        quick_lines = _workflow_run_lines(quick_step)
        _assert_contiguous_subsequence(
            self,
            quick_lines,
            readme_commands,
        )
        self.assertIn(readme_run_command[0], quick_lines)
        self.assertGreater(
            quick_lines.index(readme_run_command[0]),
            quick_lines.index(readme_commands[-1]),
        )
        self.assertIn('$PSNativeCommandUseErrorActionPreference = $true', quick_step)
        self.assertIn('$demoOutput = .\\bin\\csc3_demo_app.exe', quick_lines)
        self.assertIn(
            f'if (($demoOutput -join "`n").Trim() -cne "{EXPECTED_DEMO_OUTPUT}") {{',
            quick_lines,
        )
        self.assertIn(
            '  throw "Unexpected CSC3 demo output: $demoOutput"',
            quick_lines,
        )
        self.assertLess(
            workflow.index(f"- name: {quick_step_name}"),
            workflow.index("- name: Enter Visual Studio x64 shell"),
        )

    def test_cpp_inventory_has_documented_authoritative_path(self) -> None:
        text = TESTS_README_PATH.read_text(encoding="utf-8")
        self.assertIn("CSC3_DEMO_BUILD_CPP_TESTS", text)
        self.assertIn("tests/ctest/expected-cpp-tests.txt", text)

    def test_subproject_does_not_initialize_parent_testing_state(self) -> None:
        demo_cmake = CMAKE_PATH.read_text(encoding="utf-8")
        consumer_cmake = (EXTERNAL_CONSUMER_ROOT / "CMakeLists.txt").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            demo_cmake,
            r"if\(PROJECT_IS_TOP_LEVEL\)\s+include\(CTest\)\s+endif\(\)",
        )
        parent_include = consumer_cmake.index("include(CTest)")
        parent_snapshot = consumer_cmake.index(
            'set(csc3_demo_parent_build_testing "${BUILD_TESTING}")'
        )
        child_include = consumer_cmake.index("add_subdirectory")
        unchanged_check = consumer_cmake.index(
            'if(NOT BUILD_TESTING STREQUAL csc3_demo_parent_build_testing)'
        )
        self.assertLess(parent_include, parent_snapshot)
        self.assertLess(parent_snapshot, child_include)
        self.assertLess(child_include, unchanged_check)

    def test_external_consumer_is_a_separate_cmake_project(self) -> None:
        cmake = (EXTERNAL_CONSUMER_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        source = (EXTERNAL_CONSUMER_ROOT / "main.cpp").read_text(encoding="utf-8")

        self.assertIn("project(Csc3DemoExternalConsumer", cmake)
        self.assertIn("add_subdirectory", cmake)
        self.assertIn("csc3_demo::csc3_demo", cmake)
        self.assertNotIn("set(BUILD_TESTING", cmake)
        self.assertIn("if(BUILD_TESTING)", cmake)
        self.assertIn("if(TARGET csc3_demo_tests", cmake)
        self.assertIn('#include "csc3_demo/assembly_helper.h"', source)
        self.assertIn("DofCodingInfo", source)
        self.assertIn("HelpInfo", source)
        self.assertIn("helper.Symbolic(csc3, help_info, dof_coding_info)", source)
        self.assertIn("ElementStiffness", source)
        self.assertIn("helper.add(csc3, help_info", source)
        self.assertIn("#pragma omp parallel for", source)
        self.assertNotIn("SymmetricCscAssembler", source)


if __name__ == "__main__":
    unittest.main()
