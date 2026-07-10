from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


class PlanSourceOfTruthTests(unittest.TestCase):
    def test_completed_repository_plan_directory_is_removed(self) -> None:
        plans_dir = REPOSITORY_ROOT / "docs" / "plans"
        self.assertFalse(plans_dir.exists(), plans_dir)

        tracked = subprocess.run(
            ["git", "ls-files", "-z", "docs" + "/plans"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(tracked, "")

    def test_tracked_markdown_has_no_retired_plan_references(self) -> None:
        forbidden = (
            "docs" + "/plans",
            "2026-04-22-" + "chatgpt-pro-handoff",
            "2026-04-22-" + "git-lfs-rollout",
            "2026-05-20-" + "linux-intel-symbolic-memory-codex-prompt",
            "2026-05-23-" + "cross-platform-solver-validation-goal-prompts",
        )
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "*.md"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\0")
        violations: list[str] = []
        for relative in tracked:
            if not relative:
                continue
            text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            for marker in forbidden:
                if marker in text:
                    violations.append(f"{relative}: {marker}")

        self.assertEqual(
            violations,
            [],
            "retired repository-plan references remain:\n" + "\n".join(violations),
        )

    def test_governance_routes_active_plans_to_github_issues(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        contributing = (REPOSITORY_ROOT / "CONTRIBUTING.md").read_text(
            encoding="utf-8"
        )
        docs_index = (REPOSITORY_ROOT / "docs/README.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("GitHub Issue 为唯一活跃状态源", agents)
        self.assertIn("活跃计划只保存在 Issue", contributing)
        self.assertIn("GitHub Issues", docs_index)


if __name__ == "__main__":
    unittest.main()
