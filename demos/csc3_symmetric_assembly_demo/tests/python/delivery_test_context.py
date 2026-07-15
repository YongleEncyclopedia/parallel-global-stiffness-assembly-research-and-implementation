"""Resolve repository-only test inputs without crossing package boundaries."""

from __future__ import annotations

import json
from pathlib import Path


BUILD_INFO_SCHEMA = "csc3-demo-build-info-v1"
REPOSITORY_DEMO_DIRECTORY = "csc3_symmetric_assembly_demo"


def repository_workflow_text(demo_root: Path) -> str | None:
    """Return the repository workflow, or ``None`` for a bound source package.

    A delivery archive intentionally contains only the standalone demo. Its
    tests recognize the generated BUILD_INFO.json boundary instead of probing
    arbitrary parent directories for repository metadata.
    """
    workflow_path = demo_root.parents[1] / ".github" / "workflows" / "ci.yml"
    if workflow_path.is_file():
        if (
            demo_root.parent.name != "demos"
            or demo_root.name != REPOSITORY_DEMO_DIRECTORY
        ):
            raise AssertionError("repository demo layout does not match its contract")
        return workflow_path.read_text(encoding="utf-8")

    build_info_path = demo_root / "BUILD_INFO.json"
    if not build_info_path.is_file() or build_info_path.is_symlink():
        raise AssertionError(
            "demo is neither a repository checkout nor a bound delivery package"
        )
    try:
        build_info = json.loads(build_info_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"invalid package BUILD_INFO.json: {error}") from error
    if not isinstance(build_info, dict):
        raise AssertionError("package BUILD_INFO.json must contain an object")
    if build_info.get("schema_version") != BUILD_INFO_SCHEMA:
        raise AssertionError("package BUILD_INFO.json has an unsupported schema_version")
    if build_info.get("archive_root") != demo_root.name:
        raise AssertionError("package BUILD_INFO.json archive_root does not match its root")
    return None
