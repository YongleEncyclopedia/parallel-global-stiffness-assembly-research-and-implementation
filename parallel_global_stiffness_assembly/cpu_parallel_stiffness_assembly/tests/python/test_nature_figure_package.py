#!/usr/bin/env python3
"""Tests for the Nature-style project visualization redraw package."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from plot_nature_figures import (  # noqa: E402
    EXPECTED_FORMATS,
    LEGEND_REQUIRED_SECTIONS,
    REQUIRED_SOURCE_FAMILIES,
    figure_legends,
    planned_nature_outputs,
    source_family_inputs,
    validate_source_inputs,
)


class NatureFigurePackageTests(unittest.TestCase):
    def test_source_family_inputs_cover_all_project_visualization_families(self) -> None:
        families = source_family_inputs(PROJECT_ROOT)

        self.assertEqual(set(families), REQUIRED_SOURCE_FAMILIES)
        for family, paths in families.items():
            with self.subTest(family=family):
                self.assertTrue(paths, f"{family} has no declared source inputs")
                self.assertTrue(all(path.exists() for path in paths), f"{family} has missing source inputs")

    def test_planned_outputs_use_publication_formats_and_manifest(self) -> None:
        outputs = planned_nature_outputs(PROJECT_ROOT)
        relative_outputs = {path.relative_to(PROJECT_ROOT).as_posix() for path in outputs}

        stems = {path.with_suffix("").relative_to(PROJECT_ROOT).as_posix() for path in outputs if path.suffix != ".md"}
        suffixes_by_stem = {
            stem: {
                path.suffix
                for path in outputs
                if path.suffix != ".md" and path.with_suffix("").relative_to(PROJECT_ROOT).as_posix() == stem
            }
            for stem in stems
        }

        self.assertIn("results/nature-figures-2026-05-26/manifest.md", relative_outputs)
        self.assertIn("results/nature-figures-2026-05-26/figure_legends.md", relative_outputs)
        self.assertGreaterEqual(len(stems), 8)
        self.assertTrue(all(suffixes == EXPECTED_FORMATS for suffixes in suffixes_by_stem.values()))
        self.assertTrue(all("presentation_charts" not in item for item in relative_outputs))

    def test_validate_source_inputs_reports_complete_existing_data(self) -> None:
        validation = validate_source_inputs(PROJECT_ROOT)

        self.assertEqual(validation["missing"], [])
        self.assertEqual(set(validation["families"]), REQUIRED_SOURCE_FAMILIES)

    def test_each_redrawn_figure_has_detailed_legend_sections(self) -> None:
        legends = figure_legends()

        stems = {
            path.with_suffix("").name
            for path in planned_nature_outputs(PROJECT_ROOT)
            if path.suffix in EXPECTED_FORMATS
        }
        self.assertEqual(set(legends), stems)
        for stem, sections in legends.items():
            with self.subTest(stem=stem):
                self.assertEqual(set(sections), LEGEND_REQUIRED_SECTIONS)
                for section, text in sections.items():
                    self.assertGreaterEqual(
                        len(text),
                        80,
                        f"{stem} {section} legend section is too terse for manuscript use",
                    )


if __name__ == "__main__":
    unittest.main()
