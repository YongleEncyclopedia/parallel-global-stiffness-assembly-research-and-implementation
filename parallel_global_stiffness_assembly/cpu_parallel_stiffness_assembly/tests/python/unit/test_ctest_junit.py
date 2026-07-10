from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


CPU_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = CPU_ROOT / "scripts" / "check_ctest_junit.py"


def load_checker() -> ModuleType:
    if not CHECKER_PATH.is_file():
        raise AssertionError(f"missing JUnit checker: {CHECKER_PATH}")
    spec = importlib.util.spec_from_file_location("check_ctest_junit", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load JUnit checker: {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CTestJUnitTests(unittest.TestCase):
    def write_junit(self, document: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "ctest.xml"
        path.write_text(document, encoding="utf-8")
        return path

    def run_checker(self, document: str, expected_tests: int) -> tuple[int, str]:
        checker = load_checker()
        path = self.write_junit(document)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = checker.main(
                [
                    "--junit",
                    str(path),
                    "--expected-tests",
                    str(expected_tests),
                ]
            )
        return result, stderr.getvalue()

    def test_single_testsuite_is_accepted_when_exact_count_matches(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite tests="2" failures="0" errors="0" skipped="0">
  <testcase name="VerifyA" status="run" />
  <testcase name="VerifyB" status="run" />
</testsuite>
""",
            expected_tests=2,
        )

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")

    def test_nested_testsuites_count_all_testcases(self) -> None:
        checker = load_checker()
        path = self.write_junit(
            """\
<testsuites>
  <testsuite name="first">
    <testcase name="VerifyA" status="run" />
  </testsuite>
  <testsuites name="nested">
    <testsuite name="second">
      <testcase name="VerifyB" status="run" />
      <testcase name="VerifyC" status="run" />
    </testsuite>
  </testsuites>
</testsuites>
"""
        )

        summary = checker.read_junit_summary(path)

        self.assertEqual(summary.tests, 3)

    def test_exact_count_mismatch_is_rejected(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite>
  <testcase name="VerifyA" status="run" />
</testsuite>
""",
            expected_tests=2,
        )

        self.assertEqual(result, 1)
        self.assertIn("expected 2 tests, found 1", stderr)

    def test_failure_is_rejected(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite>
  <testcase name="VerifyA" status="failed"><failure>failed</failure></testcase>
</testsuite>
""",
            expected_tests=1,
        )

        self.assertEqual(result, 1)
        self.assertIn("failures: 1", stderr)

    def test_error_is_rejected(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite>
  <testcase name="VerifyA" status="failed"><error>crashed</error></testcase>
</testsuite>
""",
            expected_tests=1,
        )

        self.assertEqual(result, 1)
        self.assertIn("errors: 1", stderr)

    def test_skipped_test_is_rejected(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite>
  <testcase name="VerifyA" status="notrun"><skipped>disabled</skipped></testcase>
</testsuite>
""",
            expected_tests=1,
        )

        self.assertEqual(result, 1)
        self.assertIn("skipped: 1", stderr)

    def test_notrun_status_is_rejected_without_skipped_element(self) -> None:
        result, stderr = self.run_checker(
            """\
<testsuite>
  <testcase name="VerifyA" status="notrun" />
</testsuite>
""",
            expected_tests=1,
        )

        self.assertEqual(result, 1)
        self.assertIn("not-run: 1", stderr)


if __name__ == "__main__":
    unittest.main()
