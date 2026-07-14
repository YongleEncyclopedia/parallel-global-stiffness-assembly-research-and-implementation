from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


CPU_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = CPU_ROOT.parents[1]
LEGACY_ROOT = CPU_ROOT / "legacy_gpu"

EXPECTED_LEGACY_SOURCES = {
    "build_and_test.bat",
    "build_and_test.ps1",
    "build_now.bat",
    "build_simple.bat",
    "cmake/CudaConfig.cmake",
    "compile_and_test.bat",
    "configure_and_build.bat",
    "include/backends/cuda/README.md",
    "include/backends/cuda/atomic_assembler.h",
    "include/backends/cuda/block_assembler.h",
    "include/backends/cuda/cuda_utils.cuh",
    "include/backends/cuda/scan_assembler.h",
    "include/backends/cuda/workqueue_assembler.h",
    "minimal_verify.cu",
    "minimal_verify_ascii.cu",
    "quick_build.bat",
    "quick_verify.cu",
    "src/backends/cuda/atomic_assembler.cu",
    "src/backends/cuda/block_assembler.cu",
    "src/backends/cuda/scan_assembler.cu",
    "src/backends/cuda/workqueue_assembler.cu",
}

ARCHIVE_SHA256 = {
    "intel_backend_thread_sweep_isolated_raw_2026-06-26.tar.gz": (
        "0b04b5c4000c23f7805085e8a3bd451d5032e3e3081430ccc01aab1fe5ecd8fb"
    ),
    "intel_backend_thread_sweep_raw_2026-06-26.tar.gz": (
        "cfe3ffc9aa03d71d9a9745db120fc660d26c8b89dc70045106d12b31395b2d79"
    ),
    "linux_intel_symbolic_parallel_backends_raw_2026-06-26.tar.gz": (
        "71910e33e0b8a1c3dbe564fba407e44599c3fb752126c0d059f79c8299209bf8"
    ),
}
ARCHIVE_PATHS = set(ARCHIVE_SHA256)


