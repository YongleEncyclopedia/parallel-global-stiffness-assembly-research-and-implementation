# Git LFS Rollout Plan

## Goal

Roll the repository onto Git LFS for the large engineering mesh without rewriting history, keep normal Git diffs for small example inputs, and align local and remote collaboration settings with a CPU-research workflow.

## Scope

1. Install and initialize `git-lfs` on the current macOS workstation.
2. Track `examples/3d-WindTurbineHub.inp` with Git LFS using a no-history-rewrite migration.
3. Document the collaborator workflow: install LFS, clone, and run `git lfs pull`.
4. Enable automatic deletion of merged branches on GitHub.
5. Remove obsolete merged feature branches after verification.

## Explicit Non-Goals

- Do not rewrite repository history with `git lfs migrate import --everything`.
- Do not force-push `main`.
- Do not enable GitHub source archives to include LFS objects by default.
- Do not move the small example `.inp` files into Git LFS.

## Verification Targets

- `git lfs version` succeeds locally.
- `.gitattributes` contains the repository-local LFS tracking rule.
- `git lfs ls-files` shows `examples/3d-WindTurbineHub.inp`.
- GitHub repository setting `delete_branch_on_merge` is enabled.
- Remote merged feature branch `codex/cpu-rename-sync` is removed.
