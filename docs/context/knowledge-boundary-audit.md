# Knowledge Boundary Audit

This audit lists the current project references, their knowledge role, and the recommended cleanup state. It is intentionally review-oriented: `Delete candidate` means "propose for confirmation", not "delete now".

Allowed status values: `Keep`, `Update`, `Archive`, `Delete candidate`, `Needs decision`.

## Status Summary

| Status | Meaning |
| --- | --- |
| `Keep` | Current, useful, and should remain part of the working knowledge boundary. |
| `Update` | Useful but contains stale wording, incomplete routing, or missing cross-links. |
| `Archive` | Historical or provenance material that should remain discoverable but not treated as current truth. |
| `Delete candidate` | Duplicate, accidental, or low-value artifact that should be removed only after explicit confirmation. |
| `Needs decision` | Requires user judgment before promoting, archiving, or deleting. |

## Audit Table

| 资料/路径 | 当前角色 | 知识层级 | 建议状态 | 理由 | 被引用位置 | 需要你确认的问题 |
| --- | --- | --- | --- | --- | --- | --- |
| `README.md` | Repository entrypoint and high-level project positioning. | L0 entry/boundary | `Keep` | Now links the current knowledge boundary/audit and includes `lock_guard` in the algorithm inventory. | Root entrypoint; plan docs and Beamer source descriptions refer to it. | 无。 |
| `docs/context/current-knowledge-boundary.md` | First-stop current boundary summary. | L0 boundary | `Keep` | New boundary file that separates current facts from historical/provenance materials. | To be linked from root README and repository scope. | 后续是否把它设为 future agent 的第一阅读入口。 |
| `docs/context/knowledge-boundary-audit.md` | Review table for keep/update/archive/delete decisions. | L0 audit | `Keep` | Implements the requested review surface for your edits. | To be linked from repository scope and current boundary. | 你后续会在此表中逐项批注还是希望拆成 issue/task list。 |
| `docs/context/repository-scope.md` | Repository inclusion/exclusion policy and source-of-truth ordering. | L0 boundary | `Keep` | Now links the current boundary/audit and puts `current-knowledge-boundary.md` first in the source-of-truth list. | Root docs context. | 无。 |
| `docs/requirements/cpu-parallel-stiffness-assembly-design.md` | Requirements, scope, and benchmark acceptance criteria. | L1 requirements | `Keep` | The stale "当前 CPU 侧只有串行实现" sentence is now marked as early-stage context and points to current CPU docs. | Root README, repository scope, long-term Beamer. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/README.md` | CPU mainline README, commands, algorithms, result fields. | L1/L2 implementation entry | `Keep` | Algorithm table now includes `lock_guard` and links back to the current knowledge boundary. | Root README, source index, docs/plans. | 无。 |
| `docs/plans/2026-04-22-chatgpt-pro-handoff.md` | Date-stamped handoff after CPU mainline consolidation. | L1 dated handoff | `Archive` | Useful historical handoff, but should not override later lock_guard, symbolic, memory, and cross-platform results. | Root README and docs/plans README. | 是否保留 as required reading or demote below current boundary file. |
| `docs/platform/cross-platform-strategy.md` | Platform/path compatibility strategy. | L1 platform strategy | `Keep` | Still matches CPU-first and cross-platform constraints. | Root README, docs/plans README. | 无。 |
| `docs/platform/cross-platform-benchmark-schema.md` | Cross-platform benchmark package schema. | L1/L3 benchmark schema | `Keep` | Current reports and packaging scripts still depend on schema concepts. | CPU README and Beamer source index. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/cpu_algorithms.md` | Current algorithm taxonomy and implementation notes. | L2 implementation truth | `Keep` | Most current local source for seven CPU algorithms, including `lock_guard`. | Long-term Beamer source index; reports. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/symbolic_numeric_assembly.md` | Symbolic/numeric terminology and mentor mapping. | L2 concept/implementation truth | `Keep` | Current and directly connected to 2026-05 result evidence. | Long-term Beamer source index; 2026-05-22 report. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/memory_lifecycle.md` | Memory lifecycle definitions. | L2 concept/measurement truth | `Keep` | Prevents incorrect mixing of CSR, transient buffers, backend memory, and RSS. | Long-term Beamer source index; weekly report. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/implementation_notes.md` | Backend stage split and experiment order. | L2 implementation notes | `Keep` | Still useful as concise experiment/implementation orientation. | CPU docs directory. | 无。 |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/docs/cpu/smoke_test_results.md` | Packaging-era smoke results. | L3 smoke/provenance | `Archive` | Useful sanity history but not current benchmark conclusion. | CPU docs directory. | 是否 keep visible or move under validation/provenance index. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/results/2026-05-20-linux-intel-symbolic-memory-full-host/` | Latest Linux Intel symbolic/memory evidence. | L3 current result evidence | `Keep` | Most relevant current Intel full-host symbolic/memory package. | Long-term Beamer source index; 2026-05-22 weekly deck. | 无。 |
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
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/legacy_gpu/` | GPU legacy archive marker. | L5 legacy | `Archive` | Keep as explicit archive only if CUDA dirs remain or provenance is needed. | CPU README. | 是否 later move all CUDA code under this archive. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/include/backends/cuda/` | CUDA headers still under default source tree. | L5 legacy/source candidate | `Archive` | Current project excludes GPU new algorithm work; CUDA headers should not be read as current mainline. | CPU README legacy section. | 是否 move to `legacy_gpu/` after branch-safe confirmation. |
| `parallel_global_stiffness_assembly/cpu_parallel_stiffness_assembly/src/backends/cuda/` | CUDA sources still under default source tree. | L5 legacy/source candidate | `Archive` | Same as above; keep only if build/scripts still require them. | CPU README legacy section. | 是否 move to `legacy_gpu/` after checking CMake references. |
| `docs/plans/2026-05-20-linux-intel-symbolic-memory-codex-prompt.md` | Date-stamped prompt for Intel symbolic/memory run. | L5 execution prompt/provenance | `Archive` | Useful to understand how results were requested, not current truth itself. | docs/plans. | 是否 retain as provenance or fold into result README later. |
| Previously tracked Finder/manual duplicate suffix files | Finder/manual duplicate copies. | L6 cleanup | `Archive` | Removed from the active working tree after checksum or targeted diff review; canonical siblings remain. | None expected. | 无。 |

## Applied Cleanup Items

- 2026-05-23: Removed the previously listed Finder/manual duplicate suffix files after checksum or targeted diff review. Canonical sibling files remain.

## Applied Sync Items

- Added `lock_guard` to the root README and CPU mainline README algorithm inventories.
- Marked the requirements sentence "当前 CPU 侧只有串行实现" as historical early-stage context.
- Linked `current-knowledge-boundary.md` and this audit from `README.md` and `docs/context/repository-scope.md`.
- Clarified that `project-long-term-beamer/source_index.md` is a Beamer source manifest, not a full repository source-of-truth index.
- Removed the obsolete early Mac Studio validation record from the active working tree and CPU README related-doc list.
- Removed tracked Finder/manual duplicate suffix files; canonical sibling files remain.

## Deferred Cleanup Items

- Decide whether CUDA headers/sources should be physically moved under `legacy_gpu/` or kept in place with stronger README warnings.
- Decide whether early 2026-04 result variants should be consolidated to one canonical presentation-chart source.
