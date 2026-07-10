from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


CPU_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = CPU_ROOT.parents[1]
CHECKER_PATH = CPU_ROOT / "scripts" / "check_markdown_links.py"


class RepositoryMarkdownLinkTests(unittest.TestCase):
    def test_all_tracked_markdown_destinations_resolve(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CHECKER_PATH),
                "--repository-root",
                str(REPOSITORY_ROOT),
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
