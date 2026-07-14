# Knowledge Boundary Audit

This audit lists the current project references, their knowledge role, and the recommended cleanup state. It is intentionally review-oriented: `Delete candidate` means "propose for confirmation", not "delete now".

Allowed status values: `Keep`, `Update`, `Archive`, `Migrated and deleted`, `Delete candidate`, `Needs decision`.

## Status Summary

| Status | Meaning |
| --- | --- |
| `Keep` | Current, useful, and should remain part of the working knowledge boundary. |
| `Update` | Useful but contains stale wording, incomplete routing, or missing cross-links. |
| `Archive` | Historical or provenance material that should remain discoverable but not treated as current truth. |
| `Migrated and deleted` | Long-lived knowledge was moved to a stable source, then the superseded or duplicate source was removed. |
| `Delete candidate` | Duplicate, accidental, or low-value artifact that should be removed only after explicit confirmation. |
| `Needs decision` | Requires user judgment before promoting, archiving, or deleting. |

## Audit Table

| 资料/路径 | 当前角色 | 知识层级 | 建议状态 | 理由 | 被引用位置 | 需要你确认的问题 |
| --- | --- | --- | --- | --- | --- | --- |
| `README.md` | Repository entrypoint and high-level project positioning. | L0 entry/boundary | `Keep` | Links the current knowledge boundary, platform protocols and CPU mainline. | Root entrypoint and Beamer source descriptions refer to it. | 无。 |
| `docs/context/current-knowledge-boundary.md` | First-stop current boundary summary. | L0 boundary | `Keep` | Separates current facts, active Issue state and historical/provenance materials. | Root README and repository scope. | 无。 |
| `docs/context/knowledge-boundary-audit.md` | Review table for keep/update/archive/delete decisions. | L0 audit | `Keep` | Records completed migrations without retaining superseded sources. | Repository scope and current boundary. | 无。 |
| `docs/context/repository-scope.md` | Repository inclusion/exclusion policy and source-of-truth ordering. | L0 boundary | `Keep` | Now links the current boundary/audit and puts `current-knowledge-boundary.md` first in the source-of-truth list. | Root docs context. | 无。 |
| `docs/requirements/cpu-parallel-stiffness-assembly-design.md` | Requirements, scope, and benchmark acceptance criteria. | L1 requirements | `Keep` | The stale "当前 CPU 侧只有串行实现" sentence is now marked as early-stage context and points to current CPU docs. | Root README, repository scope, long-term Beamer. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md` | CPU mainline README, commands, algorithms, result fields. | L1/L2 implementation entry | `Keep` | Canonical implementation and CLI entry, including `linear_elastic_solid` and validation workflows. | Root README, source index and platform protocols. | 无。 |
| Git LFS rollout plan (2026-04-22) | Completed repository migration plan. | L1 completed coordination | `Migrated and deleted` | Materialization and pointer-safety rules are now enforced by Git attributes, README guidance, workflow helpers and contributor rules. | `.gitattributes`, root/examples README and `CONTRIBUTING.md`. | 无。 |
| CPU mainline handoff (2026-04-22) | Completed handoff snapshot. | L1 completed coordination | `Migrated and deleted` | Current facts moved to the knowledge boundary, CPU README and structured result evidence; stale task narration was not copied. | Current boundary, CPU README and result packages. | 无。 |
| Linux Intel symbolic/memory execution prompt (2026-05-20) | Completed machine-session prompt. | L1 completed coordination | `Migrated and deleted` | Full-host, repeat and memory-lifecycle rules moved into the stable Linux Intel experiment protocol. | Linux Intel protocol and result report. | 无。 |
| Cross-platform solver-validation goal prompts (2026-05-23) | Completed platform-session prompts. | L1 completed coordination | `Migrated and deleted` | The four-case, seven-file and comparison contract moved into the stable validation protocol; session instructions were discarded. | Cross-platform validation protocol. | 无。 |
| `docs/platform/cross-platform-strategy.md` | Platform/path compatibility strategy. | L1 platform strategy | `Keep` | Describes the current Linux Intel, macOS ARM64 and Windows AMD roles and the CI/physical-host boundary. | Root README and platform index. | 无。 |
| `docs/platform/linux-intel-experiment-protocol.md` | Stable full-host performance and memory protocol. | L1/L3 experiment protocol | `Keep` | Separates physical-core sweeps, repeat semantics, estimated memory and isolated OS measurements. | Platform index and CPU README. | 无。 |
| `docs/platform/cross-platform-validation-protocol.md` | Stable four-case solver-validation contract. | L1/L3 validation protocol | `Keep` | Defines seven-file export, MATLAB solve, reference mapping and no-hard-threshold reporting. | Platform index and CPU README. | 无。 |
| `docs/platform/cross-platform-benchmark-schema.md` | Cross-platform benchmark package schema. | L1/L3 benchmark schema | `Keep` | Current reports and packaging scripts still depend on schema concepts. | CPU README and Beamer source index. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md` | Current algorithm taxonomy and implementation notes. | L2 implementation truth | `Keep` | Most current local source for seven CPU algorithms, including `lock_guard`. | Long-term Beamer source index; reports. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md` | Symbolic/numeric terminology and mentor mapping. | L2 concept/implementation truth | `Keep` | Current and directly connected to 2026-05 result evidence. | Long-term Beamer source index; 2026-05-22 report. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/memory_lifecycle.md` | Memory lifecycle definitions. | L2 concept/measurement truth | `Keep` | Prevents incorrect mixing of CSR, transient buffers, backend memory, and RSS. | Long-term Beamer source index; weekly report. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/implementation_notes.md` | Backend stage split and experiment order. | L2 implementation notes | `Keep` | Current notes should point to `linear_elastic_solid`; any `simplified` mention must be legacy synthetic only. | CPU docs directory. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/smoke_test_results.md` | Packaging-era smoke results. | L3 smoke/provenance | `Archive` | Useful sanity history but not current benchmark conclusion; `simplified` rows are legacy synthetic provenance. | CPU docs directory. | 是否 keep visible or move under validation/provenance index. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-07-08-linux-intel-symbolic-parallel-backends-raw/` | Current Linux Intel five-backend isolated evidence. | L3 current result evidence | `Keep` | Three independent subprocess repeats per algorithm/thread; median summary includes backend preparation, accumulation, total time and isolated peak RSS. | Current knowledge boundary; 2026-07-10 report. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-07-10-linux-symbolic-parallel-backend-metrics/` | Current five-backend main figure and thread trends. | L4 current report | `Keep` | Reads only the 2026-07-08 summary CSV and preserves source rows for every figure. | Reports index and current knowledge boundary. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/` | Earlier Linux Intel symbolic/memory evidence. | L3 historical result evidence | `Archive` | Useful for experiment evolution, but superseded for current five-backend timing and isolated-memory claims by the 2026-07-08 package. | Long-term Beamer source index; 2026-05-22 weekly deck. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-16-mentor-action-items/` | Mentor action-item result package. | L3 current result evidence | `Keep` | Contains parallel symbolic/direct, lock_guard vs atomic, sparse pattern, and cross-platform v2 package. | Long-term Beamer source index; weekly deck. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/cross-platform-v1/` | First cross-platform package and figures. | L3 current/comparison evidence | `Keep` | Still cited for Intel/Apple profile comparison figures. | Long-term Beamer source index. | 是否 supersede部分内容 by cross-platform v2 when enough figures exist. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-symbolic-numeric/` | Initial symbolic/numeric report. | L3 result evidence | `Keep` | Still cited for symbolic reuse concepts and control experiments. | Long-term Beamer source index. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-11-thread-scaling*` and `results/2026-05-12-thread-scaling-linux-intel-*` | Thread scaling and Intel core-profile evidence. | L3 result evidence | `Keep` | Still useful for platform/profile interpretation. | Long-term Beamer source index; mentor deck. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-14-thread-scaling-macos-m4max-*` | Apple QoS-biased profile evidence. | L3 comparison evidence | `Keep` | Useful only as Apple scheduler-boundary evidence, not equivalent to Intel taskset. | cross-platform reports and Beamer notes. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-22/` | Initial CPU benchmark run and figures. | L3 early result/provenance | `Archive` | Useful for historical trajectory and early figures, but superseded for current conclusions. | CPU README examples; validation doc. | 是否 keep examples pointing to this date or switch examples to generic `results/YYYY-MM-DD`. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-04-28-*` | Presentation chart generation packages. | L3 early/presentation source | `Archive` | Useful for monthly/Beamer figure provenance; not latest benchmark truth. | Long-term Beamer direct figure references; 2026-05-14 deck. | 是否 consolidate three repeat/run variants after confirming which one is canonical. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/project-long-term-beamer/` | Long-term project handbook. | L4 handbook | `Keep` | Stable learning/manual layer; should maintain `source_index.md`. | Root reporting workflow and source index. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/project-long-term-beamer/source_index.md` | Source manifest for long-term Beamer only. | L4 Beamer provenance | `Keep` | Now explicitly says it is not the full repository knowledge-boundary index. | Long-term Beamer README. | 是否需要 separate full-repo source manifest later. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-14-mentor-next-steps-beamer/` | Date-stamped mentor report package. | L4 dated report | `Archive` | Keep as a snapshot; it must not override later 2026-05-20 evidence. | Long-term Beamer source index. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/reports/2026-05-22-weekly-meeting-beamer/` | Date-stamped weekly report package. | L4 dated report | `Keep` | Latest weekly narrative and Q&A, but still subordinate to structured result data. | Long-term Beamer source index. | 无。 |
| `docs/context/monthly-intern-reports/` | AI-readable monthly report extracts. | L5 historical narrative/provenance | `Keep` | Useful for January problem framing and April CPU-first pivot; does not override result data. | repository-scope and source index currently reference it. | 是否 keep in repo after reviewing extracted content. |
| `docs/context/legacy-gpu-assets.md` | GPU legacy policy. | L5 legacy boundary | `Keep` | Correctly says GPU assets are reference only. | repository-scope. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/legacy_gpu/` | Deterministic GPU-first archive with migration manifest. | L5 legacy | `Archive` | CUDA sources and Windows scripts are isolated from the default tree and retained only for provenance. | CPU README and GPU legacy policy. | 无。 |
| Active CUDA backend paths (before 2026-07-10) | Superseded default-tree locations. | L5 completed cleanup | `Migrated and deleted` | Exact files moved under `legacy_gpu/`; active headers no longer expose partial device APIs. | Migration manifest and archive README. | 无。 |
| Previously tracked Finder/manual duplicate suffix files | Finder/manual duplicate copies. | L6 cleanup | `Migrated and deleted` | Removed after checksum or targeted diff review; canonical siblings remain. | None expected. | 无。 |

## Applied Cleanup Items

- 2026-05-23: Removed the previously listed Finder/manual duplicate suffix files after checksum or targeted diff review. Canonical sibling files remain.
- 2026-07-10: Moved the exact GPU-first file set under `legacy_gpu/`, removed three redundant raw tar packages after per-member hash review, and retained the archive-unique log with provenance.
- 2026-07-10: Migrated durable LFS, Linux Intel and solver-validation knowledge, then removed the completed repository plan directory without creating an archive copy.
- 2026-07-14, Issue #49: Removed eight superseded or factually unsafe report packages, three obsolete June raw packages, two duplicate Nature-derived packages, obsolete plot scripts, caches, build output and repository-retained TIFF/FIG duplicates. Updated routing to the 2026-07-08 raw data and 2026-07-10 report. Git history was not rewritten.

## Applied Sync Items

- Added `lock_guard` to the root README and CPU mainline README algorithm inventories.
- Marked the requirements sentence "当前 CPU 侧只有串行实现" as historical early-stage context.
- Linked `current-knowledge-boundary.md` and this audit from `README.md` and `docs/context/repository-scope.md`.
- Clarified that `project-long-term-beamer/source_index.md` is a Beamer source manifest, not a full repository source-of-truth index.
- Removed the obsolete early Mac Studio validation record from the active working tree and CPU README related-doc list.
- Removed tracked Finder/manual duplicate suffix files; canonical sibling files remain.
- Made GitHub Issues the only active plan state and linked the stable Linux Intel and solver-validation protocols.
- Updated platform roles to Linux Intel, macOS ARM64 and Windows AMD.

## Deferred Cleanup Items

- Decide whether early 2026-04 result variants should be consolidated to one canonical presentation-chart source.