class RepositoryHygieneTests(unittest.TestCase):
    def test_retired_csc3_demo_archive_is_not_tracked(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "demos.zip"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(
            tracked.returncode,
            0,
            "the polluted root demos.zip archive must not remain tracked",
        )
        self.assertFalse(
            (REPOSITORY_ROOT / "demos.zip").exists(),
            "the retired root demos.zip archive must not exist in the worktree",
        )

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

    def test_legacy_gpu_manifest_maps_and_verifies_every_moved_file(self) -> None:
        manifest_path = LEGACY_ROOT / "MANIFEST.sha256"
        self.assertTrue(manifest_path.is_file(), manifest_path)
        entries: list[tuple[str, str, str]] = []
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            digest, source, target = line.split("\t")
            entries.append((digest, source, target))

        sources = [source for _, source, _ in entries]
        targets = [target for _, _, target in entries]
        self.assertEqual(len(entries), len(EXPECTED_LEGACY_SOURCES))
        self.assertEqual(sources, sorted(sources))
        self.assertEqual(set(sources), EXPECTED_LEGACY_SOURCES)
        self.assertEqual(len(targets), len(set(targets)))
        for digest, source, target in entries:
            with self.subTest(source=source, target=target):
                self.assertFalse((CPU_ROOT / source).exists())
                target_path = CPU_ROOT / target
                self.assertTrue(target_path.is_file(), target_path)
                self.assertEqual(hashlib.sha256(target_path.read_bytes()).hexdigest(), digest)

    def test_active_tree_contains_no_legacy_cuda_or_device_structs(self) -> None:
        self.assertFalse((CPU_ROOT / "src/backends/cuda").exists())
        self.assertFalse((CPU_ROOT / "include/backends/cuda").exists())
        for retired_cmake_file in (
            "CompilerFlags.cmake",
            "CudaConfig.cmake",
            "Dependencies.cmake",
            "README.md",
        ):
            self.assertFalse((CPU_ROOT / "cmake" / retired_cmake_file).exists())
        self.assertFalse((CPU_ROOT / "scripts/archive_gpu_legacy.py").exists())
        for suffix in ("*.cu", "*.bat", "*.ps1"):
            self.assertEqual(list(CPU_ROOT.glob(suffix)), [])

        soa_text = (CPU_ROOT / "include/core/soa.h").read_text(encoding="utf-8")
        self.assertNotIn("DeviceNodeCoordinates", soa_text)
        self.assertNotIn("DeviceConnectivity", soa_text)
        device_text = (LEGACY_ROOT / "include/core/device_soa.h").read_text(
            encoding="utf-8"
        )
        self.assertIn("struct DeviceNodeCoordinates", device_text)
        self.assertIn("struct DeviceConnectivity", device_text)

    def test_retired_raw_packages_and_tarballs_are_absent(self) -> None:
        for archive in ARCHIVE_PATHS:
            with self.subTest(archive=archive):
                self.assertFalse((CPU_ROOT / archive).exists())

        retired_packages = (
            "2026-06-26-intel-backend-thread-sweep-isolated-raw",
            "2026-06-26-intel-backend-thread-sweep-raw",
            "2026-06-26-linux-intel-symbolic-parallel-backends-raw",
        )
        for package in retired_packages:
            with self.subTest(package=package):
                self.assertFalse((CPU_ROOT / "results" / package).exists())

        tracked_archives = subprocess.run(
            ["git", "ls-files", "*.tar.gz"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(tracked_archives, [])

    def test_archive_provenance_tsv_covers_all_members_and_comparisons(self) -> None:
        provenance_path = CPU_ROOT / "results/2026-06-26-archive-provenance.tsv"
        self.assertTrue(provenance_path.is_file(), provenance_path)
        with provenance_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            rows = list(reader)

        self.assertEqual(
            reader.fieldnames,
            [
                "archive",
                "archive_sha256",
                "member",
                "archive_member_sha256",
                "working_tree_sha256",
                "normalized_lf_sha256",
                "comparison",
            ],
        )
        self.assertEqual(len(rows), 23)
        self.assertEqual({row["archive"] for row in rows}, ARCHIVE_PATHS)
        self.assertEqual(
            len({(row["archive"], row["member"]) for row in rows}), 23
        )
        for row in rows:
            self.assertEqual(row["archive_sha256"], ARCHIVE_SHA256[row["archive"]])
            for field in (
                "archive_sha256",
                "archive_member_sha256",
                "working_tree_sha256",
                "normalized_lf_sha256",
            ):
                self.assertRegex(row[field], r"^[0-9a-f]{64}$")

        line_ending_rows = [
            row for row in rows if row["comparison"] == "line_endings_only"
        ]
        self.assertEqual(len(line_ending_rows), 4)
        self.assertTrue(
            all(
                row["archive_member_sha256"] != row["working_tree_sha256"]
                and row["normalized_lf_sha256"] == row["working_tree_sha256"]
                for row in line_ending_rows
            )
        )

        run_log_row = next(row for row in rows if row["member"].endswith("/run.log"))
        self.assertEqual(
            run_log_row["comparison"], "archive_unique_extracted_byte_equal"
        )
        self.assertEqual(
            run_log_row["working_tree_sha256"],
            "48d7034d7ce565b68708216e89d24583c1380e1374c6b901431dd12705681310",
        )

        nonisolated_rows = [
            row
            for row in rows
            if row["archive"] == "intel_backend_thread_sweep_raw_2026-06-26.tar.gz"
        ]
        self.assertEqual(len(nonisolated_rows), 6)
        self.assertEqual(
            {row["comparison"] for row in nonisolated_rows}, {"byte_equal"}
        )

    def test_raw_runner_requires_repository_external_tar_destination(self) -> None:
        runner_path = CPU_ROOT / "scripts/run_linux_intel_symbolic_parallel_backends_raw.sh"
        runner = runner_path.read_text(encoding="utf-8")
        self.assertIn('TARBALL="${TARBALL:?', runner)
        self.assertIn('REPO_ROOT="$(git rev-parse --show-toplevel)"', runner)
        self.assertIn("tar destination must be outside the repository", runner)
        self.assertIn('TARBALL="$TARBALL"', runner)
        self.assertIn('REPEAT_COUNT="${REPEAT_COUNT:-3}"', runner)
        self.assertIn('--repeat-count "$REPEAT_COUNT"', runner)
        self.assertIn("isolated_symbolic_memory_summary.csv", runner)

        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "bash is required to validate the Linux runner")
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            missing_mesh = temp_root / "missing.inp"
            internal_target = CPU_ROOT / "issue28-symlink-probe.tar.gz"
            self.assertFalse(internal_target.exists())
            external_symlink = temp_root / "external-probe.tar.gz"
            external_symlink.symlink_to(internal_target)
            env = os.environ.copy()
            env.update(
                {
                    "TARBALL": str(external_symlink),
                    "OUT_DIR": str(temp_root / "out"),
                    "MESH": str(missing_mesh),
                }
            )
            result = subprocess.run(
                [bash, str(runner_path)],
                cwd=CPU_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "tar destination must not be a symbolic link",
                result.stdout + result.stderr,
            )
            self.assertFalse(internal_target.exists())

        gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(
            "/parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/*_raw_*.tar.gz",
            gitignore.splitlines(),
        )
        local_gitignore = (CPU_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("2026-06-26-linux-intel-symbolic-parallel-backends-raw", local_gitignore)

    def test_historical_result_gpu_script_remains_in_results(self) -> None:
        script = (
            CPU_ROOT
            / "results/2026-06-01-gpu-benchmark-nature-figure/plot_gpu_benchmark_nature.py"
        )
        self.assertTrue(script.is_file())
        self.assertEqual(
            hashlib.sha256(script.read_bytes()).hexdigest(),
            "7f70ea05704858fce9b339c54e25cdf24edbd049f0a84978ca12d0f129f36caf",
        )

    def test_gpu_cleanup_markdown_relative_links_resolve(self) -> None:
        markdown_link = re.compile(r"\[[^]]*\]\(([^)]+)\)")
        broken: list[str] = []
        markdown_paths = sorted(LEGACY_ROOT.rglob("*.md")) + [
            CPU_ROOT / "include/backends/README.md"
        ]
        for markdown in markdown_paths:
            for destination in markdown_link.findall(
                markdown.read_text(encoding="utf-8")
            ):
                destination = destination.strip("<>")
                if destination.startswith(("#", "http://", "https://")):
                    continue
                target = (markdown.parent / destination).resolve()
                if not target.exists():
                    broken.append(
                        f"{markdown.relative_to(CPU_ROOT)} -> {destination}"
                    )
        self.assertEqual(
            broken, [], "broken GPU-cleanup links:\n" + "\n".join(broken)
        )

    def test_legacy_gpu_guidance_has_no_deleted_active_entrypoints(self) -> None:
        guidance_paths = (
            CPU_ROOT / "README.md",
            CPU_ROOT.parent / "README.md",
            REPOSITORY_ROOT / "docs/context/legacy-gpu-assets.md",
        )
        guidance = "\n".join(path.read_text(encoding="utf-8") for path in guidance_paths)
        self.assertNotIn("scripts/archive_gpu_legacy.py", guidance)
        legacy_context = guidance_paths[-1].read_text(encoding="utf-8")
        self.assertIn("legacy_gpu/src/backends/cuda/", legacy_context)
        self.assertIn("legacy_gpu/include/backends/cuda/", legacy_context)
        self.assertIn("legacy_gpu/MANIFEST.sha256", legacy_context)


if __name__ == "__main__":
    unittest.main()
