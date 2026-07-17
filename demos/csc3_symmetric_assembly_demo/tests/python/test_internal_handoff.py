#!/usr/bin/env python3
"""Contract tests for the local-smoke internal handoff builder."""

from __future__ import annotations

import csv
import dataclasses
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = DEMO_ROOT / "scripts" / "create_internal_handoff.py"
EVIDENCE = DEMO_ROOT / "results" / "2026-07-13-macos-arm64-local-smoke"
CANONICAL_REPORT = (
    DEMO_ROOT
    / "reports"
    / "2026-07-13-csc3-demo-macos-local-smoke-test-report.zh-CN.md"
)


def load_handoff_module():
    spec = importlib.util.spec_from_file_location("csc3_internal_handoff", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load internal handoff builder: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HANDOFF = load_handoff_module()


def copy_evidence(root: Path) -> Path:
    destination = root / "evidence"
    shutil.copytree(EVIDENCE, destination)
    return destination


def rebind_artifact(evidence: Path, name: str) -> None:
    path = evidence / name
    manifest_path = evidence / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(item for item in manifest["artifacts"] if item["path"] == name)
    record["size_bytes"] = path.stat().st_size
    record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class PerformanceDataTests(unittest.TestCase):
    def test_accepts_crlf_checkout_when_manifest_binds_canonical_lf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-crlf-") as directory:
            evidence = copy_evidence(Path(directory))
            samples = evidence / "benchmark_samples.csv"
            canonical = samples.read_bytes()
            self.assertNotIn(b"\r", canonical)
            samples.write_bytes(canonical.replace(b"\n", b"\r\n"))

            data = HANDOFF.load_performance_data(evidence)

            self.assertEqual(data.case_name, "cube_tet4_1x1x1")
            self.assertAlmostEqual(data.candidates[1].numeric_speedup, 0.018219162451028871)

    def test_archived_local_smoke_metrics_are_recomputed_from_raw_samples(self) -> None:
        data = HANDOFF.load_performance_data(EVIDENCE)

        self.assertEqual(data.evidence_status, "LOCAL_SMOKE")
        self.assertEqual(data.evidence_level, "local-smoke")
        self.assertEqual(data.case_name, "cube_tet4_1x1x1")
        self.assertEqual(data.element_type, "Tet4")
        self.assertEqual(data.cpu_model, "Apple M5")
        self.assertEqual(data.architecture, "arm64")
        self.assertEqual(data.thread_counts, (1, 2))
        self.assertEqual((data.warmup_count, data.repeat_count), (1, 2))
        self.assertAlmostEqual(data.serial_symbolic_ms, 0.029, places=12)
        self.assertAlmostEqual(data.serial_numeric_ms, 0.000479, places=12)

        one, two = data.candidates
        self.assertEqual(one.thread_count, 1)
        self.assertAlmostEqual(one.symbolic_ms, 0.0174585, places=12)
        self.assertAlmostEqual(one.numeric_ms, 0.001479, places=12)
        self.assertAlmostEqual(one.symbolic_speedup, 1.6610819944439668)
        self.assertAlmostEqual(one.numeric_speedup, 0.32386747802569305)
        self.assertEqual(two.thread_count, 2)
        self.assertAlmostEqual(two.symbolic_ms, 0.106604, places=12)
        self.assertAlmostEqual(two.numeric_ms, 0.026291, places=12)
        self.assertAlmostEqual(two.symbolic_speedup, 0.27203482045701849)
        self.assertAlmostEqual(two.numeric_speedup, 0.018219162451028871)

    def test_rejects_duplicate_measured_sample_index(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-evidence-") as directory:
            evidence = copy_evidence(Path(directory))
            samples = evidence / "benchmark_samples.csv"
            with samples.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                fieldnames = reader.fieldnames
                rows = list(reader)
            self.assertIsNotNone(fieldnames)
            duplicate = next(
                row
                for row in rows
                if row["thread_count"] == "1"
                and row["sample_kind"] == "measured"
                and row["sample_index"] == "2"
            )
            duplicate["sample_index"] = "1"
            with samples.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream, fieldnames=fieldnames, lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(rows)
            rebind_artifact(evidence, "benchmark_samples.csv")

            with self.assertRaisesRegex(HANDOFF.HandoffError, "样本索引"):
                HANDOFF.load_performance_data(evidence)

    def test_rejects_csv_case_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-evidence-") as directory:
            evidence = copy_evidence(Path(directory))
            samples = evidence / "benchmark_samples.csv"
            with samples.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                fieldnames = reader.fieldnames
                rows = list(reader)
            self.assertIsNotNone(fieldnames)
            rows[0]["case_name"] = "different_case"
            with samples.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream, fieldnames=fieldnames, lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(rows)
            rebind_artifact(evidence, "benchmark_samples.csv")

            with self.assertRaisesRegex(HANDOFF.HandoffError, "case_name"):
                HANDOFF.load_performance_data(evidence)

    def test_rejects_invalid_evidence_commit_sha(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-evidence-") as directory:
            evidence = copy_evidence(Path(directory))
            manifest_path = evidence / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source"]["commit_sha"] = "not-a-commit"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(HANDOFF.HandoffError, "commit_sha"):
                HANDOFF.load_performance_data(evidence)

    def test_rejects_duplicate_thread_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-evidence-") as directory:
            evidence = copy_evidence(Path(directory))
            summary_path = evidence / "benchmark_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["per_thread_measured_statistics"].append(
                summary["per_thread_measured_statistics"][0]
            )
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            rebind_artifact(evidence, "benchmark_summary.json")

            with self.assertRaisesRegex(HANDOFF.HandoffError, "重复线程"):
                HANDOFF.load_performance_data(evidence)

    def test_reader_facing_report_states_the_nonformal_boundary(self) -> None:
        data = HANDOFF.load_performance_data(EVIDENCE)
        report = HANDOFF.render_handoff_report(
            canonical_report=CANONICAL_REPORT.read_text(encoding="utf-8"),
            data=data,
            source_commit="1" * 40,
            source_archive_name="csc3-symmetric-assembly-demo-v0.2.0+111111111111.zip",
            source_archive_sha256="2" * 64,
        )

        for required in (
            "macOS ARM64 本地验证",
            "NON-FORMAL",
            "不能用于 Linux Intel/WindHub 正式性能验收",
            "$p=2$ 的符号组装和原子数值组装均慢于串行基线",
            "本节只保留可审计的原始计时表，不展示性能对比图",
            "`1111111111111111111111111111111111111111`",
            "`2222222222222222222222222222222222222222222222222222222222222222`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)
        self.assertNotIn("![", report)
        self.assertNotIn("../figures/", report)
        self.assertNotIn("SVG 矢量图", report)
        self.assertTrue(report.endswith(
            "NON-FORMAL PERFORMANCE EVIDENCE — NOT FOR DELIVERY ACCEPTANCE\n"
        ))

    def test_reader_facing_conclusion_is_derived_from_speedups(self) -> None:
        data = HANDOFF.load_performance_data(EVIDENCE)
        faster_two_thread = dataclasses.replace(
            data.candidates[1], symbolic_speedup=1.2, numeric_speedup=1.3
        )
        changed = dataclasses.replace(
            data, candidates=(data.candidates[0], faster_two_thread)
        )
        report = HANDOFF.render_handoff_report(
            canonical_report=CANONICAL_REPORT.read_text(encoding="utf-8"),
            data=changed,
            source_commit="1" * 40,
            source_archive_name="csc3-symmetric-assembly-demo-v0.2.0+111111111111.zip",
            source_archive_sha256="2" * 64,
        )

        self.assertIn("$p=2$ 的符号组装和原子数值组装均快于串行基线", report)
        self.assertNotIn("$p=2$ 的符号组装和原子数值组装均慢于串行基线", report)


class ArchiveTests(unittest.TestCase):
    def test_verification_rejects_embedded_pass_text_inside_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-test-") as directory:
            verification = Path(directory) / "verification.json"
            verification.write_text(
                '{"status":"FAIL","message":"fake {\\\"status\\\":\\\"PASS\\\"}"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(HANDOFF.HandoffError, "未记录 PASS"):
                HANDOFF._read_pass_verification(verification, "verification")

    def test_outer_archive_is_deterministic_and_checksum_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="csc3-handoff-test-") as directory:
            root = Path(directory)
            source = root / "source.zip"
            report = root / "report.md"
            manifest_verification = root / "manifest.json"
            clean_room = root / "clean-room.log"
            source.write_bytes(b"source archive\n")
            report.write_text("# report\n", encoding="utf-8")
            manifest_verification.write_text('{"status":"PASS"}\n', encoding="utf-8")
            clean_room.write_text('{"status":"PASS"}\n', encoding="utf-8")

            first = root / "first.zip"
            second = root / "second.zip"
            arguments = dict(
                source_archive=source,
                report=report,
                manifest_verification=manifest_verification,
                clean_room_verification=clean_room,
                source_commit="a" * 40,
            )
            first_sha = HANDOFF.create_handoff_archive(output=first, **arguments)
            second_sha = HANDOFF.create_handoff_archive(output=second, **arguments)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_sha, second_sha)
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                package_root = names[0].split("/", 1)[0]
                checksum_path = f"{package_root}/SHA256SUMS"
                self.assertIn(checksum_path, names)
                checksum = archive.read(checksum_path).decode("utf-8")
                self.assertIn("source/source.zip", checksum)
                self.assertIn("reports/report.md", checksum)
                self.assertFalse(any("/figures/" in name for name in names))
                self.assertNotIn("SHA256SUMS", checksum)
                for line in checksum.splitlines():
                    digest, relative_path = line.split("  ", 1)
                    member = f"{package_root}/{relative_path}"
                    self.assertEqual(
                        digest,
                        hashlib.sha256(archive.read(member)).hexdigest(),
                    )
                self.assertFalse(any(".." in Path(name).parts for name in names))


if __name__ == "__main__":
    unittest.main()
