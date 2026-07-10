from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CPU_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = CPU_ROOT / "scripts" / "check_markdown_links.py"


class MarkdownLinkCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.repository_root = Path(self._temporary_directory.name)
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=self.repository_root,
            check=True,
        )
        self._tracked_paths: list[str] = []

    def write(
        self,
        relative_path: str,
        content: str = "",
        *,
        tracked: bool = True,
    ) -> Path:
        path = self.repository_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if tracked:
            self._tracked_paths.append(relative_path)
        return path

    def run_checker(self) -> subprocess.CompletedProcess[str]:
        if self._tracked_paths:
            subprocess.run(
                ["git", "add", "--", *self._tracked_paths],
                cwd=self.repository_root,
                check=True,
            )
        return subprocess.run(
            [
                sys.executable,
                str(CHECKER_PATH),
                "--repository-root",
                str(self.repository_root),
            ],
            cwd=self.repository_root,
            capture_output=True,
            text=True,
        )

    def assert_checker_passes(self) -> subprocess.CompletedProcess[str]:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_supported_links_are_checked_after_code_is_ignored(self) -> None:
        self.write("assets/plot.png", "binary fixture")
        self.write("docs/target.md", "# Target\n")
        self.write("docs/Target Name.md", "# Encoded target\n")
        self.write(
            "docs/guide.md",
            """# Guide

[ordinary](target.md?view=raw#section)
![image](../assets/plot.png)
[angle](<Target Name.md>)
[reference]: <Target%20Name.md#heading> "title"
[reference use][reference]
[external](https://example.com/missing.md)
[protocol relative external](//example.com/missing.md)
[custom scheme](doi:10.1000/example)
`[inline code](missing-inline.md)`
````markdown
[fenced code](missing-fenced.md)
````
~~~text
[tilde fenced code](missing-tilde.md)
~~~
""",
        )

        self.assert_checker_passes()

    def test_only_tracked_markdown_files_are_scanned(self) -> None:
        self.write("README.md", "[tracked](target.md)\n")
        self.write("target.md", "# Target\n")
        self.write("scratch.md", "[untracked](missing.md)\n", tracked=False)

        result = self.assert_checker_passes()

        self.assertIn("2 tracked Markdown files", result.stdout)

    def test_missing_relative_target_has_stable_diagnostic(self) -> None:
        self.write("docs/guide.md", "first line\n[missing](missing.md)\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "docs/guide.md:2:missing.md:target does not exist\n",
        )

    def test_relative_target_cannot_escape_repository(self) -> None:
        self.write("docs/guide.md", "[escape](../../outside.md)\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "docs/guide.md:1:../../outside.md:path escapes repository\n",
        )

    def test_percent_decoding_cannot_bypass_escape_check(self) -> None:
        self.write("docs/guide.md", "[escape](%2e%2e/%2e%2e/outside.md)\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "docs/guide.md:1:%2e%2e/%2e%2e/outside.md:path escapes repository\n",
        )

    def test_target_case_must_match_filesystem_entry(self) -> None:
        self.write("docs/Target.md", "# Target\n")
        self.write("docs/guide.md", "[wrong case](target.md)\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "docs/guide.md:1:target.md:path component has incorrect case\n",
        )

    def test_host_local_destinations_are_only_allowed_in_results(self) -> None:
        host_destinations = (
            "/Users/researcher/run.csv",
            "C:/Users/researcher/run.csv",
            r"\\server\share\run.csv",
            "file:///Users/researcher/run.csv",
        )
        self.write(
            "docs/guide.md",
            "".join(
                f"[host path {index}](<{destination}>)\n"
                for index, destination in enumerate(host_destinations, 1)
            ),
        )
        self.write(
            "results/2026-07-10/README.md",
            "".join(
                f"[provenance {index}](<{destination}>)\n"
                for index, destination in enumerate(host_destinations, 1)
            ),
        )

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "".join(
                f"docs/guide.md:{index}:{destination}:"
                "host-local absolute destination is forbidden outside results/\n"
                for index, destination in enumerate(host_destinations, 1)
            ),
        )

    def test_relative_links_inside_results_are_still_checked(self) -> None:
        self.write("results/run/README.md", "[missing](raw/output.csv)\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "results/run/README.md:1:raw/output.csv:target does not exist\n",
        )

    def test_fragment_identifiers_are_not_validated_when_path_exists(self) -> None:
        self.write("docs/guide.md", "# Guide\n[local](#not-a-real-heading)\n")

        self.assert_checker_passes()


if __name__ == "__main__":
    unittest.main()
