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


class CiBuildContractTests(unittest.TestCase):
    def test_readme_starts_with_the_simple_out_of_source_build(self) -> None:
        text = README_PATH.read_text(encoding="utf-8")
        quick_start = re.search(
            r"## 快速编译.*?```powershell\s+(?P<commands>.*?)```",
            text,
            re.DOTALL,
        )

        self.assertIsNotNone(quick_start)
        assert quick_start is not None
        commands = [
            line.strip()
            for line in quick_start.group("commands").splitlines()
            if line.strip()
        ]
        self.assertEqual(
            commands,
            [
                "cd demos/csc3_symmetric_assembly_demo",
                "mkdir build",
                "cd build",
                "cmake ..",
                "cmake --build .",
            ],
        )
        self.assertIn("build/bin/csc3_demo_app.exe", text)
        self.assertIn("Windows 下不要求统一使用 `make`", text)

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

        for token in (
            "Enter Visual Studio x64 shell, test README quick start, and run full CSC3 suite",
            "Build and test CSC3 demo with MinGW-w64 and Ninja",
            "C:\\msys64\\mingw64\\bin",
            '"-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe"',
            "cmake --preset submission",
        ):
            with self.subTest(token=token):
                self.assertIn(token, workflow)

    def test_windows_ci_executes_the_readme_quick_start(self) -> None:
        workflow = repository_workflow_text(DEMO_ROOT)
        if workflow is None:
            self.assertTrue((DEMO_ROOT / "BUILD_INFO.json").is_file())
            return

        for token in (
            'New-Item -ItemType Directory -Path "build"',
            'Push-Location "build"',
            "cmake ..",
            "cmake --build .",
            'bin\\csc3_demo_app.exe',
        ):
            with self.subTest(token=token):
                self.assertIn(token, workflow)

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
