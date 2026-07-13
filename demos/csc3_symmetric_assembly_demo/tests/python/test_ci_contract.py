from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
CMAKE_PATH = DEMO_ROOT / "CMakeLists.txt"
PRESETS_PATH = DEMO_ROOT / "CMakePresets.json"
EXPECTED_TESTS_PATH = DEMO_ROOT / "tests" / "ctest" / "expected-ci-tests.txt"
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
    "Csc3DemoBenchmarkRunner",
    "Csc3DemoAtomicContention",
]


class CiBuildContractTests(unittest.TestCase):
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

    def test_delivery_and_sanitizer_presets_are_strict(self) -> None:
        presets = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        configure = {preset["name"]: preset for preset in presets["configurePresets"]}

        delivery = configure["delivery"]["cacheVariables"]
        self.assertEqual(delivery["CSC3_DEMO_REQUIRE_OPENMP"], "ON")
        self.assertEqual(delivery["CSC3_DEMO_WARNINGS_AS_ERRORS"], "ON")
        self.assertEqual(delivery["BUILD_TESTING"], "ON")

        sanitizers = configure["ci-sanitizers"]["cacheVariables"]
        self.assertEqual(sanitizers["CSC3_DEMO_REQUIRE_OPENMP"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_WARNINGS_AS_ERRORS"], "ON")
        self.assertEqual(sanitizers["CSC3_DEMO_ENABLE_SANITIZERS"], "ON")
        self.assertEqual(sanitizers["BUILD_TESTING"], "ON")

    def test_ci_inventory_is_exact_and_ordered(self) -> None:
        names = [
            line.strip()
            for line in EXPECTED_TESTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(names, EXPECTED_CI_TESTS)
        self.assertEqual(len(names), len(set(names)))

    def test_cmake_registration_order_matches_ci_inventory(self) -> None:
        cmake = CMAKE_PATH.read_text(encoding="utf-8")
        registered_names = re.findall(
            r"add_test\s*\(\s*NAME\s+([A-Za-z0-9_]+)",
            cmake,
        )

        self.assertEqual(registered_names, EXPECTED_CI_TESTS)

    def test_external_consumer_is_a_separate_cmake_project(self) -> None:
        cmake = (EXTERNAL_CONSUMER_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        source = (EXTERNAL_CONSUMER_ROOT / "main.cpp").read_text(encoding="utf-8")

        self.assertIn("project(Csc3DemoExternalConsumer", cmake)
        self.assertIn("add_subdirectory", cmake)
        self.assertIn("csc3_demo::csc3_demo", cmake)
        self.assertIn("BUILD_TESTING OFF", cmake)
        self.assertIn('#include "csc3_demo/assembly_helper.h"', source)
        self.assertIn("symbolic_thread_count_used()", source)
        self.assertIn("numeric_thread_count_used()", source)


if __name__ == "__main__":
    unittest.main()
