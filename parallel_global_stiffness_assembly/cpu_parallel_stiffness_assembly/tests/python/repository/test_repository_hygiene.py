from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path


CPU_ROOT = Path(__file__).resolve().parents[3]


class RepositoryHygieneTests(unittest.TestCase):
    def test_active_cpu_sources_use_pgsa_openmp_capability_guard(self) -> None:
        source_suffixes = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        active_roots = [CPU_ROOT / name for name in ("include", "src", "apps", "tests/correctness")]
        compiler_openmp_guard = re.compile(
            r"^\s*#\s*(?:if|ifdef|ifndef|elif)\b[^\n]*\b_OPENMP\b"
        )
        violations: list[str] = []

        for source_root in active_roots:
            for path in sorted(source_root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in source_suffixes:
                    continue
                for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if compiler_openmp_guard.match(line):
                        relative = path.relative_to(CPU_ROOT)
                        violations.append(f"{relative}:{line_number}: {line.strip()}")

        self.assertEqual(
            violations,
            [],
            "active CPU sources must use PGSA_HAS_OPENMP as the only capability guard:\n"
            + "\n".join(violations),
        )

    def test_tracked_source_names_have_no_duplicate_suffix(self) -> None:
        git = shutil.which("git")
        self.assertIsNotNone(git, "git is required to inspect tracked source files")
        repository_root = subprocess.run(
            [git, "rev-parse", "--show-toplevel"],
            cwd=CPU_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        result = subprocess.run(
            [git, "ls-files", "-z"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        duplicates = sorted(
            path for path in result.stdout.split("\0") if path and " 2." in Path(path).name
        )

        self.assertEqual(
            duplicates,
            [],
            "tracked source files with duplicate suffixes:\n" + "\n".join(duplicates),
        )


if __name__ == "__main__":
    unittest.main()
