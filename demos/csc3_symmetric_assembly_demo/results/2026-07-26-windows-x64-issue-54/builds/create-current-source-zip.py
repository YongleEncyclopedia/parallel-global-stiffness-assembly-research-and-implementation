#!/usr/bin/env python3
"""从当前已提交的 Demo 源码生成确定性源码 ZIP。"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


REPOSITORY = Path(
    r"D:\parallel-global-stiffness-assembly-research-and-implementation"
)
DEMO = REPOSITORY / "demos" / "csc3_symmetric_assembly_demo"
PACKAGER_PATH = DEMO / "scripts" / "create_windows_delivery.py"


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        raise SystemExit(
            "usage: create-current-source-zip.py OUTPUT.zip COMMIT_SHA"
        )
    output = Path(arguments[0]).resolve()
    commit_sha = arguments[1]
    if output.exists():
        raise SystemExit(f"refusing to overwrite: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    spec = importlib.util.spec_from_file_location("windows_delivery", PACKAGER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load Windows delivery packager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = module.create_source_zip_from_commit(
        REPOSITORY,
        DEMO,
        commit_sha,
        [],
    )
    output.write_bytes(data)
    print(f"path={output}")
    print(f"size_bytes={len(data)}")
    print(f"sha256={hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
